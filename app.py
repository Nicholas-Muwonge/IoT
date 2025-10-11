import streamlit as st
import pandas as pd
import json
import threading
import queue
import paho.mqtt.client as mqtt

if "mqtt_q" not in st.session_state:
    st.session_state.mqtt_q = queue.Queue()
if "data" not in st.session_state:
    st.session_state.data = []
if "connected" not in st.session_state:
    st.session_state.connected = False

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Connected to MQTT Broker!")
        st.session_state.connected = True
        client.subscribe("sensors/#")
    else:
        print(f"❌ MQTT Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        userdata.put(payload)
    except Exception as e:
        print("Parse error:", e)

def start_mqtt(broker="localhost", port=1883):
    client = mqtt.Client(client_id="streamlit-dashboard", protocol=mqtt.MQTTv311, userdata=st.session_state.mqtt_q)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(broker, port, 60)
        thread = threading.Thread(target=client.loop_forever, daemon=True)
        thread.start()
    except Exception as e:
        st.error(f"MQTT connection failed: {e}")

st.set_page_config(page_title="IoT Real-Time Dashboard", layout="wide")
st.title("📊 Nicholas & Jarudi's IoT Live Dashboard")

broker = st.text_input("MQTT Broker", "localhost")
port = st.number_input("Port", value=1883)

if st.button("Connect"):
    start_mqtt(broker, port)
    st.success("MQTT connection started!")

while not st.session_state.mqtt_q.empty():
    msg = st.session_state.mqtt_q.get()
    st.session_state.data.append(msg)
    if len(st.session_state.data) > 500:
        st.session_state.data = st.session_state.data[-500:]

if len(st.session_state.data) > 0:
    df = pd.DataFrame(st.session_state.data)
    st.subheader("📥 Latest Sensor Data")
    st.dataframe(df.tail(10))

    numeric_cols = [col for col in df.columns if df[col].dtype in ["float64", "int64"]]
    for col in numeric_cols:
        st.line_chart(df[col], height=200, use_container_width=True)
else:
    st.info("Waiting for sensor data... (Ensure MQTT publisher is running)")
