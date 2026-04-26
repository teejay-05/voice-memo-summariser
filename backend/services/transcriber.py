"""
Transcription service using Deepgram Nova-2.
Handles audio file → transcript with speaker diarisation.
"""

import os
import httpx
from pathlib import Path


DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


async def transcribe_audio(file_path: str) -> str:
    """
    Send an audio file to Deepgram and return the transcript text.

    Args:
        file_path: Path to the local audio file.

    Returns:
        Plain text transcript.
    """
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    if not DEEPGRAM_API_KEY:
        raise ValueError("DEEPGRAM_API_KEY is not set in environment variables.")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Detect content type
    suffix = path.suffix.lower()
    content_type_map = {
        ".mp3": "audio/mpeg",
        ".mp4": "audio/mp4",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
        ".flac": "audio/flac",
    }
    content_type = content_type_map.get(suffix, "audio/wav")

    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": content_type,
    }

    params = {
        "model": "nova-2",
        "smart_format": "true",
        "punctuate": "true",
        "diarize": "true",        # Speaker separation
        "utterances": "true",
        "language": "en-GB",
    }

    with open(file_path, "rb") as audio_file:
        audio_data = audio_file.read()

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            DEEPGRAM_URL,
            headers=headers,
            params=params,
            content=audio_data,
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Deepgram error {response.status_code}: {response.text}"
        )

    result = response.json()

    # Extract transcript — handle diarised utterances if present
    try:
        utterances = result["results"]["utterances"]
        if utterances:
            lines = []
            for u in utterances:
                speaker = f"Speaker {u.get('speaker', 0) + 1}"
                lines.append(f"{speaker}: {u['transcript']}")
            return "\n".join(lines)
    except (KeyError, TypeError):
        pass

    # Fallback to flat transcript
    try:
        return result["results"]["channels"][0]["alternatives"][0]["transcript"]
    except (KeyError, IndexError):
        raise RuntimeError("Could not extract transcript from Deepgram response.")
