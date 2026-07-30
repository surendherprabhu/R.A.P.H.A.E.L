# R.A.P.H.A.E.L Design Doc

## Overview
R.A.P.H.A.E.L is a desktop assistant with three main capabilities: text chat, speech interaction, and camera-based vision. The app is centered around a local Ollama model and wraps that model with tools for system tasks and file access.

## Goals
- Keep the assistant local-first
- Support both typed and spoken input
- Let the model call tools when needed
- Persist chats and memory between runs
- Provide a simple macOS UI with live camera preview

## Module Breakdown

### `Main.py`
Owns the application lifecycle and UI. It:
- boots Ollama if needed
- creates the Tk/CustomTkinter window
- captures text and voice input
- streams assistant replies into the UI
- drives tool-calling and chat persistence

### `methods.py`
Contains utility functions and tool implementations:
- Ollama startup check
- chat file enumeration
- file read/write helpers
- web search
- time/date/battery helpers
- macOS app launch helper

### `Vision.py`
Owns webcam capture. It:
- opens camera device `0`
- runs a background frame loop
- exposes the latest frame for preview
- captures a still image for multimodal analysis

### `Data.py`
Stores app-wide configuration:
- default model name
- application name
- initial system prompt
- voice model path
- allowed apps list
- startup connection state

## Runtime Flow
1. `Main.py` loads the default conversation and memory file.
2. Ollama is started if the local server is not reachable.
3. The UI is created and the webcam preview starts.
4. User input enters the conversation buffer.
5. The assistant response loop calls Ollama with tool definitions.
6. If the model requests a tool, the Python function runs and the result is appended back to the conversation.
7. Final assistant text is cleaned, displayed, and spoken aloud.

## Tooling Model
The assistant registers functions as Ollama tools. The current tool set includes:
- `get_time`
- `get_date`
- `get_battery`
- `search_web`
- `open_app`
- `list_directory`
- `write_file`
- `read_file`
- `analyze_camera`

This lets the model decide when to query the OS, search the web, inspect files, or inspect the camera image.

## Persistence
The app writes three kinds of local state:
- saved chats in `Dependencies/Data/`
- memory text in `Dependencies/Memories/Memories.json`
- temporary audio/image artifacts in `Dependencies/`

Saving a chat also triggers a memory update pass. The memory is summarized from the current conversation and stored as plain JSON text.

## Concurrency Model
The UI stays responsive by moving slow work off the main thread:
- microphone capture runs through `sounddevice`
- assistant generation runs in a worker thread
- speech synthesis runs in a worker thread
- camera capture runs in a daemon thread

The UI thread only handles rendering and event dispatch.

## Platform Assumptions
The implementation is macOS-oriented:
- `afplay` is used for playback
- `pmset` is used for battery status
- `open -a` is used to launch apps

## Constraints
- Requires a local Ollama server and the configured model name
- Requires a functioning microphone and webcam for full functionality
- App launching is restricted to an allowlist
- Memory and file access are intentionally local and unencrypted

## Potential Improvements
- Add a dependency manifest
- Add a proper settings panel
- Add error handling around missing external binaries
- Separate persistence, UI, and assistant logic more cleanly
- Add tests for tool helpers and chat file handling
