#!/usr/bin/env python3

# Test the new LLM-based query generation
import sys
import os
sys.path.append('backend/src')

from agent.tools.tool_config import _generate_web_search_query

def test_llm_query_generation():
    test_cases = [
        # Weather queries
        "i would like to hear a story about the weather in halkidiki today, 1 of july, told by my grandma",
        "what's the weather in London today?",
        
        # News queries  
        "tell me about current news in Paris",
        "latest developments in AI technology",
        
        # Price/shopping queries
        "how much does a car cost in Germany?",
        "iPhone 15 price in Romania",
        
        # General information queries
        "best restaurants in Tokyo",
        "how to learn Python programming",
        "stock market performance today",
        "climate change impact on polar bears",
        
        # Complex queries
        "compare housing prices between New York and San Francisco",
        "what are the side effects of taking vitamin D supplements?",
        "top universities for computer science in Europe"
    ]
    
    print("🤖 Testing LLM-Based Query Generation\n" + "="*60)
    print("This uses OpenAI GPT to intelligently extract search terms from ANY query type")
    print("="*60)
    
    for i, user_input in enumerate(test_cases, 1):
        print(f"\n{i:2d}. USER INPUT: '{user_input}'")
        
        # Generate search query using LLM
        search_query = _generate_web_search_query(user_input)
        print(f"    🔎 SEARCH QUERY: '{search_query}'")
        print("    " + "-" * 50)

if __name__ == "__main__":
    print("⚠️  Note: Requires OPENAI_API_KEY environment variable")
    print("If not available, will fallback to simple word extraction\n")
    test_llm_query_generation() 