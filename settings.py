import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

import copy
import os
import json
import subprocess
import platform
import re

import ollama

from methods import load_memories, save_memories, get_disk_usage, get_system_info, volume_control
from Data import *
import Data


class Settings:
    def __init__(self):
        self.menu_is_open = False
        self.window = None
        self.models = []
        self.get_ollama_models()
        self.model = Data.model
        self.on_model_change = None
        self.appearance = "dark"

    def get_ollama_models(self):
        self.models = []
        try:
            response = ollama.list()
            for model in response.models:
                self.models.append(model.model)
        except Exception as e:
            print(f"Settings: ollama.list failed: {e}")
            # fallback to current model so combo is not empty
            if Data.model not in self.models:
                self.models.append(Data.model)
        if not self.models:
            self.models = [Data.model]
        return self.models

    def refresh_models(self):
        self.get_ollama_models()
        if self.window and self.window.winfo_exists():
            try:
                self.model_selection.configure(values=self.models)
                self.model_status.configure(text=f"{len(self.models)} models found")
            except:
                pass

    def create_window(self, parent, on_model_change=None):
        if self.menu_is_open and self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.menu_is_open = True
        self.on_model_change = on_model_change
        self.window = ctk.CTkToplevel(parent)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.window.protocol("WM_DELETE_WINDOW", self.close_window)

        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        w = min(620, int(sw * 0.45))
        h = min(720, int(sh * 0.75))
        x = int((sw - w) / 2)
        y = int((sh - h) / 2)
        self.window.geometry(f"{w}x{h}+{x}+{y}")
        self.window.title("Settings — R.A.P.H.A.E.L")
        self.window.configure(bg="#050d1e")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.focus_force()
        self.window.grab_set()

        # Title
        ctk.CTkLabel(self.window, text="Settings", font=("SF Pro", 20, "bold")).pack(pady=(14, 6))
        ctk.CTkLabel(self.window, text="Configure Raphael — changes save instantly", font=("SF Pro", 11), text_color="gray").pack(pady=(0, 8))

        # Scrollable content
        self.scroll = ctk.CTkScrollableFrame(self.window, width=w-40, height=h-120)
        self.scroll.pack(fill="both", expand=True, padx=12, pady=6)

        self._build_llm_section()
        self._build_appearance_section()
        self._build_audio_section()
        self._build_memory_section()
        self._build_storage_section()
        self._build_system_section()
        self._build_shortcuts_section()
        self._build_footer()

    # ---------- Sections ----------
    def _section(self, title):
        ctk.CTkLabel(self.scroll, text=title, font=("SF Pro", 13, "bold"), anchor="w").pack(fill="x", pady=(14, 4), padx=6)
        ttk.Separator(self.scroll, orient="horizontal").pack(fill="x", padx=6, pady=(0, 6))
        frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        frame.pack(fill="x", padx=6, pady=2)
        return frame

    def _build_llm_section(self):
        f = self._section("LLM — Model")
        ctk.CTkLabel(f, text="Ollama Model:", width=120, anchor="w").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        self.model_selection = ctk.CTkComboBox(f, values=self.models, state="readonly", command=self.select_model, width=220)
        if self.model in self.models:
            self.model_selection.set(self.model)
        else:
            self.model_selection.set(self.models[0])
        self.model_selection.grid(row=0, column=1, padx=6, pady=6, sticky="w")
        ctk.CTkButton(f, text="Refresh", width=80, command=self.refresh_models).grid(row=0, column=2, padx=6, pady=6)
        self.model_status = ctk.CTkLabel(f, text=f"{len(self.models)} models • {Data.model}", text_color="gray", font=("SF Pro", 10))
        self.model_status.grid(row=1, column=0, columnspan=3, sticky="w", padx=6)
        ctk.CTkLabel(f, text="Requires Ollama running. `ollama pull <model>` to add.", text_color="gray", font=("SF Pro", 10)).grid(row=2, column=0, columnspan=3, sticky="w", padx=6)

    def _build_appearance_section(self):
        f = self._section("Appearance")
        ctk.CTkLabel(f, text="Theme:", width=120, anchor="w").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        self.appearance_combo = ctk.CTkComboBox(f, values=["dark", "light", "system"], state="readonly", command=self.change_appearance, width=160)
        self.appearance_combo.set(self.appearance)
        self.appearance_combo.grid(row=0, column=1, padx=6, pady=6, sticky="w")
        ctk.CTkLabel(f, text="Window is non-resizable by design.", text_color="gray", font=("SF Pro", 10)).grid(row=1, column=0, columnspan=2, sticky="w", padx=6)

    def change_appearance(self, mode):
        self.appearance = mode
        ctk.set_appearance_mode(mode)

    def _build_audio_section(self):
        f = self._section("Voice & Audio")
        ctk.CTkLabel(f, text="Voice model:", width=120, anchor="w").grid(row=0, column=0, padx=6, pady=4, sticky="w")
        exists = os.path.exists(voice_model) and os.path.exists(voice_model + ".json")
        status = "Found" if exists else "Missing — fallback to 'say'"
        ctk.CTkLabel(f, text=f"{os.path.basename(voice_model)} • {status}", text_color="gray" if exists else "orange", font=("SF Pro", 10)).grid(row=0, column=1, columnspan=2, sticky="w", padx=6)
        ctk.CTkLabel(f, text="Test phrase:", width=120, anchor="w").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        self.tts_entry = ctk.CTkEntry(f, placeholder_text="Hello Suren, Raphael here", width=220)
        self.tts_entry.insert(0, "Hello Suren, voice test")
        self.tts_entry.grid(row=1, column=1, padx=6, pady=6)
        ctk.CTkButton(f, text="Speak", width=80, command=self.test_voice).grid(row=1, column=2, padx=6)
        ctk.CTkLabel(f, text="Volume:", width=120, anchor="w").grid(row=2, column=0, padx=6, pady=6, sticky="w")
        self.volume_slider = ctk.CTkSlider(f, from_=0, to=100, command=self.on_volume_slider, width=160)
        try:
            cur = int(volume_control("get")) if volume_control("get").isdigit() else 60
        except:
            cur = 60
        self.volume_slider.set(cur)
        self.volume_slider.grid(row=2, column=1, padx=6, pady=6, sticky="w")
        self.volume_label = ctk.CTkLabel(f, text=f"{int(cur)}%", width=40)
        self.volume_label.grid(row=2, column=2, padx=6)
        ctk.CTkButton(f, text="Mute", width=70, command=lambda: self.set_volume("mute")).grid(row=3, column=1, sticky="w", padx=6, pady=2)
        ctk.CTkButton(f, text="Unmute", width=70, command=lambda: self.set_volume("unmute")).grid(row=3, column=1, sticky="e", padx=6, pady=2)
        ctk.CTkLabel(f, text="Stop voice: Right Alt + .", text_color="gray", font=("SF Pro", 10)).grid(row=4, column=0, columnspan=3, sticky="w", padx=6, pady=(6,0))
        ctk.CTkLabel(f, text="Mic: Hold Left Alt to record • Ctrl+V toggles camera", text_color="gray", font=("SF Pro", 10)).grid(row=5, column=0, columnspan=3, sticky="w", padx=6)

    def test_voice(self):
        txt = self.tts_entry.get().strip() or "Hello Suren"
        # Use same speak path as Main (piper -> say). Import lazily to avoid circular.
        try:
            from Main import speak
            import threading
            threading.Thread(target=speak, args=(txt,), daemon=True).start()
        except Exception:
            try:
                subprocess.Popen(["say", "-r", "180", txt])
            except Exception as e:
                print(f"test_voice failed: {e}")

    def on_volume_slider(self, val):
        lvl = int(val)
        self.volume_label.configure(text=f"{lvl}%")
        # Debounce: only set on release would be better, but set live
        try:
            volume_control("set", lvl)
        except:
            pass

    def set_volume(self, action):
        try:
            volume_control(action)
            cur = volume_control("get")
            if cur.isdigit():
                self.volume_slider.set(int(cur))
                self.volume_label.configure(text=f"{cur}%")
        except:
            pass

    def _build_memory_section(self):
        f = self._section("Memory")
        ctk.CTkLabel(f, text="Long-term memories stored in Memories.json", text_color="gray", font=("SF Pro", 10)).pack(anchor="w", padx=6)
        self.memory_box = ctk.CTkTextbox(f, height=110, wrap="word", font=("SF Pro", 11))
        self.memory_box.pack(fill="x", padx=6, pady=6)
        self.refresh_memory_box()
        btns = ctk.CTkFrame(f, fg_color="transparent")
        btns.pack(fill="x", padx=6, pady=2)
        ctk.CTkButton(btns, text="Refresh", width=90, command=self.refresh_memory_box).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Save", width=90, command=self.save_memory_box).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Clear Memories", width=120, fg_color="#8b3a3a", hover_color="#a64d4d", command=self.clear_memories).pack(side="left", padx=4)

    def refresh_memory_box(self):
        try:
            data = load_memories()
            txt = data.get("content", "").strip() or "(no memories yet)"
            meta = f"Updated: {data.get('updated_at') or '—'} • {len(txt.splitlines())} lines"
            self.memory_box.configure(state="normal")
            self.memory_box.delete("1.0", "end")
            self.memory_box.insert("1.0", txt + "\n\n" + meta)
            self.memory_box.configure(state="disabled")
        except Exception as e:
            print(f"refresh_memory_box failed: {e}")

    def save_memory_box(self):
        try:
            # first line bulk is memories, last line is meta - strip meta
            raw = self.memory_box.get("1.0", "end-1c")
            # Remove meta line
            lines = [l for l in raw.splitlines() if not l.startswith("Updated:")]
            content = "\n".join(lines).strip()
            # Remove placeholder if present
            if content == "(no memories yet)":
                content = ""
            save_memories(content)
            self.refresh_memory_box()
        except Exception as e:
            print(f"save_memory_box failed: {e}")

    def clear_memories(self):
        try:
            if messagebox.askyesno("Clear Memories", "Delete all long-term memories?"):
                save_memories("")
                self.refresh_memory_box()
        except:
            # fallback without messagebox
            save_memories("")
            self.refresh_memory_box()

    def _build_storage_section(self):
        f = self._section("Storage & Chats")
        usage = get_disk_usage(".")
        free = usage.get("free_GB", "?") if isinstance(usage, dict) else "?"
        ctk.CTkLabel(f, text=f"Disk free: {free} GB • Chats: {len(self._list_chats())} • Data: Dependencies/Data/", text_color="gray", font=("SF Pro", 10)).pack(anchor="w", padx=6, pady=2)
        btns = ctk.CTkFrame(f, fg_color="transparent")
        btns.pack(fill="x", padx=6, pady=6)
        ctk.CTkButton(btns, text="Open Data Folder", width=140, command=lambda: subprocess.Popen(["open", "Dependencies/Data"])).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Open Memories", width=130, command=lambda: subprocess.Popen(["open", "Dependencies/Memories"])).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Clear All Chats", width=130, fg_color="#8b3a3a", hover_color="#a64d4d", command=self.clear_chats).pack(side="left", padx=4)

    def _list_chats(self):
        try:
            from methods import ListFiles
            return ListFiles()
        except:
            return []

    def clear_chats(self):
        try:
            if not messagebox.askyesno("Clear Chats", "Delete all saved chats in Dependencies/Data/?"):
                return
        except:
            pass
        try:
            for name in self._list_chats():
                for ext in [".json", ""]:
                    p = f"Dependencies/Data/{name}{ext}"
                    if os.path.exists(p):
                        os.remove(p)
        except Exception as e:
            print(f"clear_chats failed: {e}")

    def _build_system_section(self):
        f = self._section("System")
        try:
            info = get_system_info()
            if isinstance(info, dict):
                txt = f"{info.get('os','')} {info.get('release','')} • {info.get('machine','')} • Python {info.get('python_version','')}"
            else:
                txt = str(info)
        except:
            txt = f"{platform.system()} {platform.release()}"
        ctk.CTkLabel(f, text=txt, text_color="gray", font=("SF Pro", 10), wraplength=520, justify="left").pack(anchor="w", padx=6, pady=2)
        try:
            import psutil  # optional
            has_psutil = True
        except:
            has_psutil = False
        # Quick actions
        btns = ctk.CTkFrame(f, fg_color="transparent")
        btns.pack(fill="x", padx=6, pady=4)
        ctk.CTkButton(btns, text="Copy System Info", width=140, command=lambda: self._copy_text(txt)).pack(side="left", padx=4)
        if has_psutil:
            ctk.CTkLabel(f, text="psutil available for detailed metrics", text_color="gray", font=("SF Pro", 10)).pack(anchor="w", padx=6)

    def _copy_text(self, txt):
        try:
            subprocess.run(["pbcopy"], input=txt, text=True, check=True)
        except:
            pass

    def _build_shortcuts_section(self):
        f = self._section("Keyboard Shortcuts")
        shortcuts = [
            ("Enter / Send", "Send message"),
            ("Shift+Enter", "New line"),
            ("Hold Left Alt", "Record voice (release to send)"),
            ("Right Alt + .", "Stop voice playback"),
            ("Ctrl+V", "Toggle camera overlay"),
            ("Settings", "Open this panel"),
        ]
        for k, desc in shortcuts:
            row = ctk.CTkFrame(f, fg_color="transparent")
            row.pack(fill="x", padx=6, pady=1)
            ctk.CTkLabel(row, text=k, width=160, anchor="w", font=("SF Pro", 11, "bold")).pack(side="left")
            ctk.CTkLabel(row, text=desc, anchor="w", text_color="gray").pack(side="left")

    def _build_footer(self):
        row = ctk.CTkFrame(self.window, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(row, text=f"Raphael • {Data.model} • {application_name}", text_color="gray", font=("SF Pro", 10)).pack(side="left")
        ctk.CTkButton(row, text="Close", width=90, command=self.close_window).pack(side="right")

    def close_window(self):
        if self.window is not None and self.window.winfo_exists():
            try:
                self.window.grab_release()
            except:
                pass
            self.window.destroy()
        self.window = None
        self.menu_is_open = False

    def select_model(self, selected_model):
        Data.model = selected_model
        self.model = selected_model
        if self.on_model_change:
            self.on_model_change(selected_model)
        try:
            self.model_status.configure(text=f"Model: {selected_model}")
        except:
            pass
