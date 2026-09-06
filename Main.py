import tkinter as tk
from tkinter import ttk, messagebox
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

_speech_process = None
_speech_lock = threading.Lock()

def stop_speech():
    """Interrupt current TTS playback (piper/afplay/say)."""
    global _speech_process
    with _speech_lock:
        proc = _speech_process
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception:
                pass
        _speech_process = None
    # Fallback: kill any lingering afplay/say for safety
    for pat in ["afplay", "say"]:
        try:
            subprocess.run(["pkill", "-f", pat], timeout=1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def speak(text):
    global _speech_process
    text = (text or "").strip()
    if not text:
        return
    # Ensure output dir exists
    try:
        os.makedirs(os.path.dirname(speech_location) or ".", exist_ok=True)
    except Exception:
        pass

    # Prefer piper if model exists, else fallback to macOS 'say'
    use_piper = os.path.exists(voice_model) and os.path.exists(voice_model + ".json")
    # Also check piper binary available
    try:
        import shutil
        if shutil.which("piper") is None:
            use_piper = False
    except Exception:
        pass

    if use_piper:
        try:
            proc = subprocess.Popen(
                [
                    "piper",
                    "--model",
                    voice_model,
                    "--output_file",
                    speech_location,
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            out, err = proc.communicate(text, timeout=30)
            if proc.returncode != 0:
                print(f"Piper failed ({proc.returncode}): {err.strip()[:300]}")
                raise RuntimeError(err)
            if not os.path.exists(speech_location) or os.path.getsize(speech_location) < 1000:
                print("Piper produced no audio, falling back to say")
                raise RuntimeError("empty wav")
            # Play with boosted volume (afplay -v 2 is louder) - interruptible
            with _speech_lock:
                _speech_process = subprocess.Popen(["afplay", "-v", "2", speech_location])
                p = _speech_process
            p.wait()
            with _speech_lock:
                if _speech_process is p:
                    _speech_process = None
            return
        except Exception as e:
            print(f"TTS piper path failed: {e}")

    # Fallback: macOS native speech synthesis (always available) - interruptible
    try:
        with _speech_lock:
            _speech_process = subprocess.Popen(["say", "-r", "180", text])
            p = _speech_process
        p.wait()
        with _speech_lock:
            if _speech_process is p:
                _speech_process = None
    except Exception as e:
        print(f"Fallback say failed: {e}")
        try:
            with _speech_lock:
                _speech_process = subprocess.Popen(["afplay", speech_location])
                p = _speech_process
            p.wait()
            with _speech_lock:
                if _speech_process is p:
                    _speech_process = None
        except Exception:
            pass

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
    "get_time": get_time,"search_web": search_web,"get_date": get_date,"get_battery": get_battery,"open_app": open_app,"list_directory": list_directory,"write_file": write_file,"read_file": read_file,"create_directory": create_directory,"get_system_info": get_system_info,"open_website": open_website,"read_clipboard": read_clipboard,"write_clipboard": write_clipboard,"list_running_apps": list_running_apps,"get_calendar_events": get_calendar_events,"create_reminder": create_reminder,"take_screenshot": take_screenshot,"extract_text_from_image": extract_text_from_image,"media_control": media_control,"volume_control": volume_control,"analyze_camera": self.analyze_camera,
    # 100 new
    "delete_file": delete_file,"move_file": move_file,"copy_file": copy_file,"file_stats": file_stats,"search_files": search_files,"zip_directory": zip_directory,"unzip_file": unzip_file,"trash_file": trash_file,"get_disk_usage": get_disk_usage,"empty_trash": empty_trash,"reveal_in_finder": reveal_in_finder,"lock_file": lock_file,"set_brightness": set_brightness,"get_brightness": get_brightness,"toggle_wifi": toggle_wifi,"toggle_bluetooth": toggle_bluetooth,"set_do_not_disturb": set_do_not_disturb,"sleep_system": sleep_system,"restart_system": restart_system,"shutdown_system": shutdown_system,"lock_screen": lock_screen,"get_uptime": get_uptime,"kill_process": kill_process,"set_wallpaper": set_wallpaper,"clear_clipboard": clear_clipboard,"type_text": type_text,"press_keys": press_keys,"get_mouse_position": get_mouse_position,"set_mouse_position": set_mouse_position,"close_app": close_app,"hide_app": hide_app,"minimize_window": minimize_window,"maximize_window": maximize_window,"resize_window": resize_window,"move_window": move_window,"get_frontmost_app": get_frontmost_app,"focus_app": focus_app,"create_note": create_note,"list_notes": list_notes,"get_contacts": get_contacts,"create_contact": create_contact,"send_email": send_email,"get_emails": get_emails,"create_calendar_event": create_calendar_event,"delete_calendar_event": delete_calendar_event,"get_reminders": get_reminders,"delete_reminder": delete_reminder,"set_timer": set_timer,"get_notifications": get_notifications,"fetch_url": fetch_url,"summarize_website": summarize_website,"download_file": download_file,"get_weather": get_weather,"get_news": get_news,"search_youtube": search_youtube,"get_stock_price": get_stock_price,"translate_text": translate_text,"record_screen": record_screen,"record_audio": record_audio,"play_sound": play_sound,"get_microphone_list": get_microphone_list,"get_camera_list": get_camera_list,"set_camera": set_camera,"image_resize": image_resize,"image_convert": image_convert,"remember": remember,"forget": forget,"list_memories": list_memories,"summarize_chat": summarize_chat,"export_chat": export_chat,"import_chat": import_chat,"run_shell": run_shell,"run_python": run_python,"git_status": git_status,"get_env_var": get_env_var,"set_env_var": set_env_var,"list_processes": list_processes,"get_network_info": get_network_info,"ping_host": ping_host,"generate_image": generate_image,"ocr_file": ocr_file,"control_lights": control_lights,"run_shortcut": run_shortcut,"send_notification": send_notification,"get_location": get_location,"bluetooth_scan": bluetooth_scan,"calculate": calculate,"set_alarm": set_alarm,"convert_units": convert_units,"dictionary_define": dictionary_define,"get_wifi_networks": get_wifi_networks,"get_battery_health": get_battery_health,"get_cpu_usage": get_cpu_usage,"get_memory_usage": get_memory_usage,"compress_video": compress_video,"speech_to_text": speech_to_text,"text_to_speech": text_to_speech,"qr_generate": qr_generate,"qr_decode": qr_decode,"encrypt_file": encrypt_file,
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

        try:
            self.voice_segments, self.voice_info = self.whisper_model.transcribe(
                "Dependencies/voice.wav",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
        except Exception as e:
            print(f"Whisper transcribe failed: {e}")
            return

        self.voice_text = ""
        for segment in self.voice_segments:
            self.voice_text += segment.text

        self.voice_text_result = self.voice_text.strip()
        if not self.voice_text_result:
            print("No speech recognized")
            return
        print(f"Transcribed: {self.voice_text_result}")
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
            if status:
                print(f"Audio status: {status}")
            if self.recording:
                self.audio_frames.append(indata.copy())
            
        self.stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype="float32",
            callback=callback
        )

        self.stream.start()

    def stop_recording(self, event=None):
        if not self.recording:
            return
        
        print("Stopped Recording")

        self.recording = False

        try:
            self.stream.stop()
            self.stream.close()
        except Exception as e:
            print(f"Stream stop error: {e}")
            self.stream = None

        if len(self.audio_frames) == 0:
            print("No Audio Recorded")
            return

        try:
            audio = np.concatenate(self.audio_frames, axis=0)
            # Ensure dir exists
            os.makedirs(os.path.dirname("Dependencies/voice.wav") or ".", exist_ok=True)
            # sounddevice gives float32 in [-1,1]. Normalize, apply gain, convert to int16 for robust Whisper
            # Flatten to mono if needed
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            audio = audio.astype(np.float32)
            # Remove DC offset
            audio = audio - np.mean(audio)
            # Auto-gain: normalize to 0.9 peak
            peak = np.max(np.abs(audio))
            if peak > 0:
                audio = audio * (0.9 / peak)
                # Slight boost for quiet mics
                audio = np.clip(audio * 1.2, -1.0, 1.0)
            # Convert to int16
            audio_int16 = (audio * 32767).astype(np.int16)
            write("Dependencies/voice.wav", 16000, audio_int16)
            print(f"Saved Voice ({len(audio_int16)} samples, peak {peak:.3f})")
        except Exception as e:
            print(f"Voice save failed: {e}")
            return
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
        self.root.resizable(False, False)
        
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

        # Right Alt + period to stop voicing (long TTS)
        self.right_alt_held = False
        self.root.bind("<KeyPress-Alt_R>", self._on_right_alt_press)
        self.root.bind("<KeyRelease-Alt_R>", self._on_right_alt_release)
        # Handle period while Right Alt held (flag-based; direct combo <Alt_R-period> is invalid in Tk)
        self.root.bind("<KeyPress-period>", self._handle_stop_voicing)
        self.root.bind("<KeyPress-greater>", self._handle_stop_voicing)  # period with shift is >


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

    def _on_right_alt_press(self, event=None):
        self.right_alt_held = True

    def _on_right_alt_release(self, event=None):
        self.right_alt_held = False

    def _handle_stop_voicing(self, event=None):
        # Only act if Right Alt is held and period pressed
        if getattr(self, 'right_alt_held', False) and event and event.keysym in ("period", "greater", "period", "."):
            return self.stop_voicing(event)
        return None

    def stop_voicing(self, event=None):
        print("Stopping voice (Right Alt + .)")
        try:
            stop_speech()
        except Exception as e:
            print(f"stop_voicing failed: {e}")
        return "break"

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
        # Prompt to save to memory on quit if there's a meaningful conversation
        has_user_msg = any(m.get("role") == "user" for m in self.conversation)
        if has_user_msg and len(self.conversation) > 2:
            try:
                resp = messagebox.askyesnocancel(
                    "Save to Memory?",
                    "Save this conversation to long-term memory before quitting?\n\nYes = Save to memory and chat history\nNo = Quit without saving\nCancel = Stay in app",
                    parent=self.root
                )
            except Exception as e:
                print(f"Quit prompt failed: {e}")
                resp = False
            if resp is None:  # Cancel
                return
            if resp:  # Yes - save
                try:
                    self.root.configure(cursor="wait")
                    self.root.update()
                    # Use same save path as Save chat (includes memory update)
                    self.save_chat()
                    # Small delay to let file writes flush (save_chat is sync for ollama+memory)
                    time.sleep(0.3)
                except Exception as e:
                    print(f"Save on exit failed: {e}")
                finally:
                    try:
                        self.root.configure(cursor="")
                    except:
                        pass
        try:
            stop_speech()
        except:
            pass
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
},
{
    "type": "function",
    "function": {
        "name": "delete_file",
        "description": "Delete a file at path",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "move_file",
        "description": "Move/rename a file",
        "parameters": {
            "type": "object",
            "properties": {
                    "src": {"type": "string"},
                    "dest": {"type": "string"}
                },
                    "required": ["src"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "copy_file",
        "description": "Copy a file or folder",
        "parameters": {
            "type": "object",
            "properties": {
                    "src": {"type": "string"},
                    "dest": {"type": "string"}
                },
                    "required": ["src"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "file_stats",
        "description": "Get file stats (size, mtime)",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "search_files",
        "description": "Search files by glob and optional content",
        "parameters": {
            "type": "object",
            "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "content_search": {"type": "string"}
                },
                    "required": ["pattern"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "zip_directory",
        "description": "Zip a directory",
        "parameters": {
            "type": "object",
            "properties": {
                    "source": {"type": "string"},
                    "output": {"type": "string"}
                },
                    "required": ["source"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "unzip_file",
        "description": "Unzip a file",
        "parameters": {
            "type": "object",
            "properties": {
                    "zip_path": {"type": "string"},
                    "dest": {"type": "string"}
                },
                    "required": ["zip_path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "trash_file",
        "description": "Move file to Trash",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_disk_usage",
        "description": "Get disk usage",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "empty_trash",
        "description": "Empty the Trash",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "reveal_in_finder",
        "description": "Reveal file in Finder",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "lock_file",
        "description": "Lock a file (chflags uchg)",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "set_brightness",
        "description": "Set display brightness 0-100",
        "parameters": {
            "type": "object",
            "properties": {
                    "level": {"type": "integer"}
                },
                    "required": ["level"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_brightness",
        "description": "Get display brightness",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "toggle_wifi",
        "description": "Toggle WiFi on/off/toggle",
        "parameters": {
            "type": "object",
            "properties": {
                    "action": {"type": "string"}
                },
                    "required": ["action"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "toggle_bluetooth",
        "description": "Toggle Bluetooth",
        "parameters": {
            "type": "object",
            "properties": {
                    "action": {"type": "string"}
                },
                    "required": ["action"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "set_do_not_disturb",
        "description": "Enable/disable Do Not Disturb",
        "parameters": {
            "type": "object",
            "properties": {
                    "enable": {"type": "boolean"}
                },
                    "required": ["enable"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "sleep_system",
        "description": "Put system to sleep",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "restart_system",
        "description": "Restart the Mac",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "shutdown_system",
        "description": "Shut down the Mac",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "lock_screen",
        "description": "Lock the screen",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_uptime",
        "description": "Get system uptime",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "kill_process",
        "description": "Kill process by name or PID",
        "parameters": {
            "type": "object",
            "properties": {
                    "name_or_pid": {"type": "string"}
                },
                    "required": ["name_or_pid"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "set_wallpaper",
        "description": "Set desktop wallpaper",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "clear_clipboard",
        "description": "Clear clipboard",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "type_text",
        "description": "Type text via keystrokes",
        "parameters": {
            "type": "object",
            "properties": {
                    "text": {"type": "string"}
                },
                    "required": ["text"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "press_keys",
        "description": "Press key combo like command+c",
        "parameters": {
            "type": "object",
            "properties": {
                    "keys": {"type": "string"}
                },
                    "required": ["keys"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_mouse_position",
        "description": "Get mouse position",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "set_mouse_position",
        "description": "Set mouse position",
        "parameters": {
            "type": "object",
            "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"}
                },
                    "required": ["x", "y"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "close_app",
        "description": "Quit an application",
        "parameters": {
            "type": "object",
            "properties": {
                    "app_name": {"type": "string"}
                },
                    "required": ["app_name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "hide_app",
        "description": "Hide an application",
        "parameters": {
            "type": "object",
            "properties": {
                    "app_name": {"type": "string"}
                },
                    "required": ["app_name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "minimize_window",
        "description": "Minimize window",
        "parameters": {
            "type": "object",
            "properties": {
                    "app_name": {"type": "string"}
                },
                    "required": ["app_name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "maximize_window",
        "description": "Maximize window full-screen",
        "parameters": {
            "type": "object",
            "properties": {
                    "app_name": {"type": "string"}
                },
                    "required": ["app_name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "resize_window",
        "description": "Resize window",
        "parameters": {
            "type": "object",
            "properties": {
                    "app_name": {"type": "string"},
                    "width": {"type": "integer"},
                    "height": {"type": "integer"}
                },
                    "required": ["app_name", "width", "height"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "move_window",
        "description": "Move window",
        "parameters": {
            "type": "object",
            "properties": {
                    "app_name": {"type": "string"},
                    "x": {"type": "integer"},
                    "y": {"type": "integer"}
                },
                    "required": ["app_name", "x", "y"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_frontmost_app",
        "description": "Get frontmost app name",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "focus_app",
        "description": "Focus app",
        "parameters": {
            "type": "object",
            "properties": {
                    "app_name": {"type": "string"}
                },
                    "required": ["app_name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "create_note",
        "description": "Create Notes app note",
        "parameters": {
            "type": "object",
            "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"}
                },
                    "required": ["title"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "list_notes",
        "description": "List Notes titles",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_contacts",
        "description": "List Contacts names",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "create_contact",
        "description": "Create a contact",
        "parameters": {
            "type": "object",
            "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"}
                },
                    "required": ["name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "send_email",
        "description": "Draft email in Mail",
        "parameters": {
            "type": "object",
            "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                    "required": ["to", "subject"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_emails",
        "description": "Get recent email subjects",
        "parameters": {
            "type": "object",
            "properties": {
                    "limit": {"type": "integer"}
                },
                    "required": ["limit"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "create_calendar_event",
        "description": "Create calendar event",
        "parameters": {
            "type": "object",
            "properties": {
                    "title": {"type": "string"},
                    "start_date": {"type": "string"},
                    "duration_minutes": {"type": "integer"}
                },
                    "required": ["title", "start_date"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "delete_calendar_event",
        "description": "Delete calendar event by title",
        "parameters": {
            "type": "object",
            "properties": {
                    "title": {"type": "string"}
                },
                    "required": ["title"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_reminders",
        "description": "List reminders",
        "parameters": {
            "type": "object",
            "properties": {
                    "list_name": {"type": "string"}
                },
                    "required": ["list_name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "delete_reminder",
        "description": "Delete reminder",
        "parameters": {
            "type": "object",
            "properties": {
                    "title": {"type": "string"}
                },
                    "required": ["title"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "set_timer",
        "description": "Set timer seconds",
        "parameters": {
            "type": "object",
            "properties": {
                    "seconds": {"type": "integer"},
                    "label": {"type": "string"}
                },
                    "required": ["seconds"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_notifications",
        "description": "Get notifications",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "fetch_url",
        "description": "Fetch URL text",
        "parameters": {
            "type": "object",
            "properties": {
                    "url": {"type": "string"}
                },
                    "required": ["url"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "summarize_website",
        "description": "Summarize website via LLM",
        "parameters": {
            "type": "object",
            "properties": {
                    "url": {"type": "string"}
                },
                    "required": ["url"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "download_file",
        "description": "Download URL to file",
        "parameters": {
            "type": "object",
            "properties": {
                    "url": {"type": "string"},
                    "dest": {"type": "string"}
                },
                    "required": ["url"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for location",
        "parameters": {
            "type": "object",
            "properties": {
                    "location": {"type": "string"},
                    "units": {"type": "string"}
                },
                    "required": ["location"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_news",
        "description": "Get news",
        "parameters": {
            "type": "object",
            "properties": {
                    "topic": {"type": "string"},
                    "limit": {"type": "integer"}
                },
                    "required": ["topic"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "search_youtube",
        "description": "Search YouTube via web",
        "parameters": {
            "type": "object",
            "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"}
                },
                    "required": ["query"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_stock_price",
        "description": "Get stock price data",
        "parameters": {
            "type": "object",
            "properties": {
                    "symbol": {"type": "string"}
                },
                    "required": ["symbol"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "translate_text",
        "description": "Translate text",
        "parameters": {
            "type": "object",
            "properties": {
                    "text": {"type": "string"},
                    "target_lang": {"type": "string"}
                },
                    "required": ["text"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "record_screen",
        "description": "Record screen video",
        "parameters": {
            "type": "object",
            "properties": {
                    "duration": {"type": "integer"},
                    "output": {"type": "string"}
                },
                    "required": ["duration"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "record_audio",
        "description": "Record microphone audio",
        "parameters": {
            "type": "object",
            "properties": {
                    "duration": {"type": "integer"},
                    "output": {"type": "string"}
                },
                    "required": ["duration"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "play_sound",
        "description": "Play sound file",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_microphone_list",
        "description": "List microphones",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_camera_list",
        "description": "List cameras",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "set_camera",
        "description": "Set camera index",
        "parameters": {
            "type": "object",
            "properties": {
                    "index": {"type": "integer"}
                },
                    "required": ["index"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "image_resize",
        "description": "Resize image",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"},
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                    "output": {"type": "string"}
                },
                    "required": ["width", "height"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "image_convert",
        "description": "Convert image format",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"},
                    "fmt": {"type": "string"},
                    "output": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "remember",
        "description": "Remember a fact to long-term memory",
        "parameters": {
            "type": "object",
            "properties": {
                    "fact": {"type": "string"}
                },
                    "required": ["fact"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "forget",
        "description": "Forget memories containing keyword",
        "parameters": {
            "type": "object",
            "properties": {
                    "keyword": {"type": "string"}
                },
                    "required": ["keyword"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "list_memories",
        "description": "List all memories",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "summarize_chat",
        "description": "Summarize saved chat",
        "parameters": {
            "type": "object",
            "properties": {
                    "chat_name": {"type": "string"}
                },
                    "required": ["chat_name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "export_chat",
        "description": "Export chat to md/json",
        "parameters": {
            "type": "object",
            "properties": {
                    "chat_name": {"type": "string"},
                    "fmt": {"type": "string"}
                },
                    "required": ["chat_name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "import_chat",
        "description": "Import chat JSON",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "run_shell",
        "description": "Run shell command (max 10s)",
        "parameters": {
            "type": "object",
            "properties": {
                    "command": {"type": "string"}
                },
                    "required": ["command"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "run_python",
        "description": "Run Python code",
        "parameters": {
            "type": "object",
            "properties": {
                    "code": {"type": "string"}
                },
                    "required": ["code"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "git_status",
        "description": "Git status porcelain",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_env_var",
        "description": "Get env var",
        "parameters": {
            "type": "object",
            "properties": {
                    "name": {"type": "string"}
                },
                    "required": ["name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "set_env_var",
        "description": "Set env var",
        "parameters": {
            "type": "object",
            "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string"}
                },
                    "required": ["name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "list_processes",
        "description": "List processes",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_network_info",
        "description": "Get network ifconfig",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "ping_host",
        "description": "Ping a host",
        "parameters": {
            "type": "object",
            "properties": {
                    "host": {"type": "string"}
                },
                    "required": ["host"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": "Generate image from prompt (stub)",
        "parameters": {
            "type": "object",
            "properties": {
                    "prompt": {"type": "string"}
                },
                    "required": ["prompt"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "ocr_file",
        "description": "OCR image file",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "control_lights",
        "description": "Control HomeKit lights via Shortcuts",
        "parameters": {
            "type": "object",
            "properties": {
                    "action": {"type": "string"}
                },
                    "required": ["action"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "run_shortcut",
        "description": "Run Shortcuts.app shortcut",
        "parameters": {
            "type": "object",
            "properties": {
                    "name": {"type": "string"},
                    "input_text": {"type": "string"}
                },
                    "required": ["name"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "send_notification",
        "description": "Send macOS notification",
        "parameters": {
            "type": "object",
            "properties": {
                    "title": {"type": "string"},
                    "message": {"type": "string"}
                },
                    "required": ["title", "message"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_location",
        "description": "Get approximate location",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "bluetooth_scan",
        "description": "Scan Bluetooth via system_profiler",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "Calculate math expression",
        "parameters": {
            "type": "object",
            "properties": {
                    "expression": {"type": "string"}
                },
                    "required": ["expression"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "set_alarm",
        "description": "Set alarm",
        "parameters": {
            "type": "object",
            "properties": {
                    "time_str": {"type": "string"},
                    "label": {"type": "string"}
                },
                    "required": ["time_str"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "convert_units",
        "description": "Convert units c/f km/mi",
        "parameters": {
            "type": "object",
            "properties": {
                    "value": {"type": "number"},
                    "from_unit": {"type": "string"},
                    "to_unit": {"type": "string"}
                },
                    "required": ["value"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "dictionary_define",
        "description": "Define word via dictionary API",
        "parameters": {
            "type": "object",
            "properties": {
                    "word": {"type": "string"}
                },
                    "required": ["word"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_wifi_networks",
        "description": "List preferred WiFi networks",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_battery_health",
        "description": "Get battery health via system_profiler",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_cpu_usage",
        "description": "Get CPU usage via top",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_memory_usage",
        "description": "Get memory via vm_stat",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "compress_video",
        "description": "Compress video via ffmpeg",
        "parameters": {
            "type": "object",
            "properties": {
                    "input_path": {"type": "string"},
                    "output_path": {"type": "string"}
                },
                    "required": ["input_path", "output_path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "speech_to_text",
        "description": "Transcribe audio file with Whisper",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "text_to_speech",
        "description": "Speak text via TTS",
        "parameters": {
            "type": "object",
            "properties": {
                    "text": {"type": "string"}
                },
                    "required": ["text"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "qr_generate",
        "description": "Generate QR code",
        "parameters": {
            "type": "object",
            "properties": {
                    "text": {"type": "string"},
                    "output": {"type": "string"}
                },
                    "required": ["text"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "qr_decode",
        "description": "Decode QR from image",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"}
                },
                    "required": ["path"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "encrypt_file",
        "description": "XOR encrypt file with password",
        "parameters": {
            "type": "object",
            "properties": {
                    "path": {"type": "string"},
                    "password": {"type": "string"}
                },
                    "required": ["path"]
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
