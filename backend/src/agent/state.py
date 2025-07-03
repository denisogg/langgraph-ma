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
    
    # Generic agent outputs instead of hardcoded ones
    agent_outputs: Dict[str, str] = {}  # agent_id → output
    agent_metadata: Dict[str, Dict[str, Any]] = {}  # agent_id → execution metadata
    
    # For chaining agents - the last agent's output becomes input for next agent
    previous_agent_output: Optional[str] = None
    current_agent_id: Optional[str] = None
    
    # Agent flow configuration for intelligent tool usage
    agent_flow: Optional[List[Dict[str, Any]]] = None
    
    # Execution context for tracking state across components
    execution_context: Dict[str, Any] = {}

    def with_updates(self, **kwargs) -> "State":
        """Returns a new State object with updated fields."""
        return self.copy(update=kwargs)
    
    def get_agent_output(self, agent_id: str) -> Optional[str]:
        """Get output from specific agent"""
        return self.agent_outputs.get(agent_id)
    
    def set_agent_output(self, agent_id: str, output: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Set output for specific agent"""
        self.agent_outputs[agent_id] = output
        if metadata:
            self.agent_metadata[agent_id] = metadata
        
        # Update chaining context
        self.previous_agent_output = output
        self.current_agent_id = agent_id
    
    def get_agent_metadata(self, agent_id: str) -> Dict[str, Any]:
        """Get execution metadata for specific agent"""
        return self.agent_metadata.get(agent_id, {})
    
    def has_agent_output(self, agent_id: str) -> bool:
        """Check if agent has already produced output"""
        return agent_id in self.agent_outputs
    
    def get_all_agent_outputs(self) -> Dict[str, str]:
        """Get all agent outputs"""
        return self.agent_outputs.copy()
    
    def clear_agent_outputs(self) -> None:
        """Clear all agent outputs (useful for reprocessing)"""
        self.agent_outputs.clear()
        self.agent_metadata.clear()
        self.previous_agent_output = None
        self.current_agent_id = None
    
    def get_context_for_agent(self, agent_id: str) -> str:
        """Get the appropriate context for the current agent"""
        context_parts = []
        
        # Add conversation history for full context
        if self.history:
            history_context = []
            for message in self.history:
                sender = message.sender
                text = message.text[:500] + "..." if len(message.text) > 500 else message.text
                
                # Format different types of messages
                if sender == "user":
                    history_context.append(f"User: {text}")
                elif sender == "supervisor":
                    if hasattr(message, 'routing_decision') and message.routing_decision:
                        # Skip routing decision messages, just show the chosen agent
                        chosen_agent = getattr(message, 'chosen_agent', 'unknown')
                        history_context.append(f"Supervisor → {chosen_agent}")
                    else:
                        history_context.append(f"Supervisor: {text}")
                elif sender == "tool":
                    tool_id = getattr(message, 'tool_id', 'unknown')
                    for_agent = getattr(message, 'for_agent', 'unknown')
                    history_context.append(f"Tool {tool_id} (for {for_agent}): {text}")
                else:
                    # Agent response
                    history_context.append(f"{sender}: {text}")
            
            if history_context:
                context_parts.append("=== CONVERSATION HISTORY ===\n" + "\n".join(history_context))
        
        # Add tool outputs if any (current request)
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
            context_parts.append("=== CURRENT TOOL OUTPUTS ===\n" + "\n".join(tool_context))
        
        # Add all previous agent outputs from this conversation
        if self.agent_outputs:
            agent_context = []
            for agent_id_key, output in self.agent_outputs.items():
                if agent_id_key != agent_id:  # Don't include the current agent's own output
                    output_preview = output[:300] + "..." if len(output) > 300 else output
                    agent_context.append(f"{agent_id_key}: {output_preview}")
            
            if agent_context:
                context_parts.append("=== AGENT OUTPUTS IN THIS CONVERSATION ===\n" + "\n".join(agent_context))
        
        # Add original user prompt for current request
        context_parts.append(f"=== CURRENT REQUEST ===\nUser prompt: {self.user_prompt}")
        
        return "\n\n".join(context_parts)
    
    # Backward compatibility methods (deprecated - will be removed)
    @property
    def granny_output(self) -> Optional[str]:
        """Deprecated: Use get_agent_output('granny') instead"""
        return self.get_agent_output('granny')
    
    @granny_output.setter
    def granny_output(self, value: Optional[str]) -> None:
        """Deprecated: Use set_agent_output('granny', value) instead"""
        if value is not None:
            self.set_agent_output('granny', value)
    
    @property
    def story_output(self) -> Optional[str]:
        """Deprecated: Use get_agent_output('story_creator') instead"""
        return self.get_agent_output('story_creator')
    
    @story_output.setter
    def story_output(self, value: Optional[str]) -> None:
        """Deprecated: Use set_agent_output('story_creator', value) instead"""
        if value is not None:
            self.set_agent_output('story_creator', value)
    
    @property
    def parody_output(self) -> Optional[str]:
        """Deprecated: Use get_agent_output('parody_creator') instead"""
        return self.get_agent_output('parody_creator')
    
    @parody_output.setter
    def parody_output(self, value: Optional[str]) -> None:
        """Deprecated: Use set_agent_output('parody_creator', value) instead"""
        if value is not None:
            self.set_agent_output('parody_creator', value) 