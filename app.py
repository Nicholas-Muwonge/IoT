# app.py
import streamlit as st
import pandas as pd
import json, threading, queue
import paho.mqtt.client as mqtt

# Initialize shared state
if "mqtt_q" not in st.session_state:
    st.session_state.mqtt_q = queue.Queue()
if "data" not in st.session_state:
    st.session_state.data = []

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    st.session_state.connected = True
    client.subscribe("sensors/#")
    print("Connected to MQTT Broker!")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        st.session_state.mqtt_q.put(payload)
    except Exception as e:
        print("Parse error:", e)

def start_mqtt(broker="localhost", port=1883):
    client = mqtt.Client("streamlit-dashboard")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(broker, port, 60)
    thread = threading.Thread(target=client.loop_forever, daemon=True)
    thread.start()

# Streamlit UI
st.set_page_config(page_title="IoT Real-Time Dashboard", layout="wide")
st.title("📊 IoT Live Dashboard — Wi-Fi + MQTT + Streamlit")

broker = st.text_input("MQTT Broker", "localhost")
port = st.number_input("Port", value=1883)
if st.button("Connect"):
    start_mqtt(broker, port)
    st.success("MQTT connection started!")

# Process new MQTT messages
while not st.session_state.mqtt_q.empty():
    msg = st.session_state.mqtt_q.get()
    st.session_state.data.append(msg)
    if len(st.session_state.data) > 500:
        st.session_state.data = st.session_state.data[-500:]

# Convert to DataFrame for display
if len(st.session_state.data) > 0:
    df = pd.DataFrame(st.session_state.data)
    st.dataframe(df.tail(10))

    # If numeric values available, show live chart
    if "temperature" in df.columns:
        st.line_chart(df["temperature"], height=200)
    if "humidity" in df.columns:
        st.line_chart(df["humidity"], height=200)
else:
    st.info("Waiting for sensor data...")
