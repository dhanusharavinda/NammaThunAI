from __future__ import annotations

import base64

from app.core.config import settings
from app.services.openai_client import get_openai_client


def synthesize_tamil_speech(text: str) -> tuple[str, str]:
    """
    Returns (base64_audio, mime_type).
    Uses OpenAI TTS; Tamil output depends on the input being Tamil.
    """
    client = get_openai_client()

    audio = client.audio.speech.create(
        model=settings.openai_tts_model,
        voice=settings.openai_tts_voice,
        input=text,
        format="mp3",
    )

    # openai returns binary bytes via .read() in many environments
    data = audio.read()
    return base64.b64encode(data).decode("utf-8"), "audio/mpeg"

