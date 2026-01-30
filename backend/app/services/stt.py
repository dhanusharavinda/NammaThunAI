from __future__ import annotations

import io

from app.core.config import settings
from app.services.openai_client import get_openai_client


def transcribe_tamil_audio(filename: str, content_type: str | None, data: bytes) -> str:
    client = get_openai_client()
    file_obj = io.BytesIO(data)
    file_obj.name = filename  # openai sdk uses .name for filename

    transcription = client.audio.transcriptions.create(
        model=settings.openai_stt_model,
        file=file_obj,
        language="ta",
        response_format="text",
    )
    # response_format="text" returns a plain string
    return str(transcription).strip()

