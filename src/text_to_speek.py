#Basic Usage
import pyttsx3

engine = pyttsx3.init()
engine.say("I will speak this text") # replace this with text that is wanted to be spoken
engine.runAndWait()
# Customize Voice, Rate, and Volume
engine = pyttsx3.init()

# Set rate
rate = engine.getProperty('rate')
engine.setProperty('rate', 125)

# Set volume
volume = engine.getProperty('volume')
engine.setProperty('volume', 1.0)

# Set voice
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id) # 0 for male, 1 for female

engine.say("Hello World!")
engine.runAndWait()

# Saving Speech to a File
engine.save_to_file('Hello World', 'test.mp3')
engine.runAndWait()