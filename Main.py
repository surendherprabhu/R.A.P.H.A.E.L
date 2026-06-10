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
from duckduckgo_search import DDGS
import subprocess
import time
import platform
import requests


#Global Variables
model = Global_Variables["model"]
json_path = Global_Variables["json_path"]
application_name = Global_Variables["application_name"]


Conversation = [

    {
        "role" : "system",
        "content" : "Remember Raphael, You WILL do what are told to do and TELL what you are asked"
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
def get_time():
    from datetime import datetime

    return datetime.now().strftime(
        "%H:%M:%S"
    )

def search_web(query):

    with DDGS() as ddgs:
        results = list(ddgs.text(query,max_results=5))
    return results

TOOLS = {

    "get_time": get_time,
    "search_web": search_web


}


#------------------------------------------------------------------------------------------------------------------#
class Raphael:
    def __init__(self):
        self.conversation = copy.deepcopy(Conversation)
        self.connection_status = connection_status
        self.memory = ""

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
        ctk.CTkLabel(self.root, text=self.connection_status).place(relx = 0.90,rely =0.04,anchor="center",)

        #settings button
        ctk.CTkButton(self.root, text="Settings").place(relx=0.1,rely=0.95,anchor="center",relwidth = 0.14,)

        #Model name at bottom
        ctk.CTkLabel(self.root, text=f"Model: {model}").place(relx=0.88,rely=0.95,anchor="center")

        #chat selection
        self.Chat_selection = ctk.CTkComboBox(self.root,values=ListFiles(),state="readonly",command=self.chat_select)
        self.Chat_selection.place(relx = 0.1 , anchor ="center", rely = 0.17,relwidth = 0.16, relheight = 0.05)

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
            "description": "Returns the current time",
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

    def add_memories(self):
        try:
            with open("Memories/Memories.json") as file:
                data = json.load(file)
        except (FileNotFoundError , json.JSONDecodeError):
            data = ""

        temp = copy.deepcopy(self.conversation)
        temp.append({
            "role" : "system",
            "content" : f"""Hello Raphael. These are your memories '{data}',Now return me a summarize this along with the conversation that you just had.
                            Update the memory list.
                            Only include factual information.
                            Do not infer anything.
                            Do not guess.
                            Do summarize the entire conversation and extract the information from those chat which needs to be remembered and dont forget to update your memory with the things the user clearly wants you to remember"
                            Only store information likely to be useful in future chats.
                            Also this is not like prompt your going to reply to just list the things.
                        """
        })
        reply = ollama.chat(
            model = model,
            messages=temp
        )
        memory = reply["message"]["content"]
        with open("Memories/Memories.json", "w") as file:
            json.dump(memory , file , indent=4)
#------------------------------------------------------------------------------------------------------------------#

#------------------------------------------------------------------------------------------------------------------#
# Initialization
if __name__ == "__main__":
    Raphael()
#------------------------------------------------------------------------------------------------------------------#
