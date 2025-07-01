import os
import uuid
import json
import re
from typing import List, Optional, Dict, Any, Union
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path

from .story_creator.agent import create_story, create_story_response_stream
from .parody_creator.agent import create_parody, create_parody_response_stream
from .granny.agent import create_granny_response, create_granny_response_stream
from .state import ChatMessage, State
from .tools.tool_executor import execute_tool
from .tools.tool_config import ToolConfig

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, AIMessage
import threading

# Import supervisor functionality
try:
    from .supervisor.supervisor_agent import create_supervisor_agent, create_advanced_supervisor_agent
    SUPERVISOR_AVAILABLE = True
    print("✓ Supervisor functionality available")
except ImportError as e:
    print(f"⚠️  Supervisor not available: {e}")
    SUPERVISOR_AVAILABLE = False

chats_lock = threading.Lock()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "../chats.json"
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        chats: dict = json.load(f)
else:
    chats = {}

def save_chats():
    """Save chats to disk, filtering out empty conversations"""
    with chats_lock:
        # Filter out empty chats (no messages and no enabled agents)
        filtered_chats = {}
        for chat_id, chat_data in chats.items():
            has_messages = len(chat_data.get("history", [])) > 0
            has_enabled_agents = any(
                agent.get("enabled", False) 
                for agent in chat_data.get("agent_sequence", [])
            )
            
            # Keep chat if it has messages OR enabled agents
            if has_messages or has_enabled_agents:
                filtered_chats[chat_id] = chat_data
        
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered_chats, f, indent=2, ensure_ascii=False)

def sanitize_node_id(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', text)

AGENTS_REGISTRY = {
    "story_creator": create_story,
    "parody_creator": create_parody,
    "granny": create_granny_response,
}

TOOL_CONFIGS: Dict[str, ToolConfig] = {}

def build_dynamic_graph(agent_ids: List[str]):
    builder = StateGraph(State)
    prev_node = None
    for aid in agent_ids:
        if aid.startswith("tool:"):
            _, agent_id, tool_name = aid.split(":")
            node_name = f"tool_{sanitize_node_id(agent_id)}_{sanitize_node_id(tool_name)}"
            TOOL_CONFIGS[node_name] = ToolConfig(name=tool_name, option="tutorials")
            def make_tool_fn(node_key):
                def fn(state):
                    return execute_tool(state, TOOL_CONFIGS[node_key])
                return fn
            builder.add_node(node_name, make_tool_fn(node_name))
            current_node = node_name
        elif aid.startswith("tool_"):
            if aid not in TOOL_CONFIGS:
                raise ValueError(f"Missing config for tool node: {aid}")
            def make_tool_fn(node_key):
                return lambda state: execute_tool(state, TOOL_CONFIGS[node_key])
            builder.add_node(aid, make_tool_fn(aid))
            current_node = aid
        elif aid in AGENTS_REGISTRY:
            builder.add_node(aid, AGENTS_REGISTRY[aid])
            current_node = aid
        else:
            raise ValueError(f"Unknown agent ID {aid}")
        if prev_node:
            builder.add_edge(prev_node, current_node)
        prev_node = current_node
    builder.set_entry_point(agent_ids[0])
    builder.set_finish_point(agent_ids[-1])
    return builder.compile()

ToolType = Union[str, ToolConfig]

class AgentConfig(BaseModel):
    id: str
    enabled: bool
    tools: Optional[List[ToolType]] = []

class ChatSettings(BaseModel):
    agent_sequence: List[AgentConfig]
    supervisor_mode: bool = False  # Enable supervisor-based routing
    supervisor_type: str = "basic"  # "basic" or "advanced"

class MessageRequest(BaseModel):
    user_prompt: str

def build_execution_plan(enabled_agents: List[Dict[str, Any]], user_prompt: str = "") -> List[str]:
    execution_plan = []
    
    # Function to determine intelligent tools (same logic as elsewhere)
    def determine_needed_tools(user_prompt: str, agent_name: str) -> list:
        """Determine which tools an agent should use based on the request content"""
        from .tools.tool_config import ToolConfig
        tools = []
        
        prompt_lower = user_prompt.lower()
        
        # Web search tool - for current information, news, weather, etc.
        web_search_triggers = [
            "today", "current", "now", "latest", "recent", "news", 
            "weather", "temperature", "forecast", "happening",
            "what's", "what is", "price", "stock", "update"
        ]
        if any(trigger in prompt_lower for trigger in web_search_triggers):
            tools.append(ToolConfig(name="web_search"))
        
        # Knowledgebase tool - for recipes, traditional knowledge, etc.
        kb_triggers = [
            "recipe", "cooking", "traditional", "romanian", "ciorba",
            "soup", "food", "ingredient", "how to make", "prepare"
        ]
        if any(trigger in prompt_lower for trigger in kb_triggers):
            # Try to find a relevant knowledgebase option
            kb_option = None
            if "ciorba" in prompt_lower or "soup" in prompt_lower:
                kb_option = "ciorba_recipe"
            tools.append(ToolConfig(name="knowledgebase", option=kb_option))
        
        return tools
    
    for agent in enabled_agents:
        agent_id = agent["id"]
        
        # Get manually configured tools
        manual_tools = agent.get("tools") or []
        
        # Get intelligently determined tools
        intelligent_tools = determine_needed_tools(user_prompt, agent_id) if user_prompt else []
        
        # Combine tools (intelligent takes priority)
        all_tools = intelligent_tools[:]
        for manual_tool in manual_tools:
            # Convert manual tool to ToolConfig for comparison
            if isinstance(manual_tool, dict):
                manual_name = manual_tool.get("name", "")
            elif hasattr(manual_tool, 'name'):
                manual_name = getattr(manual_tool, "name", "")
            else:
                manual_name = str(manual_tool)
            
            # Only add if not already in intelligent tools
            if not any(t.name == manual_name for t in intelligent_tools):
                if isinstance(manual_tool, dict):
                    all_tools.append(ToolConfig(name=manual_tool.get("name", ""), option=manual_tool.get("option")))
                elif hasattr(manual_tool, 'name'):
                    all_tools.append(ToolConfig(name=getattr(manual_tool, "name", ""), option=getattr(manual_tool, "option", None)))
                else:
                    all_tools.append(ToolConfig(name=str(manual_tool)))
        
        # Add tool nodes before the agent node
        for tool_config in all_tools:
            tool_name = tool_config.name
            tool_option = tool_config.option
            if not isinstance(tool_name, str) or not tool_name:
                raise ValueError(f"Invalid tool name: {tool_name}")
            tool_node = f"tool_{sanitize_node_id(agent_id)}_{sanitize_node_id(tool_name)}"
            TOOL_CONFIGS[tool_node] = ToolConfig(name=tool_name, option=tool_option)
            execution_plan.append(tool_node)
        
        # Add the agent node after its tools
        execution_plan.append(agent_id)
    
    return execution_plan

# Supervisor-based helper functions
def build_supervisor_graph(supervisor_type: str = "basic", chat_config: Optional[dict] = None):
    """Build supervisor graph for intelligent agent routing with tool support"""
    if not SUPERVISOR_AVAILABLE:
        raise ValueError("Supervisor functionality not available")
    
    # Create supervisor agent
    supervisor_agent = create_advanced_supervisor_agent() if supervisor_type == "advanced" else create_supervisor_agent()
    
    # Extract tool configuration for each agent from chat config
    agent_tools_config = {}
    if chat_config is None:
        chat_config = {}
    
    if chat_config.get("agent_sequence"):
        for agent_config in chat_config["agent_sequence"]:
            if agent_config.get("enabled") and agent_config.get("tools"):
                from .tools.tool_config import ToolConfig
                agent_tools = [
                    ToolConfig(name=tool["name"], option=tool.get("option"))
                    if isinstance(tool, dict) else ToolConfig(name=tool)
                    for tool in agent_config["tools"]
                ]
                agent_tools_config[agent_config["id"]] = agent_tools
    
    # Agent wrapper functions with tool support
    def granny_node(state: MessagesState) -> Command:
        last_message = state["messages"][-1] if state["messages"] else None
        user_prompt = str(last_message.content) if last_message and hasattr(last_message, 'content') else ""
        
        # Create agent state with tool configuration
        agent_config = [{
            "id": "granny",
            "enabled": True,
            "tools": agent_tools_config.get("granny", [])
        }]
        
        agent_state = State(
            user_prompt=user_prompt,
            history=[],
            tool_outputs={},
            agent_flow=agent_config
        )
        
        # Execute tools if available
        granny_tools = agent_tools_config.get("granny", [])
        if granny_tools:
            from .tools.tool_executor import execute_intelligent_tools
            agent_state = execute_intelligent_tools(agent_state, granny_tools, "granny")
        
        result = create_granny_response(agent_state)
        return Command(
            goto="supervisor",
            update={"messages": state["messages"] + [
                AIMessage(content=result["granny_output"], name="granny")
            ]}
        )
    
    def story_creator_node(state: MessagesState) -> Command:
        last_message = state["messages"][-1] if state["messages"] else None
        user_prompt = str(last_message.content) if last_message and hasattr(last_message, 'content') else ""
        
        # Create agent state with tool configuration
        agent_config = [{
            "id": "story_creator",
            "enabled": True,
            "tools": agent_tools_config.get("story_creator", [])
        }]
        
        agent_state = State(
            user_prompt=user_prompt,
            history=[],
            tool_outputs={},
            agent_flow=agent_config
        )
        
        # Execute tools if available
        story_tools = agent_tools_config.get("story_creator", [])
        if story_tools:
            from .tools.tool_executor import execute_intelligent_tools
            agent_state = execute_intelligent_tools(agent_state, story_tools, "story_creator")
        
        result = create_story(agent_state)
        return Command(
            goto="supervisor", 
            update={"messages": state["messages"] + [
                AIMessage(content=result["story_output"], name="story_creator")
            ]}
        )
    
    def parody_creator_node(state: MessagesState) -> Command:
        last_message = state["messages"][-1] if state["messages"] else None
        user_prompt = str(last_message.content) if last_message and hasattr(last_message, 'content') else ""
        
        # Create agent state with tool configuration
        agent_config = [{
            "id": "parody_creator",
            "enabled": True,
            "tools": agent_tools_config.get("parody_creator", [])
        }]
        
        agent_state = State(
            user_prompt=user_prompt,
            history=[],
            tool_outputs={},
            agent_flow=agent_config
        )
        
        # Execute tools if available
        parody_tools = agent_tools_config.get("parody_creator", [])
        if parody_tools:
            from .tools.tool_executor import execute_intelligent_tools
            agent_state = execute_intelligent_tools(agent_state, parody_tools, "parody_creator")
        
        result = create_parody(agent_state)
        return Command(
            goto="supervisor",
            update={"messages": state["messages"] + [
                AIMessage(content=result["parody_output"], name="parody_creator")
            ]}
        )
    
    # Build the graph
    builder = StateGraph(MessagesState)
    builder.add_node("supervisor", supervisor_agent)
    builder.add_node("granny", granny_node)
    builder.add_node("story_creator", story_creator_node) 
    builder.add_node("parody_creator", parody_creator_node)
    
    builder.add_edge(START, "supervisor")
    builder.add_edge("granny", "supervisor")
    builder.add_edge("story_creator", "supervisor")
    builder.add_edge("parody_creator", "supervisor")
    
    return builder.compile()

def process_supervisor_message(chat_id: str, user_prompt: str, supervisor_type: str = "basic"):
    """Process a message using supervisor pattern with detailed tracking"""
    chat = chats[chat_id]
    
    # Check if enhanced supervisor is requested
    if supervisor_type == "enhanced":
        return process_enhanced_supervisor_message(chat_id, user_prompt)
    
    # First, run supervisor to determine which agent to use
    supervisor_graph = build_supervisor_graph(supervisor_type, {})  # Empty config for initial routing
    
    # Prepare messages from chat history
    messages = []
    for msg in chat.get("history", []):
        if msg["sender"] == "user":
            messages.append(HumanMessage(content=msg["text"]))
        elif msg["sender"] in ["granny", "story_creator", "parody_creator", "supervisor"]:
            messages.append(AIMessage(content=msg["text"], name=msg["sender"]))
    
    # Add current user message
    messages.append(HumanMessage(content=user_prompt))
    
    # Run supervisor to get routing decision
    supervisor_result = supervisor_graph.invoke({"messages": messages})
    
    # Extract supervisor decision and chosen agent
    supervisor_decision = None
    chosen_agent = "unknown"
    
    for msg in supervisor_result["messages"]:
        if hasattr(msg, 'name'):
            if msg.name == "supervisor":
                supervisor_decision = msg.content
                # Try to extract agent choice from supervisor decision
                if "granny" in msg.content.lower():
                    chosen_agent = "granny"
                elif "story" in msg.content.lower():
                    chosen_agent = "story_creator" 
                elif "parody" in msg.content.lower():
                    chosen_agent = "parody_creator"
    
    # Now execute tools and agent for the chosen agent
    tool_outputs = {}
    agent_response = "No response generated"
    
    if chosen_agent != "unknown":
        # Intelligent tool selection for supervisor mode
        def determine_needed_tools(user_prompt: str, agent_name: str) -> list:
            """Determine which tools an agent should use based on the request content"""
            from .tools.tool_config import ToolConfig
            tools = []
            
            prompt_lower = user_prompt.lower()
            
            # Web search tool - for current information, news, weather, etc.
            web_search_triggers = [
                "today", "current", "now", "latest", "recent", "news", 
                "weather", "temperature", "forecast", "happening",
                "what's", "what is", "price", "stock", "update"
            ]
            if any(trigger in prompt_lower for trigger in web_search_triggers):
                tools.append(ToolConfig(name="web_search"))
            
            # Knowledgebase tool - for recipes, traditional knowledge, etc.
            kb_triggers = [
                "recipe", "cooking", "traditional", "romanian", "ciorba",
                "soup", "food", "ingredient", "how to make", "prepare"
            ]
            if any(trigger in prompt_lower for trigger in kb_triggers):
                # Try to find a relevant knowledgebase option
                kb_option = None
                if "ciorba" in prompt_lower or "soup" in prompt_lower:
                    kb_option = "ciorba_recipe"
                tools.append(ToolConfig(name="knowledgebase", option=kb_option))
            
            return tools
        
        # Get intelligently determined tools for this request
        intelligent_tools = determine_needed_tools(user_prompt, chosen_agent)
        
        # Also check if user has manually configured tools for this agent
        manual_tools = []
        for config in chat.get("agent_sequence", []):
            if config["id"] == chosen_agent and config.get("enabled") and config.get("tools"):
                manual_tools = [
                    ToolConfig(name=tool["name"], option=tool.get("option"))
                    if isinstance(tool, dict) else ToolConfig(name=tool)
                    for tool in config["tools"]
                ]
                break
        
        # Combine intelligent and manual tools (intelligent takes priority)
        all_tools = intelligent_tools + [t for t in manual_tools if t.name not in [it.name for it in intelligent_tools]]
        
        # Execute tools if any are needed
        if all_tools:
            from .tools.tool_executor import execute_intelligent_tools
            
            # Create a minimal agent config for tool execution
            agent_config = {
                "id": chosen_agent,
                "enabled": True,
                "tools": [{"name": tool.name, "option": tool.option} for tool in all_tools]
            }
            
            # Create state for tool execution
            tool_state = State(
                user_prompt=user_prompt,
                history=[],
                tool_outputs={},
                agent_flow=[agent_config]
            )
            
            # Execute tools
            tool_state = execute_intelligent_tools(tool_state, all_tools, chosen_agent)
            tool_outputs = tool_state.tool_outputs
        else:
            # No tools needed, create minimal config
            agent_config = {"id": chosen_agent, "enabled": True, "tools": []}
        
        # Now execute the chosen agent with tool outputs
        agent_state = State(
            user_prompt=user_prompt,
            history=[],
            tool_outputs=tool_outputs,
            agent_flow=[agent_config] if agent_config else None
        )
        
        # Call the appropriate agent function
        if chosen_agent == "granny":
            from .granny.agent import create_granny_response
            result = create_granny_response(agent_state)
            agent_response = result.get("granny_output", "No response")
        elif chosen_agent == "story_creator":
            from .story_creator.agent import create_story
            result = create_story(agent_state)
            agent_response = result.get("story_output", "No response")
        elif chosen_agent == "parody_creator":
            from .parody_creator.agent import create_parody
            result = create_parody(agent_state)
            agent_response = result.get("parody_output", "No response")
    
    return {
        "supervisor_decision": supervisor_decision,
        "chosen_agent": chosen_agent,
        "agent_response": agent_response,
        "tool_outputs": tool_outputs,
        "supervisor_type": supervisor_type
    }

def process_enhanced_supervisor_message(chat_id: str, user_prompt: str):
    """Process message using enhanced supervisor with query decomposition and orchestration"""
    try:
        from .supervisor.enhanced_supervisor import EnhancedSupervisor
        
        # Load knowledgebase metadata
        kb_path = Path(__file__).parent.parent / "data" / "knowledgebase.json"
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                kb_data = json.load(f)
                # Convert to metadata format that matches real structure
                kb_metadata = {}
                for kb_key, kb_info in kb_data.items():
                    if isinstance(kb_info, dict):
                        kb_metadata[kb_key] = type('KBFile', (), {
                            'description': kb_info.get('description', ''),
                            'keywords': kb_info.get('keywords', []),
                            'label': kb_info.get('label', ''),
                            'content_type': kb_info.get('content_type', '')
                        })()
        except Exception as e:
            print(f"Knowledge base loading error: {e}")
            kb_metadata = {}
        
        # Create enhanced supervisor
        enhanced_supervisor = EnhancedSupervisor(
            available_agents=["granny", "story_creator", "parody_creator"],
            knowledgebase_metadata=kb_metadata
        )
        
        # Analyze the query
        execution_plan = enhanced_supervisor.analyze_query(user_prompt)
        
        # Build detailed explanation of the plan
        plan_explanation = f"""Enhanced Analysis Results:
Strategy: {execution_plan.strategy}
Primary Agent: {execution_plan.primary_agent}
Components Detected: {len(execution_plan.components)}"""
        
        for i, component in enumerate(execution_plan.components, 1):
            plan_explanation += f"\n  {i}. {component.intent} -> {component.resource_type.value}: {component.resource_id}"
        
        if execution_plan.tools_needed:
            plan_explanation += f"\nTools Required: {', '.join(execution_plan.tools_needed)}"
        if execution_plan.knowledge_needed:
            plan_explanation += f"\nKnowledge Required: {', '.join(execution_plan.knowledge_needed)}"
        
        plan_explanation += f"\nContext Fusion: {execution_plan.context_fusion}"
        
        # Execute the plan (simplified for now)
        tool_outputs = {}
        
        # Execute tools
        if "web_search" in execution_plan.tools_needed:
            from .tools.tool_config import _generate_web_search_query
            from .tools.web_search import run_tool
            
            search_query = _generate_web_search_query(user_prompt)
            search_result = run_tool(search_query)
            tool_outputs["web_search"] = {
                "query": search_query,
                "result": search_result
            }
        
        # Execute the primary agent with enhanced context
        enhanced_context = f"""Original request: {user_prompt}

Enhanced Analysis:
{plan_explanation}

Tool Results:
{json.dumps(tool_outputs, indent=2) if tool_outputs else "No tools executed"}

Instructions: Respond as {execution_plan.primary_agent} using the {execution_plan.context_fusion} approach."""
        
        # Create agent state with enhanced context
        agent_state = State(
            user_prompt=enhanced_context,
            history=[],
            tool_outputs=tool_outputs,
            agent_flow=[{"id": execution_plan.primary_agent, "enabled": True, "tools": []}]
        )
        
        # Execute the chosen agent
        agent_response = "No response generated"
        if execution_plan.primary_agent == "granny":
            from .granny.agent import create_granny_response
            result = create_granny_response(agent_state)
            agent_response = result.get("granny_output", "No response")
        elif execution_plan.primary_agent == "story_creator":
            from .story_creator.agent import create_story
            result = create_story(agent_state)
            agent_response = result.get("story_output", "No response")
        elif execution_plan.primary_agent == "parody_creator":
            from .parody_creator.agent import create_parody
            result = create_parody(agent_state)
            agent_response = result.get("parody_output", "No response")
        
        return {
            "supervisor_decision": plan_explanation,
            "chosen_agent": execution_plan.primary_agent,
            "agent_response": agent_response,
            "tool_outputs": tool_outputs,
            "supervisor_type": "enhanced",
            "execution_plan": {
                "strategy": execution_plan.strategy,
                "components": len(execution_plan.components),
                "context_fusion": execution_plan.context_fusion
            }
        }
        
    except Exception as e:
        print(f"Enhanced supervisor failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to basic supervisor
        return process_supervisor_message(chat_id, user_prompt, "basic")

@app.get("/knowledgebase")
def get_knowledgebase():
    kb_path = Path(__file__).parent.parent / "data" / "knowledgebase.json"
    with open(kb_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/chats")
def list_chats():
    # Only return chats that have content (messages or enabled agents)
    meaningful_chats = []
    for chat_data in chats.values():
        has_messages = len(chat_data.get("history", [])) > 0
        has_enabled_agents = any(
            agent.get("enabled", False) 
            for agent in chat_data.get("agent_sequence", [])
        )
        
        if has_messages or has_enabled_agents:
            meaningful_chats.append({
                "id": chat_data["id"], 
                "agent_sequence": chat_data["agent_sequence"]
            })
    
    return meaningful_chats

@app.post("/chats")
def create_chat():
    chat_id = str(uuid.uuid4())
    # Don't save to disk immediately - only save when there's actual content
    chats[chat_id] = {
        "id": chat_id, 
        "agent_sequence": [], 
        "history": [],
        "supervisor_mode": False,
        "supervisor_type": "basic"
    }
    return chats[chat_id]

@app.get("/chats/{chat_id}")
def get_chat(chat_id: str):
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")
    return chats[chat_id]

@app.post("/chats/{chat_id}/settings")
def update_settings(chat_id: str, settings: ChatSettings):
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")
    chats[chat_id]["agent_sequence"] = [a.dict() for a in settings.agent_sequence]
    chats[chat_id]["supervisor_mode"] = settings.supervisor_mode
    chats[chat_id]["supervisor_type"] = settings.supervisor_type
    
    # Only save if chat has content (settings or messages)
    has_content = (
        chats[chat_id]["history"] or 
        any(a["enabled"] for a in chats[chat_id]["agent_sequence"]) or
        settings.supervisor_mode
    )
    if has_content:
        save_chats()
    return {"ok": True}

@app.post("/chats/{chat_id}/message/stream")
async def stream_message(chat_id: str, req: MessageRequest):
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")
    
    chat = chats[chat_id]
    
    async def stream_generator():
        import json
        from .granny.agent import create_granny_response_stream
        from .story_creator.agent import create_story_response_stream
        from .parody_creator.agent import create_parody_response_stream
        
        hist = chat["history"]
        hist.append({"sender": "user", "text": req.user_prompt})
        
        # Check if supervisor mode is enabled
        if chat.get("supervisor_mode", False) and SUPERVISOR_AVAILABLE:
            try:
                # Process with supervisor
                result = process_supervisor_message(
                    chat_id, 
                    req.user_prompt, 
                    chat.get("supervisor_type", "basic")
                )
                
                # Stream supervisor decision if available
                if result["supervisor_decision"]:
                    supervisor_msg = {
                        "sender": "supervisor",
                        "text": result["supervisor_decision"],
                        "routing_decision": True,
                        "chosen_agent": result["chosen_agent"],
                        "supervisor_type": result["supervisor_type"]
                    }
                    hist.append(supervisor_msg)
                    yield json.dumps(supervisor_msg) + "\n"
                
                # Stream tool outputs if any were used
                if result.get("tool_outputs"):
                    for tool_name, tool_result in result["tool_outputs"].items():
                        # Extract text from result (could be string or dict)
                        if isinstance(tool_result, dict):
                            text_result = tool_result.get("result", str(tool_result))
                        else:
                            text_result = tool_result
                        
                        tool_msg = {
                            "sender": "tool", 
                            "text": text_result, 
                            "tool_id": tool_name, 
                            "for_agent": result["chosen_agent"],
                            "via_supervisor": True
                        }
                        hist.append(tool_msg)
                        yield json.dumps(tool_msg) + "\n"
                
                # Stream the chosen agent's response
                agent_msg = {
                    "sender": result["chosen_agent"],
                    "text": result["agent_response"],
                    "via_supervisor": True,
                    "supervisor_type": result["supervisor_type"]
                }
                hist.append(agent_msg)
                yield json.dumps(agent_msg) + "\n"
                
                save_chats()
                return
                
            except Exception as e:
                print(f"Supervisor streaming failed: {e}")
                import traceback
                traceback.print_exc()
                # Return error message instead of falling back
                error_msg = {
                    "sender": "system",
                    "text": f"Supervisor mode failed: {str(e)}. Please try again or disable supervisor mode.",
                    "error": True
                }
                hist.append(error_msg)
                yield json.dumps(error_msg) + "\n"
                save_chats()
                return
        
        # Sequential mode (original logic)
        cfg = chat["agent_sequence"]
        enabled = [a for a in cfg if a["enabled"]]
        if not enabled:
            raise HTTPException(400, "No agents enabled")
        
        execution_plan = build_execution_plan(enabled, req.user_prompt)
        previous = chat["history"]
        state = State(
            user_prompt=req.user_prompt, 
            history=[ChatMessage(**m) for m in previous],
            agent_flow=enabled
        )
        
        # Execute tools first for all enabled agents
        from .tools.tool_executor import execute_intelligent_tools
        from .tools.tool_config import ToolConfig
        
        # Initialize state with current state
        current_state = state
        
        # Function to determine intelligent tools (reuse the same logic as supervisor mode)
        def determine_needed_tools(user_prompt: str, agent_name: str) -> list:
            """Determine which tools an agent should use based on the request content"""
            tools = []
            
            prompt_lower = user_prompt.lower()
            
            # Web search tool - for current information, news, weather, etc.
            web_search_triggers = [
                "today", "current", "now", "latest", "recent", "news", 
                "weather", "temperature", "forecast", "happening",
                "what's", "what is", "price", "stock", "update"
            ]
            if any(trigger in prompt_lower for trigger in web_search_triggers):
                tools.append(ToolConfig(name="web_search"))
            
            # Knowledgebase tool - for recipes, traditional knowledge, etc.
            kb_triggers = [
                "recipe", "cooking", "traditional", "romanian", "ciorba",
                "soup", "food", "ingredient", "how to make", "prepare"
            ]
            if any(trigger in prompt_lower for trigger in kb_triggers):
                # Try to find a relevant knowledgebase option
                kb_option = None
                if "ciorba" in prompt_lower or "soup" in prompt_lower:
                    kb_option = "ciorba_recipe"
                tools.append(ToolConfig(name="knowledgebase", option=kb_option))
            
            return tools
        
        # Collect all tools from enabled agents (manual + intelligent)
        for agent_config in enabled:
            # Get manually configured tools
            manual_tools = []
            if "tools" in agent_config:
                manual_tools = [
                    ToolConfig(name=tool["name"], option=tool.get("option"))
                    if isinstance(tool, dict) else ToolConfig(name=tool)
                    for tool in agent_config["tools"]
                ]
            
            # Get intelligently determined tools
            intelligent_tools = determine_needed_tools(req.user_prompt, agent_config["id"])
            
            # Combine (intelligent takes priority)
            all_tools = intelligent_tools + [t for t in manual_tools if t.name not in [it.name for it in intelligent_tools]]
            
            if all_tools:
                current_state = execute_intelligent_tools(current_state, all_tools, agent_config["id"])
        
        # Stream tool outputs first
        if current_state.tool_outputs:
            for tool_name, result in current_state.tool_outputs.items():
                # Find which agent this tool belongs to
                matched_agent = None
                for agent in enabled:
                    for t in agent.get("tools") or []:
                        name = t.name if isinstance(t, ToolConfig) else (t.get("name") if isinstance(t, dict) else t)
                        if name == tool_name:
                            matched_agent = agent["id"]
                            break
                    if matched_agent:
                        break
                
                # Extract text from result (could be string or dict)
                if isinstance(result, dict):
                    text_result = result.get("result", str(result))
                else:
                    text_result = result
                
                tool_msg = {
                    "sender": "tool", 
                    "text": text_result, 
                    "tool_id": tool_name, 
                    "for_agent": matched_agent or "unknown"
                }
                hist.append(tool_msg)
                yield json.dumps(tool_msg) + "\n"
        
        # Now stream each enabled agent's response
        for agent_config in enabled:
            agent_id = agent_config["id"]
            
            # Signal start of agent response
            start_msg = {
                "sender": agent_id,
                "text": "",
                "stream_start": True
            }
            yield json.dumps(start_msg) + "\n"
            
            # Stream the agent's response
            full_response = ""
            if agent_id == "granny":
                for chunk in create_granny_response_stream(current_state):
                    full_response += chunk
                    chunk_msg = {
                        "sender": agent_id,
                        "text": chunk,
                        "stream_chunk": True
                    }
                    yield json.dumps(chunk_msg) + "\n"
            elif agent_id == "story_creator":
                for chunk in create_story_response_stream(current_state):
                    full_response += chunk
                    chunk_msg = {
                        "sender": agent_id,
                        "text": chunk,
                        "stream_chunk": True
                    }
                    yield json.dumps(chunk_msg) + "\n"
            elif agent_id == "parody_creator":
                for chunk in create_parody_response_stream(current_state):
                    full_response += chunk
                    chunk_msg = {
                        "sender": agent_id,
                        "text": chunk,
                        "stream_chunk": True
                    }
                    yield json.dumps(chunk_msg) + "\n"
            
            # Signal end of agent response and save full response
            end_msg = {
                "sender": agent_id,
                "text": full_response,
                "stream_end": True
            }
            hist.append({"sender": agent_id, "text": full_response})
            yield json.dumps(end_msg) + "\n"
        
        save_chats()
    
    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@app.post("/chats/{chat_id}/message")
def send_message(chat_id: str, req: MessageRequest):
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")
    
    chat = chats[chat_id]
    
    # Check if supervisor mode is enabled
    if chat.get("supervisor_mode", False) and SUPERVISOR_AVAILABLE:
        try:
            # Use supervisor routing
            result = process_supervisor_message(
                chat_id, 
                req.user_prompt, 
                chat.get("supervisor_type", "basic")
            )
            
            # Update chat history with detailed supervisor tracking
            hist = chat["history"]
            hist.append({"sender": "user", "text": req.user_prompt})
            
            # Add supervisor decision if available
            if result["supervisor_decision"]:
                hist.append({
                    "sender": "supervisor",
                    "text": result["supervisor_decision"],
                    "routing_decision": True,
                    "chosen_agent": result["chosen_agent"],
                    "supervisor_type": result["supervisor_type"]
                })
            
            # Add tool outputs if any were used
            if result.get("tool_outputs"):
                for tool_name, tool_result in result["tool_outputs"].items():
                    # Extract text from result (could be string or dict)
                    if isinstance(tool_result, dict):
                        text_result = tool_result.get("result", str(tool_result))
                    else:
                        text_result = tool_result
                    
                    tool_msg = {
                        "sender": "tool", 
                        "text": text_result, 
                        "tool_id": tool_name, 
                        "for_agent": result["chosen_agent"],
                        "via_supervisor": True
                    }
                    hist.append(tool_msg)
            
            # Add the chosen agent's response
            hist.append({
                "sender": result["chosen_agent"],
                "text": result["agent_response"],
                "via_supervisor": True,
                "supervisor_type": result["supervisor_type"]
            })
            
            save_chats()
            
            return {
                "agent_response": result["agent_response"],
                "chosen_agent": result["chosen_agent"],
                "supervisor_decision": result["supervisor_decision"],
                "tool_outputs": result.get("tool_outputs", {}),
                "supervisor_routing": True,
                "supervisor_type": result["supervisor_type"]
            }
            
        except Exception as e:
            print(f"Supervisor routing failed: {e}")
            import traceback
            traceback.print_exc()
            # Return error response instead of falling back
            hist = chat["history"]
            hist.append({"sender": "user", "text": req.user_prompt})
            hist.append({
                "sender": "system",
                "text": f"Supervisor mode failed: {str(e)}. Please try again or disable supervisor mode.",
                "error": True
            })
            save_chats()
            
            return {
                "system_error": f"Supervisor mode failed: {str(e)}",
                "supervisor_routing": False,
                "error": True
            }
    
    # Use original sequential mode
    cfg = chat["agent_sequence"]
    enabled = [a for a in cfg if a["enabled"]]
    if not enabled:
        raise HTTPException(400, "No agents enabled")
    
    execution_plan = build_execution_plan(enabled, req.user_prompt)
    previous = chat["history"]
    state = State(
        user_prompt=req.user_prompt, 
        history=[ChatMessage(**m) for m in previous],
        agent_flow=enabled
    )
    flow = build_dynamic_graph(execution_plan)
    
    # Execute the flow
    out = State(**flow.invoke(state))
    
    # Build response history
    hist = chat["history"]
    hist.append({"sender": "user", "text": req.user_prompt})
    
    # Add tool outputs to history
    if out.tool_outputs:
        for tool_name, result in out.tool_outputs.items():
            # Find which agent this tool belongs to
            matched_agent = None
            for agent in enabled:
                for t in agent.get("tools") or []:
                    name = t.name if isinstance(t, ToolConfig) else (t.get("name") if isinstance(t, dict) else t)
                    if name == tool_name:
                        matched_agent = agent["id"]
                        break
                if matched_agent:
                    break
            # Extract text from result (could be string or dict)
            if isinstance(result, dict):
                text_result = result.get("result", str(result))
            else:
                text_result = result
                
            hist.append({
                "sender": "tool", 
                "text": text_result, 
                "tool_id": tool_name, 
                "for_agent": matched_agent or "unknown"
            })
    
    # Add agent outputs to history
    if out.granny_output:
        hist.append({"sender": "granny", "text": out.granny_output})
    if out.story_output:
        hist.append({"sender": "story_creator", "text": out.story_output})
    if out.parody_output:
        hist.append({"sender": "parody_creator", "text": out.parody_output})
    
    save_chats()
    return out.dict(exclude_none=True)

@app.post("/chats/{chat_id}/supervisor")
def toggle_supervisor_mode(chat_id: str, enabled: bool = True, supervisor_type: str = "basic"):
    """Convenience endpoint to enable/disable supervisor mode for a chat"""
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")
    
    if not SUPERVISOR_AVAILABLE and enabled:
        raise HTTPException(400, "Supervisor functionality not available")
    
    chats[chat_id]["supervisor_mode"] = enabled
    chats[chat_id]["supervisor_type"] = supervisor_type
    save_chats()
    
    return {
        "supervisor_mode": enabled,
        "supervisor_type": supervisor_type,
        "message": f"Supervisor mode {'enabled' if enabled else 'disabled'} for chat {chat_id}"
    }

@app.get("/chats/{chat_id}/supervisor")
def get_supervisor_status(chat_id: str):
    """Get supervisor mode status for a chat"""
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")
    
    chat = chats[chat_id]
    return {
        "supervisor_mode": chat.get("supervisor_mode", False),
        "supervisor_type": chat.get("supervisor_type", "basic"),
        "supervisor_available": SUPERVISOR_AVAILABLE
    }

@app.post("/chats/cleanup")
def cleanup_empty_chats():
    """Manually clean up empty conversations"""
    initial_count = len(chats)
    
    # Filter out empty chats
    meaningful_chats = {}
    for chat_id, chat_data in chats.items():
        has_messages = len(chat_data.get("history", [])) > 0
        has_enabled_agents = any(
            agent.get("enabled", False) 
            for agent in chat_data.get("agent_sequence", [])
        )
        
        if has_messages or has_enabled_agents:
            meaningful_chats[chat_id] = chat_data
    
    # Update in-memory chats
    chats.clear()
    chats.update(meaningful_chats)
    
    # Save to disk
    save_chats()
    
    cleaned_count = initial_count - len(chats)
    return {
        "message": f"Cleaned up {cleaned_count} empty conversations", 
        "removed": cleaned_count,
        "remaining": len(chats)
    }