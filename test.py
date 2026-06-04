import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

# ---------------- WINDOW ---------------- #

root = tk.Tk()
root.title("Local LLM Assistant")
root.geometry("1200x700")
root.configure(bg="#0f172a")

# ---------------- COLORS ---------------- #

BG = "#0f172a"
PANEL = "#111827"
INPUT = "#1e293b"
TEXT = "#f8fafc"
DIM = "#94a3b8"
ACCENT = "#3b82f6"

# ---------------- STYLE ---------------- #

style = ttk.Style()
style.theme_use("clam")

style.configure(
    "TButton",
    background=ACCENT,
    foreground="white",
    borderwidth=0,
    padding=6,
)

style.configure(
    "TCombobox",
    fieldbackground=INPUT,
    background=INPUT,
    foreground="white"
)

# ---------------- TOP BAR ---------------- #

topbar = tk.Frame(root, bg=PANEL)
topbar.place(relx=0, rely=0, relwidth=1, relheight=0.08)

title = tk.Label(
    topbar,
    text="Local LLM Assistant",
    bg=PANEL,
    fg=TEXT,
    font=("Segoe UI", 16, "bold")
)
title.place(relx=0.02, rely=0.2)

status = tk.Label(
    topbar,
    text="● Connected",
    bg=PANEL,
    fg="#22c55e",
    font=("Segoe UI", 10)
)
status.place(relx=0.88, rely=0.3)

# ---------------- SIDEBAR ---------------- #

sidebar = tk.Frame(root, bg=PANEL)
sidebar.place(relx=0, rely=0.08, relwidth=0.20, relheight=0.92)

new_chat_btn = ttk.Button(sidebar, text="+ New Chat")
new_chat_btn.place(relx=0.1, rely=0.03, relwidth=0.8)

chat_list = tk.Listbox(
    sidebar,
    bg=INPUT,
    fg=TEXT,
    bd=0,
    highlightthickness=0,
    font=("Segoe UI", 10)
)

chat_list.place(relx=0.08, rely=0.12, relwidth=0.84, relheight=0.75)

# Sample chats
chat_list.insert(tk.END, "Chat 1")
chat_list.insert(tk.END, "Chat 2")
chat_list.insert(tk.END, "Python Help")
chat_list.insert(tk.END, "Code Assistant")

# ---------------- CHAT DISPLAY ---------------- #

chat_box = ScrolledText(
    root,
    bg=INPUT,
    fg=TEXT,
    insertbackground="white",
    bd=0,
    font=("Segoe UI", 11),
    wrap="word"
)

chat_box.place(relx=0.22, rely=0.1, relwidth=0.75, relheight=0.60)

# Sample messages
chat_box.insert(tk.END, "You:\n", "user")
chat_box.insert(tk.END, "Explain transformers simply.\n\n")

chat_box.insert(tk.END, "Assistant:\n", "assistant")
chat_box.insert(
    tk.END,
    "Transformers are neural networks designed for understanding sequences like language.\n\n"
)

chat_box.tag_config("user", foreground="#60a5fa")
chat_box.tag_config("assistant", foreground="#22c55e")

# ---------------- INPUT BOX ---------------- #

input_box = tk.Text(
    root,
    bg=INPUT,
    fg=TEXT,
    insertbackground="white",
    bd=0,
    font=("Segoe UI", 11),
    wrap="word"
)

input_box.place(relx=0.22, rely=0.73, relwidth=0.62, relheight=0.13)

# Placeholder text
input_box.insert("1.0", "Type your message here...")

# ---------------- SEND BUTTON ---------------- #

send_btn = ttk.Button(root, text="Send")
send_btn.place(relx=0.86, rely=0.76, relwidth=0.10, relheight=0.06)

# ---------------- SETTINGS BAR ---------------- #

settings = tk.Frame(root, bg=PANEL)
settings.place(relx=0.22, rely=0.90, relwidth=0.75, relheight=0.07)

# Model selector
model_label = tk.Label(
    settings,
    text="Model:",
    bg=PANEL,
    fg=TEXT,
    font=("Segoe UI", 10)
)
model_label.place(relx=0.02, rely=0.25)

model_box = ttk.Combobox(
    settings,
    values=["llama3", "mistral", "deepseek"],
    state="readonly"
)
model_box.place(relx=0.10, rely=0.22, relwidth=0.18)
model_box.set("llama3")

# Temperature
temp_label = tk.Label(
    settings,
    text="Temperature",
    bg=PANEL,
    fg=TEXT,
    font=("Segoe UI", 10)
)
temp_label.place(relx=0.35, rely=0.25)

temp_slider = ttk.Scale(
    settings,
    from_=0,
    to=1,
    orient="horizontal"
)
temp_slider.place(relx=0.48, rely=0.3, relwidth=0.20)

# Max tokens
token_label = tk.Label(
    settings,
    text="Tokens",
    bg=PANEL,
    fg=TEXT,
    font=("Segoe UI", 10)
)
token_label.place(relx=0.72, rely=0.25)

token_spin = tk.Spinbox(
    settings,
    from_=256,
    to=8192,
    bg=INPUT,
    fg=TEXT,
    bd=0
)
token_spin.place(relx=0.82, rely=0.22, relwidth=0.12)

# ---------------- RUN ---------------- #

root.mainloop()