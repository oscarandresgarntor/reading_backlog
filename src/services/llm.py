"""LLM service for intelligent article metadata extraction using Ollama."""

import json
import re
from typing import Optional

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# Default model - can be changed in config
DEFAULT_MODEL = "llama3.2"

# Maximum text length to send to LLM (to avoid context limits)
MAX_TEXT_LENGTH = 6000

EXTRACTION_PROMPT = """Analyze this document and extract the following information. Respond ONLY with a JSON object, no other text.

Document text:
{text}

---

Extract and return a JSON object with these fields:
- "title": The main title of the document (be accurate, use the actual title)
- "summary": A concise 2-3 sentence summary of the main content
- "suggested_tags": An array of 2-4 relevant topic tags (lowercase, single words)

JSON response:"""


def is_ollama_running() -> bool:
    """Check if Ollama service is running."""
    if not OLLAMA_AVAILABLE:
        return False
    try:
        ollama.list()
        return True
    except Exception:
        return False


def extract_with_llm(
    text: str,
    model: str = DEFAULT_MODEL,
) -> Optional[dict]:
    """
    Use Ollama LLM to extract title, summary, and tags from document text.

    Returns dict with 'title', 'summary', 'suggested_tags' or None if failed.
    """
    if not OLLAMA_AVAILABLE:
        return None

    if not is_ollama_running():
        return None

    # Truncate text if too long
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH] + "\n\n[Text truncated...]"

    # Skip if text is too short
    if len(text.strip()) < 50:
        return None

    try:
        prompt = EXTRACTION_PROMPT.format(text=text)

        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={
                "temperature": 0.1,  # Low temperature for consistent extraction
                "num_predict": 500,  # Limit response length
            }
        )

        response_text = response.get("response", "").strip()

        # Try to extract JSON from response
        result = parse_llm_response(response_text)

        if result and "title" in result and "summary" in result:
            return result

        return None

    except Exception as e:
        # Silently fail and fall back to basic extraction
        return None


def parse_llm_response(response: str) -> Optional[dict]:
    """Parse JSON from LLM response, handling common formatting issues."""
    # Try direct JSON parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in response
    json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Try to find JSON with nested structures
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return None


def check_model_available(model: str = DEFAULT_MODEL) -> bool:
    """Check if the specified model is available in Ollama."""
    if not OLLAMA_AVAILABLE or not is_ollama_running():
        return False

    try:
        models = ollama.list()
        model_names = [m.get("name", "").split(":")[0] for m in models.get("models", [])]
        return model in model_names or any(model in name for name in model_names)
    except Exception:
        return False
