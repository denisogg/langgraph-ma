"""
Simplified Agent Registry - JSON-configured agents only
"""
from typing import Dict, List, Optional, Any
from .base_agent import BaseAgent
from .configurable_agent import ConfigurableAgent, load_agents_from_config


class EnhancedAgentRegistry:
    """Registry supporting JSON-configured agents only"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        
        # JSON-configured agents
        self._json_agents: Dict[str, ConfigurableAgent] = {}
        
        self.load_all_agents()
    
    def load_all_agents(self) -> None:
        """Load agents from JSON configuration"""
        print("🔄 Loading JSON-configured agents...")
        
        # Load JSON-configured agents
        self.load_json_agents()
        
        total_agents = len(self._json_agents)
        print(f"✅ Total agents loaded: {total_agents}")
    
    def load_json_agents(self) -> None:
        """Load JSON-configured agents"""
        print("🔍 Loading JSON-configured agents...")
        
        try:
            # Pass config_path or let the function use its default
            if self.config_path:
                json_agents = load_agents_from_config(self.config_path)
            else:
                json_agents = load_agents_from_config()
            self._json_agents.update(json_agents)
            print(f"✓ Loaded {len(json_agents)} JSON-configured agents")
            
            # Print agent details
            for agent_id, agent in json_agents.items():
                print(f"  - {agent_id}: {agent.get_name()} ({len(agent.get_skills())} skills)")
            
        except Exception as e:
            print(f"⚠️ Error loading JSON agents: {e}")
    
    def get_agent(self, agent_id: str) -> ConfigurableAgent:
        """Get agent by ID"""
        if agent_id not in self._json_agents:
            available = list(self._json_agents.keys())
            raise ValueError(f"Unknown agent: {agent_id}. Available: {available}")
        
        return self._json_agents[agent_id]
    
    def list_available_agents(self) -> List[str]:
        """Get list of all available agent IDs"""
        return list(self._json_agents.keys())
    
    def get_agent_type(self, agent_id: str) -> str:
        """Get agent type (always 'json' for this registry)"""
        if agent_id in self._json_agents:
            return "json"
        else:
            return "unknown"
    
    def get_agent_metadata(self, agent_id: str) -> Dict[str, Any]:
        """Get metadata for a specific agent"""
        agent = self.get_agent(agent_id)
        metadata = agent.get_metadata()
        
        # Add registry-specific metadata
        metadata.update({
            "agent_type": "json",
            "registry": "enhanced",
            "skills": agent.get_skills(),
            "skill_count": len(agent.get_skills())
        })
        
        return metadata
    
    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find agents that support a specific capability"""
        matching_agents = []
        for agent_id in self.list_available_agents():
            try:
                agent = self.get_agent(agent_id)
                if agent.supports_capability(capability):
                    matching_agents.append(agent_id)
            except Exception as e:
                print(f"⚠️ Error checking capability for {agent_id}: {e}")
        return matching_agents
    
    def find_agents_by_skill(self, skill_name: str) -> List[str]:
        """Find agents that have a specific skill"""
        matching_agents = []
        for agent_id, agent in self._json_agents.items():
            if agent.has_skill(skill_name):
                matching_agents.append(agent_id)
        return matching_agents
    
    def list_all_agents_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all available agents"""
        metadata_list = []
        for agent_id in self.list_available_agents():
            try:
                metadata = self.get_agent_metadata(agent_id)
                metadata_list.append(metadata)
            except Exception as e:
                print(f"⚠️ Error getting metadata for {agent_id}: {e}")
                metadata_list.append({
                    "id": agent_id,
                    "name": agent_id.title(),
                    "description": f"Agent {agent_id} (failed to load)",
                    "capabilities": [],
                    "error": str(e),
                    "agent_type": "json"
                })
        return metadata_list
    
    def reload_agents(self) -> None:
        """Reload all agents"""
        print("🔄 Reloading all agents...")
        self._json_agents.clear()
        self.load_all_agents()
        print("✅ Agents reloaded successfully")


# Global registry instance
enhanced_agent_registry = EnhancedAgentRegistry() 