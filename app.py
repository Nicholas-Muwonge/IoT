import streamlit as st
import pandas as pd
import json, threading, queue
import paho.mqtt.client as mqtt

# ---------- Shared State ----------
if "mqtt_q" not in st.session_state:
    st.session_state.mqtt_q = queue.Queue()
if "data" not in st.session_state:
    st.session_state.data = []
if "connected" not in st.session_state:
    st.session_state.connected = False

# ---------- MQTT Callbacks ----------
def on_connect(client, userdata, flags, rc, properties=None):
    """Callback when the client connects to the broker."""
    st.session_state.connected = True
    client.subscribe("sensors/#")
    print("✅ Connected to MQTT Broker!", rc)

def on_message(client, userdata, msg):
    """Callback for incoming MQTT messages."""
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        st.session_state.mqtt_q.put(payload)
    except Exception as e:
        print("⚠️ Parse error:", e)

# ---------- MQTT Start Function ----------
def start_mqtt(broker="localhost", port=1883):
    # Handle different paho-mqtt versions
    try:
        client = mqtt.Client(
            client_id="streamlit-dashboard",
            protocol=mqtt.MQTTv311,
            callback_api_version=1
        )
    except TypeError:
        # For older versions without callback_api_version argument
        client = mqtt.Client(client_id="streamlit-dashboard", protocol=mqtt.MQTTv311)
    except ValueError:
        # For older 1.x that raise ValueError
        client = mqtt.Client(client_id="streamlit-dashboard", protocol=mqtt.MQTTv311)

    client.on_connect = on_connect
    client.on_message = on_message

    # Connect and start MQTT loop in background thread
    try:
        client.connect(broker, int(port), 60)
        thread = threading.Thread(target=client.loop_forever, daemon=True)
        thread.start()
    except Exception as e:
        st.error(f"MQTT connection failed: {e}")

# ---------- Streamlit UI ----------
st.set_page_config(page_title="IoT Real-Time Dashboard", layout="wide")
st.title("📊 IoT Live Dashboard — Wi-Fi + MQTT + Streamlit")

broker = st.text_input("MQTT Broker", "localhost")
port = st.number_input("Port", value=1883)

if st.button("Connect"):
    start_mqtt(broker, port)
    st.success("MQTT connection started!")

# ---------- Process Incoming Data ----------
while not st.session_state.mqtt_q.empty():
    msg = st.session_state.mqtt_q.get()
    st.session_state.data.append(msg)
    if len(st.session_state.data) > 500:
        st.session_state.data = st.session_state.data[-500:]

# ---------- Display Dashboard ----------
if len(st.session_state.data) > 0:
    df = pd.DataFrame(st.session_state.data)
    st.subheader("📥 Latest Sensor Data")
    st.dataframe(df.tail(10))

    # Live charts (if numeric)
    numeric_cols = [col for col in df.columns if df[col].dtype in ["float64", "int64"]]
    for col in numeric_cols:
        st.line_chart(df[col], height=200, use_container_width=True)
else:
    st.info("Waiting for sensor data... (Ensure MQTT publisher is running)")
