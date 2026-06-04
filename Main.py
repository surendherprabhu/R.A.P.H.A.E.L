import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import customtkinter as ctk


import ollama

import sys
import os
import threading
import json


model = "Raphael"
chat_limit = 64
json_path = "./Data"
application_name = "R.A.P.H.A.E.L"
connection_status = "Connected 🌐"


GUI_colors = {
        
        "background" : "",
        "panel" : "",
        "input" : "",
        "dim" : "",
        "text" : "",
        "accent" : ""

}

Conversation = [

    {
        "role" : "system",
        "content" : "Remember Raphael, You WILL do what are told to do and TELL what you are asked"
    }
]

def start_ollama():
    os.system("ollama serve")

def Start_Chat(Convo = Conversation):
    response = ollama.chat(
        model = model,
        messages=Convo
    )
    for chat in range(chat_limit):
        
        user_input = str(input("You: "))
        print("\n")
        
        if "goodbye" in user_input.lower():
            break
        

        user_message = {
            "role" : "user",
            "content" : f"{user_input}"
        }

        Convo.append(user_message)

        response = ollama.chat(
            model = model,
            messages=Convo
        )
        
        if "code1" in user_input.lower():
            os.system(f"{response["message"]["content"]}")
            continue

        assistant_message = {
            "role" : "assistant",
            "content" : f"{response["message"]["content"]}"
        }

        Convo.append(assistant_message)

        print(f"Raphael : {response["message"]["content"]}")
        print("\n")



    SaveAsJson(Convo)
    
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
        print(f"{index}. {new_file}")
    return files

def Terminal_access():
    print("1.Open rapahel \n2.list data files \n3.Continue Conversation \n\n")
    user_choice = str(input(">>"))


    if user_choice.lower() in "1.Open rapahel".lower():
        Start_Chat()
    elif user_choice.lower() in "2.list data files":
        ListFiles()
    elif user_choice.lower() in "3.continue conversation":
        ListFiles()
        file_name = str(input("Enter the Name of the conversation that you wish to continue:\n>> "))
        with open(f"Data/{file_name}.json") as file:
            data = json.load(file)
        Start_Chat(data)

class Raphael:
    def __init__(self):
        self.conversation = Conversation.copy()

        self.create_window()
        self.root.mainloop()

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
        ttk.Separator(self.root, orient="vertical").place(relx=0.2, rely=0.09, relheight=0.81, relwidth=0.001)
        ttk.Separator(self.root, orient="horizontal").place(relx=0, rely=0.09, relheight=0.001, relwidth=1)
        ttk.Separator(self.root, orient="horizontal").place(relx=0, rely=0.9, relheight=0.001, relwidth=1)

        #LOGO
        ctk.CTkLabel(self.root,text=application_name).place(relx = 0.1,rely =0.04,anchor = "center",relwidth = 0.15,relheight=0.1)
         
        #Connection Status
        ctk.CTkLabel(self.root, text=connection_status).place(relx = 0.90,rely =0.04,anchor="center",)

        #settings button
        ctk.CTkButton(self.root, text="Settings").place(relx=0.1,rely=0.95,anchor="center",relwidth = 0.14,)

        #Model name at bottom
        ctk.CTkLabel(self.root, text=f"Model: {model}").place(relx=0.88,rely=0.95,anchor="center")

        #chat selection
        Chat_selection = ctk.CTkComboBox(self.root,values=ListFiles(),state="readonly",command=self.chat_select)
        Chat_selection.place(relx = 0.1 , anchor ="center", rely = 0.17,relwidth = 0.16, relheight = 0.05)

        #new chat button and save chat button
        ctk.CTkButton(self.root,text="Save chat",command= self.save_chat).place(relx = 0.1,anchor="center",rely = 0.8,relwidth = 0.13)
        ctk.CTkButton(self.root,text="+ New Chat",command=self.new_chat).place(relx = 0.1,anchor="center",rely = 0.7,relwidth = 0.13)
        
        #chat area
        self.chat_box = ctk.CTkTextbox(self.root, wrap = "word",state = "normal" , font =("SF Pro", 12))
        self.chat_box.place(relx = 0.6 , rely = 0.45 , anchor = "center", relwidth = 0.75 , relheight= 0.65)

        #input box 
        self.input_box = ctk.CTkTextbox(self.root)
        self.input_box.place(relx = 0.549, rely = 0.83 , anchor = "center" , relwidth = 0.65 , relheight = 0.085  )
        
        #send button
        self.send_button = ctk.CTkButton(self.root, text = "Send",command = self.program_cycle)
        self.send_button.place(relx = 0.925 , rely = 0.83 , anchor ="center" ,relheight = 0.085 , relwidth = 0.085)
        
    def chat_select(self,selected_chat):
         return(selected_chat)
  
    def add_message(self, content, role):
        self.chat_box.configure(state="normal")

        self.chat_box.insert("end", f"{role}:\n")
        self.chat_box.insert("end", f"{content}\n\n")

        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def Generate_Response(self, Convo):
        self.repsonse = ollama.chat(
            model = model,
            messages=Convo
        )

        reply = self.repsonse["message"]["content"]

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
        self.conversation = Conversation.copy()

        self.chat_box.configure(state="normal")
        self.chat_box.delete("1.0", "end")
        self.chat_box.configure(state="disabled")
    
    def save_chat(self):
        
        

Raphael()