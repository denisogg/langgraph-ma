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

const ALL_AGENTS = ["granny", "story_creator", "parody_creator"];
const ALL_TOOLS = ["web_search", "knowledgebase"];

export default function App() {
  const [chats, setChats] = useState([]);
  const [current, setCurrent] = useState(null);
  const [flow, setFlow] = useState([]);
  const [history, setHistory] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [knowledgebaseOptions, setKnowledgebaseOptions] = useState({});

  const dragItem = useRef();
  const dragType = useRef();
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
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
  };

  const newChat = async () => {
    const res = await axios.post("http://localhost:8000/chats");
    setChats((prev) => [res.data, ...prev]);
    loadChat(res.data.id);
  };

  const saveSettings = async (newFlow) => {
    if (!current) {
      console.warn("No active chat. Cannot save settings.");
      return;
    }
    try {
      await axios.post(`http://localhost:8000/chats/${current}/settings`, {
        agent_sequence: newFlow,
      });
      setFlow(newFlow);
    } catch (err) {
      console.error("Failed to save settings:", err);
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
                for_agent: data.for_agent
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
                  m.sender === "granny" 
                  ? "#dbeafe" :
                  m.sender === "story_creator" 
                  ? "#dcfce7" :
                  m.sender === "parody_creator" 
                  ? "#fce7f3" :
                  "#ffffff",
                color: m.sender === "user" ? "#fff" : 
                       m.sender === "tool" ? "#92400e" : "#374151", // Professional brown for tool text
                border: m.sender === "tool" 
                  ? "1px solid #f59e0b" 
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
              background: "#3b82f6",
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
            Available Agents
          </h4>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
            {ALL_AGENTS.map((agent) => (
              <div
                key={agent}
                draggable
                onDragStart={() => {
                  dragItem.current = agent;
                  dragType.current = "agent";
                }}
                style={{
                  padding: "8px 12px",
                  background: "#dbeafe",
                  border: "1px solid #3b82f6",
                  borderRadius: "6px",
                  cursor: "grab",
                  fontSize: "12px",
                  fontWeight: "500",
                  color: "#1e40af",
                  transition: "all 0.2s ease",
                  userSelect: "none"
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = "#bfdbfe";
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = "#dbeafe";
                }}
              >
                {agent === "granny" ? "Granny" :
                 agent === "story_creator" ? "Story Creator" :
                 agent === "parody_creator" ? "Parody Creator" :
                 agent}
              </div>
            ))}
          </div>
        </div>

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
              background: "#f59e0b",
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
          </h4>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
            {ALL_TOOLS.map((tool) => (
              <div
                key={tool}
                draggable
                onDragStart={() => {
                  dragItem.current = tool;
                  dragType.current = "tool";
                }}
                style={{
                  padding: "8px 12px",
                  background: "#fef3c7",
                  border: "1px solid #f59e0b",
                  borderRadius: "6px",
                  cursor: "grab",
                  fontSize: "12px",
                  fontWeight: "500",
                  color: "#92400e",
                  transition: "all 0.2s ease",
                  userSelect: "none"
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = "#fde68a";
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = "#fef3c7";
                }}
              >
                {tool === "web_search" ? "Web Search" :
                 tool === "knowledgebase" ? "Knowledge Base" :
                 tool}
              </div>
            ))}
          </div>
        </div>

        <div style={{ flex: 1, minHeight: 0 }}>
          <h4 style={{ 
            fontSize: "14px", 
            fontWeight: "600", 
            color: "#374151", 
            marginBottom: "16px",
            display: "flex",
            alignItems: "center"
          }}>
            <div style={{
              width: "16px",
              height: "16px",
              background: "#10b981",
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
            Chat Agent Flow
          </h4>
          
                     <div style={{ 
             flex: 1,
             overflowY: "auto",
             paddingRight: "4px",
             minHeight: 0
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
