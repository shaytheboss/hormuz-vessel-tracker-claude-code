import streamlit as st
import pandas as pd
import sqlite3
import urllib.request
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Hormuz Vessel Tracker",
    layout="wide",
    page_icon="🚢",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
div[data-testid="metric-container"] {
    background: #1a1f2e;
    border: 1px solid #2a2f3e;
    border-radius: 10px;
    padding: 16px 20px;
}
div[data-testid="metric-container"] label { color: #8b92a5 !important; font-size: 13px; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #e8eaf0 !important;
    font-size: 28px !important;
}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 12px; }
</style>
""", unsafe_allow_html=True)

DB_URL = "https://raw.githubusercontent.com/shaytheboss/hormuz-vessel-tracker/data/hormuz_ships.db"
LOCAL_DB = "/tmp/hormuz_ships.db"

@st.cache_data(ttl=1800)  # קאש חצי שעה
def load_data():
    try:
        urllib.request.urlretrieve(DB_URL, LOCAL_DB)
        with sqlite3.connect(LOCAL_DB) as conn:
            df = pd.read_sql("SELECT * FROM ship_logs ORDER BY timestamp DESC", conn)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        st.error(f"שגיאת חיבור: {e}")
        return pd.DataFrame()

# --- Header ---
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown("## 🚢 ניטור מצרי הורמוז")
with col_status:
    st.markdown("")

df = load_data()

if df.empty:
    st.warning("⚠️ עדיין אין נתונים. הרץ את ה-Action לפחות פעם אחת.")
    st.stop()

# --- פילטר זמן ---
st.markdown("**חתך זמן:**")
time_options = {
    "שעה אחרונה": 1,
    "6 שעות": 6,
    "24 שעות": 24,
    "7 ימים": 168,
    "הכל": None
}
selected_range = st.radio(
    "", list(time_options.keys()),
    index=2, horizontal=True, label_visibility="collapsed"
)

hours = time_options[selected_range]
now = datetime.now()
if hours:
    mask = df['timestamp'] >= (now - timedelta(hours=hours))
    filtered = df[mask]
else:
    filtered = df

# --- פילטר סוג ---
all_types = ["הכל"] + sorted(df['ship_type'].dropna().unique().tolist())
ship_type_filter = st.selectbox("סוג ספינה:", all_types, label_visibility="visible")
if ship_type_filter != "הכל":
    filtered = filtered[filtered['ship_type'] == ship_type_filter]

st.divider()

# --- KPIs ---
prev_period = df[df['timestamp'] >= (now - timedelta(hours=(hours or 168) * 2))] \
              .iloc[len(filtered):] if hours else pd.DataFrame()

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("סה\"כ מעברים", len(filtered),
              delta=f"+{len(filtered) - len(prev_period)}" if not prev_period.empty else None)
with k2:
    tankers = filtered['ship_type'].str.contains('Tanker', case=False, na=False).sum()
    st.metric("מכליות נפט", tankers)
with k3:
    if hours and hours > 1:
        per_hour = round(len(filtered) / hours, 1)
        st.metric("ממוצע לשעה", per_hour)
    else:
        st.metric("ממוצע לשעה", "—")
with k4:
    countries = filtered['country'].dropna().nunique()
    st.metric("מדינות שונות", countries)

st.divider()

# --- גרף תנועה לפי שעה ---
if hours and len(filtered) > 0:
    st.subheader("📊 תנועה לפי שעה")
    filtered_copy = filtered.copy()
    filtered_copy['hour'] = filtered_copy['timestamp'].dt.floor('H')
    hourly = filtered_copy.groupby('hour').size().reset_index(name='count')
    st.bar_chart(hourly.set_index('hour')['count'], color="#378ADD")
    st.divider()

# --- מפה ---
map_df = filtered.dropna(subset=['lat', 'lon'])
if not map_df.empty:
    st.subheader("📍 מפה")
    st.map(map_df[['lat', 'lon']], zoom=6)
    st.divider()

# --- טבלה ---
st.subheader("📋 יומן מעברים")
st.dataframe(
    filtered[['timestamp', 'name', 'ship_type', 'country', 'mmsi', 'lat', 'lon']],
    use_container_width=True,
    hide_index=True,
    column_config={
        "timestamp": st.column_config.DatetimeColumn("זמן", format="DD/MM HH:mm"),
        "name": "שם הספינה",
        "ship_type": "סוג",
        "country": "דגל",
        "mmsi": "MMSI",
        "lat": st.column_config.NumberColumn("קו רוחב", format="%.4f"),
        "lon": st.column_config.NumberColumn("קו אורך", format="%.4f"),
    }
)

st.caption(f"סה\"כ {len(df):,} רשומות היסטוריות · מקור: AISstream.io")
