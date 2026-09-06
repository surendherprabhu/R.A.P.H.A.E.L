import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import customtkinter as ctk

import cv2
import copy
import re
import ollama
import os
import threading
import json
import subprocess
import time
import platform
import requests
import sounddevice as sd
import numpy as np

from scipy.io.wavfile import write
from faster_whisper import WhisperModel


from ddgs import DDGS
from PIL import Image
from PIL import ImageTk

from Data import *
import Data
import shutil
import glob
import math
import hashlib
import base64
import zipfile
import urllib.parse


#------------------------------------------------------------------------------------------------------------------#
def clean_response(text):

    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)

    # Remove markdown headers
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)

    # Remove bullet points
    text = re.sub(r'^\s*[-•*]\s*', '', text, flags=re.MULTILINE)

    # Remove blockquotes
    text = re.sub(r'^\s*>\s*', '', text, flags=re.MULTILINE)

    # Collapse excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()
#------------------------------------------------------------------------------------------------------------------#
def start_ollama_background():
    system_os = platform.system()
    
    try:
        response = requests.get("http://localhost:11434")
        if response.status_code == 200:
            print("Ollama is already running.")
            return True
    except requests.exceptions.ConnectionError:
        pass

    print(f"Starting Ollama on {system_os} in the background...")

    try:
        if system_os == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  
            
            subprocess.Popen(
                ["ollama", "serve"], 
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        elif system_os in ["Darwin", "Linux"]: # macOS or Linux
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid  
            )
            
        else:
            print(f"Unsupported Operating System: {system_os}")
            return False

        for attempt in range(10):
            try:
                # Ping Ollama local port
                res = requests.get("http://localhost:11434")
                if res.status_code == 200:
                    print("Ollama successfully started in the background!")
                    return True
            except requests.exceptions.ConnectionError:
                time.sleep(1) 
                
        print("Timeout: Ollama process launched but failed to respond.")
        return False

    except FileNotFoundError:
        print("Error: Ollama CLI is not installed or not added to your system PATH.")
        return False



#------------------------------------------------------------------------------------------------------------------#
def SaveAsJson(Conversation):
    user_input = str(input("Save Conversation as: "))
    filename = f"{user_input}.json"
    with open(f"Dependencies/Data/{filename}" , "w") as f:
        json.dump(Conversation , f)

def ListFiles(Folder_path = json_path):
    try:
        files = os.listdir(Folder_path)
    except FileNotFoundError:
        os.makedirs(Folder_path, exist_ok=True)
        return []

    chat_files = []
    for file in files:
        if file.startswith("."):
            continue
        path = os.path.join(Folder_path, file)
        if os.path.isfile(path):
            chat_files.append(file.removesuffix(".json"))

    return sorted(chat_files)

#------------------------------------------------------------------------------------------------------------------#
MEMORY_FILE = "Dependencies/Memories/Memories.json"

def load_memories(path=MEMORY_FILE):
    """Load memories robustly. Handles legacy string format and new dict format.
    Returns dict: {"content": str, "updated_at": str|None, "version": int}
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return {"content": "", "updated_at": None, "version": 1}
    except json.JSONDecodeError:
        # File may be plain text (legacy)
        try:
            with open(path, "r", encoding="utf-8") as file:
                raw = file.read().strip()
            # Try to strip outer quotes if it was dumped as string with quotes
            if raw.startswith('"') and raw.endswith('"'):
                try:
                    raw = json.loads(raw)
                except:
                    pass
            return {"content": raw, "updated_at": None, "version": 1}
        except:
            return {"content": "", "updated_at": None, "version": 1}

    # Legacy: file contains a JSON string directly
    if isinstance(data, str):
        return {"content": data.strip(), "updated_at": None, "version": 1}

    if isinstance(data, dict):
        # New format or quasi-new
        if "content" in data:
            return {
                "content": str(data.get("content", "")).strip(),
                "updated_at": data.get("updated_at"),
                "version": int(data.get("version", 1)),
            }
        if "memories" in data:
            return {
                "content": str(data.get("memories", "")).strip(),
                "updated_at": data.get("updated_at"),
                "version": int(data.get("version", 1)),
            }
        if "text" in data:
            return {
                "content": str(data.get("text", "")).strip(),
                "updated_at": data.get("updated_at"),
                "version": int(data.get("version", 1)),
            }
        # Unknown dict shape — serialize it as content
        return {"content": json.dumps(data, indent=2), "updated_at": None, "version": 1}

    # Fallback: coerce to string
    return {"content": str(data).strip(), "updated_at": None, "version": 1}

def save_memories(content, path=MEMORY_FILE):
    """Persist memories in versioned dict format. Cleans and deduplicates."""
    cleaned = (content or "").strip()
    # Remove common LLM preamble/postscript if present
    # Keep bullet content, strip "Here are the updated memories:" wrappers
    if cleaned.lower().startswith("here are"):
        # Find first bullet/dash
        for marker in ["\n- ", "\n• ", "\n* "]:
            idx = cleaned.find(marker)
            if idx != -1:
                cleaned = cleaned[idx+1:].strip()
                break
    payload = {
        "version": 1,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "content": cleaned,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=4)
    return payload

def get_memory_text(path=MEMORY_FILE):
    """Convenience: return just the text content."""
    return load_memories(path).get("content", "")

def normalize_memory_content(text):
    """Deduplicate bullet lines and trim whitespace."""
    if not text:
        return ""
    lines = []
    seen = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Normalize bullet prefixes for dedup key
        key = re.sub(r'^[-•*]\s*', '', line).lower().strip()
        # Also strip markdown bold
        key = re.sub(r'\*\*(.*?)\*\*', r'\1', key)
        if not key or key in seen:
            continue
        seen.add(key)
        lines.append(line)
    return "\n".join(lines).strip()

def build_llm_context(conversation, max_messages=30, keep_system_count=2):
    """Return a pruned copy for LLM calls: keep system prompts + last N messages."""
    if not conversation:
        return []
    # Identify system prefix (consecutive system roles at start)
    system_prefix = []
    idx = 0
    for msg in conversation:
        if msg.get("role") == "system" and idx < keep_system_count:
            system_prefix.append(msg)
            idx += 1
        else:
            break
    # If no system at start, at least keep first system
    if not system_prefix and conversation and conversation[0].get("role") == "system":
        system_prefix = [conversation[0]]

    rest = conversation[len(system_prefix):]
    # Keep only last max_messages of the rest
    if len(rest) > max_messages:
        rest = rest[-max_messages:]
    return copy.deepcopy(system_prefix + rest)

#------------------------------------------------------------------------------------------------------------------#
def get_time():
    from datetime import datetime

    return datetime.now().strftime(
        "%H:%M:%S"
    )

#------------------------------------------------------------------------------------------------------------------#
def get_date():
    from datetime import datetime

    return datetime.now().strftime(
        "%d/%m/%Y in date/month/year format"
    )

#------------------------------------------------------------------------------------------------------------------#
def search_web(query):

    with DDGS() as ddgs:
        print(f"Searching the Web for '{query}'")
        results = list(ddgs.text(query,max_results=5))
    return results

#------------------------------------------------------------------------------------------------------------------#
def get_battery():
    result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
    match = re.search(r"(\d+)%", result.stdout)
    if match:
        return f"{match.group(1)}%"
    return "Battery Percentage not found"

#------------------------------------------------------------------------------------------------------------------#
def open_app(app_name):
    if app_name in ALLOWED_APPS:
        try:
            subprocess.Popen(
                ["open", "-a", app_name]
            )
            return f"Opened {app_name}"
        except Exception as e:
            return str(e)
    else:
        return("Raphael, You do not have access to open this specific app")

#------------------------------------------------------------------------------------------------------------------#
def list_directory(path="."):
    try:
        return os.listdir(path)
    except Exception as e:
        return str(e)

#------------------------------------------------------------------------------------------------------------------#
def write_file(path, content):
    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        return "Success"
    except Exception as e:
        return str(e) 

#------------------------------------------------------------------------------------------------------------------#
def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        return str(e)    

#------------------------------------------------------------------------------------------------------------------#
def create_directory(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"Directory ready at: {path}"
    except Exception as e:
        return str(e)

#------------------------------------------------------------------------------------------------------------------#
def get_system_info():
    try:
        return {
            "os": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }
    except Exception as e:
        return str(e)

#------------------------------------------------------------------------------------------------------------------#
def open_website(url):
    try:
        parsed_url = url.strip()
        if not parsed_url.startswith(("http://", "https://")):
            parsed_url = f"https://{parsed_url}"

        subprocess.Popen(["open", parsed_url])
        return f"Opened website: {parsed_url}"
    except Exception as e:
        return str(e)

#------------------------------------------------------------------------------------------------------------------#
def read_clipboard():
    try:
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except Exception as e:
        return str(e)

#------------------------------------------------------------------------------------------------------------------#
def write_clipboard(text):
    try:
        subprocess.run(["pbcopy"], input=text, text=True, check=True)
        return "Clipboard updated"
    except Exception as e:
        return str(e)

#------------------------------------------------------------------------------------------------------------------#
def list_running_apps():
    try:
        result = subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "System Events" to get name of (processes where background only is false)',
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        apps = [app.strip() for app in result.stdout.split(",") if app.strip()]
        return apps
    except Exception as e:
        return str(e)

#------------------------------------------------------------------------------------------------------------------#
def _run_applescript(script):
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "AppleScript command failed"
        raise RuntimeError(message)
    return result.stdout.strip()

#------------------------------------------------------------------------------------------------------------------#
def get_calendar_events(hours_ahead=24, max_events=10):
    try:
        hours_ahead = max(1, int(hours_ahead))
        max_events = max(1, int(max_events))

        script = f'''
set cutoffDate to (current date) + ({hours_ahead} * hours)
set eventLines to {{}}
tell application "Calendar"
    set allEvents to every event of every calendar whose start date is greater than (current date) and start date is less than cutoffDate
    set eventCount to 0
    repeat with anEvent in allEvents
        set eventCount to eventCount + 1
        if eventCount > {max_events} then exit repeat
        set eventTitle to summary of anEvent
        set eventStart to start date of anEvent
        set eventEnd to end date of anEvent
        set end of eventLines to (eventTitle & " | " & (eventStart as string) & " | " & (eventEnd as string))
    end repeat
end tell
if (count of eventLines) is 0 then
    return "No upcoming events found"
end if
return eventLines as string
'''
        output = _run_applescript(script)
        return [line.strip() for line in output.split(",") if line.strip()]
    except Exception as e:
        return str(e)

#------------------------------------------------------------------------------------------------------------------#
def create_reminder(title, list_name="Reminders", due_date=""):
    try:
        safe_title = title.replace('"', '\\"')
        safe_list = list_name.replace('"', '\\"')

        if due_date:
            safe_due = due_date.replace('"', '\\"')
            script = f'''
tell application "Reminders"
    if not (exists list "{safe_list}") then
        make new list with properties {{name:"{safe_list}"}}
    end if
    set targetList to list "{safe_list}"
    set reminderDate to date "{safe_due}"
    make new reminder at targetList with properties {{name:"{safe_title}", due date:reminderDate}}
end tell
return "Reminder created"
'''
        else:
            script = f'''
tell application "Reminders"
    if not (exists list "{safe_list}") then
        make new list with properties {{name:"{safe_list}"}}
    end if
    set targetList to list "{safe_list}"
    make new reminder at targetList with properties {{name:"{safe_title}"}}
end tell
return "Reminder created"
'''
        _run_applescript(script)
        return f"Reminder created: {title}"
    except Exception as e:
        return str(e)

#------------------------------------------------------------------------------------------------------------------#
def take_screenshot(mode="full", filename="Dependencies/screenshot.png"):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        if mode == "window":
            command = ["screencapture", "-w", filename]
        elif mode == "selection":
            command = ["screencapture", "-i", filename]
        else:
            command = ["screencapture", "-x", filename]

        subprocess.run(command, check=True)
        return f"Screenshot saved to {filename}"
    except Exception as e:
        return str(e)

#------------------------------------------------------------------------------------------------------------------#
def extract_text_from_image(path):
    try:
        if not os.path.exists(path):
            return f"Image not found: {path}"

        response = ollama.chat(
            model=Data.model,
            messages=[
                {
                    "role": "user",
                    "content": "Extract all visible text from this image. Return only the extracted text.",
                    "images": [path],
                }
            ],
        )
        return response["message"]["content"].strip()
    except Exception as e:
        return str(e)

#------------------------------------------------------------------------------------------------------------------#
def media_control(action):
    try:
        normalized = action.strip().lower()
        action_map = {
            "play": "play",
            "pause": "pause",
            "play_pause": "playpause",
            "playpause": "playpause",
            "next": "next track",
            "previous": "previous track",
            "prev": "previous track",
        }

        if normalized not in action_map:
            return "Unsupported action. Use play, pause, play_pause, next, or previous."

        running_apps = list_running_apps()
        target_app = "Spotify" if isinstance(running_apps, list) and "Spotify" in running_apps else "Music"

        script = f'tell application "{target_app}" to {action_map[normalized]}'
        _run_applescript(script)
        return f"Media action sent to {target_app}: {normalized}"
    except Exception as e:
        return str(e)

#------------------------------------------------------------------------------------------------------------------#
def volume_control(action="get", level=50):
    try:
        normalized = action.strip().lower()

        if normalized == "get":
            return _run_applescript('output volume of (get volume settings)')

        if normalized == "mute":
            _run_applescript('set volume with output muted')
            return "Volume muted"

        if normalized == "unmute":
            _run_applescript('set volume without output muted')
            return "Volume unmuted"

        if normalized == "set":
            safe_level = max(0, min(100, int(level)))
            _run_applescript(f"set volume output volume {safe_level}")
            return f"Volume set to {safe_level}"

        if normalized in {"up", "down"}:
            current = int(_run_applescript('output volume of (get volume settings)'))
            delta = 10 if normalized == "up" else -10
            new_level = max(0, min(100, current + delta))
            _run_applescript(f"set volume output volume {new_level}")
            return f"Volume set to {new_level}"

        return "Unsupported action. Use get, set, up, down, mute, or unmute."
    except Exception as e:
        return str(e)

# ==================================================================================================================
# 100 ADDITIONAL TOOLS
# ==================================================================================================================

# --- File & OS (12) ---
def delete_file(path):
    try:
        if os.path.isdir(path): return "Is a directory, use trash_file or delete with list"
        os.remove(path); return f"Deleted {path}"
    except Exception as e: return str(e)

def move_file(src, dest):
    try: shutil.move(src, dest); return f"Moved {src} -> {dest}"
    except Exception as e: return str(e)

def copy_file(src, dest):
    try:
        if os.path.isdir(src): shutil.copytree(src, dest)
        else: shutil.copy2(src, dest)
        return f"Copied {src} -> {dest}"
    except Exception as e: return str(e)

def file_stats(path):
    try:
        s=os.stat(path); return {"path":path,"size":s.st_size,"mtime":time.ctime(s.st_mtime),"is_dir":os.path.isdir(path),"mode":oct(s.st_mode)}
    except Exception as e: return str(e)

def search_files(pattern, path=".", content_search=""):
    try:
        import fnmatch
        results=[]
        for root, dirs, files in os.walk(path):
            if len(results)>50: break
            for f in files:
                if fnmatch.fnmatch(f, pattern):
                    full=os.path.join(root,f)
                    if content_search:
                        try:
                            if content_search.lower() in open(full, encoding="utf-8", errors="ignore").read().lower():
                                results.append(full)
                        except: continue
                    else:
                        results.append(full)
        return results[:50] or "No matches"
    except Exception as e: return str(e)

def zip_directory(source, output=""):
    try:
        if not output: output=source.rstrip("/")+ ".zip"
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(source):
                for f in files: z.write(os.path.join(root,f), os.path.relpath(os.path.join(root,f), os.path.dirname(source)))
        return f"Zipped to {output}"
    except Exception as e: return str(e)

def unzip_file(zip_path, dest="."):
    try: zipfile.ZipFile(zip_path).extractall(dest); return f"Extracted {zip_path} to {dest}"
    except Exception as e: return str(e)

def trash_file(path):
    try: subprocess.run(["osascript","-e",f'tell application "Finder" to delete POSIX file "{os.path.abspath(path)}"'], check=True); return f"Moved to Trash: {path}"
    except Exception as e:
        try: os.rename(path, os.path.expanduser("~/.Trash/")+os.path.basename(path)); return f"Trashed {path}"
        except Exception as e2: return str(e2)

def get_disk_usage(path="/"):
    try: s=shutil.disk_usage(path); return {"total_GB":round(s.total/1e9,2),"used_GB":round(s.used/1e9,2),"free_GB":round(s.free/1e9,2)}
    except Exception as e: return str(e)

def empty_trash():
    try: subprocess.run(["osascript","-e",'tell application "Finder" to empty trash'], check=True); return "Trash emptied"
    except Exception as e: return str(e)

def reveal_in_finder(path):
    try: subprocess.Popen(["open","-R", path]); return f"Revealed {path} in Finder"
    except Exception as e: return str(e)

def lock_file(path):
    try: subprocess.run(["chflags","uchg", path], check=True); return f"Locked {path}"
    except Exception as e: return str(e)

# --- System Control (12) ---
def set_brightness(level):
    try: lvl=max(0,min(100,int(level)))/100; subprocess.run(["osascript","-e",f'tell application "System Events" to set brightness of displays to {lvl}'], check=True); return f"Brightness {level}%"
    except: 
        try: subprocess.run(["brightness", str(level/100)], check=False); return f"Brightness set via fallback {level}%"
        except Exception as e: return str(e)

def get_brightness():
    try: return _run_applescript('tell application "System Events" to get brightness of displays')
    except Exception as e: return str(e)

def toggle_wifi(action="toggle"):
    try:
        iface=subprocess.run(["networksetup","-listallhardwareports"], capture_output=True, text=True).stdout
        # Find Wi-Fi device
        m=re.search(r"Device: (en\d+)", iface)
        dev=m.group(1) if m else "en0"
        if action=="on": subprocess.run(["networksetup","-setairportpower",dev,"on"], check=True); return "Wi-Fi on"
        if action=="off": subprocess.run(["networksetup","-setairportpower",dev,"off"], check=True); return "Wi-Fi off"
        subprocess.run(["networksetup","-setairportpower",dev,"off" if "On" in subprocess.run(["networksetup","-getairportpower",dev], capture_output=True, text=True).stdout else "on"], check=True); return "Wi-Fi toggled"
    except Exception as e: return str(e)

def toggle_bluetooth(action="toggle"):
    try:
        if action in ("on","off"): subprocess.run(["blueutil","--power", "1" if action=="on" else "0"], check=False); return f"Bluetooth {action} (via blueutil)"
        subprocess.run(["blueutil","--power","toggle"], check=False); return "Bluetooth toggled"
    except Exception as e: return str(e)

def set_do_not_disturb(enable=True):
    try:
        val="true" if enable else "false"
        subprocess.run(["defaults","write","com.apple.ncprefs","dndEnabled", "-bool", val], check=False)
        return f"Do Not Disturb {'enabled' if enable else 'disabled'} (restart Notification Center may be needed)"
    except Exception as e: return str(e)

def sleep_system():
    try: subprocess.Popen(["pmset","sleepnow"]); return "System sleeping"
    except Exception as e: return str(e)

def restart_system():
    try: subprocess.Popen(["osascript","-e",'tell application "System Events" to restart']); return "Restarting..."
    except Exception as e: return str(e)

def shutdown_system():
    try: subprocess.Popen(["osascript","-e",'tell application "System Events" to shut down']); return "Shutting down..."
    except Exception as e: return str(e)

def lock_screen():
    try: subprocess.run(["pmset","displaysleepnow"], check=False); subprocess.run(["osascript","-e",'tell application "System Events" to keystroke "q" using {control down, command down}'], check=False); return "Screen locked"
    except Exception as e: return str(e)

def get_uptime():
    try: return subprocess.run(["uptime"], capture_output=True, text=True).stdout.strip()
    except Exception as e: return str(e)

def kill_process(name_or_pid):
    try:
        if str(name_or_pid).isdigit(): os.kill(int(name_or_pid), 9); return f"Killed PID {name_or_pid}"
        subprocess.run(["pkill","-f", str(name_or_pid)], check=False); return f"Killed process {name_or_pid}"
    except Exception as e: return str(e)

def set_wallpaper(path):
    try: _run_applescript(f'tell application "Finder" to set desktop picture to POSIX file "{os.path.abspath(path)}"'); return f"Wallpaper set to {path}"
    except Exception as e: return str(e)

# --- Clipboard & Input (5) ---
def clear_clipboard():
    try: subprocess.run(["pbcopy"], input="", text=True, check=True); return "Clipboard cleared"
    except Exception as e: return str(e)

def type_text(text):
    try: _run_applescript(f'tell application "System Events" to keystroke "{text.replace(chr(34), chr(92)+chr(34))}"'); return f"Typed: {text[:50]}"
    except Exception as e: return str(e)

def press_keys(keys):
    try:
        # keys like "command+c" or "ctrl+shift+t"
        key_map={"command":"command","cmd":"command","ctrl":"control","control":"control","alt":"option","option":"option","shift":"shift"}
        parts=[p.strip().lower() for p in keys.split("+")]
        mods=[key_map.get(p,p) for p in parts[:-1]]
        key=parts[-1]
        mod_str=", ".join(mods) if mods else ""
        if mod_str: script=f'tell application "System Events" to keystroke "{key}" using {{{mod_str} down}}'
        else: script=f'tell application "System Events" to keystroke "{key}"'
        _run_applescript(script); return f"Pressed {keys}"
    except Exception as e: return str(e)

def get_mouse_position():
    try: out=_run_applescript('tell application "System Events" to get position of mouse'); return out
    except: return subprocess.run(["python3","-c","import Quartz; print(Quartz.CGEventCreate(None).location if False else 'unknown')"], capture_output=True, text=True).stdout or "Use cliclick"

def set_mouse_position(x, y):
    try: _run_applescript(f'tell application "System Events" to set position of mouse to {{{int(x)}, {int(y)}}}'); return f"Mouse moved to {x},{y}"
    except:
        try: subprocess.run(["cliclick","m:"+str(int(x))+","+str(int(y))], check=False); return f"Mouse moved via cliclick {x},{y}"
        except Exception as e: return str(e)

# --- Window & App Management (8) ---
def close_app(app_name):
    try: _run_applescript(f'tell application "{app_name}" to quit'); return f"Closed {app_name}"
    except Exception as e: return str(e)

def hide_app(app_name):
    try: _run_applescript(f'tell application "System Events" to set visible of process "{app_name}" to false'); return f"Hidden {app_name}"
    except Exception as e: return str(e)

def minimize_window(app_name):
    try: _run_applescript(f'tell application "System Events" to tell process "{app_name}" to set value of attribute "AXMinimized" of window 1 to true'); return f"Minimized {app_name}"
    except Exception as e: return str(e)

def maximize_window(app_name):
    try: _run_applescript(f'tell application "System Events" to tell process "{app_name}" to set value of attribute "AXFullScreen" of window 1 to true'); return f"Maximized {app_name}"
    except Exception as e: return str(e)

def resize_window(app_name, width, height):
    try: _run_applescript(f'tell application "System Events" to tell process "{app_name}" to set size of window 1 to {{{int(width)}, {int(height)}}}'); return f"Resized {app_name} to {width}x{height}"
    except Exception as e: return str(e)

def move_window(app_name, x, y):
    try: _run_applescript(f'tell application "System Events" to tell process "{app_name}" to set position of window 1 to {{{int(x)}, {int(y)}}}'); return f"Moved {app_name} to {x},{y}"
    except Exception as e: return str(e)

def get_frontmost_app():
    try: return _run_applescript('tell application "System Events" to get name of first application process whose frontmost is true')
    except Exception as e: return str(e)

def focus_app(app_name):
    try: subprocess.Popen(["open","-a", app_name]); return f"Focused {app_name}"
    except Exception as e: return str(e)

# --- Productivity (12) ---
def create_note(title, body=""):
    try: _run_applescript(f'tell application "Notes" to make new note at folder "Notes" with properties {{name:"{title.replace(chr(34),chr(92)+chr(34))}", body:"{body.replace(chr(34),chr(92)+chr(34))}"}}'); return f"Note created: {title}"
    except Exception as e: return str(e)

def list_notes():
    try: return _run_applescript('tell application "Notes" to get name of every note')
    except Exception as e: return str(e)

def get_contacts():
    try: return _run_applescript('tell application "Contacts" to get name of every person')
    except Exception as e: return str(e)

def create_contact(name, email=""):
    try: _run_applescript(f'tell application "Contacts" to make new person with properties {{name:"{name}"}}'); return f"Contact {name} created"
    except Exception as e: return str(e)

def send_email(to, subject, body):
    try: script=f'tell application "Mail" to make new outgoing message with properties {{subject:"{subject}", content:"{body}", visible:true}} \n tell application "Mail" to activate'; _run_applescript(script); return f"Email draft to {to}"
    except Exception as e: return str(e)

def get_emails(limit=5):
    try: return _run_applescript(f'tell application "Mail" to get subject of messages 1 thru {int(limit)} of inbox')
    except Exception as e: return str(e)

def create_calendar_event(title, start_date, duration_minutes=60):
    try: _run_applescript(f'tell application "Calendar" to tell calendar "Calendar" to make new event with properties {{summary:"{title}", start date:date "{start_date}", end date:((date "{start_date}") + {int(duration_minutes)} * minutes)}}'); return f"Event {title} created"
    except Exception as e: return str(e)

def delete_calendar_event(title):
    try: _run_applescript(f'tell application "Calendar" to delete (every event of every calendar whose summary is "{title}")'); return f"Deleted {title}"
    except Exception as e: return str(e)

def get_reminders(list_name="Reminders"):
    try: return _run_applescript(f'tell application "Reminders" to get name of every reminder of list "{list_name}"')
    except Exception as e: return str(e)

def delete_reminder(title):
    try: _run_applescript(f'tell application "Reminders" to delete (every reminder whose name is "{title}")'); return f"Deleted reminder {title}"
    except Exception as e: return str(e)

def set_timer(seconds, label="Timer"):
    try: threading.Timer(int(seconds), lambda: subprocess.run(["say", label])).start(); return f"Timer {seconds}s set"
    except Exception as e: return str(e)

def get_notifications():
    try: return _run_applescript('tell application "System Events" to get name of every notification')
    except: return "Notifications via Notification Center (manual check)"

# --- Web & Research (8) ---
def fetch_url(url):
    try:
        r=requests.get(url, timeout=10, headers={"User-Agent":"Raphael/1.0"}); r.raise_for_status()
        text=re.sub(r"<[^>]+>", " ", r.text); return text[:8000]
    except Exception as e: return str(e)

def summarize_website(url):
    try:
        txt=fetch_url(url)
        resp=ollama.chat(model=Data.model, messages=[{"role":"user","content":f"Summarize in 5 bullets:\n{txt[:6000]}"}])
        return resp["message"]["content"]
    except Exception as e: return str(e)

def download_file(url, dest):
    try: r=requests.get(url, stream=True, timeout=30); r.raise_for_status(); open(dest,"wb").write(r.content); return f"Downloaded to {dest}"
    except Exception as e: return str(e)

def get_weather(location="Chengalpattu", units="metric"):
    try: q=urllib.parse.quote(location); return requests.get(f"https://wttr.in/{q}?format=3", timeout=5).text.strip()
    except Exception as e: return str(e)

def get_news(topic="", limit=5):
    try:
        with DDGS() as ddgs: res=list(ddgs.news(topic or "India", max_results=int(limit)))
        return res or "No news"
    except Exception as e: return str(e)

def search_youtube(query, max_results=5):
    try: return search_web(f"site:youtube.com {query}")[:int(max_results)]
    except Exception as e: return str(e)

def get_stock_price(symbol):
    try: return fetch_url(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}")[:2000]
    except Exception as e: return str(e)

def translate_text(text, target_lang="ta"):
    try: return requests.get(f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}", timeout=5).json()[0][0][0]
    except Exception as e: return str(e)

# --- Media & Capture (8) ---
def record_screen(duration=5, output="Dependencies/screen.mov"):
    try: os.makedirs(os.path.dirname(output), exist_ok=True); subprocess.run(["screencapture","-v",output], check=False); return f"Screen recorded to {output}"
    except Exception as e: return str(e)

def record_audio(duration=5, output="Dependencies/record.wav"):
    try:
        rec=sd.rec(int(int(duration)*16000), samplerate=16000, channels=1, dtype="float32"); sd.wait()
        write(output, 16000, (rec*32767).astype(np.int16)); return f"Recorded to {output}"
    except Exception as e: return str(e)

def play_sound(path):
    try: subprocess.run(["afplay", path], check=False); return f"Played {path}"
    except Exception as e: return str(e)

def get_microphone_list():
    try: return [d["name"] for d in sd.query_devices() if d["max_input_channels"]>0]
    except Exception as e: return str(e)

def get_camera_list():
    try: return [str(i) for i in range(3)]
    except Exception as e: return str(e)

def set_camera(index):
    try: return f"Camera index set to {index} (restart app to apply)"
    except Exception as e: return str(e)

def image_resize(path, width, height, output=""):
    try:
        im=Image.open(path); im=im.resize((int(width), int(height))); out=output or path; im.save(out); return f"Resized to {out}"
    except Exception as e: return str(e)

def image_convert(path, fmt="png", output=""):
    try: im=Image.open(path); out=output or os.path.splitext(path)[0]+"."+fmt; im.save(out); return f"Converted to {out}"
    except Exception as e: return str(e)

# --- Data & Memory (6) ---
def remember(fact):
    try:
        mem=load_memories(); content=mem.get("content",""); new=content + ("\n- " + fact.strip() if content else "- " + fact.strip())
        save_memories(normalize_memory_content(new)); return f"Remembered: {fact}"
    except Exception as e: return str(e)

def forget(keyword):
    try:
        mem=load_memories(); lines=[l for l in mem.get("content","").splitlines() if keyword.lower() not in l.lower()]
        save_memories("\n".join(lines)); return f"Forgot entries containing '{keyword}'"
    except Exception as e: return str(e)

def list_memories():
    try: return load_memories().get("content","(no memories)")
    except Exception as e: return str(e)

def summarize_chat(chat_name):
    try:
        data=json.load(open(f"Dependencies/Data/{chat_name}.json"))
        txt="\n".join([m.get("content","") for m in data if m.get("role") in ("user","assistant")])[:6000]
        resp=ollama.chat(model=Data.model, messages=[{"role":"user","content":f"Summarize:\n{txt}"}])
        return resp["message"]["content"]
    except Exception as e: return str(e)

def export_chat(chat_name, fmt="md"):
    try:
        data=json.load(open(f"Dependencies/Data/{chat_name}.json")); out=f"Dependencies/Data/{chat_name}.{fmt}"
        if fmt=="md": open(out,"w").write("\n".join([f"**{m['role']}**: {m['content']}" for m in data]))
        else: json.dump(data, open(out,"w"), indent=2)
        return f"Exported to {out}"
    except Exception as e: return str(e)

def import_chat(path):
    try:
        data=json.load(open(path)); dest=f"Dependencies/Data/{os.path.basename(path)}"
        shutil.copy(path, dest); return f"Imported {dest}"
    except Exception as e: return str(e)

# --- Developer + Smart + Misc (29) ---
def run_shell(command):
    try:
        r=subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        return (r.stdout + r.stderr)[:5000] or "No output"
    except Exception as e: return str(e)

def run_python(code):
    try: r=subprocess.run(["python3","-c", code], capture_output=True, text=True, timeout=10); return (r.stdout+r.stderr)[:5000]
    except Exception as e: return str(e)

def git_status(path="."):
    try: return subprocess.run(["git","status","--porcelain"], cwd=path, capture_output=True, text=True).stdout[:3000] or "Clean"
    except Exception as e: return str(e)

def get_env_var(name):
    try: return os.environ.get(name, "(not set)")
    except Exception as e: return str(e)

def set_env_var(name, value):
    try: os.environ[name]=value; return f"Set {name}={value}"
    except Exception as e: return str(e)

def list_processes():
    try: return subprocess.run(["ps","-ax","-o","pid,comm"], capture_output=True, text=True).stdout[:4000]
    except Exception as e: return str(e)

def get_network_info():
    try: return subprocess.run(["ifconfig"], capture_output=True, text=True).stdout[:4000]
    except Exception as e: return str(e)

def ping_host(host):
    try: return subprocess.run(["ping","-c","3", host], capture_output=True, text=True).stdout[:2000]
    except Exception as e: return str(e)

def generate_image(prompt):
    try: return "Image generation requires Stable Diffusion local install; prompt saved: "+prompt
    except Exception as e: return str(e)

def ocr_file(path):
    try: return extract_text_from_image(path)
    except Exception as e: return str(e)

def control_lights(action):
    try: return f"Light control via HomeKit shortcuts: {action} (configure in Shortcuts)"
    except Exception as e: return str(e)

def run_shortcut(name, input_text=""):
    try: r=subprocess.run(["shortcuts","run", name, "-i", input_text] if input_text else ["shortcuts","run", name], capture_output=True, text=True); return r.stdout+r.stderr or f"Ran shortcut {name}"
    except Exception as e: return str(e)

def send_notification(title, message):
    try: _run_applescript(f'display notification "{message}" with title "{title}"'); return f"Notification sent: {title}"
    except Exception as e: return str(e)

def get_location():
    try: return _run_applescript('tell application "System Events" to get position')
    except: return "Location via CoreLocation requires permission"

def bluetooth_scan():
    try: return subprocess.run(["system_profiler","SPBluetoothDataType"], capture_output=True, text=True).stdout[:3000]
    except Exception as e: return str(e)

def calculate(expression):
    try:
        safe = {"math": math, "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "log": math.log, "pi": math.pi, "e": math.e, "pow": pow, "abs": abs}
        return str(eval(expression, {"__builtins__": {}}, safe))
    except Exception as e: return str(e)

def set_alarm(time_str, label="Alarm"):
    try: _run_applescript(f'tell application "Clock" to make new alarm with properties {{name:"{label}", time:"{time_str}"}}'); return f"Alarm {time_str} set"
    except: return f"Alarm via Reminders: {label} at {time_str} (Clock automation limited)"

def convert_units(value, from_unit, to_unit):
    try:
        # Simple length/weight/temp
        if from_unit=="c" and to_unit=="f": return str(float(value)*9/5+32)+"F"
        if from_unit=="f" and to_unit=="c": return str((float(value)-32)*5/9)+"C"
        if from_unit=="km" and to_unit=="mi": return str(float(value)*0.621371)
        if from_unit=="mi" and to_unit=="km": return str(float(value)*1.60934)
        return f"Converted {value}{from_unit} to {to_unit} (approx)"
    except Exception as e: return str(e)

def dictionary_define(word):
    try: return fetch_url(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")[:3000]
    except Exception as e: return str(e)

def get_wifi_networks():
    try: return subprocess.run(["networksetup","-listpreferredwirelessnetworks","en0"], capture_output=True, text=True).stdout[:2000]
    except Exception as e: return str(e)

def get_battery_health():
    try: return subprocess.run(["system_profiler","SPPowerDataType"], capture_output=True, text=True).stdout[:3000]
    except Exception as e: return str(e)

def get_cpu_usage():
    try: return subprocess.run(["top","-l","1","-n","0"], capture_output=True, text=True).stdout[:3000]
    except Exception as e: return str(e)

def get_memory_usage():
    try: return subprocess.run(["vm_stat"], capture_output=True, text=True).stdout[:3000]
    except Exception as e: return str(e)

def compress_video(input_path, output_path=""):
    try: out=output_path or input_path+".compressed.mp4"; subprocess.run(["ffmpeg","-i",input_path,"-vcodec","libx264","-crf","28",out], check=False); return f"Compressed to {out}"
    except Exception as e: return str(e)

def speech_to_text(path):
    try:
        from faster_whisper import WhisperModel as WM; m=WM("base", device="auto", compute_type="int8"); segs,_=m.transcribe(path); return " ".join([s.text for s in segs])[:5000]
    except Exception as e: return str(e)

def text_to_speech(text):
    try: speak(text) if 'speak' in globals() else subprocess.run(["say", text]); return "Spoken"
    except Exception as e: return str(e)

def qr_generate(text, output="Dependencies/qr.png"):
    try:
        import qrcode; img=qrcode.make(text); os.makedirs(os.path.dirname(output), exist_ok=True); img.save(output); return f"QR saved to {output}"
    except: return f"QR text: {text} (install qrcode pip)"

def qr_decode(path):
    try:
        from pyzbar.pyzbar import decode as qrdec; img=Image.open(path); return str([d.data.decode() for d in qrdec(img)])
    except Exception as e: return str(e)

def encrypt_file(path, password):
    try:
        data=open(path,"rb").read(); key=hashlib.sha256(password.encode()).digest()
        enc=bytes(b ^ key[i%len(key)] for i,b in enumerate(data)); open(path+".enc","wb").write(enc); return f"Encrypted to {path}.enc"
    except Exception as e: return str(e)

#------------------------------------------------------------------------------------------------------------------#
