# server.py 
# Flask server with MQTT subscriber for data collection and WebSocket for frontend

from paho.mqtt import client as mqtt
from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import time

import audio_engine

# ===== CONFIG =====
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

DISTANCE_MIN = 2   # cm - min thresh
DISTANCE_MAX = 25  # cm - max thresh
BUFFER_MIN = 0 # cm - setting high base tone
BUFFER_MAX = 27 # cm - a little bit higher for low base tone

FREQ_MIN = 256  # C4
FREQ_MAX = 1024  # C6

# ===== FLASK INIT =====
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# ===== GLOBAL VARS =====
current_distance = 0.0
current_volume = 0.5
current_frequency = 0.0
is_playing = False

# ===== MQTT CALLBACKS =====
def on_connect(client, userdata, flags, rc):
    """When MQTT connects to broker"""
    if rc == 0:
        print("Connected to MQTT broker")
        # sub to sensor topics
        client.subscribe("sensors/distance")
        client.subscribe("sensors/volume")
        client.subscribe("control/status")
        print("Subscribed to sensor topics")
    else:
        print(f"Failed to connect to MQTT broker, return code {rc}")

def on_message(client, userdata, msg):
    """When MQTT message arrives"""
    global current_distance, current_volume, current_frequency, is_playing
    
    try:
        # parse msg
        topic = msg.topic
        value = float(msg.payload.decode())
        
        if topic == "sensors/distance":
            current_distance = value

            # Calculate freq from dist
            if DISTANCE_MIN <= current_distance <= DISTANCE_MAX:
 
                # Map dist to freq
                normalized = (current_distance - DISTANCE_MIN) / (DISTANCE_MAX - DISTANCE_MIN)
                current_frequency = FREQ_MIN + (FREQ_MAX - FREQ_MIN) * (1 - normalized)
                is_playing = True

            elif DISTANCE_MAX <= current_distance <= BUFFER_MAX:
                current_distance = 25
                normalized = (current_distance - DISTANCE_MIN) / (DISTANCE_MAX - DISTANCE_MIN)
                current_frequency = FREQ_MIN + (FREQ_MAX - FREQ_MIN) * (1 - normalized)
                is_playing = True

            elif BUFFER_MIN <= current_distance <= DISTANCE_MIN:
                current_distance = 2
                normalized = (current_distance - DISTANCE_MIN) / (DISTANCE_MAX - DISTANCE_MIN)
                current_frequency = FREQ_MIN + (FREQ_MAX - FREQ_MIN) * (1 - normalized)
                is_playing = True
                
            else:
                # silence outside thresh
                current_frequency = 0.0
                is_playing = False
            
            ####TEMP####
            # print audio state for debugging
            if is_playing:
                print(f"PLAYING | Freq: {current_frequency:.1f} Hz | Vol: {current_volume:.2f} | Dist: {current_distance:.1f}cm")
            else:
                print(f"SILENT  | Distance: {current_distance:.1f}cm (outside threshold)")
        
        elif topic == "sensors/volume":
            current_volume = value
        
        elif topic == "control/status":
            print(f"Status: {msg.payload.decode()}")
        
        # broadcast current state to all connected browsers
        broadcast_state()

        # aduio engine update
        audio_engine.update_audio_params(current_frequency, current_volume, is_playing)
        
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

# ===== MQTT INIT =====
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def start_mqtt():
    """Connect to MQTT broker and start loop"""
    print(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()  # block loop

# Start MQTT in background thread
mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
mqtt_thread.start()

# Init audio engine
audio_engine.init_audio()

# ===== WEBSOCKET FUNCTIONS =====
def broadcast_state():
    """Send current audio state to all connected browsers"""
    state_data = {
        'frequency': current_frequency,
        'volume': current_volume,
        'distance': current_distance,
        'playing': is_playing
    }
    socketio.emit('audio_state', state_data)

def broadcast_sensor_update():
    """Send sensor readings to browsers"""
    sensor_data = {
        'distance': current_distance,
        'volume': current_volume,
        'timestamp': time.time()
    }
    socketio.emit('sensor_update', sensor_data)

# ===== FLASK ROUTES =====
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

# ===== WEBSOCKET EVENTS =====
@socketio.on('connect')
def handle_connect():
    """When browser connects via WebSocket"""
    print("Browser connected")
    broadcast_state()

@socketio.on('disconnect')
def handle_disconnect():
    """When browser disconnects"""
    print("Browser disconnected")

# ===== BACKGROUND TASK =====
def background_broadcast():
    """Periodically broadcast sensor data for visualization"""
    while True:
        broadcast_sensor_update()

        # get and broadcast waveform data
        waveform = audio_engine.get_current_waveform()
        socketio.emit('waveform_data', {'samples': waveform})

        time.sleep(0.05)  # 20 Hz

# Start background broadcasting
broadcast_thread = threading.Thread(target=background_broadcast, daemon=True)
broadcast_thread.start()

# ===== MAIN =====
if __name__ == '__main__':
    print("=" * 50)
    print("Theremin Server Starting...")
    print(f"Distance threshold: {DISTANCE_MIN}cm - {DISTANCE_MAX}cm")
    print(f"Frequency range: {FREQ_MIN}Hz - {FREQ_MAX}Hz")
    print("=" * 50)
    
    # Run Flask-SocketIO server
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)