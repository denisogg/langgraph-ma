# 🧠 Enhanced Supervisor Architecture

## Overview

The Enhanced Supervisor transforms basic agent routing into intelligent multi-resource orchestration through NLP-driven query analysis, component decomposition, and strategic execution planning.

## Core Architecture

```
User Query → Analysis → Decomposition → Planning → Orchestration → Response
     ↓           ↓            ↓           ↓            ↓
Entity Extract → Components → Strategy → Resources → Enhanced Context
Intent Detect → Priority → Fusion → Tools/Knowledge → Primary Agent
```

## System Components

### 1. Query Analysis Pipeline

**Entity Extraction** (spaCy NER + Domain Logic):
- **Locations**: Geographic entities (cities, countries)
- **Dates**: Temporal references ("today", specific dates)
- **People**: Person names and references
- **Organizations**: Companies, institutions
- **Products**: Items, technologies, brands
- **Key Concepts**: Domain-specific terms

**Intent Detection** (Prioritized Pattern Matching):
```python
High Priority Intents:
├── "humor" → Humor/comedy requests
├── "recipe" → Cooking/food preparation
└── "weather" → Weather information

Standard Intents:
├── "storytelling" → Narrative requests
├── "information" → Question answering
└── "current_events" → Real-time data
```

### 2. Component Decomposition

Each query creates **QueryComponent** objects:

```python
@dataclass
class QueryComponent:
    text: str                    # Human-readable description
    intent: str                  # What needs to be done
    entities: Dict[str, List[str]]  # Extracted entities
    resource_type: ResourceType  # AGENT, TOOL, KNOWLEDGE
    resource_id: str            # Specific resource identifier
    priority: int               # Execution order (1=highest)
    dependencies: Optional[List[str]] = None
```

### 3. Resource Types

```python
class ResourceType(Enum):
    AGENT = "agent"        # AI agents (granny, story_creator, parody_creator)
    TOOL = "tool"          # External tools (web_search, calculator)
    KNOWLEDGE = "knowledge"  # Knowledge bases (ciorba, recipes)
    CONTEXT = "context"    # Context modifiers
```

### 4. Execution Planning

```python
@dataclass
class ExecutionPlan:
    components: List[QueryComponent]  # Decomposed query parts
    strategy: str                    # Execution strategy
    primary_agent: str              # Main response generator
    tools_needed: List[str]         # Required tools
    knowledge_needed: List[str]     # Required knowledge
    context_fusion: str             # How to combine outputs
```

## Execution Strategies

### Sequential Strategy
- **When**: Simple queries (1-2 components)
- **Flow**: Linear execution (tool → agent)
- **Example**: "What's the weather today?"

```
Query → Web Search → Story Creator → Response
```

### Hierarchical Strategy  
- **When**: Complex queries (3+ components)
- **Flow**: Prioritized execution with dependencies
- **Example**: "Funny story about ciorba in today's weather"

```
Query → Priority 1: Select parody_creator
      → Priority 2: Execute web_search + Retrieve ciorba knowledge
      → Priority 3: Enhanced context fusion
      → Response
```

### Parallel Strategy
- **When**: Multiple independent tools needed
- **Flow**: Tools run simultaneously
- **Example**: "Compare weather in 3 cities"

```
Query → Web Search Paris   ↘
      → Web Search London  → Results Aggregation → Agent → Response
      → Web Search Berlin  ↗
```

## Resource Determination Logic

### Agent Selection Priority

```python
Priority Matrix:
1. "humor" keywords → parody_creator (ALWAYS)
2. "recipe" + "traditional" → granny (cultural expertise)
3. "story" + "granny" hints → granny (persona-specific)
4. "storytelling" → story_creator (general narrative)
5. Default → story_creator (fallback)
```

### Tool Selection Logic

```python
Web Search Triggers:
- Temporal: "today", "current", "now", "latest"
- Weather: "weather", "forecast", "temperature"
- News: "news", "happening", "update"
- Pricing: "price", "cost", "buy"

Knowledge Base Triggers:
- Recipe: "ciorba", "soup", "romanian", "recipe"
- Cultural: "traditional", "heritage", "history"
```

### Priority System

```
Priority 1: Primary agent selection (establishes response style)
Priority 2: Resource gathering (tools + knowledge)
Priority 3: Context fusion (combine everything)
```

## Context Fusion Strategies

### Persona Integrated Storytelling
- **When**: Granny agent selected
- **Behavior**: Warm grandmother voice with cultural wisdom
- **Example**: "Ah, draga mea, let me tell you about the weather..."

### Humor Integration  
- **When**: Parody creator selected
- **Behavior**: Transform information into comedic content
- **Example**: "So the weather in Paris is like my cooking skills..."

### Factual Integration
- **When**: Information-focused queries
- **Behavior**: Present data clearly within response style
- **Example**: "Based on current data, here's what you need to know..."

### Narrative Integration
- **When**: Story creator or general queries
- **Behavior**: Weave facts into engaging stories
- **Example**: "Once upon a time, when the temperature reached 25°C..."

## Component Generation Logic

### Intent-to-Component Mapping

```python
Intent Detection → Component Creation:

"humor" → QueryComponent(
    text="humor/parody creation",
    intent="humor_creation",
    resource_type=ResourceType.AGENT,
    resource_id="parody_creator",
    priority=1
)

"recipe" + "traditional" → QueryComponent(
    text="traditional recipe guidance", 
    intent="recipe_with_tradition",
    resource_type=ResourceType.AGENT,
    resource_id="granny",
    priority=1
)

"weather" + "today" → QueryComponent(
    text="current information",
    intent="information_gathering",
    resource_type=ResourceType.TOOL,
    resource_id="web_search", 
    priority=2
)
```

### Text Field Generation

The `text` field provides human-readable descriptions:

```python
Agent Components:
- "humor/parody creation" → parody_creator handles humor
- "story told by grandma" → granny with persona
- "traditional recipe guidance" → granny with cultural context

Tool Components:
- "current information" → web_search for real-time data
- "calculation results" → calculator for math

Knowledge Components:  
- "knowledge from ciorba" → recipe information
- "cultural context" → traditional knowledge
```

## Enhanced Context Generation

The system builds rich context for the primary agent:

```python
Enhanced Context Structure:
├── Original Query
├── Tool Outputs (with metadata)
├── Knowledge Outputs (relevant content)
├── Fusion Strategy Instructions
└── Integration Guidelines

Example:
"""
Original request: Tell me a funny story about ciorba in today's weather

Tool Results:
- web_search: "Temperature: 22°C, partly cloudy, humidity: 65%"

Knowledge Retrieved:
- ciorba: "Traditional Romanian soup with sour cream base..."

Instructions: Create humorous content integrating weather and recipe 
information into an entertaining story using comedic transformation style.
"""
```

## Benefits Over Basic Supervisor

| Aspect | Basic Supervisor | Enhanced Supervisor |
|--------|------------------|-------------------|
| **Query Handling** | Single intent only | Multi-intent decomposition |
| **Resource Usage** | Agent OR tools | Agent AND tools AND knowledge |
| **Context Awareness** | Pattern matching | NLP + cultural understanding |
| **Scalability** | Hardcoded rules | Universal NLP-driven |
| **Intelligence** | Rule-based routing | Strategic orchestration |
| **Accuracy** | Keyword collision | Entity-driven precision |

## Implementation Classes

### Core Data Structures

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional

class ResourceType(Enum):
    AGENT = "agent"
    TOOL = "tool" 
    KNOWLEDGE = "knowledge"
    CONTEXT = "context"

@dataclass
class QueryComponent:
    text: str
    intent: str
    entities: Dict[str, List[str]]
    resource_type: ResourceType
    resource_id: str
    priority: int
    dependencies: Optional[List[str]] = None

@dataclass  
class ExecutionPlan:
    components: List[QueryComponent]
    strategy: str
    primary_agent: str
    tools_needed: List[str]
    knowledge_needed: List[str]
    context_fusion: str
```

### Main Controller

```python
class EnhancedSupervisor:
    def __init__(self, available_agents: List[str], knowledgebase_metadata: Dict):
        self.available_agents = available_agents
        self.knowledgebase_metadata = knowledgebase_metadata
        
    def analyze_query(self, user_query: str) -> ExecutionPlan:
        # Extract entities and intents
        # Decompose into components  
        # Map to resources
        # Create execution strategy
        
    def _extract_entities_comprehensive(self, query: str) -> Dict[str, List[str]]:
        # spaCy NER + domain-specific detection
        
    def _decompose_query(self, query: str, entities: Dict, intents: List[str]) -> List[QueryComponent]:
        # Create components based on priority logic
        
    def _create_execution_plan(self, components: List[QueryComponent], query: str) -> ExecutionPlan:
        # Determine strategy, primary agent, and fusion type
```

This architecture enables true AI orchestration that understands complex intent, coordinates multiple resources, and delivers sophisticated responses with cultural awareness and contextual precision. 