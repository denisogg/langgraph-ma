# granny/agent.py
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from dotenv import load_dotenv
from typing import Generator, List, Dict, Any, Optional
from ..base_agent import BaseAgent
from ..state import State
from ..tools.tool_config import ToolConfig
from ..tools.tool_executor import get_agent_tools_context, execute_intelligent_tools

load_dotenv()


class GrannyAgent(BaseAgent):
    """Romanian grandmother agent providing warm wisdom, recipes, and family advice"""
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config)
        self.llm = ChatOpenAI(
            model=self.model, 
            temperature=self.temperature, 
            streaming=True
        )
    
    def get_name(self) -> str:
        return "Romanian Grandmother"
    
    def get_description(self) -> str:
        return "A warm, wise Romanian grandmother who shares traditional recipes, family values, and life lessons with love and care"
    
    def get_capabilities(self) -> List[str]:
        return [
            "recipes", 
            "cooking", 
            "family_advice", 
            "traditional_knowledge", 
            "romanian_culture", 
            "wisdom", 
            "life_lessons",
            "comfort",
            "nurturing"
        ]
    
    def get_system_prompt(self) -> str:
        return """You are a sweet old Romanian grandmother who responds with warmth, wisdom, and love. 
You often reference traditional Romanian recipes, family values, and life lessons.

When you have tools available, you are aware of their capabilities and will use them strategically to provide better help.
The system will automatically analyze your user's needs and provide you with relevant tool results when needed.
Your job is to integrate any tool results naturally into your warm, grandmotherly responses.

Remember: You are still the loving grandmother, but now you can access additional information when needed to help better."""
    
    def get_routing_keywords(self) -> List[str]:
        return [
            "recipe", "cooking", "cook", "food", "ciorba", "soup",
            "grandmother", "granny", "bunica", "family", "traditional",
            "romanian", "advice", "wisdom", "comfort", "help", "guidance"
        ]
    
    def _get_tools_for_request(self, state: State) -> List[ToolConfig]:
        """Get tools configured for this agent from the current flow"""
        granny_tools = []
        if state.agent_flow:
            for agent_config in state.agent_flow:
                if agent_config["id"] == self.agent_id and "tools" in agent_config:
                    granny_tools = [
                        ToolConfig(name=tool["name"], option=tool.get("option"))
                        if isinstance(tool, dict) else ToolConfig(name=tool)
                        for tool in agent_config["tools"]
                    ]
                    break
        return granny_tools
    
    def _build_prompt(self, state: State, tools_context: str = "") -> str:
        """Build the complete prompt for the agent"""
        convo = "\n".join(f"{msg.sender}: {msg.text}" for msg in state.history)
        
        # Prepare the prompt with tool outputs if available
        prompt_parts = [f"Conversation history:\n{convo}"]
        
        # Add tool outputs to context if any were used
        if state.tool_outputs:
            prompt_parts.append("\nTool Results Available:")
            for tool_name, tool_output in state.tool_outputs.items():
                if isinstance(tool_output, dict):
                    result = tool_output.get("result", str(tool_output))
                    query_used = tool_output.get("query_used", "")
                    confidence = tool_output.get("confidence", 0)
                    
                    prompt_parts.append(f"\n• {tool_name.upper()} (query: '{query_used}', confidence: {confidence:.2f}):")
                    prompt_parts.append(f"  {result}")
                else:
                    prompt_parts.append(f"\n• {tool_name.upper()}: {tool_output}")
        
        prompt_parts.append(f"\nUser's current request: {state.user_prompt}")
        
        if state.tool_outputs:
            prompt_parts.append(
                "\nInstructions: Use the tool results above to enhance your response. "
                "Integrate the information naturally into your warm, grandmotherly advice. "
                "If the tools provided useful information, reference it in your response. "
                "If the tool results weren't helpful, acknowledge this and provide your best guidance anyway."
            )
        
        return "\n".join(prompt_parts)
    
    def process_request(self, state: State) -> Dict[str, Any]:
        """Process user request and return response (non-streaming)"""
        # Get and execute tools
        granny_tools = self._get_tools_for_request(state)
        if granny_tools:
            state = execute_intelligent_tools(state, granny_tools, self.agent_id)
        
        # Generate dynamic tools context for the agent prompt
        tools_context = get_agent_tools_context(granny_tools) if granny_tools else ""
        
        # Build system prompt
        system_content = self.get_system_prompt()
        if tools_context:
            system_content += f"\n\n{tools_context}"
        
        system = SystemMessage(content=system_content)
        
        # Build final prompt
        final_prompt = self._build_prompt(state, tools_context)
        
        # Generate response
        result = self.llm.invoke([system, HumanMessage(content=final_prompt)])
        
        # Update state with generic method
        output_text = str(result.content) if result.content else ""
        state.set_agent_output(self.agent_id, output_text, {
            "execution_time": 0,  # Could track this
            "tools_used": [tool.name for tool in granny_tools],
            "confidence": 1.0
        })
        
        return {
            "output": output_text,
            "agent_id": self.agent_id,
            "tools_used": [tool.name for tool in granny_tools]
        }
    
    def process_request_stream(self, state: State) -> Generator[str, None, None]:
        """Process user request and yield streaming response"""
        # Get and execute tools
        granny_tools = self._get_tools_for_request(state)
        if granny_tools:
            state = execute_intelligent_tools(state, granny_tools, self.agent_id)
        
        # Generate dynamic tools context for the agent prompt
        tools_context = get_agent_tools_context(granny_tools) if granny_tools else ""
        
        # Build system prompt
        system_content = self.get_system_prompt()
        if tools_context:
            system_content += f"\n\n{tools_context}"
        
        system = SystemMessage(content=system_content)
        
        # Build final prompt
        final_prompt = self._build_prompt(state, tools_context)
        
        # Stream the response
        full_response = ""
        for chunk in self.llm.stream([system, HumanMessage(content=final_prompt)]):
            if hasattr(chunk, 'content') and chunk.content:
                content_str = str(chunk.content)
                full_response += content_str
                # Add small delay for testing streaming
                import time
                time.sleep(0.05)  # 50ms delay between chunks
                yield content_str
        
        # Update state after streaming is complete with generic method
        state.set_agent_output(self.agent_id, full_response, {
            "execution_time": 0,  # Could track this
            "tools_used": [tool.name for tool in granny_tools],
            "confidence": 1.0,
            "streaming": True
        })


# Backward compatibility functions (deprecated)
def create_granny_response_stream(state: State) -> Generator[str, None, None]:
    """Deprecated: Use GrannyAgent.process_request_stream() instead"""
    agent = GrannyAgent("granny")
    yield from agent.process_request_stream(state)


def create_granny_response(state: State) -> dict:
    """Deprecated: Use GrannyAgent.process_request() instead"""
    agent = GrannyAgent("granny")
    result = agent.process_request(state)
    
    # Return old format for backward compatibility
    return {
        "granny_output": result["output"],
        "previous_agent_output": result["output"],
        "current_agent_id": "granny"
    }


