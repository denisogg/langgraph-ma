from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseSkill(ABC):
    """Base interface for all agent skills"""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.execution_count = 0
        self.last_result = None
    
    @abstractmethod
    def get_description(self) -> str:
        """Return a description of what this skill does"""
        pass
    
    @abstractmethod
    def execute(self, input_data: Any, **kwargs) -> Any:
        """Execute the skill with given input data"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Return skill parameters/configuration"""
        return self.config.copy()
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Return execution statistics"""
        return {
            "execution_count": self.execution_count,
            "last_execution": self.last_result is not None
        }
    
    def _record_execution(self, result: Any) -> None:
        """Record execution for statistics"""
        self.execution_count += 1
        self.last_result = result 