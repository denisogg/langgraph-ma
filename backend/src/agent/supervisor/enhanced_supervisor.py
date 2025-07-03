"""
Enhanced Supervisor with Intelligent Query Decomposition and Orchestration

This supervisor can:
1. Decompose complex queries into components
2. Map components to appropriate resources (agents/tools/knowledge)  
3. Plan efficient execution strategies
4. Orchestrate multiple resources contextually
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class ResourceType(Enum):
    AGENT = "agent"
    TOOL = "tool" 
    KNOWLEDGE = "knowledge"
    CONTEXT = "context"

@dataclass
class QueryComponent:
    text: str
    intent: str  # story, weather, recipe, etc.
    entities: Dict[str, List[str]]  # locations, dates, people, etc.
    resource_type: ResourceType
    resource_id: str  # granny, web_search, knowledgebase, etc.
    priority: int  # 1=highest, 3=lowest
    dependencies: Optional[List[str]] = None  # depends on other components

@dataclass
class ExecutionPlan:
    components: List[QueryComponent]
    strategy: str  # "sequential", "parallel", "hierarchical"
    primary_agent: str
    tools_needed: List[str]
    knowledge_needed: List[str]
    context_fusion: str  # how to combine outputs
    # Multi-agent execution support
    agent_sequence: List[str]  # Ordered list of agents to execute
    requires_multi_agent: bool = False

class EnhancedSupervisor:
    def __init__(self, available_agents: List[str], knowledgebase_metadata: Dict):
        self.available_agents = available_agents
        self.knowledgebase_metadata = knowledgebase_metadata
        
        # Load agent expertise dynamically from configuration
        self.agent_expertise = self._load_agent_expertise_from_config()

    def _load_agent_expertise_from_config(self) -> Dict[str, Dict[str, Any]]:
        """Load agent expertise mapping dynamically from agents configuration file"""
        agent_expertise = {}
        
        try:
            # Load agents configuration
            config_path = Path(__file__).parent.parent.parent / "data" / "agents_config.json"
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            agents_config = config_data.get("agents", {})
            
            for agent_id, agent_config in agents_config.items():
                if agent_id in self.available_agents:
                    # Extract routing keywords (primary source)
                    keywords = agent_config.get("routing_keywords", [])
                    
                    # Extract capabilities as contexts
                    contexts = agent_config.get("capabilities", [])
                    
                    # Generate personality from description
                    personality = self._extract_personality_from_description(
                        agent_config.get("description", ""),
                        agent_config.get("system_prompt", "")
                    )
                    
                    agent_expertise[agent_id] = {
                        "keywords": keywords,
                        "contexts": contexts,
                        "personality": personality,
                        "description": agent_config.get("description", ""),
                        "name": agent_config.get("name", agent_id)
                    }
            
            # Fallback for agents not in config (should not happen, but defensive)
            for agent_id in self.available_agents:
                if agent_id not in agent_expertise:
                    agent_expertise[agent_id] = {
                        "keywords": [agent_id],
                        "contexts": ["general"],
                        "personality": "helpful, professional",
                        "description": f"General purpose {agent_id} agent",
                        "name": agent_id.replace("_", " ").title()
                    }
            
            print(f"✓ Loaded expertise for {len(agent_expertise)} agents from configuration")
            return agent_expertise
            
        except Exception as e:
            print(f"⚠️ Error loading agent expertise from config: {e}")
            # Fallback to minimal expertise mapping
            fallback_expertise = {}
            for agent_id in self.available_agents:
                fallback_expertise[agent_id] = {
                    "keywords": [agent_id],
                    "contexts": ["general"],
                    "personality": "helpful, professional",
                    "description": f"General purpose {agent_id} agent",
                    "name": agent_id.replace("_", " ").title()
                }
            return fallback_expertise

    def _extract_personality_from_description(self, description: str, system_prompt: str) -> str:
        """Extract personality traits from agent description and system prompt"""
        # Combine description and system prompt for analysis
        text = f"{description} {system_prompt}".lower()
        
        # Define personality trait patterns
        personality_patterns = {
            "warm": ["warm", "caring", "loving", "nurturing", "sweet"],
            "wise": ["wise", "wisdom", "experienced", "knowledgeable", "traditional"],
            "creative": ["creative", "imaginative", "artistic", "innovative", "original"],
            "humorous": ["humorous", "funny", "witty", "entertaining", "amusing"],
            "analytical": ["analytical", "precise", "systematic", "thorough", "methodical"],
            "professional": ["professional", "skilled", "expert", "competent", "reliable"],
            "helpful": ["helpful", "supportive", "friendly", "accommodating", "service"],
            "technical": ["technical", "programming", "code", "system", "development"],
            "engaging": ["engaging", "compelling", "captivating", "interesting", "dynamic"]
        }
        
        # Find matching personality traits
        traits = []
        for trait, patterns in personality_patterns.items():
            if any(pattern in text for pattern in patterns):
                traits.append(trait)
        
        # Create personality string
        if traits:
            if len(traits) >= 3:
                return f"{traits[0]}, {traits[1]}, {traits[2]}"
            elif len(traits) == 2:
                return f"{traits[0]}, {traits[1]}"
            else:
                return traits[0]
        else:
            return "helpful, professional"

    def analyze_query(self, user_query: str) -> ExecutionPlan:
        """
        Decompose and analyze a complex query to create an intelligent execution plan
        """
        
        # Step 1: Extract entities and intents
        entities = self._extract_entities_comprehensive(user_query)
        intents = self._detect_intents(user_query)
        
        # Step 2: Decompose into components
        components = self._decompose_query(user_query, entities, intents)
        
        # Step 3: Map components to resources
        mapped_components = self._map_to_resources(components)
        
        # Step 4: Create execution strategy
        execution_plan = self._create_execution_plan(mapped_components, user_query)
        
        return execution_plan

    def _extract_entities_comprehensive(self, query: str) -> Dict[str, List[str]]:
        """Enhanced entity extraction with domain-specific knowledge"""
        try:
            from ..tools.tool_config import _extract_entities_with_spacy
            entities = _extract_entities_with_spacy(query)
        except:
            entities = {"locations": [], "dates": [], "people": [], "key_concepts": []}
        
        # Add domain-specific entity detection
        query_lower = query.lower()
        
        # Detect agent-related entities
        entities["agent_hints"] = []
        for agent, info in self.agent_expertise.items():
            if any(keyword in query_lower for keyword in info["keywords"]):
                entities["agent_hints"].append(agent)
        
        # Detect knowledge-related entities (be more conservative)
        entities["knowledge_hints"] = []
        for kb_key, kb_info in self.knowledgebase_metadata.items():
            # Only match if the main keyword is found
            if kb_key.lower() in query_lower:
                entities["knowledge_hints"].append(kb_key)
            # OR if specific recipe terms are found for ciorba
            elif kb_key == "ciorba" and any(term in query_lower for term in ["ciorba", "soup", "recipe", "romanian"]):
                entities["knowledge_hints"].append(kb_key)
        
        # Remove duplicates
        entities["knowledge_hints"] = list(set(entities["knowledge_hints"]))
        
        # Detect tool needs
        entities["tool_hints"] = []
        web_search_triggers = ["today", "current", "weather", "news", "price", "latest"]
        if any(trigger in query_lower for trigger in web_search_triggers):
            entities["tool_hints"].append("web_search")
        
        return entities

    def _detect_intents(self, query: str) -> List[str]:
        """Detect multiple intents in the query"""
        intents = []
        query_lower = query.lower()
        
        # Prioritize strong intent indicators
        intent_patterns = {
            "humor": ["funny", "joke", "comedy", "parody", "amusing", "make it into a joke", "humor"],
            "recipe": ["recipe", "cook", "prepare", "ingredient", "how to make", "ciorba"],
            "storytelling": ["story", "tale", "tell me", "narrative"],
            "information": ["what", "how", "where", "when", "explain"],
            "weather": ["weather", "forecast", "temperature"],
            "guidance": ["advice", "help", "suggest", "recommend", "should"],
            "current_events": ["today", "now", "current", "latest"],
            "cultural": ["traditional", "cultural", "heritage", "history"],
            "personal": ["grandma", "family", "my", "our"]
        }
        
        for intent, patterns in intent_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                intents.append(intent)
        
        return intents

    def _decompose_query(self, query: str, entities: Dict, intents: List[str]) -> List[QueryComponent]:
        """Decompose query into manageable components with intelligent agent selection"""
        components = []
        query_lower = query.lower()
        
        # Detect multi-agent needs
        multi_agent_patterns = self._detect_multi_agent_needs(query_lower, entities, intents)
        
        if multi_agent_patterns:
            # Create multi-agent components
            for i, agent_need in enumerate(multi_agent_patterns):
                agent_component = QueryComponent(
                    text=agent_need["text"],
                    intent=agent_need["intent"],
                    entities=entities,
                    resource_type=ResourceType.AGENT,
                    resource_id=agent_need["agent_id"],
                    priority=i + 1,  # Sequential priority
                    dependencies=agent_need.get("dependencies", [])
                )
                components.append(agent_component)
        else:
            # Single agent fallback
            agent_scores = self._score_agents_for_query(query, entities, intents)
            best_agent = max(agent_scores.items(), key=lambda x: x[1])[0] if agent_scores else "story_creator"
            primary_intent = self._determine_primary_intent(intents, query)
            
            components.append(QueryComponent(
                text=f"{primary_intent} request",
                intent=primary_intent,
                entities=entities,
                resource_type=ResourceType.AGENT,
                resource_id=best_agent,
                priority=1
            ))
        
        # Add tool requirements
        if entities.get("tool_hints"):
            for tool in entities["tool_hints"]:
                if tool == "web_search":
                    components.append(QueryComponent(
                        text=f"current information",
                        intent="information_gathering",
                        entities=entities,
                        resource_type=ResourceType.TOOL,
                        resource_id="web_search",
                        priority=0  # Tools execute first
                    ))
        
        # Add knowledge requirements (deduplicated)
        if entities.get("knowledge_hints"):
            added_knowledge = set()
            for kb_key in entities["knowledge_hints"]:
                if kb_key not in added_knowledge:
                    components.append(QueryComponent(
                        text=f"knowledge from {kb_key}",
                        intent="knowledge_retrieval",
                        entities=entities,
                        resource_type=ResourceType.KNOWLEDGE,
                        resource_id=kb_key,
                        priority=0  # Knowledge retrieval happens first
                    ))
                    added_knowledge.add(kb_key)
        
        return components
    
    def _detect_multi_agent_needs(self, query_lower: str, entities: Dict, intents: List[str]) -> List[Dict]:
        """Detect when multiple agents are needed and determine the sequence"""
        multi_agent_patterns = []
        
        # Pattern 1: Analysis + Granny commentary
        if any(analysis_word in query_lower for analysis_word in ["analysis", "analyze", "data"]) and \
           any(granny_word in query_lower for granny_word in ["granny", "grandmother", "bunica", "tell me about it"]):
            multi_agent_patterns.append({
                "agent_id": "data_analyst",
                "text": "Analyze the data/information",
                "intent": "analysis",
                "dependencies": []
            })
            multi_agent_patterns.append({
                "agent_id": "granny",
                "text": "Provide grandmother's perspective on the analysis",
                "intent": "guidance",
                "dependencies": ["data_analyst"]
            })
        
        # Pattern 2: Research + Granny commentary
        elif any(research_word in query_lower for research_word in ["research", "find", "investigate"]) and \
             any(granny_word in query_lower for granny_word in ["granny", "grandmother", "bunica", "tell me about it"]):
            multi_agent_patterns.append({
                "agent_id": "research_specialist",
                "text": "Research the requested information",
                "intent": "information",
                "dependencies": []
            })
            multi_agent_patterns.append({
                "agent_id": "granny",
                "text": "Provide grandmother's perspective on the research",
                "intent": "guidance",
                "dependencies": ["research_specialist"]
            })
        
        # Pattern 3: Weather + Granny (specific pattern from user example)
        elif any(weather_word in query_lower for weather_word in ["weather", "temperature", "forecast"]) and \
             any(granny_word in query_lower for granny_word in ["granny", "grandmother", "bunica", "tell me about it"]):
            multi_agent_patterns.append({
                "agent_id": "research_specialist",
                "text": "Get weather information and analysis",
                "intent": "current_events",
                "dependencies": []
            })
            multi_agent_patterns.append({
                "agent_id": "granny",
                "text": "Provide grandmother's wisdom about the weather",
                "intent": "guidance",
                "dependencies": ["research_specialist"]
            })
        
        # Pattern 4: Technical + Content creation
        elif any(tech_word in query_lower for tech_word in ["code", "technical", "programming"]) and \
             any(content_word in query_lower for content_word in ["write", "create", "story", "explain"]):
            multi_agent_patterns.append({
                "agent_id": "technical_expert",
                "text": "Handle technical aspects",
                "intent": "technical",
                "dependencies": []
            })
            multi_agent_patterns.append({
                "agent_id": "content_writer",
                "text": "Create content based on technical information",
                "intent": "content_creation",
                "dependencies": ["technical_expert"]
            })
        
        # Pattern 5: Research + Content creation
        elif any(research_word in query_lower for research_word in ["research", "find", "investigate"]) and \
             any(content_word in query_lower for content_word in ["write", "create", "story", "article"]):
            multi_agent_patterns.append({
                "agent_id": "research_specialist",
                "text": "Research the topic",
                "intent": "information",
                "dependencies": []
            })
            multi_agent_patterns.append({
                "agent_id": "content_writer",
                "text": "Create content based on research",
                "intent": "content_creation",
                "dependencies": ["research_specialist"]
            })
        
        # Pattern 6: Data + Story creation
        elif any(data_word in query_lower for data_word in ["data", "analysis", "statistics"]) and \
             any(story_word in query_lower for story_word in ["story", "narrative", "tale"]):
            multi_agent_patterns.append({
                "agent_id": "data_analyst",
                "text": "Analyze the data",
                "intent": "analysis",
                "dependencies": []
            })
            multi_agent_patterns.append({
                "agent_id": "story_creator",
                "text": "Create story based on data analysis",
                "intent": "storytelling",
                "dependencies": ["data_analyst"]
            })
        
        return multi_agent_patterns

    def _score_agents_for_query(self, query: str, entities: Dict, intents: List[str]) -> Dict[str, float]:
        """Score all available agents based on how well they match the query"""
        agent_scores = {}
        query_lower = query.lower()
        
        for agent_id in self.available_agents:
            if agent_id in self.agent_expertise:
                score = 0.0
                expertise = self.agent_expertise[agent_id]
                
                # Score based on keyword matches
                keyword_matches = sum(1 for keyword in expertise["keywords"] if keyword in query_lower)
                score += keyword_matches * 2.0
                
                # Score based on context matches
                context_matches = sum(1 for context in expertise["contexts"] if context in query_lower)
                score += context_matches * 1.5
                
                # Score based on agent hints from entity extraction
                if agent_id in entities.get("agent_hints", []):
                    score += 5.0
                
                # Score based on intent matching with dynamic agent detection
                if "humor" in intents and any(humor_keyword in expertise["keywords"] for humor_keyword in ["funny", "humor", "parody", "comedy", "joke"]):
                    score += 10.0
                elif "recipe" in intents and any(recipe_keyword in expertise["keywords"] for recipe_keyword in ["recipe", "cooking", "food"]):
                    score += 10.0
                elif "storytelling" in intents and any(story_keyword in expertise["keywords"] for story_keyword in ["story", "narrative", "creative"]):
                    score += 10.0
                elif "information" in intents and any(research_keyword in expertise["keywords"] for research_keyword in ["research", "analyze", "investigate"]):
                    score += 10.0
                elif any(tech_word in query_lower for tech_word in ["code", "programming", "technical", "debug", "system"]) and any(tech_keyword in expertise["keywords"] for tech_keyword in ["code", "technical", "programming"]):
                    score += 10.0
                elif any(content_word in query_lower for content_word in ["write", "article", "blog", "content"]) and any(content_keyword in expertise["keywords"] for content_keyword in ["write", "content", "article"]):
                    score += 10.0
                
                agent_scores[agent_id] = score
        
        return agent_scores

    def _determine_primary_intent(self, intents: List[str], query: str) -> str:
        """Determine the primary intent from the list of detected intents"""
        # Priority order for intents
        intent_priority = {
            "humor": 1,
            "recipe": 2,
            "storytelling": 3,
            "current_events": 4,
            "information": 5,
            "guidance": 6,
            "cultural": 7,
            "personal": 8,
            "weather": 9
        }
        
        # Find the highest priority intent
        primary_intent = "general"
        best_priority = 999
        
        for intent in intents:
            if intent in intent_priority and intent_priority[intent] < best_priority:
                primary_intent = intent
                best_priority = intent_priority[intent]
        
        return primary_intent

    def _map_to_resources(self, components: List[QueryComponent]) -> List[QueryComponent]:
        """Refine component-to-resource mapping"""
        
        for component in components:
            if component.resource_type == ResourceType.AGENT:
                # Validate agent selection based on context
                if component.resource_id == "granny" and "storytelling" in component.intent:
                    # Perfect match - granny telling stories
                    component.priority = 1
                elif component.resource_id == "story_creator" and "granny" in component.entities.get("agent_hints", []):
                    # Consider switching to granny for more authentic storytelling
                    component.resource_id = "granny"
                    component.text = "traditional story with grandma's wisdom"
                    
        return components

    def _create_execution_plan(self, components: List[QueryComponent], original_query: str) -> ExecutionPlan:
        """Create an intelligent execution strategy"""
        
        # Sort components by priority
        components.sort(key=lambda x: x.priority)
        
        # Determine agent sequence and multi-agent requirements
        agent_components = [c for c in components if c.resource_type == ResourceType.AGENT]
        agent_sequence = [c.resource_id for c in agent_components]
        requires_multi_agent = len(agent_sequence) > 1
        
        # Determine primary agent (first in sequence or fallback)
        primary_agent = agent_sequence[0] if agent_sequence else "story_creator"
        
        # Determine tools and knowledge needed (deduplicated)
        tools_needed = list(set([c.resource_id for c in components if c.resource_type == ResourceType.TOOL]))
        knowledge_needed = list(set([c.resource_id for c in components if c.resource_type == ResourceType.KNOWLEDGE]))
        
        # Determine execution strategy
        strategy = "sequential"  # Default
        if requires_multi_agent:
            strategy = "multi_agent_sequential"
        elif len(components) > 2:
            # Complex query - might need hierarchical execution
            strategy = "hierarchical"
        elif len([c for c in components if c.resource_type == ResourceType.TOOL]) > 1:
            # Multiple tools - can run in parallel
            strategy = "parallel"
        
        # Determine context fusion strategy
        context_fusion = "narrative_integration"  # Default for storytelling
        if "information" in [c.intent for c in components]:
            context_fusion = "factual_integration"
        if any("granny" in c.resource_id for c in components):
            context_fusion = "persona_integrated_storytelling"
        
        return ExecutionPlan(
            components=components,
            strategy=strategy,
            primary_agent=primary_agent,
            tools_needed=tools_needed,
            knowledge_needed=knowledge_needed,
            context_fusion=context_fusion,
            agent_sequence=agent_sequence,
            requires_multi_agent=requires_multi_agent
        )

    def execute_plan(self, plan: ExecutionPlan, user_query: str) -> Dict[str, Any]:
        """Execute the intelligent plan"""
        
        results = {
            "plan_summary": f"Strategy: {plan.strategy}, Primary: {plan.primary_agent}",
            "components_executed": [],
            "tool_outputs": {},
            "knowledge_outputs": {},
            "final_agent_response": "",
            "context_fusion_type": plan.context_fusion
        }
        
        try:
            # Execute tools first (information gathering)
            for tool_id in plan.tools_needed:
                if tool_id == "web_search":
                    from ..tools.tool_config import _generate_web_search_query
                    search_query = _generate_web_search_query(user_query)
                    
                    # Execute web search (simplified for now)
                    from ..tools.web_search import run_tool
                    tool_result = run_tool(search_query)
                    results["tool_outputs"][tool_id] = {
                        "query": search_query,
                        "result": tool_result
                    }
                    results["components_executed"].append(f"web_search: {search_query}")
            
            # Execute knowledge retrieval
            for kb_id in plan.knowledge_needed:
                # Simplified knowledge retrieval
                results["knowledge_outputs"][kb_id] = f"Knowledge from {kb_id}"
                results["components_executed"].append(f"knowledge: {kb_id}")
            
            # Execute primary agent with enhanced context
            enhanced_context = self._build_enhanced_context(
                user_query, 
                results["tool_outputs"], 
                results["knowledge_outputs"],
                plan.context_fusion
            )
            
            # For now, return the enhanced context - in real implementation,
            # this would call the actual agent with the enhanced context
            results["final_agent_response"] = f"Enhanced context prepared for {plan.primary_agent}: {enhanced_context[:200]}..."
            
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def execute_multi_agent_plan(self, plan: ExecutionPlan, user_query: str, chat_history: List, enhanced_agent_registry) -> Dict[str, Any]:
        """Execute a multi-agent plan with sequential agent orchestration"""
        
        results = {
            "plan_summary": f"Multi-Agent Strategy: {plan.strategy}",
            "agents_executed": [],
            "tool_outputs": {},
            "agent_outputs": {},
            "final_agent_response": "",
            "context_fusion_type": plan.context_fusion,
            "execution_sequence": plan.agent_sequence
        }
        
        try:
            # Step 1: Execute tools first (information gathering)
            for tool_id in plan.tools_needed:
                if tool_id == "web_search":
                    from ..tools.tool_config import _generate_web_search_query
                    search_query = _generate_web_search_query(user_query)
                    
                    from ..tools.web_search import run_tool
                    tool_result = run_tool(search_query)
                    results["tool_outputs"][tool_id] = {
                        "query": search_query,
                        "result": tool_result
                    }
                    results["agents_executed"].append(f"Tool: {tool_id}")
            
            # Step 2: Execute agents sequentially
            accumulated_context = user_query
            
            for i, agent_id in enumerate(plan.agent_sequence):
                try:
                    # Build context for this agent
                    if i == 0:
                        # First agent gets the original query + tools
                        agent_context = self._build_enhanced_context(
                            user_query,
                            results["tool_outputs"],
                            {},
                            plan.context_fusion
                        )
                    else:
                        # Subsequent agents get previous agent outputs
                        previous_outputs = []
                        for prev_agent in plan.agent_sequence[:i]:
                            if prev_agent in results["agent_outputs"]:
                                previous_outputs.append(f"{prev_agent}: {results['agent_outputs'][prev_agent]}")
                        
                        agent_context = f"""Original Request: {user_query}
                        
Previous Agent Outputs:
{chr(10).join(previous_outputs)}

Tools Used:
{json.dumps(results['tool_outputs'], indent=2) if results['tool_outputs'] else 'None'}

Instructions for {agent_id}: {self._get_agent_instructions(agent_id, plan.context_fusion)}"""
                    
                    # Create State for this agent
                    from ..state import State, ChatMessage
                    agent_state = State(
                        user_prompt=agent_context,
                        history=chat_history,
                        tool_outputs=results["tool_outputs"],
                        agent_outputs=results["agent_outputs"]  # Pass previous agent outputs
                    )
                    
                    # Execute agent
                    if agent_id in enhanced_agent_registry.list_available_agents():
                        agent = enhanced_agent_registry.get_agent(agent_id)
                        result = agent.process_request(agent_state)
                        agent_response = result.get("output", "No response generated")
                        
                        # Store agent output
                        results["agent_outputs"][agent_id] = agent_response
                        results["agents_executed"].append(f"Agent: {agent_id}")
                        
                        # Update accumulated context
                        accumulated_context += f"\n\n{agent_id}: {agent_response}"
                    else:
                        error_msg = f"Agent '{agent_id}' not available in registry"
                        results["agent_outputs"][agent_id] = error_msg
                        results["agents_executed"].append(f"Agent: {agent_id} (ERROR)")
                        
                except Exception as e:
                    error_msg = f"Error executing agent {agent_id}: {str(e)}"
                    results["agent_outputs"][agent_id] = error_msg
                    results["agents_executed"].append(f"Agent: {agent_id} (ERROR)")
                    print(f"⚠️ {error_msg}")
            
            # Step 3: Set final response (last agent's output)
            if plan.agent_sequence:
                final_agent = plan.agent_sequence[-1]
                results["final_agent_response"] = results["agent_outputs"].get(final_agent, "No final response")
            else:
                results["final_agent_response"] = "No agents executed"
                
        except Exception as e:
            results["error"] = str(e)
            print(f"⚠️ Multi-agent execution error: {e}")
        
        return results
    
    def _get_agent_instructions(self, agent_id: str, context_fusion: str) -> str:
        """Get specific instructions for an agent based on context fusion type"""
        
        # Base instructions that apply to all agents
        base_instructions = f"You are {agent_id}. Respond only as {agent_id} with your unique expertise and perspective."
        
        if context_fusion == "persona_integrated_storytelling":
            if agent_id == "granny":
                return f"{base_instructions} Provide your warm, grandmother perspective on the information provided. Share wisdom and comfort as only a Romanian grandmother can. Do not summarize or repeat other agents' work - add your own unique grandmother's insight."
            elif agent_id == "data_analyst":
                return f"{base_instructions} Analyze the data and provide insights from your data analysis perspective. If you need information, use your web research capabilities. Focus on facts, trends, and analytical insights. Do not generate responses for other agents."
            elif agent_id == "story_creator":
                return f"{base_instructions} Create engaging narrative content based on the information provided. Focus on storytelling elements. Do not generate responses for other agents."
            else:
                return f"{base_instructions} Integrate the information naturally into your response, adding your unique expertise and perspective. Do not simulate or generate responses for other agents."
        
        elif context_fusion == "factual_integration":
            if agent_id == "data_analyst":
                return f"{base_instructions} Analyze the available information and provide factual insights. Use your web research capabilities if you need additional data. Focus on accuracy and analytical depth. Do not generate responses for other agents."
            elif agent_id == "granny":
                return f"{base_instructions} Share your grandmother's wisdom and perspective about the information provided. Provide comfort and traditional insights. Do not repeat analysis from other agents."
            else:
                return f"{base_instructions} Integrate the information naturally into your response, adding your expertise and perspective. Do not simulate other agents' responses."
        
        # Default instructions for any agent
        if agent_id == "granny":
            return f"{base_instructions} Share your grandmother's wisdom and perspective about the information or context provided. Provide warmth and traditional insights."
        elif agent_id == "data_analyst":
            return f"{base_instructions} Analyze the information provided and offer data-driven insights. Use your web research capabilities if you need additional information."
        elif agent_id == "story_creator":
            return f"{base_instructions} Create engaging narrative content based on the information provided. Focus on storytelling."
        elif agent_id == "parody_creator":
            return f"{base_instructions} Create humorous, satirical content based on the information provided. Keep it entertaining but tasteful."
        else:
            return f"{base_instructions} Build upon the previous work with your expertise as {agent_id}. Do not generate responses for other agents."

    def _build_enhanced_context(self, query: str, tool_outputs: Dict, knowledge_outputs: Dict, fusion_type: str) -> str:
        """Build enhanced context for the agent"""
        
        context_parts = [f"Original request: {query}"]
        
        if tool_outputs:
            context_parts.append("Current information gathered:")
            for tool, output in tool_outputs.items():
                context_parts.append(f"- {tool}: {output.get('result', '')[:100]}...")
        
        if knowledge_outputs:
            context_parts.append("Relevant stored knowledge:")
            for kb, content in knowledge_outputs.items():
                context_parts.append(f"- {kb}: {content}")
        
        if fusion_type == "persona_integrated_storytelling":
            context_parts.append("Context: Respond as a wise grandmother sharing knowledge and stories with warmth and traditional wisdom.")
        elif fusion_type == "factual_integration":
            context_parts.append("Context: Integrate the gathered information naturally into your response.")
        
        return "\n".join(context_parts)

def create_enhanced_supervisor(available_agents: List[str], knowledgebase_metadata: Dict) -> EnhancedSupervisor:
    """Factory function to create enhanced supervisor"""
    return EnhancedSupervisor(available_agents, knowledgebase_metadata) 