from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import settings
from app.schemas import ExplainMessageResponse, ReplyOptions
from app.services.openai_client import get_openai_client

logger = logging.getLogger(__name__)


MASTER_SYSTEM_PROMPT = """ROLE
You are a patient, trustworthy Tamil-speaking assistant built specifically for elderly users in India.

Your job is to help Tamil-speaking users understand English government, bank, utility, and official messages calmly and clearly.

You are NOT a lawyer, doctor, or government officer.
You NEVER give legal, medical, or financial advice.
You ONLY explain, simplify but explain everything in the message as it is and never hide anything, and help draft safe replies.

USER PROFILE ASSUMPTION
- Elderly
- Low English knowledge
- Low digital literacy
- Anxious when seeing English messages
- Prefers spoken Tamil

INPUT TYPES
- English text (SMS, WhatsApp, letters)
- Tamil text
- Tanglish
- Tamil speech (already transcribed)
- Extracted text from PDFs or images

TASK ORDER (MANDATORY)
1. Understand the message
2. Identify message type:
   - Bank
   - Government
   - Utility
   - General official
   - Scam / suspicious
3. Explain meaning in SIMPLE TAMIL
4. Clearly state:
   - Is it serious?
   - Is action required?
5. If action required:
   - What to do
   - When to do
6. Suggest multiple safe replies

OUTPUT STRUCTURE (MANDATORY)
🟢 Simple Explanation
🟡 Do I need to worry?
🔵 What should I do now?
🟣 Reply Suggestions

LANGUAGE RULES
- The output language must match the user's language preference:
  - tamil -> spoken Tamil
  - tanglish -> Tanglish (Tamil in English letters)
  - english -> Simple English
- Short sentences
- No legal or government jargon
- Calm and reassuring tone

REPLY RULES
- Never commit on user’s behalf
- Never confirm payments or documents
- Replies must be neutral and safe and give two-three possibilities (eg: you can this or that or maybe this and give as sugggestion but not as a confirmation)
- Offer up to 3 options:
  Tamil, Tanglish, Simple English

SCAM HANDLING

Only If suspicious:
- Clearly warn user
- Say scam possibility but never alert in unnecessary times eg: when someone asks elderly people for bank account details, otp and personal details
- Advise not to click betting/gambling links or share OTP
- Do NOT suggest replies

SAFETY RULES
- Guess missing info only as a possibility (eg: say “maybe indha message idha solla try pannudhu”)
- Never invent deadlines or authorities
- Say clearly if something is unclear

----------------------------------------------------------------
ADDITIONAL BEHAVIOUR GUIDELINES (DO NOT OVERRIDE ABOVE RULES)
----------------------------------------------------------------

ELDERLY CONTEXT RULE
After explaining the message, always add brief context such as:
- What this type of message usually means
- Why the user may have received it
- What normally happens next

This context must be calm, reassuring, and in the user's preferred output language.
Do NOT add new facts not present in the message.

DETAIL PRESERVATION RULE
If the message contains:
- Dates
- Times
- Locations
- Names
- Deadlines
- Event titles

You MUST restate ALL of them clearly in the user's preferred output language.
Do not summarise away specific details.

REASSURANCE RULE
Always include at least one short reassurance sentence in the preferred language when appropriate.

Do NOT reassure if the message is actually urgent or risky.

NEXT STEPS CLARITY RULE
In “What should I do now?”:
- Break guidance into clear steps
- Even if no action is needed, explain WHY no action is needed
- If the action is only to remember, attend, or keep note, say that clearly

NON-SCAM CALMING RULE
If the message is informational (exam, schedule, reminder, notice):
- Clearly say it is NOT a problem or warning
- Avoid alerting or fear-inducing words
- Keep tone neutral and steady

FINAL GUIDING PRINCIPLE
Your job is not to be brief.
Your job is to make sure an elderly Tamil user feels:
- Clear about what the message says
- Calm about what it means
- Confident about what to do next

"""


def _build_user_prompt(text: str, language_preference: str) -> str:
    # Keep the assistant output Tamil spoken style as required.
    # Also ensure response is parseable into the required API schema.
    return (
        "User language preference: "
        f"{language_preference}\n\n"
        "Input text (may be English/Tamil/Tanglish, extracted from file, OR a follow-up question block):\n"
        f"{text}\n\n"
        "If the input includes a follow-up block (like 'Original message (context)' and 'User follow-up question'):\n"
        "- Focus on answering the user's follow-up question.\n"
        "- Use the original message only as context.\n"
        "- Do NOT re-explain the full message unless the user asks.\n\n"
        "Return a SINGLE JSON object with keys exactly:\n"
        "{\n"
        '  "explanation": "string",\n'
        '  "urgency": "low|medium|high",\n'
        '  "next_steps": "string",\n'
        '  "reply_options": {\n'
        '     "tamil": "string",\n'
        '     "tanglish": "string",\n'
        '     "english": "string"\n'
        "  }\n"
        "}\n\n"
        "Important:\n"
        "- If language_preference is tamil/tanglish/english:\n"
        "  - explanation + next_steps must be ONLY in that language (no mixed languages).\n"
        "- If language_preference is all:\n"
        "  - explanation + next_steps must include ALL three languages in this order: Tamil, Tanglish, English.\n"
        "  - Clearly label each block with 'Tamil:', 'Tanglish:', 'English:'.\n"
        "  - Keep the emoji headings inside each language block.\n"
        "- explanation should use ONLY these emoji headings: 🟢, 🟡, 🔵, 🟣 (no extra headings).\n"
        "- If scam/suspicious: set urgency=\"high\", warn clearly, and set all reply_options to empty strings.\n"
        "- If unclear: say it's unclear and ask for the missing detail; do NOT guess.\n"
        "- Never provide medical/legal/financial advice.\n"
        "- reply_options rule (IMPORTANT):\n"
        "  - ALWAYS fill reply_options.english (Simple English) with a safe reply suggestion.\n"
        "  - If language_preference=tamil: also fill reply_options.tamil.\n"
        "  - If language_preference=tanglish: also fill reply_options.tanglish.\n"
        "  - If language_preference=english: only fill reply_options.english.\n"
        "  - If language_preference=all: fill reply_options.tamil, reply_options.tanglish, reply_options.english.\n"
    )


def _safe_parse_response(text: str) -> dict[str, Any]:
    text = text.strip()
    # Some models may wrap JSON in code fences; strip gently.
    if text.startswith("```"):
        text = text.strip("`")
        # if it still contains a language header like json\n{...}
        first_brace = text.find("{")
        if first_brace != -1:
            text = text[first_brace:]
    return json.loads(text)


def explain_message(text: str, language_preference: str) -> ExplainMessageResponse:
    client = get_openai_client()

    # Very basic unclear-input guardrail before LLM.
    if not text or len(text.strip()) < 3:
        return ExplainMessageResponse(
            explanation="🟢 Simple Explanation (Tamil)\nIdhu romba kuraiyaana thagaval. Please andha message full-a anuppunga.\n"
            "🔴 Simple Explanation (Tanglish)\nIdhu romba kuraiyaana thagaval. Please andha message full-a anuppunga.\n"
            "🟡 Do I need to worry?\nIppo vendam.\n"
            "🔵 What should I do now?\nMessage full text / screenshot-la irukura ellaa varigalum anuppunga.\n"
            "🟣 Reply Suggestions (Tamil / Tanglish / Simple English)\nIdhula edhuvum seyyave vendam.",
            urgency="low",
            next_steps="Message full-a anuppunga. Link/OTP share pannaadheenga.",
            reply_options=ReplyOptions(tamil="", tanglish="", english=""),
        )

    resp = client.chat.completions.create(
        model=settings.openai_chat_model,
        messages=[
            {"role": "system", "content": MASTER_SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(text, language_preference)},
        ],
        temperature=0.2,
    )

    content = (resp.choices[0].message.content or "").strip()
    try:
        data = _safe_parse_response(content)
        return ExplainMessageResponse(
            explanation=str(data.get("explanation", "")),
            urgency=str(data.get("urgency", "low")),
            next_steps=str(data.get("next_steps", "")),
            reply_options=ReplyOptions(**(data.get("reply_options") or {})),
        )
    except Exception:
        logger.exception("Failed to parse model JSON. Raw=%r", content)
        # Fail safe in Tamil, ask for clarification.
        return ExplainMessageResponse(
            explanation="🟢 Simple Explanation (Tamil)\nIdha parse panna mudiyala. Message konjam clear-a anuppunga.\n"
            "🔴 Simple Explanation (Tanglish)\nIdha parse panna mudiyala. Message konjam clear-a anuppunga.\n"
            "🟡 Do I need to worry?\nIppo vendam.\n"
            "🔵 What should I do now?\nMessage full text copy-paste pannunga illa screenshot anuppunga.\n"
            "🟣 Reply Suggestions (Tamil / Tanglish / Simple English)\nIdhula edhuvum seyyave vendam.",
            urgency="low",
            next_steps="Message full-a anuppunga. Link/OTP share pannaadheenga.",
            reply_options=ReplyOptions(tamil="", tanglish="", english=""),
        )

