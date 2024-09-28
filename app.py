from flask import Flask, render_template, jsonify
import speech_recognition as sr
import pyttsx3
import geocoder
from twilio.rest import Client
import threading
import time
import random

app = Flask(__name__)

# Twilio credentials
TWILIO_ACCOUNT_SID = 
TWILIO_AUTH_TOKEN = 
TWILIO_PHONE_NUMBER = sender twilio number
TO_PHONE_NUMBER = receiver phone

# Initialize text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1) 

def speak_text(text):
    engine.say(text)
    engine.runAndWait()

def recognize_speech():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            print("Listening...")
            audio = recognizer.listen(source)
        print("Recognizing...")
        command = recognizer.recognize_google(audio).lower()
        print(f"Recognized command: {command}")
        return command
    except sr.UnknownValueError:
        print("Speech recognition could not understand the audio")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return None
    except Exception as e:
        print(f"An error occurred during speech recognition: {e}")
        return None

def get_location():
    try:
        g = geocoder.ip('me')
        return g.latlng
    except Exception as e:
        print(f"Error retrieving location: {e}")
        return None

def send_sms(message, location=None):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        if location:
            # Create Google Maps link
            maps_link = f"https://www.google.com/maps?q={location[0]},{location[1]}"
            # Append the Google Maps link to the message
            message += f"\n\nView on Google Maps: {maps_link}"
        
        client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=TO_PHONE_NUMBER
        )
    except Exception as e:
        print(f"Failed to send SMS: {e}")

# Flag to indicate whether SOS has been triggered
sos_triggered = False
detection_active = True

def shake_detection():
    global sos_triggered, detection_active
    SHAKE_THRESHOLD = 20
    SHAKE_COUNT = 3
    shake_detected = 0
    detection_interval = 0.5  # seconds between shake detections
    
    def detect_shake():
        nonlocal shake_detected
        if not detection_active:
            return  # Stop detecting shakes if detection is not active

        # Mock sensor data
        magnitude = random.uniform(0, 30)  # Simulate sensor readings
        print(f"Sensor magnitude: {magnitude}")  # Debugging line

        if magnitude > SHAKE_THRESHOLD:
            shake_detected += 1
            print(f"Shake detected! Count: {shake_detected}")  # Debugging line
            if shake_detected >= SHAKE_COUNT:
                trigger_sos()
                shake_detected = 0  # Reset shake count after triggering SOS
        else:
            shake_detected = 0  # Reset shake count if no significant shake is detected

    def trigger_sos():
        global sos_triggered, detection_active
        if sos_triggered:
            return  # Do not trigger SOS if already triggered
        print("SOS Triggered!")
        sos_triggered = True  # Set flag to indicate SOS has been triggered
        detection_active = False  # Stop further shake detection
        location = get_location()
        if location:
            location_message = f"Emergency! Location: Latitude {location[0]}, Longitude {location[1]}"
            send_sms(location_message, location)  # Pass the location to send_sms
        else:
            location_message = "Emergency! Location data could not be retrieved."
            send_sms(location_message)  # No location available

    while detection_active:
        detect_shake()
        time.sleep(detection_interval)

# Create a global variable to store the shake detection thread
shake_detection_thread = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['GET'])
def start():
    try:
        command = recognize_speech()
        if command and "sos" in command:
            location = get_location()
            if location:
                location_message = f"Emergency! Location: Latitude {location[0]}, Longitude {location[1]}"
                send_sms(location_message, location)  # Pass the location to send_sms
                return jsonify({"status": "SOS alert sent", "location": location_message})
            else:
                location_message = "Emergency! Location data could not be retrieved."
                send_sms(location_message)  # No location available
                return jsonify({"status": "SOS alert sent", "location": location_message})
        return jsonify({"status": "No SOS detected"})
    except Exception as e:
        print(f"Error in /start route: {e}")
        return jsonify({"status": "Error", "message": str(e)}), 500

@app.route('/shake-status', methods=['GET'])
def shake_status():
    try:
        status_message = "Shake detection is active" if detection_active else "SOS has been triggered"
        return jsonify({"status": status_message})
    except Exception as e:
        print(f"Error in /shake-status route: {e}")
        return jsonify({"status": "Error", "message": str(e)}), 500

if __name__ == '__main__':
    # Start the shake detection thread
    shake_detection_thread = threading.Thread(target=shake_detection, daemon=True)
    shake_detection_thread.start()
    
    # Run the Flask app
    try:
        app.run(debug=True)
    finally:
        # Ensure the shake detection thread is stopped when Flask exits
        detection_active = False
        if shake_detection_thread:
            shake_detection_thread.join()
