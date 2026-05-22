import sys
import ollama
import os
import json

model = "raphael"
chat_limit = 3
json_path = "./Data"

Conversation = [
    {
        "role" : "system",
        "content" : """If the user message starts with the keyword “code1” then return this exact string f’ open -a {app_name}’ . 
This is similar to the python d strings for example , it asked to say open safari the user would say, ‘code1 , open safari ‘ and you would return  ‘open -a safari‘
 if the user doesnt specify this, it means he wishes to chat normally. You need not incentivize the user to use the code1 command"""

    }
    ,

    {
        "role" : "user",
        "content" : "hello"
    }
]

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
    for file in files:
        print(file)

def Terminal_access():
    print("1.Open rapahel \n2.list data files \n\n")
    user_choice = str(input(">>"))


    if user_choice.lower() in "1.Open rapahel".lower():
        Start_Chat()
    elif user_choice.lower() in "2.list data files":
        ListFiles()

Terminal_access()