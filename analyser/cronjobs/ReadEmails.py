from analyser.chat.ChatEmailReader import ChatEmailReader
import traceback


def processEmail():
    try:
        reader = ChatEmailReader()
        reader.readEmail()
    except Exception as e:
        traceback.print_exc()
