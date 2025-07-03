from typing import Dict, List, Any, Optional
from .base_skill import BaseSkill
from .implementations import get_skill_implementation
import importlib


class SkillManager:
    """Manages skills for a configurable agent"""
    
    def __init__(self, skill_names: List[str], skills_config: Dict[str, Any]):
        self.skill_names = skill_names
        self.skills_config = skills_config
        self.loaded_skills: Dict[str, BaseSkill] = {}
        self.execution_results: Dict[str, Any] = {}
        self.executed_skills: List[str] = []
        
        self._load_skills()
    
    def _load_skills(self) -> None:
        """Load skill implementations"""
        for skill_name in self.skill_names:
            try:
                skill_config = self.skills_config.get(skill_name, {})
                skill_implementation = get_skill_implementation(skill_name, skill_config)
                
                if skill_implementation:
                    self.loaded_skills[skill_name] = skill_implementation
                    print(f"✓ Loaded skill: {skill_name}")
                else:
                    print(f"⚠️ Skill implementation not found: {skill_name}")
                    
            except Exception as e:
                print(f"⚠️ Error loading skill {skill_name}: {e}")
    
    def has_skills(self) -> bool:
        """Check if any skills are loaded"""
        return len(self.loaded_skills) > 0
    
    def has_skill(self, skill_name: str) -> bool:
        """Check if a specific skill is loaded"""
        return skill_name in self.loaded_skills
    
    def get_skill_names(self) -> List[str]:
        """Get list of loaded skill names"""
        return list(self.loaded_skills.keys())
    
    def get_skills_description(self) -> str:
        """Get formatted description of all loaded skills"""
        descriptions = []
        for skill_name, skill in self.loaded_skills.items():
            descriptions.append(f"- {skill_name}: {skill.get_description()}")
        return "\n".join(descriptions)
    
    def execute_skill(self, skill_name: str, input_data: Any, **kwargs) -> Any:
        """Execute a specific skill"""
        if skill_name not in self.loaded_skills:
            raise ValueError(f"Skill '{skill_name}' not available")
        
        skill = self.loaded_skills[skill_name]
        try:
            result = skill.execute(input_data, **kwargs)
            
            # Record execution
            self.execution_results[skill_name] = result
            if skill_name not in self.executed_skills:
                self.executed_skills.append(skill_name)
            
            skill._record_execution(result)
            return result
            
        except Exception as e:
            error_result = f"Error executing skill {skill_name}: {e}"
            self.execution_results[skill_name] = error_result
            return error_result
    
    def get_executed_skills(self) -> List[str]:
        """Get list of skills that were executed"""
        return self.executed_skills.copy()
    
    def get_execution_results(self) -> str:
        """Get formatted execution results"""
        if not self.execution_results:
            return ""
        
        results = []
        for skill_name, result in self.execution_results.items():
            results.append(f"• {skill_name}: {result}")
        
        return "\n".join(results)
    
    def clear_execution_history(self) -> None:
        """Clear execution history"""
        self.execution_results.clear()
        self.executed_skills.clear()
    
    def get_skill_metadata(self, skill_name: str) -> Dict[str, Any]:
        """Get metadata for a specific skill"""
        if skill_name not in self.loaded_skills:
            return {}
        
        skill = self.loaded_skills[skill_name]
        return {
            "name": skill_name,
            "description": skill.get_description(),
            "parameters": skill.get_parameters(),
            "stats": skill.get_execution_stats()
        }
    
    def get_all_skills_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for all loaded skills"""
        return [self.get_skill_metadata(skill_name) for skill_name in self.get_skill_names()] 