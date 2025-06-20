import streamlit as st
import paho.mqtt.client as paho
from paho import mqtt
# import ssl
import threading
import json
import time

# Konfigurasi MQTT
MQTT_BROKER = "f6cac07c41f14b0cb9dc708769c192b1.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_TOPIC = "esp32/ir_sensor"
MQTT_USERNAME = "jujundial"
MQTT_PASSWORD = "Jujundial_7"

# rerun = False

# Global variable untuk shared data antar thread
if 'shared_data' not in st.session_state:
    st.session_state.shared_data = {
        "parking_state": {
            "lantai1": ["Kosong", "Kosong", "Kosong", "Kosong", "Kosong", "Kosong", "Kosong"],  # 3 slot selalu kosong, 2 dari broker
            "lantai2": ["Kosong", "Kosong", "Kosong", "Kosong"]  # 4 slot dari broker
        },
        "last_update": time.time(),
        "mqtt_connected": False
    }

# Thread-safe data storage
class ThreadSafeData:
    def __init__(self):
        self.lock = threading.Lock()
        self.data = {
            "parking_state": {
                "lantai1": ["Kosong", "Kosong", "Kosong", "Kosong", "Kosong", "Kosong", "Kosong"],
                "lantai2": ["Kosong", "Kosong", "Kosong", "Kosong"]
            },
            "last_update": time.time(),
            "mqtt_connected": False
        }
    
    def update_parking_data(self, new_data):
        with self.lock:
            if "lantai1" in new_data and len(new_data["lantai1"]) == 2:
                self.data["parking_state"]["lantai1"][5] = "Terisi" if new_data["lantai1"][0] else "Kosong"
                self.data["parking_state"]["lantai1"][6] = "Terisi" if new_data["lantai1"][1] else "Kosong"
                
            if "lantai2" in new_data and len(new_data["lantai2"]) == 4:
                for i in range(4):
                    self.data["parking_state"]["lantai2"][i] = "Terisi" if new_data["lantai2"][i] else "Kosong"
            
            self.data["last_update"] = time.time()
    
    def get_data(self):
        with self.lock:
            return self.data.copy()
    
    def set_connection_status(self, status):
        with self.lock:
            self.data["mqtt_connected"] = status

# Inisialisasi thread-safe data storage
if 'thread_data' not in st.session_state:
    st.session_state.thread_data = ThreadSafeData()

# Fungsi callback MQTT
def on_connect(client, userdata, flags, rc):
    thread_data = userdata
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        thread_data.set_connection_status(True)
        print(f"Connected to MQTT broker and subscribed to {MQTT_TOPIC}")
    else:
        thread_data.set_connection_status(False)
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    global rerun
    thread_data = userdata
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        print(f"Received data: {payload}")
        
        # Update thread-safe data
        thread_data.update_parking_data(data)
        print(f"Updated parking state successfully")
        # rerun = True
        # st.rerun()
        
    except Exception as e:
        print(f"Error parsing message: {e}")

def on_disconnect(client, userdata, rc):
    thread_data = userdata
    thread_data.set_connection_status(False)
    print("Disconnected from MQTT broker")

# Thread untuk MQTT agar tidak blocking Streamlit
def mqtt_thread(thread_data):
    try:
        client = paho.Client(client_id="streamlit-client", userdata=thread_data)
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
        client.tls_insecure_set(False)
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        
        print("Connecting to MQTT broker...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        print(f"MQTT connection error: {e}")
        thread_data.set_connection_status(False)

# Jalankan thread MQTT hanya sekali
if 'mqtt_started' not in st.session_state:
    threading.Thread(target=mqtt_thread, args=(st.session_state.thread_data,), daemon=True).start()
    st.session_state.mqtt_started = True

# Konfigurasi page
st.set_page_config(
    page_title="Smart Parking System",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS untuk centering
st.markdown("""
<style>
    /* Center the main title */
    .main-title {
        text-align: center;
        font-size: 3rem;
        margin-bottom: 2rem;
    }
    
    /* Center the subtitle */
    .subtitle {
        text-align: center;
        font-size: 1.2rem;
        margin-bottom: 3rem;
        color: #666;
    }
    
    /* Center tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        justify-content: center;
    }
    
    /* Center tab content */
    .tab-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 2rem 0;
    }
    
    /* Style for parking slots */
    .parking-slot {
        background: var(--slot-color);
        color: white;
        padding: 20px;
        text-align: center;
        border-radius: 10px;
        margin: 5px;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Center images */
    .centered-image {
        display: flex;
        justify-content: center;
        margin: 2rem 0;
    }
    
    /* Center refresh button */
    .refresh-button {
        display: flex;
        justify-content: center;
        margin: 2rem 0;
    }
    
    /* Center status messages */
    .status-center {
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Title dengan styling custom
st.markdown('<h1 class="main-title">🚗 Smart Parking System</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Status slot parkir real-time</p>', unsafe_allow_html=True)

# Tombol refresh manual yang di-center
# col1, col2, col3 = st.columns([1, 2, 1])
# with col1:
#     if st.button("🔄 Refresh Status", type="primary") or rerun:
#         st.rerun()
#         rerun = False

# Ambil data terbaru dari thread-safe storage
current_data = st.session_state.thread_data.get_data()

# Tampilkan status parkir
def show_parking(lantai, slots):
    # Container untuk centering content
    container = st.container()
    with container:
        st.markdown(f'<div class="tab-content">', unsafe_allow_html=True)
        st.markdown(f'<h2 style="text-align: center; margin-bottom: 2rem;">Lantai {lantai}</h2>', unsafe_allow_html=True)
        
        # Parking slots dengan layout yang lebih baik
        cols = st.columns(len(slots))
        for i, status in enumerate(slots):
            color = "green" if status == "Kosong" else ("red" if status == "Terisi" else "gray")
            with cols[i]:
                st.markdown(
                    f"""<div style='background:{color};color:white;padding:20px;text-align:center;
                    border-radius:10px;margin:5px;box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                    <strong>Parkiran {i+1}</strong><br><b>{status}</b></div>""", 
                    unsafe_allow_html=True
                )
        st.markdown('</div>', unsafe_allow_html=True)

# Container utama untuk centering tabs
main_container = st.container()
with main_container:
    # Tampilkan data parkir dengan tabs yang di-center
    tab1, tab2 = st.tabs(["🏢 Lantai 1", "🏢 Lantai 2"])
    
    with tab1:
        show_parking(1, current_data["parking_state"]["lantai1"])
        st.markdown("<br>", unsafe_allow_html=True)
        # Center the image
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                st.image("lantai1.png")
            except:
                st.info("📷 Gambar lantai1.png tidak ditemukan")
    
    with tab2:
        show_parking(2, current_data["parking_state"]["lantai2"])
        st.markdown("<br>", unsafe_allow_html=True)
        # Center the image
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                st.image("lantai2.png")
            except:
                st.info("📷 Gambar lantai2.png tidak ditemukan")

# Spacing
st.markdown("<br>", unsafe_allow_html=True)

# Status koneksi dan info yang di-center
mqtt_status = "🟢 Connected" if current_data["mqtt_connected"] else "🔴 Disconnected"
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if current_data["mqtt_connected"]:
        st.success(f"{mqtt_status} to MQTT Broker")
    else:
        st.error(f"{mqtt_status} to MQTT Broker")
    
    st.info("💡 Klik refresh untuk memperbarui status parkiran.")

# Footer spacing
st.markdown("<br><br>", unsafe_allow_html=True)
time.sleep(0.5)
st.rerun()
# Debug information (optional - uncomment if needed)
# with st.expander("🔍 Debug Information"):
#     st.json(current_data["parking_state"])
#     last_update_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_data["last_update"]))
#     st.write(f"Last Update: {last_update_time}")
#     st.write(f"MQTT Status: {'Connected' if current_data['mqtt_connected'] else 'Disconnected'}")
#     st.write(f"Thread Started: {st.session_state.get('mqtt_started', False)}")