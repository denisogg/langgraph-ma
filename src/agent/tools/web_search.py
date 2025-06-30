from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()
client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def run_tool(query: str) -> str:
    try:
        result = client.search(query=query, max_results=3)
        if result and "results" in result:
            return "\n".join([r["content"] for r in result["results"]])
        return "No useful results found."
    except Exception as e:
        return f"Tool error: {str(e)}"
