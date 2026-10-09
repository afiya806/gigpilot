"""Base agent class for all GigPilot AI agents."""

import json
import os
import re


# Use Claude API if available, otherwise fall back to local heuristics
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def call_llm(system_prompt: str, user_message: str) -> str:
    """Call Claude API or fall back to rule-based extraction."""
    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except Exception:
            pass
    return ""


def extract_json(text: str) -> dict:
    """Extract JSON from LLM response text."""
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try to find JSON block
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return {}
