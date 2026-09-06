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
import multiprocessing
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
from settings import Settings


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
        self.camera_ready = False
        self.whisper_model = None

        self.settings = Settings()

        # Robust memory load (handles legacy string & new dict format)
        self._memory_data = load_memories()
        self.memory = self._memory_data.get("content", "")

        self._inject_memory()
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
    "create_directory": create_directory,
    "get_system_info": get_system_info,
    "open_website": open_website,
    "read_clipboard": read_clipboard,
    "write_clipboard": write_clipboard,
    "list_running_apps": list_running_apps,
    "get_calendar_events": get_calendar_events,
    "create_reminder": create_reminder,
    "take_screenshot": take_screenshot,
    "extract_text_from_image": extract_text_from_image,
    "media_control": media_control,
    "volume_control": volume_control,
    "analyze_camera": self.analyze_camera,
}

        self.create_window()

        if start_ollama_background():
            self.connection_status = "Online 🌐"
        else:
            self.connection_status = "Offline 💤"

        self.connection_label.configure(text=self.connection_status)

        self.camera_ready = self.vision.start_camera()
        if not self.camera_ready:
            print("Camera unavailable. Starting without vision.")

        self.update_camera()
        self.root.mainloop()

    def process_voice(self):
        if self.whisper_model is None:
            self.whisper_model = WhisperModel(
                "base",
                device="auto",
                compute_type="int8"
            )

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
        ttk.Separator(self.root, orient="vertical").place(relx=0.2, rely=0.09, relheight=0.81, relwidth=0.001)
        ttk.Separator(self.root, orient="horizontal").place(relx=0, rely=0.09, relheight=0.001, relwidth=1)
        ttk.Separator(self.root, orient="horizontal").place(relx=0, rely=0.9, relheight=0.001, relwidth=1)

        #LOGO
        ctk.CTkLabel(self.root,text=application_name).place(relx = 0.1,rely =0.04,anchor = "center",relwidth = 0.15,relheight=0.1)
         
        #Connection Status
        self.connection_label = ctk.CTkLabel(self.root, text=self.connection_status)
        self.connection_label.place(relx = 0.90,rely =0.04,anchor="center")

        #settings button
        ctk.CTkButton(
            self.root,
            text="Settings",
            command=lambda: self.settings.create_window(self.root, self.update_model_label)
        ).place(relx=0.1,rely=0.95,anchor="center",relwidth = 0.14,)

        #Model name at bottom
        self.model_label = ctk.CTkLabel(self.root, text=f"Model: {model}")
        self.model_label.place(relx=0.88,rely=0.95,anchor="center")

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
        if not self.vision.is_running():
            return "Camera is unavailable right now."
        filename = "Dependencies/camera.jpg"

        success = self.vision.capture_image(filename)

        if not success:
            return "Unable to return an image from the camera."

        response: ollama.ChatResponse = ollama.chat(
        model=self.settings.model,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [filename]
            }
        ]
    )

        return response["message"]["content"]   
        
    def update_model_label(self, selected_model):
        self.model_label.configure(text=f"Model: {selected_model}")

    # ---------------- Memory & Context Helpers ----------------
    def _load_memory_text(self):
        data = load_memories()
        self._memory_data = data
        self.memory = data.get("content", "")
        return self.memory

    def _inject_memory(self):
        """Ensure conversation has exactly one memory system message after the personality prompt."""
        mem_text = self.memory or ""
        content = f"Your memories:\n{mem_text}" if mem_text.strip() else "Your memories: (no prior memories yet)"
        mem_msg = {"role": "system", "content": content}
        # Conversation[0] is personality system prompt; memory should be at index 1
        if len(self.conversation) >= 1 and self.conversation[0].get("role") == "system":
            if len(self.conversation) >= 2 and "Your memories" in self.conversation[1].get("content", ""):
                self.conversation[1] = mem_msg
            else:
                self.conversation.insert(1, mem_msg)
        else:
            self.conversation.insert(0, mem_msg)

    def _refresh_memory_in_conversation(self):
        self._load_memory_text()
        self._inject_memory()

    def _get_pruned_context(self, max_messages=30):
        return build_llm_context(self.conversation, max_messages=max_messages, keep_system_count=2)

    def _render_conversation_to_ui(self):
        """Repopulate chat_box from conversation (user/assistant only)."""
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        for msg in self.conversation:
            role = msg.get("role", "")
            if role == "user":
                self.chat_box.insert("end", f"You:\n{msg.get('content','')}\n\n")
            elif role == "assistant":
                # Skip empty tool-call placeholder messages
                content = msg.get("content", "")
                if content and content.strip():
                    self.chat_box.insert("end", f"{application_name}:\n{content}\n\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

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
        json_file = f"Dependencies/Data/{selected_chat}.json"
        legacy_file = f"Dependencies/Data/{selected_chat}"
        chat_file = json_file if os.path.exists(json_file) else legacy_file

        # Save current before switching (avoid saving empty)
        try:
            if len(self.conversation) > 2:
                self.save_chat()
        except Exception as e:
            print(f"Auto-save before chat switch failed: {e}")

        try:
            with open(chat_file, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception as e:
            print(f"Failed to load chat {selected_chat}: {e}")
            return

        self.conversation = data if isinstance(data, list) else copy.deepcopy(Conversation)
        # Refresh memory to current version, not stale saved one
        self._refresh_memory_in_conversation()
        self._render_conversation_to_ui()   
  
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
        "name": "create_directory",
        "description": "Create a directory if it does not exist",
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
        "name": "get_system_info",
        "description": "Return macOS and Python runtime information",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "open_website",
        "description": "Open a website in the default browser",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string"
                }
            },
            "required": ["url"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "read_clipboard",
        "description": "Read text from the system clipboard",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "write_clipboard",
        "description": "Write text into the system clipboard",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string"
                }
            },
            "required": ["text"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "list_running_apps",
        "description": "List currently running foreground applications",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_calendar_events",
        "description": "Get upcoming calendar events in the next number of hours",
        "parameters": {
            "type": "object",
            "properties": {
                "hours_ahead": {
                    "type": "integer"
                },
                "max_events": {
                    "type": "integer"
                }
            }
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "create_reminder",
        "description": "Create a reminder in the Reminders app",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string"
                },
                "list_name": {
                    "type": "string"
                },
                "due_date": {
                    "type": "string",
                    "description": "Natural date string accepted by AppleScript, for example 'Friday at 5:00 PM'."
                }
            },
            "required": ["title"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "take_screenshot",
        "description": "Capture a screenshot. Use mode full, window, or selection.",
        "parameters": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string"
                },
                "filename": {
                    "type": "string"
                }
            }
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "extract_text_from_image",
        "description": "Extract visible text from an image file",
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
        "name": "media_control",
        "description": "Control media playback in Spotify or Music",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "play, pause, play_pause, next, previous"
                }
            },
            "required": ["action"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "volume_control",
        "description": "Get or control system volume",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "get, set, up, down, mute, unmute"
                },
                "level": {
                    "type": "integer",
                    "description": "Used when action is set, range 0 to 100"
                }
            }
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
            # Use pruned context for LLM to avoid unbounded growth, but persist full Convo
            pruned = build_llm_context(Convo, max_messages=30, keep_system_count=2)
            response = ollama.chat(
            model=self.settings.model,
            messages=pruned,
            tools=tools)

            assistant_message = response["message"]
            # Persist the raw assistant message (with tool_calls) to full history
            Convo.append(assistant_message)

            tool_calls = assistant_message.get("tool_calls")

            if not tool_calls:
                raw = assistant_message.get("content") or ""
                reply = clean_response(raw)
                # Replace the just-appended message's content with cleaned version to avoid duplicate
                if reply != raw:
                    Convo[-1] = {"role": "assistant", "content": reply}
                # If raw was empty or already clean, keep as is but ensure content is cleaned
                elif not Convo[-1].get("content"):
                    Convo[-1]["content"] = reply
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
        # Save current first if non-trivial
        try:
            if len(self.conversation) > 2:
                self.save_chat()
        except Exception as e:
            print(f"Auto-save before new chat failed: {e}")
        self.conversation = copy.deepcopy(Conversation)
        self._load_memory_text()
        self._inject_memory()
        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.configure(state="disabled")
    
    def save_chat(self):
        if len(self.conversation) <= 1:
            return

        os.makedirs("Dependencies/Data", exist_ok=True)

        for existing in ListFiles():
            try:
                with open(f"Dependencies/Data/{existing}.json") as file:
                    if json.load(file) == self.conversation:
                        return
            except (FileNotFoundError, json.JSONDecodeError):
                continue

        # Use pruned context for title generation to avoid tool bloat
        convo_copy = build_llm_context(self.conversation, max_messages=12, keep_system_count=1)
        # Strip tool messages for cleaner title
        convo_copy = [m for m in convo_copy if m.get("role") in ("system", "user", "assistant")]
        convo_copy.append({
            "role" : "user",
            "content": "Summarize this conversation in 3 words for a filename. Return only the 3 words, no punctuation."
        })

        try:
            filename_total = ollama.chat(
                model = self.settings.model,
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
        except Exception as e:
            print(f"Summary failed, using default name: {e}")
            filename = time.strftime("Chat %d-%m-%Y %H-%M")

        file = f"Dependencies/Data/{filename}.json"
        with open(file , "w") as f:
            json.dump(self.conversation, f, indent=4)

        try:
            self.add_memories()
        except Exception as e:
            print(f"Memory update failed: {e}")

        self.root.after(
            0,
            lambda: self.Chat_selection.configure(values=ListFiles())
        )

    def send_message_event(self, event):
        if event.state & 0x1:  # Shift key
            return
        self.program_cycle()
        return "break"
 
    def add_memories(self):
        # Load current memories safely (handles legacy string & dict)
        mem_data = load_memories()
        existing = mem_data.get("content", "")

        # Build a focused conversation slice for memory extraction (avoid system/tool bloat)
        temp = build_llm_context(self.conversation, max_messages=20, keep_system_count=1)
        # Keep only user/assistant turns for memory relevance
        filtered = [m for m in temp if m.get("role") in ("user", "assistant") and m.get("content", "").strip()]
        # Always include memory context as system
        memory_system = {
            "role": "system",
            "content": (
                "You are a memory curator for R.A.P.H.A.E.L.\n"
                f"Current memories:\n{existing if existing.strip() else '(none)'}\n\n"
                "Task: Review the recent conversation and update the memory list.\n"
                "Rules:\n"
                "- Keep only factual, long-term useful information (user preferences, goals, facts, important events)\n"
                "- Do not infer or hallucinate. Do not duplicate existing memories.\n"
                "- If the user explicitly asked to remember something, include it.\n"
                "- Return ONLY a bullet list (one fact per line starting with '- ').\n"
                "- Keep bullets concise, max 15.\n"
                "- If nothing new to remember, return the existing memories unchanged.\n"
                "- Merge with existing memories, remove outdated contradictions, deduplicate."
            ),
        }
        prompt = filtered + [memory_system]

        reply = ollama.chat(
            model=self.settings.model,
            messages=prompt
        )

        raw_memory = (reply["message"]["content"] or "").strip()
        # Clean and normalize (deduplicate, strip wrappers)
        cleaned = normalize_memory_content(raw_memory)
        if not cleaned:
            cleaned = existing.strip()

        # If LLM echoed existing verbatim without bullets, preserve existing
        if cleaned.lower().startswith("here are") and existing:
            # Prefer existing if new is just preamble
            cleaned = existing.strip()

        payload = save_memories(cleaned)
        # Immediately refresh runtime memory so next turns see it
        self._memory_data = payload
        self.memory = payload.get("content", "")
        # Update the injected memory message in current conversation
        try:
            self._inject_memory()
        except Exception as e:
            print(f"Memory injection refresh failed: {e}")

    def save_thread(self):
        self.save_chat()

    def save_activation(self):
        threading.Thread(target=self.save_thread,daemon=True).start()
#------------------------------------------------------------------------------------------------------------------#

#------------------------------------------------------------------------------------------------------------------#
# Initialization
if __name__ == "__main__":
    multiprocessing.freeze_support()
    raphael = Raphael()
#------------------------------------------------------------------------------------------------------------------#
