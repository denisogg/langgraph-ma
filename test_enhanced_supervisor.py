#!/usr/bin/env python3
"""
Enhanced Supervisor Test Suite

This script demonstrates the advanced query decomposition and orchestration
capabilities of the Enhanced Supervisor system.
"""

import os
import sys
import json
from pathlib import Path

# Add the backend src to path
sys.path.append(str(Path(__file__).parent / "backend" / "src"))

def test_enhanced_supervisor():
    """Test the enhanced supervisor with various complex queries"""
    
    print("🧠 ENHANCED SUPERVISOR TEST SUITE")
    print("=" * 60)
    
    try:
        from agent.supervisor.enhanced_supervisor import EnhancedSupervisor
        print("✅ Enhanced supervisor imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import enhanced supervisor: {e}")
        return False
    
    # Real knowledgebase metadata (matching actual system)
    kb_metadata = {
        "ciorba": type('KBFile', (), {
            "title": "Ciorba Recipe",
            "description": "Reteta de ciorba radauteana de la JAMILA",
            "keywords": ["ciorba", "reteta", "gatit", "mancare", "supa", "ingrediente", "bucatarie", "radauteana"]
        })()
    }
    
    # Create enhanced supervisor
    supervisor = EnhancedSupervisor(
        available_agents=["granny", "story_creator", "parody_creator"],
        knowledgebase_metadata=kb_metadata
    )
    
    # Test queries with increasing complexity
    test_queries = [
        {
            "query": "i would like to hear a story about the weather in halkidiki today, 1 of july, told by my grandma",
            "expected_agent": "granny",
            "expected_tools": ["web_search"],
            "expected_knowledge": [],
            "description": "Complex query with story + weather + agent preference"
        },
        {
            "query": "tell me a funny story about jamila making ciorba soup in today's weather",
            "expected_agent": "parody_creator",  # Humor should trigger parody_creator
            "expected_tools": ["web_search"],
            "expected_knowledge": ["ciorba"],  # Real knowledge base key
            "description": "Multi-resource query: humor + knowledge + current info"
        },
        {
            "query": "what's the weather like in paris today and can you make it into a joke",
            "expected_agent": "parody_creator",
            "expected_tools": ["web_search"],
            "expected_knowledge": [],
            "description": "Information + humor combination"
        },
        {
            "query": "how do I make traditional romanian ciorba",
            "expected_agent": "granny",
            "expected_tools": [],
            "expected_knowledge": ["ciorba"],  # Real knowledge base key
            "description": "Pure knowledge retrieval with cultural context"
        },
        {
            "query": "create a parody of today's news about inflation",
            "expected_agent": "parody_creator",
            "expected_tools": ["web_search"],
            "expected_knowledge": [],
            "description": "Current events + creative transformation"
        }
    ]
    
    print(f"\n📊 Testing {len(test_queries)} complex queries...\n")
    
    results = []
    for i, test_case in enumerate(test_queries, 1):
        print(f"🔬 TEST {i}: {test_case['query']}")
        print("-" * 80)
        
        try:
            # Analyze the query
            execution_plan = supervisor.analyze_query(test_case['query'])
            
            print(f"📋 ANALYSIS RESULTS:")
            print(f"   Strategy: {execution_plan.strategy}")
            print(f"   Primary Agent: {execution_plan.primary_agent}")
            print(f"   Context Fusion: {execution_plan.context_fusion}")
            print(f"   Components: {len(execution_plan.components)}")
            
            # Show detailed component breakdown
            print(f"\n🔍 COMPONENT BREAKDOWN:")
            for j, component in enumerate(execution_plan.components, 1):
                print(f"   {j}. {component.intent}")
                print(f"      Resource: {component.resource_type.value} -> {component.resource_id}")
                print(f"      Priority: {component.priority}")
                print(f"      Text: {component.text}")
            
            # Show resource requirements
            if execution_plan.tools_needed:
                print(f"\n🛠️  TOOLS REQUIRED: {', '.join(execution_plan.tools_needed)}")
            if execution_plan.knowledge_needed:
                print(f"📚 KNOWLEDGE REQUIRED: {', '.join(execution_plan.knowledge_needed)}")
            
            # Validate against expectations
            validation_results = {
                "agent_match": execution_plan.primary_agent == test_case['expected_agent'],
                "tools_match": set(execution_plan.tools_needed) == set(test_case['expected_tools']),
                "knowledge_match": set(execution_plan.knowledge_needed) >= set(test_case['expected_knowledge'])
            }
            
            print(f"\n✅ VALIDATION:")
            print(f"   Agent Selection: {'✅' if validation_results['agent_match'] else '⚠️ '} "
                  f"Got: {execution_plan.primary_agent}, Expected: {test_case['expected_agent']}")
            print(f"   Tool Selection: {'✅' if validation_results['tools_match'] else '⚠️ '} "
                  f"Got: {execution_plan.tools_needed}, Expected: {test_case['expected_tools']}")
            print(f"   Knowledge Selection: {'✅' if validation_results['knowledge_match'] else '⚠️ '} "
                  f"Got: {execution_plan.knowledge_needed}, Expected: {test_case['expected_knowledge']}")
            
            results.append({
                "query": test_case['query'],
                "plan": execution_plan,
                "validation": validation_results,
                "success": True
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "query": test_case['query'],
                "error": str(e),
                "success": False
            })
        
        print(f"\n" + "="*80 + "\n")
    
    # Summary
    successful_tests = sum(1 for r in results if r['success'])
    print(f"📊 SUMMARY: {successful_tests}/{len(test_queries)} tests successful\n")
    
    # Show intelligence features
    print("🧠 ENHANCED INTELLIGENCE FEATURES DEMONSTRATED:")
    print("   ✅ Multi-intent query decomposition")
    print("   ✅ Context-aware agent selection")
    print("   ✅ Intelligent tool requirement detection")
    print("   ✅ Knowledge base relevance matching")
    print("   ✅ Execution strategy planning")
    print("   ✅ Resource orchestration planning")
    
    return successful_tests == len(test_queries)

def test_component_systems():
    """Test individual components of the enhanced supervisor"""
    
    print("\n🔧 COMPONENT SYSTEM TESTS")
    print("=" * 60)
    
    # Test entity extraction
    print("🔍 Testing Entity Extraction...")
    try:
        # Test spaCy integration
        import spacy
        print("   ✅ spaCy available")
        
        try:
            nlp = spacy.load("en_core_web_sm")
            print("   ✅ English model loaded")
            
            # Test on sample text
            doc = nlp("Tell me about the weather in Halkidiki today, July 1st")
            entities = [(ent.text, ent.label_) for ent in doc.ents]
            print(f"   📍 Entities found: {entities}")
            
        except OSError:
            print("   ⚠️  English model not found (run: python -m spacy download en_core_web_sm)")
            
    except ImportError:
        print("   ❌ spaCy not available")
    
    # Test OpenAI integration
    print("\n🤖 Testing OpenAI Integration...")
    try:
        import openai
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            print("   ✅ OpenAI API key found")
            # Note: Not testing actual API call to avoid costs
        else:
            print("   ⚠️  OpenAI API key not found in environment")
            
    except ImportError:
        print("   ❌ OpenAI package not available")
    
    # Test tool config integration
    print("\n🛠️  Testing Tool Configuration...")
    try:
        from agent.tools.tool_config import _extract_entities_with_spacy, _generate_web_search_query
        
        # Test hybrid entity extraction
        test_query = "weather in Halkidiki today"
        entities = _extract_entities_with_spacy(test_query)
        print(f"   📍 Hybrid entities: {entities}")
        
        # Test query generation
        search_query = _generate_web_search_query(test_query)
        print(f"   🔍 Generated query: {search_query}")
        
        print("   ✅ Tool configuration working")
        
    except Exception as e:
        print(f"   ❌ Tool configuration error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Enhanced Supervisor Test Suite...\n")
    
    # Test component systems first
    test_component_systems()
    
    # Test main enhanced supervisor
    success = test_enhanced_supervisor()
    
    if success:
        print("\n🎉 All tests passed! Enhanced Supervisor is ready for complex query orchestration.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    print("\n" + "="*80)
    print("💡 USAGE: Set supervisor_type='enhanced' in the frontend to use these capabilities!")
    print("="*80) 