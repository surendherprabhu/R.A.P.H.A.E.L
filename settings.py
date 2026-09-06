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



import Data

class Settings:
    def __init__(self):
        self.menu_is_open = False
        self.window = None
        self.models = []
        self.get_ollama_models()
        self.model = Data.model
        self.on_model_change = None


    def get_ollama_models(self):
        response = ollama.list()

        for model in response.models:
            self.models.append(model.model)
        return self.models

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

        full_screen_width = self.window.winfo_screenwidth()
        full_screen_height = self.window.winfo_screenheight()
        
        
        self.screenwidth = int(full_screen_width / 3)
        self.screenheight = int(full_screen_height / 3)
        
        
        x_coordinate = int((full_screen_width / 2) - (self.screenwidth / 2))
        y_coordinate = int((full_screen_height / 2) - (self.screenheight / 2))
        
        
        self.window.geometry(f"{self.screenwidth}x{self.screenheight}+{x_coordinate}+{y_coordinate}")
        self.window.title("Settings")
        self.window.configure(bg="#050d1e")
        self.window.transient(parent)
        self.window.focus_force()

        self.model_selection = ctk.CTkComboBox(self.window, values = self.models,state="readonly", command = self.select_model)
        self.model_selection.place(relx = 0.7, anchor = "center" , rely = 0.1, relwidth = 0.4)

    def close_window(self):
        if self.window is not None and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
        self.menu_is_open = False

    def select_model(self, selected_model):
        Data.model = selected_model
        self.model = selected_model
        if self.on_model_change:
            self.on_model_change(selected_model)
        
