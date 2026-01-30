# Backend (FastAPI)

## Required environment variables

Copy `.env.example` to `.env` and set:

- `OPENAI_API_KEY`

## Run locally

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend will be available at `http://127.0.0.1:8000`.

## API routes (as per brief)

- `POST /api/explain-message` (JSON)
- `POST /api/voice-input` (multipart: `audio` + optional `language_preference`)
- `POST /api/file-upload` (multipart: `file` + optional `language_preference`)

## Notes

- Image OCR uses `pytesseract` and requires the **Tesseract** binary installed (and either on PATH or configured via `TESSERACT_CMD`).
- Scanned PDFs may require **Poppler** (for `pdf2image`) and Tesseract for OCR fallback.

### Windows: install OCR dependencies

Install Tesseract (recommended via winget):

```powershell
winget install --id UB-Mannheim.TesseractOCR
```

Verify:

```powershell
where tesseract
tesseract --version
```

If it's installed but not found, set in `backend/.env`:

- `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`

For scanned PDFs on Windows, install Poppler and set:

- `POPPLER_PATH=C:\path\to\poppler\Library\bin`

