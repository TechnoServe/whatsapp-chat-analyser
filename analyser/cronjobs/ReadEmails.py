from analyser.chat.ChatEmailReader import ChatEmailReader

def processEmail():
    reader = ChatEmailReader()
    reader.readEmail()

    print("Hey what's up?")