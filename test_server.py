# test_server.py
# Flask server with mock data for testing the dashboard

from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import time
import math

# ===== FLASK INIT =====
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ===== MOCK DATA GENERATION =====
mock_time = 0.0

def generate_mock_data():
    """Generate realistic mock sensor data"""
    global mock_time
    
    while True:
        mock_time += 0.05  # increment time
        
        # simulate hand moving back and forth (sine wave)
        # occasionally goes out of range to trigger SILENT status
        distance = 15 + 12 * math.sin(mock_time * 3.0)  # faster oscillation
        
        # volume changes
        volume = 0.5 + 0.5 * abs(math.sin(mock_time * 2.0))  # always positive
        
        # calculate frequency from distance (same logic as real server)
        DISTANCE_MIN = 2
        DISTANCE_MAX = 25
        FREQ_MIN = 256
        FREQ_MAX = 1024
        
        if DISTANCE_MIN <= distance <= DISTANCE_MAX:
            normalized = (distance - DISTANCE_MIN) / (DISTANCE_MAX - DISTANCE_MIN)
            frequency = FREQ_MIN + (FREQ_MAX - FREQ_MIN) * (1 - normalized)
            is_playing = True
        else:
            frequency = 0.0
            is_playing = False
        
        # emit audio state
        socketio.emit('audio_state', {
            'frequency': frequency,
            'volume': volume,
            'distance': distance,
            'playing': is_playing,
            'timestamp': time.time()
        })
        
        # emit sensor update
        socketio.emit('sensor_update', {
            'distance': distance,
            'volume': volume,
            'timestamp': time.time()
        })
        
        # emit mock waveform data
        waveform_samples = [math.sin(2 * math.pi * i / 50) for i in range(200)]
        socketio.emit('waveform_data', {
            'samples': waveform_samples
        })
        
        time.sleep(0.05)  # 20 Hz update rate

# ===== FLASK ROUTES =====
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

# ===== WEBSOCKET EVENTS =====
@socketio.on('connect')
def handle_connect():
    """When browser connects"""
    print("Browser connected")

@socketio.on('disconnect')
def handle_disconnect():
    """When browser disconnects"""
    print("Browser disconnected")

# ===== MAIN =====
if __name__ == '__main__':
    print("=" * 50)
    print("Test Server Starting...")
    print("Open browser to: http://localhost:5000")
    print("This will show MOCK DATA for testing")
    print("=" * 50)
    
    # start mock data generation in background thread
    mock_thread = threading.Thread(target=generate_mock_data, daemon=True)
    mock_thread.start()
    
    # run Flask-SocketIO server
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)