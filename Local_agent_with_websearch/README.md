# Edith — Local Voice Assistant

**Edith** is a fully local voice assistant built with Python. You speak into the microphone, Edith transcribes your words, thinks with a local LLM (Ollama), and speaks the answer back using the macOS system voice. No OpenAI or cloud API keys required.

**Main file:** `voice.py`

---

## Quick start

### 1. Prerequisites (system)

| Requirement | Purpose | Install |
|-------------|---------|---------|
| **Python 3.9+** | Run the app | Pre-installed or [python.org](https://www.python.org/) |
| **ffmpeg** | Reliable mic recording on macOS | `brew install ffmpeg` |
| **Ollama** | Local LLM server | [ollama.com](https://ollama.com/) |

### 2. Start Ollama

```bash
ollama serve
ollama pull llama3.2:1b
```

Keep `ollama serve` running in a separate terminal.

### 3. Python environment

From the project root (`GenAI/`):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r Local_agent_with_websearch/requirements.txt
```

### 4. Configuration (optional)

```bash
cp Local_agent_with_websearch/.env.example Local_agent_with_websearch/.env
```

Edit `.env` if you want a different model or microphone.

### 5. Microphone permission

**System Settings → Privacy & Security → Microphone → enable Cursor** (or Terminal if you run from there).

Use **MacBook Pro Microphone** under **System Settings → Sound → Input** for best results.

### 6. Run Edith

```bash
cd Local_agent_with_websearch
python voice.py
```

---

## Libraries & frameworks

| Package | Version (pinned) | Role in Edith |
|---------|------------------|---------------|
| [openai-whisper](https://github.com/openai/whisper) | latest | Speech-to-text (local) |
| [langchain](https://python.langchain.com/) | 0.3.30 | LLM orchestration |
| [langchain-ollama](https://python.langchain.com/) | 0.3.6 | Connect to Ollama |
| [pyttsx3](https://pypi.org/project/pyttsx3/) | 2.98 | Fallback text-to-speech |
| [soundfile](https://pypi.org/project/soundfile/) | 0.13.1 | Read/write `.wav` audio |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | 1.2.1 | Load `.env` settings |
| [numpy](https://numpy.org/) | (via whisper) | Audio array processing |

**System tools (not pip):**

| Tool | Role |
|------|------|
| **ffmpeg** | Records microphone via macOS AVFoundation |
| **macOS `say`** | Primary text-to-speech (built into macOS) |
| **Ollama** | Runs Llama locally on port `11434` |

---

## How Edith works (short)

```
You speak → ffmpeg records → Whisper transcribes → Ollama replies → macOS speaks
                ↑__________________________________________________|
                        (loop until you say "thank you" or "exit")
```

### Exit phrases

Say any of these to end the conversation:

`thank you` · `thanks` · `goodbye` · `bye` · `exit` · `quit` · `stop` · `done`

---

## Project files

| File | Description |
|------|-------------|
| `voice.py` | Main Edith voice assistant |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |
| `EDITH_MANUAL.md` | Full technical manual with code walkthrough |
| `VA_Openai.py` | Earlier OpenAI-based experiment (not used by Edith) |

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.2:1b` | Ollama model name |
| `WHISPER_MODEL` | `base` | Whisper size: `tiny`, `base`, `small`, `medium` |
| `FFMPEG_MIC` | `:0` | ffmpeg AVFoundation mic index (`:0` = MacBook mic) |

List ffmpeg audio devices:

```bash
ffmpeg -f avfoundation -list_devices true -i ""
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Connection refused` on port 11434 | Run `ollama serve` |
| `ffmpeg not found` | Run `brew install ffmpeg` |
| `Audio level: 0.000` | Grant mic access to Cursor; use MacBook mic, not AirPods |
| Whisper hears wrong words | Speak slower; use a quieter room |
| Voice cuts out mid-reply | Already handled via sentence chunking — see `EDITH_MANUAL.md` |
| `Mic test FAILED` | System Settings → Microphone → enable Cursor, restart Cursor |

---

## For full documentation

See **[EDITH_MANUAL.md](./EDITH_MANUAL.md)** for workflows, architecture diagrams, and explained code snippets.
