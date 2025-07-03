import importlib
import inspect
import os
from pathlib import Path
from typing import Dict, Type, List, Optional, Any
from .base_agent import BaseAgent


class AgentRegistry:
    """Registry for auto-discovering and managing agent plugins"""
    
    def __init__(self):
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}
        self._agent_instances: Dict[str, BaseAgent] = {}
        self._agent_configs: Dict[str, Dict[str, Any]] = {}
        self.discover_agents()
    
    def discover_agents(self) -> None:
        """Automatically discover all agent plugins in the current directory"""
        current_dir = Path(__file__).parent
        agent_files = []
        
        # Look for agent files in current directory and subdirectories
        for item in current_dir.iterdir():
            if item.is_file() and item.name.endswith('_agent.py') and item.name != 'base_agent.py':
                agent_files.append(item)
            elif item.is_dir() and item.name not in ['__pycache__', '.git']:
                # Look for agent.py files in subdirectories
                agent_file = item / 'agent.py'
                if agent_file.exists():
                    agent_files.append(agent_file)
        
        print(f"🔍 Discovering agents in {current_dir}")
        
        for agent_file in agent_files:
            try:
                self._load_agent_from_file(agent_file)
            except Exception as e:
                print(f"⚠️ Failed to load agent from {agent_file}: {e}")
    
    def _load_agent_from_file(self, agent_file: Path) -> None:
        """Load agent class from a Python file"""
        # Determine module path
        current_dir = Path(__file__).parent
        relative_path = agent_file.relative_to(current_dir)
        
        if relative_path.name == 'agent.py':
            # Handle subdirectory/agent.py pattern
            agent_id = relative_path.parent.name
            module_name = f"agent.{agent_id}.agent"
        else:
            # Handle xxx_agent.py pattern  
            agent_id = relative_path.stem.replace('_agent', '')
            module_name = f"agent.{agent_id}_agent"
        
        # Try different module path strategies
        module_paths_to_try = [
            module_name,  # Relative path (agent.granny.agent)
            f"backend.src.{module_name}",  # Absolute path from project root
            f"src.{module_name}",  # Alternate path
        ]
        
        module = None
        for module_path in module_paths_to_try:
            try:
                module = importlib.import_module(module_path)
                break
            except ImportError:
                continue
        
        if module is None:
            print(f"⚠️ Failed to import any of these module paths: {module_paths_to_try}")
            return
        
        try:
            
            # Find BaseAgent subclasses in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseAgent) and 
                    obj != BaseAgent):
                    
                    self._agent_classes[agent_id] = obj
                    print(f"✓ Discovered agent: {agent_id} ({obj.__name__})")
                    break
            else:
                print(f"⚠️ No BaseAgent subclass found in module")
                # Debug: print all classes found in the module
                classes_found = [name for name, obj in inspect.getmembers(module) if inspect.isclass(obj)]
                print(f"   Classes found in module: {classes_found}")
                
        except Exception as e:
            print(f"⚠️ Error loading agent from {agent_file}: {e}")
    
    def register_agent(self, agent_id: str, agent_class: Type[BaseAgent], config: Optional[Dict[str, Any]] = None) -> None:
        """Manually register an agent class"""
        self._agent_classes[agent_id] = agent_class
        if config:
            self._agent_configs[agent_id] = config
        print(f"✓ Manually registered agent: {agent_id}")
    
    def get_agent(self, agent_id: str) -> BaseAgent:
        """Get agent instance (singleton per agent_id)"""
        if agent_id not in self._agent_instances:
            if agent_id not in self._agent_classes:
                raise ValueError(f"Unknown agent: {agent_id}. Available: {list(self._agent_classes.keys())}")
            
            agent_class = self._agent_classes[agent_id]
            config = self._agent_configs.get(agent_id, {})
            self._agent_instances[agent_id] = agent_class(agent_id, config)
        
        return self._agent_instances[agent_id]
    
    def set_agent_config(self, agent_id: str, config: Dict[str, Any]) -> None:
        """Set configuration for an agent"""
        self._agent_configs[agent_id] = config
        # Remove instance to force recreation with new config
        if agent_id in self._agent_instances:
            del self._agent_instances[agent_id]
    
    def list_available_agents(self) -> List[str]:
        """Get list of all available agent IDs"""
        return list(self._agent_classes.keys())
    
    def get_agent_metadata(self, agent_id: str) -> Dict[str, Any]:
        """Get metadata for a specific agent"""
        agent = self.get_agent(agent_id)
        return agent.get_metadata()
    
    def list_all_agents_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all available agents"""
        metadata_list = []
        for agent_id in self.list_available_agents():
            try:
                metadata = self.get_agent_metadata(agent_id)
                metadata_list.append(metadata)
            except Exception as e:
                print(f"⚠️ Error getting metadata for {agent_id}: {e}")
                # Add basic metadata even if agent fails to initialize
                metadata_list.append({
                    "id": agent_id,
                    "name": agent_id.title(),
                    "description": f"Agent {agent_id} (failed to load)",
                    "capabilities": [],
                    "error": str(e)
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
    
    def reload_agents(self) -> None:
        """Reload all agents (useful for development)"""
        self._agent_classes.clear()
        self._agent_instances.clear()
        self.discover_agents()


# Global registry instance
agent_registry = AgentRegistry() 