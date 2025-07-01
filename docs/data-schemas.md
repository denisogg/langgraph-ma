# 📊 Enhanced Supervisor Data Schemas

## Core Data Structures

### ResourceType Enum

```python
from enum import Enum

class ResourceType(Enum):
    AGENT = "agent"        # AI agents that generate responses
    TOOL = "tool"          # External tools for data gathering
    KNOWLEDGE = "knowledge"  # Knowledge base files
    CONTEXT = "context"    # Context modifiers
```

**Usage Examples:**
- `ResourceType.AGENT` → granny, story_creator, parody_creator
- `ResourceType.TOOL` → web_search, calculator, translator
- `ResourceType.KNOWLEDGE` → ciorba, recipes, cultural_stories
- `ResourceType.CONTEXT` → persona_hints, style_modifiers

---

## QueryComponent Schema

```python
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class QueryComponent:
    """Represents a decomposed part of a user query"""
    
    text: str                        # Human-readable description
    intent: str                      # What this component should accomplish  
    entities: Dict[str, List[str]]   # Extracted entities from query
    resource_type: ResourceType      # Type of resource needed
    resource_id: str                # Specific resource identifier
    priority: int                   # Execution priority (1=highest)
    dependencies: Optional[List[str]] = None  # Other components this depends on
```

### Field Details

| Field | Type | Description | Examples |
|-------|------|-------------|----------|
| `text` | `str` | Human-readable component description | "humor/parody creation", "current weather information" |
| `intent` | `str` | Specific intent identifier | "humor_creation", "information_gathering", "recipe_with_tradition" |
| `entities` | `Dict[str, List[str]]` | Extracted entities by category | `{"locations": ["Paris"], "dates": ["today"]}` |
| `resource_type` | `ResourceType` | Category of resource needed | `ResourceType.AGENT`, `ResourceType.TOOL` |
| `resource_id` | `str` | Specific resource identifier | "parody_creator", "web_search", "ciorba" |
| `priority` | `int` | Execution order (1=first) | 1 (agent), 2 (tools/knowledge), 3 (context) |
| `dependencies` | `Optional[List[str]]` | Prerequisites | `["web_search_weather"]` |

### Example QueryComponent Objects

```python
# Humor request component
humor_component = QueryComponent(
    text="humor/parody creation",
    intent="humor_creation", 
    entities={"locations": ["Paris"], "dates": ["today"]},
    resource_type=ResourceType.AGENT,
    resource_id="parody_creator",
    priority=1
)

# Web search component  
search_component = QueryComponent(
    text="current weather information",
    intent="information_gathering",
    entities={"locations": ["Paris"], "dates": ["today"]},
    resource_type=ResourceType.TOOL,
    resource_id="web_search",
    priority=2
)

# Knowledge retrieval component
knowledge_component = QueryComponent(
    text="recipe knowledge from ciorba",
    intent="knowledge_retrieval", 
    entities={"recipes": ["ciorba"], "cuisine": ["romanian"]},
    resource_type=ResourceType.KNOWLEDGE,
    resource_id="ciorba",
    priority=2
)
```

---

## ExecutionPlan Schema

```python
@dataclass
class ExecutionPlan:
    """Complete plan for executing a decomposed query"""
    
    components: List[QueryComponent]  # All query components
    strategy: str                    # Execution strategy type
    primary_agent: str              # Main response generator
    tools_needed: List[str]         # Tools to execute
    knowledge_needed: List[str]     # Knowledge to retrieve
    context_fusion: str             # How to combine outputs
```

### Field Details

| Field | Type | Description | Examples |
|-------|------|-------------|----------|
| `components` | `List[QueryComponent]` | All decomposed parts | `[humor_component, search_component]` |
| `strategy` | `str` | Execution approach | "sequential", "hierarchical", "parallel" |
| `primary_agent` | `str` | Main response agent | "granny", "story_creator", "parody_creator" |
| `tools_needed` | `List[str]` | Required tools | `["web_search"]`, `["web_search", "calculator"]` |
| `knowledge_needed` | `List[str]` | Required knowledge | `["ciorba"]`, `["ciorba", "recipes"]` |
| `context_fusion` | `str` | Integration strategy | "persona_integrated_storytelling", "humor_integration" |

### Example ExecutionPlan Objects

```python
# Simple weather query plan
simple_plan = ExecutionPlan(
    components=[search_component, agent_component],
    strategy="sequential",
    primary_agent="story_creator", 
    tools_needed=["web_search"],
    knowledge_needed=[],
    context_fusion="narrative_integration"
)

# Complex multi-resource plan  
complex_plan = ExecutionPlan(
    components=[humor_component, search_component, knowledge_component],
    strategy="hierarchical",
    primary_agent="parody_creator",
    tools_needed=["web_search"], 
    knowledge_needed=["ciorba"],
    context_fusion="humor_integration"
)
```

---

## Entity Extraction Schema

```python
EntityDict = Dict[str, List[str]]

# Standard entity categories
entity_structure = {
    "locations": List[str],      # Geographic places
    "dates": List[str],          # Temporal references  
    "people": List[str],         # Person names
    "organizations": List[str],  # Companies, institutions
    "money": List[str],          # Currency amounts
    "products": List[str],       # Items, brands
    "events": List[str],         # Happenings, occasions
    "key_concepts": List[str]    # Domain terms
}
```

### Entity Examples

```python
weather_query_entities = {
    "locations": ["Halkidiki", "Greece"],
    "dates": ["today", "July 1st"],
    "people": [],
    "organizations": [],
    "money": [],
    "products": [],
    "events": [],
    "key_concepts": ["weather", "story", "grandma"]
}

recipe_query_entities = {
    "locations": ["Romania"],
    "dates": [],
    "people": ["Jamila"],
    "organizations": [],
    "money": [],
    "products": ["ciorba", "soup"],
    "events": [],
    "key_concepts": ["recipe", "traditional", "cooking"]
}
```

---

## Intent Classification Schema

```python
from typing import List

IntentList = List[str]

# Intent hierarchy (order matters for priority)
intent_categories = {
    "high_priority": [
        "humor",           # Comedy/parody requests
        "recipe",          # Cooking/food preparation
        "weather"          # Weather information
    ],
    "standard_priority": [
        "storytelling",    # Narrative requests
        "information",     # Question answering  
        "current_events",  # Real-time data
        "cultural",        # Traditional knowledge
        "personal"         # Family/personal references
    ]
}

# Intent patterns for detection
intent_patterns = {
    "humor": ["funny", "joke", "comedy", "parody", "amusing", "make it into a joke"],
    "recipe": ["recipe", "cook", "prepare", "ingredient", "how to make", "ciorba"],
    "weather": ["weather", "forecast", "temperature", "climate"],
    "storytelling": ["story", "tale", "tell me", "narrative"],
    "information": ["what", "how", "where", "when", "explain"],
    "current_events": ["today", "now", "current", "latest"],
    "cultural": ["traditional", "cultural", "heritage", "history"],
    "personal": ["grandma", "family", "my", "our"]
}
```

---

## Context Fusion Schema

```python
from typing import Literal

ContextFusionType = Literal[
    "persona_integrated_storytelling",
    "humor_integration", 
    "factual_integration",
    "narrative_integration"
]

# Fusion strategy mapping
fusion_strategies = {
    "persona_integrated_storytelling": {
        "when": "Granny agent selected",
        "behavior": "Warm grandmother voice with cultural wisdom",
        "example": "Ah, draga mea, let me tell you about the weather..."
    },
    "humor_integration": {
        "when": "Parody creator selected", 
        "behavior": "Transform information into comedic content",
        "example": "So the weather in Paris is like my cooking skills..."
    },
    "factual_integration": {
        "when": "Information-focused queries",
        "behavior": "Present data clearly within response style", 
        "example": "Based on current data, here's what you need to know..."
    },
    "narrative_integration": {
        "when": "Story creator or general queries",
        "behavior": "Weave facts into engaging stories",
        "example": "Once upon a time, when the temperature reached 25°C..."
    }
}
```

---

## Tool Configuration Schema

```python
from pydantic import BaseModel
from typing import Optional, List

class ToolConfig(BaseModel):
    """Configuration for individual tools"""
    name: str                    # Tool identifier
    option: Optional[str] = None # Tool-specific option

class ToolMetadata(BaseModel):
    """Comprehensive tool information"""
    name: str                           # Tool name
    description: str                    # What the tool does
    use_cases: List[str]               # When to use it
    input_format: str                   # How to format input
    confidence_threshold: float = 0.7   # Minimum confidence to use
    fallback_behavior: str = "inform_user"  # What to do if fails

# Example tool metadata
web_search_metadata = ToolMetadata(
    name="web_search",
    description="Searches the internet for current information, news, weather, facts",
    use_cases=[
        "current weather conditions",
        "recent news and events", 
        "real-time data and statistics",
        "current prices and market info"
    ],
    input_format="Generate specific, focused search query from user request",
    confidence_threshold=0.8,
    fallback_behavior="inform_user_no_results"
)
```

---

## Agent Expertise Schema

```python
agent_expertise_mapping = {
    "granny": {
        "keywords": ["grandma", "granny", "bunica", "traditional", "romanian", "recipe"],
        "contexts": ["storytelling", "traditional_knowledge", "family", "cultural"],
        "personality": "traditional, warm, wise",
        "specialties": ["recipes", "cultural_stories", "traditional_wisdom"]
    },
    "story_creator": {
        "keywords": ["story", "tale", "narrative", "once upon", "character", "plot"],
        "contexts": ["creative_writing", "storytelling", "fictional", "imaginative"],
        "personality": "creative, engaging, narrative",
        "specialties": ["creative_stories", "world_building", "character_development"]
    },
    "parody_creator": {
        "keywords": ["funny", "humor", "parody", "comedy", "joke", "satire"],
        "contexts": ["humor", "entertainment", "satirical", "comedic"],
        "personality": "humorous, witty, entertaining", 
        "specialties": ["comedy", "satire", "humorous_transformations"]
    }
}
```

---

## Response Format Schema

```python
@dataclass
class SupervisorResponse:
    """Standard response format from Enhanced Supervisor"""
    
    supervisor_decision: str        # Analysis explanation
    chosen_agent: str              # Selected primary agent
    agent_response: str            # Final response content
    tool_outputs: Dict[str, Any]   # Tool execution results
    supervisor_type: str           # "enhanced" 
    execution_plan: Dict[str, Any] # Plan metadata
    
    # Optional debugging info
    analysis_time_ms: Optional[int] = None
    components_count: Optional[int] = None
    entities_found: Optional[Dict[str, List[str]]] = None
```

### Example Response

```python
enhanced_response = SupervisorResponse(
    supervisor_decision="Enhanced Analysis: Strategy=hierarchical, Components=3, Context=humor_integration",
    chosen_agent="parody_creator",
    agent_response="So there I was, looking at the weather forecast for Halkidiki...",
    tool_outputs={
        "web_search": {
            "query": "weather Halkidiki today",
            "result": "Temperature: 28°C, sunny, light breeze"
        }
    },
    supervisor_type="enhanced",
    execution_plan={
        "strategy": "hierarchical", 
        "components": 3,
        "context_fusion": "humor_integration"
    },
    components_count=3,
    entities_found={
        "locations": ["Halkidiki"],
        "dates": ["today"], 
        "key_concepts": ["weather", "story"]
    }
)
```

These schemas provide the complete data structure foundation for the Enhanced Supervisor system, enabling type-safe development and clear API contracts. 