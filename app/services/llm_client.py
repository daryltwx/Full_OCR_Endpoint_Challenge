import json
import ollama

from app.config import settings


def query_llm(prompt: str, system: str = "") -> str:
    """Send a prompt to the local Ollama model and return the response text."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = ollama.chat(
        model=settings.llm_model,
        messages=messages,
        options={"temperature": 0.0},
    )
    return response["message"]["content"]


def query_llm_json(prompt: str, system: str = "") -> dict | None:
    """Query the LLM and parse the response as JSON.

    Extracts JSON from the response even if wrapped in markdown code fences.
    """
    raw = query_llm(prompt, system)

    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end])
            except json.JSONDecodeError:
                return None
    return None
