import React, { useEffect, useRef, useState } from "react";
import axios from "axios";

// Add CSS animations
const styles = `
  * {
    box-sizing: border-box;
  }
  
  html, body {
    margin: 0;
    padding: 0;
    height: 100%;
    overflow: hidden;
  }
  
  #root {
    height: 100vh;
    overflow: hidden;
  }
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  @keyframes slideIn {
    from { opacity: 0; transform: translateX(-20px); }
    to { opacity: 1; transform: translateX(0); }
  }
  
  ::-webkit-scrollbar {
    width: 6px;
  }
  
  ::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 10px;
  }
  
  ::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 10px;
  }
  
  ::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
  }
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement("style");
  styleSheet.type = "text/css";
  styleSheet.innerText = styles;
  document.head.appendChild(styleSheet);
}

export default function App() {
  const [chats, setChats] = useState([]);
  const [current, setCurrent] = useState(null);
  const [flow, setFlow] = useState([]);
  const [history, setHistory] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [knowledgebaseOptions, setKnowledgebaseOptions] = useState({});
  const [supervisorMode, setSupervisorMode] = useState(false);
  const [supervisorType, setSupervisorType] = useState("enhanced");
  const [supervisorAvailable, setSupervisorAvailable] = useState(false);
  
  // Dynamic loading state for agents and tools
  const [allAgents, setAllAgents] = useState([]);
  const [allTools, setAllTools] = useState([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [toolsLoading, setToolsLoading] = useState(true);
  const [agentFilter, setAgentFilter] = useState("");
  const [selectedCapability, setSelectedCapability] = useState("");

  const dragItem = useRef();
  const dragType = useRef();
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Load agents from API
  const loadAgents = async () => {
    try {
      setAgentsLoading(true);
      const response = await axios.get("http://localhost:8000/agents");
      setAllAgents(response.data.agents);
      console.log("Loaded agents:", response.data.agents);
    } catch (err) {
      console.error("Error loading agents:", err);
      // Fallback to original agents if API fails
      setAllAgents([
        { id: "granny", name: "Romanian Grandmother", capabilities: ["cooking", "wisdom"], skills: [] },
        { id: "story_creator", name: "Creative Story Writer", capabilities: ["creative_writing"], skills: ["creative_writing"] },
        { id: "parody_creator", name: "Parody Creator", capabilities: ["humor"], skills: ["creative_writing"] }
      ]);
    } finally {
      setAgentsLoading(false);
    }
  };

  // Load tools from API
  const loadTools = async () => {
    try {
      setToolsLoading(true);
      const response = await axios.get("http://localhost:8000/tools");
      setAllTools(response.data.tools);
      console.log("Loaded tools:", response.data.tools);
    } catch (err) {
      console.error("Error loading tools:", err);
      // Fallback to original tools if API fails
      setAllTools([
        { id: "web_search", name: "Web Search", description: "Search the internet for information" },
        { id: "knowledgebase", name: "Knowledge Base", description: "Access stored knowledge and documents" }
      ]);
    } finally {
      setToolsLoading(false);
    }
  };



  // Filter agents based on search and capability
  const filteredAgents = allAgents.filter(agent => {
    const matchesSearch = agentFilter === "" || 
      agent.name.toLowerCase().includes(agentFilter.toLowerCase()) ||
      agent.id.toLowerCase().includes(agentFilter.toLowerCase()) ||
      agent.capabilities.some(cap => cap.toLowerCase().includes(agentFilter.toLowerCase()));
    
    const matchesCapability = selectedCapability === "" || 
      agent.capabilities.includes(selectedCapability);
    
    return matchesSearch && matchesCapability;
  });

  // Get unique capabilities for filter dropdown
  const allCapabilities = [...new Set(allAgents.flatMap(agent => agent.capabilities))].sort();

  useEffect(() => {
    // Load all dynamic data from APIs
    const loadAllData = async () => {
      await Promise.all([
        loadAgents(),
        loadTools()
      ]);
    };
    
    loadAllData();
    
    // Load knowledgebase options
    axios.get("http://localhost:8000/knowledgebase")
      .then(({ data }) => setKnowledgebaseOptions(data))
      .catch((err) => console.error("Error loading knowledgebase:", err));
    
    // Load existing chats
    axios.get("http://localhost:8000/chats")
      .then(({ data }) => setChats(data))
      .catch((err) => console.error("Error loading chats:", err));
  }, []);

  useEffect(scrollToBottom, [history]);

  // Auto-create a chat on load only if no chats exist
  useEffect(() => {
    if (!current && chats.length === 0) {
      newChat();
    }
  }, [current, chats]);

  const loadChat = async (chatId) => {
    const res = await axios.get(`http://localhost:8000/chats/${chatId}`);
    setCurrent(chatId);
    setFlow(res.data.agent_sequence);
    setHistory(res.data.history);
    setSupervisorMode(res.data.supervisor_mode || false);
    setSupervisorType("enhanced"); // Always enhanced now
    
    // Check supervisor availability for this chat
    try {
      const supervisorRes = await axios.get(`http://localhost:8000/chats/${chatId}/supervisor`);
      setSupervisorAvailable(supervisorRes.data.supervisor_available);
    } catch (err) {
      console.warn("Could not check supervisor availability:", err);
      setSupervisorAvailable(false);
    }
  };

  const newChat = async () => {
    const res = await axios.post("http://localhost:8000/chats");
    setChats((prev) => [res.data, ...prev]);
    loadChat(res.data.id);
  };

  const saveSettings = async (newFlow, newSupervisorMode = supervisorMode) => {
    if (!current) {
      console.warn("No active chat. Cannot save settings.");
      return;
    }
    try {
      await axios.post(`http://localhost:8000/chats/${current}/settings`, {
        agent_sequence: newFlow,
        supervisor_mode: newSupervisorMode,
      });
      setFlow(newFlow);
      setSupervisorMode(newSupervisorMode);
    } catch (err) {
      console.error("Failed to save settings:", err);
    }
  };

  const toggleSupervisorMode = async (enabled) => {
    if (!current) return;
    try {
      await axios.post(`http://localhost:8000/chats/${current}/supervisor?enabled=${enabled}`);
      setSupervisorMode(enabled);
    } catch (err) {
      console.error("Failed to toggle supervisor mode:", err);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !current) return;
    setLoading(true);
    
    // Add user message immediately
    const userMessage = { sender: "user", text: input };
    setHistory((h) => [...h, userMessage]);
    const currentInput = input;
    setInput("");

    try {
      const response = await fetch(`http://localhost:8000/chats/${current}/message/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_prompt: currentInput }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      // Track streaming messages
      const streamingMessages = new Map();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim());

        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            
            if (data.sender === "tool") {
              // Handle tool messages (complete messages)
              setHistory((h) => [...h, {
                sender: "tool",
                text: data.text,
                tool_id: data.tool_id,
                for_agent: data.for_agent,
                via_supervisor: data.via_supervisor || false
              }]);
            } else if (data.sender === "supervisor") {
              // Handle supervisor routing decisions
              setHistory((h) => [...h, {
                sender: "supervisor",
                text: data.text,
                routing_decision: data.routing_decision,
                chosen_agent: data.chosen_agent,
                supervisor_type: data.supervisor_type
              }]);
            } else if (data.via_supervisor) {
              // Handle agent responses via supervisor
              setHistory((h) => [...h, {
                sender: data.sender,
                text: data.text,
                via_supervisor: true,
                supervisor_type: data.supervisor_type
              }]);
            } else if (data.sender === "system" && data.error) {
              // Handle system error messages
              setHistory((h) => [...h, {
                sender: "system",
                text: data.text,
                error: true
              }]);
            } else if (data.stream_start) {
              // Start of agent streaming
              const messageId = `${data.sender}-stream`;
              streamingMessages.set(messageId, "");
              setHistory((h) => [...h, {
                sender: data.sender,
                text: "",
                streaming: true,
                id: messageId
              }]);
            } else if (data.stream_chunk) {
              // Streaming chunk
              const messageId = `${data.sender}-stream`;
              const currentText = streamingMessages.get(messageId) || "";
              const newText = currentText + data.text;
              streamingMessages.set(messageId, newText);
              
              setHistory((h) => h.map(msg => 
                msg.id === messageId 
                  ? { ...msg, text: newText }
                  : msg
              ));
            } else if (data.stream_end) {
              // End of agent streaming
              const messageId = `${data.sender}-stream`;
              setHistory((h) => h.map(msg => 
                msg.id === messageId 
                  ? { ...msg, text: data.text, streaming: false, id: undefined }
                  : msg
              ));
              streamingMessages.delete(messageId);
            }
          } catch (e) {
            console.error("Error parsing streaming data:", e);
          }
        }
      }
    } catch (err) {
      console.error("Streaming failed:", err);
      // Fallback to non-streaming
      try {
        const res = await axios.post(`http://localhost:8000/chats/${current}/message`, {
          user_prompt: currentInput,
        });

        const newMessages = [];
        
                          // Handle system errors from supervisor mode
        if (res.data.error && res.data.system_error) {
          newMessages.push({
            sender: "system",
            text: res.data.system_error,
            error: true
          });
        } else if (res.data.supervisor_routing) {
            // Add supervisor decision if available
            if (res.data.supervisor_decision) {
              newMessages.push({
                sender: "supervisor",
                text: res.data.supervisor_decision,
                routing_decision: true,
                chosen_agent: res.data.chosen_agent,
                supervisor_type: res.data.supervisor_type
              });
            }
            
            // Add tool outputs from supervisor if available
            if (res.data.tool_outputs) {
              for (const [toolName, toolResult] of Object.entries(res.data.tool_outputs)) {
                let text_result;
                if (typeof toolResult === 'object' && toolResult.result) {
                  text_result = toolResult.result;
                } else {
                  text_result = toolResult;
                }
                
                newMessages.push({ 
                  sender: "tool", 
                  text: text_result,
                  tool_id: toolName,
                  for_agent: res.data.chosen_agent,
                  via_supervisor: true
                });
              }
            }
            
            // Add agent response via supervisor
            if (res.data.agent_response) {
              newMessages.push({
                sender: res.data.chosen_agent,
                text: res.data.agent_response,
                via_supervisor: true,
                supervisor_type: res.data.supervisor_type
              });
            }
          } else {
          // Handle regular sequential mode responses
          
          // Process tool outputs correctly
          if (res.data.tool_outputs) {
            for (const [toolName, toolResult] of Object.entries(res.data.tool_outputs)) {
              // Extract text from result (could be string or dict)
              let text_result;
              if (typeof toolResult === 'object' && toolResult.result) {
                text_result = toolResult.result;
              } else {
                text_result = toolResult;
              }
              
              newMessages.push({ 
                sender: "tool", 
                text: text_result,
                tool_id: toolName,
                for_agent: toolResult.agent || "unknown"
              });
            }
          }
          
          // Process agent outputs
          if (res.data.granny_output) newMessages.push({ sender: "granny", text: res.data.granny_output });
          if (res.data.story_output) newMessages.push({ sender: "story_creator", text: res.data.story_output });
          if (res.data.parody_output) newMessages.push({ sender: "parody_creator", text: res.data.parody_output });
        }

        setHistory((h) => [...h, ...newMessages]);
      } catch (fallbackErr) {
        console.error("Fallback also failed:", fallbackErr);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDropAgent = (idx) => {
    if (dragType.current !== "agent") return;
    const newAgent = { id: dragItem.current, enabled: true, tools: [] };
    const updated = [...flow];
    updated.splice(idx, 0, newAgent);
    saveSettings(updated);
  };

  const handleDropTool = (agentIdx) => {
    if (dragType.current !== "tool") return;
    const tool = dragItem.current;
    const updated = [...flow];
    const agent = { ...updated[agentIdx] };
    agent.tools = agent.tools || [];

    if (!agent.tools.find((t) => typeof t === "string" ? t === tool : t.name === tool)) {
      const newTool = tool === "knowledgebase" ? { name: "knowledgebase", option: null } : tool;
      agent.tools.push(newTool);
    }

    updated[agentIdx] = agent;
    saveSettings(updated);
  };

  const removeAgent = (idx) => {
    const updated = [...flow];
    updated.splice(idx, 1);
    saveSettings(updated);
  };

  const removeTool = (agentIdx, tool) => {
    const updated = [...flow];
    updated[agentIdx].tools = updated[agentIdx].tools.filter((t) => {
      return typeof t === "string" ? t !== tool : t.name !== tool;
    });
    saveSettings(updated);
  };

  const updateKnowledgeOption = (agentIdx, toolIdx, newValue) => {
    const updated = [...flow];
    updated[agentIdx].tools[toolIdx].option = newValue;
    saveSettings(updated);
  };

  return (
    <>
      <style>
        {`
          @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
          }
          @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
          }
        `}
      </style>
      <div style={{ 
        display: "flex", 
        height: "100vh", 
        fontFamily: "'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        background: "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)",
        overflow: "hidden",
        margin: 0,
        padding: 0
      }}>
      {/* Sidebar */}
      <aside style={{ 
        width: 280, 
        background: "#ffffff",
        boxShadow: "0 4px 20px rgba(0, 0, 0, 0.08)",
        borderRight: "1px solid #e2e8f0",
        color: "#334155", 
        padding: "24px 20px",
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden"
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          marginBottom: "24px",
          paddingBottom: "16px",
          borderBottom: "1px solid #e2e8f0"
        }}>
          <div style={{
            width: "36px",
            height: "36px",
            background: "#1e40af",
            borderRadius: "8px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginRight: "12px",
            color: "#ffffff"
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
          </div>
          <h3 style={{ 
            margin: 0, 
            fontSize: "18px", 
            fontWeight: "600",
            color: "#1e293b"
          }}>
            Conversations
          </h3>
        </div>

        <button onClick={newChat} style={{ 
          margin: "0 0 20px 0", 
          width: "100%",
          padding: "12px 16px",
          background: "#1e40af",
          color: "#fff",
          border: "none",
          borderRadius: "8px",
          cursor: "pointer",
          fontSize: "14px",
          fontWeight: "500",
          transition: "all 0.2s ease"
        }}
        onMouseEnter={(e) => {
          e.target.style.background = "#1d4ed8";
        }}
        onMouseLeave={(e) => {
          e.target.style.background = "#1e40af";
        }}>
          + New Chat
        </button>
        
        {/* Scrollable chat list */}
        <div style={{
          flex: 1,
          overflowY: "auto",
          paddingRight: "4px",
          minHeight: 0
        }}>
          {chats.slice().reverse().map((chat, index) => (
            <button
              key={chat.id}
              onClick={() => loadChat(chat.id)}
              style={{
                display: "block",
                marginBottom: "8px",
                padding: "12px 16px",
                width: "100%",
                background: chat.id === current 
                  ? "#1e40af" 
                  : "#f8fafc",
                color: chat.id === current ? "#fff" : "#475569",
                border: chat.id === current 
                  ? "none" 
                  : "1px solid #e2e8f0",
                borderRadius: "6px",
                cursor: "pointer",
                textAlign: "left",
                fontSize: "13px",
                fontWeight: "500",
                transition: "all 0.2s ease",
                userSelect: "none"
              }}
              onMouseEnter={(e) => {
                if (chat.id !== current) {
                  e.target.style.background = "#e2e8f0";
                }
              }}
              onMouseLeave={(e) => {
                if (chat.id !== current) {
                  e.target.style.background = "#f8fafc";
                }
              }}
              onMouseDown={(e) => {
                e.preventDefault(); // Prevent text selection
              }}
            >
              <div style={{ display: "flex", alignItems: "center" }}>
                <div style={{
                  width: "8px",
                  height: "8px",
                  background: chat.id === current ? "#60a5fa" : "#94a3b8",
                  borderRadius: "50%",
                  marginRight: "10px"
                }}></div>
                <span>Chat {chats.length - index}</span>
              </div>
              <div style={{ 
                fontSize: "11px", 
                opacity: 0.7, 
                marginTop: "2px",
                fontFamily: "monospace"
              }}>
                {chat.id.slice(0, 8)}
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* Main Chat Area */}
      <main style={{ 
        flex: 1, 
        display: "flex", 
        flexDirection: "column",
        background: "#ffffff",
        height: "100vh",
        overflow: "hidden"
      }}>
        {/* Chat Header */}
        <div style={{
          padding: "20px 24px",
          background: "#ffffff",
          borderBottom: "1px solid #e2e8f0",
          boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)"
        }}>
          <h2 style={{
            margin: 0,
            fontSize: "18px",
            fontWeight: "600",
            color: "#1e293b",
            display: "flex",
            alignItems: "center"
          }}>
            <div style={{
              width: "24px",
              height: "24px",
              background: "#1e40af",
              borderRadius: "4px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginRight: "10px",
              color: "#ffffff"
            }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14l4 4V4c0-1.1-.9-2-2-2z"/>
              </svg>
            </div>
            {current ? `Chat ${chats.length - chats.findIndex(c => c.id === current)}` : "New Chat"}
          </h2>
        </div>

        <div style={{ 
          flex: 1, 
          padding: "24px", 
          overflowY: "auto",
          background: "#f8fafc",
          minHeight: 0
        }}>
          {history.map((m, i) => (
            <div key={i} style={{
              display: "flex",
              justifyContent: m.sender === "user" ? "flex-end" : "flex-start",
              marginBottom: "16px",
              animation: "fadeIn 0.3s ease-in"
            }}>
              <div style={{
                padding: "16px 20px",
                borderRadius: "18px",
                maxWidth: "75%",
                background: m.sender === "user" 
                  ? "#1e40af" :
                  m.sender === "tool" 
                  ? "#fef3c7" : // Light cream for tools
                  m.sender === "supervisor"
                  ? "#f3e8ff" : // Light purple for supervisor
                  m.sender === "system" && m.error
                  ? "#fee2e2" : // Light red for system errors
                  m.sender === "granny" 
                  ? "#dbeafe" :
                  m.sender === "story_creator" 
                  ? "#dcfce7" :
                  m.sender === "parody_creator" 
                  ? "#fce7f3" :
                  "#ffffff",
                color: m.sender === "user" ? "#fff" : 
                       m.sender === "tool" ? "#92400e" : 
                       m.sender === "supervisor" ? "#7c3aed" : 
                       m.sender === "system" && m.error ? "#dc2626" : "#374151",
                border: m.sender === "tool" 
                  ? "1px solid #f59e0b" 
                  : m.sender === "supervisor"
                  ? "1px solid #8b5cf6"
                  : m.sender === "system" && m.error
                  ? "1px solid #ef4444"
                  : m.sender === "user" 
                  ? "none" 
                  : "1px solid #e5e7eb",
                boxShadow: "0 1px 3px rgba(0, 0, 0, 0.1)"
              }}>
                {m.sender === "tool" ? (
                  // Special design for tool messages
                  <div>
                    <div style={{ 
                      display: "flex", 
                      alignItems: "center", 
                      marginBottom: "12px",
                      padding: "8px 12px",
                      background: "#fbbf24",
                      borderRadius: "6px",
                      fontSize: "14px",
                      fontWeight: "600"
                    }}>
                      <div style={{
                        width: "20px",
                        height: "20px",
                        background: "#d97706",
                        borderRadius: "4px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        marginRight: "8px",
                        color: "#ffffff"
                      }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
                        </svg>
                      </div>
                      <span style={{ color: "#92400e" }}>Tool: {m.tool_id}</span>
                      {m.via_supervisor && (
                        <span style={{ 
                          marginLeft: "8px", 
                          fontSize: "10px",
                          color: "#ffffff",
                          background: "#8b5cf6",
                          padding: "2px 6px",
                          borderRadius: "3px",
                          fontWeight: "500"
                        }}>
                          VIA SUPERVISOR
                        </span>
                      )}
                      {m.for_agent && (
                        <span style={{ 
                          marginLeft: "auto", 
                          fontSize: "12px",
                          color: "#92400e",
                          background: "#ffffff",
                          padding: "4px 8px",
                          borderRadius: "4px",
                          fontWeight: "500"
                        }}>
                          pentru {m.for_agent}
                        </span>
                      )}
                    </div>
                    <div style={{ 
                      whiteSpace: "pre-wrap", 
                      fontSize: "14px",
                      lineHeight: "1.6",
                      color: "#92400e"
                    }}>
                      {m.text}
                    </div>
                  </div>
                ) : m.sender === "supervisor" ? (
                  // Special design for supervisor routing messages
                  <div>
                    <div style={{ 
                      display: "flex", 
                      alignItems: "center", 
                      marginBottom: "12px",
                      padding: "8px 12px",
                      background: "#8b5cf6",
                      borderRadius: "6px",
                      fontSize: "14px",
                      fontWeight: "600"
                    }}>
                      <div style={{
                        width: "20px",
                        height: "20px",
                        background: "#7c3aed",
                        borderRadius: "4px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        marginRight: "8px",
                        color: "#ffffff"
                      }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                        </svg>
                      </div>
                      <span style={{ color: "#ffffff" }}>🤖 Supervisor Routing</span>
                      {m.chosen_agent && (
                        <span style={{ 
                          marginLeft: "auto", 
                          fontSize: "12px",
                          color: "#7c3aed",
                          background: "#ffffff",
                          padding: "4px 8px",
                          borderRadius: "4px",
                          fontWeight: "500"
                        }}>
                          → {m.chosen_agent}
                        </span>
                      )}
                    </div>
                    <div style={{ 
                      whiteSpace: "pre-wrap", 
                      fontSize: "14px",
                      lineHeight: "1.6",
                      color: "#7c3aed"
                    }}>
                      {m.text}
                    </div>
                    {m.chosen_agent && (
                      <div style={{
                        marginTop: "8px",
                        padding: "6px 10px",
                        background: "#ffffff",
                        borderRadius: "4px",
                        fontSize: "12px",
                        color: "#6b7280",
                        border: "1px solid #d1d5db"
                      }}>
                        🎯 Delegated to <strong>{
                          m.chosen_agent === "granny" ? "Granny" :
                          m.chosen_agent === "story_creator" ? "Story Creator" :
                          m.chosen_agent === "parody_creator" ? "Parody Creator" :
                          m.chosen_agent
                        }</strong> ({m.supervisor_type} routing)
                      </div>
                                         )}
                   </div>
                 ) : m.sender === "system" && m.error ? (
                   // Special design for system error messages
                   <div>
                     <div style={{ 
                       display: "flex", 
                       alignItems: "center", 
                       marginBottom: "12px",
                       padding: "8px 12px",
                       background: "#ef4444",
                       borderRadius: "6px",
                       fontSize: "14px",
                       fontWeight: "600"
                     }}>
                       <div style={{
                         width: "20px",
                         height: "20px",
                         background: "#dc2626",
                         borderRadius: "4px",
                         display: "flex",
                         alignItems: "center",
                         justifyContent: "center",
                         marginRight: "8px",
                         color: "#ffffff"
                       }}>
                         <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                           <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                         </svg>
                       </div>
                       <span style={{ color: "#ffffff" }}>⚠️ System Error</span>
                     </div>
                     <div style={{ 
                       whiteSpace: "pre-wrap", 
                       fontSize: "14px",
                       lineHeight: "1.6",
                       color: "#dc2626"
                     }}>
                       {m.text}
                     </div>
                   </div>
                 ) : (
                  // Modern design for agent messages
                  <div>
                    <div style={{
                      display: "flex",
                      alignItems: "center",
                      marginBottom: "8px",
                      fontSize: "14px",
                      fontWeight: "600",
                      color: m.sender === "user" ? "rgba(255, 255, 255, 0.9)" : "#374151"
                    }}>
                      <div style={{
                        width: "20px",
                        height: "20px",
                        background: m.sender === "user" ? "#3b82f6" : 
                                   m.sender === "granny" ? "#3b82f6" :
                                   m.sender === "story_creator" ? "#10b981" :
                                   m.sender === "parody_creator" ? "#ec4899" : "#6b7280",
                        borderRadius: "4px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        marginRight: "8px",
                        color: "#ffffff",
                        fontSize: "12px"
                      }}>
                        {m.sender === "granny" ? "G" :
                         m.sender === "story_creator" ? "S" :
                         m.sender === "parody_creator" ? "P" :
                         m.sender === "user" ? "U" : "A"}
                      </div>
                      {m.sender === "granny" ? "Granny" :
                       m.sender === "story_creator" ? "Story Creator" :
                       m.sender === "parody_creator" ? "Parody Creator" :
                       m.sender === "user" ? "You" :
                       m.sender}
                      {m.via_supervisor && (
                        <span style={{
                          marginLeft: "8px",
                          fontSize: "10px",
                          background: "#8b5cf6",
                          color: "#ffffff",
                          padding: "2px 6px",
                          borderRadius: "3px",
                          fontWeight: "500"
                        }}>
                          VIA SUPERVISOR
                        </span>
                      )}
                    </div>
                    <div style={{ 
                      whiteSpace: "pre-wrap", 
                      fontSize: "14px",
                      lineHeight: "1.6",
                      color: m.sender === "user" ? "#fff" : "#374151",
                      position: "relative"
                    }}>
                      {m.text}
                      {m.streaming && (
                        <span style={{
                          display: "inline-block",
                          width: "8px",
                          height: "14px",
                          background: "#374151",
                          marginLeft: "2px",
                          animation: "blink 1s infinite",
                          borderRadius: "1px"
                        }} />
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Modern Input Area */}
        <div style={{ 
          padding: "20px 24px",
          background: "#ffffff",
          borderTop: "1px solid #e2e8f0",
          boxShadow: "0 -1px 3px rgba(0, 0, 0, 0.05)"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <input
              style={{ 
                flex: 1, 
                padding: "12px 16px", 
                borderRadius: "8px", 
                border: "1px solid #d1d5db",
                fontSize: "14px",
                background: "#ffffff",
                color: "#374151",
                outline: "none",
                transition: "all 0.2s ease"
              }}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Scrie mesajul tău aici..."
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              onFocus={(e) => {
                e.target.style.borderColor = "#1e40af";
                e.target.style.boxShadow = "0 0 0 3px rgba(30, 64, 175, 0.1)";
              }}
              onBlur={(e) => {
                e.target.style.borderColor = "#d1d5db";
                e.target.style.boxShadow = "none";
              }}
            />
            <button 
              onClick={sendMessage} 
              disabled={loading}
              style={{ 
                padding: "12px 20px",
                background: loading ? "#9ca3af" : "#1e40af",
                color: "#fff",
                border: "none",
                borderRadius: "8px",
                cursor: loading ? "not-allowed" : "pointer",
                fontSize: "14px",
                fontWeight: "500",
                transition: "all 0.2s ease",
                minWidth: "80px"
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  e.target.style.background = "#1d4ed8";
                }
              }}
              onMouseLeave={(e) => {
                if (!loading) {
                  e.target.style.background = "#1e40af";
                }
              }}
            >
              {loading ? "..." : "Send"}
            </button>
          </div>
        </div>
      </main>

      {/* Modern Configuration Panel */}
      <aside style={{ 
        width: 350, 
        background: "#ffffff",
        borderLeft: "1px solid #e2e8f0",
        boxShadow: "-4px 0 20px rgba(0, 0, 0, 0.08)",
        padding: "24px 20px",
        overflowY: "auto",
        height: "100vh",
        display: "flex",
        flexDirection: "column"
      }}>
        <div style={{
          display: "flex",
          alignItems: "center",
          marginBottom: "24px",
          paddingBottom: "16px",
          borderBottom: "1px solid #e2e8f0"
        }}>
          <div style={{
            width: "32px",
            height: "32px",
            background: "#1e40af",
            borderRadius: "6px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginRight: "12px",
            color: "#ffffff"
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 15.5A3.5 3.5 0 0 1 8.5 12A3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.43-2.53c.04-.32.07-.64.07-.97 0-.33-.03-.66-.07-1l2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.31-.61-.22l-2.49 1c-.52-.39-1.06-.73-1.69-.98l-.37-2.65A.506.506 0 0 0 14 2h-4c-.25 0-.46.18-.5.42l-.37 2.65c-.63.25-1.17.59-1.69.98l-2.49-1c-.22-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64L4.57 11c-.04.34-.07.67-.07 1 0 .33.03.65.07.97l-2.11 1.66c-.19.15-.25.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1.01c.52.4 1.06.74 1.69.99l.37 2.65c.04.24.25.42.5.42h4c.25 0 .46-.18.5-.42l.37-2.65c.63-.26 1.17-.59 1.69-.99l2.49 1.01c.22.08.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.66Z"/>
            </svg>
          </div>
          <h3 style={{ 
            margin: 0, 
            fontSize: "16px", 
            fontWeight: "600",
            color: "#1e293b"
          }}>
            Configuration
          </h3>
        </div>

        <div style={{ 
          marginBottom: "20px",
          opacity: supervisorMode ? 0.5 : 1,
          pointerEvents: supervisorMode ? "none" : "auto"
        }}>
          <h4 style={{ 
            fontSize: "14px", 
            fontWeight: "600", 
            color: supervisorMode ? "#9ca3af" : "#374151", 
            marginBottom: "12px",
            display: "flex",
            alignItems: "center"
          }}>
            <div style={{
              width: "16px",
              height: "16px",
              background: supervisorMode ? "#9ca3af" : "#3b82f6",
              borderRadius: "3px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginRight: "8px",
              color: "#ffffff",
              fontSize: "10px"
            }}>
              A
            </div>
            Available Agents ({filteredAgents.length})
            {supervisorMode && (
              <span style={{
                fontSize: "10px",
                background: "#f3f4f6",
                color: "#6b7280",
                padding: "2px 6px",
                borderRadius: "3px",
                marginLeft: "8px",
                fontWeight: "500"
              }}>
                AUTO-MANAGED
              </span>
            )}
          </h4>
          
          {/* Agent Search and Filter */}
          {!supervisorMode && (
            <div style={{ marginBottom: "12px", display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <input
                type="text"
                placeholder="Search agents by name or capability..."
                value={agentFilter}
                onChange={(e) => setAgentFilter(e.target.value)}
                style={{
                  padding: "6px 10px",
                  border: "1px solid #d1d5db",
                  borderRadius: "4px",
                  fontSize: "12px",
                  minWidth: "200px",
                  flexGrow: 1
                }}
              />
              <select
                value={selectedCapability}
                onChange={(e) => setSelectedCapability(e.target.value)}
                style={{
                  padding: "6px 10px",
                  border: "1px solid #d1d5db",
                  borderRadius: "4px",
                  fontSize: "12px",
                  background: "white"
                }}
              >
                <option value="">All Capabilities</option>
                {allCapabilities.map(cap => (
                  <option key={cap} value={cap}>{cap}</option>
                ))}
              </select>
            </div>
          )}
          
          {agentsLoading ? (
            <div style={{ 
              padding: "20px",
              textAlign: "center",
              color: "#6b7280",
              fontSize: "12px"
            }}>
              Loading agents...
            </div>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              {filteredAgents.map((agent) => (
                <div
                  key={agent.id}
                  draggable={!supervisorMode}
                  onDragStart={() => {
                    if (!supervisorMode) {
                      dragItem.current = agent.id;
                      dragType.current = "agent";
                    }
                  }}
                  style={{
                    padding: "10px 12px",
                    background: supervisorMode ? "#f3f4f6" : "#dbeafe",
                    border: `1px solid ${supervisorMode ? "#d1d5db" : "#3b82f6"}`,
                    borderRadius: "8px",
                    cursor: supervisorMode ? "not-allowed" : "grab",
                    fontSize: "12px",
                    fontWeight: "500",
                    color: supervisorMode ? "#6b7280" : "#1e40af",
                    transition: "all 0.2s ease",
                    userSelect: "none",
                    minWidth: "140px",
                    maxWidth: "200px"
                  }}
                  onMouseEnter={(e) => {
                    if (!supervisorMode) {
                      e.currentTarget.style.background = "#bfdbfe";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!supervisorMode) {
                      e.currentTarget.style.background = "#dbeafe";
                    }
                  }}
                  title={`${agent.description}\nCapabilities: ${agent.capabilities.join(', ')}\nSkills: ${agent.skills.join(', ') || 'None'}`}
                >
                  <div style={{ fontWeight: "600", marginBottom: "4px" }}>
                    {agent.name}
                  </div>
                  <div style={{ 
                    fontSize: "10px", 
                    color: supervisorMode ? "#9ca3af" : "#64748b",
                    marginBottom: "4px"
                  }}>
                    {agent.capabilities.slice(0, 2).join(', ')}
                    {agent.capabilities.length > 2 && '...'}
                  </div>
                  {agent.skills.length > 0 && (
                    <div style={{ 
                      fontSize: "9px", 
                      color: supervisorMode ? "#9ca3af" : "#059669",
                      fontWeight: "500"
                    }}>
                      ⚡ {agent.skills.length} skill{agent.skills.length !== 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ 
          marginBottom: "20px",
          opacity: supervisorMode ? 0.5 : 1,
          pointerEvents: supervisorMode ? "none" : "auto"
        }}>
          <h4 style={{ 
            fontSize: "14px", 
            fontWeight: "600", 
            color: supervisorMode ? "#9ca3af" : "#374151", 
            marginBottom: "12px",
            display: "flex",
            alignItems: "center"
          }}>
            <div style={{
              width: "16px",
              height: "16px",
              background: supervisorMode ? "#9ca3af" : "#f59e0b",
              borderRadius: "3px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginRight: "8px",
              color: "#ffffff",
              fontSize: "10px"
            }}>
              T
            </div>
            Available Tools
            {supervisorMode && (
              <span style={{
                fontSize: "10px",
                background: "#f3f4f6",
                color: "#6b7280",
                padding: "2px 6px",
                borderRadius: "3px",
                marginLeft: "8px",
                fontWeight: "500"
              }}>
                AUTO-MANAGED
              </span>
            )}
          </h4>
          {toolsLoading ? (
            <div style={{ 
              padding: "20px",
              textAlign: "center",
              color: "#6b7280",
              fontSize: "12px"
            }}>
              Loading tools...
            </div>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              {allTools.map((tool) => (
                <div
                  key={tool.id}
                  draggable={!supervisorMode}
                  onDragStart={() => {
                    if (!supervisorMode) {
                      dragItem.current = tool.id;
                      dragType.current = "tool";
                    }
                  }}
                  style={{
                    padding: "10px 12px",
                    background: supervisorMode ? "#f3f4f6" : "#fef3c7",
                    border: `1px solid ${supervisorMode ? "#d1d5db" : "#f59e0b"}`,
                    borderRadius: "8px",
                    cursor: supervisorMode ? "not-allowed" : "grab",
                    fontSize: "12px",
                    fontWeight: "500",
                    color: supervisorMode ? "#6b7280" : "#92400e",
                    transition: "all 0.2s ease",
                    userSelect: "none",
                    minWidth: "120px",
                    maxWidth: "180px"
                  }}
                  onMouseEnter={(e) => {
                    if (!supervisorMode) {
                      e.currentTarget.style.background = "#fde68a";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!supervisorMode) {
                      e.currentTarget.style.background = "#fef3c7";
                    }
                  }}
                  title={`${tool.description}\nUse cases: ${tool.use_cases ? tool.use_cases.join(', ') : 'General purpose'}`}
                >
                  <div style={{ fontWeight: "600", marginBottom: "4px" }}>
                    {tool.name}
                  </div>
                  <div style={{ 
                    fontSize: "10px", 
                    color: supervisorMode ? "#9ca3af" : "#78716c",
                    lineHeight: "1.3"
                  }}>
                    {tool.description.length > 50 ? 
                      tool.description.substring(0, 50) + '...' : 
                      tool.description}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Supervisor Mode Controls */}
        <div style={{ marginBottom: "20px" }}>
          <h4 style={{ 
            fontSize: "14px", 
            fontWeight: "600", 
            color: "#374151", 
            marginBottom: "12px",
            display: "flex",
            alignItems: "center"
          }}>
            <div style={{
              width: "16px",
              height: "16px",
              background: "#8b5cf6",
              borderRadius: "3px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginRight: "8px",
              color: "#ffffff",
              fontSize: "10px"
            }}>
              S
            </div>
            Supervisor Mode
            {!supervisorAvailable && (
              <span style={{
                fontSize: "10px",
                background: "#fef3c7",
                color: "#92400e",
                padding: "2px 6px",
                borderRadius: "3px",
                marginLeft: "8px",
                fontWeight: "500"
              }}>
                UNAVAILABLE
              </span>
            )}
          </h4>
          
          <div style={{ 
            background: supervisorMode ? "#f0f9ff" : "#f8fafc", 
            border: `1px solid ${supervisorMode ? "#0ea5e9" : "#e2e8f0"}`,
            borderRadius: "8px", 
            padding: "12px" 
          }}>
            <div style={{ marginBottom: "12px" }}>
              <label style={{ 
                display: "flex", 
                alignItems: "center", 
                fontSize: "13px", 
                fontWeight: "500",
                color: "#374151",
                cursor: supervisorAvailable ? "pointer" : "not-allowed"
              }}>
                <input
                  type="checkbox"
                  checked={supervisorMode}
                  disabled={!supervisorAvailable}
                  onChange={(e) => toggleSupervisorMode(e.target.checked)}
                  style={{
                    marginRight: "8px",
                    transform: "scale(1.1)",
                    cursor: supervisorAvailable ? "pointer" : "not-allowed"
                  }}
                />
                Enable Intelligent Agent Routing
              </label>
            </div>
            
            {supervisorMode && (
              <div style={{
                fontSize: "12px",
                color: "#6b7280",
                fontWeight: "500",
                display: "flex",
                alignItems: "center",
                padding: "8px 12px",
                background: "#f8fafc",
                border: "1px solid #e2e8f0",
                borderRadius: "6px"
              }}>
                🧠 Enhanced Intelligence Mode
              </div>
            )}
            
            <div style={{ 
              fontSize: "11px", 
              color: "#6b7280", 
              marginTop: "8px",
              lineHeight: "1.4"
            }}>
              {supervisorMode ? (
                <>🧠 AI will intelligently analyze your request, select the best agent from all 6 available agents, and orchestrate tools and resources</>
              ) : (
                <>⚙️ Use manual agent flow configuration below</>
              )}
            </div>
          </div>
        </div>

        <div style={{ flex: 1, minHeight: 0 }}>
          <h4 style={{ 
            fontSize: "14px", 
            fontWeight: "600", 
            color: supervisorMode ? "#9ca3af" : "#374151", 
            marginBottom: "16px",
            display: "flex",
            alignItems: "center",
            opacity: supervisorMode ? 0.6 : 1
          }}>
            <div style={{
              width: "16px",
              height: "16px",
              background: supervisorMode ? "#9ca3af" : "#10b981",
              borderRadius: "3px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginRight: "8px",
              color: "#ffffff",
              fontSize: "10px"
            }}>
              F
            </div>
            Manual Agent Flow
            {supervisorMode && (
              <span style={{
                fontSize: "10px",
                background: "#f3f4f6",
                color: "#6b7280",
                padding: "2px 6px",
                borderRadius: "3px",
                marginLeft: "8px",
                fontWeight: "500"
              }}>
                DISABLED
              </span>
            )}
          </h4>
          
                     <div style={{ 
             flex: 1,
             overflowY: "auto",
             paddingRight: "4px",
             minHeight: 0,
             opacity: supervisorMode ? 0.5 : 1,
             pointerEvents: supervisorMode ? "none" : "auto"
           }}>
            {flow.map((agent, idx) => (
              <div
                key={idx}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() =>
                  dragType.current === "agent"
                    ? handleDropAgent(idx)
                    : handleDropTool(idx)
                }
                style={{
                  marginBottom: "12px",
                  padding: "16px",
                  background: "#ffffff",
                  borderRadius: "8px",
                  border: "1px solid #e5e7eb",
                  boxShadow: "0 1px 3px rgba(0, 0, 0, 0.1)",
                  transition: "all 0.2s ease"
                }}
                onMouseEnter={(e) => {
                  e.target.style.boxShadow = "0 4px 6px rgba(0, 0, 0, 0.1)";
                }}
                onMouseLeave={(e) => {
                  e.target.style.boxShadow = "0 1px 3px rgba(0, 0, 0, 0.1)";
                }}
              >
                <div style={{ 
                  display: "flex", 
                  justifyContent: "space-between", 
                  alignItems: "center",
                  marginBottom: "12px"
                }}>
                  <div style={{ display: "flex", alignItems: "center" }}>
                    <div style={{
                      width: "20px",
                      height: "20px",
                      background: "#3b82f6",
                      borderRadius: "4px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      marginRight: "8px",
                      color: "#ffffff",
                      fontSize: "12px",
                      fontWeight: "600"
                    }}>
                      {agent.id === "granny" ? "G" :
                       agent.id === "story_creator" ? "S" :
                       agent.id === "parody_creator" ? "P" : "A"}
                    </div>
                    <span style={{ 
                      fontWeight: "600", 
                      fontSize: "14px", 
                      color: "#1e293b" 
                    }}>
                      {agent.id === "granny" ? "Granny" :
                       agent.id === "story_creator" ? "Story Creator" :
                       agent.id === "parody_creator" ? "Parody Creator" :
                       agent.id}
                    </span>
                  </div>
                  <button 
                    onClick={() => removeAgent(idx)}
                    style={{
                      background: "#ef4444",
                      color: "#ffffff",
                      border: "none",
                      borderRadius: "4px",
                      padding: "4px 8px",
                      fontSize: "12px",
                      cursor: "pointer",
                      transition: "all 0.2s ease"
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.background = "#dc2626";
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.background = "#ef4444";
                    }}
                  >
                    Remove
                  </button>
                </div>
                
                {agent.tools && agent.tools.length > 0 && (
                  <div>
                    <div style={{ 
                      fontSize: "12px", 
                      color: "#6b7280", 
                      marginBottom: "8px",
                      fontWeight: "500"
                    }}>
                      Tools:
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {agent.tools.map((tool, ti) => {
                        const toolName = typeof tool === "string" ? tool : tool.name;
                        return (
                          <div key={ti} style={{ 
                            display: "flex", 
                            alignItems: "center", 
                            gap: "6px",
                            background: "#fef3c7",
                            padding: "6px 10px",
                            borderRadius: "6px",
                            border: "1px solid #f59e0b"
                          }}>
                            <span style={{
                              fontSize: "11px",
                              fontWeight: "500",
                              color: "#92400e"
                            }}>
                              {toolName === "web_search" ? "Web Search" :
                               toolName === "knowledgebase" ? "Knowledge Base" :
                               toolName}
                            </span>
                                                         {toolName === "knowledgebase" && (
                               <select
                                 value={tool.option || ""}
                                 onChange={(e) => updateKnowledgeOption(idx, ti, e.target.value)}
                                 style={{ 
                                   fontSize: "11px",
                                   padding: "4px 8px",
                                   borderRadius: "6px",
                                   border: "1px solid #d1d5db",
                                   background: "#ffffff",
                                   color: "#374151",
                                   fontWeight: "500",
                                   cursor: "pointer",
                                   outline: "none",
                                   transition: "all 0.2s ease",
                                   minWidth: "120px"
                                 }}
                                 onFocus={(e) => {
                                   e.target.style.borderColor = "#3b82f6";
                                 }}
                                 onBlur={(e) => {
                                   e.target.style.borderColor = "#d1d5db";
                                 }}
                                 onMouseEnter={(e) => {
                                   e.target.style.borderColor = "#9ca3af";
                                 }}
                                 onMouseLeave={(e) => {
                                   if (e.target !== document.activeElement) {
                                     e.target.style.borderColor = "#d1d5db";
                                   }
                                 }}>
                                 <option value="" style={{ color: "#9ca3af" }}>Select option...</option>
                                 {Object.entries(knowledgebaseOptions).map(([key, entry]) => (
                                   <option key={key} value={key} style={{ color: "#374151", fontWeight: "500" }}>
                                     {entry.label}
                                   </option>
                                 ))}
                               </select>
                             )}
                            <button 
                              onClick={() => removeTool(idx, toolName)}
                              style={{
                                background: "#ef4444",
                                color: "#ffffff",
                                border: "none",
                                borderRadius: "3px",
                                padding: "2px 4px",
                                fontSize: "10px",
                                cursor: "pointer",
                                lineHeight: 1
                              }}
                            >
                              ×
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ))}
            
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => handleDropAgent(flow.length)}
              style={{
                marginTop: "16px",
                padding: "20px",
                border: "2px dashed #d1d5db",
                borderRadius: "8px",
                textAlign: "center",
                fontSize: "14px",
                color: "#6b7280",
                background: "#f9fafb",
                transition: "all 0.2s ease"
              }}
              onDragEnter={(e) => {
                e.target.style.borderColor = "#3b82f6";
                e.target.style.background = "#eff6ff";
              }}
              onDragLeave={(e) => {
                e.target.style.borderColor = "#d1d5db";
                e.target.style.background = "#f9fafb";
              }}
            >
              <div style={{ marginBottom: "4px" }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" style={{ opacity: 0.5 }}>
                  <path d="M12 5v14M5 12h14"/>
                </svg>
              </div>
              Drag agents here to build your flow
            </div>
          </div>
                </div>
      </aside>
    </div>
    </>
  );
}
