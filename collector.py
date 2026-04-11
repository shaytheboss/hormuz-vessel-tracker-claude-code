import websocket, json, sqlite3, os, datetime, threading, time

DB_PATH = "hormuz_ships.db"
DURATION = int(os.getenv("COLLECTION_SECONDS", "300"))

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS ship_logs
        (mmsi TEXT, name TEXT, lat REAL, lon REAL, timestamp DATETIME,
         cog REAL, sog REAL, heading REAL, nav_status INTEGER, rot REAL)''')
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON ship_logs(timestamp)")
    conn.commit()
    conn.close()

def parse_timestamp(ts_str):
    try:
        # מנקה את הפורמט: "2026-04-11 08:37:43.328790216 +0000 UTC"
        clean = ts_str.replace(" +0000 UTC", "").strip()
        # מקצר נאנו-שניות ל-מיקרו-שניות (6 ספרות)
        if "." in clean:
            parts = clean.split(".")
            clean = parts[0] + "." + parts[1][:6]
        return datetime.datetime.strptime(clean, "%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def on_message(ws, message):
    try:
        msg = json.loads(message)
        meta = msg.get("MetaData", {})
        pos = msg.get("Message", {}).get("PositionReport", {})
        if not (meta and pos and pos.get("Latitude")):
            return
        ts = parse_timestamp(meta.get("time_utc", ""))
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """INSERT INTO ship_logs
               (mmsi, name, lat, lon, timestamp, cog, sog, heading, nav_status, rot)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (str(meta.get("MMSI")),
             str(meta.get("ShipName", "Unknown")).strip(),
             pos.get("Latitude"),
             pos.get("Longitude"),
             ts,
             pos.get("Cog"),
             pos.get("Sog"),
             pos.get("TrueHeading"),
             pos.get("NavigationalStatus"),
             pos.get("RateOfTurn"))
        )
        conn.commit()
        conn.close()
        print(f"✓ {str(meta.get('ShipName')).strip()} | {pos.get('Sog')}kn | heading={pos.get('TrueHeading')}°")
    except Exception as e:
        print(f"Error: {e}")

def on_open(ws):
    token = os.environ.get("AIS_TOKEN", "")
    print(f"TOKEN LENGTH: {len(token)}")
    if not token:
        print("ERROR: AIS_TOKEN not set")
        ws.close()
        return
    ws.send(json.dumps({
        "APIKey": token,
        "BoundingBoxes": [[[24.0, 55.0], [27.5, 60.0]]],
        "FilterMessageTypes": ["PositionReport"]
    }))
    print("📡 Subscribed to Hormuz AIS feed")

def run():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    before = conn.execute("SELECT COUNT(*) FROM ship_logs").fetchone()[0]
    conn.close()

    ws = websocket.WebSocketApp(
        "wss://stream.aisstream.io/v0/stream",
        on_open=on_open,
        on_message=on_message,
        on_error=lambda ws, e: print(f"WS Error: {e}"),
        on_close=lambda ws, c, m: print("Connection closed")
    )

    t = threading.Thread(target=ws.run_forever, daemon=True)
    t.start()
    time.sleep(DURATION)
    ws.close()

    conn = sqlite3.connect(DB_PATH)
    after = conn.execute("SELECT COUNT(*) FROM ship_logs").fetchone()[0]
    conn.close()
    print(f"✅ Captured {after - before} new vessels (total: {after})")

if __name__ == "__main__":
    run()
