import time, json, random
from datetime import datetime
import sys
import paho.mqtt.client as mqtt

BROKER = "localhost"     
PORT = 1883
TOPIC = "sensors/room1/temp"
DEVICE_ID = "esp32-room1"

try:
    client = mqtt.Client(client_id=DEVICE_ID, protocol=mqtt.MQTTv311)
except TypeError:
    client = mqtt.Client(client_id=DEVICE_ID, protocol=mqtt.MQTTv311)
except ValueError:
    client = mqtt.Client(client_id=DEVICE_ID, protocol=mqtt.MQTTv311)

try:
    client.connect(BROKER, PORT, 60)
except Exception as e:
    print("Could not connect to broker:", e)
    sys.exit(1)

client.loop_start()

try:
    i = 0
    while True:
        i += 1
        payload = {
            "device_id": DEVICE_ID,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "temperature": round(20 + random.random() * 5, 2),
            "humidity": round(40 + random.random() * 10, 2),
            "seq": i
        }
        client.publish(TOPIC, json.dumps(payload), qos=1)
        print("Published:", payload)
        time.sleep(2)
except KeyboardInterrupt:
    print("Stopping publisher...")
finally:
    client.loop_stop()
    client.disconnect()

