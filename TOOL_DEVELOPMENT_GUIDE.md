# 🔧 Ghid pentru Dezvoltarea Tool-urilor

Acest ghid explică cum să adaugi tool-uri noi în sistemul dinamic de agenți AI.

## 📋 Prezentare Generală

Sistemul nostru de tool-uri este **complet dinamic**:
- ✅ Nu există cod hardcodat în agenți
- ✅ Tool-urile noi se adaugă automat în contextul agenților
- ✅ Fiecare agent descoperă automat tool-urile disponibile
- ✅ Sistemul se scalează automat cu tool-uri noi

## 🏗️ Arhitectura Sistemului

```
📁 src/agent/tools/
├── tool_config.py      # Registry-ul central de tool-uri
├── tool_executor.py    # Execuția inteligentă a tool-urilor
├── usage_tracker.py    # Tracking și învățare
└── web_search.py       # Implementarea tool-urilor specifice
```

## 🚀 Cum să Adaugi un Tool Nou

### Pasul 1: Definește Metadata Tool-ului

```python
from src.agent.tools.tool_config import ToolMetadata, register_new_tool

# Definește metadata completă
new_tool = ToolMetadata(
    name="calculator",
    description="Performs mathematical calculations and solves equations. Use this when you need to compute numbers, solve math problems, or perform calculations.",
    use_cases=[
        "basic arithmetic operations",
        "complex mathematical calculations", 
        "equation solving",
        "unit conversions",
        "percentage calculations",
        "financial calculations"
    ],
    input_format="Provide a clear mathematical expression or describe the calculation you need. Examples: '2+2', 'square root of 64', 'convert 100 USD to EUR'",
    confidence_threshold=0.9,
    fallback_behavior="show_calculation_steps"
)

# Înregistrează tool-ul în sistem
register_new_tool("calculator", new_tool)
```

### Pasul 2: Implementează Funcția de Execuție

Adaugă implementarea în `tool_executor.py`:

```python
def _execute_single_tool(tool_name: str, query: str, option: Optional[str] = None) -> str:
    """Execute a single tool with the given query"""
    
    if tool_name == "calculator":
        return _execute_calculator(query)
    elif tool_name == "web_search":
        return _execute_web_search(query)
    elif tool_name == "knowledgebase":
        return _execute_knowledgebase(query, option)
    # Adaugă noul tool aici
    elif tool_name == "your_new_tool":
        return _execute_your_new_tool(query, option)
    else:
        return f"Unknown tool: {tool_name}"

def _execute_your_new_tool(query: str, option: Optional[str] = None) -> str:
    """Implementarea tool-ului tău"""
    try:
        # Logica tool-ului aici
        result = your_tool_logic(query)
        return result
    except Exception as e:
        return f"Error executing tool: {str(e)}"
```

### Pasul 3: Adaugă Logica de Detecție (Opțional)

Pentru detecție inteligentă, actualizează `should_use_tool()` în `tool_config.py`:

```python
def should_use_tool(user_input: str, tool_name: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # ... cod existent ...
    
    # Adaugă logica pentru noul tool
    elif tool_name == "your_new_tool":
        tool_indicators = ["keyword1", "keyword2", "specific_pattern"]
        if any(indicator in user_lower for indicator in tool_indicators):
            relevance_score += 2
            matching_cases.append("Specific use case detected")
    
    # ... rest of function ...
```

### Pasul 4: Adaugă Generarea de Query-uri (Opțional)

Pentru query-uri mai inteligente, actualizează `generate_tool_query()`:

```python
def generate_tool_query(user_input: str, tool_name: str, context: Optional[Dict[str, Any]] = None) -> str:
    if tool_name == "web_search":
        return _generate_web_search_query(user_input, context)
    elif tool_name == "knowledgebase":
        return _generate_knowledgebase_query(user_input, context)
    elif tool_name == "your_new_tool":
        return _generate_your_tool_query(user_input, context)
    else:
        return user_input

def _generate_your_tool_query(user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Generează query specific pentru tool-ul tău"""
    # Procesează input-ul utilizatorului
    # Returnează query optimizat
    return processed_query
```

## 📝 Exemplu Complet: Tool de Traducere

```python
# 1. Definește metadata
translator_tool = ToolMetadata(
    name="translator",
    description="Translates text between different languages. Use this when you need to translate content or communicate in multiple languages.",
    use_cases=[
        "translate text to different languages",
        "detect language of text",
        "multilingual communication",
        "language learning assistance",
        "international content adaptation"
    ],
    input_format="Specify the source language, target language, and the text to translate. Example: 'Translate from English to Romanian: Hello world'",
    confidence_threshold=0.8,
    fallback_behavior="suggest_alternative_translation_service"
)

# 2. Înregistrează tool-ul
register_new_tool("translator", translator_tool)

# 3. Implementează execuția
def _execute_translator(query: str, option: Optional[str] = None) -> str:
    """Execute translation"""
    try:
        # Parsează query-ul pentru a extrage limbile și textul
        # Exemplu: "Translate from English to Romanian: Hello world"
        
        # Logica de traducere aici (Google Translate API, etc.)
        translated_text = your_translation_service(query)
        
        return f"Translation: {translated_text}"
    except Exception as e:
        return f"Translation error: {str(e)}"

# 4. Adaugă detecția
# În should_use_tool():
elif tool_name == "translator":
    translate_indicators = ["translate", "translation", "traduce", "limba", "language"]
    if any(indicator in user_lower for indicator in translate_indicators):
        relevance_score += 2

# 5. Adaugă generarea de query
def _generate_translator_query(user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Generate focused translation query"""
    # Extrage informațiile de traducere din input
    if "translate" in user_input.lower():
        return user_input  # Păstrează formatul original pentru claritate
    else:
        return f"Translate: {user_input}"
```

## 🧪 Testarea Tool-ului Nou

```python
# Test rapid
from src.agent.tools.tool_config import ToolConfig, generate_dynamic_tools_context

# Testează contextul cu noul tool
test_tools = [
    ToolConfig(name="web_search"),
    ToolConfig(name="your_new_tool"),
    ToolConfig(name="knowledgebase")
]

context = generate_dynamic_tools_context(test_tools)
print(context)
```

## 📚 Tipuri de Tool-uri Suportate

### 1. **Tool-uri de Informații**
- Web search, knowledge base, databases
- Confidence threshold: 0.7-0.8

### 2. **Tool-uri de Procesare**
- Calculator, translator, analyzer
- Confidence threshold: 0.8-0.9

### 3. **Tool-uri de Comunicare**
- Email, chat, notifications
- Confidence threshold: 0.6-0.8

### 4. **Tool-uri Creative**
- Image generation, music, art
- Confidence threshold: 0.5-0.7

## ⚙️ Configurarea Avansată

### Threshold-uri de Confidence
```python
# Pentru tool-uri precise (calculator, date)
confidence_threshold=0.9

# Pentru tool-uri de informații (search, knowledge)
confidence_threshold=0.7-0.8

# Pentru tool-uri creative (art, music)
confidence_threshold=0.5-0.7
```

### Fallback Behaviors
- `"inform_user"` - Informează utilizatorul că tool-ul nu a funcționat
- `"retry_with_different_query"` - Încearcă din nou cu query diferit
- `"suggest_alternative_source"` - Sugerează surse alternative
- `"show_calculation_steps"` - Pentru tool-uri matematice

## 🔄 Integrarea Automată

Odată ce adaugi un tool nou:

1. **Agenții îl descoperă automat** - nu trebuie să modifici codul agenților
2. **Contextul se actualizează dinamic** - informațiile despre tool apar automat în prompt-uri
3. **Sistemul de tracking funcționează** - usage și confidence se monitorizează automat
4. **Frontend-ul îl recunoaște** - tool-ul apare în configurațiile disponibile

## 🚨 Best Practices

### ✅ DO:
- Folosește nume descriptive pentru tool-uri
- Adaugă use cases detaliate și specifice
- Testează thoroughly înainte de deployment
- Documentează input format-ul clar
- Implementează error handling robust

### ❌ DON'T:
- Nu hardcoda informații despre tool-uri în agenți
- Nu uita să adaugi confidence thresholds
- Nu ignora error handling
- Nu faci tool-uri prea generice (specificity helps)

## 📈 Monitoring și Optimizare

Sistemul de usage tracking îți oferă:
- Statistici de utilizare per tool
- Confidence scores în timp real
- Feedback pentru optimizare
- Detecția de probleme automat

```python
from src.agent.tools.usage_tracker import get_usage_tracker

tracker = get_usage_tracker()
stats = tracker.get_tool_statistics("your_tool")
print(f"Usage: {stats['usage_count']}, Avg confidence: {stats['avg_confidence']}")
```

## 🎯 Următorii Pași

După ce adaugi tool-ul:
1. Testează cu diferite scenarii
2. Monitorizează performance-ul
3. Optimizează pe baza feedback-ului
4. Documentează pentru echipă
5. Consideră integrări cu alte tool-uri

---

**💡 Tip:** Sistemul este proiectat să fie extensibil. Fiecare tool nou îmbunătățește capabilitățile tuturor agenților automat! 