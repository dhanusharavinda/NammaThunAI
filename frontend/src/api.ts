export type LanguagePreference = "tamil" | "tanglish" | "english" | "all";
export type Urgency = "low" | "medium" | "high";

export type ExplainResponse = {
  explanation: string;
  urgency: Urgency;
  next_steps: string;
  reply_options: {
    tamil: string;
    tanglish: string;
    english: string;
  };
  source_text?: string | null;
  tts_audio_base64?: string | null;
  tts_mime_type?: string | null;
};

// Must be domain only (no `/api` suffix). Keep it clean and add `/api` in code.
const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL as string).replace(/\/+$/, "");
const API_BASE_URL = `${BACKEND_URL}/api`;


async function safeJson(res: Response) {
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text || res.statusText };
  }
}

export async function explainMessage(text: string, language_preference: LanguagePreference) {
  const res = await fetch(`${API_BASE_URL}/explain-message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language_preference })
  });
  if (!res.ok) throw await safeJson(res);
  return (await res.json()) as ExplainResponse;
}

export async function voiceInput(
  audioBlob: Blob,
  language_preference: LanguagePreference,
  context_text?: string,
  history?: string
) {
  const form = new FormData();
  const t = (audioBlob.type || "").toLowerCase();
  const ext = t.includes("ogg") ? "ogg" : t.includes("wav") ? "wav" : t.includes("mp3") ? "mp3" : "webm";
  form.append("audio", audioBlob, `voice.${ext}`);
  form.append("language_preference", language_preference);
  // Optional: allow voice as a follow-up question about pasted/uploaded context.
  // The backend will use these when provided.
  // (Kept optional for backward compatibility.)
  if (context_text) form.append("context_text", context_text);
  if (history) form.append("history", history);
  const res = await fetch(`${API_BASE_URL}/voice-input`, { method: "POST", body: form });
  if (!res.ok) throw await safeJson(res);
  return (await res.json()) as ExplainResponse;
}

export async function fileUpload(file: File, language_preference: LanguagePreference) {
  const form = new FormData();
  form.append("file", file);
  form.append("language_preference", language_preference);
  const res = await fetch(`${API_BASE_URL}/file-upload`, { method: "POST", body: form });
  if (!res.ok) throw await safeJson(res);
  return (await res.json()) as ExplainResponse;
}

export function base64ToObjectUrl(b64: string, mimeType: string) {
  const byteChars = atob(b64);
  const byteNumbers = new Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) {
    byteNumbers[i] = byteChars.charCodeAt(i);
  }
  const bytes = new Uint8Array(byteNumbers);
  const blob = new Blob([bytes], { type: mimeType });
  return URL.createObjectURL(blob);
}

