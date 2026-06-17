from faster_whisper import WhisperModel
import subprocess

print("Loading Whisper...")

model = WhisperModel(
    "base",
    device="auto",
    compute_type="int8"
)

segments, info = model.transcribe("voice.wav")

text = ""

for segment in segments:
    text += segment.text

print("\nTranscription:")
print(text)

def speak(text):

    subprocess.run([
        "say",
        "-v",
        "Alex",
        text
    ])

speak(text)