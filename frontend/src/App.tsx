import React, { useEffect, useRef, useState } from "react";
import {
  explainMessage,
  fileUpload,
  type ExplainResponse,
  type LanguagePreference,
  voiceInput
} from "./api";

type ChatRole = "user" | "assistant";
type ChatMessage = {
  role: ChatRole;
  content: string;
  lang?: LanguagePreference;
  context_text?: string;
  urgency?: ExplainResponse["urgency"];
  tts_audio_base64?: string | null;
  tts_mime_type?: string | null;
};

function urgencyLabel(u: ExplainResponse["urgency"]) {
  if (u === "high") return "High urgency";
  if (u === "medium") return "Medium urgency";
  return "Low urgency";
}

function labelsFor(lang: LanguagePreference) {
  if (lang === "all") return { next: "Next steps", reply: "Reply suggestions" };
  return { next: "Next steps", reply: "Reply suggestion" };
}

function replyBlocksFor(lang: LanguagePreference, r: ExplainResponse) {
  const tamil = (r.reply_options?.tamil || "").trim();
  const tanglish = (r.reply_options?.tanglish || "").trim();
  const english = (r.reply_options?.english || "").trim();

  if (lang === "all") {
    return [
      tamil ? `Tamil:\n${tamil}` : "",
      tanglish ? `Tanglish:\n${tanglish}` : "",
      english ? `English:\n${english}` : ""
    ].filter(Boolean);
  }

  if (lang === "english") return english ? [`English:\n${english}`] : [];

  // Always include English reply suggestion in addition to the selected language.
  const primary = lang === "tanglish" ? tanglish : tamil;
  return [
    primary ? `${lang === "tanglish" ? "Tanglish" : "Tamil"}:\n${primary}` : "",
    english ? `English:\n${english}` : ""
  ].filter(Boolean);
}

function formatExplainForChat(r: ExplainResponse, lang: LanguagePreference) {
  const lbl = labelsFor(lang);
  function normalizeAllBlocks(s: string) {
    const t = (s || "").trim();
    if (!t) return "";
    // Ensure each language block starts on its own paragraph.
    // Handles cases like: "Tamil: ... Tanglish: ... English: ..."
    const withBreaks = t
      .replace(/\s*(Tamil:)\s*/g, "\n\n$1\n")
      .replace(/\s*(Tanglish:)\s*/g, "\n\n$1\n")
      .replace(/\s*(English:)\s*/g, "\n\n$1\n")
      .replace(/^\n+/, "")
      .replace(/\n{3,}/g, "\n\n");
    return withBreaks.trim();
  }

  const explanation = lang === "all" ? normalizeAllBlocks(r.explanation || "") : (r.explanation?.trim() || "");
  const nextSteps = lang === "all" ? normalizeAllBlocks(r.next_steps || "") : (r.next_steps?.trim() || "");

  const parts = [explanation];
  if (nextSteps) parts.push(`${lbl.next}:\n${nextSteps}`);
  const replyBlocks = replyBlocksFor(lang, r);
  if (replyBlocks.length) parts.push(`${lbl.reply}:\n${replyBlocks.join("\n\n")}`);
  return parts.filter(Boolean).join("\n\n").trim();
}

export default function App() {
  const [language, setLanguage] = useState<LanguagePreference>("tamil");

  const [draft, setDraft] = useState("");
  const [aboutOpen, setAboutOpen] = useState(false);

  const [isBusy, setIsBusy] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");

  // Conversational follow-ups (ChatGPT-style).
  const [sourceText, setSourceText] = useState<string>("");
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [followupsUsed, setFollowupsUsed] = useState(0);

  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [currentAudioUrl, setCurrentAudioUrl] = useState<string>("");
  const chatListRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    // Autoplay voice output (as per brief) when available.
    if (!currentAudioUrl) return;
    const a = audioRef.current;
    if (!a) return;
    a.src = currentAudioUrl;
    a.play().catch(() => {});
    return () => {
      try {
        URL.revokeObjectURL(currentAudioUrl);
      } catch {}
    };
  }, [currentAudioUrl]);

  useEffect(() => {
    // Auto-scroll to latest message, ChatGPT-style.
    const el = chatListRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [chat.length, status]);

  function resetMessages() {
    setError("");
    setStatus("");
  }

  function playTts(r: ExplainResponse) {
    if (!r.tts_audio_base64 || !r.tts_mime_type) return;
    try {
      // Stop and revoke previous audio URL (if any).
      if (currentAudioUrl) URL.revokeObjectURL(currentAudioUrl);
    } catch {}
    // Convert base64 to Blob URL (local).
    const byteChars = atob(r.tts_audio_base64);
    const byteNumbers = new Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) byteNumbers[i] = byteChars.charCodeAt(i);
    const bytes = new Uint8Array(byteNumbers);
    const blob = new Blob([bytes], { type: r.tts_mime_type });
    const url = URL.createObjectURL(blob);
    setCurrentAudioUrl(url);
  }

  function playTtsFromParts(b64?: string | null, mime?: string | null) {
    if (!b64 || !mime) return;
    try {
      if (currentAudioUrl) URL.revokeObjectURL(currentAudioUrl);
    } catch {}
    const byteChars = atob(b64);
    const byteNumbers = new Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) byteNumbers[i] = byteChars.charCodeAt(i);
    const bytes = new Uint8Array(byteNumbers);
    const blob = new Blob([bytes], { type: mime });
    const url = URL.createObjectURL(blob);
    setCurrentAudioUrl(url);
  }

  function appendUserMessage(content: string) {
    setChat((prev) => [...prev, { role: "user", content }]);
  }

  function appendAssistantMessage(r: ExplainResponse) {
    const ctx = sourceText || "";
    setChat((prev) => [
      ...prev,
      {
        role: "assistant",
        content: formatExplainForChat(r, language),
        lang: language,
        context_text: ctx,
        urgency: r.urgency,
        tts_audio_base64: r.tts_audio_base64,
        tts_mime_type: r.tts_mime_type
      }
    ]);
    playTts(r);
  }

  function buildFollowupPrompt(question: string) {
    const history = chat.slice(-8).map((m) => `${m.role === "user" ? "User" : "Assistant"}: ${m.content}`).join("\n\n");
    return [
      "You are continuing a conversation about the SAME message.",
      "",
      "Original message (context):",
      sourceText || "(missing)",
      "",
      "Conversation so far:",
      history || "(none)",
      "",
      "User follow-up question:",
      question
    ].join("\n");
  }

  function looksLikeNewMessageContext(msg: string) {
    // Heuristic to reduce cognitive load: long pasted texts are treated as the "message to explain",
    // short texts are treated as follow-up questions.
    const m = msg.trim();
    if (m.length >= 120) return true;
    if (m.split("\n").length >= 3) return true;
    return false;
  }

  async function shareAssistantMessage(m: ChatMessage) {
    if (m.role !== "assistant") return;
    const original = (m.context_text || sourceText || "").trim();
    const text = [
      "Namma thunAI",
      "",
      original ? `Original message:\n${original}` : "Original message:\n(missing)",
      "",
      `Explanation:\n${(m.content || "").trim()}`
    ].join("\n");

    try {
      // Use native share sheet on mobile when available.
      if ((navigator as any).share) {
        await (navigator as any).share({ title: "Namma thunAI", text });
        setStatus("");
        return;
      }
    } catch {
      // If share dialog was cancelled or failed, fall back to clipboard.
    }

    try {
      await navigator.clipboard.writeText(text);
      setStatus("Copied for sharing.");
      return;
    } catch {}

    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setStatus("Copied for sharing.");
    } catch {
      setError("Could not share or copy. Please copy manually.");
    }
  }

  async function onSendText() {
    const msg = draft.trim();
    if (!msg) return;
    resetMessages();
    setIsBusy(true);
    appendUserMessage(msg);
    setDraft("");
    try {
      setStatus("Thinking…");
      const isNewContext = !sourceText || looksLikeNewMessageContext(msg);
      if (!isNewContext && followupsUsed >= 5) {
        setError("Inga 5 follow-up கேள்விகள் மட்டும். Pudhu message anuppunga.");
        setStatus("");
        return;
      }
      if (isNewContext) setSourceText(msg);
      const prompt = isNewContext ? msg : buildFollowupPrompt(msg);
      const r = await explainMessage(prompt, language);
      appendAssistantMessage(r);
      if (!isNewContext) setFollowupsUsed((n) => n + 1);
      if (isNewContext) setFollowupsUsed(0);
      setStatus("");
    } catch (e: any) {
      setError(e?.detail || "Something went wrong.");
      setStatus("");
    } finally {
      setIsBusy(false);
    }
  }

  async function onUploadFile(file: File) {
    resetMessages();
    setIsBusy(true);
    try {
      setStatus("Reading the file…");
      const r = await fileUpload(file, language);
      const extracted = (r.source_text || "").trim();
      appendUserMessage(extracted || "(No text detected from file)");
      if (extracted) setSourceText(extracted);
      setFollowupsUsed(0);
      appendAssistantMessage(r);
      setStatus("");
    } catch (e: any) {
      setError(e?.detail || "Something went wrong.");
      setStatus("");
    } finally {
      setIsBusy(false);
    }
  }

  async function startRecording() {
    resetMessages();

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Microphone not supported in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const preferredTypes = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/ogg"
      ];
      const chosenType = preferredTypes.find((t) => (window as any).MediaRecorder?.isTypeSupported?.(t)) || "";
      const mr = chosenType ? new MediaRecorder(stream, { mimeType: chosenType }) : new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (evt) => {
        if (evt.data.size > 0) chunksRef.current.push(evt.data);
      };
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blobType = mr.mimeType || chosenType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: blobType });
        await sendVoice(blob);
      };
      mediaRecorderRef.current = mr;
      mr.start();
      setIsRecording(true);
      setStatus("Listening…");
    } catch {
      setError("Could not access microphone. Please allow permission.");
    }
  }

  function stopRecording() {
    const mr = mediaRecorderRef.current;
    if (!mr) return;
    if (mr.state !== "inactive") mr.stop();
    setIsRecording(false);
    setStatus("Sending…");
  }

  async function sendVoice(blob: Blob) {
    setIsBusy(true);
    try {
      setStatus("Understanding your voice…");
      const isFollowup = !!sourceText;
      if (isFollowup && followupsUsed >= 5) {
        setError("Inga 5 follow-up கேள்விகள் மட்டும். Pudhu message anuppunga.");
        setStatus("");
        return;
      }
      const history = chat.slice(-8).map((m) => `${m.role === "user" ? "User" : "Assistant"}: ${m.content}`).join("\n\n");
      // If the user already pasted/uploaded something, treat voice as a FOLLOW-UP QUESTION.
      const r = await voiceInput(blob, language, sourceText || "", history || "");
      const spoken = (r.source_text || "").trim();
      appendUserMessage(spoken || "(Voice input)");
      if (!sourceText && spoken) setSourceText(spoken);
      appendAssistantMessage(r);
      if (isFollowup) setFollowupsUsed((n) => n + 1);
      if (!isFollowup) setFollowupsUsed(0);
      setStatus("");
    } catch (e: any) {
      setError(e?.detail || "Something went wrong.");
      setStatus("");
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <div className="wa">
      <header className="waHeader">
        <div className="waHeaderLeft">
          <div className="waTitle">
            Namma thun<span className="waAI">AI</span>
          </div>
          <div className="waSubtitle">Calm explanations for confusing English messages</div>
          <button className="waAboutBtn" onClick={() => setAboutOpen(true)} disabled={isBusy || isRecording}>
            Idhu enna? / What’s this?
          </button>
        </div>

        <div className="waHeaderRight">
          <select
            className="waLang"
            value={language}
            onChange={(e) => setLanguage(e.target.value as LanguagePreference)}
            disabled={isBusy || isRecording}
            aria-label="Output language"
          >
            <option value="tamil">Tamil</option>
            <option value="tanglish">Tanglish</option>
            <option value="english">English</option>
            <option value="all">All</option>
          </select>

          <button
            className="waIconBtn"
            onClick={() => {
              setChat([]);
              setSourceText("");
              setDraft("");
              setFollowupsUsed(0);
              resetMessages();
            }}
            disabled={isBusy || isRecording}
            aria-label="Clear chat"
            title="Clear"
          >
            ×
          </button>
        </div>
      </header>

      {aboutOpen && (
        <div
          className="waModalOverlay"
          role="dialog"
          aria-modal="true"
          aria-label="About Namma thunAI"
          onMouseDown={(e) => {
            // click outside to close
            if (e.target === e.currentTarget) setAboutOpen(false);
          }}
        >
          <div className="waModal">
            <div className="waModalHeader">
              <div className="waModalTitle">
                Namma thun<span className="waAI">AI</span>
              </div>
              <button className="waIconBtn" onClick={() => setAboutOpen(false)} aria-label="Close about">
                ×
              </button>
            </div>
            <div className="waModalBody">
              <div className="waModalLead">Calm explanations for confusing English messages</div>
              <div className="waModalText">
                Bank, government, WhatsApp message ellam English-la vandha confuse aagum.
                <br />
                Indha app adha simple Tamil-la explain pannum.
                <br />
                Scam-aa illa genuine-aa nu sollum.
                <br />
                Reply eppadi panradhu nu help pannum.
                <br />
                Type panna vendam. Pesinaalum podhum.
              </div>
            </div>
          </div>
        </div>
      )}

      <main className="waChat" ref={chatListRef} aria-live="polite">
        {chat.length === 0 ? (
          <div className="waEmpty">
            Paste a message below and press Send.
          </div>
        ) : (
          chat.map((m, idx) => (
            <div key={idx} className={`waRow ${m.role}`}>
              <div className={`waBubble ${m.role}`}>
                <div className="waMeta">
                  <span className="waName">{m.role === "user" ? "You" : "Assistant"}</span>
                  {m.role === "assistant" && m.urgency ? (
                    <span className={`waPill ${m.urgency}`}>{urgencyLabel(m.urgency)}</span>
                  ) : null}
                  {m.role === "assistant" && m.tts_audio_base64 && m.tts_mime_type ? (
                    <button
                      className="waLinkBtn"
                      onClick={() => playTtsFromParts(m.tts_audio_base64, m.tts_mime_type)}
                      disabled={isBusy || isRecording}
                    >
                      Play voice
                    </button>
                  ) : null}
                  {m.role === "assistant" ? (
                    <button
                      className="waLinkBtn"
                      onClick={() => shareAssistantMessage(m)}
                      disabled={isBusy || isRecording}
                      title="Share to family"
                    >
                      Share
                    </button>
                  ) : null}
                </div>
                <div className="waText">{m.content}</div>
              </div>
            </div>
          ))
        )}

        {status ? <div className="waStatus">{status}</div> : null}
        {error ? <div className="waError">{error}</div> : null}
      </main>

      <footer className="waInputBar">
        <input
          className="waInput"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={isBusy || isRecording}
          placeholder="Type or paste message…"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              onSendText();
            }
          }}
        />

        <button
          className={`waIconBtn ${isRecording ? "danger" : ""}`}
          onClick={() => {
            if (isBusy) return;
            if (isRecording) stopRecording();
            else startRecording();
          }}
          disabled={isBusy}
          aria-label="Voice"
          title={isRecording ? "Stop" : "Mic"}
        >
          🎤
        </button>

        <button
          className="waIconBtn"
          onClick={() => fileInputRef.current?.click()}
          disabled={isBusy || isRecording}
          aria-label="Upload file"
          title="Upload file"
        >
          📎
        </button>

        <button className="waSendBtn" onClick={onSendText} disabled={isBusy || isRecording || draft.trim().length < 1}>
          Send
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,image/*"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (!f) return;
            // Allow picking same file again later
            e.currentTarget.value = "";
            onUploadFile(f);
          }}
        />

        {/* Hidden audio element (no big player UI) */}
        <audio ref={audioRef} style={{ display: "none" }} />
      </footer>
    </div>
  );
}

