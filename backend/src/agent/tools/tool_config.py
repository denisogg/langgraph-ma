from typing import Optional, Dict, List, Any
from pydantic import BaseModel
import json
import os
import re
from pathlib import Path

class ToolConfig(BaseModel):
    name: str
    option: Optional[str] = None

class ToolMetadata(BaseModel):
    name: str
    description: str
    use_cases: List[str]
    input_format: str
    confidence_threshold: float = 0.7
    fallback_behavior: str = "inform_user"

class KnowledgebaseFile(BaseModel):
    description: str
    keywords: List[str]  # Keep for backward compatibility but won't use
    content_type: str

# Romanian stop words and common words to ignore
ROMANIAN_STOP_WORDS = {
    "si", "sau", "dar", "ca", "de", "la", "cu", "pe", "in", "din", "pentru", "despre",
    "cum", "ce", "cine", "unde", "cand", "care", "ce", "mai", "foarte", "prea", "destul",
    "un", "o", "ai", "ale", "lui", "ei", "lor", "meu", "tau", "sau", "nostru", "vostru",
    "este", "sunt", "era", "eram", "fi", "fost", "fiind", "va", "vor", "ar", "as", "am",
    "bunico", "bunica", "dragul", "draga", "copil", "copile", "te", "rog", "poti", "vrei"
}

def calculate_semantic_similarity(user_input: str, description: str) -> float:
    """Calculate semantic similarity between user input and description using NLP techniques"""
    
    # Normalize and clean text
    user_clean = _normalize_text(user_input)
    desc_clean = _normalize_text(description)
    
    # Extract meaningful words
    user_words = _extract_meaningful_words(user_clean)
    desc_words = _extract_meaningful_words(desc_clean)
    
    if not user_words or not desc_words:
        return 0.0
    
    # 1. Exact word overlap score
    exact_matches = len(set(user_words).intersection(set(desc_words)))
    exact_score = exact_matches / len(user_words) if user_words else 0
    
    # 2. Partial word overlap (for Romanian inflections)
    partial_score = _calculate_partial_overlap(user_words, desc_words)
    
    # 3. Semantic context score (food-related, cooking-related, etc.)
    context_score = _calculate_context_similarity(user_words, desc_words)
    
    # 4. Question type matching
    question_score = _calculate_question_type_match(user_input, description)
    
    # Weighted combination
    final_score = (
        exact_score * 0.4 +          # 40% for exact matches
        partial_score * 0.25 +       # 25% for partial matches  
        context_score * 0.25 +       # 25% for semantic context
        question_score * 0.1         # 10% for question type
    )
    
    return min(final_score, 1.0)

def _normalize_text(text: str) -> str:
    """Normalize Romanian text for better matching"""
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation except hyphens
    text = re.sub(r'[^\w\s\-]', ' ', text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    return text

def _extract_meaningful_words(text: str) -> List[str]:
    """Extract meaningful words, removing stop words and short words"""
    words = text.split()
    
    meaningful = []
    for word in words:
        # Skip stop words, very short words, and numbers
        if (len(word) > 2 and 
            word not in ROMANIAN_STOP_WORDS and 
            not word.isdigit()):
            meaningful.append(word)
    
    return meaningful

def _calculate_partial_overlap(user_words: List[str], desc_words: List[str]) -> float:
    """Calculate partial word overlap for Romanian inflections"""
    partial_matches = 0
    
    for user_word in user_words:
        for desc_word in desc_words:
            # Check if words share a common root (at least 4 characters)
            if len(user_word) >= 4 and len(desc_word) >= 4:
                # Check for common prefix (Romanian root)
                common_length = 0
                for i in range(min(len(user_word), len(desc_word))):
                    if user_word[i] == desc_word[i]:
                        common_length += 1
                    else:
                        break
                
                if common_length >= 4:  # At least 4 characters match
                    partial_matches += 0.7  # Partial match worth less than exact
                    break
    
    return partial_matches / len(user_words) if user_words else 0

def _calculate_context_similarity(user_words: List[str], desc_words: List[str]) -> float:
    """Calculate semantic context similarity"""
    
    # Define semantic contexts for Romanian
    contexts = {
        'cooking': ['reteta', 'gatit', 'bucatarie', 'mancare', 'ingrediente', 'preparat', 'copt', 'fiert'],
        'food': ['ciorba', 'supa', 'fel', 'masa', 'gustos', 'savuros', 'delicios'],
        'instructions': ['cum', 'mod', 'metoda', 'pas', 'etapa', 'procedura'],
        'location': ['radauteana', 'romanesc', 'traditional', 'local', 'regional']
    }
    
    user_contexts = set()
    desc_contexts = set()
    
    # Identify contexts in user input
    for context_name, context_words in contexts.items():
        if any(word in user_words for word in context_words):
            user_contexts.add(context_name)
        if any(word in desc_words for word in context_words):
            desc_contexts.add(context_name)
    
    # Calculate context overlap
    if user_contexts and desc_contexts:
        context_overlap = len(user_contexts.intersection(desc_contexts))
        return context_overlap / len(user_contexts.union(desc_contexts))
    
    return 0.0

def _calculate_question_type_match(user_input: str, description: str) -> float:
    """Calculate how well the question type matches the content type"""
    user_lower = user_input.lower()
    desc_lower = description.lower()
    
    score = 0.0
    
    # "How" questions match well with recipes/instructions
    if ('cum' in user_lower or 'how' in user_lower) and 'reteta' in desc_lower:
        score += 0.8
    
    # "What" questions match well with descriptions
    if ('ce' in user_lower or 'what' in user_lower) and any(word in desc_lower for word in ['descriere', 'despre']):
        score += 0.6
    
    # Recipe-specific questions
    if any(word in user_lower for word in ['reteta', 'prepara', 'gatit']) and 'reteta' in desc_lower:
        score += 0.9
    
    return min(score, 1.0)

# Tool descriptions and metadata
TOOL_DESCRIPTIONS = {
    "web_search": ToolMetadata(
        name="web_search",
        description="Searches the internet for current information, news, weather, facts, and real-time data. Use this when you need up-to-date information that changes frequently.",
        use_cases=[
            "current weather conditions",
            "recent news and events", 
            "real-time data and statistics",
            "current prices and market info",
            "today's date and time",
            "recent developments in any field",
            "live sports scores",
            "current stock prices"
        ],
        input_format="Generate a specific, focused search query. Extract only the essential search terms from the user's request. Do NOT send the full user request.",
        confidence_threshold=0.8,
        fallback_behavior="inform_user_no_results"
    ),
    "knowledgebase": ToolMetadata(
        name="knowledgebase", 
        description="Accesses specific knowledge files with detailed, curated information. Use this for accessing stored knowledge about specific topics.",
        use_cases=[
            "recipe information and cooking instructions",
            "detailed procedural knowledge",
            "specific domain expertise",
            "stored reference materials"
        ],
        input_format="Ask a specific, direct question about the content you need. Be precise about what information you're looking for.",
        confidence_threshold=0.7,
        fallback_behavior="suggest_alternative_source"
    )
}

def load_knowledgebase_metadata() -> Dict[str, KnowledgebaseFile]:
    """Load metadata about available knowledgebase files"""
    try:
        kb_path = os.path.join(os.path.dirname(__file__), "../../data/knowledgebase.json")
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        metadata = {}
        for key, entry in kb_data.items():
            metadata[key] = KnowledgebaseFile(
                description=entry.get("description", ""),
                keywords=entry.get("keywords", []),
                content_type=entry.get("content_type", "text")
            )
        return metadata
    except Exception as e:
        print(f"Error loading knowledgebase metadata: {e}")
        return {}

def get_tool_description(tool_name: str) -> Optional[ToolMetadata]:
    """Get comprehensive description for a tool"""
    return TOOL_DESCRIPTIONS.get(tool_name)

def get_available_tools_info(tool_names: List[str]) -> Dict[str, Any]:
    """Get formatted information about available tools for agent prompts"""
    tools_info = {}
    for tool_name in tool_names:
        tool_desc = get_tool_description(tool_name)
        if tool_desc:
            tools_info[tool_name] = {
                "description": tool_desc.description,
                "use_cases": tool_desc.use_cases,
                "input_format": tool_desc.input_format
            }
            
            # Add knowledgebase specific info
            if tool_name == "knowledgebase":
                kb_metadata = load_knowledgebase_metadata()
                tools_info[tool_name]["available_files"] = kb_metadata
                
    return tools_info

def should_use_tool(user_input: str, tool_name: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Determine if a tool should be used based on user input and context"""
    tool_desc = get_tool_description(tool_name)
    if not tool_desc:
        return {"should_use": False, "reason": "Tool not found"}
    
    user_lower = user_input.lower()
    
    # Check if any use cases match the user input
    relevance_score = 0
    matching_cases = []
    
    for use_case in tool_desc.use_cases:
        if any(keyword in user_lower for keyword in use_case.split()):
            relevance_score += 1
            matching_cases.append(use_case)
    
    # Additional heuristics
    if tool_name == "web_search":
        web_indicators = ["today", "current", "now", "latest", "recent", "weather", "news", 
                         "azi", "acum", "curent", "vremea", "vreme", "stiri", "noutati", 
                         "recent", "ultima", "ultimele", "pret", "preturi", "cost"]
        if any(indicator in user_lower for indicator in web_indicators):
            relevance_score += 2
            
    elif tool_name == "knowledgebase":
        kb_metadata = load_knowledgebase_metadata()
        for kb_key, kb_info in kb_metadata.items():
            # Use NLP-based semantic similarity on description only
            similarity_score = calculate_semantic_similarity(user_input, kb_info.description)
            
            if similarity_score > 0.3:  # Minimum threshold for relevance
                relevance_score += similarity_score * 3  # Scale up for final scoring
                matching_cases.append(f"Knowledge about {kb_key} (similarity: {similarity_score:.2f})")
    
    should_use = relevance_score > 0
    confidence = min(relevance_score / 3.0, 1.0)  # Normalize to 0-1
    
    return {
        "should_use": should_use,
        "confidence": confidence,
        "matching_cases": matching_cases,
        "reason": f"Relevance score: {relevance_score}, Matching cases: {matching_cases}" if should_use else "No relevant use cases found"
    }

def generate_tool_query(user_input: str, tool_name: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Generate a specific, focused query for a tool based on user input"""
    
    if tool_name == "web_search":
        return _generate_web_search_query(user_input, context)
    elif tool_name == "knowledgebase":
        return _generate_knowledgebase_query(user_input, context)
    else:
        return user_input

def _generate_web_search_query(user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Generate focused web search query using hybrid NLP approach"""
    
    # Step 1: Extract entities using spaCy NER
    entities = _extract_entities_with_spacy(user_input)
    
    # Step 2: Use LLM to intelligently compose query from entities and intent
    return _hybrid_query_generation(user_input, entities, "web_search")

def _extract_entities_with_spacy(text: str) -> Dict[str, List[str]]:
    """Extract entities using spaCy Named Entity Recognition with improved classification"""
    try:
        import spacy
        
        # Try to load spaCy model
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
            return _fallback_entity_extraction(text)
        
        doc = nlp(text)
        
        entities = {
            "locations": [],
            "dates": [],
            "people": [],
            "organizations": [],
            "money": [],
            "products": [],
            "events": [],
            "key_concepts": []
        }
        
        # Known location names that might be misclassified
        known_locations = {
            "halkidiki", "paris", "london", "berlin", "rome", "madrid", "athens", 
            "bucharest", "romania", "greece", "france", "germany", "italy", "spain"
        }
        
        # Extract named entities with improved classification
        for ent in doc.ents:
            entity_text = ent.text.strip()
            entity_lower = entity_text.lower()
            
            # Force location classification for known places
            if entity_lower in known_locations:
                entities["locations"].append(entity_text)
            elif ent.label_ in ["GPE", "LOC"]:  # Geopolitical entities, locations
                entities["locations"].append(entity_text)
            elif ent.label_ in ["DATE", "TIME"]:  # Dates and times
                entities["dates"].append(entity_text)
            elif ent.label_ == "PERSON":  # People
                entities["people"].append(entity_text)
            elif ent.label_ == "ORG":  # Organizations (but not if it's a known location)
                if entity_lower not in known_locations:
                    entities["organizations"].append(entity_text)
                else:
                    entities["locations"].append(entity_text)
            elif ent.label_ == "MONEY":  # Money amounts
                entities["money"].append(entity_text)
            elif ent.label_ in ["PRODUCT", "WORK_OF_ART"]:  # Products, works of art
                entities["products"].append(entity_text)
            elif ent.label_ == "EVENT":  # Events
                entities["events"].append(entity_text)
        
        # Extract additional context using dependency parsing
        important_nouns = []
        for token in doc:
            # Get important nouns that aren't stop words
            if (token.pos_ in ["NOUN", "PROPN"] and 
                not token.is_stop and 
                len(token.text) > 2 and
                token.text.lower() not in [e.lower() for sublist in entities.values() for e in sublist]):
                important_nouns.append(token.text)
        
        entities["key_concepts"] = important_nouns[:5]  # Limit to top 5
        
        # Remove duplicates while preserving order
        for key in entities:
            entities[key] = list(dict.fromkeys(entities[key]))
        
        return entities
        
    except ImportError:
        print("spaCy not available. Install with: pip install spacy")
        return _fallback_entity_extraction(text)
    except Exception as e:
        print(f"spaCy entity extraction failed: {e}")
        return _fallback_entity_extraction(text)

def _fallback_entity_extraction(text: str) -> Dict[str, List[str]]:
    """Simple fallback entity extraction when spaCy is not available"""
    words = text.split()
    entities = {
        "locations": [],
        "dates": [],
        "people": [],
        "organizations": [],
        "money": [],
        "products": [],
        "events": [],
        "key_concepts": []
    }
    
    # Basic pattern matching for common entities
    location_indicators = ["in", "at", "from", "to", "near"]
    date_patterns = ["today", "tomorrow", "yesterday", "monday", "tuesday", "wednesday", 
                    "thursday", "friday", "saturday", "sunday"]
    
    for i, word in enumerate(words):
        word_clean = word.strip(".,!?").lower()
        
        # Detect potential locations (capitalized words after location indicators)
        if (i > 0 and words[i-1].lower() in location_indicators and 
            word[0].isupper() and len(word) > 2):
            entities["locations"].append(word_clean)
        
        # Detect dates
        if word_clean in date_patterns:
            entities["dates"].append(word_clean)
        
        # Detect key concepts (longer words that aren't common)
        if (len(word_clean) > 3 and 
            word_clean not in ["would", "like", "tell", "about", "what", "how", "where", "when"]):
            entities["key_concepts"].append(word_clean)
    
    # Limit key concepts
    entities["key_concepts"] = entities["key_concepts"][:5]
    
    return entities

def _hybrid_query_generation(user_input: str, entities: Dict[str, List[str]], tool_type: str) -> str:
    """Hybrid approach: Use LLM with extracted entities for intelligent query generation"""
    import os
    
    # Try LLM-based generation with entity context
    try:
        from openai import OpenAI
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return _compose_query_from_entities(user_input, entities)
        
        client = OpenAI(api_key=api_key)
        
        # Build entity context for the LLM
        entity_context = ""
        for entity_type, entity_list in entities.items():
            if entity_list:
                entity_context += f"- {entity_type}: {', '.join(entity_list)}\n"
        
        prompt = f"""You are an expert at creating focused search queries.

User request: "{user_input}"

Extracted entities:
{entity_context if entity_context else "- No specific entities detected"}

Create a concise search query (3-6 words) that captures:
1. The core intent (what they want to know)
2. Key entities (especially locations, dates, products)
3. Search context (current events, pricing, information)

Examples:
- "weather in Halkidiki today" → "weather Halkidiki today"
- "best restaurants in Tokyo" → "best restaurants Tokyo"
- "iPhone price Germany" → "iPhone price Germany"
- "AI technology developments" → "AI technology developments"

Return ONLY the search query:"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=15,
            temperature=0.1
        )
        
        query = response.choices[0].message.content
        if query:
            query = query.strip()
        
        # Validate and return
        if query and 2 <= len(query.split()) <= 8:
            return query
        else:
            return _compose_query_from_entities(user_input, entities)
            
    except Exception as e:
        print(f"LLM query generation failed: {e}")
        return _compose_query_from_entities(user_input, entities)

def _compose_query_from_entities(user_input: str, entities: Dict[str, List[str]]) -> str:
    """Compose search query using extracted entities with better prioritization"""
    query_parts = []
    user_lower = user_input.lower()
    
    # Detect intent keywords first (priority order matters)
    intent_keywords = {
        "weather": ["weather", "forecast", "temperature", "climate", "today"],
        "news": ["news", "latest", "update", "happening", "current"],
        "price": ["price", "cost", "buy", "purchase", "expensive", "cheap"],
        "restaurant": ["restaurant", "food", "eat", "dining"],
        "travel": ["travel", "visit", "trip", "vacation"],
        "learn": ["learn", "how", "tutorial", "guide"]
    }
    
    # Add the most specific intent first
    primary_intent = None
    for intent, keywords in intent_keywords.items():
        if any(keyword in user_lower for keyword in keywords):
            primary_intent = intent
            query_parts.append(intent)
            break
    
    # Add entities in logical priority order
    # 1. Locations are often most important for search queries
    if entities.get("locations"):
        query_parts.extend(entities["locations"][:1])  # Take only the first/most important location
    
    # 2. Add temporal information (today, dates)
    if entities.get("dates"):
        # Prioritize "today" and current time references
        dates = entities["dates"]
        today_terms = [d for d in dates if "today" in d.lower()]
        if today_terms:
            query_parts.extend(today_terms[:1])
        else:
            query_parts.extend(dates[:1])
    
    # 3. Add products/things if relevant
    if entities.get("products") and len(query_parts) < 4:
        query_parts.extend(entities["products"][:1])
    
    # 4. Add key concepts only if we need more specificity
    if len(query_parts) < 3 and entities.get("key_concepts"):
        # Filter out concepts that are too generic
        useful_concepts = []
        generic_terms = {"story", "tell", "about", "like", "would", "make", "create"}
        
        for concept in entities["key_concepts"][:3]:
            if concept.lower() not in generic_terms:
                useful_concepts.append(concept)
        
        query_parts.extend(useful_concepts[:2])
    
    # If still not enough, carefully extract important words
    if len(query_parts) < 2:
        important_words = []
        stop_words = {"i", "would", "like", "to", "can", "you", "please", "tell", "me", "about", 
                      "the", "a", "an", "and", "or", "but", "in", "on", "at", "of", "for", "with"}
        
        for word in user_input.split():
            clean_word = word.strip(".,!?").lower()
            if (len(clean_word) > 2 and 
                clean_word not in stop_words and 
                not clean_word.isdigit() and
                clean_word not in [part.lower() for part in query_parts]):
                important_words.append(clean_word)
        
        query_parts.extend(important_words[:4-len(query_parts)])
    
    # Clean up and return
    final_query = " ".join(query_parts[:5])  # Limit to 5 words max for better search results
    return final_query if final_query.strip() else " ".join(user_input.split()[:3])  # Fallback

def _generate_knowledgebase_query(user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Generate focused knowledgebase query using NLP-based similarity"""
    kb_metadata = load_knowledgebase_metadata()
    
    # Find the most relevant knowledge base using NLP similarity
    best_match = None
    best_score = 0.0
    
    for kb_key, kb_info in kb_metadata.items():
        # Calculate semantic similarity between user input and description
        similarity_score = calculate_semantic_similarity(user_input, kb_info.description)
        
        if similarity_score > best_score:
            best_score = similarity_score
            best_match = kb_key
    
    if best_match and best_score > 0.3:  # Only if we have a good match
        # Generate specific question about the content
        user_lower = user_input.lower()
        if "how" in user_lower or "cum" in user_lower:
            if "cum" in user_lower:
                question_part = user_input.split('cum')[-1].strip()
                return f"Cum {question_part}" if not question_part.endswith('?') else question_part
            else:
                return f"How to {user_input.split('how')[-1].strip()}?"
        elif "what" in user_lower or "ce" in user_lower:
            if "ce" in user_lower:
                return f"Ce {user_input.split('ce')[-1].strip()}?"
            else:
                return f"What {user_input.split('what')[-1].strip()}?"
        else:
            return f"Information about {user_input}"
    
    return user_input

def generate_dynamic_tools_context(tool_configs: List[ToolConfig]) -> str:
    """Generate dynamic context about available tools for agent prompts"""
    if not tool_configs:
        return ""
    
    context_parts = ["Available Tools:"]
    
    for tool_config in tool_configs:
        tool_name = tool_config.name
        tool_desc = get_tool_description(tool_name)
        
        if tool_desc:
            context_parts.append(f"\n🔧 {tool_name.upper()}:")
            context_parts.append(f"   • Description: {tool_desc.description}")
            context_parts.append(f"   • Use when: {', '.join(tool_desc.use_cases[:3])}...")
            context_parts.append(f"   • Input format: {tool_desc.input_format}")
            
            # Add specific info for knowledgebase
            if tool_name == "knowledgebase":
                kb_metadata = load_knowledgebase_metadata()
                if kb_metadata:
                    context_parts.append("   • Available knowledge:")
                    for kb_key, kb_info in list(kb_metadata.items())[:3]:  # Show first 3
                        keywords_str = ', '.join(kb_info.keywords[:3])
                        context_parts.append(f"     - {kb_key}: {kb_info.description} (keywords: {keywords_str})")
                    if len(kb_metadata) > 3:
                        context_parts.append(f"     - ... and {len(kb_metadata) - 3} more knowledge files")
        else:
            # Fallback for unknown tools
            context_parts.append(f"\n🔧 {tool_name.upper()}: Available but no description found")
    
    context_parts.append(f"\nTool Usage Instructions:")
    context_parts.append("• Only use tools when you genuinely need additional information")
    context_parts.append("• The system will automatically decide which tools to use based on user input")
    context_parts.append("• Tool results will be provided to you - integrate them naturally into your response")
    context_parts.append("• If tool results aren't helpful, acknowledge this and provide your best guidance anyway")
    
    return "\n".join(context_parts)

def get_all_available_tools() -> List[str]:
    """Get list of all available tool names"""
    return list(TOOL_DESCRIPTIONS.keys())

def register_new_tool(tool_name: str, metadata: ToolMetadata):
    """Register a new tool dynamically"""
    TOOL_DESCRIPTIONS[tool_name] = metadata
    print(f"✅ Tool '{tool_name}' registered successfully")

def get_tool_registry_info() -> Dict[str, Dict[str, Any]]:
    """Get complete information about all registered tools"""
    registry_info = {}
    for tool_name, tool_desc in TOOL_DESCRIPTIONS.items():
        registry_info[tool_name] = {
            "name": tool_desc.name,
            "description": tool_desc.description,
            "use_cases": tool_desc.use_cases,
            "input_format": tool_desc.input_format,
            "confidence_threshold": tool_desc.confidence_threshold,
            "fallback_behavior": tool_desc.fallback_behavior
        }
        
        # Add specific metadata for certain tools
        if tool_name == "knowledgebase":
            registry_info[tool_name]["available_files"] = load_knowledgebase_metadata()
    
    return registry_info
