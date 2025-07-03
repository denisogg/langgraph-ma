from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Generator, AsyncGenerator
from .state import State

class BaseAgent(ABC):
    """Base interface for all agents in the system"""
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id
        self.config = config or {}
        self.temperature = self.config.get('temperature', 0.7)
        self.model = self.config.get('model', 'gpt-3.5-turbo')
        self.default_tools = self.config.get('default_tools', [])
    
    @abstractmethod
    def get_name(self) -> str:
        """Return human-readable agent name"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return agent description for UI and routing"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities for intelligent routing"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return agent's system prompt"""
        pass
    
    @abstractmethod
    def process_request(self, state: State) -> Dict[str, Any]:
        """Process user request and return response (non-streaming)"""
        pass
    
    @abstractmethod
    def process_request_stream(self, state: State) -> Generator[str, None, None]:
        """Process user request and yield streaming response"""
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return agent metadata for discovery and routing"""
        return {
            "id": self.agent_id,
            "name": self.get_name(),
            "description": self.get_description(),
            "capabilities": self.get_capabilities(),
            "category": self.config.get('category', 'general'),
            "tags": self.config.get('tags', []),
            "version": self.config.get('version', '1.0.0'),
            "temperature": self.temperature,
            "model": self.model,
            "default_tools": self.default_tools
        }
    
    def supports_capability(self, capability: str) -> bool:
        """Check if agent supports a specific capability"""
        return capability.lower() in [cap.lower() for cap in self.get_capabilities()]
    
    def get_routing_keywords(self) -> List[str]:
        """Return keywords that should route to this agent"""
        # Default implementation based on capabilities
        keywords = []
        for capability in self.get_capabilities():
            keywords.extend(capability.split('_'))
        return keywords 