# Tamil Government & Bank Message Explainer

Voice-first Tamil web app for elderly users to understand **English government/bank/utility/official messages** safely and calmly.  
It **explains only** — it does **not** provide medical/legal/financial advice.

## Project structure

```
PROJECT_TAMILLM/
  backend/
    app/
      api/routes.py
      core/config.py
      core/logging.py
      services/
        explainer.py
        file_extract.py
        openai_client.py
        stt.py
        tts.py
      main.py
      schemas.py
    .env.example
    requirements.txt
    README.md
  frontend/
    src/
      api.ts
      App.tsx
      main.tsx
      styles.css
    .env.example
    index.html
    package.json
    tsconfig.json
    vite.config.ts
    README.md
  PROJECT_BRIEF.md
```

## API (exact routes from brief)

- `POST /api/explain-message`
  - JSON: `{ "text": "string", "language_preference": "tamil|tanglish|english" }`
  - JSON response includes the required fields:
    - `explanation`, `urgency`, `next_steps`, `reply_options`
  - Also includes optional `tts_audio_base64` and `tts_mime_type` so the frontend can play Tamil audio **without adding any new routes**.

- `POST /api/voice-input`
  - multipart form:
    - `audio`: file
    - `language_preference`: optional
  - Returns same schema as above

- `POST /api/file-upload`
  - multipart form:
    - `file`: PDF/image
    - `language_preference`: optional
  - Returns same schema as above

## Run locally (Windows PowerShell)

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set OPENAI_API_KEY
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open `http://localhost:5173`.

## System prompt + safety constraints

The backend uses the **MASTER SYSTEM PROMPT** from `PROJECT_BRIEF.md` (embedded in `backend/app/services/explainer.py`) and instructs the model to:

- Explain calmly in **spoken Tamil**
- Follow the required sectioned structure (🟢/🟡/🔵/🟣)
- Warn about scams (OTP/link rules)
- Never provide medical/legal/financial advice
- Never guess missing info

## Notes (dependencies for file/voice)

- **Microphone**: browser permission required.
- **Image OCR**: requires installing **Tesseract OCR** (used by `pytesseract`).
- **Scanned PDFs**: OCR fallback uses `pdf2image` and may require **Poppler** (Windows).

### Install Tesseract (Windows)

Option A (recommended, winget):

```powershell
winget install --id UB-Mannheim.TesseractOCR
```

Then restart your terminal and verify:

```powershell
where tesseract
tesseract --version
```

If `tesseract` is installed but not found, set this in `backend/.env`:

- `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`

### Poppler (only for scanned PDF OCR on Windows)

If scanned PDF OCR returns empty, install Poppler and set `backend/.env`:

- `POPPLER_PATH=C:\path\to\poppler\Library\bin`

## Where to extend later (without changing current scope)

- Improve PDF OCR reliability (better heuristics + clearer user guidance when OCR fails).
- Add stronger structured extraction (message type detection + explicit fields) while still returning the same API response.
- Add rate limiting / request IDs / audit logging for production deployments.

