# R.A.P.H.A.E.L

R.A.P.H.A.E.L is a local macOS assistant built in Python. It combines text chat, voice input, voice output, webcam vision, and tool use through a local Ollama model.

![R.A.P.H.A.E.L screenshot](https://github.com/user-attachments/assets/e0af861e-817a-4dd9-a714-adf5324822c3)

## Features
- Chat UI built with `customtkinter`
- Local LLM responses through Ollama
- Voice input by holding the left `Alt` key
- Voice output using `piper` plus `afplay`
- Webcam preview and image analysis
- Built-in tools for time, date, battery, web search, app launching, and file access
- Chat saving plus lightweight memory storage

## Requirements
- macOS
- Python 3
- Ollama installed and available on `PATH`
- `piper` installed and available on `PATH`
- A working webcam and microphone
- The bundled voice model at `Non_Github_Dependencies/Voices/en_GB-alan-medium.onnx`

## Python Dependencies
Install the packages used by the app:

```bash
python3 -m pip install customtkinter opencv-python ollama requests sounddevice numpy scipy faster-whisper ddgs pillow
```

## Setup
1. Clone the repository.
2. Install the Python dependencies from the section above.

3. Make sure Ollama is running or let the app start it automatically.
4. Pull the configured model if needed:

```bash
ollama pull qwen3.5:9b
```

5. Confirm `piper` can find the bundled model file.

## Run

```bash
python3 Main.py
```

## Controls
- Type a message and press `Enter` or click `Send`
- Hold left `Alt` to record voice, release to transcribe
- Press `Ctrl+V` to toggle the camera overlay
- Use `+ New Chat` to clear the current conversation
- Use `Save chat` to persist the current thread

## Data Files
- Chat logs: `Dependencies/Data/`
- Memory store: `Dependencies/Memories/Memories.json`
- Voice recordings: `Dependencies/voice.wav`, `Dependencies/speech.wav`
- Camera snapshot: `Dependencies/camera.jpg`

## Notes
- App launching is restricted to the allowlist in `Data.py`
- The assistant is designed around local execution and local files
- Existing build output in `build/` and `dist/` is generated and not required for development
