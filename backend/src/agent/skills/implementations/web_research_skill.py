from typing import Any, Dict
from ..base_skill import BaseSkill


class WebResearchSkill(BaseSkill):
    """Web research capability for agents"""
    
    def get_description(self) -> str:
        return "Searches and analyzes web-based information to provide comprehensive research results"
    
    def execute(self, input_data: Any, **kwargs) -> Any:
        """Execute web research using the actual web search tool"""
        
        query = str(input_data) if input_data else kwargs.get('query', '')
        max_results = self.config.get('max_results', 10)
        search_depth = self.config.get('search_depth', 'standard')
        
        print(f"🎮 CONTROL FLOW: web_research skill has control, processing query: {query[:50]}...")
        
        if not query:
            print(f"🎮 CONTROL FLOW: web_research skill error - no query provided")
            return "No search query provided for web research"
        
        try:
            print(f"🎮 CONTROL FLOW: web_research skill calling web search tool")
            # Import and use the actual web search tool
            from ...tools.web_search import run_tool
            
            # Call the actual web search tool
            search_result = run_tool(query)
            print(f"🎮 CONTROL FLOW: web search tool completed, returning control to web_research skill")
            
            # Structure the result
            research_result = {
                "query": query,
                "search_depth": search_depth,
                "result": search_result,
                "summary": f"Web research conducted for: '{query}'",
                "success": True
            }
            
            print(f"🎮 CONTROL FLOW: web_research skill structured results, preparing to return")
            self._record_execution(research_result)
            return research_result
            
        except Exception as e:
            print(f"🎮 CONTROL FLOW: web_research skill error during web search: {str(e)}")
            error_result = {
                "query": query,
                "error": str(e),
                "summary": f"Web research failed for: '{query}' - {str(e)}",
                "success": False
            }
            self._record_execution(error_result)
            return error_result 