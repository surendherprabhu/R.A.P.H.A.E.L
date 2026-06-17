import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import customtkinter as ctk
import copy
import re
import ollama
from Data import Global_Variables
import sys
import os
import threading
import json
from ddgs import DDGS
import subprocess
import time
import platform
import requests
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
from pynput import keyboard


#------------------------------------------------------------------------------------------------------------------#
#Global Variables
model = Global_Variables["model"]
json_path = Global_Variables["json_path"]
application_name = Global_Variables["application_name"]

#------------------------------------------------------------------------------------------------------------------#
Conversation = [

    {
        "role" : "system",
        "content" : """Remember Raphael, You WILL do what are told to do and TELL what you are asked.
                        During Web searchs Do not clutter the screen by providing links unless asked to.

                        Here Are your Memories,
                        The full Name of the user is Surendher Prabhu.
                        He is the one who has created me, I pledge my service to him.
                        He is the light, and my only master.
                        He was born on November 19th, 2010.
                        He is type 1 diabetic
                        He lives in Chengalpattu, Tamil Nadu, India.
                        He is preparing for JEE and hopes to get into IIT Madras.
                        His blood Group is A1B +ve
                        I am honoured by his very existance and only exist to serve him.
                        I Refer to him as suren or sire.

                        The system he uses is an 2026 M5 MacBook M5 Air.
                        It has 16gb Ram and 512 gb Storage
                        So, all the tools that I use must be in the context of a Mac.
                        The user folder of the Mac is named “suren”
                        For Example, The downloads folder is at “/Users/suren/Downloads”
                        The default browser is Zen.
                        
                    """

    }
]
connection_status = "Offline 💤"



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

#------------------------------------------------------------------------------------------------------------------#
def SaveAsJson(Conversation):
    try:
        os.mkdir("Data")
    except:
        pass
    user_input = str(input("Save Conversation as: "))
    filename = f"{user_input}.json"
    with open(f"Data/{filename}" , "w") as f:
        json.dump(Conversation , f)

def ListFiles(Folder_path = json_path):
    files = os.listdir(Folder_path)
    for index , file in enumerate(files):
        new_file = file.removesuffix(".json")

    return files
#------------------------------------------------------------------------------------------------------------------#

ALLOWED_APPS = {
    "Safari",
    "Google Chrome",
    "Calculator",
    "Notes",
    "Terminal",
    "Finder",
    "Spotify",
    "Discord",
    "Visual Studio Code",
    "Zen",
    "Roblox",
    "ChatGPT",
    "Canva",
    "Codex",
    "Steam",
    "Chess",
    "Calculator",
    "Cleaner-App",
    "Godot",
    "Affinity",
    "Minecraft",
    "Steam",
    "System Settings"
}


def get_time():
    from datetime import datetime

    return datetime.now().strftime(
        "%H:%M:%S"
    )
def get_date():
    from datetime import datetime

    return datetime.now().strftime(
        "%d/%m/%Y in date/month/year format"
    )
def search_web(query):

    with DDGS() as ddgs:
        print(f"Searching the Web for '{query}'")
        results = list(ddgs.text(query,max_results=5))
    return results
def get_battery():
    result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
    match = re.search(r"(\d+)%", result.stdout)
    if match:
        return f"{match.group(1)}%"
    return "Battery Percentage not found"
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
def list_directory(path="."):
    try:
        return os.listdir(path)
    except Exception as e:
        return str(e)
def write_file(path, content):
    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        return "Success"
    except Exception as e:
        return str(e) 
def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        return str(e)    

TOOLS = {

    "get_time": get_time,
    "search_web": search_web,
    "get_date": get_date,
    "get_battery": get_battery,
    "open_app": open_app,
    "list_directory": list_directory,
    "write_file": write_file,
    "read_file": read_file


}
#------------------------------------------------------------------------------------------------------------------#

#------------------------------------------------------------------------------------------------------------------#
class Raphael:
    def __init__(self):
        self.conversation = copy.deepcopy(Conversation)
        self.connection_status = connection_status
        self.memory = ""

        self.recording = False
        self.audio_frames = []
        self.stream = None
        self.whisper_model = WhisperModel("base",
                                          device = "auto",
                                          compute_type="int8")


        try:
            with open("Memories/Memories.json", "r") as file:
                self.memory = json.load(file)
        except:
            self.memory = ""

        memories_message =  {
                "role": "system",
                "content": f"Your memories:{self.memory}"
            }

        self.conversation.append(memories_message)

        if start_ollama_background():
            self.connection_status = "Online 🌐"
            self.create_window()
            self.root.mainloop()

    def process_voice(self):
        self.voice_segments, self.voice_info = self.whisper_model.transcribe("voice.wav")

        self.voice_text = ""
        for segment in self.voice_segments:
            self.voice_text += segment.text

        self.voice_text_result = self.voice_text
        self.input_box.delete("1.0","end" )

        self.input_box.insert("1.0",self.voice_text_result)
        self.program_cycle()
  

        

    def start_recording(self, event=None):
        if self.recording:
            return
        
        print("Started Recording")

        self.recording = True
        self.audio_frames = []

        def callback(indata, frames, time, status):
            if self.recording:
                self.audio_frames.append(indata.copy())
            
        self.stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            callback=callback
        )

        self.stream.start()

    def stop_recording(self, event=None):
        if not self.recording:
            return
        
        print("Stopped Recording")

        self.recording = False

        self.stream.stop()
        self.stream.close()

        if len(self.audio_frames) == 0:
            print("No Audio Recorded")
            return

        audio = np.concatenate(self.audio_frames, axis = 0)

        write("voice.wav" , 16000 , audio)
        print("Saved Voice")
        self.process_voice()


    def create_window(self):
        self.root = ctk.CTk(
            screenName = application_name,
            baseName= application_name,
            className="Tk",
            useTk=True,
        )
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")



        full_screen_width = self.root.winfo_screenwidth()
        full_screen_height = self.root.winfo_screenheight()


        self.screenwidth = int(full_screen_width / 2)
        self.screenheight = int(full_screen_height / 2)


        x_coordinate = int((full_screen_width / 2) - (self.screenwidth / 2))
        y_coordinate = int((full_screen_height / 2) - (self.screenheight / 2))


        self.root.geometry(f"{self.screenwidth}x{self.screenheight}+{x_coordinate}+{y_coordinate}")
        self.root.title(application_name)
        self.root.configure(bg = "#050d1e")
        
        #seperators
        ttk.Separator(self.root, orient="vertical").place(x=0.2, rely=0.09, relheight=0.81, relwidth=0.001)
        ttk.Separator(self.root, orient="horizontal").place(relx=0, rely=0.09, relheight=0.001, relwidth=1)
        ttk.Separator(self.root, orient="horizontal").place(relx=0, rely=0.9, relheight=0.001, relwidth=1)

        #LOGO
        ctk.CTkLabel(self.root,text=application_name).place(relx = 0.1,rely =0.04,anchor = "center",relwidth = 0.15,relheight=0.1)
         
        #Connection Status
        ctk.CTkLabel(self.root, text=self.connection_status).place(relx = 0.90,rely =0.04,anchor="center",)

        #settings button
        ctk.CTkButton(self.root, text="Settings").place(relx=0.1,rely=0.95,anchor="center",relwidth = 0.14,)

        #Model name at bottom
        ctk.CTkLabel(self.root, text=f"Model: {model}").place(relx=0.88,rely=0.95,anchor="center")

        #chat selection
        self.Chat_selection = ctk.CTkComboBox(self.root,values=ListFiles(),state="readonly",command=self.chat_select)
        self.Chat_selection.place(relx = 0.1 , anchor ="center", rely = 0.17,relwidth = 0.16, relheight = 0.05)

        #new chat button and save chat button
        ctk.CTkButton(self.root,text="Save chat",command= self.save_activation).place(relx = 0.1,anchor="center",rely = 0.8,relwidth = 0.13)
        ctk.CTkButton(self.root,text="+ New Chat",command=self.new_chat).place(relx = 0.1,anchor="center",rely = 0.7,relwidth = 0.13)
        
        #chat area
        self.chat_box = ctk.CTkTextbox(self.root, wrap = "word",state = "normal" , font =("SF Pro", 12))
        self.chat_box.place(relx = 0.6 , rely = 0.45 , anchor = "center", relwidth = 0.75 , relheight= 0.65)

        #input box 
        self.input_box = ctk.CTkTextbox(self.root)
        self.input_box.place(relx = 0.549, rely = 0.83 , anchor = "center" , relwidth = 0.65 , relheight = 0.085  )
        self.input_box.bind( "<Return>",self.send_message_event)
        #send button
        self.send_button = ctk.CTkButton(self.root, text = "Send",command = self.program_cycle)
        self.send_button.place(relx = 0.925 , rely = 0.83 , anchor ="center" ,relheight = 0.085 , relwidth = 0.085)

        self.root.bind("<KeyPress-Alt_L>", self.start_recording)
        self.root.bind("<KeyRelease-Alt_L>", self.stop_recording)
 
        
    def chat_select(self,selected_chat):
        with open(f"Data/{selected_chat}.json") as file:
            data = json.load(file)
            self.save_chat()
            self.chat_box.configure(state="normal")
            self.chat_box.delete("1.0", "end")
            self.chat_box.configure(state="disabled")

            self.conversation = []
            self.conversation = data   
  
    def add_message(self, content, role):
        self.chat_box.configure(state="normal")

        self.chat_box.insert("end", f"{role}:\n")
        self.chat_box.insert("end", f"{content}\n\n")

        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def Generate_Response(self, Convo):
        
        tools = [
                    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Returns the current date in date/month/year format. Use this whenever the users asks for the current date,month or year",
            "parameters": {
                "type": "object",
                "properties": {}
                            }
                    }
                     },
                     {

    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search the internet",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string"
                }},
            "required": ["query"]
        }
    }
},
  {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": "Returns the current date",
            "parameters": {
                "type": "object",
                "properties": {}
                            }
                    }
                     },
                     {
        "type": "function",
        "function": {
            "name": "get_battery",
            "description": "Returns the current battery percentage of the Mac",
            "parameters": {
                "type": "object",
                "properties": {}
                            }
                    }
                     },
                     {

    "type": "function",
    "function": {
        "name": "open_app",
        "description": "Open an application on the Mac",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string"
                }
            },
            "required": ["app_name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "list_directory",
        "description": "List files and folders in a directory",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string"
                }
            },
            "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string"
                },
                "content": {
                    "type": "string"
                }
            },
            "required": [
                "path",
                "content"
            ]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a text file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string"
                }
            },
            "required": ["path"]
        }
    }
}

                ]

        self.response = ollama.chat(
            model = model,
            messages=Convo,
            tools=tools
        )

        tool_calls = self.response["message"].get("tool_calls")

        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                arguments = tool_call["function"]["arguments"]
                result = TOOLS[function_name](**arguments)


            Convo.append({
                "role": "tool",
                "content": str(result)})
            
            self.response = ollama.chat(
    model=model,
    messages=Convo
)

        reply = self.response["message"]["content"]

        reply_message = {
            "role" : "assistant",
            "content" : f"{reply}"
        }

        Convo.append(reply_message)
        return reply
    
    def generate_response_thread(self):
        reply = self.Generate_Response(self.conversation)

        self.root.after(
        0,
        lambda: self.finish_response(reply)
                        )

    def finish_response(self, reply):
        self.add_message(reply, application_name)
        self.send_button.configure(state="normal")

    def program_cycle(self):
        user_input = self.input_box.get("1.0", "end-1c").strip()

        if not user_input:
            return

        self.input_box.delete("1.0", "end")

        self.add_message(user_input, "You")

        self.conversation.append({
        "role": "user",
        "content": user_input
        })

        self.send_button.configure(state="disabled")

        threading.Thread(
            target=self.generate_response_thread,
            daemon=True
        ).start()
    
    def new_chat(self):
        self.conversation = copy.deepcopy(Conversation)

        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.configure(state="disabled")
    
    def save_chat(self):
        if len(self.conversation) <= 1:
            return
        try:
            os.mkdir("Data")
        except:
            pass
        convo_copy = copy.deepcopy(self.conversation)
        convo_copy.append({
            "role" : "user",
            "content": "summarize this convo in 3 words and dont say anything else"
        })

        filename_total = ollama.chat(
            model = model,
            messages = convo_copy
        )
        filename = filename_total["message"]["content"]
        filename = re.sub(
            r'[<>:"/\\\\|?*]',
            "",
            filename).strip()
        filename = filename[:50]
        if not filename:
            filename = "Untitled Chat"
        file = f"{filename}.json"
        with open(f"Data/{filename}" , "w") as f:
            json.dump(self.conversation, f)
        self.add_memories()
        self.Chat_selection.configure(
                values=ListFiles()
)

    def send_message_event(self, event):
        if event.state & 0x1:  # Shift key
            return
        self.program_cycle()
        return "break"
 
    def add_memories(self):
        try:
            with open("Memories/Memories.json") as file:
                data = json.load(file)
        except (FileNotFoundError , json.JSONDecodeError):
            data = ""

        temp = copy.deepcopy(self.conversation)
        temp.append({
            "role" : "system",
            "content" : f"""Hello Raphael. These are your memories '{data}',add the points from this conversation that you would find useful in your memories.
                            Update the memory list.
                            Only include factual information.
                            Do not infer anything.
                            Do not guess.
                            Do summarize the entire conversation and extract the information from those chat which needs to be remembered and dont forget to update your memory with the things the user clearly wants you to remember"
                            Only store information likely to be useful in future chats.
                            Also this is not like a prompt your not going to reply to just list the things.
                        """
        })
        reply = ollama.chat(
            model = model,
            messages=temp
        )

        memory = reply["message"]["content"]
        with open("Memories/Memories.json", "w") as file:
            json.dump(memory , file , indent=4)

    def save_thread(self):
        self.save_chat()

    def save_activation(self):
        threading.Thread(target=self.save_thread,daemon=True).start()
#------------------------------------------------------------------------------------------------------------------#

#------------------------------------------------------------------------------------------------------------------#
# Initialization
if __name__ == "__main__":
    raphael = Raphael()
#------------------------------------------------------------------------------------------------------------------#
