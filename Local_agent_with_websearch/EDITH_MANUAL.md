# Edith Voice Assistant — Technical Manual

**Edith** is a local, privacy-friendly voice assistant. She listens through your microphone, understands speech with OpenAI Whisper (running offline on your machine), reasons with a Llama model via Ollama, and responds aloud using the macOS system voice.

Everything runs on your Mac — no cloud API keys, no data sent to OpenAI or Google.

---

## Table of contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Workflows](#3-workflows)
4. [Setup guide](#4-setup-guide)
5. [Configuration](#5-configuration)
6. [Code walkthrough](#6-code-walkthrough)
7. [Libraries & why we use them](#7-libraries--why-we-use-them)
8. [Troubleshooting](#8-troubleshooting)
9. [Extending Edith](#9-extending-edith)

---

## 1. Overview

### What Edith does

| Step | What happens | Technology |
|------|--------------|------------|
| 1 | You press Enter and speak | ffmpeg + AVFoundation |
| 2 | Your speech becomes text | Whisper (local) |
| 3 | Edith generates an answer | Ollama + LangChain |
| 4 | The answer is spoken aloud | macOS `say` command |
| 5 | Loop continues until you say goodbye | Python `while` loop |

### Design goals

- **Fully local** — works offline after models are downloaded
- **Conversational** — remembers earlier messages in the same session
- **Voice-controlled exit** — say "thank you" or "exit" to stop
- **Reliable on macOS** — ffmpeg for mic capture, chunked TTS to avoid cutouts

---

## 2. Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Microphone │────▶│ record_audio │────▶│ transcribe  │────▶│ should_exit? │
│  (hardware) │     │   (ffmpeg)   │     │  (Whisper)  │     └──────┬───────┘
└─────────────┘     └──────────────┘     └─────────────┘            │
                                                                    │
                    ┌───────────────────────────────────────────────┤
                    │ YES (thank you / exit)                        │ NO
                    ▼                                               ▼
            ┌──────────────┐                              ┌─────────────────┐
            │ speak goodbye│                              │ ask_local_llm   │
            │   → END      │                              │ (Ollama+history)│
            └──────────────┘                              └────────┬────────┘
                                                                   │
                                                                   ▼
                                                          ┌──────────────┐
                                                          │    speak     │
                                                          │ (macOS say)  │
                                                          └──────┬───────┘
                                                                 │
                                                                 ▼
                                                    "Ready for your next question"
                                                                 │
                                                                 └──▶ loop back
```

### Data flow in one line

```
Audio (wav) → numpy array → text string → LLM text reply → spoken chunks
```

---

## 3. Workflows

### 3.1 Startup workflow

```
python voice.py
    │
    ├─▶ check_ffmpeg()     → Is ffmpeg installed?
    ├─▶ check_ollama()     → Is Ollama running on :11434?
    ├─▶ load .env          → OLLAMA_MODEL, WHISPER_MODEL, FFMPEG_MIC
    └─▶ history = [SystemMessage]  → Start empty conversation with rules
```

**Why checks first?** Fails fast with a clear message instead of crashing mid-conversation.

---

### 3.2 Main conversation loop

```
while True:
    │
    ├─▶ listen_for_speech()
    │       ├─ record_audio()  → press Enter, speak, press Enter
    │       └─ transcribe()    → Whisper converts audio to text
    │       (retries if transcription too short)
    │
    ├─▶ should_exit(transcript)?
    │       YES → speak("Goodbye!") → break
    │
    ├─▶ ask_local_llm(transcript, history)
    │       → append user message + get AI reply + save to history
    │
    └─▶ speak(reply)
            → clean text → split sentences → macOS say each chunk
            → "Ready for your next question"
```

---

### 3.3 Recording workflow (`record_audio`)

```
Press Enter to start
    │
    ▼
ffmpeg starts recording from FFMPEG_MIC (:0 = MacBook mic)
    │
    ▼
Press Enter to stop → SIGINT sent to ffmpeg
    │
    ▼
Read .wav file → numpy array
    │
    ▼
normalize_audio() → boost quiet recordings
    │
    ▼
Save debug copy to /tmp/....wav
    │
    ▼
Return audio array to transcribe()
```

**Why ffmpeg instead of Python sounddevice?** On macOS, especially inside Cursor, `sounddevice` often captured silence (`Audio level: 0.000`). ffmpeg uses Apple's native AVFoundation API and is far more reliable for microphone access.

---

### 3.4 Speech-to-text workflow (`transcribe`)

```
Audio numpy array (16 kHz, float32)
    │
    ▼
get_whisper_model()  → load "base" model once (lazy)
    │
    ▼
model.transcribe(audio, language="en", fp16=False)
    │
    ▼
Return text string e.g. "Hi, tell me about RAG"
```

**Why Whisper?** Free, runs locally, good accuracy, no API key. The `base` model balances speed and quality on a laptop.

**Why `fp16=False`?** Mac CPU does not support FP16 well; FP32 avoids warnings and errors.

---

### 3.5 LLM workflow (`ask_local_llm`)

```
history = [
    SystemMessage("You are Edith, a friendly voice assistant..."),
    HumanMessage("What is RAG?"),
    AIMessage("RAG stands for..."),
    HumanMessage("Tell me more"),   ← new message appended
]

    │
    ▼
llm.invoke(history)  → Ollama at http://localhost:11434
    │
    ▼
Append AIMessage(reply) to history
    │
    ▼
Return reply text
```

**Why a system prompt?** Without it, small models like `llama3.2:1b` often reply with generic intros ("I am Llama, a large language model...") instead of answering your question.

**Why conversation history?** Edith remembers context — follow-up questions like "tell me more" work naturally.

---

### 3.6 Text-to-speech workflow (`speak`)

```
LLM reply text
    │
    ▼
clean_text_for_speech()  → remove *, #, URLs, markdown
    │
    ▼
split_for_speech()       → break into ~100 char chunks
    │
    ▼
For each chunk:
    subprocess.run(["say", "-r", "170", chunk])
```

**Why chunk speech?** One long `say` or `pyttsx3` call on macOS often cuts out mid-sentence. Speaking sentence-by-sentence fixes this.

**Why `say` over pyttsx3?** macOS built-in `say` is more reliable for longer replies. pyttsx3 is kept as fallback.

**Why clean text?** Symbols like `*`, URLs, and markdown confuse TTS and cause skips.

---

### 3.7 Exit workflow

User says: **"thank you"**, **"exit"**, **"goodbye"**, etc.

```
transcribe() → "thank you"
    │
    ▼
should_exit() → True  (matches EXIT_PHRASES)
    │
    ▼
speak("Goodbye! Talk to you later.")
    │
    ▼
Conversation ended.
```

---

## 4. Setup guide

### 4.1 Install system dependencies

```bash
# ffmpeg — microphone recording
brew install ffmpeg

# Ollama — local LLM
# Download from https://ollama.com and install
ollama serve
ollama pull llama3.2:1b
```

### 4.2 Install Python packages

```bash
cd /path/to/GenAI
python -m venv .venv
source .venv/bin/activate
pip install -r Local_agent_with_websearch/requirements.txt
```

### 4.3 Configure environment

```bash
cp Local_agent_with_websearch/.env.example Local_agent_with_websearch/.env
```

Example `.env`:

```env
OLLAMA_MODEL=llama3.2:1b
WHISPER_MODEL=base
FFMPEG_MIC=:0
```

### 4.4 Grant microphone access

1. **System Settings → Privacy & Security → Microphone**
2. Enable **Cursor** (or **Terminal**)
3. **System Settings → Sound → Input** → select **MacBook Pro Microphone**
4. Quit and reopen Cursor after granting permission

### 4.5 Run Edith

```bash
cd Local_agent_with_websearch
python voice.py
```

---

## 5. Configuration

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.2:1b` | Ollama model. Larger = smarter but slower. Try `llama3.2:3b`. |
| `WHISPER_MODEL` | `base` | `tiny` (fast), `base` (balanced), `small`/`medium` (accurate) |
| `FFMPEG_MIC` | `:0` | ffmpeg audio device index. List with `ffmpeg -f avfoundation -list_devices true -i ""` |

### Edith's personality (system prompt)

Edith is instructed to:

- Answer directly and conversationally
- Remember the conversation
- Keep replies short (1–3 sentences) for speech
- Use plain English — no bullets, markdown, or URLs
- Not introduce herself as "Llama" unless asked

---

## 6. Code walkthrough

### 6.1 Imports and config

```python
import whisper
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

SAMPLE_RATE = 16000          # Whisper expects 16 kHz audio
FFMPEG_MIC = os.getenv("FFMPEG_MIC", ":0")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
```

**Why 16 kHz?** Whisper is trained on 16 kHz mono audio. ffmpeg records directly at this rate.

---

### 6.2 Lazy model loading

```python
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(WHISPER_MODEL)
    return _whisper_model
```

**Why lazy loading?** Whisper and Ollama models are large. Loading once and reusing saves 5–15 seconds on every turn.

---

### 6.3 Startup checks

```python
def check_ollama():
    urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
```

**Why?** The most common runtime error was `Connection refused` when users forgot to run `ollama serve`. This check explains the fix immediately.

---

### 6.4 Recording with ffmpeg

```python
proc = subprocess.Popen([
    "ffmpeg", "-y",
    "-f", "avfoundation",
    "-i", FFMPEG_MIC,
    "-ar", str(SAMPLE_RATE),
    "-ac", "1",
    wav_path,
], ...)

input()                          # user presses Enter to stop
proc.send_signal(signal.SIGINT)  # gracefully stop ffmpeg
```

**Why SIGINT?** Tells ffmpeg to finalize the `.wav` file cleanly instead of corrupting it.

---

### 6.5 Audio normalization

```python
def normalize_audio(audio):
    peak = float(np.max(np.abs(audio)))
    if peak < 0.5:
        audio = audio * (0.9 / peak)
    return audio
```

**Why?** Quiet mic input causes Whisper to return empty text. Boosting low-volume recordings improves transcription.

---

### 6.6 Exit phrase detection

```python
EXIT_PHRASES = {"exit", "quit", "thank you", "goodbye", "bye", ...}

def should_exit(transcript):
    text = transcript.lower().strip().rstrip(".,!?")
    if text in EXIT_PHRASES:
        return True
    ...
```

**Why a set of phrases?** Voice interfaces need a natural way to end — typing Ctrl+C is not user-friendly when hands-free.

---

### 6.7 Multi-turn conversation

```python
history = [SystemMessage(content=SYSTEM_PROMPT)]

def ask_local_llm(user_text, history):
    history.append(HumanMessage(content=user_text))
    response = llm.invoke(history)
    history.append(AIMessage(content=response.content))
    return response.content
```

**Why append to history?** Each call to Ollama includes all prior messages, so Edith understands follow-up questions in context.

---

### 6.8 Chunked speech output

```python
def split_for_speech(text, max_len=100):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    # ... split long sentences into smaller chunks

def speak(text):
    chunks = split_for_speech(clean_text_for_speech(text))
    for chunk in chunks:
        subprocess.run(["say", "-r", "170", chunk], check=True)
```

**Why max 100 characters?** macOS TTS skips or cuts off when given very long strings in a single call. Short chunks play completely.

---

### 6.9 Main entry point

```python
if __name__ == "__main__":
    check_ffmpeg()
    check_ollama()
    history = [SystemMessage(content=SYSTEM_PROMPT)]

    while True:
        transcript = listen_for_speech()
        if should_exit(transcript):
            speak("Goodbye! Talk to you later.")
            break
        reply = ask_local_llm(transcript, history)
        speak(reply)
```

This is the full Edith loop: **listen → exit check → think → speak → repeat**.

---

## 7. Libraries & why we use them

### Python packages

| Library | Purpose | Why this one |
|---------|---------|--------------|
| **openai-whisper** | Speech-to-text | Best open-source STT; runs fully offline |
| **langchain** | LLM framework | Clean message API (`SystemMessage`, `HumanMessage`) |
| **langchain-ollama** | Ollama connector | One-line `init_chat_model(..., provider="ollama")` |
| **python-dotenv** | Load `.env` | Keep model names and mic settings out of code |
| **soundfile** | Read/write WAV | Simple numpy ↔ audio file conversion |
| **numpy** | Audio arrays | Standard for audio processing in Python |
| **pyttsx3** | TTS fallback | Used if macOS `say` command fails |

### System tools

| Tool | Purpose | Why this one |
|------|---------|--------------|
| **ffmpeg** | Mic recording | AVFoundation access; reliable in Cursor/Terminal |
| **macOS `say`** | Text-to-speech | Native, offline, no extra install |
| **Ollama** | Local LLM | Easy Llama deployment; REST API on :11434 |

### Install command

```bash
pip install -r requirements.txt
```

**requirements.txt contents:**

```
soundfile==0.13.1
python-dotenv==1.2.1
openai-whisper
langchain==0.3.30
langchain-ollama==0.3.6
pyttsx3==2.98
```

Plus system installs: `brew install ffmpeg` and Ollama from [ollama.com](https://ollama.com).

---

## 8. Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| `Connection refused` port 11434 | Ollama not running | `ollama serve` in another terminal |
| `ffmpeg not found` | ffmpeg not installed | `brew install ffmpeg` |
| `Audio level: 0.000` | Mic permission or wrong device | Enable Cursor in Microphone privacy; use MacBook mic |
| `(nothing heard)` from Whisper | Silent or very quiet recording | Speak louder; check saved `.wav` in QuickTime |
| Voice cuts out mid-reply | Long TTS string | Fixed by `split_for_speech()` — update `voice.py` if old |
| "I am Llama..." intro | No system prompt effect | Ensure `SYSTEM_PROMPT` is in `history` |
| Whisper hears "rank" not "RAG" | STT limitation | Speak slower or spell it out |
| AirPods mic silent | Bluetooth latency/permissions | Use built-in MacBook microphone |

### Debug tip

Every recording saves a `.wav` path in the terminal:

```
Saved audio to /var/folders/.../tmpXXXX.wav
```

Open it in QuickTime:

- **Hear yourself?** → mic works; issue is Whisper or LLM
- **Silence?** → mic permission or device problem

---

## 9. Extending Edith

Ideas for future improvements:

| Feature | How |
|---------|-----|
| Web search tool | Add LangChain agent + Tavily/DuckDuckGo tool |
| Wake word ("Hey Edith") | Use `pvporcupine` or similar |
| Better LLM | `ollama pull llama3.2:3b` and set in `.env` |
| Gradio UI | Wrap functions in `gradio.Interface` |
| Faster STT | Replace Whisper with `faster-whisper` |
| Cross-platform | Replace `say` with `pyttsx3` or `edge-tts` on Windows/Linux |

---

## Quick reference card

```
NAME:     Edith
FILE:     voice.py
BRAIN:    Ollama (llama3.2:1b) @ localhost:11434
EARS:     Whisper (base) — local
VOICE:    macOS say command
MIC:      ffmpeg AVFoundation :0
LOOP:     listen → transcribe → LLM → speak → repeat
EXIT:     "thank you" | "exit" | "goodbye" | "bye"
```

---

*Edith — Local Voice Assistant · GenAI Project · `Local_agent_with_websearch/`*
