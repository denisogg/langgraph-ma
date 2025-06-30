from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import os

@dataclass
class ToolUsage:
    tool_name: str
    query: str
    result: str
    confidence_score: float
    user_feedback: Optional[str] = None
    timestamp: Optional[datetime] = None
    success: bool = True
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass 
class UserPreference:
    preferred_tools: Dict[str, float]  # tool_name -> preference_score
    query_patterns: Dict[str, List[str]]  # successful query patterns
    feedback_history: List[Dict[str, Any]]
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()

class ToolUsageTracker:
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.usage_history: List[ToolUsage] = []
        self.user_preferences = UserPreference(
            preferred_tools={},
            query_patterns={},
            feedback_history=[]
        )
        self._load_session_data()
    
    def _get_session_file(self) -> str:
        """Get session file path"""
        data_dir = os.path.join(os.path.dirname(__file__), "../../data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, f"usage_history_{self.session_id}.json")
    
    def _load_session_data(self):
        """Load usage history and preferences from file"""
        try:
            session_file = self._get_session_file()
            if os.path.exists(session_file):
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Load usage history
                for usage_data in data.get('usage_history', []):
                    usage = ToolUsage(
                        tool_name=usage_data['tool_name'],
                        query=usage_data['query'],
                        result=usage_data['result'],
                        confidence_score=usage_data['confidence_score'],
                        user_feedback=usage_data.get('user_feedback'),
                        timestamp=datetime.fromisoformat(usage_data['timestamp']) if usage_data['timestamp'] else None,
                        success=usage_data.get('success', True)
                    )
                    self.usage_history.append(usage)
                
                # Load user preferences
                prefs_data = data.get('user_preferences', {})
                self.user_preferences = UserPreference(
                    preferred_tools=prefs_data.get('preferred_tools', {}),
                    query_patterns=prefs_data.get('query_patterns', {}),
                    feedback_history=prefs_data.get('feedback_history', []),
                    last_updated=datetime.fromisoformat(prefs_data.get('last_updated', datetime.now().isoformat())) if prefs_data.get('last_updated') else None
                )
        except Exception as e:
            print(f"Error loading session data: {e}")
    
    def _save_session_data(self):
        """Save usage history and preferences to file"""
        try:
            session_file = self._get_session_file()
            
            # Prepare data for JSON serialization
            usage_data = []
            for usage in self.usage_history:
                usage_data.append({
                    'tool_name': usage.tool_name,
                    'query': usage.query,
                    'result': usage.result,
                    'confidence_score': usage.confidence_score,
                    'user_feedback': usage.user_feedback,
                    'timestamp': usage.timestamp.isoformat() if usage.timestamp else None,
                    'success': usage.success
                })
            
            prefs_data = {
                'preferred_tools': self.user_preferences.preferred_tools,
                'query_patterns': self.user_preferences.query_patterns,
                'feedback_history': self.user_preferences.feedback_history,
                'last_updated': self.user_preferences.last_updated.isoformat() if self.user_preferences.last_updated else None
            }
            
            data = {
                'usage_history': usage_data,
                'user_preferences': prefs_data
            }
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving session data: {e}")
    
    def record_tool_usage(self, tool_name: str, query: str, result: str, 
                         confidence_score: float, success: bool = True) -> str:
        """Record a tool usage instance"""
        usage = ToolUsage(
            tool_name=tool_name,
            query=query,
            result=result,
            confidence_score=confidence_score,
            success=success
        )
        
        self.usage_history.append(usage)
        
        # Update preferences based on success
        if success and confidence_score > 0.7:
            current_score = self.user_preferences.preferred_tools.get(tool_name, 0.5)
            # Increase preference for successful tools
            new_score = min(current_score + 0.1, 1.0)
            self.user_preferences.preferred_tools[tool_name] = new_score
            
            # Record successful query pattern
            if tool_name not in self.user_preferences.query_patterns:
                self.user_preferences.query_patterns[tool_name] = []
            
            self.user_preferences.query_patterns[tool_name].append(query)
            # Keep only last 10 successful patterns per tool
            self.user_preferences.query_patterns[tool_name] = \
                self.user_preferences.query_patterns[tool_name][-10:]
        
        self._save_session_data()
        return f"usage_{len(self.usage_history)}"
    
    def get_recent_usage(self, tool_name: Optional[str] = None, hours: int = 24) -> List[ToolUsage]:
        """Get recent tool usage within specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_usage = [
            usage for usage in self.usage_history 
            if usage.timestamp and usage.timestamp >= cutoff_time
        ]
        
        if tool_name:
            recent_usage = [usage for usage in recent_usage if usage.tool_name == tool_name]
        
        return recent_usage
    
    def was_recently_used(self, tool_name: str, query: str, hours: int = 1) -> bool:
        """Check if similar query was recently used for this tool"""
        recent_usage = self.get_recent_usage(tool_name, hours)
        
        for usage in recent_usage:
            # Simple similarity check (can be improved with more sophisticated matching)
            if self._queries_similar(query, usage.query):
                return True
        
        return False
    
    def _queries_similar(self, query1: str, query2: str, threshold: float = 0.7) -> bool:
        """Check if two queries are similar (simple word overlap)"""
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union)
        return similarity >= threshold
    
    def get_tool_preference_score(self, tool_name: str) -> float:
        """Get user preference score for a tool"""
        return self.user_preferences.preferred_tools.get(tool_name, 0.5)
    
    def get_successful_query_patterns(self, tool_name: str) -> List[str]:
        """Get successful query patterns for a tool"""
        return self.user_preferences.query_patterns.get(tool_name, [])
    
    def calculate_confidence_score(self, tool_name: str, result: str) -> float:
        """Calculate confidence score based on result quality and historical data"""
        base_confidence = 0.5
        
        # Adjust based on result length and content
        if result and len(result) > 50:
            base_confidence += 0.2
        
        if "error" in result.lower() or "not found" in result.lower():
            base_confidence -= 0.3
        
        # Adjust based on tool preference
        preference_score = self.get_tool_preference_score(tool_name)
        base_confidence = (base_confidence + preference_score) / 2
        
        # Adjust based on recent success rate
        recent_usage = self.get_recent_usage(tool_name, hours=24)
        if recent_usage:
            success_rate = sum(1 for usage in recent_usage if usage.success) / len(recent_usage)
            base_confidence = (base_confidence + success_rate) / 2
        
        return max(0.0, min(1.0, base_confidence))
    
    def should_retry_with_different_query(self, tool_name: str, current_query: str, 
                                        result: str) -> Dict[str, Any]:
        """Determine if we should retry with a different query based on poor results"""
        confidence = self.calculate_confidence_score(tool_name, result)
        
        if confidence < 0.4:
            # Suggest alternative query based on successful patterns
            successful_patterns = self.get_successful_query_patterns(tool_name)
            
            return {
                "should_retry": True,
                "confidence": confidence,
                "suggested_patterns": successful_patterns[-3:] if successful_patterns else [],
                "reason": "Low confidence result, consider alternative query"
            }
        
        return {
            "should_retry": False,
            "confidence": confidence,
            "reason": "Result quality acceptable"
        }
    
    def add_user_feedback(self, usage_id: str, feedback: str, rating: Optional[int] = None):
        """Add user feedback for a specific tool usage"""
        try:
            usage_index = int(usage_id.split('_')[1]) - 1
            if 0 <= usage_index < len(self.usage_history):
                self.usage_history[usage_index].user_feedback = feedback
                
                # Update preferences based on feedback
                usage = self.usage_history[usage_index]
                feedback_entry = {
                    "tool_name": usage.tool_name,
                    "query": usage.query,
                    "feedback": feedback,
                    "rating": rating,
                    "timestamp": datetime.now().isoformat()
                }
                
                self.user_preferences.feedback_history.append(feedback_entry)
                
                # Adjust tool preference based on rating
                if rating is not None:
                    current_pref = self.user_preferences.preferred_tools.get(usage.tool_name, 0.5)
                    if rating >= 4:  # Good rating
                        new_pref = min(current_pref + 0.15, 1.0)
                    elif rating <= 2:  # Poor rating
                        new_pref = max(current_pref - 0.15, 0.0)
                    else:  # Neutral rating
                        new_pref = current_pref
                    
                    self.user_preferences.preferred_tools[usage.tool_name] = new_pref
                
                self._save_session_data()
                
        except (ValueError, IndexError) as e:
            print(f"Error adding feedback: {e}")

# Global tracker instance
_global_tracker: Optional[ToolUsageTracker] = None

def get_usage_tracker(session_id: str = "default") -> ToolUsageTracker:
    """Get or create global usage tracker instance"""
    global _global_tracker
    if _global_tracker is None or _global_tracker.session_id != session_id:
        _global_tracker = ToolUsageTracker(session_id)
    return _global_tracker 