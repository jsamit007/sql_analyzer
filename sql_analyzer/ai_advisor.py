"""AI advisor for SQL performance optimization.

Supports OpenAI (cloud), Groq (fast cloud, free tier), and Ollama (local).
Sends EXPLAIN output to the chosen backend and returns smart optimization advice.
"""

import logging
from typing import Optional

from rich.console import Console

logger = logging.getLogger(__name__)
_console = Console(stderr=True)

SYSTEM_PROMPT = (
    "You are a senior database performance engineer. "
    "Analyze the SQL query and its execution plan. "
    "Provide concise, actionable performance improvement suggestions. "
    "Focus on indexing, query rewriting, and configuration tuning. "
    "Keep your response under 300 words. Use bullet points."
)


def get_ai_suggestions(
    query: str,
    explain_output: Optional[str],
    api_key: str,
    model: str = "gpt-4o",
) -> Optional[str]:
    """Send query and EXPLAIN output to OpenAI for optimization advice.

    Args:
        query: The SQL query text.
        explain_output: EXPLAIN plan output (JSON or text).
        api_key: OpenAI API key.
        model: OpenAI model to use (default: gpt-4o).

    Returns:
        AI-generated optimization suggestions, or None on failure.
    """
    if not api_key:
        logger.warning("OpenAI API key not configured. Skipping AI analysis.")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        logger.error("openai package not installed. Install with: pip install openai")
        return None

    prompt = _build_prompt(query, explain_output)

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        advice = response.choices[0].message.content
        logger.info("Received AI optimization advice.")
        return advice

    except Exception as e:
        logger.error("OpenAI API call failed: %s", e)
        return None


def get_ollama_suggestions(
    query: str,
    explain_output: Optional[str],
    model: str = "llama3",
    host: str = "http://localhost:11434",
) -> Optional[str]:
    """Send query and EXPLAIN output to a local Ollama model for advice.

    No API key or authentication required — Ollama runs locally.

    Args:
        query: The SQL query text.
        explain_output: EXPLAIN plan output.
        model: Ollama model name (default: llama3).
        host: Ollama server URL (default: http://localhost:11434).

    Returns:
        AI-generated optimization suggestions, or None on failure.
    """
    try:
        import ollama as ollama_lib
    except ImportError:
        msg = "ollama package not installed. Install with: pip install ollama"
        logger.error(msg)
        _console.print(f"[red]{msg}[/red]")
        return None

    prompt = _build_prompt(query, explain_output)

    try:
        client = ollama_lib.Client(host=host)
        _console.print(
            f"[dim]Querying Ollama ({model}) for AI suggestions…[/dim]",
        )
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.3},
        )

        advice = response.message.content
        logger.info("Received Ollama AI optimization advice.")
        return advice

    except Exception as e:
        msg = f"Ollama call failed: {e}"
        logger.error(msg)
        _console.print(f"[red]{msg}[/red]")
        return None


def get_groq_suggestions(
    query: str,
    explain_output: Optional[str],
    api_key: str,
    model: str = "llama-3.3-70b-versatile",
) -> Optional[str]:
    """Send query and EXPLAIN output to Groq for fast AI advice.

    Groq offers extremely fast inference with a free tier.
    Get your API key at: https://console.groq.com/keys

    Args:
        query: The SQL query text.
        explain_output: EXPLAIN plan output.
        api_key: Groq API key.
        model: Groq model name (default: llama-3.3-70b-versatile).

    Returns:
        AI-generated optimization suggestions, or None on failure.
    """
    if not api_key:
        logger.warning("Groq API key not configured. Skipping AI analysis.")
        return None

    try:
        from groq import Groq
    except ImportError:
        logger.error("groq package not installed. Install with: pip install groq")
        return None

    prompt = _build_prompt(query, explain_output)

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        advice = response.choices[0].message.content
        logger.info("Received Groq AI optimization advice.")
        return advice

    except Exception as e:
        logger.error("Groq API call failed: %s", e)
        return None


def _build_prompt(query: str, explain_output: Optional[str]) -> str:
    """Build the prompt for the OpenAI API.

    Args:
        query: SQL query text.
        explain_output: EXPLAIN output.

    Returns:
        Formatted prompt string.
    """
    parts = [
        "Analyze the following SQL query and its execution plan for performance issues.",
        "",
        "## SQL Query",
        "```sql",
        query,
        "```",
    ]

    if explain_output:
        parts.extend([
            "",
            "## Execution Plan (EXPLAIN output)",
            "```",
            explain_output[:3000],  # Limit size to avoid token overflow
            "```",
        ])

    parts.extend([
        "",
        "## Please provide:",
        "1. Key performance issues identified",
        "2. Specific index recommendations",
        "3. Query rewrite suggestions (if applicable)",
        "4. Database configuration recommendations (if applicable)",
    ])

    return "\n".join(parts)
