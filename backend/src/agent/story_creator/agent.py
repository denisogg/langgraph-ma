from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from dotenv import load_dotenv
from typing import Generator, List, Dict, Any, Optional
from ..base_agent import BaseAgent
from ..state import State
from ..tools.tool_config import ToolConfig
from ..tools.tool_executor import get_agent_tools_context, execute_intelligent_tools

load_dotenv()


class StoryCreatorAgent(BaseAgent):
    """Creative writer agent for crafting vivid, engaging stories and narratives"""
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config)
        self.llm = ChatOpenAI(
            model=self.model, 
            temperature=self.temperature, 
            streaming=True
        )
    
    def get_name(self) -> str:
        return "Creative Story Writer"
    
    def get_description(self) -> str:
        return "A creative writer who crafts vivid, engaging stories with rich descriptions, interesting characters, and captivating plots"
    
    def get_capabilities(self) -> List[str]:
        return [
            "creative_writing", 
            "storytelling", 
            "narrative_creation", 
            "character_development", 
            "plot_creation",
            "fiction",
            "drama",
            "adventure",
            "romance",
            "fantasy"
        ]
    
    def get_system_prompt(self) -> str:
        return """You are a creative writer who crafts vivid, engaging stories. 
You create compelling narratives with rich descriptions, interesting characters, and captivating plots.

When you have tools available, you are aware of their capabilities and will use them strategically to enhance your storytelling.
The system will automatically analyze your user's needs and provide you with relevant tool results when needed.
Your job is to integrate any tool results naturally into your creative narrative.

Remember: You are first and foremost a storyteller, but now you can access additional information to make your stories more authentic and engaging."""
    
    def get_routing_keywords(self) -> List[str]:
        return [
            "story", "write", "narrative", "tale", "fiction", "creative",
            "character", "plot", "adventure", "drama", "romance", "fantasy",
            "novel", "short story", "scene", "dialogue", "description"
        ]
    
    def _get_tools_for_request(self, state: State) -> List[ToolConfig]:
        """Get tools configured for this agent from the current flow"""
        story_tools = []
        if state.agent_flow:
            for agent_config in state.agent_flow:
                if agent_config["id"] == self.agent_id and "tools" in agent_config:
                    story_tools = [
                        ToolConfig(name=tool["name"], option=tool.get("option"))
                        if isinstance(tool, dict) else ToolConfig(name=tool)
                        for tool in agent_config["tools"]
                    ]
                    break
        return story_tools
    
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
                "\nInstructions: Use the tool results above to enhance your story. "
                "Integrate the information naturally into your creative narrative. "
                "If the tools provided useful information, weave it into your story. "
                "If the tool results weren't helpful, create an engaging story based on the user's request anyway."
            )
        
        prompt_parts.append("\nWrite a short, vivid story based on the provided context and any tool results.")
        
        return "\n".join(prompt_parts)
    
    def process_request(self, state: State) -> Dict[str, Any]:
        """Process user request and return response (non-streaming)"""
        # Get and execute tools
        story_tools = self._get_tools_for_request(state)
        if story_tools:
            state = execute_intelligent_tools(state, story_tools, self.agent_id)
        
        # Generate dynamic tools context for the agent prompt
        tools_context = get_agent_tools_context(story_tools) if story_tools else ""
        
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
            "tools_used": [tool.name for tool in story_tools],
            "confidence": 1.0
        })
        
        return {
            "output": output_text,
            "agent_id": self.agent_id,
            "tools_used": [tool.name for tool in story_tools]
        }
    
    def process_request_stream(self, state: State) -> Generator[str, None, None]:
        """Process user request and yield streaming response"""
        # Get and execute tools
        story_tools = self._get_tools_for_request(state)
        if story_tools:
            state = execute_intelligent_tools(state, story_tools, self.agent_id)
        
        # Generate dynamic tools context for the agent prompt
        tools_context = get_agent_tools_context(story_tools) if story_tools else ""
        
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
            "tools_used": [tool.name for tool in story_tools],
            "confidence": 1.0,
            "streaming": True
        })


# Backward compatibility functions (deprecated)

def create_story_response_stream(state: State) -> Generator[str, None, None]:
    """Stream the story creator response token by token"""
    # Get story creator's tools from the current flow
    story_tools = []
    if state.agent_flow:
        for agent_config in state.agent_flow:
            if agent_config["id"] == "story_creator" and "tools" in agent_config:
                story_tools = [
                    ToolConfig(name=tool["name"], option=tool.get("option"))
                    if isinstance(tool, dict) else ToolConfig(name=tool)
                    for tool in agent_config["tools"]
                ]
                break
    
    # Execute tools intelligently if available
    if story_tools:
        state = execute_intelligent_tools(state, story_tools, "story_creator")
    
    # Get context including tool outputs and previous agent outputs
    context = state.get_context_for_agent("story_creator")
    
    # Generate dynamic tools context for the agent prompt
    tools_context = get_agent_tools_context(story_tools) if story_tools else ""
    
    convo = "\n".join(f"{msg.sender}: {msg.text}" for msg in state.history)
    
    # Dynamic system prompt with tool awareness
    system_content = """You are a creative writer who crafts vivid, engaging stories. 
You create compelling narratives with rich descriptions, interesting characters, and captivating plots.

When you have tools available, you are aware of their capabilities and will use them strategically to enhance your storytelling.
The system will automatically analyze your user's needs and provide you with relevant tool results when needed.
Your job is to integrate any tool results naturally into your creative narrative.

Remember: You are first and foremost a storyteller, but now you can access additional information to make your stories more authentic and engaging."""

    if tools_context:
        system_content += f"\n\n{tools_context}"
    
    system = SystemMessage(content=system_content)
    
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
    prompt_parts.append(f"\nContext to respond to:\n{context}")
    
    if state.tool_outputs:
        prompt_parts.append(
            "\nInstructions: Use the tool results above to enhance your story. "
            "Integrate the information naturally into your creative narrative. "
            "If the tools provided useful information, weave it into your story. "
            "If the tool results weren't helpful, create an engaging story based on the user's request anyway."
        )
    
    prompt_parts.append("\nWrite a short, vivid story based on the provided context and any tool results.")

    final_prompt = "\n".join(prompt_parts)

    # Stream the response
    full_response = ""
    for chunk in llm.stream([system, HumanMessage(content=final_prompt)]):
        if hasattr(chunk, 'content') and chunk.content:
            content_str = str(chunk.content)
            full_response += content_str
            # Add small delay for testing streaming
            import time
            time.sleep(0.05)  # 50ms delay between chunks
            yield content_str
    
    # Update state after streaming is complete
    state.story_output = full_response
    state.previous_agent_output = full_response
    state.current_agent_id = "story_creator"

def create_story(state: State) -> dict:
    # Get story creator's tools from the current flow
    story_tools = []
    if state.agent_flow:
        for agent_config in state.agent_flow:
            if agent_config["id"] == "story_creator" and "tools" in agent_config:
                story_tools = [
                    ToolConfig(name=tool["name"], option=tool.get("option"))
                    if isinstance(tool, dict) else ToolConfig(name=tool)
                    for tool in agent_config["tools"]
                ]
                break
    
    # Execute tools intelligently if available
    if story_tools:
        state = execute_intelligent_tools(state, story_tools, "story_creator")
    
    # Get context including tool outputs and previous agent outputs
    context = state.get_context_for_agent("story_creator")
    
    # Generate dynamic tools context for the agent prompt
    tools_context = get_agent_tools_context(story_tools) if story_tools else ""
    
    convo = "\n".join(f"{msg.sender}: {msg.text}" for msg in state.history)
    
    # Dynamic system prompt with tool awareness
    system_content = """You are a creative writer who crafts vivid, engaging stories. 
You create compelling narratives with rich descriptions, interesting characters, and captivating plots.

When you have tools available, you are aware of their capabilities and will use them strategically to enhance your storytelling.
The system will automatically analyze your user's needs and provide you with relevant tool results when needed.
Your job is to integrate any tool results naturally into your creative narrative.

Remember: You are first and foremost a storyteller, but now you can access additional information to make your stories more authentic and engaging."""

    if tools_context:
        system_content += f"\n\n{tools_context}"
    
    system = SystemMessage(content=system_content)
    
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
    prompt_parts.append(f"\nContext to respond to:\n{context}")
    
    if state.tool_outputs:
        prompt_parts.append(
            "\nInstructions: Use the tool results above to enhance your story. "
            "Integrate the information naturally into your creative narrative. "
            "If the tools provided useful information, weave it into your story. "
            "If the tool results weren't helpful, create an engaging story based on the user's request anyway."
        )
    
    prompt_parts.append("\nWrite a short, vivid story based on the provided context and any tool results.")

    final_prompt = "\n".join(prompt_parts)

    result = llm.invoke([system, HumanMessage(content=final_prompt)])
    
    # Update state with this agent's output for the next agent
    return {
        "story_output": result.content,
        "previous_agent_output": result.content,
        "current_agent_id": "story_creator"
    }