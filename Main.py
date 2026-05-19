import ollama

model = "raphael"

Conversation = [
    {
        "role" : "user",
        "content" : "Wake up R.A.P.H.A.E.L!"
    }
]

def Start_Chat():
    response = ollama.chat(
        model = model,
        messages=Conversation
    )
    for i in range(50):
        
        assistant_message = {
            "role" : "assistant",
            "content" : f"{response["message"]["content"]}"
        }

        Conversation.append(assistant_message)

        print(f"Raphael : {response["message"]["content"]}")

        user_input = str(input("You: "))

        user_message = {
            "role" : "user",
            "content" : f"{user_input}"
        }

        Conversation.append(user_message)

        response = ollama.chat(
            model = model,
            messages=Conversation
        )

Start_Chat()