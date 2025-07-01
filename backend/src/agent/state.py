from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ChatMessage(BaseModel):
    sender: str
    text: str
    for_agent: Optional[str] = None
    tool_id: Optional[str] = None

class State(BaseModel):
    user_prompt: str
    history: List[ChatMessage]
    tool_outputs: Dict[str, Any] = {}  # store tool_name → result here (can be string or dict with metadata)
    
    # Agent outputs - renamed to avoid conflicts with node names
    granny_output: Optional[str] = None
    story_output: Optional[str] = None
    parody_output: Optional[str] = None
    
    # For chaining agents - the last agent's output becomes input for next agent
    previous_agent_output: Optional[str] = None
    current_agent_id: Optional[str] = None
    
    # Agent flow configuration for intelligent tool usage
    agent_flow: Optional[List[Dict[str, Any]]] = None

    def with_updates(self, **kwargs) -> "State":
        """Returns a new State object with updated fields."""
        return self.copy(update=kwargs)
    
    def get_context_for_agent(self, agent_id: str) -> str:
        """Get the appropriate context for the current agent"""
        context_parts = []
        
        # Add tool outputs if any
        if self.tool_outputs:
            tool_context = []
            for tool_name, output in self.tool_outputs.items():
                if isinstance(output, dict):
                    # Extract result from metadata dict
                    result = output.get("result", str(output))
                    query = output.get("query_used", "")
                    confidence = output.get("confidence", 0)
                    tool_context.append(f"Tool '{tool_name}' (query: '{query}', confidence: {confidence:.2f}): {result}")
                else:
                    tool_context.append(f"Tool '{tool_name}' result: {output}")
            context_parts.append("\n".join(tool_context))
        
        # Add previous agent output if this isn't the first agent
        if self.previous_agent_output:
            context_parts.append(f"Previous agent output: {self.previous_agent_output}")
        
        # Add original user prompt
        context_parts.append(f"User prompt: {self.user_prompt}")
        
        return "\n\n".join(context_parts) 