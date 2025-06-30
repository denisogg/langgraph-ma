#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from agent.tools.tool_config import calculate_semantic_similarity, should_use_tool, _generate_knowledgebase_query

def test_nlp_matching():
    """Test the NLP-based knowledgebase matching"""
    
    # Test description (from our knowledgebase.json)
    description = "Reteta de ciorba radauteana de la JAMILA"
    
    # Test various user inputs
    test_cases = [
        # Direct matches
        "Cum se face ciorba?",
        "Vreau reteta de ciorba",
        "Bunico, cum prepari ciorba radauteana?",
        
        # Partial matches
        "Ce fel de mancare este ciorba?",
        "Spune-mi despre ciorba",
        "Cum gatesc supa?",
        
        # Context matches
        "Vreau sa gatesc ceva traditional",
        "Ce reteta de mancare ai?",
        "Cum se prepara felul asta de mancare?",
        
        # Non-matches
        "Cum e vremea azi?",
        "Spune-mi o poveste",
        "Ce faci tu acum?",
        
        # Edge cases
        "Ciorba este buna?",
        "Jamila face ciorba",
        "Radauteana este din Moldova"
    ]
    
    print("🧠 **NLP-Based Knowledgebase Matching Test**")
    print("=" * 60)
    print(f"📝 **Target Description**: {description}")
    print("=" * 60)
    
    for i, user_input in enumerate(test_cases, 1):
        similarity = calculate_semantic_similarity(user_input, description)
        
        # Test tool detection
        tool_decision = should_use_tool(user_input, "knowledgebase")
        
        # Test query generation
        generated_query = _generate_knowledgebase_query(user_input)
        
        print(f"\n{i:2d}. **Input**: \"{user_input}\"")
        print(f"    📊 **Similarity Score**: {similarity:.3f}")
        print(f"    🔧 **Should Use Tool**: {tool_decision['should_use']}")
        print(f"    🎯 **Confidence**: {tool_decision['confidence']:.3f}")
        print(f"    📝 **Generated Query**: \"{generated_query}\"")
        
        if tool_decision['matching_cases']:
            print(f"    ✅ **Matching Cases**: {tool_decision['matching_cases']}")
        
        # Visual indicator
        if similarity > 0.7:
            print("    🟢 **STRONG MATCH**")
        elif similarity > 0.4:
            print("    🟡 **MODERATE MATCH**")
        elif similarity > 0.2:
            print("    🟠 **WEAK MATCH**")
        else:
            print("    🔴 **NO MATCH**")

def test_semantic_components():
    """Test individual semantic components"""
    
    print("\n\n🔬 **Semantic Component Analysis**")
    print("=" * 60)
    
    description = "Reteta de ciorba radauteana de la JAMILA"
    test_input = "Bunico, cum se face ciorba radauteana?"
    
    from agent.tools.tool_config import _normalize_text, _extract_meaningful_words
    from agent.tools.tool_config import _calculate_partial_overlap, _calculate_context_similarity
    from agent.tools.tool_config import _calculate_question_type_match
    
    # Normalize texts
    user_clean = _normalize_text(test_input)
    desc_clean = _normalize_text(description)
    
    print(f"📥 **Original Input**: {test_input}")
    print(f"🧹 **Normalized Input**: {user_clean}")
    print(f"📥 **Original Description**: {description}")
    print(f"🧹 **Normalized Description**: {desc_clean}")
    
    # Extract meaningful words
    user_words = _extract_meaningful_words(user_clean)
    desc_words = _extract_meaningful_words(desc_clean)
    
    print(f"\n🔤 **User Words**: {user_words}")
    print(f"🔤 **Description Words**: {desc_words}")
    
    # Calculate individual scores
    exact_matches = len(set(user_words).intersection(set(desc_words)))
    exact_score = exact_matches / len(user_words) if user_words else 0
    
    partial_score = _calculate_partial_overlap(user_words, desc_words)
    context_score = _calculate_context_similarity(user_words, desc_words)
    question_score = _calculate_question_type_match(test_input, description)
    
    print(f"\n📊 **Component Scores**:")
    print(f"   🎯 **Exact Matches**: {exact_matches}/{len(user_words)} = {exact_score:.3f}")
    print(f"   🔄 **Partial Overlap**: {partial_score:.3f}")
    print(f"   🧠 **Context Similarity**: {context_score:.3f}")
    print(f"   ❓ **Question Type Match**: {question_score:.3f}")
    
    # Final weighted score
    final_score = (
        exact_score * 0.4 +
        partial_score * 0.25 +
        context_score * 0.25 +
        question_score * 0.1
    )
    
    print(f"\n🏆 **Final Weighted Score**: {final_score:.3f}")

if __name__ == "__main__":
    test_nlp_matching()
    test_semantic_components() 