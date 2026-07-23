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
    files = os.listdir(Folder_path)
    for index , file in enumerate(files):
        new_file = file.removesuffix(".json")

    return files

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