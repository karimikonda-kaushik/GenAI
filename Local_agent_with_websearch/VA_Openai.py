import os
import tempfile
import sounddevice as sd
import soundfile as sf
import openai
from dotenv import load_dotenv

load_dotenv()

client = openai.OpenAI()

SAMPLE_RATE = 16000
MAX_DURATION = 30


def record_audio() -> str:
    """Record from microphone, return path to temp WAV file."""
    input("Press Enter to start recording...")
    print("Recording... Press Enter to stop.")

    audio_data = sd.rec(
        int(MAX_DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float64",
    )

    input()
    sd.stop()
    print("Recording stopped.")

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio_data, SAMPLE_RATE)
    return tmp.name


def transcribe(audio_path: str) -> str:
    """Send audio to OpenAI Whisper API and return the transcript."""
    with open(audio_path, "rb") as f:
        return client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="text",
        )


def think(text: str) -> str:
    """Send text to GPT and return the response."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful voice assistant. Keep responses short and conversational."},
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content


def speak(text: str):
    """Convert text to speech and play it."""
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="nova",
        input=text,
    ) as response:
        response.stream_to_file(tmp.name)

    data, sr = sf.read(tmp.name)
    sd.play(data, sr)
    sd.wait()
    os.unlink(tmp.name)


audio_file = record_audio()

transcript = transcribe(audio_file)
print(f"\nYou said: {transcript}")
os.unlink(audio_file)

reply = think(transcript)
print(f"AI: {reply}")

speak(reply)
