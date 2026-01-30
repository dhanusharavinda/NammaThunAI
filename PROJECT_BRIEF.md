Tamil Government & Bank Message Explainer (Niche 1)
1. Product Overview
Problem

Tamil-speaking elderly users frequently receive English government, bank, and official messages via:

WhatsApp

SMS

Letters (PDF / image)

They do not understand:

What the message means

Whether it is serious

What action is required
This creates fear, confusion, and dependency on others.

Solution

A Tamil-first AI web app that:

Accepts Tamil voice or text

Accepts English messages or files

Explains them in simple spoken Tamil

Clearly states urgency

Suggests safe reply messages

Warns against scams

2. Target Users

Elderly Tamil speakers

Limited English knowledge

Low digital literacy

Prefer voice over typing

High anxiety around official communication

Design assumption:

Always assume the user is confused or worried.

3. Explicit Scope (Very Important)
INCLUDED

Government messages

Bank messages

Utility messages

Official WhatsApp / SMS / letters

Translation, explanation, reply drafting

Scam detection (basic)


EXCLUDED (INTENTIONALLY)

Medical advice

Legal advice

Prescription interpretation

Financial decision making

Form filling or submission

Payments

The app explains only, it does not decide.

4. Core Features
Input

Tamil voice

Tamil text

English text

Tanglish

PDF files

Image files (text extraction)

Output

Simple Tamil explanation (primary) and Tamil voice output(when clicked button)

Tanglish (optional)

Simple English (optional)



5. AI MASTER SYSTEM PROMPT (DO NOT MODIFY LIGHTLY)
ROLE
You are a patient, trustworthy Tamil-speaking assistant built specifically for elderly users in India.

Your job is to help Tamil-speaking users understand English government, bank, utility, and official messages calmly and clearly.

You are NOT a lawyer, doctor, or government officer.
You NEVER give legal, medical, or financial advice.
You ONLY explain, simplify, and help draft safe replies.

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
6. Suggest safe replies (if applicable)

OUTPUT STRUCTURE (MANDATORY)
🟢 Simple Explanation (Tamil)
🟡 Do I need to worry?
🔵 What should I do now?
🟣 Reply Suggestions (Tamil / Tanglish / Simple English)


If not applicable:

“Idhula edhuvum seyyave vendam.”

LANGUAGE RULES
- Spoken Tamil only
- Short sentences
- No legal or government jargon
- No long paragraphs
- Calm and reassuring tone

REPLY RULES
- Never commit on user’s behalf
- Never confirm payments or documents
- Replies must be neutral and safe
- Offer up to 3 options:
  Tamil, Tanglish, Simple English

SCAM HANDLING

If suspicious:

- Clearly warn user
- Say scam possibility
- Advise not to click links or share OTP
- Do NOT suggest replies

SAFETY RULES
- Never guess missing info
- Never invent deadlines or authorities
- Say clearly if something is unclear

6. Technical Architecture
Backend

Python

FastAPI

AI

OpenAI GPT-4.1 or GPT-4o

Whisper (Tamil STT)

OpenAI TTS (Tamil voice)

File Handling

PDF parsing

Image text extraction

Frontend

Web app (React / Next.js)

Voice-first UX

Large buttons

Minimal text

7. API Design (Backend)
POST /api/explain-message

Input

{
  "text": "string",
  "language_preference": "tamil | tanglish | english"
}


Output

{
  "explanation": "string",
  "urgency": "low | medium | high",
  "next_steps": "string",
  "reply_options": {
    "tamil": "string",
    "tanglish": "string",
    "english": "string"
  }
}

POST /api/voice-input

Accepts audio

Returns same response as above

POST /api/file-upload

PDF / image

Extract text

Pass to LLM

8. UX Principles

One action per screen

Big mic button

Auto-play Tamil voice output

No login for MVP

No clutter

No ads

Trust > fancy visuals