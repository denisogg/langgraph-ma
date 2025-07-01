import os
import uuid
import json
from typing import List, Optional, Dict, Any, Union
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pathlib import Path

try:
    from .story_creator.agent import create_story, create_story_response_stream
    from .parody_creator.agent import create_parody
    from .granny.agent import create_granny_response, create_granny_response_stream
    from .state import ChatMessage, State
    from .supervisor.supervisor_agent import create_supervisor_agent, create_advanced_supervisor_agent
    print("✓ Successfully imported all agent modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    raise

try:
    from langgraph.graph import StateGraph, START, END, MessagesState
    from langgraph.types import Command
    from langchain_core.messages import HumanMessage, AIMessage
    print("✓ Successfully imported LangGraph modules")
except ImportError as e:
    print(f"❌ LangGraph import error: {e}")
    print("Please install langgraph: pip install langgraph")
    raise

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

DATA_FILE = "../chats_supervisor.json"
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        chats: dict = json.load(f)
else:
    chats = {}

def save_chats():
    """Save chats to disk"""
    with chats_lock:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(chats, f, indent=2, ensure_ascii=False)

def convert_state_to_messages(state: State) -> List[Dict]:
    """Convert custom State to MessagesState format"""
    messages = []
    
    # Add conversation history
    for msg in state.history:
        if msg.sender == "user":
            messages.append(HumanMessage(content=msg.text))
        else:
            messages.append(AIMessage(content=msg.text, name=msg.sender))
    
    # Add current user prompt
    messages.append(HumanMessage(content=state.user_prompt))
    
    return messages

def convert_messages_to_state(messages: List, original_state: State) -> State:
    """Convert MessagesState back to custom State format"""
    # Extract the last AI message as the response
    last_message = messages[-1] if messages else None
    
    if last_message and hasattr(last_message, 'content'):
        # Determine which agent generated the response based on the name
        agent_name = getattr(last_message, 'name', 'unknown')
        
        # Update the appropriate agent output field
        updates = {
            "previous_agent_output": last_message.content,
            "current_agent_id": agent_name
        }
        
        if agent_name == "granny":
            updates["granny_output"] = last_message.content
        elif agent_name == "story_creator":
            updates["story_output"] = last_message.content
        elif agent_name == "parody_creator":
            updates["parody_output"] = last_message.content
            
        return original_state.with_updates(**updates)
    
    return original_state

# Agent wrapper functions that integrate with your existing agents
def granny_node(state: MessagesState) -> Command:
    """Wrapper for granny agent that maintains compatibility"""
    # Convert MessagesState to your custom State format
    last_message = state["messages"][-1] if state["messages"] else None
    user_prompt = str(last_message.content) if last_message and hasattr(last_message, 'content') else ""
    
    # Create a minimal State object for the agent
    agent_state = State(
        user_prompt=user_prompt,
        history=[],  # Could extract from messages if needed
        tool_outputs={},
        agent_flow=None  # Could be configured if tools are needed
    )
    
    # Call your existing agent
    result = create_granny_response(agent_state)
    
    # Return with supervisor as the next destination
    return Command(
        goto="supervisor",
        update={"messages": state["messages"] + [
            AIMessage(content=result["granny_output"], name="granny")
        ]}
    )

def story_creator_node(state: MessagesState) -> Command:
    """Wrapper for story creator agent"""
    last_message = state["messages"][-1] if state["messages"] else None
    user_prompt = str(last_message.content) if last_message and hasattr(last_message, 'content') else ""
    
    agent_state = State(
        user_prompt=user_prompt,
        history=[],
        tool_outputs={},
        agent_flow=None
    )
    
    result = create_story(agent_state)
    
    return Command(
        goto="supervisor", 
        update={"messages": state["messages"] + [
            AIMessage(content=result["story_output"], name="story_creator")
        ]}
    )

def parody_creator_node(state: MessagesState) -> Command:
    """Wrapper for parody creator agent"""
    last_message = state["messages"][-1] if state["messages"] else None
    user_prompt = str(last_message.content) if last_message and hasattr(last_message, 'content') else ""
    
    agent_state = State(
        user_prompt=user_prompt,
        history=[],
        tool_outputs={},
        agent_flow=None
    )
    
    result = create_parody(agent_state)
    
    return Command(
        goto="supervisor",
        update={"messages": state["messages"] + [
            AIMessage(content=result["parody_output"], name="parody_creator")
        ]}
    )

def build_supervisor_graph(use_advanced: bool = False):
    """Build the supervisor-based graph"""
    
    # Create supervisor agent
    if use_advanced:
        supervisor_agent = create_advanced_supervisor_agent()
    else:
        supervisor_agent = create_supervisor_agent()
    
    # Build the graph
    builder = StateGraph(MessagesState)
    
    # Add supervisor node
    builder.add_node("supervisor", supervisor_agent)
    
    # Add agent nodes
    builder.add_node("granny", granny_node)
    builder.add_node("story_creator", story_creator_node) 
    builder.add_node("parody_creator", parody_creator_node)
    
    # Set entry point
    builder.add_edge(START, "supervisor")
    
    # Add edges back to supervisor (agents return control to supervisor)
    builder.add_edge("granny", "supervisor")
    builder.add_edge("story_creator", "supervisor")
    builder.add_edge("parody_creator", "supervisor")
    
    return builder.compile()

# Create both versions of the graph
supervisor_graph = build_supervisor_graph(use_advanced=False)
advanced_supervisor_graph = build_supervisor_graph(use_advanced=True)

class MessageRequest(BaseModel):
    user_prompt: str
    use_advanced_supervisor: bool = False

class SupervisorChatSettings(BaseModel):
    supervisor_mode: str = "basic"  # "basic" or "advanced"

@app.get("/supervisor/chats")
def list_supervisor_chats():
    """List all supervisor-based chats"""
    return [{"id": chat_id, **chat_data} for chat_id, chat_data in chats.items()]

@app.post("/supervisor/chats")
def create_supervisor_chat():
    """Create a new supervisor-based chat"""
    chat_id = str(uuid.uuid4())
    chats[chat_id] = {
        "id": chat_id, 
        "supervisor_mode": "basic",
        "history": []
    }
    save_chats()
    return chats[chat_id]

@app.get("/supervisor/chats/{chat_id}")
def get_supervisor_chat(chat_id: str):
    """Get a specific supervisor chat"""
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")
    return chats[chat_id]

@app.post("/supervisor/chats/{chat_id}/settings")
def update_supervisor_settings(chat_id: str, settings: SupervisorChatSettings):
    """Update supervisor chat settings"""
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")
    chats[chat_id]["supervisor_mode"] = settings.supervisor_mode
    save_chats()
    return {"ok": True}

@app.post("/supervisor/chats/{chat_id}/message")
def send_supervisor_message(chat_id: str, req: MessageRequest):
    """Send a message using the supervisor pattern"""
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")
    
    chat = chats[chat_id]
    
    # Choose which graph to use
    graph = advanced_supervisor_graph if req.use_advanced_supervisor else supervisor_graph
    
    # Prepare input messages
    messages = []
    
    # Add chat history
    for msg in chat.get("history", []):
        if msg["sender"] == "user":
            messages.append(HumanMessage(content=msg["text"]))
        else:
            messages.append(AIMessage(content=msg["text"], name=msg.get("agent", "assistant")))
    
    # Add current user message
    messages.append(HumanMessage(content=req.user_prompt))
    
    try:
        # Run the supervisor graph
        result = graph.invoke({"messages": messages})
        
        # Extract the final response
        final_message = result["messages"][-1]
        agent_name = getattr(final_message, 'name', 'assistant')
        response_text = final_message.content
        
        # Update chat history
        chat["history"].append({
            "sender": "user",
            "text": req.user_prompt
        })
        chat["history"].append({
            "sender": agent_name,
            "text": response_text,
            "agent": agent_name
        })
        
        save_chats()
        
        return {
            "response": response_text,
            "agent": agent_name,
            "message_history": result["messages"]
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error processing message: {str(e)}")

@app.post("/supervisor/chats/{chat_id}/message/stream")
async def stream_supervisor_message(chat_id: str, req: MessageRequest):
    """Stream a message using the supervisor pattern"""
    if chat_id not in chats:
        raise HTTPException(404, "Chat not found")
    
    # For now, use non-streaming and return the result
    # You could implement streaming by modifying the graph to support streaming
    result = send_supervisor_message(chat_id, req)
    
    async def stream_response():
        # Simulate streaming by yielding the response in chunks
        response = result["response"]
        import time
        for i in range(0, len(response), 10):
            chunk = response[i:i+10]
            yield f"data: {json.dumps({'content': chunk, 'agent': result['agent']})}\n\n"
            time.sleep(0.05)
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return StreamingResponse(stream_response(), media_type="text/plain")

@app.get("/supervisor/graph/visualization")
def get_supervisor_graph_visualization():
    """Get a visual representation of the supervisor graph"""
    try:
        # You could implement graph visualization here
        # For now, return a simple description
        return {
            "nodes": ["supervisor", "granny", "story_creator", "parody_creator"],
            "edges": [
                {"from": "START", "to": "supervisor"},
                {"from": "supervisor", "to": "granny"},
                {"from": "supervisor", "to": "story_creator"}, 
                {"from": "supervisor", "to": "parody_creator"},
                {"from": "granny", "to": "supervisor"},
                {"from": "story_creator", "to": "supervisor"},
                {"from": "parody_creator", "to": "supervisor"}
            ],
            "description": "Supervisor-based multi-agent system with dynamic routing"
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 