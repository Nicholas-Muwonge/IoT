# app.py
import streamlit as st
import requests
import time
import threading
import queue
import json
import pandas as pd

# Optional libs for websocket and redis ingestion
try:
    import websocket  # websocket-client
except Exception:
    websocket = None

try:
    import redis
except Exception:
    redis = None

# ---------- Helpers ----------
def init_state():
    if "ws_q" not in st.session_state:
        st.session_state.ws_q = queue.Queue()
    if "redis_q" not in st.session_state:
        st.session_state.redis_q = queue.Queue()
    if "data" not in st.session_state:
        st.session_state.data = []  # list of dicts

init_state()

def append_data(item):
    st.session_state.data.append(item)
    # Keep last N
    if len(st.session_state.data) > 1000:
        st.session_state.data = st.session_state.data[-1000:]

# ---------- WebSocket client thread ----------
def start_ws_client(url):
    if websocket is None:
        st.warning("websocket-client library not installed; WebSocket mode unavailable.")
        return

    def on_message(ws, message):
        try:
            obj = json.loads(message)
        except Exception:
            obj = {"payload": message}
        st.session_state.ws_q.put(obj)

    def on_error(ws, error):
        st.session_state.ws_q.put({"error": str(error)})

    def on_close(ws, close_status_code, close_msg):
        st.session_state.ws_q.put({"info": "ws closed"})

    def run():
        while True:
            try:
                ws = websocket.WebSocketApp(url,
                                            on_message=on_message,
                                            on_error=on_error,
                                            on_close=on_close)
                ws.run_forever()
            except Exception as e:
                st.session_state.ws_q.put({"error": f"WS client exception: {e}"})
            # backoff before reconnect
            time.sleep(2)

    t = threading.Thread(target=run, daemon=True)
    t.start()

# ---------- Redis PubSub listener ----------
def start_redis_listener(url, channel):
    if redis is None:
        st.warning("redis library not installed; Redis Pub/Sub unavailable.")
        return

    def run():
        try:
            r = redis.from_url(url)
            pubsub = r.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(channel)
            for msg in pubsub.listen():
                try:
                    data = msg.get("data")
                    if isinstance(data, bytes):
                        try:
                            obj = json.loads(data.decode("utf-8"))
                        except Exception:
                            obj = {"payload": data.decode("utf-8")}
                    else:
                        obj = {"payload": str(data)}
                except Exception as e:
                    obj = {"error": str(e)}
                st.session_state.redis_q.put(obj)
        except Exception as e:
            st.session_state.redis_q.put({"error": f"redis listener exception: {e}"})
            time.sleep(3)
            return

    t = threading.Thread(target=run, daemon=True)
    t.start()

# ---------- UI ----------
st.set_page_config(page_title="Real-time Streamlit App", layout="wide")
st.title("🔴 Real-time Data App (Polling, WebSocket, Redis Pub/Sub)")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("Ingestion")
    mode = st.radio("Choose ingestion mode", ["Polling (HTTP)", "WebSocket (client)", "Redis Pub/Sub"])

    if mode == "Polling (HTTP)":
        endpoint = st.text_input("Polling endpoint (returns JSON list or object)", "http://localhost:9000/data")
        interval = st.number_input("Poll every (seconds)", min_value=1, value=2)
        start_poll = st.button("Start Polling")
    elif mode == "WebSocket (client)":
        ws_url = st.text_input("WebSocket URL (ws:// or wss://)", "ws://localhost:9001/ws")
        if st.button("Start WebSocket client"):
            start_ws_client(ws_url)
    else:
        redis_url = st.text_input("Redis URL", "redis://localhost:6379/0")
        redis_channel = st.text_input("Redis channel", "realtime")
        if st.button("Start Redis listener"):
            start_redis_listener(redis_url, redis_channel)

    st.markdown("---")
    st.header("Controls")
    if st.button("Clear data"):
        st.session_state.data = []
        st.success("Cleared recent data")

with col2:
    st.header("Live feed")
    placeholder = st.empty()

    # Polling loop (simplified): uses st.experimental_rerun or st_autorefresh
    if mode == "Polling (HTTP)" and 'start_poll' in locals() and start_poll:
        st.info(f"Polling {endpoint} every {interval}s — use Ctrl+C to stop if running locally.")
        # We'll do a limited polling loop in the browser: manual button to poll once + autorefresh
        if st.button("Poll once now"):
            try:
                r = requests.get(endpoint, timeout=5)
                r.raise_for_status()
                try:
                    payload = r.json()
                except Exception:
                    payload = {"text": r.text}
                # accept list or dict
                if isinstance(payload, list):
                    for item in payload:
                        append_data(item)
                elif isinstance(payload, dict):
                    append_data(payload)
                else:
                    append_data({"payload": str(payload)})
            except Exception as e:
                st.error(f"Poll error: {e}")

        # auto-refresh UI (client-side)
        st_autorefresh = st.experimental_rerun  # alias to remind
        # show last N rows
        df = pd.DataFrame(st.session_state.data[-100:])
        placeholder.dataframe(df)

    else:
        # For websocket & redis modes, pull from the queues into data
        # Drain websocket queue
        drained = False
        try:
            while not st.session_state.ws_q.empty():
                item = st.session_state.ws_q.get_nowait()
                append_data(item)
                drained = True
        except Exception:
            pass

        try:
            while not st.session_state.redis_q.empty():
                item = st.session_state.redis_q.get_nowait()
                append_data(item)
                drained = True
        except Exception:
            pass

        df = pd.DataFrame(st.session_state.data[-200:])
        placeholder.dataframe(df)

    st.markdown("---")
    st.header("Simple charts & metrics")
    if len(st.session_state.data) > 0:
        # If numeric field 'value' present, plot it
        try:
            df = pd.DataFrame(st.session_state.data)
            if "value" in df.columns:
                st.line_chart(df["value"].astype(float))
            else:
                st.write("No numeric 'value' field found in recent data. Show sample rows below.")
        except Exception as e:
            st.write("Could not build chart:", e)
    else:
        st.write("No data yet.")

st.markdown("---")
st.caption("Tip: run the included `sim_publisher.py` to test polling / websocket / redis modes locally.")
