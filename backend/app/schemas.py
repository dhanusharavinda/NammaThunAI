from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


LanguagePreference = Literal["tamil", "tanglish", "english", "all"]
Urgency = Literal["low", "medium", "high"]


class ExplainMessageRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language_preference: LanguagePreference = "tamil"


class ReplyOptions(BaseModel):
    tamil: str = ""
    tanglish: str = ""
    english: str = ""


class ExplainMessageResponse(BaseModel):
    explanation: str
    urgency: Urgency
    next_steps: str
    reply_options: ReplyOptions

    # Optional: original text used for the explanation (useful for conversational follow-ups).
    source_text: Optional[str] = None

    # Needed for "OpenAI TTS (Tamil voice)" without adding extra routes.
    # Frontend can autoplay this if present.
    tts_audio_base64: Optional[str] = None
    tts_mime_type: Optional[str] = None

