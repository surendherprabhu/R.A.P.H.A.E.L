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

#------------------------------------------------------------------------------------------------------------------#
