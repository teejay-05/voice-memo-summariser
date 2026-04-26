"""
Summarisation service using Anthropic Claude.
Extracts summary, action items, sentiment, and key topics from a transcript.
"""

import os
import json
import re
import httpx


ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-5"

SYSTEM_PROMPT = """You are an expert assistant that analyses voice memo transcripts.
Given a transcript, you extract structured insights.

Always respond with valid JSON only — no markdown, no preamble, no explanation.
Your response must be a single JSON object with exactly these keys:
{
  "summary": "2-3 sentence summary of the memo",
  "action_items": ["action 1", "action 2"],
  "sentiment": "positive | neutral | negative",
  "key_topics": ["topic 1", "topic 2", "topic 3"]
}

Rules:
- summary: concise, 2-3 sentences, past tense
- action_items: concrete next steps mentioned or implied. Empty array if none.
- sentiment: must be exactly one of: positive, neutral, negative
- key_topics: 2-5 short topic labels (2-4 words each)
"""


async def summarise_transcript(transcript: str) -> dict:
    """
    Send a transcript to Claude and return structured summary data.

    Args:
        transcript: Plain text or diarised transcript.

    Returns:
        Dict with keys: summary, action_items, sentiment, key_topics
    """
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not set in environment variables.")

    if not transcript or not transcript.strip():
        raise ValueError("Transcript is empty — nothing to summarise.")

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": f"Please analyse this voice memo transcript:\n\n{transcript}",
            }
        ],
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(ANTHROPIC_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise RuntimeError(
            f"Anthropic API error {response.status_code}: {response.text}"
        )

    data = response.json()
    raw_text = data["content"][0]["text"].strip()

    # Strip markdown fences if present
    raw_text = re.sub(r"^```json\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Claude returned invalid JSON: {e}\nRaw: {raw_text}")

    # Validate required keys
    required = {"summary", "action_items", "sentiment", "key_topics"}
    missing = required - set(result.keys())
    if missing:
        raise RuntimeError(f"Claude response missing keys: {missing}")

    return result
