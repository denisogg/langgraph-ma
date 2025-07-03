from typing import Dict, Any, List, Optional, Generator
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from .base_agent import BaseAgent
from .state import State
from .skills.skill_manager import SkillManager
import json
import os


class ConfigurableAgent(BaseAgent):
    """Agent that loads its behavior from JSON configuration"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any], skills_config: Optional[Dict[str, Any]] = None):
        # Initialize with config from JSON
        super().__init__(agent_id, config.get('parameters', {}))
        
        # Load agent configuration
        self.agent_config = config
        self._name = config.get('name', agent_id.title())
        self._description = config.get('description', f'Agent {agent_id}')
        self._capabilities = config.get('capabilities', [])
        self._system_prompt = config.get('system_prompt', f'You are {self._name}.')
        self._routing_keywords = config.get('routing_keywords', [])
        self._category = config.get('category', 'general')
        self._version = config.get('version', '1.0.0')
        
        # Load parameters
        params = config.get('parameters', {})
        self.temperature = params.get('temperature', 0.7)
        self.model = params.get('model', 'gpt-3.5-turbo')
        self.max_tokens = params.get('max_tokens', 2000)
        
        # LLM will be initialized lazily when needed
        self._llm = None
        
        # Initialize skills manager
        agent_skills = config.get('skills', [])
        self.skill_manager = SkillManager(agent_skills, skills_config or {})
    
    @property
    def llm(self):
        """Lazy initialization of LLM"""
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                streaming=True
            )
        return self._llm
    
    def get_name(self) -> str:
        return self._name
    
    def get_description(self) -> str:
        return self._description
    
    def get_capabilities(self) -> List[str]:
        return self._capabilities.copy()
    
    def get_system_prompt(self) -> str:
        # Build enhanced system prompt with skills information
        base_prompt = self._system_prompt
        
        if self.skill_manager.has_skills():
            skills_info = self.skill_manager.get_skills_description()
            enhanced_prompt = f"{base_prompt}\n\nYou have access to the following specialized skills:\n{skills_info}\n\nUse these skills when appropriate to enhance your responses."
            return enhanced_prompt
        
        return base_prompt
    
    def get_routing_keywords(self) -> List[str]:
        return self._routing_keywords.copy()
    
    def get_skills(self) -> List[str]:
        """Get list of skills assigned to this agent"""
        return self.skill_manager.get_skill_names()
    
    def has_skill(self, skill_name: str) -> bool:
        """Check if agent has a specific skill"""
        return self.skill_manager.has_skill(skill_name)
    
    def execute_skill(self, skill_name: str, input_data: Any, **kwargs) -> Any:
        """Execute a specific skill"""
        return self.skill_manager.execute_skill(skill_name, input_data, **kwargs)
    
    def process_request(self, state: State) -> Dict[str, Any]:
        """Process user request and return response (non-streaming)"""
        print(f"🎮 CONTROL FLOW: Agent {self.agent_id} has control, starting request processing")
        
        # Build context for the agent
        context = self._build_context(state)
        print(f"🎮 CONTROL FLOW: Agent {self.agent_id} built context from state")
        
        # Execute any relevant skills based on the request
        print(f"🎮 CONTROL FLOW: Agent {self.agent_id} checking for relevant skills to execute")
        self._execute_relevant_skills(state)
        
        # Build the final prompt
        prompt = self._build_prompt(state, context)
        print(f"🎮 CONTROL FLOW: Agent {self.agent_id} built final prompt, calling LLM")
        
        # Generate response
        messages = [
            SystemMessage(content=self.get_system_prompt()),
            HumanMessage(content=prompt)
        ]
        
        result = self.llm.invoke(messages)
        output_text = str(result.content) if result.content else ""
        print(f"🎮 CONTROL FLOW: Agent {self.agent_id} received LLM response, preparing to return control")
        
        # Update state
        state.set_agent_output(self.agent_id, output_text, {
            "agent_type": "configurable",
            "skills_used": self.skill_manager.get_executed_skills(),
            "model": self.model,
            "temperature": self.temperature,
            "category": self._category,
            "version": self._version
        })
        
        # Log final result
        tools_used = list(state.tool_outputs.keys()) if state.tool_outputs else []
        if tools_used:
            print(f"🎮 CONTROL FLOW: Agent {self.agent_id} used tools: {tools_used}")
        else:
            print(f"🎮 CONTROL FLOW: Agent {self.agent_id} did not use any tools")
        
        skills_used = self.skill_manager.get_executed_skills()
        if skills_used:
            print(f"🎮 CONTROL FLOW: Agent {self.agent_id} executed skills: {skills_used}")
        else:
            print(f"🎮 CONTROL FLOW: Agent {self.agent_id} did not execute any skills")
        
        print(f"🎮 CONTROL FLOW: Agent {self.agent_id} completed processing, ready to return control")
        
        return {
            "output": output_text,
            "agent_id": self.agent_id,
            "skills_used": self.skill_manager.get_executed_skills(),
            "tool_outputs": state.tool_outputs,  # Include tool outputs that were executed
            "category": self._category
        }
    
    def process_request_stream(self, state: State) -> Generator[str, None, None]:
        """Process user request and yield streaming response"""
        # Build context for the agent
        context = self._build_context(state)
        
        # Execute any relevant skills based on the request
        self._execute_relevant_skills(state)
        
        # Build the final prompt
        prompt = self._build_prompt(state, context)
        
        # Generate streaming response
        messages = [
            SystemMessage(content=self.get_system_prompt()),
            HumanMessage(content=prompt)
        ]
        
        full_response = ""
        for chunk in self.llm.stream(messages):
            if hasattr(chunk, 'content') and chunk.content:
                content_str = str(chunk.content)
                full_response += content_str
                yield content_str
        
        # Update state after streaming
        state.set_agent_output(self.agent_id, full_response, {
            "agent_type": "configurable",
            "skills_used": self.skill_manager.get_executed_skills(),
            "model": self.model,
            "temperature": self.temperature,
            "category": self._category,
            "version": self._version,
            "streaming": True
        })
    
    def _build_context(self, state: State) -> str:
        """Build context for the agent from state"""
        return state.get_context_for_agent(self.agent_id)
    
    def _execute_relevant_skills(self, state: State) -> None:
        """Execute skills that are relevant to the current request"""
        user_prompt = state.user_prompt.lower()
        
        # Check if this agent has skills and if they're relevant
        if not self.skill_manager.has_skills():
            print(f"🎮 CONTROL FLOW: Agent {self.agent_id} has no skills available")
            return
        
        available_skills = self.skill_manager.get_skill_names()
        print(f"🎮 CONTROL FLOW: Agent {self.agent_id} has skills available: {available_skills}")
        
        # Determine if web research is needed
        if self.skill_manager.has_skill("web_research"):
            research_indicators = [
                "weather", "news", "current", "latest", "recent", "information",
                "search", "find", "research", "data", "analyze", "report",
                "temperature", "climate", "forecast", "today", "yesterday",
                "last week", "this week", "bucharest", "romania", "city"
            ]
            
            needs_research = any(indicator in user_prompt for indicator in research_indicators)
            
            if needs_research:
                print(f"🎮 CONTROL FLOW: Agent {self.agent_id} detected need for web research")
                # Extract potential search query from the request
                search_query = self._extract_search_query(state.user_prompt)
                if search_query:
                    try:
                        print(f"🎮 CONTROL FLOW: Agent {self.agent_id} executing web_research skill")
                        print(f"🔍 DEBUG: Agent {self.agent_id} executing web_research skill with query: {search_query}")
                        print(f"🎮 CONTROL FLOW: - Agent {self.agent_id} delegating to web_research skill")
                        print(f"🎮 CONTROL FLOW: - web_research skill will call web search tool")
                        
                        research_result = self.skill_manager.execute_skill("web_research", search_query)
                        
                        print(f"🎮 CONTROL FLOW: - web_research skill completed, returning control to {self.agent_id}")
                        print(f"🔍 DEBUG: Web research completed for {self.agent_id}")
                        
                        # Store tool result in state for later use
                        if isinstance(research_result, dict) and research_result.get("success"):
                            state.tool_outputs["web_search"] = research_result
                            print(f"🎮 CONTROL FLOW: Agent {self.agent_id} stored web search results in state")
                            print(f"🔍 DEBUG: Stored web research result in state")
                        else:
                            print(f"🎮 CONTROL FLOW: Agent {self.agent_id} web research failed or returned no results")
                        
                    except Exception as e:
                        print(f"🎮 CONTROL FLOW: Agent {self.agent_id} web research failed with exception: {e}")
                        print(f"⚠️ Web research skill failed for {self.agent_id}: {e}")
                else:
                    print(f"🎮 CONTROL FLOW: Agent {self.agent_id} could not extract search query from request")
            else:
                print(f"🎮 CONTROL FLOW: Agent {self.agent_id} determined web research not needed")
        else:
            print(f"🎮 CONTROL FLOW: Agent {self.agent_id} does not have web_research skill")
    
    def _extract_search_query(self, user_prompt: str) -> str:
        """Extract a search query from the user prompt"""
        # For now, use a simple extraction
        # This could be enhanced with more sophisticated NLP
        
        # Look for specific patterns that indicate what to search for
        prompt_lower = user_prompt.lower()
        
        # If asking about weather in a specific location
        if "weather" in prompt_lower:
            if "bucharest" in prompt_lower:
                return "weather Bucharest Romania current forecast"
            elif "romania" in prompt_lower:
                return "weather Romania current forecast"
            else:
                return "weather current forecast"
        
        # If asking for analysis of something specific
        if "analysis" in prompt_lower or "analyze" in prompt_lower:
            if "weather" in prompt_lower:
                return "weather analysis forecast data"
            elif "data" in prompt_lower:
                return "data analysis information"
        
        # For general information requests, extract key terms
        import re
        
        # Remove common stop words and extract meaningful terms
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "about", "make", "me", "tell", "let"}
        words = re.findall(r'\b\w+\b', user_prompt.lower())
        meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Take the most important words (first few after filtering)
        if meaningful_words:
            return " ".join(meaningful_words[:5])
        
        return user_prompt[:100]  # Fallback to first 100 chars
    
    def _build_prompt(self, state: State, context: str) -> str:
        """Build the complete prompt for the agent"""
        prompt_parts = []
        
        # Add conversation context
        if context:
            prompt_parts.append(f"Context:\n{context}")
        
        # Add skills results if any were executed
        skills_results = self.skill_manager.get_execution_results()
        if skills_results:
            prompt_parts.append(f"Skills Results:\n{skills_results}")
        
        # Add current request
        prompt_parts.append(f"Current Request: {state.user_prompt}")
        
        return "\n\n".join(prompt_parts)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return enhanced metadata including skills and configuration"""
        base_metadata = super().get_metadata()
        base_metadata.update({
            "skills": self.get_skills(),
            "category": self._category,
            "version": self._version,
            "configuration_source": "json",
            "max_tokens": self.max_tokens,
            "skill_count": len(self.get_skills())
        })
        return base_metadata


def load_agents_from_config(config_path: Optional[str] = None) -> Dict[str, ConfigurableAgent]:
    """Load all agents from JSON configuration file"""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'agents_config.json')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        agents = {}
        agents_config = config_data.get('agents', {})
        skills_config = config_data.get('skills', {})
        
        for agent_id, agent_config in agents_config.items():
            if agent_config.get('active', True):
                agent = ConfigurableAgent(agent_id, agent_config, skills_config)
                agents[agent_id] = agent
        
        print(f"✓ Loaded {len(agents)} configurable agents from {config_path}")
        return agents
        
    except FileNotFoundError:
        print(f"⚠️ Configuration file not found: {config_path}")
        return {}
    except Exception as e:
        print(f"⚠️ Error loading agents configuration: {e}")
        return {} 