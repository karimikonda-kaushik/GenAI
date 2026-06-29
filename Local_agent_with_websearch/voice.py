"""
Edith — Local voice assistant: record mic -> Whisper (speech-to-text) -> Ollama (LLM reply).

Everything runs on your machine — no OpenAI or cloud API keys required.
Requires: Ollama running locally (`ollama serve`) with the model pulled.
Requires: ffmpeg (`brew install ffmpeg`) for reliable mic capture on macOS.
See README.md and EDITH_MANUAL.md for full documentation.
"""

import os
import re
import signal
import subprocess
import tempfile

import numpy as np
import pyttsx3                  # uses macOS built-in system voices (offline)
import soundfile as sf        # reads/writes .wav files
import whisper                # OpenAI's Whisper model, runs locally for transcription
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model  # connects to local Ollama LLM
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# --- Audio settings ---
SAMPLE_RATE = 16000   # 16 kHz — standard rate Whisper expects
FFMPEG_MIC = os.getenv("FFMPEG_MIC", ":0")  # avfoundation mic — :0 = MacBook Pro Microphone

# --- Model settings (override via .env if needed) ---
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")   # local LLM in Ollama
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")        # whisper model size: tiny/base/small/medium

SYSTEM_PROMPT = """
You are Edith, a friendly local voice assistant having a natural conversation.
Answer the user's question directly and conversationally.
Remember what was said earlier in this conversation.
Do not introduce yourself or explain what Llama or AI is unless the user explicitly asks.
Keep replies short (1-3 sentences) since they will be spoken aloud.
Use plain spoken English only — no bullet points, lists, markdown, URLs, or special symbols.
"""

# Say any of these (e.g. "thank you", "exit", "goodbye") to end the conversation
EXIT_PHRASES = {
    "exit", "quit", "stop", "goodbye", "good bye", "bye", "bye bye",
    "thank you", "thanks", "thank you very much", "thanks a lot",
    "that's all", "thats all", "done", "see you", "see you later",
    "ok thank you", "okay thank you", "ok thanks", "okay thanks",
}

# Loaded once on first use, then reused (avoids reloading heavy models every call)
_whisper_model = None
_llm = None
_tts_engine = None


def get_whisper_model():
    """Load Whisper only the first time — subsequent calls reuse the same model."""
    global _whisper_model
    if _whisper_model is None:
        print(f"Loading local Whisper model '{WHISPER_MODEL}'...")
        _whisper_model = whisper.load_model(WHISPER_MODEL)  # downloads on first run
    return _whisper_model


def get_local_llm():
    """Connect to Ollama LLM only the first time — talks to http://localhost:11434."""
    global _llm
    if _llm is None:
        _llm = init_chat_model(OLLAMA_MODEL, model_provider="ollama")
    return _llm


def get_tts_engine():
    """Initialize macOS system TTS once — uses built-in voices."""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = pyttsx3.init()
        _tts_engine.setProperty("rate", 165)   # slower = clearer, fewer cutoffs
        _tts_engine.setProperty("volume", 1.0)
    return _tts_engine


def clean_text_for_speech(text):
    """Remove characters that cause macOS TTS to skip or cut out."""
    text = re.sub(r"\*+|_+|#+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[`$\\|<>{}[\]]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_for_speech(text, max_len=100):
    """Split into small chunks — long single say() calls cut out on macOS."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= max_len:
            chunks.append(sentence)
            continue

        words = sentence.split()
        current = []
        length = 0
        for word in words:
            if length + len(word) + 1 > max_len and current:
                chunks.append(" ".join(current))
                current = [word]
                length = len(word)
            else:
                current.append(word)
                length += len(word) + 1
        if current:
            chunks.append(" ".join(current))

    return chunks or [text]


def normalize_audio(audio):
    """Boost quiet mic input so Whisper can hear it."""
    audio = audio.flatten().astype("float32")
    peak = float(np.max(np.abs(audio)))
    if peak < 1e-6:
        return audio
    if peak < 0.5:
        audio = audio * (0.9 / peak)
    return audio


def check_ffmpeg():
    """ffmpeg + avfoundation is the most reliable mic path on macOS."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("ffmpeg not found. Install it with: brew install ffmpeg")
        raise SystemExit(1)


def check_ollama():
    """Ollama must be running locally before we can get an LLM reply."""
    import urllib.request

    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
    except Exception:
        print(
            "Ollama is not running (connection refused on port 11434).\n"
            "Start it in another terminal:\n"
            "  ollama serve\n"
            "Then pull the model if needed:\n"
            f"  ollama pull {OLLAMA_MODEL}\n"
        )
        raise SystemExit(1)


def record_audio():
    """
    Record using ffmpeg AVFoundation (macOS native mic API).
    More reliable than sounddevice for Cursor / Terminal mic permissions.
    """
    input("Press Enter to start recording...")
    print("Recording... press Enter to stop")

    wav_path = tempfile.mktemp(suffix=".wav")
    proc = subprocess.Popen(
        [
            "ffmpeg", "-y",
            "-loglevel", "error",
            "-f", "avfoundation",
            "-i", FFMPEG_MIC,
            "-ar", str(SAMPLE_RATE),
            "-ac", "1",
            wav_path,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    try:
        input()
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
        proc.wait()

    if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 100:
        print("Recording failed — no audio file created.")
        return np.array([], dtype=np.float32)

    audio, _ = sf.read(wav_path)
    os.remove(wav_path)
    audio = audio.flatten().astype(np.float32)

    duration = len(audio) / SAMPLE_RATE
    peak = float(np.max(np.abs(audio)))
    print(f"Recording complete! ({duration:.1f}s)")
    print(f"Audio level: {peak:.3f}" + (" (very quiet — speak louder)" if peak < 0.01 else ""))

    # Save a copy so you can replay and debug: open(path) in QuickTime
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(temp.name, audio, SAMPLE_RATE)
    print(f"Saved audio to {temp.name}")

    return normalize_audio(audio)


def transcribe(audio):
    """Convert speech audio to text using local Whisper."""
    if len(audio) == 0:
        return ""

    model = get_whisper_model()
    result = model.transcribe(
        audio.astype("float32"),
        language="en",
        fp16=False,
        condition_on_previous_text=False,
    )
    return result["text"].strip()


def should_exit(transcript):
    """True when the user wants to end the conversation."""
    text = transcript.lower().strip().rstrip(".,!?")
    if not text:
        return False
    if text in EXIT_PHRASES:
        return True
    # Short farewells like "thanks bye" or "ok exit"
    words = text.split()
    if len(words) <= 3 and any(w in ("exit", "quit", "stop", "bye") for w in words):
        return True
    return False


def listen_for_speech():
    """Record and transcribe until we get usable speech."""
    while True:
        audio = record_audio()
        print("\nTranscribing locally...")
        transcript = transcribe(audio)
        print(f"You said: {transcript or '(nothing heard)'}")

        if len(transcript.strip()) >= 3:
            return transcript

        print(
            "\nCouldn't hear you clearly — try again.\n"
            "Tip: grant mic access to Cursor in System Settings → Privacy → Microphone.\n"
        )


def ask_local_llm(user_text, history):
    """Send message with full conversation history for multi-turn chat."""
    llm = get_local_llm()
    history.append(HumanMessage(content=user_text))
    response = llm.invoke(history)
    history.append(AIMessage(content=response.content))
    return response.content


def speak(text):
    """Speak reply in small chunks so macOS TTS does not cut out mid-sentence."""
    if not text.strip():
        return

    chunks = split_for_speech(clean_text_for_speech(text))
    print("Speaking response...")

    # macOS `say` is more reliable than one big pyttsx3 call for longer replies
    for chunk in chunks:
        try:
            subprocess.run(["say", "-r", "170", chunk], check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            engine = get_tts_engine()
            engine.say(chunk)
            engine.runAndWait()


# --- Main pipeline: continuous record -> transcribe -> LLM -> speak ---
if __name__ == "__main__":
    check_ffmpeg()
    check_ollama()
    print(f"Edith voice assistant — microphone: ffmpeg AVFoundation {FFMPEG_MIC} @ {SAMPLE_RATE} Hz")
    print("Say 'exit', 'thank you', or 'goodbye' to end the conversation.\n")

    history = [SystemMessage(content=SYSTEM_PROMPT)]

    while True:
        transcript = listen_for_speech()

        if should_exit(transcript):
            speak("Goodbye! Talk to you later.")
            print("\nConversation ended.")
            break

        print("\nAsking local LLM...")
        reply = ask_local_llm(transcript, history)
        speak(reply)
        print("\n--- Ready for your next question ---\n")

