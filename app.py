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

def safe_toast(message, icon=None):
    try:
        st.toast(message, icon=icon)
    except AttributeError:
        st.sidebar.success(f"{icon if icon else ''} {message}")

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
if 'activity_log' not in st.session_state:
    st.session_state.activity_log = []

# Persistent-like DB for the session
if 'user_db' not in st.session_state:
    st.session_state.user_db = {
        "admin@example.com": "admin123",
        "kumarmohit48729@gmail.com": "Mohit@123",
        "yourname@gmail.com": "secure456"
    }

# --- 4. AUTHENTICATION ---
ADMIN_EMAILS = ["admin@example.com", "kumarmohit48729@gmail.com"]

def auth_page():
    st.markdown("<h1 style='text-align: center;'>🔐 Wellness Portal</h1>", unsafe_allow_html=True)
    
    auth_mode = st.radio("Choose Action", ["Login", "Create New Account"], horizontal=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if auth_mode == "Login":
            email = st.text_input("Email Address").lower().strip()
            password = st.text_input("Password", type="password")
            
            if st.button("Login"):
                if email in st.session_state.user_db and st.session_state.user_db[email] == password:
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.activity_log.append(f"🟢 {email} logged in at {datetime.now().strftime('%H:%M:%S')}")
                    safe_rerun()
                else:
                    st.error("❌ Invalid credentials.")
        
        else:
            new_email = st.text_input("New Email Address").lower().strip()
            new_password = st.text_input("Set Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            if st.button("Register Account"):
                if not new_email or not new_password:
                    st.warning("Please fill all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif new_email in st.session_state.user_db:
                    st.error("User already exists.")
                else:
                    st.session_state.user_db[new_email] = new_password
                    st.success("✅ Account created! You can now login.")
                    st.session_state.activity_log.append(f"🆕 New account created: {new_email}")

if not st.session_state.logged_in:
    auth_page()
    st.stop()

user_email = st.session_state.user_email
is_admin = user_email in ADMIN_EMAILS
user_role = "🚀 Admin" if is_admin else "👤 Viewer"

# --- 5. ANALYTICS & MEDICAL LOGIC ---
class BPSensorAnalytics:
    def classify_bp(self, sys, dia):
        if sys >= 180 or dia >= 120: return "Crisis"
        if sys >= 140 or dia >= 90: return "Hypertension S2"
        if 130 <= sys <= 139 or 80 <= dia <= 89: return "Hypertension S1"
        if 120 <= sys <= 129 and dia < 80: return "Elevated"
        return "Normal"

    def get_advice(self, category):
        advice = {
            "Normal": "✅ Healthy range. Maintain a balanced diet and regular exercise.",
            "Elevated": "⚠️ Monitor salt/caffeine. Stress management recommended.",
            "Hypertension S1": "🩺 Consult a doctor. Lifestyle modifications needed.",
            "Hypertension S2": "💊 Medical consultation required. Strict monitoring advised.",
            "Crisis": "🚨 EMERGENCY: Seek immediate medical attention!"
        }
        return advice.get(category, "")

tracker = BPSensorAnalytics()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.header("👤 User Profile")
    st.info(f"**User:** {user_email}\n\n**Role:** {user_role}")
    if st.button("🚪 Log Out"):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.live_df = pd.DataFrame(columns=['Timestamp', 'Systolic', 'Diastolic', 'Pulse', 'Pulse_Pressure', 'Category'])
        safe_rerun()
    
    st.markdown("---")
    st.header("📜 Activity Log")
    with st.expander("View Recent Events", expanded=True):
        for log in reversed(st.session_state.activity_log[-10:]):
            st.caption(log)

    st.markdown("---")
    if is_admin:
        st.header("📡 Hardware Setup")
        mode = st.radio("Select Mode", ["Simulated Live", "Physical Hardware"])
        ports = [p.device for p in serial.tools.list_ports.comports()]
        port = st.selectbox("Select COM Port", ports if ports else ["No Ports Found"])
        baud = st.number_input("Baud Rate", value=9600)
        run_live = st.checkbox("Start Live Monitoring")
    else:
        st.warning("Monitoring restricted to Viewers.")
        run_live = False
        mode = "Simulated Live"
    
    st.markdown("---")
    sidebar_stat_ptr = st.empty()

# --- 7. MAIN UI ---
st.title("🩸 Community Blood Pressure Awareness Tracker")

alert_placeholder = st.empty()

m1, m2, m3, m4, m5 = st.columns(5)
curr_sys = m1.empty()
curr_dia = m2.empty()
curr_pulse = m3.empty()
curr_pp = m4.empty() 
curr_status = m5.empty()

chart_placeholder = st.empty()

st.markdown("---")
col_advice, col_stats = st.columns([1, 2])
with col_advice:
    st.header("💡 Medical Advice")
    advice_ptr = st.empty()

with col_stats:
    st.header("📋 Session Statistics")
    stats_ptr = st.empty()

st.markdown("---")
st.header("📊 Health Trends")
t_col1, t_col2 = st.columns(2)
dist_chart_ptr = t_col1.empty()
pie_chart_ptr = t_col2.empty()

# --- 8. HARDWARE DATA FUNCTION ---
def get_hardware_data(ser_connection):
    try:
        if ser_connection and ser_connection.in_waiting > 0:
            line = ser_connection.readline().decode('utf-8', errors='ignore').strip()
            if line and ',' in line:
                parts = line.split(',')
                if len(parts) >= 3:
                    return int(parts[0]), int(parts[1]), int(parts[2])
    except Exception:
        return None, None, None
    return None, None, None

# --- 9. THE LIVE LOOP ---
if run_live and is_admin:
    ser = None
    if mode == "Physical Hardware":
        try:
            ser = serial.Serial(port, baud, timeout=1)
            st.success(f"Connected to {port}")
            st.session_state.activity_log.append(f"🔌 Hardware connected to {port}")
        except Exception as e:
            st.error(f"Serial Error: {e}")
            run_live = False

    while run_live:
        if mode == "Simulated Live":
            s, d, p = (np.random.randint(110, 160), np.random.randint(70, 100), np.random.randint(65, 95))
        else:
            s, d, p = get_hardware_data(ser)
        
        if s is not None:
            ts = datetime.now().strftime("%H:%M:%S")
            cat = tracker.classify_bp(s, d)
            pp = s - d 

            new_row = pd.DataFrame([[ts, s, d, p, pp, cat]], columns=['Timestamp', 'Systolic', 'Diastolic', 'Pulse', 'Pulse_Pressure', 'Category'])
            st.session_state.live_df = pd.concat([st.session_state.live_df, new_row], ignore_index=True).iloc[-30:]
            df = st.session_state.live_df
            
            if cat == "Crisis":
                st.session_state.activity_log.append(f"🚨 ALERT: Crisis detected at {ts}")

            curr_sys.metric("Systolic", f"{s}")
            curr_dia.metric("Diastolic", f"{d}")
            curr_pulse.metric("Pulse", f"{p} BPM")
            curr_pp.metric("Pulse Pressure", f"{pp}")
            
            if cat == "Crisis":
                curr_status.error("CRISIS")
                alert_placeholder.error("🚨 EMERGENCY: BLOOD PRESSURE IS CRITICALLY HIGH!")
            elif cat.startswith("Hyper"):
                curr_status.warning(cat)
                alert_placeholder.empty()
            else:
                curr_status.success(cat)
                alert_placeholder.empty()

            advice_ptr.info(tracker.get_advice(cat))

            fig, ax = plt.subplots(figsize=(10, 3.5))
            ax.axhspan(90, 120, color='green', alpha=0.1, label="Healthy Zone") 
            sns.lineplot(data=df, x='Timestamp', y='Systolic', marker='o', label="Systolic", ax=ax)
            sns.lineplot(data=df, x='Timestamp', y='Pulse', color='red', label="BPM", ax=ax)
            plt.xticks(rotation=45)
            ax.set_ylim(40, 200)
            chart_placeholder.pyplot(fig)
            plt.close(fig)

            with sidebar_stat_ptr.container():
                st.write("**Session Avg:**")
                st.write(f"Sys: {df['Systolic'].mean():.1f}")
                st.write(f"Pulse: {df['Pulse'].mean():.1f}")

            with dist_chart_ptr.container():
                st.subheader("Pressure Density")
                fig2, ax2 = plt.subplots()
                sns.kdeplot(df['Systolic'], fill=True, label="Systolic", ax=ax2)
                sns.kdeplot(df['Diastolic'], fill=True, label="Diastolic", ax=ax2)
                st.pyplot(fig2)
                plt.close(fig2)

            with pie_chart_ptr.container():
                st.subheader("Category Distribution")
                fig3, ax3 = plt.subplots()
                df['Category'].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=ax3, colors=sns.color_palette("muted"))
                ax3.set_ylabel("")
                st.pyplot(fig3)
                plt.close(fig3)

            stats_df = df[['Systolic', 'Diastolic', 'Pulse', 'Pulse_Pressure']].agg(['mean', 'max', 'min']).T
            stats_ptr.dataframe(stats_df.style.format("{:.1f}").background_gradient(cmap='YlOrRd'))

        time.sleep(1)
    if ser: ser.close() 

else:
    if is_admin:
        st.info("💡 Click 'Start Live Monitoring' in the sidebar to begin.")
    else:
        if not st.session_state.live_df.empty:
            st.success("📢 Live session is active!")
            st.dataframe(st.session_state.live_df.tail(10))
        else:
            st.info("👀 Viewer Mode active. Data will appear when Admin starts monitoring.")