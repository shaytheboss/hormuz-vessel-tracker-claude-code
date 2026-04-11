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

[data-testid="stAppViewContainer"] {
    direction: rtl;
}

.block-container {
    padding: 2rem 2rem 3rem 2rem;
    max-width: 1400px;
}

/* כותרת */
.header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.5rem;
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    border-radius: 16px;
    margin-bottom: 1.5rem;
    direction: rtl;
}
.header-title {
    font-size: 24px;
    font-weight: 700;
    color: white;
    margin: 0;
}
.header-sub {
    font-size: 13px;
    color: rgba(255,255,255,0.6);
    margin: 4px 0 0 0;
}
.live-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(16, 185, 129, 0.2);
    border: 1px solid rgba(16, 185, 129, 0.4);
    color: #10b981;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
}
.live-dot {
    width: 7px;
    height: 7px;
    background: #10b981;
    border-radius: 50%;
    animation: blink 1.5s infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }

/* KPI cards */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 1.5rem;
    direction: rtl;
}
.kpi-card {
    background: var(--background-color, #1a1f2e);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 18px 20px;
    text-align: right;
    direction: rtl;
}
.kpi-icon {
    font-size: 22px;
    margin-bottom: 8px;
    display: block;
}
.kpi-label {
    font-size: 12px;
    color: rgba(255,255,255,0.45);
    margin-bottom: 4px;
    font-weight: 400;
}
.kpi-value {
    font-size: 32px;
    font-weight: 700;
    color: white;
    line-height: 1;
}
.kpi-sub {
    font-size: 11px;
    margin-top: 4px;
}
.kpi-sub.up { color: #10b981; }
.kpi-sub.neutral { color: rgba(255,255,255,0.4); }

/* פילטרים */
.filter-bar {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 1.5rem;
    direction: rtl;
}

/* כרטיסי ספינה */
.ship-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    direction: rtl;
    transition: border-color 0.2s;
}
.ship-card:hover {
    border-color: rgba(255,255,255,0.2);
}
.ship-name {
    font-size: 15px;
    font-weight: 600;
    color: white;
    margin-bottom: 6px;
}
.ship-meta {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    direction: rtl;
}
.ship-tag {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 500;
}
.tag-tanker { background: rgba(251,191,36,0.15); color: #fbbf24; }
.tag-cargo  { background: rgba(16,185,129,0.15);  color: #10b981; }
.tag-mil    { background: rgba(239,68,68,0.15);   color: #ef4444; }
.tag-other  { background: rgba(148,163,184,0.15); color: #94a3b8; }
.ship-coord { font-size: 11px; color: rgba(255,255,255,0.35); font-family: monospace; }

/* divider */
hr { border-color: rgba(255,255,255,0.07) !important; }

/* Streamlit overrides */
div[data-testid="metric-container"] { display: none; }
.stRadio > div { direction: rtl; }
.stRadio label { direction: rtl; }
[data-testid="stDataFrame"] { direction: rtl; }
h1,h2,h3 { direction: rtl; text-align: right; }
p { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

# --- נתונים ---
DB_URL = "https://raw.githubusercontent.com/shaytheboss/hormuz-vessel-tracker-claude-code/data/hormuz_ships.db"
LOCAL_DB = "/tmp/hormuz_ships.db"

SHIP_TYPE_MAP = {
    "70": "מטען כללי", "71": "מטען כללי", "72": "מטען כללי",
    "73": "מטען כללי", "74": "מטען כללי", "75": "מטען כללי",
    "79": "מטען כללי", "80": "מכלית נפט", "81": "מכלית נפט",
    "82": "מכלית נפט", "83": "מכלית נפט", "84": "מכלית נפט",
    "85": "מכלית נפט", "89": "מכלית נפט", "35": "צבאית",
    "36": "צבאית", "50": "טייס נמל", "60": "נוסעים",
    "69": "נוסעים", "30": "דייג",
}

FLAG_MAP = {
    "IR": "🇮🇷 איראן", "AE": "🇦🇪 איחוד האמירויות",
    "SA": "🇸🇦 ערב הסעודית", "OM": "🇴🇲 עומאן",
    "KW": "🇰🇼 כווית", "QA": "🇶🇦 קטאר",
    "BH": "🇧🇭 בחריין", "PK": "🇵🇰 פקיסטן",
    "IN": "🇮🇳 הודו", "CN": "🇨🇳 סין",
    "PA": "🇵🇦 פנמה", "MH": "🇲🇭 איי מרשל",
    "LR": "🇱🇷 ליבריה", "SG": "🇸🇬 סינגפור",
    "MT": "🇲🇹 מלטה", "BS": "🇧🇸 בהאמאס",
    "CY": "🇨🇾 קפריסין", "GR": "🇬🇷 יוון",
    "NO": "🇳🇴 נורווגיה", "GB": "🇬🇧 בריטניה",
}

def get_ship_type_label(t):
    return SHIP_TYPE_MAP.get(str(t), f"אחר ({t})" if t else "לא ידוע")

def get_type_class(t):
    label = get_ship_type_label(t)
    if "מכלית" in label: return "tag-tanker"
    if "מטען" in label: return "tag-cargo"
    if "צבאית" in label: return "tag-mil"
    return "tag-other"

def get_flag(code):
    return FLAG_MAP.get(str(code).strip().upper(), f"🏳️ {code}" if code else "לא ידוע")

@st.cache_data(ttl=1800)
def load_data():
    try:
        urllib.request.urlretrieve(DB_URL, LOCAL_DB)
        with sqlite3.connect(LOCAL_DB) as conn:
            df = pd.read_sql("SELECT * FROM ship_logs ORDER BY timestamp DESC", conn)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        return pd.DataFrame()

df = load_data()

# --- Header ---
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

# --- פילטר זמן ---
st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    time_options = {"שעה אחרונה": 1, "6 שעות": 6, "24 שעות": 24, "7 ימים": 168, "הכל": None}
    selected_range = st.radio("חתך זמן", list(time_options.keys()), index=2, horizontal=True)
with col_f2:
    type_filter = st.selectbox("סוג ספינה", ["הכל", "מכלית נפט", "מטען כללי", "צבאית", "נוסעים"])
st.markdown('</div>', unsafe_allow_html=True)

hours = time_options[selected_range]
now = datetime.utcnow()
filtered = df.copy()
if hours:
    filtered = filtered[filtered['timestamp'] >= (now - timedelta(hours=hours))]
if type_filter != "הכל":
    filtered = filtered[filtered['ship_type'].apply(get_ship_type_label).str.contains(type_filter)]

# --- KPIs ---
tankers = filtered['ship_type'].apply(get_ship_type_label).str.contains("מכלית").sum()
per_hour = round(len(filtered) / hours, 1) if hours else "—"
countries = filtered['country'].dropna().nunique()

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <span class="kpi-icon">🚢</span>
    <div class="kpi-label">סה"כ מעברים</div>
    <div class="kpi-value">{len(filtered)}</div>
    <div class="kpi-sub neutral">מתוך {len(df):,} היסטוריים</div>
  </div>
  <div class="kpi-card">
    <span class="kpi-icon">🛢️</span>
    <div class="kpi-label">מכליות נפט</div>
    <div class="kpi-value">{tankers}</div>
    <div class="kpi-sub up">{round(tankers/len(filtered)*100) if len(filtered) else 0}% מהתנועה</div>
  </div>
  <div class="kpi-card">
    <span class="kpi-icon">⏱️</span>
    <div class="kpi-label">ממוצע לשעה</div>
    <div class="kpi-value">{per_hour}</div>
    <div class="kpi-sub neutral">בחתך הנבחר</div>
  </div>
  <div class="kpi-card">
    <span class="kpi-icon">🌍</span>
    <div class="kpi-label">מדינות שונות</div>
    <div class="kpi-value">{countries}</div>
    <div class="kpi-sub neutral">דגלים ברשומות</div>
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
st.markdown(f"#### 📋 יומן מעברים — {len(filtered)} רשומות")

for _, row in filtered.head(50).iterrows():
    type_label = get_ship_type_label(row.get('ship_type'))
    type_class = get_type_class(row.get('ship_type'))
    flag = get_flag(row.get('country'))
    ts = row['timestamp'].strftime("%d/%m %H:%M")
    lat = f"{row['lat']:.4f}°N" if pd.notna(row.get('lat')) else "—"
    lon = f"{row['lon']:.4f}°E" if pd.notna(row.get('lon')) else "—"
    mmsi = row.get('mmsi', '—')

    st.markdown(f"""
    <div class="ship-card">
      <div class="ship-name">{row.get('name', 'לא ידוע')}</div>
      <div class="ship-meta">
        <span class="ship-tag {type_class}">{type_label}</span>
        <span style="font-size:13px;color:rgba(255,255,255,0.7)">{flag}</span>
        <span style="font-size:12px;color:rgba(255,255,255,0.4)">🕐 {ts}</span>
        <span class="ship-coord">📍 {lat}, {lon}</span>
        <span style="font-size:11px;color:rgba(255,255,255,0.25)">MMSI: {mmsi}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

st.caption(f"מציג 50 רשומות אחרונות מתוך {len(filtered):,} · Hormuz Vessel Tracker")
