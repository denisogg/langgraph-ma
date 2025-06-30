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

from src.agent.story_creator.agent import create_story
from src.agent.parody_creator.agent import create_parody
from src.agent.granny.agent import create_granny_response
from src.agent.state import ChatMessage, State
from src.agent.tools.tool_executor import execute_tool
from src.agent.tools.tool_config import ToolConfig

from langgraph.graph import StateGraph
import threading

chats_lock = threading.Lock()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "chats.json"
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

class MessageRequest(BaseModel):
    user_prompt: str

def build_execution_plan(enabled_agents: List[Dict[str, Any]]) -> List[str]:
    execution_plan = []
    
    for agent in enabled_agents:
        agent_id = agent["id"]
        tools = agent.get("tools") or []
        
        # Add tool nodes before the agent node
        for t in tools:
            if isinstance(t, dict):
                tool_name = t.get("name", "")
                tool_option = t.get("option")
            elif hasattr(t, 'name'):
                tool_name = getattr(t, "name", "")
                tool_option = getattr(t, "option", None)
            else:
                tool_name = str(t)
                tool_option = None
            if not isinstance(tool_name, str) or not tool_name:
                raise ValueError(f"Invalid tool name: {tool_name}")
            tool_node = f"tool_{sanitize_node_id(agent_id)}_{sanitize_node_id(tool_name)}"
            TOOL_CONFIGS[tool_node] = ToolConfig(name=tool_name, option=tool_option)
            execution_plan.append(tool_node)
        
        # Add the agent node after its tools
        execution_plan.append(agent_id)
    
    return execution_plan

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
    chats[chat_id] = {"id": chat_id, "agent_sequence": [], "history": []}
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
    # Only save if chat has content (settings or messages)
    if chats[chat_id]["history"] or any(a["enabled"] for a in chats[chat_id]["agent_sequence"]):
        save_chats()
    return {"ok": True}

@app.post("/chats/{chat_id}/message/stream")
async def stream_message(chat_id: str, req: MessageRequest):
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")
    cfg = chats[chat_id]["agent_sequence"]
    enabled = [a for a in cfg if a["enabled"]]
    if not enabled:
        raise HTTPException(400, "No agents enabled")
    
    execution_plan = build_execution_plan(enabled)
    previous = chats[chat_id]["history"]
    state = State(
        user_prompt=req.user_prompt, 
        history=[ChatMessage(**m) for m in previous],
        agent_flow=enabled
    )
    
    async def stream_generator():
        import json
        from src.agent.granny.agent import create_granny_response_stream
        from src.agent.story_creator.agent import create_story_response_stream
        from src.agent.parody_creator.agent import create_parody_response_stream
        
        hist = chats[chat_id]["history"]
        hist.append({"sender": "user", "text": req.user_prompt})
        
        # Execute tools first for all enabled agents
        from src.agent.tools.tool_executor import execute_intelligent_tools
        from src.agent.tools.tool_config import ToolConfig
        
        # Initialize state with current state
        current_state = state
        
        # Collect all tools from enabled agents
        for agent_config in enabled:
            agent_tools = []
            if "tools" in agent_config:
                agent_tools = [
                    ToolConfig(name=tool["name"], option=tool.get("option"))
                    if isinstance(tool, dict) else ToolConfig(name=tool)
                    for tool in agent_config["tools"]
                ]
            
            if agent_tools:
                current_state = execute_intelligent_tools(current_state, agent_tools, agent_config["id"])
        
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
    cfg = chats[chat_id]["agent_sequence"]
    enabled = [a for a in cfg if a["enabled"]]
    if not enabled:
        raise HTTPException(400, "No agents enabled")
    
    execution_plan = build_execution_plan(enabled)
    previous = chats[chat_id]["history"]
    state = State(
        user_prompt=req.user_prompt, 
        history=[ChatMessage(**m) for m in previous],
        agent_flow=enabled
    )
    flow = build_dynamic_graph(execution_plan)
    
    # Execute the flow
    out = State(**flow.invoke(state))
    
    # Build response history
    hist = chats[chat_id]["history"]
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