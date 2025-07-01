# parody_creator/agent.py
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from dotenv import load_dotenv
from typing import Generator, List
from ..state import State
from ..tools.tool_config import ToolConfig
from ..tools.tool_executor import get_agent_tools_context, execute_intelligent_tools

load_dotenv()

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=1.2, streaming=True)

def create_parody(state: State) -> dict:
    # Get parody creator's tools from the current flow
    parody_tools = []
    if state.agent_flow:
        for agent_config in state.agent_flow:
            if agent_config["id"] == "parody_creator" and "tools" in agent_config:
                parody_tools = [
                    ToolConfig(name=tool["name"], option=tool.get("option"))
                    if isinstance(tool, dict) else ToolConfig(name=tool)
                    for tool in agent_config["tools"]
                ]
                break
    
    # Execute tools intelligently if available
    if parody_tools:
        state = execute_intelligent_tools(state, parody_tools, "parody_creator")
    
    # Get context including tool outputs and previous agent outputs
    context = state.get_context_for_agent("parody_creator")
    
    # Generate dynamic tools context for the agent prompt
    tools_context = get_agent_tools_context(parody_tools) if parody_tools else ""
    
    convo = "\n".join(f"{msg.sender}: {msg.text}" for msg in state.history)
    
    # Dynamic system prompt with tool awareness
    system_content = """You are a parody creator who takes input and creates humorous, satirical, or playful versions of it. 
You are creative and entertaining while maintaining good taste and avoiding offensive content.

When you have tools available, you are aware of their capabilities and will use them strategically to enhance your parody creation.
The system will automatically analyze your user's needs and provide you with relevant tool results when needed.
Your job is to integrate any tool results naturally into your humorous content.

Remember: You are first and foremost a comedian and satirist, but now you can access additional information to make your parodies more topical and engaging."""

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
    prompt_parts.append(f"\nContext to create parody from:\n{context}")
    
    if state.tool_outputs:
        prompt_parts.append(
            "\nInstructions: Use the tool results above to enhance your parody. "
            "Integrate the information naturally into your humorous content. "
            "If the tools provided useful information, incorporate it into your satirical take. "
            "If the tool results weren't helpful, create an entertaining parody based on the available context anyway."
        )
    
    prompt_parts.append("\nCreate a humorous, satirical, or playful parody based on the provided context and any tool results.")

    final_prompt = "\n".join(prompt_parts)

    result = llm.invoke([system, HumanMessage(content=final_prompt)])
    
    # Update state with this agent's output for the next agent  
    return {
        "parody_output": result.content,
        "previous_agent_output": result.content,
        "current_agent_id": "parody_creator"
    }

def create_parody_response_stream(state: State) -> Generator[str, None, None]:
    """Stream the parody creator response token by token"""
    # Get parody creator's tools from the current flow
    parody_tools = []
    if state.agent_flow:
        for agent_config in state.agent_flow:
            if agent_config["id"] == "parody_creator" and "tools" in agent_config:
                parody_tools = [
                    ToolConfig(name=tool["name"], option=tool.get("option"))
                    if isinstance(tool, dict) else ToolConfig(name=tool)
                    for tool in agent_config["tools"]
                ]
                break
    
    # Execute tools intelligently if available
    if parody_tools:
        state = execute_intelligent_tools(state, parody_tools, "parody_creator")
    
    # Get context including tool outputs and previous agent outputs
    context = state.get_context_for_agent("parody_creator")
    
    # Generate dynamic tools context for the agent prompt
    tools_context = get_agent_tools_context(parody_tools) if parody_tools else ""
    
    convo = "\n".join(f"{msg.sender}: {msg.text}" for msg in state.history)
    
    # Dynamic system prompt with tool awareness
    system_content = """You are a witty satirist who creates humorous parodies and clever commentary.
You excel at finding the absurd in the mundane and making people laugh through clever observations.

When you have tools available, you are aware of their capabilities and will use them strategically to enhance your comedic material.
The system will automatically analyze your user's needs and provide you with relevant tool results when needed.
Your job is to integrate any tool results into your comedic commentary in unexpected and funny ways.

Remember: You are the court jester of the digital age, but now you can access real information to make your humor more cutting and relevant."""

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
            "\nInstructions: Use the tool results above to enhance your parody. "
            "Integrate the information naturally into your humorous content. "
            "If the tools provided useful information, incorporate it into your satirical take. "
            "If the tool results weren't helpful, create an entertaining parody based on the available context anyway."
        )

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
    state.parody_output = full_response
    state.previous_agent_output = full_response
    state.current_agent_id = "parody_creator"
