# 🤖 LangGraph Multi-Agent Conversational System

A sophisticated multi-agent AI system featuring Romanian grandmother wisdom, creative storytelling, and humor generation with intelligent routing and tool integration.

## 🎯 Features

- **🧙‍♀️ Multi-Agent Architecture**: Granny (wisdom/recipes), Story Creator (narratives), Parody Creator (humor)
- **🧠 Intelligent Supervisor**: Automatic agent routing based on request content analysis
- **🔧 Smart Tool Integration**: Web search, knowledge base access with NLP-driven selection
- **💬 Real-time Streaming**: Live response streaming with React frontend
- **⚙️ Dual Execution Modes**: Sequential agent chains OR supervisor-based routing
- **🌍 Cultural Context**: Romanian traditional knowledge and recipes

## 🏗️ Architecture

```
Frontend (React) ←→ Backend (FastAPI + LangGraph) ←→ External APIs
                                ↓
                    ┌─────────────────────┐
                    │     Supervisor      │
                    │   (Route Requests)  │
                    └─────────────────────┘
                              ↓
         ┌────────────────────┼────────────────────┐
         ↓                    ↓                    ↓
    ┌─────────┐        ┌──────────────┐    ┌──────────────┐
    │ Granny  │        │Story Creator │    │Parody Creator│
    │ Agent   │        │    Agent     │    │    Agent     │
    └─────────┘        └──────────────┘    └──────────────┘
         ↓                    ↓                    ↓
    ┌─────────────────────────────────────────────────────┐
    │              Tools & Knowledge Base                 │
    │         • Web Search  • Recipe Database             │
    └─────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Node.js 16+** 
- **OpenAI API Key**
- **Tavily API Key** (for web search)

### 1. 📁 Clone Repository

```bash
git clone <repository-url>
cd ma
```

### 2. 🔑 Environment Setup

Create environment file:
```bash
cp .env.example .env
```

Add your API keys to `.env`:
```bash
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

### 3. 🔧 Backend Setup

Navigate to backend directory:
```bash
cd backend
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

**Alternative with virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 🎨 Frontend Setup

Navigate to frontend directory:
```bash
cd frontend
```

Install Node.js dependencies:
```bash
npm install
```

---

## 🏃‍♂️ Running the Application

### Backend Server

From the `backend` directory:

```bash
uvicorn src.agent.graph:app --reload
```

**Backend runs on:** `http://localhost:8000`

**API Documentation:** `http://localhost:8000/docs`

### Frontend Application

From the `frontend` directory:

```bash
npm start
```

**Frontend runs on:** `http://localhost:3000`

### ✅ Verify Setup

1. **Backend Health Check:**
   ```bash
   curl http://localhost:8000/chats
   ```

2. **Frontend Access:**
   Open `http://localhost:3000` in your browser

3. **Create a Chat:**
   - Click "New Chat" in the frontend
   - Configure agents or enable supervisor mode
   - Send a test message

---

## 🎮 Usage Guide

### Sequential Mode (Manual Configuration)

1. **Create New Chat**
2. **Configure Agent Sequence:**
   - Drag agents from the palette
   - Enable/disable agents as needed
   - Assign tools to agents
3. **Send Messages:**
   - Messages flow through enabled agents sequentially
   - Each agent adds its perspective

### Supervisor Mode (Intelligent Routing)

1. **Enable Supervisor Mode:**
   - Toggle "Supervisor Mode" in the chat interface
   - Choose "Basic" or "Advanced" supervisor type
2. **Natural Conversation:**
   - Ask questions naturally
   - Supervisor automatically routes to appropriate agents
   - Tools are intelligently selected

### Example Conversations

**Recipe Request:**
```
User: "Tell me how to make traditional Romanian ciorba"
→ Routes to Granny + Knowledge Base tool
```

**Creative Writing:**
```
User: "Write a story about a magical forest"
→ Routes to Story Creator agent
```

**Humor Request:**
```
User: "Make a funny parody of that recipe"
→ Routes to Parody Creator agent
```

**Complex Request:**
```
User: "What's the weather today and can you tell me a funny story about it?"
→ Supervisor analyzes → Web Search + Story Creator/Parody Creator
```

---

## 🛠️ Development

### Project Structure

```
ma/
├── backend/
│   ├── src/agent/
│   │   ├── graph.py              # Main FastAPI app
│   │   ├── state.py              # Data models
│   │   ├── granny/agent.py       # Romanian grandmother
│   │   ├── story_creator/agent.py # Creative writer
│   │   ├── parody_creator/agent.py # Humor specialist
│   │   ├── supervisor/           # Intelligent routing
│   │   └── tools/                # Web search, knowledge base
│   └── requirements.txt
├── frontend/
│   ├── src/App.js               # React main component
│   ├── package.json
│   └── public/
├── docs/                        # Technical documentation
└── README.md
```

### Adding New Agents

1. **Create Agent File:**
   ```python
   # backend/src/agent/new_agent/agent.py
   def create_new_agent(state: State) -> dict:
       # Implementation
       return {"new_agent_output": response}
   ```

2. **Register Agent:**
   ```python
   # In graph.py
   AGENTS_REGISTRY = {
       "new_agent": create_new_agent,
       # ... existing agents
   }
   ```

3. **Update Frontend:**
   ```javascript
   // In App.js
   const ALL_AGENTS = ["granny", "story_creator", "parody_creator", "new_agent"];
   ```

### Adding New Tools

1. **Implement Tool** (`backend/src/agent/tools/new_tool.py`)
2. **Add Metadata** (`tool_config.py`)
3. **Register in Executor** (`tool_executor.py`)
4. **Update Intelligence Logic** (trigger patterns)

### Running Tests

```bash
# Backend tests
cd backend
python -m pytest test_*.py

# Frontend tests
cd frontend
npm test
```

---

## 🔧 Configuration

### Agent Configuration

```python
# Example agent sequence configuration
{
    "agent_sequence": [
        {
            "id": "granny",
            "enabled": true,
            "tools": ["knowledgebase", "web_search"]
        },
        {
            "id": "story_creator", 
            "enabled": true,
            "tools": []
        }
    ],
    "supervisor_mode": false,
    "supervisor_type": "basic"
}
```

### Tool Configuration

```python
# Intelligent tool selection triggers
WEB_SEARCH_TRIGGERS = ["today", "current", "weather", "news", "latest"]
KNOWLEDGEBASE_TRIGGERS = ["recipe", "ciorba", "traditional", "romanian"]
```

### Environment Variables

```bash
# Required
OPENAI_API_KEY=your_openai_key
TAVILY_API_KEY=your_tavily_key

# Optional
LANGSMITH_API_KEY=your_langsmith_key  # For tracing
```

---

## 🧪 API Reference

### Key Endpoints

- **`GET /chats`** - List all conversations
- **`POST /chats`** - Create new conversation
- **`POST /chats/{id}/settings`** - Configure agents and tools
- **`POST /chats/{id}/message/stream`** - Send message with streaming
- **`POST /chats/{id}/supervisor`** - Toggle supervisor mode
- **`GET /knowledgebase`** - View available knowledge

### WebSocket Streaming

The system uses Server-Sent Events for real-time response streaming:

```javascript
const response = await fetch('/chats/{id}/message/stream', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({user_prompt: message})
});

const reader = response.body.getReader();
// Handle streaming chunks
```

---

## 📚 Documentation

- **[Technical Documentation](./TECHNICAL_DOCUMENTATION.md)** - Complete system architecture
- **[API Documentation](http://localhost:8000/docs)** - Interactive API explorer
- **[Agent Documentation](./docs/)** - Agent implementation guides

---

## 🐛 Troubleshooting

### Common Issues

**Backend Won't Start:**
```bash
# Check Python version
python --version  # Should be 3.9+

# Install missing dependencies
pip install -r backend/requirements.txt

# Check port availability
netstat -an | grep 8000
```

**Frontend Connection Issues:**
```bash
# Verify backend is running
curl http://localhost:8000/chats

# Check CORS settings in backend/src/agent/graph.py
```

**API Key Issues:**
```bash
# Verify .env file exists and has correct keys
cat .env

# Test OpenAI connection
python -c "import openai; print('OpenAI key valid')"
```

**Missing Knowledge Base:**
```bash
# Check if knowledgebase.json exists
ls backend/src/data/knowledgebase.json

# File will be auto-created on first run if missing
```

### Performance Issues

- **Slow Responses:** Check API key limits and network connectivity
- **Memory Usage:** Monitor conversation history; implement pruning if needed  
- **Tool Timeouts:** Adjust timeout settings in tool configurations

---

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch** (`git checkout -b feature/amazing-feature`)
3. **Implement changes** with tests
4. **Commit changes** (`git commit -m 'Add amazing feature'`)
5. **Push to branch** (`git push origin feature/amazing-feature`)
6. **Open Pull Request**

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- **LangGraph** - Multi-agent orchestration framework
- **FastAPI** - High-performance web framework
- **React** - Frontend user interface
- **OpenAI** - Language model capabilities
- **Tavily** - Web search integration

---

**🚀 Happy Chatting with Romanian Grandmother Wisdom, Creative Stories, and Hilarious Parodies!**
