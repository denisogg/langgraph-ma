import importlib
import inspect
import os
from pathlib import Path
from typing import Dict, Type, List, Optional, Any, Union
from .base_agent import BaseAgent
from .configurable_agent import ConfigurableAgent, load_agents_from_config


class EnhancedAgentRegistry:
    """Enhanced registry supporting both file-based and JSON-configured agents"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        
        # File-based agents (traditional)
        self._file_agent_classes: Dict[str, Type[BaseAgent]] = {}
        self._file_agent_instances: Dict[str, BaseAgent] = {}
        self._file_agent_configs: Dict[str, Dict[str, Any]] = {}
        
        # JSON-configured agents
        self._json_agents: Dict[str, ConfigurableAgent] = {}
        
        # Combined registry
        self._all_agents: Dict[str, BaseAgent] = {}
        
        self.load_all_agents()
    
    def load_all_agents(self) -> None:
        """Load agents from both file system and JSON configuration"""
        print("🔄 Loading agents from multiple sources...")
        
        # Load file-based agents
        self.discover_file_agents()
        
        # Load JSON-configured agents
        self.load_json_agents()
        
        # Update combined registry
        self._update_combined_registry()
        
        total_agents = len(self._all_agents)
        print(f"✅ Total agents loaded: {total_agents}")
    
    def discover_file_agents(self) -> None:
        """Discover traditional file-based agents"""
        current_dir = Path(__file__).parent
        agent_files = []
        
        # Look for agent files in current directory and subdirectories
        for item in current_dir.iterdir():
            if item.is_file() and item.name.endswith('_agent.py') and item.name != 'base_agent.py':
                agent_files.append(item)
            elif item.is_dir() and item.name not in ['__pycache__', '.git', 'skills']:
                # Look for agent.py files in subdirectories
                agent_file = item / 'agent.py'
                if agent_file.exists():
                    agent_files.append(agent_file)
        
        print(f"🔍 Discovering file-based agents in {current_dir}")
        
        for agent_file in agent_files:
            try:
                self._load_file_agent(agent_file)
            except Exception as e:
                print(f"⚠️ Failed to load file agent from {agent_file}: {e}")
    
    def load_json_agents(self) -> None:
        """Load JSON-configured agents"""
        print("🔍 Loading JSON-configured agents...")
        
        try:
            json_agents = load_agents_from_config(self.config_path)
            self._json_agents.update(json_agents)
            
            print(f"✓ Loaded {len(json_agents)} JSON-configured agents")
            
        except Exception as e:
            print(f"⚠️ Error loading JSON agents: {e}")
    
    def _load_file_agent(self, agent_file: Path) -> None:
        """Load agent class from a Python file"""
        # Determine module path (same logic as original registry)
        current_dir = Path(__file__).parent
        relative_path = agent_file.relative_to(current_dir)
        
        if relative_path.name == 'agent.py':
            agent_id = relative_path.parent.name
            module_name = f"agent.{agent_id}.agent"
        else:
            agent_id = relative_path.stem.replace('_agent', '')
            module_name = f"agent.{agent_id}_agent"
        
        # Try different module path strategies
        module_paths_to_try = [
            module_name,
            f"backend.src.{module_name}",
            f"src.{module_name}",
        ]
        
        module = None
        for module_path in module_paths_to_try:
            try:
                module = importlib.import_module(module_path)
                break
            except ImportError:
                continue
        
        if module is None:
            print(f"⚠️ Failed to import file agent module: {module_paths_to_try}")
            return
        
        # Find BaseAgent subclasses in the module
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, BaseAgent) and 
                obj != BaseAgent and 
                obj != ConfigurableAgent):
                
                self._file_agent_classes[agent_id] = obj
                print(f"✓ Discovered file agent: {agent_id} ({obj.__name__})")
                break
    
    def _update_combined_registry(self) -> None:
        """Update the combined registry with all agents"""
        self._all_agents.clear()
        
        # Add file-based agent instances
        for agent_id in self._file_agent_classes.keys():
            try:
                agent = self.get_file_agent(agent_id)
                self._all_agents[agent_id] = agent
            except Exception as e:
                print(f"⚠️ Error adding file agent {agent_id} to combined registry: {e}")
        
        # Add JSON-configured agents
        self._all_agents.update(self._json_agents)
    
    def get_file_agent(self, agent_id: str) -> BaseAgent:
        """Get file-based agent instance (singleton per agent_id)"""
        if agent_id not in self._file_agent_instances:
            if agent_id not in self._file_agent_classes:
                raise ValueError(f"Unknown file agent: {agent_id}")
            
            agent_class = self._file_agent_classes[agent_id]
            config = self._file_agent_configs.get(agent_id, {})
            self._file_agent_instances[agent_id] = agent_class(agent_id, config)
        
        return self._file_agent_instances[agent_id]
    
    def get_agent(self, agent_id: str) -> BaseAgent:
        """Get any agent (file-based or JSON-configured)"""
        if agent_id not in self._all_agents:
            raise ValueError(f"Unknown agent: {agent_id}. Available: {list(self._all_agents.keys())}")
        
        return self._all_agents[agent_id]
    
    def list_available_agents(self) -> List[str]:
        """Get list of all available agent IDs"""
        return list(self._all_agents.keys())
    
    def list_file_agents(self) -> List[str]:
        """Get list of file-based agent IDs"""
        return list(self._file_agent_classes.keys())
    
    def list_json_agents(self) -> List[str]:
        """Get list of JSON-configured agent IDs"""
        return list(self._json_agents.keys())
    
    def get_agent_type(self, agent_id: str) -> str:
        """Get agent type (file or json)"""
        if agent_id in self._json_agents:
            return "json"
        elif agent_id in self._file_agent_classes:
            return "file"
        else:
            return "unknown"
    
    def get_agent_metadata(self, agent_id: str) -> Dict[str, Any]:
        """Get metadata for a specific agent"""
        agent = self.get_agent(agent_id)
        metadata = agent.get_metadata()
        
        # Add registry-specific metadata
        metadata.update({
            "agent_type": self.get_agent_type(agent_id),
            "registry": "enhanced"
        })
        
        # Add skills info for JSON agents
        if isinstance(agent, ConfigurableAgent):
            metadata.update({
                "skills": agent.get_skills(),
                "skill_count": len(agent.get_skills())
            })
        
        return metadata
    
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
                    "agent_type": self.get_agent_type(agent_id)
                })
        return metadata_list
    
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
        """Find JSON agents that have a specific skill"""
        matching_agents = []
        for agent_id, agent in self._json_agents.items():
            if agent.has_skill(skill_name):
                matching_agents.append(agent_id)
        return matching_agents
    
    def reload_agents(self) -> None:
        """Reload all agents"""
        print("🔄 Reloading all agents...")
        
        # Clear all registries
        self._file_agent_classes.clear()
        self._file_agent_instances.clear()
        self._json_agents.clear()
        self._all_agents.clear()
        
        # Reload everything
        self.load_all_agents()
    
    def set_agent_config(self, agent_id: str, config: Dict[str, Any]) -> None:
        """Set configuration for a file-based agent"""
        if agent_id in self._file_agent_classes:
            self._file_agent_configs[agent_id] = config
            # Remove instance to force recreation with new config
            if agent_id in self._file_agent_instances:
                del self._file_agent_instances[agent_id]
            # Update combined registry
            self._update_combined_registry()
        else:
            print(f"⚠️ Cannot set config for non-file agent: {agent_id}")


# Global enhanced registry instance
enhanced_agent_registry = EnhancedAgentRegistry() 