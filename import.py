import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import time
import serial 
import serial.tools.list_ports 

# --- 1. COMPATIBILITY WRAPPERS ---
def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="Community Blood Pressure Awareness Tracker", layout="wide")
sns.set_theme(style="whitegrid")

# --- 3. INITIALIZE SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'live_df' not in st.session_state:
    st.session_state.live_df = pd.DataFrame(
        columns=['Timestamp', 'Systolic', 'Diastolic', 'Pulse', 'Pulse_Pressure', 'Category']
    )
if 'login_history' not in st.session_state:
    st.session_state.login_history = []

# --- 4. AUTHENTICATION ---
ADMIN_EMAILS = ["admin@example.com", "kumarmohit48729@gmail.com"]

def login_user():
    st.markdown("<h1 style='text-align: center;'>🔐 Sign In</h1>", unsafe_allow_html=True)
    with st.container():
        email = st.text_input("Email Address", placeholder="example@gmail.com").lower().strip()
        if st.button("Sign In"):
            if email:
                st.session_state.logged_in = True
                st.session_state.user_email = email
                login_time = datetime.now().strftime("%H:%M:%S")
                role = "🚀 Admin" if email in ADMIN_EMAILS else "👤 Viewer"
                st.session_state.login_history.append({
                    "User": email, 
                    "Time": login_time, 
                    "Role": role
                })
                safe_rerun()
            else:
                st.error("⚠️ Email is required.")

if not st.session_state.logged_in:
    login_user()
    st.stop()

user_email = st.session_state.user_email
is_admin = user_email in ADMIN_EMAILS

# --- 5. ANALYTICS ---
class BPSensorAnalytics:
    def classify_bp(self, sys, dia):
        if sys >= 180 or dia >= 120: return "Crisis"
        if sys >= 140 or dia >= 90: return "Hypertension S2"
        if 130 <= sys <= 139 or 80 <= dia <= 89: return "Hypertension S1"
        if 120 <= sys <= 129 and dia < 80: return "Elevated"
        return "Normal"

tracker = BPSensorAnalytics()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.header("👤 Profile")
    st.write(f"**Current User:** {user_email}")
    st.write(f"**Your Role:** {'🚀 Admin' if is_admin else '👤 Viewer'}")
    
    st.markdown("---")
    st.subheader("👥 User Activity Log")
    if st.session_state.login_history:
        log_df = pd.DataFrame(st.session_state.login_history)
        st.dataframe(log_df) 
    else:
        st.write("No active logs.")
    st.markdown("---")
    
    if st.button("🚪 Sign Out"):
        st.session_state.logged_in = False
        safe_rerun()
    
    st.markdown("---")
    if is_admin:
        st.header("📡 Setup")
        mode = st.radio("Mode", ["Simulated Live", "Physical Hardware"])
        ports = [p.device for p in serial.tools.list_ports.comports()]
        port = st.selectbox("COM Port", ports if ports else ["No Ports"])
        run_live = st.checkbox("Start Live Monitoring")
    else:
        run_live = False

# --- 7. MAIN UI ---
st.title("🩸 Community BP Tracker & Analytics")

# Top Row Metrics
m1, m2, m3, m4 = st.columns(4)
curr_sys = m1.empty()
curr_dia = m2.empty()
curr_pulse = m3.empty()
curr_status = m4.empty()

# Main Trend Chart
st.subheader("📈 Live Pressure & Pulse Trend")
chart_placeholder = st.empty()

st.markdown("---")

# Bottom Analytics Section
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 Category Distribution")
    pie_placeholder = st.empty()

with col_right:
    st.subheader("📋 Session Statistics")
    stats_ptr = st.empty()

st.subheader("📉 Pressure Density (Distribution)")
dist_placeholder = st.empty()

# --- 8. HARDWARE DATA ---
def get_hardware_data(ser_connection):
    try:
        if ser_connection and ser_connection.in_waiting > 0:
            line = ser_connection.readline().decode('utf-8', errors='ignore').strip()
            if ',' in line:
                parts = line.split(',')
                return int(parts[0]), int(parts[1]), int(parts[2])
    except: pass
    return None, None, None

# --- 9. LIVE LOOP ---
if run_live and is_admin:
    ser = None
    if mode == "Physical Hardware":
        try: 
            ser = serial.Serial(port, 9600, timeout=1)
        except Exception as e: 
            st.error(f"Error: {e}")
            run_live = False

    while run_live:
        if mode == "Simulated Live":
            s, d, p = np.random.randint(110, 150), np.random.randint(70, 95), np.random.randint(65, 85)
        else:
            s, d, p = get_hardware_data(ser)
        
        if s:
            ts = datetime.now().strftime("%H:%M:%S")
            cat = tracker.classify_bp(s, d)
            pp = s - d

            new_row = pd.DataFrame([[ts, s, d, p, pp, cat]], columns=['Timestamp', 'Systolic', 'Diastolic', 'Pulse', 'Pulse_Pressure', 'Category'])
            st.session_state.live_df = pd.concat([st.session_state.live_df, new_row], ignore_index=True).iloc[-20:]
            df = st.session_state.live_df

            curr_sys.metric("Systolic", f"{s} mmHg")
            curr_dia.metric("Diastolic", f"{d} mmHg")
            curr_pulse.metric("Pulse", f"{p} BPM")
            curr_status.info(f"Status: {cat}")

            # --- 10. CHARTS & TRENDS (Updated with Pulse Pressure) ---
            # 1. Main Line Chart (Added Pulse Pressure line)
            fig1, ax1 = plt.subplots(figsize=(12, 4))
            sns.lineplot(data=df, x='Timestamp', y='Systolic', marker='o', label='Systolic', ax=ax1)
            sns.lineplot(data=df, x='Timestamp', y='Pulse_Pressure', marker='x', label='Pulse Pressure', color='orange', ax=ax1)
            plt.xticks(rotation=45)
            chart_placeholder.pyplot(fig1)
            plt.close(fig1)

            # 2. Pie Chart (Remains Category based as per medical logic)
            if not df.empty:
                fig2, ax2 = plt.subplots(figsize=(6, 6))
                df['Category'].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=ax2, colors=sns.color_palette("pastel"))
                ax2.set_ylabel("")
                pie_placeholder.pyplot(fig2)
                plt.close(fig2)

            # 3. Distribution Chart (Added Pulse Pressure density)
            fig3, ax3 = plt.subplots(figsize=(10, 3))
            sns.kdeplot(df['Systolic'], fill=True, label="Systolic", ax=ax3, color="red")
            sns.kdeplot(df['Pulse_Pressure'], fill=True, label="Pulse Pressure", ax=ax3, color="orange")
            plt.legend()
            dist_placeholder.pyplot(fig3)
            plt.close(fig3)

            # 4. Stats Table (Added Pulse Pressure stats)
            stats_df = df[['Systolic', 'Diastolic', 'Pulse', 'Pulse_Pressure']].agg(['mean', 'max', 'min']).T
            stats_ptr.dataframe(stats_df.style.format("{:.1f}"))

        time.sleep(1)
    if ser: ser.close()
else:
    st.info("Click on Start Live Monitoring to begin.")