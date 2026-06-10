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

import subprocess
import time
import platform
import requests

model = Global_Variables["model"]
json_path = Global_Variables["json_path"]
application_name = Global_Variables["application_name"]

def get_time():
    from datetime import datetime

    return datetime.now().strftime(
        "%H:%M:%S"
    )