#!/usr/bin/env python3
"""
Test script for the Hybrid NLP Query Generation System

This demonstrates how the system combines:
1. spaCy NER for entity extraction
2. LLM for intelligent query composition  
3. Multiple fallback layers for robustness
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

sys.path.append('backend/src')

def test_hybrid_system():
    """Test the complete hybrid NLP system"""
    
    # Import our hybrid functions
    try:
        from agent.tools.tool_config import (
            _generate_web_search_query,
            _extract_entities_with_spacy, 
            _hybrid_query_generation,
            _compose_query_from_entities
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the project root directory")
        return

    # Test cases covering various domains and complexities
    test_cases = [
        # Weather queries (original issue)
        "i would like to hear a story about the weather in halkidiki today, 1 of july, told by my grandma",
        "what's the current weather in London?",
        "weather forecast for Tokyo tomorrow",
        
        # News and current events
        "tell me about latest news in Paris",
        "recent developments in artificial intelligence",
        "what's happening in Ukraine today",
        
        # Shopping and pricing
        "how much does iPhone 15 cost in Germany?",
        "Tesla Model 3 price in Romania",
        "best laptop deals this week",
        
        # Travel and local information  
        "best restaurants in Barcelona",
        "things to do in Amsterdam",
        "hotels near Eiffel Tower",
        
        # Learning and how-to
        "how to learn Python programming",
        "JavaScript tutorial for beginners",
        "what is machine learning",
        
        # Complex multi-entity queries
        "compare house prices between San Francisco and Austin Texas",
        "side effects of vitamin D supplements for elderly people",
        "top computer science universities in Germany and Netherlands"
    ]
    
    print("🤖 HYBRID NLP QUERY GENERATION TEST")
    print("=" * 70)
    print("🔬 spaCy NER + 🧠 LLM Generation + 🛡️ Multi-layer Fallbacks")
    print("=" * 70)
    
    # Test each query
    for i, user_input in enumerate(test_cases, 1):
        print(f"\n📝 TEST {i:2d}: {user_input}")
        print("-" * 60)
        
        # Step 1: Entity extraction with spaCy
        try:
            entities = _extract_entities_with_spacy(user_input)
            print("🔬 EXTRACTED ENTITIES:")
            for entity_type, values in entities.items():
                if values:
                    print(f"   • {entity_type}: {values}")
            
            if not any(entities.values()):
                print("   • No specific entities detected")
        except Exception as e:
            print(f"   ❌ Entity extraction failed: {e}")
            entities = {}
        
        # Step 2: Generate final query
        try:
            final_query = _generate_web_search_query(user_input)
            print(f"🎯 FINAL QUERY: '{final_query}'")
            
            # Show which generation method was likely used
            if len(final_query.split()) <= 6 and any(entities.values()):
                print("   💡 Method: Likely spaCy NER + LLM generation")
            elif any(entities.values()):
                print("   💡 Method: Likely spaCy NER + rule-based fallback") 
            else:
                print("   💡 Method: Likely simple word extraction fallback")
                
        except Exception as e:
            print(f"   ❌ Query generation failed: {e}")
        
        print()

def test_individual_components():
    """Test individual components of the hybrid system"""
    
    print("\n🔧 COMPONENT TESTING")
    print("=" * 50)
    
    test_query = "weather in Halkidiki today, July 1st"
    
    try:
        from agent.tools.tool_config import (
            _extract_entities_with_spacy,
            _compose_query_from_entities
        )
        
        print(f"🧪 Test Query: '{test_query}'")
        
        # Test spaCy extraction
        print("\n1️⃣ spaCy Entity Extraction:")
        entities = _extract_entities_with_spacy(test_query)
        for entity_type, values in entities.items():
            if values:
                print(f"   {entity_type}: {values}")
        
        # Test rule-based composition
        print("\n2️⃣ Rule-based Query Composition:")
        rule_query = _compose_query_from_entities(test_query, entities)
        print(f"   Result: '{rule_query}'")
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")

def check_dependencies():
    """Check if required dependencies are available"""
    
    print("\n🔍 DEPENDENCY CHECK")
    print("=" * 30)
    
    # Check spaCy
    try:
        import spacy
        print("✅ spaCy installed")
        
        try:
            nlp = spacy.load("en_core_web_sm")
            print("✅ English model (en_core_web_sm) available")
        except OSError:
            print("❌ English model missing")
            print("   Install with: python -m spacy download en_core_web_sm")
    except ImportError:
        print("❌ spaCy not installed")
        print("   Install with: pip install spacy")
    
    # Check OpenAI
    try:
        import openai
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            print("✅ OpenAI library and API key available")
        else:
            print("⚠️  OpenAI library installed but no API key found")
            print("   Set OPENAI_API_KEY environment variable")
    except ImportError:
        print("❌ OpenAI library not installed")
        print("   Install with: pip install openai")

if __name__ == "__main__":
    print("🚀 HYBRID NLP QUERY GENERATION SYSTEM TEST")
    print("⭐ Combining spaCy NER + LLM Intelligence + Robust Fallbacks\n")
    
    # Check dependencies first
    check_dependencies()
    
    # Test individual components
    test_individual_components()
    
    # Test full system
    test_hybrid_system()
    
    print("\n🎉 Test completed!")
    print("\n💡 To set up the system:")
    print("   1. pip install spacy openai")
    print("   2. python -m spacy download en_core_web_sm")
    print("   3. Set OPENAI_API_KEY environment variable")
    print("   4. The system will gracefully fallback if any component is missing!") 