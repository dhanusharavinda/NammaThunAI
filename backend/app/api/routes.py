from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.core.config import settings
from app.core.rate_limit import SlidingWindowRateLimiter
from app.schemas import ExplainMessageRequest, ExplainMessageResponse
from app.services.explainer import explain_message
from app.services.file_extract import (
    extract_text_from_image,
    extract_text_from_pdf,
    try_pdf_ocr_fallback,
)
from app.services.stt import transcribe_tamil_audio
from app.services.tts import synthesize_tamil_speech

logger = logging.getLogger(__name__)

_limiter = SlidingWindowRateLimiter(max_requests=settings.rate_limit_per_minute, window_seconds=60)


def _enforce_rate_limit(request: Request) -> None:
    ip = (request.client.host if request.client else "") or "unknown"
    if not _limiter.allow(ip):
        raise HTTPException(status_code=429, detail="Romba adhigama try panreenga. Konjam neram kalichu try pannunga.")


def _enforce_input_limit(text: str) -> None:
    if len(text) > settings.max_input_chars:
        raise HTTPException(status_code=413, detail="Message romba perusa irukku. Konjam short-aa anuppunga.")


def _enforce_followup_limit(prompt_text: str) -> None:
    # Soft backend guard: if this looks like our follow-up prompt block, limit follow-ups.
    if "User follow-up question:" not in prompt_text:
        return
    # Count user turns present in the prompt (history includes "User:" prefixes).
    user_turns = prompt_text.count("\nUser:")
    # Allow 1 original + N follow-ups => (N+1) user turns.
    if user_turns > settings.followup_limit + 1:
        raise HTTPException(status_code=400, detail="Inga 5 follow-up கேள்விகள் மட்டும். Pudhu message anuppunga.")


router = APIRouter(prefix="/api", dependencies=[Depends(_enforce_rate_limit)])

try:
    # Raised when Tesseract is missing from PATH.
    from pytesseract.pytesseract import TesseractNotFoundError  # type: ignore
except Exception:  # pragma: no cover
    TesseractNotFoundError = RuntimeError  # type: ignore[misc,assignment]


@router.post("/explain-message", response_model=ExplainMessageResponse)
def api_explain_message(payload: ExplainMessageRequest) -> ExplainMessageResponse:
    _enforce_input_limit(payload.text)
    _enforce_followup_limit(payload.text)
    try:
        result = explain_message(payload.text, payload.language_preference)
    except Exception as e:
        logger.exception("LLM explain failed.")
        raise HTTPException(status_code=502, detail=f"AI explain failed: {e}")

    # Produce Tamil voice output (as required) without adding a new route.
    # Keep voice based on the explanation, which is spoken Tamil.
    try:
        audio_b64, mime = synthesize_tamil_speech(result.explanation)
        result.tts_audio_base64 = audio_b64
        result.tts_mime_type = mime
    except Exception:
        logger.exception("TTS synthesis failed; returning text-only response.")

    result.source_text = payload.text
    return result


@router.post("/voice-input", response_model=ExplainMessageResponse)
async def api_voice_input(
    audio: UploadFile = File(...),
    language_preference: str = Form("tamil"),
    context_text: str = Form(""),
    history: str = Form(""),
) -> ExplainMessageResponse:
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio upload.")

    try:
        transcript = transcribe_tamil_audio(audio.filename or "audio.wav", audio.content_type, data)
    except Exception as e:
        logger.exception("STT failed.")
        raise HTTPException(status_code=502, detail=f"STT failed: {e}")

    try:
        prompt = transcript
        if context_text and context_text.strip():
            prompt = "\n".join(
                [
                    "You are continuing a conversation about the SAME message.",
                    "",
                    "Original message (context):",
                    context_text.strip(),
                    "",
                    "Conversation so far:",
                    (history or "").strip() or "(none)",
                    "",
                    "User follow-up question:",
                    transcript.strip(),
                ]
            )
        _enforce_input_limit(prompt)
        _enforce_followup_limit(prompt)
        result = explain_message(prompt, language_preference)
    except Exception as e:
        logger.exception("LLM explain failed.")
        raise HTTPException(status_code=502, detail=f"AI explain failed: {e}")
    try:
        audio_b64, mime = synthesize_tamil_speech(result.explanation)
        result.tts_audio_base64 = audio_b64
        result.tts_mime_type = mime
    except Exception:
        logger.exception("TTS synthesis failed; returning text-only response.")
    result.source_text = transcript
    return result


@router.post("/file-upload", response_model=ExplainMessageResponse)
async def api_file_upload(
    file: UploadFile = File(...),
    language_preference: str = Form("tamil"),
) -> ExplainMessageResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file upload.")

    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()

    extracted = ""
    try:
        if content_type == "application/pdf" or filename.endswith(".pdf"):
            extracted = extract_text_from_pdf(data)
            if not extracted:
                ocr = try_pdf_ocr_fallback(data)
                extracted = ocr or ""
        elif content_type.startswith("image/") or any(
            filename.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"]
        ):
            extracted = extract_text_from_image(data)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Upload PDF or image.")
    except HTTPException:
        raise
    except TesseractNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=(
                "File extraction failed: Tesseract is not installed or not in PATH. "
                "Install Tesseract OCR, or set BACKEND .env -> TESSERACT_CMD "
                '(example: C:\\Program Files\\Tesseract-OCR\\tesseract.exe).'
            ),
        )
    except Exception as e:
        logger.exception("File extraction failed.")
        raise HTTPException(status_code=500, detail=f"File extraction failed: {e}")

    if not extracted or len(extracted.strip()) < 5:
        # Keep response schema consistent; ask for clearer upload rather than guessing.
        return ExplainMessageResponse(
            explanation="🟢 Simple Explanation (Tamil)\nIndha file-la text edukkave mudiyala. "
            "Photo / PDF clear-a irukanum.\n"
            "🟡 Do I need to worry?\nIppo vendam.\n"
            "🔵 What should I do now?\nClear screenshot / readable PDF anuppunga.\n"
            "🟣 Reply Suggestions (Tamil / Tanglish / Simple English)\nIdhula edhuvum seyyave vendam.",
            urgency="low",
            next_steps="Clear-a irukura file/screenshot anuppunga. Link/OTP share pannaadheenga.",
            reply_options={"tamil": "", "tanglish": "", "english": ""},
            source_text=None,
        )

    _enforce_input_limit(extracted)
    try:
        result = explain_message(extracted, language_preference)
    except Exception as e:
        logger.exception("LLM explain failed.")
        raise HTTPException(status_code=502, detail=f"AI explain failed: {e}")
    try:
        audio_b64, mime = synthesize_tamil_speech(result.explanation)
        result.tts_audio_base64 = audio_b64
        result.tts_mime_type = mime
    except Exception:
        logger.exception("TTS synthesis failed; returning text-only response.")
    result.source_text = extracted
    return result

