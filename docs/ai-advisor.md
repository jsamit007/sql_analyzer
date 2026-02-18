# AI Advisor

**Module:** `sql_analyzer/ai_advisor.py`

Sends SQL queries and their EXPLAIN plans to an AI backend for optimization advice. Three backends are supported: OpenAI, Groq, and Ollama.

## Shared Components

### `SYSTEM_PROMPT`

A constant string used as the system message for all backends:

```
You are a senior database performance engineer.
Analyze the SQL query and its execution plan.
Provide concise, actionable performance improvement suggestions.
Focus on indexing, query rewriting, and configuration tuning.
Keep your response under 300 words. Use bullet points.
```

### `_build_prompt(query, explain_output) → str`

Builds the user message sent to the AI. Structure:

```markdown
Analyze the following SQL query and its execution plan for performance issues.

## SQL Query
```sql
<query text>
```

## Execution Plan (EXPLAIN output)
```
<explain output, truncated to 3000 chars>
```

## Please provide:
1. Key performance issues identified
2. Specific index recommendations
3. Query rewrite suggestions (if applicable)
4. Database configuration recommendations (if applicable)
```

The EXPLAIN output is truncated to 3000 characters to avoid exceeding token limits.

## Backend Functions

All three follow the same pattern:

```
1. Validate key/prerequisites
2. Lazy-import the client library
3. Build the prompt
4. Call the chat completion API
5. Return the response content (or None on failure)
```

### `get_ai_suggestions(query, explain_output, api_key, model) → str | None`

**Backend:** OpenAI

| Parameter | Default |
|-----------|---------|
| `model` | `"gpt-4o"` |
| `temperature` | `0.3` |
| `max_tokens` | `500` |

```python
from openai import OpenAI
client = OpenAI(api_key=api_key)
response = client.chat.completions.create(...)
return response.choices[0].message.content
```

**Returns `None` when:**
- `api_key` is empty
- `openai` package not installed
- API call throws any exception

### `get_groq_suggestions(query, explain_output, api_key, model) → str | None`

**Backend:** Groq (fast cloud inference, free tier)

| Parameter | Default |
|-----------|---------|
| `model` | `"llama-3.3-70b-versatile"` |
| `temperature` | `0.3` |
| `max_tokens` | `500` |

```python
from groq import Groq
client = Groq(api_key=api_key)
response = client.chat.completions.create(...)
return response.choices[0].message.content
```

The Groq Python SDK uses the same OpenAI-compatible API format, so the code is nearly identical.

### `get_ollama_suggestions(query, explain_output, model, host) → str | None`

**Backend:** Ollama (local, no API key needed)

| Parameter | Default |
|-----------|---------|
| `model` | `"llama3"` |
| `host` | `"http://localhost:11434"` |
| `temperature` | `0.3` (via `options` dict) |

```python
import ollama as ollama_lib
client = ollama_lib.Client(host=host)
response = client.chat(model=model, messages=[...], options={"temperature": 0.3})
return response.message.content
```

**Key differences from OpenAI/Groq:**
- No API key parameter
- Uses `client.chat()` instead of `client.chat.completions.create()`
- Temperature is passed via `options` dict
- Response uses `response.message.content` (not `response.choices[0].message.content`)
- No `max_tokens` parameter (Ollama doesn't support it the same way)

## Error Handling

All three functions follow the same pattern:

```python
try:
    # import, create client, call API
except ImportError:
    logger.error("Package not installed")
    return None
except Exception as e:
    logger.error("API call failed: %s", e)
    return None
```

Failures are always graceful — the caller gets `None` and can skip AI advice without crashing.

## Adding a New Backend

To add a new AI backend:

1. Add a new function following the pattern: `get_<provider>_suggestions(query, explain_output, ...)`
2. Lazy-import the client library
3. Use `SYSTEM_PROMPT` and `_build_prompt()` for consistency
4. Return `str | None`
5. Add config fields to `AnalyzerConfig` in `config.py`
6. Add CLI flags in `sql_analyzer.py`
7. Add the dispatch in `run_analysis()` priority chain
