import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import customtkinter as ctk
import threading
import ollama


MODEL = "Raphael"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


class GUI:

    def __init__(self):

        self.conversation = []

        self.root = ctk.CTk()
        self.root.title("R.A.P.H.A.E.L")
        self.root.geometry("1000x650")

        self.build_ui()

        self.add_message(
            "R.A.P.H.A.E.L",
            "Online and awaiting instructions, sire."
        )

        self.root.mainloop()

    def build_ui(self):

        self.chat_box = ScrolledText(
            self.root,
            bg="#272727",
            fg="white",
            insertbackground="white",
            bd=0,
            wrap="word",
            font=("SF Pro", 12)
        )

        self.chat_box.place(
            relx=0.5,
            rely=0.42,
            anchor="center",
            relwidth=0.95,
            relheight=0.72
        )

        self.chat_box.config(state="disabled")

        self.input_box = ctk.CTkTextbox(
            self.root,
            font=("SF Pro", 12)
        )

        self.input_box.place(
            relx=0.45,
            rely=0.9,
            anchor="center",
            relwidth=0.8,
            relheight=0.1
        )

        self.send_button = ctk.CTkButton(
            self.root,
            text="Send",
            command=self.send_message
        )

        self.send_button.place(
            relx=0.92,
            rely=0.9,
            anchor="center",
            relwidth=0.08
        )

    def add_message(self, sender, message):

        self.chat_box.config(state="normal")

        self.chat_box.insert(
            "end",
            f"{sender}: {message}\n\n"
        )

        self.chat_box.see("end")

        self.chat_box.config(state="disabled")

    def send_message(self):

        user_message = self.input_box.get(
            "1.0",
            "end-1c"
        ).strip()

        if not user_message:
            return

        self.input_box.delete(
            "1.0",
            "end"
        )

        self.add_message(
            "Suren",
            user_message
        )

        self.conversation.append(
            {
                "role": "user",
                "content": user_message
            }
        )

        threading.Thread(
            target=self.generate_response,
            daemon=True
        ).start()

    def generate_response(self):

        try:

            response = ollama.chat(
                model=MODEL,
                messages=self.conversation
            )

            reply = response["message"]["content"]

            self.conversation.append(
                {
                    "role": "assistant",
                    "content": reply
                }
            )

            self.root.after(
                0,
                lambda: self.add_message(
                    "R.A.P.H.A.E.L",
                    reply
                )
            )

        except Exception as error:

            self.root.after(
                0,
                lambda: self.add_message(
                    "SYSTEM",
                    str(error)
                )
            )


GUI()