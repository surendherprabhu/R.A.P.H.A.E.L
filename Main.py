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


from methods import *
from Data import *
from Vision import Vision


#------------------------------------------------------------------------------------------------------------------#

def speak(text):
    process = subprocess.Popen(
        [
            "piper",
            "--model",
            voice_model,
            "--output_file",
            speech_location
        ],
        stdin=subprocess.PIPE,
        text=True
    )
    process.communicate(text)

    subprocess.run(
        ["afplay", speech_location]
    )

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
            with open("Dependencies/Memories/Memories.json", "r") as file:
                self.memory = json.load(file)
        except:
            self.memory = ""

        memories_message =  {
                "role": "system",
                "content": f"Your memories:{self.memory}"
            }

        self.conversation.append(memories_message)
        self.vision = Vision()
        self.tools = {
    "get_time": get_time,
    "search_web": search_web,
    "get_date": get_date,
    "get_battery": get_battery,
    "open_app": open_app,
    "list_directory": list_directory,
    "write_file": write_file,
    "read_file": read_file,
    "analyze_camera": self.analyze_camera,
}

        if start_ollama_background():
            self.connection_status = "Online 🌐"
            self.create_window()
            self.vision.start_camera()
            self.update_camera()
            self.root.mainloop()

    def process_voice(self):
        self.voice_segments, self.voice_info = self.whisper_model.transcribe("Dependencies/voice.wav")

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

        write("Dependencies/voice.wav" , 16000 , audio)
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

        self.root.protocol("WM_DELETE_WINDOW",self.close_program)

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

        #vison
        self.create_vision_overlay()

        #input box 
        self.input_box = ctk.CTkTextbox(self.root)
        self.input_box.place(relx = 0.549, rely = 0.83 , anchor = "center" , relwidth = 0.65 , relheight = 0.085  )
        self.input_box.bind( "<Return>",self.send_message_event)
        #send button
        self.send_button = ctk.CTkButton(self.root, text = "Send",command = self.program_cycle)
        self.send_button.place(relx = 0.925 , rely = 0.83 , anchor ="center" ,relheight = 0.085 , relwidth = 0.085)

        self.root.bind("<KeyPress-Alt_L>", self.start_recording)
        self.root.bind("<KeyRelease-Alt_L>", self.stop_recording)

        self.root.bind_all("<Control-v>", self.toggle_vision)

    def create_vision_overlay(self):
         #vision frame
        self.vision_frame = ctk.CTkFrame(self.root)
        self.vision_frame.place(relx = 0.6 , rely = 0.45 , anchor = "center", relwidth = 0.75 , relheight= 0.65)
        self.vision_frame.place_forget()

        self.camera_label = ctk.CTkLabel(self.vision_frame, text = "")
        self.camera_label.pack(fill = "both", expand = True)

    def update_camera(self):
        frame = self.vision.get_frame()

        if frame is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            image = Image.fromarray(frame)

            image.thumbnail(
                (
                    self.vision_frame.winfo_width(),
                    self.vision_frame.winfo_height()
                ),
                Image.Resampling.LANCZOS
            )

            photo = ImageTk.PhotoImage(image)

            self.camera_label.configure(image=photo, text="")
            self.camera_label.image = photo

        self.root.after(30, self.update_camera)

    def analyze_camera(self, prompt):
        print("Camera tool called!")
        filename = "Dependencies/camera.jpg"

        success = self.vision.capture_image(filename)

        if not success:
            return "Unable to return an image from the camera."

        response: ollama.ChatResponse = ollama.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [filename]
            }
        ]
    )

        return response["message"]["content"]   
        
    def close_program(self):

        self.vision.stop_camera()

        self.root.destroy()

    def toggle_vision(self, event=None):
        print("Mapped:", self.vision_frame.winfo_ismapped())

        if self.vision_frame.winfo_ismapped():
            print("Hiding")
            self.vision_frame.place_forget()
            self.chat_box.lift()
            print(self.vision_frame.winfo_ismapped())
        else:
            print("Showing")
            self.vision_frame.place(
                relx=0.6,
                rely=0.45,
                anchor="center",
                relwidth=0.75,
                relheight=0.65
            )
            self.vision_frame.lift()

    def chat_select(self,selected_chat):
        with open(f"Dependencies/Data/{selected_chat}.json") as file:
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
},
{
    "type": "function",
    "function": {
        "name": "analyze_camera",
        "description": "Capture an image from the webcam and answer a question about it.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The user's question about the camera image."
                }
            },
            "required": ["prompt"]
        }
    }
}


                ]
        MAX_TOOL_ITERATIONS = 10

        for _ in range(MAX_TOOL_ITERATIONS):
            response = ollama.chat(
            model=model,
            messages=Convo,
            tools=tools)

            assistant_message = response["message"]
            Convo.append(assistant_message)

            tool_calls = assistant_message.get("tool_calls")

            if not tool_calls:
                reply = clean_response(
                    assistant_message["content"]
                )

                Convo.append({

                    "role": "assistant",

                    "content": reply

                })

                return reply

            for tool_call in tool_calls:

                function_name = tool_call["function"]["name"]

                arguments = tool_call["function"].get(

                    "arguments",

                    {}

                )

                try:

                    result = self.tools[function_name](

                        **arguments

                    )

                except Exception as e:

                    result = f"Tool Error: {e}"

                Convo.append({

                    "role": "tool",
                    "content": str(result)

                })

        return "Maximum tool iterations reached."

    def generate_response_thread(self):
        reply = self.Generate_Response(self.conversation)

        self.root.after(
        0,
        lambda: self.finish_response(reply)
                        )

    def finish_response(self, reply):
        self.add_message(reply, application_name)


        threading.Thread(

        target=speak,

        args=(reply,),

        daemon=True).start()

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
        with open(f"Dependencies/Data/{filename}" , "w") as f:
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
            with open("Dependencies/Memories/Memories.json") as file:
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
        with open("Dependencies/Memories/Memories.json", "w") as file:
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
