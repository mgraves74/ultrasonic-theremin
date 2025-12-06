# sensors.py - Raspberry Pi sensor reading and MQTT publishing
# written in python 2

from paho.mqtt import client as mqtt
import grovepi
import time
from collections import deque

# ===== CONFIG =====
LAPTOP_IP = "172.20.10.12"
MQTT_PORT = 1883

ULTRASONIC_PORT = 4  # port D4
POTENTIOMETER_PORT = 0  # port A0

PUBLISH_RATE = 20  # 20 Hz
FILTER_WINDOW_SIZE = 5  # averages 5 readings

DISTANCE_MIN = 2  # cm - minimum threshold
DISTANCE_MAX = 25  # cm - maximum threshold

# ===== MQTT SETUP =====
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    """When MQTT connects to broker"""
    if rc == 0:
        print("Connected to MQTT broker successfully")
    else:
        print("Failed to connect, return code {}".format(rc))

def on_disconnect(client, userdata, rc):
    """When MQTT disconnects"""
    print("Disconnected from MQTT broker")

mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect

# Connect to broker
print("Connecting to MQTT broker at {}:{}".format(LAPTOP_IP, MQTT_PORT))
mqtt_client.connect(LAPTOP_IP, MQTT_PORT, 60)
mqtt_client.loop_start()  # start MQTT in background thread

# ===== SENSOR FILTERING =====
# Moving average filter for ultrasonic sensor
distance_buffer = deque(maxlen=FILTER_WINDOW_SIZE)

def get_filtered_distance():
    """Read ultrasonic sensor and apply moving average filter"""
    try:
        # read raw distance
        raw_distance = grovepi.ultrasonicRead(ULTRASONIC_PORT)
        
        # add to buffer
        distance_buffer.append(raw_distance)
        
        # calculate moving average
        if len(distance_buffer) > 0:
            filtered_distance = sum(distance_buffer) / float(len(distance_buffer))
            return filtered_distance
        else:
            return raw_distance
            
    except Exception as e:
        print("Error reading ultrasonic sensor: {}".format(e))
        return None

def get_volume():
    """Read potentiometer and normalize"""
    try:
        # read anlog value (0-1023)
        pot_value = grovepi.analogRead(POTENTIOMETER_PORT)
        
        # normalize
        volume = pot_value / 1023.0
        
        return volume
        
    except Exception as e:
        print("Error reading potentiometer: {}".format(e))
        return None

# ===== MAIN LOOP =====
def main():
    """Main sensor reading and publishing loop"""
    print("Starting sensor readings...")
    print("Distance threshold: {}cm - {}cm".format(DISTANCE_MIN, DISTANCE_MAX))
    print("Publishing at {} Hz".format(PUBLISH_RATE))
    
    sleep_time = 1.0 / PUBLISH_RATE
    
    try:
        while True:
            # read sensors
            distance = get_filtered_distance()
            volume = get_volume()
            
            # only publish if readings are valid
            if distance is not None and volume is not None:
                # publish distance
                mqtt_client.publish("sensors/distance", str(distance))
                
                # publish volume
                mqtt_client.publish("sensors/volume", str(volume))
                
                # print for debugging
                print("Distance: {:.1f}cm | Volume: {:.2f}".format(distance, volume))
            
            # Sleep to maintain publish rate
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\nStopping sensor readings...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("Disconnected from MQTT broker")

if __name__ == "__main__":
    main()