import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import time
import serial 
import serial.tools.list_ports 
import sqlite3

# --- 1. COMPATIBILITY WRAPPERS ---
def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# --- 2. DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect('bp_data.db')
    c = conn.cursor()
    # Table for BP Readings
    c.execute('''CREATE TABLE IF NOT EXISTS readings 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  user_email TEXT,
                  timestamp TEXT, 
                  systolic INTEGER, 
                  diastolic INTEGER, 
                  pulse INTEGER, 
                  pulse_pressure INTEGER, 
                  category TEXT)''')
    
    # NEW: Table for Persistent User Accounts
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT)''')
    
    # Add default admin if it doesn't exist
    c.execute("INSERT OR IGNORE INTO users (email, password) VALUES (?, ?)", 
              ("admin@example.com", "admin123"))
    c.execute("INSERT OR IGNORE INTO users (email, password) VALUES (?, ?)", 
              ("kumarmohit48729@gmail.com", "Mohit@123"))
    
    conn.commit()
    conn.close()

def save_to_db(email, sys, dia, pulse, pp, cat):
    conn = sqlite3.connect('bp_data.db')
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO readings (user_email, timestamp, systolic, diastolic, pulse, pulse_pressure, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (email, ts, sys, dia, pulse, pp, cat))
    conn.commit()
    conn.close()

def get_user_data(email, is_admin):
    conn = sqlite3.connect('bp_data.db')
    if is_admin:
        query = "SELECT * FROM readings ORDER BY id DESC"
        df = pd.read_sql_query(query, conn)
    else:
        query = "SELECT * FROM readings WHERE user_email = ? ORDER BY id DESC"
        df = pd.read_sql_query(query, conn, params=(email,))
    conn.close()
    return df

# NEW: Helper functions for persistent users
def db_register_user(email, password):
    try:
        conn = sqlite3.connect('bp_data.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def db_check_login(email, password):
    conn = sqlite3.connect('bp_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    user = c.fetchone()
    conn.close()
    return user is not None

def db_update_password(email, new_password):
    conn = sqlite3.connect('bp_data.db')
    c = conn.cursor()
    c.execute("UPDATE users SET password = ? WHERE email = ?", (new_password, email))
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    return updated

# Initialize DB on startup
init_db()

# --- 3. PAGE CONFIG ---
st.set_page_config(page_title="Community Blood Pressure Awareness Tracker", layout="wide")
sns.set_theme(style="whitegrid")

# --- 4. INITIALIZE SESSION STATE ---
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

# --- 5. AUTHENTICATION ---
ADMIN_EMAILS = ["admin@example.com", "kumarmohit48729@gmail.com"]

def auth_page():
    st.markdown("<h1 style='text-align: center;'>🔐 Account</h1>", unsafe_allow_html=True)
    auth_mode = st.radio("Choose Action", ["Login", "Create New Account", "Forgot Password"], horizontal=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if auth_mode == "Login":
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email Address").lower().strip()
                password = st.text_input("Password", type="password")
                submit_button = st.form_submit_button("Login")
                
                if submit_button:
                    # UPDATED: Checks database instead of session_state
                    if db_check_login(email, password):
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.session_state.activity_log.append(f"🟢 {email} logged in at {datetime.now().strftime('%H:%M:%S')}")
                        safe_rerun()
                    else:
                        st.error("❌ Invalid credentials.")
        
        elif auth_mode == "Create New Account":
            new_email = st.text_input("New Email Address").lower().strip()
            new_password = st.text_input("Set Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            if st.button("Register Account"):
                if not new_email or not new_password:
                    st.warning("Please fill all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    # UPDATED: Saves to database
                    if db_register_user(new_email, new_password):
                        st.success("✅ Account created! You can now login.")
                        st.session_state.activity_log.append(f"🆕 New account created: {new_email}")
                    else:
                        st.error("❌ User already exists.")
        
        elif auth_mode == "Forgot Password":
            st.subheader("Reset Password")
            reset_email = st.text_input("Registered Email Address").lower().strip()
            new_pwd = st.text_input("New Password", type="password")
            confirm_new_pwd = st.text_input("Confirm New Password", type="password")
            
            if st.button("Update Password"):
                if new_pwd != confirm_new_pwd:
                    st.error("Passwords do not match.")
                elif len(new_pwd) < 6:
                    st.warning("Password should be at least 6 characters.")
                else:
                    # UPDATED: Updates database
                    if db_update_password(reset_email, new_pwd):
                        st.success("✅ Password updated successfully! Please switch to Login.")
                        st.session_state.activity_log.append(f"🔄 Password reset for: {reset_email}")
                    else:
                        st.error("Email not found in our database.")

if not st.session_state.logged_in:
    auth_page()
    st.stop()

user_email = st.session_state.user_email
is_admin = user_email in ADMIN_EMAILS
user_role = "🚀 Admin" if is_admin else "👤 Viewer"

# --- 6. ANALYTICS & MEDICAL LOGIC ---
class BPSensorAnalytics:
    def classify_bp(self, sys, dia):
        # 1. Hypertensive Crisis
        if sys >= 180 or dia >= 120: 
            return "Crisis"
        
        # 2. Hypertension Stage 2
        if sys >= 140 or dia >= 90: 
            return "Hypertension S2"
        
        # 3. Hypertension Stage 1
        if (130 <= sys <= 139) or (80 <= dia <= 89): 
            return "Hypertension S1"
        
        # 4. Elevated (Systolic is 120-129 AND Diastolic is less than 80)
        if (120 <= sys <= 129) and dia < 80: 
            return "Elevated"
        
        # 5. Normal (Systolic less than 120 AND Diastolic less than 80)
        if sys < 120 and dia < 80:
            return "Normal"
            
        # Fallback for borderline cases
        return "Normal"

    def get_advice(self, category):
        advice = {
            "Normal": "✅ Healthy range. Maintain a balanced diet, keep hydrated, and stay active.",
            "Elevated": "⚠️ Your blood pressure is a bit high. It’s time to control salt intake and manage stress.",
            "Hypertension S1": "🩺 Lifestyle changes are needed. Please consult a doctor to discuss your heart health.",
            "Hypertension S2": "💊 High priority. Medical consultation and possible medication are required. Monitor strictly.",
            "Crisis": "🚨 EMERGENCY: This is a critical reading. Seek immediate medical attention or call emergency services!"
        }
        return advice.get(category, "")

tracker = BPSensorAnalytics()

# --- 7. SIDEBAR ---
with st.sidebar:
    st.header("👤 User Profile")
    st.info(f"**User:** {user_email}\n\n**Role:** {user_role}")
    
    # --- INDIVIDUAL PATIENT CHECK (LIVE MONITORING FOR VIEWERS) ---
    st.markdown("---")
    st.header("🏥 BP Reading")
    with st.expander("Record Current Reading", expanded=not is_admin):
        check_sys = st.number_input("Systolic (Top)", value=120, min_value=50, max_value=250)
        check_dia = st.number_input("Diastolic (Bottom)", value=80, min_value=30, max_value=150)
        
        if st.button("Update My Dashboard"):
            res_cat = tracker.classify_bp(check_sys, check_dia)
            ts = datetime.now().strftime("%H:%M:%S")
            p_sim = np.random.randint(65, 95)
            pp = check_sys - check_dia
            
            # Save to Database under Viewer's email
            save_to_db(user_email, check_sys, check_dia, p_sim, pp, res_cat)
            
            # Update the UI Dataframe
            new_patient_row = pd.DataFrame([[ts, check_sys, check_dia, p_sim, pp, res_cat]], 
                                           columns=['Timestamp', 'Systolic', 'Diastolic', 'Pulse', 'Pulse_Pressure', 'Category'])
            st.session_state.live_df = pd.concat([st.session_state.live_df, new_patient_row], ignore_index=True).iloc[-30:]
            st.session_state.activity_log.append(f"📝 {user_email} updated reading: {check_sys}/{check_dia}")
            safe_rerun()

    # --- AWARENESS HUB ---
    st.markdown("---")
    st.header("📢 Awareness Hub")
    with st.expander("Learn About Blood Pressure", expanded=False):
        st.write("Hypertension occurs when the force of blood is too high.")
        st.markdown("* 🧂 **Salt:** Excess sodium holds fluid.")
        st.markdown("* 🏃 **Inactivity:** Increases heart strain.")

    st.markdown("---")
    st.header("📜 Activity Log")
    with st.expander("View Recent Events", expanded=False):
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
        run_live = False
        mode = "Simulated Live"
        follow_live = st.checkbox("Follow Live Broadcast", value=True)
    
    sidebar_stat_ptr = st.empty()

    # --- LOGOUT ---
    st.markdown("---")
    if st.button("🚪 Log Out"):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.live_df = pd.DataFrame(columns=['Timestamp', 'Systolic', 'Diastolic', 'Pulse', 'Pulse_Pressure', 'Category'])
        safe_rerun()

# --- 8. MAIN UI ---
st.title("🩸 Community Blood Pressure Awareness Tracker")

tab_dash, tab_db = st.tabs(["📺 Dashboard", "📂 Historical Data"])

with tab_dash:
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

    st.markdown("---")
    st.header("📢 Awareness Hub: Understanding Your Numbers")
    awareness_display = st.empty()

with tab_db:
    st.header("📊 History Explorer")
    db_data = get_user_data(user_email, is_admin)
    if not db_data.empty:
        st.dataframe(db_data)
        csv = db_data.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Data as CSV", data=csv, file_name=f"bp_history_{user_email}.csv", mime="text/csv")
    else:
        st.info("No monitoring records found.")

# --- HARDWARE DATA FUNCTION ---
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

# --- FUNCTION TO RENDER DATA ---
def render_dashboard(df):
    if not df.empty:
        latest = df.iloc[-1]
        s, d, p, pp, cat = latest['Systolic'], latest['Diastolic'], latest['Pulse'], latest['Pulse_Pressure'], latest['Category']
        
        curr_sys.metric("Systolic", f"{s}")
        curr_dia.metric("Diastolic", f"{d}")
        curr_pulse.metric("Pulse", f"{p} BPM")
        curr_pp.metric("Pulse Pressure", f"{pp}")
        
        if cat == "Crisis":
            curr_status.error("CRISIS")
            alert_placeholder.error("🚨 EMERGENCY: Seek help now!")
        elif cat.startswith("Hyper"):
            curr_status.warning(cat)
            alert_placeholder.empty()
        else:
            curr_status.success(cat)
            alert_placeholder.empty()

        advice_ptr.info(tracker.get_advice(cat))

        with awareness_display.container():
            aw1, aw2 = st.columns(2)
            with aw1:
                st.subheader(f"Status: {cat}")
                st.write(f"Your reading of **{s}/{d}** is classified as **{cat}**.")
                if cat == "Normal":
                    st.write("Excellent! Your blood pressure is in a range associated with low risk for cardiovascular events.")
                elif cat == "Elevated":
                    st.write("Take note: While not yet high BP, you are at risk. Reduce sodium and stay active.")
                else:
                    st.write("High blood pressure strains the arteries. Consult a healthcare provider for a management plan.")
            with aw2:
                st.subheader("🚨 Global Risks")
                st.write("Did you know? High BP is often a 'Silent Killer'.")
                st.error("Risks: Stroke, Heart Attack, Kidney Failure.")

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

# --- THE LIVE LOOP ---
if run_live and is_admin:
    ser = None
    if mode == "Physical Hardware":
        try:
            ser = serial.Serial(port, baud, timeout=1)
            st.success(f"Connected to {port}")
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
            save_to_db(user_email, s, d, p, pp, cat)
            new_row = pd.DataFrame([[ts, s, d, p, pp, cat]], columns=['Timestamp', 'Systolic', 'Diastolic', 'Pulse', 'Pulse_Pressure', 'Category'])
            st.session_state.live_df = pd.concat([st.session_state.live_df, new_row], ignore_index=True).iloc[-30:]
            render_dashboard(st.session_state.live_df)
        time.sleep(1)
    if ser: ser.close() 

else:
    render_dashboard(st.session_state.live_df)
    if not is_admin and follow_live and not st.session_state.live_df.empty:
        time.sleep(2)
        st.experimental_rerun()
