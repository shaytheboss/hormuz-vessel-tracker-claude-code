import websocket, json, sqlite3, os, datetime, threading, time

DB_PATH = "hormuz_ships.db"
DURATION = int(os.getenv("COLLECTION_SECONDS", "300"))

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS ship_logs
        (mmsi TEXT, name TEXT, ship_type TEXT, country TEXT,
         lat REAL, lon REAL, timestamp DATETIME)''')
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON ship_logs(timestamp)")
    conn.commit()
    conn.close()

def on_message(ws, message):
    try:
        msg = json.loads(message)
        meta = msg.get("MetaData", {})
        pos = msg.get("Message", {}).get("PositionReport", {})
        if not (meta and pos and pos.get("Latitude")):
            return
        # חיבור חדש בכל הודעה — בטוח לthread
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO ship_logs VALUES (?,?,?,?,?,?,?)",
            (str(meta.get("MMSI")),
             str(meta.get("ShipName", "Unknown")).strip(),
             str(meta.get("ShipType", "")),
             meta.get("Flag", ""),
             pos.get("Latitude"),
             pos.get("Longitude"),
             datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
        print(f"✓ {meta.get('ShipName', 'Unknown')}")
    except Exception as e:
        print(f"Error: {e}")

def on_open(ws):
    token = os.environ.get("AIS_TOKEN", "")
    if not token:
        print("ERROR: AIS_TOKEN not set")
        ws.close()
        return
    ws.send(json.dumps({
        "APIKey": token,
        "BoundingBoxes": [[[22.0, 50.0], [28.0, 60.0]]],
        "FilterMessageTypes": ["PositionReport"]
    }))
    print("📡 Subscribed to Hormuz AIS feed")

def run():
    init_db()
    before = sqlite3.connect(DB_PATH).execute("SELECT COUNT(*) FROM ship_logs").fetchone()[0]

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

    after = sqlite3.connect(DB_PATH).execute("SELECT COUNT(*) FROM ship_logs").fetchone()[0]
    print(f"✅ Captured {after - before} new vessels (total: {after})")

if __name__ == "__main__":
    run()
