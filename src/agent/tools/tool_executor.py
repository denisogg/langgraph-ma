import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from tavily import TavilyClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.agent.state import State
from src.agent.tools.tool_config import (
    ToolConfig, 
    get_available_tools_info, 
    should_use_tool, 
    generate_tool_query,
    get_tool_description,
    generate_dynamic_tools_context
)
from src.agent.tools.usage_tracker import get_usage_tracker

# Load knowledgebase from disk
KNOWLEDGEBASE_PATH = Path(__file__).parent.parent.parent / "data" / "knowledgebase.json"
with open(KNOWLEDGEBASE_PATH, "r", encoding="utf-8") as f:
    KNOWLEDGEBASE = json.load(f)

# Initialize Tavily client
try:
    api_key = os.getenv("TAVILY_API_KEY")
    if api_key:
        client = TavilyClient(api_key=api_key)
    else:
        client = None
        print("Warning: TAVILY_API_KEY not found in environment variables")
except Exception as e:
    client = None
    print(f"Error initializing Tavily client: {e}")


def get_agent_tools_context(agent_tools: List[ToolConfig]) -> str:
    """Generate dynamic context about available tools for agent prompts"""
    return generate_dynamic_tools_context(agent_tools)


def should_agent_use_tools(user_input: str, available_tools: List[ToolConfig], 
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Determine which tools an agent should use based on the user input"""
    if not available_tools:
        return {"should_use_any": False, "tools_to_use": [], "reasoning": "No tools available"}
    
    tools_analysis = {}
    tools_to_use = []
    
    # Get usage tracker for this session
    tracker = get_usage_tracker()
    
    for tool in available_tools:
        # Check if tool should be used
        usage_decision = should_use_tool(user_input, tool.name, context)
        
        # Check if recently used to avoid redundancy
        if usage_decision["should_use"]:
            # Generate the query that would be sent
            potential_query = generate_tool_query(user_input, tool.name, context)
            
            if tracker.was_recently_used(tool.name, potential_query, hours=1):
                usage_decision["should_use"] = False
                usage_decision["reason"] = "Similar query used recently"
            else:
                tools_to_use.append({
                    "tool": tool,
                    "query": potential_query,
                    "confidence": usage_decision["confidence"],
                    "matching_cases": usage_decision["matching_cases"]
                })
        
        tools_analysis[tool.name] = usage_decision
    
    return {
        "should_use_any": len(tools_to_use) > 0,
        "tools_to_use": tools_to_use,
        "tools_analysis": tools_analysis,
        "reasoning": f"Found {len(tools_to_use)} relevant tools out of {len(available_tools)} available"
    }


def execute_intelligent_tools(state: State, agent_tools: List[ToolConfig], 
                             agent_name: str) -> State:
    """Execute tools intelligently based on user input and agent reasoning"""
    if not agent_tools:
        return state
    
    # Analyze which tools should be used
    tools_decision = should_agent_use_tools(
        state.user_prompt, 
        agent_tools,
        context={"agent_name": agent_name, "conversation_history": getattr(state, "history", [])}
    )
    
    if not tools_decision["should_use_any"]:
        return state
    
    # Execute selected tools
    updated_outputs = state.tool_outputs.copy()
    tracker = get_usage_tracker()
    
    for tool_info in tools_decision["tools_to_use"]:
        tool = tool_info["tool"]
        query = tool_info["query"]
        expected_confidence = tool_info["confidence"]
        
        try:
            # Execute the tool with the generated query
            result = _execute_single_tool(tool.name, query, tool.option)
            
            # Calculate actual confidence based on result
            actual_confidence = tracker.calculate_confidence_score(tool.name, result)
            
            # Record usage
            usage_id = tracker.record_tool_usage(
                tool_name=tool.name,
                query=query,
                result=result,
                confidence_score=actual_confidence,
                success=actual_confidence > 0.4
            )
            
            # Store result with metadata
            tool_output = {
                "result": result,
                "query_used": query,
                "confidence": actual_confidence,
                "usage_id": usage_id,
                "agent": agent_name,
                "matching_cases": tool_info["matching_cases"]
            }
            
            updated_outputs[tool.name] = tool_output
            
            # Check if we should retry with different query
            if actual_confidence < 0.4:
                retry_decision = tracker.should_retry_with_different_query(tool.name, query, result)
                if retry_decision["should_retry"]:
                    # Try one more time with a more general query
                    fallback_query = _generate_fallback_query(query, tool.name)
                    if fallback_query != query:
                        fallback_result = _execute_single_tool(tool.name, fallback_query, tool.option)
                        fallback_confidence = tracker.calculate_confidence_score(tool.name, fallback_result)
                        
                        if fallback_confidence > actual_confidence:
                            # Use the better result
                            tool_output["result"] = fallback_result
                            tool_output["query_used"] = fallback_query
                            tool_output["confidence"] = fallback_confidence
                            tool_output["retry_attempt"] = True
                            
                            updated_outputs[tool.name] = tool_output
            
        except Exception as e:
            error_result = f"Tool execution error: {str(e)}"
            tracker.record_tool_usage(
                tool_name=tool.name,
                query=query,
                result=error_result,
                confidence_score=0.0,
                success=False
            )
            
            updated_outputs[tool.name] = {
                "result": error_result,
                "query_used": query,
                "confidence": 0.0,
                "agent": agent_name,
                "error": True
            }
    
    return state.copy(update={"tool_outputs": updated_outputs})


def _execute_single_tool(tool_name: str, query: str, option: Optional[str] = None) -> str:
    """Execute a single tool with the given query"""
    
    if tool_name == "knowledgebase":
        # Use option if provided, otherwise try to infer from query
        category_key = option
        if not category_key:
            # Try to match query with available categories
            query_lower = query.lower()
            for key in KNOWLEDGEBASE.keys():
                if key.lower() in query_lower:
                    category_key = key
                    break
            
            if not category_key:
                category_key = list(KNOWLEDGEBASE.keys())[0]  # Default to first available
        
        category = KNOWLEDGEBASE.get(category_key)
        if not category:
            return f"Knowledge category '{category_key}' not found"
        
        files_data = category.get("files", {})
        if isinstance(files_data, dict):
            files_data = list(files_data.values())

        entries = []
        for file in files_data:
            desc = file.get("description", "No description")
            body = ""

            if "content" in file:
                body = file["content"]
            elif "path" in file:
                try:
                    full_path = KNOWLEDGEBASE_PATH.parent / file["path"]
                    with open(full_path, "r", encoding="utf-8") as f:
                        body = f.read()
                except Exception as e:
                    body = f"Error loading file: {e}"
            else:
                body = "No content available"

            # Filter content based on query if it's specific
            if len(query.split()) > 1 and query.lower() not in ["information", "details"]:
                # Simple relevance filtering
                query_words = set(query.lower().split())
                body_words = set(body.lower().split())
                if query_words.intersection(body_words):
                    entries.append(f"• {desc}\n{body}")
            else:
                entries.append(f"• {desc}\n{body}")

        return "\n\n".join(entries) if entries else "No relevant information found"

    elif tool_name == "web_search":
        if client is None:
            return "Web search unavailable: TAVILY_API_KEY not configured"
        
        try:
            search_result = client.search(query=query, search_depth="basic", max_results=3)
            
            if not search_result.get("results"):
                return "No search results found"
            
            entries = []
            for r in search_result["results"]:
                title = r.get("title", "No title")
                url = r.get("url", "")
                content = r.get("content", "No content")[:250]  # Truncate
                entries.append(f"• {title}\n{url}\n{content}...")
            
            return "\n\n".join(entries)
            
        except Exception as e:
            return f"Web search failed: {str(e)}"

    else:
        return f"Tool '{tool_name}' not implemented"


def _generate_fallback_query(original_query: str, tool_name: str) -> str:
    """Generate a fallback query if the original one didn't work well"""
    if tool_name == "web_search":
        # Make query more general
        words = original_query.split()
        if len(words) > 2:
            return " ".join(words[:2])  # Use first 2 words
        return original_query
    
    elif tool_name == "knowledgebase":
        # Make query more general
        if "how" in original_query.lower():
            return "instructions"
        elif "what" in original_query.lower():
            return "information"
        return "details"
    
    return original_query


# Legacy function for backward compatibility
def execute_tool(state: State, tool_cfg: ToolConfig):
    """Legacy function - use execute_intelligent_tools instead"""
    result = _execute_single_tool(tool_cfg.name, tool_cfg.option or state.user_prompt, tool_cfg.option)
    
    updated_outputs = state.tool_outputs.copy()
    updated_outputs[tool_cfg.name] = result
    return state.copy(update={"tool_outputs": updated_outputs})
