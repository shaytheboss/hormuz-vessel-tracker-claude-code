import streamlit as st
import pandas as pd
import sqlite3
import urllib.request
from datetime import datetime, timedelta

st.set_page_config(
    page_title="מצרי הורמוז | ניטור ספינות",
    layout="wide",
    page_icon="🚢",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Heebo', sans-serif !important;
    direction: rtl;
}
.block-container { padding: 2rem 2rem 3rem 2rem; max-width: 1400px; }

.header-bar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1.2rem 1.8rem;
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    border-radius: 16px; margin-bottom: 1.5rem; direction: rtl;
}
.header-title { font-size: 24px; font-weight: 700; color: white; margin: 0; }
.header-sub { font-size: 13px; color: rgba(255,255,255,0.55); margin: 4px 0 0 0; }
.live-badge {
    display: flex; align-items: center; gap: 6px;
    background: rgba(16,185,129,0.2); border: 1px solid rgba(16,185,129,0.4);
    color: #10b981; padding: 6px 14px; border-radius: 20px;
    font-size: 13px; font-weight: 500;
}
.live-dot {
    width: 7px; height: 7px; background: #10b981;
    border-radius: 50%; animation: blink 1.5s infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }

.kpi-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 12px; margin-bottom: 1.5rem; direction: rtl;
}
.kpi-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px; padding: 18px 20px; text-align: right;
}
.kpi-icon { font-size: 22px; margin-bottom: 8px; display: block; }
.kpi-label { font-size: 12px; color: rgba(255,255,255,0.45); margin-bottom: 4px; }
.kpi-value { font-size: 32px; font-weight: 700; color: white; line-height: 1; }
.kpi-sub { font-size: 11px; margin-top: 4px; }
.kpi-sub.up { color: #10b981; }
.kpi-sub.neutral { color: rgba(255,255,255,0.35); }

.ship-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; padding: 14px 18px; margin-bottom: 10px;
    direction: rtl;
}
.ship-name { font-size: 15px; font-weight: 600; color: white; margin-bottom: 8px; }
.ship-meta { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.ship-tag { font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 500; }
.tag-moving  { background: rgba(59,130,246,0.2);  color: #60a5fa; }
.tag-anchor  { background: rgba(251,191,36,0.2);  color: #fbbf24; }
.tag-moored  { background: rgba(148,163,184,0.2); color: #94a3b8; }
.tag-other   { background: rgba(148,163,184,0.15); color: #94a3b8; }
.ship-detail { font-size: 12px; color: rgba(255,255,255,0.5); }
.ship-coord  { font-size: 11px; color: rgba(255,255,255,0.3); font-family: monospace; }

hr { border-color: rgba(255,255,255,0.07) !important; }
h1,h2,h3,h4 { direction: rtl; text-align: right; }
p { direction: rtl; }
.stRadio > div { direction: rtl; }
</style>
""", unsafe_allow_html=True)

NAV_STATUS_MAP = {
    0: ("בתנועה", "tag-moving"),
    1: ("עוגן", "tag-anchor"),
    5: ("קשור לרציף", "tag-moored"),
    2: ("ללא פיקוד", "tag-other"),
    3: ("מוגבל בתמרון", "tag-other"),
    6: ("על שרטון", "tag-other"),
    7: ("דיג", "tag-other"),
    8: ("שייט", "tag-moving"),
    15: ("לא מוגדר", "tag-other"),
}

DB_URL = "https://raw.githubusercontent.com/shaytheboss/hormuz-vessel-tracker-claude-code/data/hormuz_ships.db"
LOCAL_DB = "/tmp/hormuz_ships.db"

@st.cache_data(ttl=1800)
def load_data():
    try:
        urllib.request.urlretrieve(DB_URL, LOCAL_DB)
        with sqlite3.connect(LOCAL_DB) as conn:
            df = pd.read_sql("SELECT * FROM ship_logs ORDER BY timestamp DESC", conn)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        st.error(f"שגיאה: {e}")
        return pd.DataFrame()

df = load_data()

last_update = df['timestamp'].iloc[0].strftime("%d/%m/%Y %H:%M") if not df.empty else "—"
st.markdown(f"""
<div class="header-bar">
  <div>
    <p class="header-title">🚢 ניטור מצרי הורמוז</p>
    <p class="header-sub">עדכון אחרון: {last_update} UTC · מקור: AISstream.io</p>
  </div>
  <div class="live-badge"><div class="live-dot"></div>פעיל</div>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ עדיין אין נתונים. הרץ את ה-Action לפחות פעם אחת.")
    st.stop()

# --- פילטרים ---
col_f1, col_f2 = st.columns([3, 1])
with col_f1:
    time_options = {"שעה אחרונה": 1, "6 שעות": 6, "24 שעות": 24, "7 ימים": 168, "הכל": None}
    selected_range = st.radio("חתך זמן", list(time_options.keys()), index=2, horizontal=True)
with col_f2:
    status_filter = st.selectbox("סטטוס", ["הכל", "בתנועה", "עוגן", "קשור לרציף"])

hours = time_options[selected_range]
now = datetime.utcnow()
filtered = df.copy()
if hours:
    filtered = filtered[filtered['timestamp'] >= (now - timedelta(hours=hours))]
if status_filter != "הכל":
    status_codes = [k for k, v in NAV_STATUS_MAP.items() if v[0] == status_filter]
    filtered = filtered[filtered['nav_status'].isin(status_codes)]

# --- KPIs ---
moving = filtered[filtered['nav_status'] == 0]
avg_speed = round(filtered['sog'].dropna().mean(), 1) if not filtered['sog'].dropna().empty else 0
per_hour = round(len(filtered) / hours, 1) if hours else "—"
unique_vessels = filtered['mmsi'].nunique()

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <span class="kpi-icon">🚢</span>
    <div class="kpi-label">סה"כ רשומות</div>
    <div class="kpi-value">{len(filtered)}</div>
    <div class="kpi-sub neutral">מתוך {len(df):,} היסטוריים</div>
  </div>
  <div class="kpi-card">
    <span class="kpi-icon">⚓</span>
    <div class="kpi-label">ספינות ייחודיות</div>
    <div class="kpi-value">{unique_vessels}</div>
    <div class="kpi-sub neutral">MMSI שונים</div>
  </div>
  <div class="kpi-card">
    <span class="kpi-icon">💨</span>
    <div class="kpi-label">מהירות ממוצעת</div>
    <div class="kpi-value">{avg_speed}</div>
    <div class="kpi-sub neutral">קשר (knots)</div>
  </div>
  <div class="kpi-card">
    <span class="kpi-icon">⏱️</span>
    <div class="kpi-label">ממוצע לשעה</div>
    <div class="kpi-value">{per_hour}</div>
    <div class="kpi-sub neutral">רשומות בחתך הנבחר</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# --- גרף + מפה ---
col_chart, col_map = st.columns([1, 1])
with col_chart:
    st.markdown("#### 📊 תנועה לפי שעה")
    if hours and len(filtered) > 0:
        fc = filtered.copy()
        fc['hour'] = fc['timestamp'].dt.floor('h')
        hourly = fc.groupby('hour').size().reset_index(name='ספינות')
        st.bar_chart(hourly.set_index('hour')['ספינות'], color="#3b82f6")
    else:
        st.info("אין מספיק נתונים לגרף")

with col_map:
    st.markdown("#### 📍 מפת תנועה")
    map_df = filtered.dropna(subset=['lat', 'lon'])
    if not map_df.empty:
        st.map(map_df[['lat', 'lon']], zoom=6)
    else:
        st.info("אין קואורדינטות להצגה")

st.divider()

# --- כרטיסי ספינות ---
st.markdown(f"#### 📋 יומן מעברים — {len(filtered):,} רשומות")

for _, row in filtered.head(50).iterrows():
    nav = int(row['nav_status']) if pd.notna(row.get('nav_status')) else 15
    status_label, status_class = NAV_STATUS_MAP.get(nav, ("לא ידוע", "tag-other"))
    ts = row['timestamp'].strftime("%d/%m %H:%M")
    lat = f"{row['lat']:.4f}°N" if pd.notna(row.get('lat')) else "—"
    lon = f"{row['lon']:.4f}°E" if pd.notna(row.get('lon')) else "—"
    sog = f"{row['sog']:.1f} קשר" if pd.notna(row.get('sog')) else "—"
    heading = f"{int(row['heading'])}°" if pd.notna(row.get('heading')) and row['heading'] != 511 else "—"
    cog = f"{row['cog']:.1f}°" if pd.notna(row.get('cog')) else "—"

    st.markdown(f"""
    <div class="ship-card">
      <div class="ship-name">{row.get('name', 'לא ידוע')}</div>
      <div class="ship-meta">
        <span class="ship-tag {status_class}">{status_label}</span>
        <span class="ship-detail">💨 {sog}</span>
        <span class="ship-detail">🧭 כיוון: {heading} | מסלול: {cog}</span>
        <span class="ship-detail">🕐 {ts}</span>
        <span class="ship-coord">📍 {lat}, {lon}</span>
        <span class="ship-coord">MMSI: {row.get('mmsi', '—')}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

st.caption(f"מציג 50 רשומות אחרונות מתוך {len(filtered):,} · Hormuz Vessel Tracker")
