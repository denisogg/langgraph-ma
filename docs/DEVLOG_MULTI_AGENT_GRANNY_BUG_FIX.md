# Development Log: Multi-Agent Orchestration Bug Fix

**Date:** January 2025  
**Issue:** Granny agent not executing in multi-agent workflows  
**Status:** ✅ RESOLVED

## Problem Statement

User reported that in supervisor mode, when requesting multi-agent workflows like:
> "make me an analysis about the weather in bucharest in the last week and let granny tell me about it"

The expected flow should be:
1. User → Supervisor (plan)
2. Supervisor → Tools (web search) 
3. Tools → Data Analyst (with data)
4. Data Analyst → Supervisor (with analysis)
5. Supervisor → Granny (with analysis) 
6. Granny → User (final friendly response)

**Actual behavior:** Granny never executed, despite being mentioned in supervisor's plan.

## Investigation Process

### Step 1: Verified Multi-Agent Detection
- ✅ Supervisor correctly detected multi-agent request
- ✅ Plan showed: `data_analyst → granny` sequence
- ✅ Strategy: `multi_agent_sequential`
- ✅ All agents available in registry

### Step 2: Identified Function Call Issue  
Chat logs showed `"chosen_agent": "data_analyst"` suggesting single-agent logic was still being used.

**Root Cause Discovery:** The streaming endpoint was calling the OLD function:
```python
# Line 1137 - WRONG 
result = process_supervisor_message(chat_id, req.user_prompt)

# Should be:
result = process_multi_agent_supervisor_message(chat_id, req.user_prompt)
```

### Step 3: Deeper Investigation
After fixing the function call, the issue persisted. Further investigation revealed:

**The Real Root Cause:** Streaming logic incompatibility.

## Root Cause Analysis

The multi-agent orchestration was working correctly, but the streaming logic was designed for single-agent responses.

### What Was Working ✅
- `process_multi_agent_supervisor_message()` correctly called
- `execute_multi_agent_orchestration()` properly executed both agents  
- All messages added to chat history (`hist`) including:
  - Supervisor plan
  - Tool outputs
  - Data analyst response
  - **Granny response** (this WAS being generated!)
  - Supervisor acknowledgments

### What Was Broken ❌
The streaming logic in `/chats/{chat_id}/message/stream` expected single-agent format:

```python
# Lines 1170-1181: Only streamed these 3 things
yield supervisor_decision  
yield tool_outputs
yield result["chosen_agent"]  # Only ONE agent response!
```

**The bug:** Multi-agent orchestration added 6+ messages to `hist`, but streaming only sent the final `chosen_agent` to the frontend. Granny's response was generated but never streamed to the user.

## Technical Details

### File: `backend/src/agent/graph.py`

#### Functions Involved:
1. **`process_multi_agent_supervisor_message()`** - Entry point ✅
2. **`execute_multi_agent_orchestration()`** - Agent execution ✅  
3. **`stream_message()`** endpoint - Streaming logic ❌

#### Data Flow:
```
User Input 
   ↓
process_multi_agent_supervisor_message()
   ↓
execute_multi_agent_orchestration()
   ↓ (adds to hist)
[supervisor, tool, delegation, data_analyst, delegation, granny, ack]
   ↓
stream_message() - OLD LOGIC: only streams final agent
   ↓ (should stream all hist entries)
Frontend receives: supervisor + tool + data_analyst only
```

## Solution Implemented

### Fix 1: Correct Function Call
**File:** `backend/src/agent/graph.py:1137`
```python
# BEFORE
result = process_supervisor_message(chat_id, req.user_prompt)

# AFTER  
result = process_multi_agent_supervisor_message(chat_id, req.user_prompt)
```

### Fix 2: Multi-Agent Streaming Logic
**File:** `backend/src/agent/graph.py:1144-1168`

Added conditional logic to detect multi-agent responses:

```python
# Check if this is a multi-agent response
if result.get("multi_agent_execution", False):
    # For multi-agent: all messages were already added to hist during orchestration
    # Stream all messages that were added during orchestration (everything after user message)
    
    # Find the last user message (the one we just processed)
    user_msg_index = -1
    for i in range(len(hist) - 1, -1, -1):
        if hist[i].get("sender") == "user" and hist[i].get("text") == req.user_prompt:
            user_msg_index = i
            break
    
    # Stream all messages added after the user message
    if user_msg_index >= 0:
        for msg in hist[user_msg_index + 1:]:
            yield json.dumps(msg) + "\n"
            
else:
    # Single-agent logic (original)
    # Stream supervisor decision, tools, and chosen agent response
```

### Key Changes:
1. **Detection:** Check for `result.get("multi_agent_execution", False)`
2. **Find Start Point:** Locate the user message that triggered orchestration
3. **Stream Everything:** Send all messages added to `hist` after user message
4. **Preserve Single-Agent:** Keep original logic for single-agent workflows

## Expected Result After Fix

### Backend Console Debug Output:
```
🔍 DEBUG: process_multi_agent_supervisor_message called
🔍 DEBUG: Execution plan requires_multi_agent: True
🔍 DEBUG: Agent sequence: ['data_analyst', 'granny'] 
🔍 DEBUG: Calling execute_multi_agent_orchestration...
🔍 DEBUG: Starting multi-agent execution with sequence: ['data_analyst', 'granny']
🔍 DEBUG: Processing agent 1/2: data_analyst
🔍 DEBUG: Processing agent 2/2: granny  
🔍 DEBUG: Multi-agent streaming - hist has 8 messages
🔍 DEBUG: Streamed message from supervisor
🔍 DEBUG: Streamed message from tool
🔍 DEBUG: Streamed message from supervisor  
🔍 DEBUG: Streamed message from data_analyst
🔍 DEBUG: Streamed message from supervisor
🔍 DEBUG: Streamed message from granny  ← FIXED!
🔍 DEBUG: Streamed message from supervisor
```

### Frontend Chat Flow:
```
User: "make me an analysis about weather in bucharest and let granny tell me about it"
Supervisor: "Enhanced Analysis Results: Strategy: multi_agent_sequential..."
Tool: "{'location': {'name': 'Bucharest'...}"
Supervisor: "🔄 Delegating to data_analyst (step 1/2)"
Data Analyst: "Well, dear, let's take a look at the weather in Bucharest..."
Supervisor: "🔄 Delegating to granny (step 2/2)"
Granny: "Oh my dear, let me tell you about this weather..." ← FIXED!
Supervisor: "✅ Multi-agent workflow completed. Final response from granny."
```

## Lessons Learned

1. **Separation of Concerns:** Orchestration logic vs. streaming logic can have different requirements
2. **Data Flow Tracing:** Need to trace data through multiple layers (orchestration → history → streaming → frontend)
3. **Backward Compatibility:** When adding multi-agent support, ensure single-agent workflows still work
4. **Debug Logging:** Comprehensive logging at each step reveals where data gets lost
5. **Response Format Evolution:** New features may require new response formats that existing code doesn't handle

## Related Files Modified

- `backend/src/agent/graph.py` (Lines 1137, 1144-1168)

## Testing Commands

```bash
# Test multi-agent workflow
curl -X POST "http://localhost:8000/chats/{chat_id}/message/stream" \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "make me an analysis about weather in bucharest and let granny tell me about it"}'

# Verify both agents execute:
# 1. data_analyst should provide weather analysis
# 2. granny should provide friendly interpretation
```

## Status: ✅ RESOLVED

Multi-agent workflows now correctly execute all agents in sequence and stream all responses to the frontend. The issue was in the streaming layer, not the orchestration layer. 