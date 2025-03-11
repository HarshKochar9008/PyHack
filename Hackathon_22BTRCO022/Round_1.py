import speech_recognition as sr
import pyttsx3
import datetime
import os
import json
import re
import random
import requests
from threading import Timer
import logging
from difflib import get_close_matches

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='Assistant.log'
)
logger = logging.getLogger('Assistant')

class SmartHomeController:
    def __init__(self):
        self.devices = self._load_devices()
        logger.info(f"Loaded {len(self.devices)} smart home devices")
    
    def _load_devices(self):
        try:
            with open('devices.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            devices = {
                "lights": {
                    "living_room": {"state": "off", "brightness": 100, "color": "white"},
                    "bedroom": {"state": "off", "brightness": 100, "color": "white"},
                    "kitchen": {"state": "off", "brightness": 100, "color": "white"}
                },
                "alarms": []
            }
            with open('devices.json', 'w') as file:
                json.dump(devices, file, indent=2)
            return devices
    
    def _save_devices(self):
        with open('devices.json', 'w') as file:
            json.dump(self.devices, file, indent=2)
    
    def control_light(self, room, action, brightness=None, color=None):
        if room not in self.devices["lights"]:
            return f"I couldn't find any lights in the {room}"
        
        if action in ["on", "off"]:
            self.devices["lights"][room]["state"] = action
            result = f"{room} lights turned {action}"
        elif action == "dim" and brightness is not None:
            self.devices["lights"][room]["brightness"] = brightness
            self.devices["lights"][room]["state"] = "on"
            result = f"{room} lights dimmed to {brightness}%"
        elif action == "color" and color is not None:
            self.devices["lights"][room]["color"] = color
            self.devices["lights"][room]["state"] = "on"
            result = f"{room} lights changed to {color}"
        else:
            return f"Cant perform that light command"
        
        self._save_devices()
        logger.info(f"Light control: {result}")
        return result
    
    def get_light_status(self, room=None):
        if room and room in self.devices["lights"]:
            light = self.devices["lights"][room]
            return f"The {room} lights are {light['state']}, brightness is {light['brightness']}%, and color is {light['color']}"
        elif room:
            return f"I couldn't find any lights in the {room}"
        else:
            status = []
            for room, light in self.devices["lights"].items():
                status.append(f"{room}: {light['state']}")
            return "Light status: " + ", ".join(status)
    
    def set_alarm(self, time_str):
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
            return "Please specify the time in HH:MM format"
            
        self.devices["alarms"].append(time_str)
        self._save_devices()
        logger.info(f"Alarm set for {time_str}")
        return f"Alarm set for {time_str}"
    
    def list_alarms(self):
        if not self.devices["alarms"]:
            return "You have no alarms set"
        
        return "Your alarms: " + ", ".join(self.devices["alarms"])
    
    def clear_alarms(self):
        count = len(self.devices["alarms"])
        self.devices["alarms"] = []
        self._save_devices()
        logger.info("All alarms cleared")
        return f"Cleared {count} alarms"

class NaturalLanguageProcessor:
    def __init__(self):
        self.intents = {
            "greeting": [
                r"hello", r"hi there", r"hey", r"greetings", r"good morning", 
                r"good afternoon", r"good evening", r"howdy"
            ],
            "farewell": [
                r"goodbye", r"bye", r"see you", r"see you later", r"good night",
                r"farewell", r"take care"
            ],
            "gratitude": [
                r"thank you", r"thanks", r"appreciate it", r"thanks a lot"
            ],
            "light_control": [
                r"turn (on|off) (the )?([\w\s]+) lights?",
                r"([\w\s]+) lights? (on|off)",
                r"dim (the )?([\w\s]+) lights? to (\d+)%?",
                r"change (the )?([\w\s]+) lights? to ([\w\s]+) color"
            ],
            "light_status": [
                r"(how are|what's the status of) (the )?([\w\s]+) lights?",
                r"are (the )?([\w\s]+) lights? (on|off)",
                r"light status"
            ],
            "alarm_control": [
                r"set (an )?alarm for ([\d:]+)(?: ?(am|pm))?",
                r"wake me up at ([\d:]+)(?: ?(am|pm))?",
                r"what alarms (do I have|are set)",
                r"list( all)? alarms",
                r"clear( all)? alarms"
            ],
            "time_query": [
                r"what time is it", r"current time", r"tell me the time", r"what's the time"
            ],
            "date_query": [
                r"what (day|date) is (it|today)", r"today's date", r"current date", r"what's the date"
            ],
            "weather_query": [
                r"what's the weather( like)?( today| now)?",
                r"(is it|will it be) (sunny|rainy|cloudy|snowing)( today| tomorrow)?",
                r"do I need (a|an) (umbrella|jacket|coat)( today| tomorrow)?"
            ],
            "help": [
                r"help( me)?", r"what can you do", r"commands", r"features", 
                r"what (commands|things) can I say"
            ]
        }
        
        self.room_names = ["living room", "bedroom", "kitchen", "bathroom", 
                           "dining room", "office", "hallway", "entryway"]
        
        self.color_names = ["white", "red", "green", "blue", "yellow", "purple", 
                            "orange", "pink", "warm white", "cool white"]
    
    def match_intent(self, text):
        text = text.lower().strip()
        
        for intent, patterns in self.intents.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return intent, match
        
        return "unknown", None
    
    def extract_room_name(self, text):
        for room in self.room_names:
            if room in text.lower():
                return room
                
        words = text.lower().split()
        for word in words:
            matches = get_close_matches(word, self.room_names, n=1, cutoff=0.7)
            if matches:
                return matches[0]
                
        return None
    
    def extract_color_name(self, text):
        for color in self.color_names:
            if color in text.lower():
                return color
                
        words = text.lower().split()
        for word in words:
            matches = get_close_matches(word, self.color_names, n=1, cutoff=0.7)
            if matches:
                return matches[0]
                
        return None
    
    def extract_time(self, time_str, period=None):
        if ":" in time_str:
            hour, minute = map(int, time_str.split(":"))
        else:
            hour = int(time_str)
            minute = 0
            
        if period == "pm" and hour < 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
            
        return f"{hour:02d}:{minute:02d}"
    
    def process_command(self, text):
        intent, match = self.match_intent(text)
        
        logger.info(f"Detected intent: {intent}")
        if match:
            logger.info(f"Intent match groups: {match.groups()}")
        
        if intent == "greeting":
            return {
                "action": "respond",
                "response": self._get_greeting_response()
            }
            
        elif intent == "farewell":
            return {
                "action": "respond",
                "response": self._get_farewell_response()
            }
            
        elif intent == "gratitude":
            return {
                "action": "respond",
                "response": self._get_gratitude_response()
            }
            
        elif intent == "light_control":
            return self._process_light_control(text, match)
            
        elif intent == "light_status":
            return self._process_light_status(text, match)
            
        elif intent == "alarm_control":
            return self._process_alarm_control(text, match)
            
        elif intent == "time_query":
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            return {
                "action": "respond",
                "response": f"The current time is {current_time}"
            }
            
        elif intent == "date_query":
            current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return {
                "action": "respond",
                "response": f"Today is {current_date}"
            }
            
        elif intent == "weather_query":
            return {
                "action": "respond",
                "response": "I'm sorry, I don't have access to weather information in this demo."
            }
            
        elif intent == "help":
            return {
                "action": "respond",
                "response": self._get_help_message()
            }
            
        else:
            return {
                "action": "respond",
                "response": "I'm not sure I understand. Try asking for help to see what I can do."
            }
    
    def _get_greeting_response(self):
        responses = [
            "Hello! How can I help you today?",
            "Hi there! What can I do for you?",
            "Greetings! How may I assist you?",
            "Hello! I'm listening.",
            "Hi! What would you like me to do?"
        ]
        return random.choice(responses)
    
    def _get_farewell_response(self):
        responses = [
            "Goodbye! Have a great day!",
            "See you later!",
            "Bye for now! Let me know if you need anything else.",
            "Take care!",
            "Until next time!"
        ]
        return random.choice(responses)
    
    def _get_gratitude_response(self):
        responses = [
            "You're welcome!",
            "Happy to help!",
            "Anytime!",
            "My pleasure!",
            "Glad I could assist!"
        ]
        return random.choice(responses)
    
    def _get_help_message(self):
        return """Here are some things you can ask me to do:
- Control lights: "Turn on the living room lights" or "Dim the bedroom lights to 50%"
- Check light status: "Are the kitchen lights on?"
- Set alarms: "Set an alarm for 7:30 am" or "Wake me up at 6:00"
- Ask about time: "What time is it?"
- Ask about date: "What day is today?"
You can also say hello or goodbye!"""
    
    def _process_light_control(self, text, match):
        room = self.extract_room_name(text)
        if not room:
            return {
                "action": "respond", 
                "response": "I couldn't figure out which room you're referring to."
            }
        
        if "dim" in text.lower():
            brightness_match = re.search(r"(\d+)%?", text)
            if brightness_match:
                brightness = int(brightness_match.group(1))
                return {
                    "action": "light_control",
                    "room": room,
                    "command": "dim",
                    "brightness": brightness
                }
        elif "color" in text.lower() or "change" in text.lower():
            color = self.extract_color_name(text)
            if color:
                return {
                    "action": "light_control",
                    "room": room,
                    "command": "color",
                    "color": color
                }
        else:
            if "on" in text.lower():
                return {
                    "action": "light_control",
                    "room": room,
                    "command": "on"
                }
            elif "off" in text.lower():
                return {
                    "action": "light_control",
                    "room": room,
                    "command": "off"
                }
        
        return {
            "action": "respond",
            "response": "I couldn't understand that light command."
        }
    
    def _process_light_status(self, text, match):
        if "light status" in text.lower():
            return {
                "action": "light_status"
            }
            
        room = self.extract_room_name(text)
        if room:
            return {
                "action": "light_status",
                "room": room
            }
            
        return {
            "action": "respond",
            "response": "I couldn't figure out which lights you're asking about."
        }
    

    
    def _process_alarm_control(self, text, match):
        if "list" in text.lower() or "what" in text.lower():
            return {
                "action": "list_alarms"
            }
            
        if "clear" in text.lower():
            return {
                "action": "clear_alarms"
            }
            
        time_match = re.search(r"(\d+(?::\d+)?)\s*(am|pm)?", text)
        if time_match:
            time_str = time_match.group(1)
            period = time_match.group(2)
            
            formatted_time = self.extract_time(time_str, period)
            return {
                "action": "set_alarm",
                "time": formatted_time
            }
            
        return {
            "action": "respond",
            "response": "I couldn't understand that alarm command."
        }

class VirtualAssistant:
    def __init__(self, voice_enabled=True):
        self.voice_enabled = voice_enabled
        self.smart_home = SmartHomeController()
        self.nlp = NaturalLanguageProcessor()
        self.recognizer = sr.Recognizer()
        
        if self.voice_enabled:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            voices = self.engine.getProperty('voices')
            self.engine.setProperty('voice', voices[1].id)
        
        self.conversation_history = []
        self.active = True
    
    def speak(self, text):
        print(f"Assistant: {text}")
        if self.voice_enabled:
            self.engine.say(text)
            self.engine.runAndWait()
    
    def listen(self):
        try:
            with sr.Microphone() as source:
                print("Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
                print("Processing speech...")
                text = self.recognizer.recognize_google(audio)
                print(f"User: {text}")
                return text
                
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            print("Speech recognition could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"Could not request results from speech recognition service; {e}")
            return None
        except Exception as e:
            print(f"Error in speech recognition: {e}")
            return None
    
    def text_input(self):
        try:
            text = input("You: ")
            return text
        except Exception as e:
            print(f"Error getting text input: {e}")
            return None
    
    def process_response(self, response_data):
        action = response_data.get("action")
        
        if action == "respond":
            return response_data.get("response", "I'm not sure how to respond to that.")
            
        elif action == "light_control":
            room = response_data.get("room")
            command = response_data.get("command")
            brightness = response_data.get("brightness")
            color = response_data.get("color")
            
            return self.smart_home.control_light(room, command, brightness, color)
            
        elif action == "light_status":
            room = response_data.get("room")
            return self.smart_home.get_light_status(room)
            
        elif action == "set_alarm":
            time_str = response_data.get("time")
            return self.smart_home.set_alarm(time_str)
            
        elif action == "list_alarms":
            return self.smart_home.list_alarms()
            
        elif action == "clear_alarms":
            return self.smart_home.clear_alarms()
            
        else:
            return "I'm not sure how to handle that request."
    
    def run(self):
        self.speak("Hello! I'm your virtual assistant. How can I help you today?")
        
        while self.active:
            if self.voice_enabled:
                user_input = self.listen()
            else:
                user_input = self.text_input()
                
            if user_input:
                self.conversation_history.append({"role": "user", "content": user_input})
                
                if user_input.lower() in ["exit", "quit", "goodbye", "bye", "bye-bye", "thank you", "thanks", "appreciate it", "thanks a lot"]:
                    self.speak("Goodbye! Have a great day!")
                    self.active = False
                    break
                
                response_data = self.nlp.process_command(user_input)
                response_text = self.process_response(response_data)
                
                self.speak(response_text)
                
                self.conversation_history.append({"role": "assistant", "content": response_text})

def main():
    voice_enabled = True
    try:
        import speech_recognition as sr
        import pyttsx3
    except ImportError:
        print("Speech recognition libraries not found. Running in text-only mode.")
        voice_enabled = False
    
    assistant = VirtualAssistant(voice_enabled=voice_enabled)
    assistant.run()

if __name__ == "__main__":
    main()