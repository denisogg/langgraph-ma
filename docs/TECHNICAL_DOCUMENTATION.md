# 📚 LangGraph Multi-Agent System - Technical Documentation

## 🎯 System Overview

This is a sophisticated multi-agent conversational AI system built with LangGraph, FastAPI, and React. The system supports both **sequential agent execution** and **intelligent supervisor-based routing**, featuring Romanian grandmother wisdom, creative storytelling, and humor generation capabilities.

### 🏗️ Architecture Patterns

1. **Sequential Mode**: User manually configures agent chains (granny → story_creator → parody_creator)
2. **Supervisor Mode**: Intelligent routing based on request content analysis
3. **Hybrid Execution**: Tools are intelligently selected and executed before agent processing

---

## 🧱 Core Architecture Components

### Backend Structure (`backend/src/agent/`)

```
backend/src/agent/
├── graph.py                 # Main FastAPI app and LangGraph orchestration
├── state.py                 # State management and data models
├── supervisor_graph.py      # Standalone supervisor service (deprecated)
├── agents/
│   ├── granny/agent.py      # Romanian grandmother agent
│   ├── story_creator/agent.py  # Creative writing agent  
│   ├── parody_creator/agent.py # Humor and parody agent
│   └── supervisor/
│       ├── enhanced_supervisor.py  # Advanced supervisor logic (unused)
│       └── supervisor_agent.py    # LangGraph Command-based supervisor
├── tools/
│   ├── tool_config.py       # Tool metadata and intelligent selection
│   ├── tool_executor.py     # Tool execution and context management
│   ├── usage_tracker.py     # Tool usage analytics
│   └── web_search.py        # Tavily web search integration
└── memory/
    └── memory_manager.py    # Conversation persistence
```

### Frontend Structure (`frontend/src/`)

```
frontend/src/
├── App.js                   # Main React application
├── index.js                 # Entry point
└── assets/                  # CSS and static resources
```

---

## 📊 Data Models and State Management

### State Schema (`state.py`)

```python
class State(BaseModel):
    user_prompt: str                           # Current user input
    history: List[ChatMessage]                 # Conversation history  
    tool_outputs: Dict[str, Any] = {}         # Tool execution results
    granny_output: Optional[str] = None        # Agent-specific outputs
    story_output: Optional[str] = None
    parody_output: Optional[str] = None
    previous_agent_output: Optional[str] = None # Agent chaining
    current_agent_id: Optional[str] = None
    agent_flow: Optional[List[Dict[str, Any]]] = None # Execution config
```

### Chat Configuration

```python
class ChatSettings(BaseModel):
    agent_sequence: List[AgentConfig]
    supervisor_mode: bool = False     # Enable intelligent routing
    supervisor_type: str = "basic"    # "basic" or "advanced"

class AgentConfig(BaseModel):
    id: str                          # "granny", "story_creator", "parody_creator"  
    enabled: bool
    tools: Optional[List[ToolType]] = []
```

---

## 🤖 Agent Implementations

### 1. Granny Agent (`granny/agent.py`)

**Purpose**: Warm Romanian grandmother providing wisdom, recipes, and family advice

**Key Features**:
- High temperature (0.9) for warm, emotional responses
- Romanian cultural context and traditional knowledge
- Recipe expertise with knowledgebase integration
- Tool-aware prompt engineering

**System Prompt**:
```
You are a sweet old Romanian grandmother who responds with warmth, wisdom, and love. 
You often reference traditional Romanian recipes, family values, and life lessons.
When you have tools available, you integrate tool results naturally into your responses.
```

### 2. Story Creator Agent (`story_creator/agent.py`)

**Purpose**: Creative writer crafting vivid, engaging narratives

**Key Features**:
- Moderate temperature (0.7) for creative but coherent stories
- Rich descriptions and compelling character development
- Context-aware storytelling with tool integration
- Adaptable narrative style based on input

### 3. Parody Creator Agent (`parody_creator/agent.py`)

**Purpose**: Humor specialist creating parodies, satire, and comedic content

**Key Features**:
- Creative temperature for humor generation
- Multiple comedy styles (parody, satire, wordplay)
- Context-sensitive humor adaptation
- Tool integration for topical comedy

---

## 🔧 Tool System Architecture

### Tool Configuration (`tools/tool_config.py`)

**Intelligent Tool Selection Algorithm**:

```python
def determine_needed_tools(user_prompt: str, agent_name: str) -> List[ToolConfig]:
    """NLP-based tool selection with confidence scoring"""
    
    # Web Search Triggers
    web_triggers = ["today", "current", "now", "latest", "news", "weather"]
    
    # Knowledge Base Triggers  
    kb_triggers = ["recipe", "ciorba", "traditional", "romanian", "cooking"]
    
    # Semantic matching with confidence thresholds
    return selected_tools
```

### Tool Execution Pipeline (`tools/tool_executor.py`)

```python
def execute_intelligent_tools(state: State, tools: List[ToolConfig], agent_id: str) -> State:
    """
    1. Analyze user prompt for tool relevance
    2. Generate optimized tool queries
    3. Execute tools with error handling
    4. Aggregate results with metadata
    5. Update state with enriched context
    """
```

### Available Tools

#### 1. Web Search Tool (`web_search.py`)
- **Provider**: Tavily API
- **Use Cases**: Current events, weather, real-time information
- **Query Optimization**: Entity extraction + context-aware query generation
- **Confidence Scoring**: Result relevance assessment

#### 2. Knowledge Base Tool
- **Storage**: JSON-based knowledge files
- **Content**: Romanian recipes (ciorba), cultural knowledge
- **Semantic Matching**: Romanian NLP with stop-word filtering
- **Extensible**: Easy addition of new knowledge domains

---

## 🧠 Supervisor System Architecture

### Supervisor Modes

#### Basic Supervisor (`supervisor_agent.py`)
```python
def create_supervisor_agent():
    """
    Simple handoff-based routing using LangGraph Command pattern
    - Analyzes user request intent
    - Routes to single most appropriate agent
    - Uses handoff tools for delegation
    """
```

**Routing Logic**:
- Recipe/wisdom requests → granny
- Creative writing → story_creator  
- Humor/parodies → parody_creator

#### Advanced Supervisor
```python  
def create_advanced_supervisor_agent():
    """
    Task delegation with explicit context passing
    - Breaks down complex requests
    - Provides detailed task descriptions
    - Contextual agent instruction
    """
```

### Supervisor Integration (`graph.py`)

The supervisor functionality is integrated into the main application with:

1. **Backward Compatibility**: Original sequential mode preserved
2. **Runtime Switching**: Toggle between modes per conversation
3. **Fallback Handling**: Automatic fallback to sequential mode on errors
4. **Agent Wrappers**: Seamless integration with existing agent implementations

---

## 🔄 Execution Flow Patterns

### Sequential Mode Flow

```
User Input → Agent Selection → Tool Execution → Agent Processing → Response
```

1. User configures agent sequence manually
2. Each agent executes with assigned tools
3. Output chains to next agent as context
4. Final agent generates user response

### Supervisor Mode Flow

```
User Input → Supervisor Analysis → Agent Selection → Tool Intelligence → Primary Agent → Response
```

1. Supervisor analyzes request intent and context
2. Routes to most appropriate single agent
3. Intelligent tools execute based on request analysis
4. Primary agent generates enhanced response

### Tool Intelligence Flow

```
Request Analysis → Tool Relevance → Query Generation → Execution → Context Enrichment
```

**Example**:
```
"Tell me about today's weather in Bucharest and share a ciorba recipe"

Analysis:
- Entities: [Bucharest, today, ciorba]
- Tools: [web_search for weather, knowledgebase for recipe]
- Agent: granny (recipe expertise)

Execution:
1. Web search: "weather Bucharest today"
2. Knowledge query: "ciorba recipe Romanian traditional"
3. Granny receives enriched context
4. Generates warm response integrating both results
```

---

## 🌐 API Endpoints Reference

### Chat Management

#### `GET /chats`
- **Purpose**: List all chats with content
- **Filtering**: Excludes empty chats (no messages or enabled agents)
- **Response**: Array of chat objects with metadata

#### `POST /chats`
- **Purpose**: Create new chat session
- **Response**: Chat object with generated UUID

#### `GET /chats/{chat_id}`  
- **Purpose**: Retrieve chat details
- **Response**: Full chat state including history and settings

### Configuration

#### `POST /chats/{chat_id}/settings`
```python
{
    "agent_sequence": [
        {"id": "granny", "enabled": true, "tools": ["web_search"]},
        {"id": "story_creator", "enabled": true, "tools": []}
    ],
    "supervisor_mode": false,
    "supervisor_type": "basic"
}
```

#### `POST /chats/{chat_id}/supervisor`
- **Purpose**: Toggle supervisor mode
- **Parameters**: `enabled: bool`, `supervisor_type: str`

### Message Processing

#### `POST /chats/{chat_id}/message/stream`
- **Purpose**: Stream agent responses in real-time
- **Protocol**: Server-Sent Events with JSON chunks
- **Response Format**:
```python
{
    "sender": "agent_name",
    "text": "partial_response",
    "for_agent": "target_agent"  # Optional
}
```

#### `POST /chats/{chat_id}/message`
- **Purpose**: Non-streaming message processing
- **Use Case**: Testing and integration scenarios

### Utility Endpoints

#### `GET /knowledgebase`
- **Purpose**: Retrieve knowledgebase metadata
- **Response**: Available knowledge files and options

#### `POST /chats/cleanup`
- **Purpose**: Remove empty chat sessions
- **Criteria**: No messages AND no enabled agents

---

## 🔌 LangGraph Integration

### Graph Construction (`graph.py`)

```python
def build_dynamic_graph(agent_ids: List[str]):
    """
    Constructs LangGraph StateGraph with:
    1. Tool nodes (dynamically created)
    2. Agent nodes (from registry)
    3. Sequential edge connections
    4. State management
    """
    builder = StateGraph(State)
    # Dynamic node creation and edge linking
    return builder.compile()
```

### Supervisor Graph Integration

```python
def build_supervisor_graph(supervisor_type: str = "basic"):
    """
    Creates supervisor-managed graph with:
    1. Supervisor entry point
    2. Agent wrapper nodes
    3. Command-based routing
    4. State conversion (MessagesState ↔ State)
    """
```

### State Management

The system handles conversion between:
- **LangGraph MessagesState**: Standard LangGraph format
- **Custom State**: Application-specific state with tool outputs and agent chaining

---

## 🛠️ Development Patterns

### Agent Development

**Creating New Agents**:

1. **Implement Agent Function**:
```python
def create_new_agent(state: State) -> dict:
    # Tool integration
    agent_tools = get_agent_tools_from_state(state, "new_agent")
    state = execute_intelligent_tools(state, agent_tools, "new_agent")
    
    # Response generation
    context = state.get_context_for_agent("new_agent")
    response = llm.invoke([system_prompt, HumanMessage(content=context)])
    
    return {"new_agent_output": response.content}
```

2. **Register in Agent Registry**:
```python
AGENTS_REGISTRY = {
    "new_agent": create_new_agent,
    # ... existing agents
}
```

3. **Add to Frontend Options**:
```javascript
const ALL_AGENTS = ["granny", "story_creator", "parody_creator", "new_agent"];
```

### Tool Development

**Adding New Tools**:

1. **Implement Tool Function** (`tools/new_tool.py`)
2. **Add Tool Metadata** (`tool_config.py`)
3. **Register in Tool Executor** (`tool_executor.py`)
4. **Update Intelligence Logic** (trigger words, use cases)

### Configuration Patterns

**Environment Variables**:
```bash
OPENAI_API_KEY=your_key_here
TAVILY_API_KEY=your_tavily_key
```

**File Structure**:
```
backend/src/data/
├── knowledgebase.json    # Knowledge base content
├── usage_history.json   # Tool usage analytics  
└── reteta_ciorba.txt     # Raw knowledge files
```

---

## 🔄 Streaming Architecture

### Backend Streaming (`graph.py`)

```python
async def stream_generator():
    """
    Server-Sent Events implementation:
    1. Process user message
    2. Execute agent pipeline
    3. Stream partial responses
    4. Maintain conversation state
    """
    
    # Agent streaming with token-by-token delivery
    for agent_response in agent_stream:
        yield f"data: {json.dumps(response_chunk)}\n\n"
```

### Frontend Streaming (`App.js`)

```javascript
const response = await fetch('/message/stream', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({user_prompt: currentInput})
});

const reader = response.body.getReader();
// Process streaming chunks and update UI in real-time
```

---

## 🚀 Performance Considerations

### Tool Execution Optimization

1. **Parallel Tool Execution**: Independent tools run concurrently
2. **Caching Strategy**: Tool results cached per session
3. **Confidence Thresholds**: Avoid unnecessary tool calls
4. **Fallback Mechanisms**: Graceful degradation on tool failures

### Memory Management

1. **Conversation Pruning**: Automatic cleanup of empty chats
2. **State Persistence**: JSON-based chat storage
3. **Tool Output Metadata**: Rich context with confidence scoring

### Error Handling

1. **Tool Failure Recovery**: Continue with partial results
2. **Agent Fallbacks**: Default responses when agents fail
3. **Supervisor Fallbacks**: Automatic sequential mode switching
4. **API Error Handling**: Graceful degradation for external services

---

## 🧪 Testing and Debugging

### Test Files

- `test_enhanced_supervisor.py`: Supervisor routing logic
- `test_hybrid_nlp.py`: NLP processing and tool selection
- `test_query_generation.py`: Query optimization algorithms

### Debugging Tools

1. **Logging**: Comprehensive logging throughout the pipeline
2. **State Inspection**: Full state dumps for debugging
3. **Tool Analytics**: Usage tracking and performance metrics
4. **Response Streaming**: Real-time execution monitoring

---

## 🔮 Extension Points

### Adding New Capabilities

1. **New Agents**: Following the established agent pattern
2. **Additional Tools**: API integrations, databases, external services
3. **Enhanced NLP**: spaCy models, transformer integration
4. **Memory Systems**: Vector stores, conversation memory
5. **Multi-modal Support**: Image, audio, document processing

### Configuration Extensions

1. **Agent Personalities**: Configurable personality parameters
2. **Tool Preferences**: User-specific tool selection preferences
3. **Response Styles**: Customizable output formatting
4. **Integration Hooks**: Webhook support for external systems

---

## 📈 Monitoring and Analytics

### Usage Tracking (`tools/usage_tracker.py`)

- Tool usage frequency and success rates
- Agent selection patterns
- Conversation flow analytics
- Performance metrics and optimization insights

### Health Monitoring

- API endpoint health checks
- Tool availability monitoring  
- Agent response quality metrics
- Error rate tracking and alerting

---

This technical documentation provides a comprehensive overview of the LangGraph Multi-Agent system architecture, implementation patterns, and extension capabilities. The system is designed for flexibility, maintainability, and intelligent automation while preserving the unique personalities and capabilities of each specialized agent. 