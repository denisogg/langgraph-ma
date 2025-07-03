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

# Legacy imports removed - now using enhanced_agent_registry
# from .story_creator.agent import create_story, create_story_response_stream
# from .parody_creator.agent import create_parody, create_parody_response_stream  
# from .granny.agent import create_granny_response, create_granny_response_stream
from .state import ChatMessage, State
from .tools.tool_executor import execute_tool
from .tools.tool_config import ToolConfig

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, AIMessage
import threading

# Import enhanced agent registry and supervisor functionality
from .enhanced_registry import enhanced_agent_registry
from .supervisor.enhanced_supervisor import create_enhanced_supervisor

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

# Enhanced agent function wrapper with support for both file-based and JSON agents
def get_agent_function(agent_id: str):
    """Get agent function from enhanced registry for use in LangGraph nodes"""
    try:
        agent = enhanced_agent_registry.get_agent(agent_id)
        agent_type = enhanced_agent_registry.get_agent_type(agent_id)
        
        def agent_node_wrapper(state: State) -> dict:
            """Wrapper function that adapts new agent interface to old format"""
            result = agent.process_request(state)
            
            # Return old format for backward compatibility
            agent_output_key = f"{agent_id}_output"
            return {
                agent_output_key: result["output"],
                "previous_agent_output": result["output"],
                "current_agent_id": agent_id,
                # Add new metadata for enhanced functionality
                "agent_type": agent_type,
                "agent_metadata": result
            }
        
        return agent_node_wrapper
    except Exception as e:
        print(f"⚠️ Failed to get agent {agent_id} from enhanced registry: {e}")
        raise ValueError(f"Unknown agent ID: {agent_id}. Available agents: {enhanced_agent_registry.list_available_agents()}")

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
        elif aid in enhanced_agent_registry.list_available_agents():
            agent_function = get_agent_function(aid)
            builder.add_node(aid, agent_function)
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
def build_supervisor_graph(chat_config: Optional[dict] = None):
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
        
        # Use enhanced registry instead of hardcoded function
        granny_agent = enhanced_agent_registry.get_agent("granny")
        result = granny_agent.process_request(agent_state)
        return Command(
            goto="supervisor",
            update={"messages": state["messages"] + [
                AIMessage(content=result["output"], name="granny")
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
        
        # Use enhanced registry instead of hardcoded function
        story_agent = enhanced_agent_registry.get_agent("story_creator")
        result = story_agent.process_request(agent_state)
        return Command(
            goto="supervisor", 
            update={"messages": state["messages"] + [
                AIMessage(content=result["output"], name="story_creator")
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
        
        # Use enhanced registry instead of hardcoded function
        parody_agent = enhanced_agent_registry.get_agent("parody_creator")
        result = parody_agent.process_request(agent_state)
        return Command(
            goto="supervisor",
            update={"messages": state["messages"] + [
                AIMessage(content=result["output"], name="parody_creator")
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



def process_multi_agent_supervisor_message(chat_id: str, user_prompt: str):
    """Process message using enhanced supervisor with multi-agent support"""
    
    print(f"\n{'='*80}")
    print(f"🎮 CONTROL FLOW: WORKFLOW START - User request received")
    print(f"🎮 CONTROL FLOW: Chat ID: {chat_id}")
    print(f"🎮 CONTROL FLOW: User prompt: {user_prompt[:100]}...")
    print(f"{'='*80}")
    
    # Get chat history and state
    chat_history = chats.get(chat_id, {}).get("history", [])
    hist = chats.get(chat_id, {}).get("history", [])
    
    print(f"🎮 CONTROL FLOW: Supervisor taking initial control for planning")
    
    try:
        # Enhanced supervisor analysis
        print(f"🔍 DEBUG: process_multi_agent_supervisor_message called")
        
        # Create enhanced supervisor
        available_agents = enhanced_agent_registry.list_available_agents()
        enhanced_supervisor = create_enhanced_supervisor(available_agents, {})
        
        print(f"🎮 CONTROL FLOW: Supervisor analyzing request and building execution plan")
        # Analyze query and create execution plan
        execution_plan = enhanced_supervisor.analyze_query(user_prompt)
        
        print(f"🔍 DEBUG: Execution plan requires_multi_agent: {execution_plan.requires_multi_agent}")
        print(f"🔍 DEBUG: Agent sequence: {execution_plan.agent_sequence}")
        
        if execution_plan.requires_multi_agent:
            print(f"🎮 CONTROL FLOW: Supervisor determined multi-agent execution required")
            print(f"🎮 CONTROL FLOW: Planned agent sequence: {execution_plan.agent_sequence}")
            
            # Add initial supervisor message to history
            supervisor_msg = {
                "sender": "supervisor",
                "text": f"Enhanced Analysis Results:\nStrategy: {execution_plan.strategy}\nPrimary Agent: {execution_plan.primary_agent}\nComponents Detected: {len(execution_plan.components)}\n" + 
                       "\n".join([f"  {i+1}. {comp.intent} -> {comp.resource_type.value}: {comp.resource_id}" for i, comp in enumerate(execution_plan.components)]) +
                       f"\nTools Required: {', '.join(execution_plan.tools_needed) if execution_plan.tools_needed else 'None'}\n" +
                       f"Context Fusion: {execution_plan.context_fusion}",
                "routing_decision": True,
                "chosen_agent": execution_plan.primary_agent,
                "supervisor_type": "enhanced"
            }
            hist.append(supervisor_msg)
            
            print(f"🎮 CONTROL FLOW: Supervisor added planning message to history")
            print(f"🔍 DEBUG: Calling execute_multi_agent_orchestration...")
            
            return execute_multi_agent_orchestration(
                execution_plan, user_prompt, chat_history, hist, enhanced_supervisor
            )
            
        else:
            print(f"🎮 CONTROL FLOW: Supervisor determined single-agent execution sufficient")
            print(f"🎮 CONTROL FLOW: Delegating to single agent: {execution_plan.primary_agent}")
            # Fall back to single agent execution
            supervisor_msg = {
                "sender": "supervisor", 
                "text": f"Analysis Results:\nStrategy: {execution_plan.strategy}\nPrimary Agent: {execution_plan.primary_agent}\nTools Required: {', '.join(execution_plan.tools_needed) if execution_plan.tools_needed else 'None'}",
                "routing_decision": True,
                "chosen_agent": execution_plan.primary_agent,
                "supervisor_type": "enhanced"
            }
            hist.append(supervisor_msg)
            
            return execute_single_agent_orchestration(
                execution_plan, user_prompt, chat_history, hist, enhanced_supervisor
            )
            
    except Exception as e:
        error_msg = f"Enhanced supervisor processing failed: {str(e)}"
        print(f"🎮 CONTROL FLOW: CRITICAL ERROR - Supervisor failed during planning: {str(e)}")
        print(f"🔍 DEBUG: Exception in process_multi_agent_supervisor_message: {e}")
        import traceback
        traceback.print_exc()
        
        hist.append({
            "sender": "system",
            "text": error_msg,
            "error": True
        })
        
        return {
            "system_error": error_msg,
            "supervisor_routing": False,
            "error": True
        }

def execute_multi_agent_orchestration(execution_plan, user_prompt, chat_history, hist, enhanced_supervisor):
    """Execute multi-agent workflow with step-by-step tracking"""
    tool_outputs = {}
    agent_outputs = {}
    
    print("🎮 CONTROL FLOW: Supervisor taking control for multi-agent orchestration")
    print(f"🎮 CONTROL FLOW: Supervisor planning execution sequence: {execution_plan.agent_sequence}")
    
    try:
        # DON'T execute tools upfront - let agents call them when needed
        # Tools will be executed by individual agents through their process_request method
        
        # Execute agents sequentially
        print(f"🔍 DEBUG: Starting multi-agent execution with sequence: {execution_plan.agent_sequence}")
        print(f"🎮 CONTROL FLOW: Supervisor beginning sequential agent execution")
        
        for i, agent_id in enumerate(execution_plan.agent_sequence):
            print(f"\n{'='*60}")
            print(f"🎮 CONTROL FLOW: Supervisor preparing to delegate to {agent_id} (step {i+1}/{len(execution_plan.agent_sequence)})")
            print(f"🔍 DEBUG: Processing agent {i+1}/{len(execution_plan.agent_sequence)}: {agent_id}")
            
            # Add supervisor delegation message
            hist.append({
                "sender": "supervisor",
                "text": f"🔄 Delegating to {agent_id} (step {i+1}/{len(execution_plan.agent_sequence)})",
                "delegation": True,
                "agent_delegated": agent_id,
                "step": i+1
            })
            
            print(f"🎮 CONTROL FLOW: Supervisor delegating control to {agent_id}")
            
            # Build context for this agent - ensure clean separation
            if i == 0:
                # First agent gets the original query only
                agent_context = f"""Original request: {user_prompt}

Instructions: You are {agent_id} in a multi-agent workflow. {enhanced_supervisor._get_agent_instructions(agent_id, execution_plan.context_fusion)}

IMPORTANT: Only provide YOUR OWN response as {agent_id}. Do not generate responses for other agents in the sequence."""
            else:
                # Subsequent agents get previous outputs but with clear boundaries
                previous_outputs = []
                for prev_agent in execution_plan.agent_sequence[:i]:
                    if prev_agent in agent_outputs:
                        # Truncate long outputs but preserve full meaning
                        output = agent_outputs[prev_agent]
                        if len(output) > 500:
                            output = output[:500] + "... [truncated]"
                        previous_outputs.append(f"--- {prev_agent.upper()} OUTPUT ---\n{output}\n--- END {prev_agent.upper()} OUTPUT ---")
                
                agent_context = f"""Original request: {user_prompt}

Previous Agent Results:
{chr(10).join(previous_outputs)}

Instructions: You are {agent_id} (agent {i+1} of {len(execution_plan.agent_sequence)}). {enhanced_supervisor._get_agent_instructions(agent_id, execution_plan.context_fusion)}

IMPORTANT: Only provide YOUR OWN response as {agent_id}. Do not repeat or simulate responses from other agents. Build upon the previous work but respond only as yourself."""
            
            # Create State for this agent - let agent handle its own tools
            agent_state = State(
                user_prompt=agent_context,
                history=chat_history,
                tool_outputs={},  # Start fresh for each agent
                agent_outputs=agent_outputs  # Pass previous agent outputs
            )
            
            # Execute agent - agent will call tools if it needs them
            try:
                print(f"🔍 DEBUG: Checking if {agent_id} is in registry...")
                available_agents = enhanced_agent_registry.list_available_agents()
                print(f"🔍 DEBUG: Available agents: {available_agents}")
                
                if agent_id in available_agents:
                    print(f"🔍 DEBUG: Getting agent {agent_id} from registry...")
                    agent = enhanced_agent_registry.get_agent(agent_id)
                    print(f"🔍 DEBUG: Executing agent {agent_id}...")
                    print(f"🎮 CONTROL FLOW: {agent_id} taking control, processing request...")
                    
                    result = agent.process_request(agent_state)
                    agent_response = result.get("output", "No response generated")
                    
                    print(f"🎮 CONTROL FLOW: {agent_id} completed processing, returning control to supervisor")
                    print(f"🔍 DEBUG: Agent {agent_id} response: {agent_response[:100]}...")
                    
                    # Check if agent used tools and add them to history
                    if "tool_outputs" in result and result["tool_outputs"]:
                        print(f"🎮 CONTROL FLOW: {agent_id} used tools during execution:")
                        for tool_name, tool_result in result["tool_outputs"].items():
                            print(f"🎮 CONTROL FLOW: - {agent_id} called tool: {tool_name}")
                            hist.append({
                                "sender": "tool",
                                "text": tool_result.get("result", str(tool_result)),
                                "tool_id": tool_name,
                                "called_by_agent": agent_id,
                                "via_supervisor": False  # Called by agent, not supervisor
                            })
                            print(f"🔍 DEBUG: Added tool output from {agent_id} calling {tool_name}")
                    else:
                        print(f"🎮 CONTROL FLOW: {agent_id} did not use any tools")
                    
                    # Store agent output
                    agent_outputs[agent_id] = agent_response
                    
                    # Add agent response to history
                    hist.append({
                        "sender": agent_id,
                        "text": agent_response,
                        "via_supervisor": True,
                        "supervisor_type": "enhanced",
                        "step_in_sequence": i+1,
                        "total_steps": len(execution_plan.agent_sequence)
                    })
                    print(f"🔍 DEBUG: Added {agent_id} response to history")
                    print(f"🎮 CONTROL FLOW: Supervisor received output from {agent_id}")
                    
                    # Add supervisor acknowledgment
                    if i < len(execution_plan.agent_sequence) - 1:
                        next_agent = execution_plan.agent_sequence[i + 1]
                        ack_text = f"✅ Received output from {agent_id}, proceeding to next step..."
                        print(f"🎮 CONTROL FLOW: Supervisor acknowledging {agent_id}, preparing to delegate to {next_agent}")
                    else:
                        ack_text = f"✅ Multi-agent workflow completed. Final response from {agent_id}."
                        print(f"🎮 CONTROL FLOW: Supervisor acknowledging {agent_id}, workflow complete")
                    
                    hist.append({
                        "sender": "supervisor",
                        "text": ack_text,
                        "acknowledgment": True,
                        "agent_completed": agent_id
                    })
                    print(f"🔍 DEBUG: Added supervisor acknowledgment for {agent_id}")
                    
                else:
                    error_msg = f"Agent '{agent_id}' not available in registry"
                    print(f"🔍 DEBUG: ERROR - {error_msg}")
                    print(f"🎮 CONTROL FLOW: ERROR - Supervisor cannot delegate to {agent_id} (not in registry)")
                    agent_outputs[agent_id] = error_msg
                    hist.append({
                        "sender": "system",
                        "text": error_msg,
                        "error": True,
                        "agent_id": agent_id
                    })
            except Exception as e:
                error_msg = f"Exception executing agent {agent_id}: {str(e)}"
                print(f"🔍 DEBUG: EXCEPTION - {error_msg}")
                print(f"🎮 CONTROL FLOW: ERROR - Exception while {agent_id} had control: {str(e)}")
                import traceback
                traceback.print_exc()
                agent_outputs[agent_id] = error_msg
                hist.append({
                    "sender": "system",
                    "text": error_msg,
                    "error": True,
                    "agent_id": agent_id
                })
        
        print(f"\n{'='*60}")
        print(f"🎮 CONTROL FLOW: Supervisor concluding multi-agent orchestration")
        print(f"🎮 CONTROL FLOW: All agents completed: {list(agent_outputs.keys())}")
        
        # Return final result
        final_agent = execution_plan.agent_sequence[-1] if execution_plan.agent_sequence else "unknown"
        final_response = agent_outputs.get(final_agent, "No final response generated")
        
        print(f"🎮 CONTROL FLOW: Supervisor preparing final result with {final_agent}'s output")
        
        return {
            "agent_response": final_response,
            "chosen_agent": final_agent,
            "supervisor_decision": f"Multi-agent workflow: {' → '.join(execution_plan.agent_sequence)}",
            "tool_outputs": tool_outputs,
            "supervisor_routing": True,
            "supervisor_type": "enhanced",
            "multi_agent_execution": True,
            "agent_sequence": execution_plan.agent_sequence,
            "all_agent_outputs": agent_outputs
        }
        
    except Exception as e:
        error_msg = f"Multi-agent orchestration failed: {str(e)}"
        print(f"🎮 CONTROL FLOW: CRITICAL ERROR - Supervisor lost control due to: {str(e)}")
        hist.append({
            "sender": "system",
            "text": error_msg,
            "error": True
        })
        
        return {
            "system_error": error_msg,
            "supervisor_routing": False,
            "error": True
        }

def execute_single_agent_orchestration(execution_plan, user_prompt, chat_history, hist, enhanced_supervisor):
    """Execute single agent workflow"""
    # This is the original single-agent logic
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
        
        hist.append({
            "sender": "tool",
            "text": search_result,
            "tool_id": "web_search",
            "for_agent": execution_plan.primary_agent,
            "via_supervisor": True
        })
    
    # Execute the primary agent
    enhanced_context = f"""Original request: {user_prompt}

Tool Results:
{json.dumps(tool_outputs, indent=2) if tool_outputs else "No tools executed"}

Instructions: Respond as {execution_plan.primary_agent} using the {execution_plan.context_fusion} approach."""
    
    agent_state = State(
        user_prompt=enhanced_context,
        history=chat_history,
        tool_outputs=tool_outputs,
        agent_flow=[{"id": execution_plan.primary_agent, "enabled": True, "tools": []}]
    )
    
    # Execute the chosen agent
    agent_response = "No response generated"
    try:
        if execution_plan.primary_agent in enhanced_agent_registry.list_available_agents():
            agent = enhanced_agent_registry.get_agent(execution_plan.primary_agent)
            result = agent.process_request(agent_state)
            agent_response = result.get("output", "No response generated")
        else:
            agent_response = f"Agent '{execution_plan.primary_agent}' not available in registry"
    except Exception as e:
        print(f"Error executing agent {execution_plan.primary_agent}: {e}")
        agent_response = f"Error executing agent: {str(e)}"
    
    # Add agent response to history
    hist.append({
        "sender": execution_plan.primary_agent,
        "text": agent_response,
        "via_supervisor": True,
        "supervisor_type": "enhanced"
    })
    
    return {
        "agent_response": agent_response,
        "chosen_agent": execution_plan.primary_agent,
        "supervisor_decision": f"Single agent routing to {execution_plan.primary_agent}",
        "tool_outputs": tool_outputs,
        "supervisor_routing": True,
        "supervisor_type": "enhanced"
    }

def process_supervisor_message(chat_id: str, user_prompt: str):
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
        
        # Create enhanced supervisor with all available agents
        available_agents = enhanced_agent_registry.list_available_agents()
        enhanced_supervisor = EnhancedSupervisor(
            available_agents=available_agents,
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
        
        # Get conversation history from chat
        chat_history = []
        if chat_id in chats:
            chat = chats[chat_id]
            chat_history = [ChatMessage(**m) for m in chat.get("history", [])]
        
        # Execute the plan - check if multi-agent execution is needed
        if execution_plan.requires_multi_agent:
            # Execute multi-agent plan
            execution_results = enhanced_supervisor.execute_multi_agent_plan(
                execution_plan, 
                user_prompt, 
                chat_history, 
                enhanced_agent_registry
            )
            
            # Build multi-agent plan explanation
            multi_agent_explanation = f"""Multi-Agent Enhanced Analysis:
Strategy: {execution_plan.strategy}
Agent Sequence: {' → '.join(execution_plan.agent_sequence)}
Components Detected: {len(execution_plan.components)}"""
            
            for i, component in enumerate(execution_plan.components, 1):
                multi_agent_explanation += f"\n  {i}. {component.intent} -> {component.resource_type.value}: {component.resource_id}"
            
            if execution_plan.tools_needed:
                multi_agent_explanation += f"\nTools Required: {', '.join(execution_plan.tools_needed)}"
            
            multi_agent_explanation += f"\nContext Fusion: {execution_plan.context_fusion}"
            multi_agent_explanation += f"\nExecution Sequence: {' → '.join(execution_results['execution_sequence'])}"
            
            return {
                "supervisor_decision": multi_agent_explanation,
                "chosen_agent": execution_plan.agent_sequence[-1],  # Last agent in sequence
                "agent_response": execution_results["final_agent_response"],
                "tool_outputs": execution_results["tool_outputs"],
                "supervisor_type": "enhanced",
                "execution_plan": {
                    "strategy": execution_plan.strategy,
                    "components": len(execution_plan.components),
                    "context_fusion": execution_plan.context_fusion,
                    "multi_agent": True,
                    "agent_sequence": execution_plan.agent_sequence
                },
                "multi_agent_results": execution_results
            }
        else:
            # Single agent execution (original logic)
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
            
            # Create agent state with enhanced context AND conversation history
            agent_state = State(
                user_prompt=enhanced_context,
                history=chat_history,
                tool_outputs=tool_outputs,
                agent_flow=[{"id": execution_plan.primary_agent, "enabled": True, "tools": []}]
            )
            
            # Execute the chosen agent using the enhanced registry
            agent_response = "No response generated"
            try:
                if execution_plan.primary_agent in enhanced_agent_registry.list_available_agents():
                    agent = enhanced_agent_registry.get_agent(execution_plan.primary_agent)
                    result = agent.process_request(agent_state)
                    agent_response = result.get("output", "No response generated")
                else:
                    agent_response = f"Agent '{execution_plan.primary_agent}' not available in registry"
            except Exception as e:
                print(f"Error executing agent {execution_plan.primary_agent}: {e}")
                agent_response = f"Error executing agent: {str(e)}"
            
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
        
        # Return error if enhanced supervisor fails
        return {
            "supervisor_decision": f"Enhanced supervisor failed: {str(e)}",
            "chosen_agent": "story_creator",
            "agent_response": "I apologize, but I encountered an error processing your request. Please try again.",
            "tool_outputs": {},
            "supervisor_type": "enhanced",
            "execution_plan": {
                "strategy": "error_fallback",
                "components": 0,
                "context_fusion": "error_handling"
            }
        }

@app.get("/knowledgebase")
def get_knowledgebase():
    kb_path = Path(__file__).parent.parent / "data" / "knowledgebase.json"
    with open(kb_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/agents")
def list_available_agents():
    """Get all available agents with their metadata"""
    try:
        agents_metadata = enhanced_agent_registry.list_all_agents_metadata()
        return {
            "agents": agents_metadata,
            "total": len(agents_metadata),
            "available_ids": enhanced_agent_registry.list_available_agents()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing agents: {str(e)}")

@app.get("/agents/{agent_id}")
def get_agent_info(agent_id: str):
    """Get detailed information about a specific agent"""
    try:
        if agent_id not in enhanced_agent_registry.list_available_agents():
            raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
        
        metadata = enhanced_agent_registry.get_agent_metadata(agent_id)
        return metadata
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting agent info: {str(e)}")

@app.get("/agents/capabilities/{capability}")
def find_agents_by_capability(capability: str):
    """Find agents that support a specific capability"""
    try:
        matching_agents = enhanced_agent_registry.find_agents_by_capability(capability)
        agents_info = []
        
        for agent_id in matching_agents:
            try:
                metadata = enhanced_agent_registry.get_agent_metadata(agent_id)
                agents_info.append(metadata)
            except Exception as e:
                print(f"⚠️ Error getting info for agent {agent_id}: {e}")
        
        return {
            "capability": capability,
            "matching_agents": agents_info,
            "count": len(agents_info)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding agents: {str(e)}")

@app.get("/agents/skills/{skill_name}")
def find_agents_by_skill(skill_name: str):
    """Find JSON agents that have a specific skill"""
    try:
        matching_agents = enhanced_agent_registry.find_agents_by_skill(skill_name)
        agents_info = []
        
        for agent_id in matching_agents:
            try:
                metadata = enhanced_agent_registry.get_agent_metadata(agent_id)
                agents_info.append(metadata)
            except Exception as e:
                print(f"⚠️ Error getting info for agent {agent_id}: {e}")
        
        return {
            "skill": skill_name,
            "matching_agents": agents_info,
            "count": len(agents_info)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding agents by skill: {str(e)}")

@app.post("/agents/reload")
def reload_agents():
    """Reload all agents (useful for development)"""
    try:
        enhanced_agent_registry.reload_agents()
        agents_metadata = enhanced_agent_registry.list_all_agents_metadata()
        return {
            "message": "Agents reloaded successfully",
            "agents": agents_metadata,
            "total": len(agents_metadata)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reloading agents: {str(e)}")


@app.get("/skills")
def get_all_skills():
    """Get all available skills with their metadata"""
    try:
        import json
        import os
        
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'agents_config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        skills = config_data.get('skills', {})
        skills_list = []
        
        for skill_id, skill_config in skills.items():
            skills_list.append({
                "id": skill_id,
                "name": skill_config.get("name", skill_id.title()),
                "description": skill_config.get("description", f"Skill: {skill_id}"),
                "function": skill_config.get("function", f"{skill_id}_skill"),
                "parameters": skill_config.get("parameters", {}),
                "category": skill_config.get("category", "general")
            })
        
        return {
            "skills": skills_list,
            "total": len(skills_list),
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading skills: {str(e)}")


@app.get("/tools")
def get_all_tools():
    """Get all available tools with their metadata"""
    try:
        from .tools.tool_config import get_all_available_tools, get_tool_description
        
        all_tools = get_all_available_tools()
        tools_list = []
        
        for tool_name in all_tools:
            tool_metadata = get_tool_description(tool_name)
            if tool_metadata:
                tools_list.append({
                    "id": tool_name,
                    "name": tool_metadata.name,
                    "description": tool_metadata.description,
                    "use_cases": tool_metadata.use_cases,
                    "input_format": tool_metadata.input_format,
                    "confidence_threshold": tool_metadata.confidence_threshold,
                    "fallback_behavior": tool_metadata.fallback_behavior
                })
            else:
                # Fallback for tools without metadata
                tools_list.append({
                    "id": tool_name,
                    "name": tool_name.replace("_", " ").title(),
                    "description": f"Tool: {tool_name}",
                    "use_cases": [],
                    "input_format": "General input",
                    "confidence_threshold": 0.7,
                    "fallback_behavior": "inform_user"
                })
        
        return {
            "tools": tools_list,
            "total": len(tools_list),
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading tools: {str(e)}")

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
        "supervisor_type": "enhanced"
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
        # Legacy imports removed - now using enhanced_agent_registry for streaming too
        # from .granny.agent import create_granny_response_stream
        # from .story_creator.agent import create_story_response_stream  
        # from .parody_creator.agent import create_parody_response_stream
        
        hist = chat["history"]
        hist.append({"sender": "user", "text": req.user_prompt})
        
        # Check if supervisor mode is enabled
        if chat.get("supervisor_mode", False) and SUPERVISOR_AVAILABLE:
            try:
                # Process with supervisor
                result = process_multi_agent_supervisor_message(
                    chat_id, 
                    req.user_prompt
                )
                
                # Check if this is a multi-agent response
                if result.get("multi_agent_execution", False):
                    # For multi-agent: all messages were already added to hist during orchestration
                    # Stream all messages that were added during orchestration (everything after user message)
                    print(f"🔍 DEBUG: Multi-agent streaming - hist has {len(hist)} messages")
                    
                    # Find the last user message (the one we just processed)
                    user_msg_index = -1
                    for i in range(len(hist) - 1, -1, -1):
                        if hist[i].get("sender") == "user" and hist[i].get("text") == req.user_prompt:
                            user_msg_index = i
                            break
                    
                    # Stream all messages added after the user message
                    if user_msg_index >= 0:
                        for msg in hist[user_msg_index + 1:]:
                            yield json.dumps(msg) + "\n"
                            print(f"🔍 DEBUG: Streamed message from {msg.get('sender', 'unknown')}")
                    else:
                        print(f"🔍 DEBUG: Could not find user message to start streaming from")
                
                else:
                    # Single-agent logic (original)
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
            
            # Stream the agent's response using enhanced registry
            full_response = ""
            try:
                # Get agent from enhanced registry and stream response
                agent = enhanced_agent_registry.get_agent(agent_id)
                for chunk in agent.process_request_stream(current_state):
                    full_response += chunk
                    chunk_msg = {
                        "sender": agent_id,
                        "text": chunk,
                        "stream_chunk": True
                    }
                    yield json.dumps(chunk_msg) + "\n"
            except Exception as e:
                # Fallback if streaming fails
                error_msg = {
                    "sender": agent_id,
                    "text": f"Error streaming from {agent_id}: {str(e)}",
                    "stream_chunk": True,
                    "error": True
                }
                yield json.dumps(error_msg) + "\n"
                full_response = f"Error: {str(e)}"
            
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
            # Use enhanced multi-agent supervisor orchestration
            result = process_multi_agent_supervisor_message(chat_id, req.user_prompt)
            
            save_chats()
            return result
            
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
def toggle_supervisor_mode(chat_id: str, enabled: bool = True):
    """Convenience endpoint to enable/disable supervisor mode for a chat"""
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")
    
    if not SUPERVISOR_AVAILABLE and enabled:
        raise HTTPException(400, "Supervisor functionality not available")
    
    chats[chat_id]["supervisor_mode"] = enabled
    chats[chat_id]["supervisor_type"] = "enhanced"  # Always use enhanced
    save_chats()
    
    return {
        "supervisor_mode": enabled,
        "supervisor_type": "enhanced",
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
        "supervisor_type": "enhanced",
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