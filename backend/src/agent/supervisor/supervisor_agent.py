from typing import Annotated, Literal
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.graph import MessagesState
from langgraph.types import Command
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# Available agents in your system
AVAILABLE_AGENTS = ["granny", "story_creator", "parody_creator"]

def create_handoff_tool(*, agent_name: str, description: str | None = None):
    """Create a handoff tool for transferring control to a specific agent"""
    name = f"transfer_to_{agent_name}"
    description = description or f"Transfer control to {agent_name} agent."

    @tool(name, description=description)
    def handoff_tool(
        state: Annotated[MessagesState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        tool_message = {
            "role": "tool",
            "content": f"Successfully transferred to {agent_name}",
            "name": name,
            "tool_call_id": tool_call_id,
        }
        return Command(
            goto=agent_name,
            update={**state, "messages": state["messages"] + [tool_message]},
            graph=Command.PARENT,
        )

    return handoff_tool

# Create handoff tools for each agent
transfer_to_granny = create_handoff_tool(
    agent_name="granny",
    description="Transfer to the Romanian grandmother agent for warm, wisdom-filled responses about recipes, family values, and life advice."
)

transfer_to_story_creator = create_handoff_tool(
    agent_name="story_creator", 
    description="Transfer to the creative writing agent for crafting vivid, engaging stories with rich descriptions."
)

transfer_to_parody_creator = create_handoff_tool(
    agent_name="parody_creator",
    description="Transfer to the humor agent for creating funny parodies, satire, or comedic content."
)

def create_supervisor_agent():
    """Create the supervisor agent that coordinates all other agents"""
    
    system_prompt = """You are a supervisor managing a team of specialized AI agents. Your role is to analyze user requests and delegate them to the most appropriate agent(s).

Available agents:
- **granny**: A warm Romanian grandmother who provides wisdom, recipes, family advice, and life lessons
- **story_creator**: A creative writer who crafts vivid, engaging stories with rich descriptions and compelling narratives
- **parody_creator**: A humor specialist who creates funny parodies, satire, and comedic content

Instructions:
1. Analyze the user's request carefully
2. Determine which agent is best suited to handle the request
3. Transfer control to the appropriate agent using the transfer tools
4. You can only transfer to ONE agent at a time
5. Do not attempt to fulfill the request yourself - always delegate to an agent

Examples of routing decisions:
- Recipe requests, family advice, wisdom → granny
- Creative writing, storytelling, narratives → story_creator  
- Humor, parodies, jokes, satire → parody_creator

If a request could fit multiple agents, choose the most specific match."""

    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1)
    
    supervisor = create_react_agent(
        model=llm,
        tools=[transfer_to_granny, transfer_to_story_creator, transfer_to_parody_creator],
        prompt=system_prompt,
        name="supervisor"
    )
    
    return supervisor

def create_task_delegation_handoff_tool(*, agent_name: str, description: str | None = None):
    """Create a handoff tool that allows explicit task delegation with context"""
    name = f"delegate_to_{agent_name}"
    description = description or f"Delegate a specific task to {agent_name} agent."

    @tool(name, description=description)
    def handoff_tool(
        task_description: Annotated[
            str,
            "Clear, detailed description of what the agent should do, including all necessary context and requirements.",
        ],
        state: Annotated[MessagesState, InjectedState],
    ) -> Command:
        # Create a focused task message instead of passing full history
        task_message = {"role": "user", "content": task_description}
        agent_input = {**state, "messages": [task_message]}
        
        return Command(
            goto=agent_name,
            update=agent_input,
            graph=Command.PARENT,
        )

    return handoff_tool

def create_advanced_supervisor_agent():
    """Create an advanced supervisor that provides explicit task delegation"""
    
    delegate_to_granny = create_task_delegation_handoff_tool(
        agent_name="granny",
        description="Delegate a specific task to the Romanian grandmother agent."
    )
    
    delegate_to_story_creator = create_task_delegation_handoff_tool(
        agent_name="story_creator",
        description="Delegate a specific task to the creative writing agent."
    )
    
    delegate_to_parody_creator = create_task_delegation_handoff_tool(
        agent_name="parody_creator", 
        description="Delegate a specific task to the humor/parody agent."
    )
    
    system_prompt = """You are an intelligent supervisor managing a team of specialized AI agents. 

Your role is to:
1. Analyze complex user requests 
2. Break them down into specific, actionable tasks
3. Delegate each task to the most appropriate agent with clear instructions

Available agents:
- **granny**: Romanian grandmother (recipes, family wisdom, traditional advice)
- **story_creator**: Creative writer (stories, narratives, creative content)
- **parody_creator**: Humor specialist (parodies, jokes, satirical content)

When delegating:
- Provide clear, specific task descriptions
- Include all necessary context and requirements  
- Choose the agent whose expertise best matches the task
- Only delegate to ONE agent per user request

You are the coordinator, not the executor. Always delegate rather than attempting to fulfill requests yourself."""

    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1)
    
    supervisor = create_react_agent(
        model=llm,
        tools=[delegate_to_granny, delegate_to_story_creator, delegate_to_parody_creator],
        prompt=system_prompt,
        name="supervisor"
    )
    
    return supervisor 