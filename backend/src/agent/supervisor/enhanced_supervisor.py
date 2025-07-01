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

class EnhancedSupervisor:
    def __init__(self, available_agents: List[str], knowledgebase_metadata: Dict):
        self.available_agents = available_agents
        self.knowledgebase_metadata = knowledgebase_metadata
        
        # Agent expertise mapping
        self.agent_expertise = {
            "granny": {
                "keywords": ["grandma", "granny", "bunica", "traditional", "romanian", "recipe", "cooking"],
                "contexts": ["storytelling", "traditional_knowledge", "family", "cultural"],
                "personality": "traditional, warm, wise"
            },
            "story_creator": {
                "keywords": ["story", "tale", "narrative", "once upon", "character", "plot"],
                "contexts": ["creative_writing", "storytelling", "fictional", "imaginative"], 
                "personality": "creative, engaging, narrative"
            },
            "parody_creator": {
                "keywords": ["funny", "humor", "parody", "comedy", "joke", "satire"],
                "contexts": ["humor", "entertainment", "satirical", "comedic"],
                "personality": "humorous, witty, entertaining"
            }
        }

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
        """Decompose query into manageable components with proper prioritization"""
        components = []
        
        # PRIORITY 1: Humor/Parody requests (highest priority)
        if "humor" in intents:
            components.append(QueryComponent(
                text="humor/parody creation",
                intent="humor_creation",
                entities=entities,
                resource_type=ResourceType.AGENT,
                resource_id="parody_creator",
                priority=1
            ))
        
        # PRIORITY 2: Recipe requests with cultural context
        elif "recipe" in intents:
            if "granny" in entities.get("agent_hints", []) or "traditional" in query.lower():
                components.append(QueryComponent(
                    text="traditional recipe guidance",
                    intent="recipe_with_tradition",
                    entities=entities,
                    resource_type=ResourceType.AGENT,
                    resource_id="granny",
                    priority=1
                ))
            else:
                components.append(QueryComponent(
                    text="recipe information",
                    intent="recipe",
                    entities=entities,
                    resource_type=ResourceType.AGENT,
                    resource_id="granny",  # Recipes are better with granny
                    priority=1
                ))
        
        # PRIORITY 3: Story requests with agent context
        elif "storytelling" in intents:
            if "granny" in entities.get("agent_hints", []):
                components.append(QueryComponent(
                    text="story told by grandma",
                    intent="storytelling_with_persona",
                    entities=entities,
                    resource_type=ResourceType.AGENT,
                    resource_id="granny",
                    priority=1
                ))
            else:
                components.append(QueryComponent(
                    text="creative story",
                    intent="storytelling",
                    entities=entities,
                    resource_type=ResourceType.AGENT,
                    resource_id="story_creator",
                    priority=1
                ))
        
        # DEFAULT: Use story creator for general queries
        else:
            components.append(QueryComponent(
                text="general response",
                intent="general",
                entities=entities,
                resource_type=ResourceType.AGENT,
                resource_id="story_creator",
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
                        priority=2
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
                        priority=2
                    ))
                    added_knowledge.add(kb_key)
        
        return components

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
        
        # Determine primary agent
        agent_components = [c for c in components if c.resource_type == ResourceType.AGENT]
        primary_agent = agent_components[0].resource_id if agent_components else "story_creator"
        
        # Determine tools and knowledge needed (deduplicated)
        tools_needed = list(set([c.resource_id for c in components if c.resource_type == ResourceType.TOOL]))
        knowledge_needed = list(set([c.resource_id for c in components if c.resource_type == ResourceType.KNOWLEDGE]))
        
        # Determine execution strategy
        strategy = "sequential"  # Default
        if len(components) > 2:
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
            context_fusion=context_fusion
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