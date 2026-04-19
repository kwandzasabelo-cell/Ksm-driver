"""
KSM Smart Freight Solutions — Driver Terminal v4.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Secure field app integrated with the KSM fleet system.

Run alongside the main app:
    streamlit run yizo.py            --server.port 8501   (Main System)
    streamlit run driver_app.py      --server.port 8502   (Driver Terminal)
"""

import streamlit as st
import sqlite3
import math
import os
from datetime import datetime, date

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="KSM Driver Terminal",
    page_icon="🚛",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# =============================================================================
# CONSTANTS
# =============================================================================
DB_PATH              = "fleet.db"
FUEL_PRICE_DEFAULT   = 19.85
MAINTENANCE_PER_KM   = 1.5
BORDER_COST_EACH     = 200
MAX_PAYLOAD_KG       = 25_000
FUEL_BASE_L_PER_100  = 28.0
SERVICE_INTERVAL_KM  = 15_000

LOCATIONS = [
    "Mbabane", "Manzini", "Matsapha", "Piggs Peak",
    "Lomahasha", "Lavumisa", "Johannesburg", "Durban",
    "Maputo", "Nelspruit",
]

LOCATION_COORDS = {
    "Mbabane":      (-26.318, 31.135),
    "Manzini":      (-26.485, 31.360),
    "Matsapha":     (-26.516, 31.300),
    "Piggs Peak":   (-25.959, 31.250),
    "Lomahasha":    (-25.933, 31.983),
    "Lavumisa":     (-27.310, 31.888),
    "Johannesburg": (-26.204, 28.047),
    "Durban":       (-29.858, 31.021),
    "Maputo":       (-25.969, 32.573),
    "Nelspruit":    (-25.466, 30.970),
}

EVENT_TYPES = [
    "Near miss", "Vehicle breakdown", "Tyre blowout / puncture",
    "Engine overheating", "Cargo damage",
    "Border / weigh-bridge delay", "Road closure / accident scene",
    "Speeding warning", "Fatigue stop",
    "Theft or security incident", "Other",
]

# Credentials: driver_id -> PIN
DRIVER_PINS = {
    "KSM-DRV-0001": "1234",
    "KSM-DRV-0002": "5678",
    "KSM-DRV-0003": "9012",
    "KSM-DRV-0004": "3456",
    "KSM-DRV-0005": "7890",
    "FLEET-MGR":     "ksm2025",   # fleet manager override
}

# =============================================================================
# STYLING
# =============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
.stApp {
    background:
        linear-gradient(135deg,rgba(10,15,40,0.97) 0%,rgba(15,30,70,0.95) 35%,
            rgba(20,50,100,0.93) 65%,rgba(10,20,55,0.97) 100%),
        url('https://images.unsplash.com/photo-1519003722824-194d4455a60c?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80');
    background-size:cover;background-attachment:fixed;background-position:center;
    font-family:'Sora',sans-serif;
}
.main .block-container {
    background:rgba(255,255,255,0.04);backdrop-filter:blur(12px);
    border-radius:16px;border:1px solid rgba(255,255,255,0.08);
    padding:1.5rem 1.8rem;max-width:820px;
}
.stApp,.stApp p,.stApp label,.stApp div,.stApp span,.stApp h1,.stApp h2,.stApp h3 {
    color:#e2e8f0 !important;font-family:'Sora',sans-serif !important;
}
h1{color:#60a5fa !important;letter-spacing:-0.5px;}
h2{color:#93c5fd !important;}h3{color:#bfdbfe !important;}
[data-testid="stMetric"]{background:linear-gradient(135deg,rgba(30,58,138,0.7),rgba(37,99,235,0.5));padding:14px;border-radius:12px;border:1px solid rgba(96,165,250,0.35);box-shadow:0 4px 16px rgba(0,0,0,0.4);backdrop-filter:blur(10px);}
[data-testid="stMetricLabel"]{color:#93c5fd !important;font-weight:700 !important;font-size:0.72rem !important;letter-spacing:0.08em !important;}
[data-testid="stMetricValue"]{color:#ffffff !important;font-size:1.35rem !important;font-weight:800 !important;}
.stTextInput>div>div>input,.stNumberInput>div>div>input,.stTextArea>div>textarea,.stSelectbox>div>div{background:rgba(15,23,42,0.75) !important;border:1px solid rgba(96,165,250,0.4) !important;border-radius:8px !important;color:#e2e8f0 !important;backdrop-filter:blur(6px);font-family:'Sora',sans-serif !important;font-size:0.88rem !important;}
.stSelectbox>div>div>div{color:#e2e8f0 !important;}
.stButton>button{background:linear-gradient(135deg,#1d4ed8,#2563eb) !important;color:white !important;border:1px solid rgba(96,165,250,0.4) !important;border-radius:10px !important;font-weight:700 !important;font-family:'Sora',sans-serif !important;font-size:0.85rem !important;transition:all 0.2s ease;box-shadow:0 4px 12px rgba(37,99,235,0.4);width:100%;padding:0.55rem 1rem !important;}
.stButton>button:hover{background:linear-gradient(135deg,#2563eb,#3b82f6) !important;box-shadow:0 6px 20px rgba(59,130,246,0.5);transform:translateY(-1px);}
[data-testid="stFormSubmitButton"]>button{background:linear-gradient(135deg,#059669,#10b981) !important;box-shadow:0 4px 14px rgba(16,185,129,0.45) !important;width:100%;font-size:0.9rem !important;padding:0.65rem 1rem !important;}
[data-testid="stFormSubmitButton"]>button:hover{background:linear-gradient(135deg,#10b981,#34d399) !important;transform:translateY(-1px);}
.stTabs [data-baseweb="tab-list"]{background:rgba(15,23,42,0.6) !important;border-radius:10px !important;padding:4px !important;border:1px solid rgba(96,165,250,0.2);gap:2px;}
.stTabs [data-baseweb="tab"]{color:#94a3b8 !important;border-radius:8px !important;font-weight:600 !important;font-size:0.78rem !important;font-family:'Sora',sans-serif !important;padding:6px 10px !important;}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#1e3a8a,#2563eb) !important;color:white !important;}
.stSuccess{background:rgba(6,78,59,0.6) !important;border-color:#10b981 !important;color:#a7f3d0 !important;border-radius:10px !important;}
.stWarning{background:rgba(78,54,6,0.6) !important;border-color:#f59e0b !important;color:#fde68a !important;border-radius:10px !important;}
.stError{background:rgba(78,6,6,0.6) !important;border-color:#dc2626 !important;color:#fca5a5 !important;border-radius:10px !important;}
.stInfo{background:rgba(6,42,78,0.6) !important;border-color:#3b82f6 !important;color:#bfdbfe !important;border-radius:10px !important;}
.stDataFrame,[data-testid="stDataFrame"]{background:rgba(15,23,42,0.7) !important;border-radius:10px !important;border:1px solid rgba(96,165,250,0.2) !important;}
hr{border-color:rgba(96,165,250,0.15) !important;}
::-webkit-scrollbar{width:6px;}::-webkit-scrollbar-track{background:rgba(15,23,42,0.4);}::-webkit-scrollbar-thumb{background:rgba(96,165,250,0.4);border-radius:3px;}
.ksm-section-title{font-size:0.67rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#60a5fa;margin:1.1rem 0 0.6rem 0;border-bottom:1px solid rgba(96,165,250,0.2);padding-bottom:0.4rem;}
.ksm-odometer{background:linear-gradient(135deg,#1e3a8a,#2563eb);border-radius:12px;padding:14px 20px;margin-bottom:1rem;border:1px solid rgba(96,165,250,0.35);box-shadow:0 4px 16px rgba(37,99,235,0.35);}
.ai-card{border-radius:12px;padding:1rem 1.2rem;margin:0.8rem 0;border:1px solid;}
.ai-card-good{background:rgba(6,78,59,0.45);border-color:#10b981;}
.ai-card-warn{background:rgba(78,54,6,0.45);border-color:#f59e0b;}
.ai-card-bad{background:rgba(78,6,6,0.45);border-color:#dc2626;}
.ai-card-info{background:rgba(6,42,78,0.45);border-color:#3b82f6;}
.ai-badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.67rem;font-weight:800;letter-spacing:0.09em;margin-bottom:6px;}
.badge-good{background:rgba(16,185,129,0.25);color:#34d399;border:1px solid #10b981;}
.badge-warn{background:rgba(245,158,11,0.25);color:#fbbf24;border:1px solid #f59e0b;}
.badge-bad{background:rgba(220,38,38,0.25);color:#f87171;border:1px solid #dc2626;}
.badge-info{background:rgba(59,130,246,0.25);color:#60a5fa;border:1px solid #3b82f6;}
.history-row{background:linear-gradient(135deg,rgba(30,58,138,0.25),rgba(15,23,42,0.4));border:1px solid rgba(96,165,250,0.18);border-radius:10px;padding:0.75rem 1rem;margin-bottom:0.55rem;}
.history-route{font-size:0.93rem;font-weight:700;color:#e2e8f0;}
.history-meta{font-size:0.73rem;color:#94a3b8;margin-top:5px;display:flex;flex-wrap:wrap;gap:10px;}
.conn-badge{display:inline-flex;align-items:center;gap:7px;padding:5px 14px;border-radius:20px;font-size:0.73rem;font-weight:700;letter-spacing:0.05em;}
.conn-live{background:rgba(6,78,59,0.5);border:1px solid #10b981;color:#34d399;}
.conn-pending{background:rgba(78,54,6,0.5);border:1px solid #f59e0b;color:#fbbf24;}
.conn-offline{background:rgba(78,6,6,0.5);border:1px solid #dc2626;color:#f87171;}
.queue-item{background:rgba(78,54,6,0.25);border:1px solid rgba(245,158,11,0.3);border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.45rem;font-size:0.79rem;}
.sysinfo{font-size:0.74rem;color:#94a3b8;line-height:2.2;background:rgba(15,23,42,0.5);border-radius:8px;padding:10px 14px;border:1px solid rgba(96,165,250,0.15);font-family:'JetBrains Mono',monospace;}
.insight-card{background:linear-gradient(135deg,rgba(30,58,138,0.3),rgba(15,23,42,0.5));border:1px solid rgba(96,165,250,0.22);border-radius:12px;padding:0.9rem 1.1rem;margin:0.55rem 0;}
.link-banner{background:linear-gradient(135deg,rgba(5,150,105,0.2),rgba(6,78,59,0.3));border:1px solid rgba(52,211,153,0.35);border-radius:10px;padding:9px 15px;margin:0.4rem 0 0.9rem 0;font-size:0.77rem;color:#6ee7b7;}
.driver-profile-row{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;}
.driver-profile-item{background:rgba(15,23,42,0.5);border:1px solid rgba(96,165,250,0.2);border-radius:8px;padding:6px 12px;font-size:0.74rem;color:#cbd5e1;flex:1;min-width:130px;}
.driver-profile-item b{color:#93c5fd;display:block;font-size:0.62rem;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:2px;}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def db_available() -> bool:
    return os.path.exists(DB_PATH)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_driver_columns():
    """Add driver-specific columns to Truck table if missing, and auto-generate driver IDs."""
    if not db_available():
        return
    try:
        conn = get_conn()
        cols = [r[1] for r in conn.execute("PRAGMA table_info(Truck)").fetchall()]
        for col, typ in [
            ("driver_id", "TEXT"),
            ("driver_license", "TEXT"),
            ("driver_phone", "TEXT"),
            ("driver_id_number", "TEXT"),
            ("driver_experience_years", "INTEGER DEFAULT 0"),
            ("driver_routes", "TEXT"),
            ("driver_certifications", "TEXT"),
        ]:
            if col not in cols:
                conn.execute(f"ALTER TABLE Truck ADD COLUMN {col} {typ}")
        trucks = conn.execute("SELECT truck_id FROM Truck WHERE driver_id IS NULL OR driver_id=''").fetchall()
        for (tid,) in trucks:
            conn.execute("UPDATE Truck SET driver_id=? WHERE truck_id=?", (f"KSM-DRV-{tid:04d}", tid))
        conn.commit()
        conn.close()
    except Exception:
        pass


def load_trucks():
    if not db_available():
        return []
    try:
        conn = get_conn()
        rows = conn.execute(
            """SELECT truck_id, registration, driver, mileage, fuel_tank_capacity,
                      driver_id, driver_license, driver_phone, driver_id_number,
                      driver_experience_years, driver_routes, driver_certifications,
                      truck_status, model
               FROM Truck ORDER BY registration"""
        ).fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def get_driver_by_id(driver_id: str):
    if not db_available():
        return None
    try:
        conn = get_conn()
        row = conn.execute(
            """SELECT truck_id, registration, driver, mileage, fuel_tank_capacity,
                      driver_id, driver_license, driver_phone, driver_id_number,
                      driver_experience_years, driver_routes, driver_certifications,
                      truck_status, model
               FROM Truck WHERE driver_id=?""",
            (driver_id,)
        ).fetchone()
        conn.close()
        return row
    except Exception:
        return None


def get_truck_fuel_history(truck_id):
    if not db_available():
        return None, None
    try:
        conn = get_conn()
        last = conn.execute(
            "SELECT fuel_added, odometer, date FROM FuelConsumption "
            "WHERE truck_id=? ORDER BY date DESC, odometer DESC LIMIT 1", (truck_id,)
        ).fetchone()
        prev = conn.execute(
            "SELECT odometer FROM FuelConsumption "
            "WHERE truck_id=? ORDER BY date DESC, odometer DESC LIMIT 1 OFFSET 1", (truck_id,)
        ).fetchone()
        conn.close()
        return last, prev
    except Exception:
        return None, None


def get_trip_history(truck_id, limit=10):
    if not db_available():
        return []
    try:
        conn = get_conn()
        rows = conn.execute(
            """SELECT date, start_location, end_location, distance,
                      fuel_consumed, actual_fuel_efficiency,
                      trip_duration_hours, load, hard_braking_events, idle_time_minutes
               FROM Trip WHERE truck_id=? ORDER BY date DESC, trip_id DESC LIMIT ?""",
            (truck_id, limit),
        ).fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def get_avg_efficiency(truck_id, window=10):
    if not db_available():
        return None
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT actual_fuel_efficiency FROM Trip "
            "WHERE truck_id=? AND actual_fuel_efficiency > 0 "
            "ORDER BY date DESC, trip_id DESC LIMIT ?", (truck_id, window),
        ).fetchall()
        conn.close()
        vals = [r[0] for r in rows if r[0]]
        return round(sum(vals) / len(vals), 2) if vals else None
    except Exception:
        return None


def get_driver_performance_stats(truck_id):
    if not db_available():
        return {}
    try:
        conn = get_conn()
        rows = conn.execute(
            """SELECT actual_fuel_efficiency, hard_braking_events, idle_time_minutes,
                      trip_duration_hours, distance, profit_margin
               FROM Trip WHERE truck_id=? AND date >= date('now', '-30 days') ORDER BY date DESC""",
            (truck_id,)
        ).fetchall()
        conn.close()
        if not rows:
            return {}
        effs    = [r[0] for r in rows if r[0]]
        brakes  = [r[1] for r in rows if r[1] is not None]
        idles   = [r[2] for r in rows if r[2] is not None]
        margins = [r[5] for r in rows if r[5] is not None]
        return {
            "trips_30d":   len(rows),
            "avg_eff":     round(sum(effs)/len(effs), 2) if effs else 0,
            "avg_braking": round(sum(brakes)/len(brakes), 1) if brakes else 0,
            "avg_idle":    round(sum(idles)/len(idles), 1) if idles else 0,
            "avg_margin":  round(sum(margins)/len(margins), 1) if margins else 0,
        }
    except Exception:
        return {}


def get_revenue_30d(truck_id):
    if not db_available():
        return 0.0
    try:
        conn = get_conn()
        row = conn.execute(
            "SELECT SUM(COALESCE(revenue, 0)) FROM Trip WHERE truck_id=? AND date >= date('now', '-30 days')",
            (truck_id,)
        ).fetchone()
        conn.close()
        return float(row[0] or 0)
    except Exception:
        return 0.0


def save_trip(data):
    if not db_available():
        return False
    try:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute(
            """INSERT INTO Trip
               (truck_id, start_location, end_location, distance, load, date,
                fuel_consumed, actual_fuel_efficiency, trip_duration_hours,
                idle_time_minutes, hard_braking_events, border_crossings,
                revenue, terrain_type, weather_condition, road_quality,
                predicted_fuel_efficiency, risk_score, profit_margin,
                driver_experience_years, delivery_on_time)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data["truck_id"], data["origin"], data["destination"],
                data["distance"], data["load_kg"], data["date"],
                data["fuel_consumed"], data["fuel_efficiency"],
                data["duration_hours"], data["idle_minutes"],
                data["hard_braking"], data["border_crossings"],
                data.get("revenue", 0), data.get("terrain", "Rolling"),
                data.get("weather", "Clear"), data.get("road_quality", 0.75),
                data["fuel_efficiency"],
                0.3 if data.get("anomaly") else 0.15,
                data.get("profit_margin", 0),
                data.get("driver_exp", 5),
                1 if data.get("on_time", True) else 0,
            ),
        )
        new_odo = data.get("odometer", 0)
        if new_odo > 0:
            cur.execute("UPDATE Truck SET mileage=? WHERE truck_id=?", (new_odo, data["truck_id"]))
        svc = conn.execute(
            "SELECT last_service_km, service_interval, service_warning_active FROM Truck WHERE truck_id=?",
            (data["truck_id"],)
        ).fetchone()
        if svc and new_odo > 0:
            last_svc, interval, active = svc
            interval = interval or SERVICE_INTERVAL_KM
            svc_gap  = new_odo - (last_svc or 0)
            if svc_gap >= interval * 0.90 and not active:
                cur.execute(
                    "UPDATE Truck SET service_warning_active=1, service_warning_date=? WHERE truck_id=?",
                    (data["date"], data["truck_id"]),
                )
                try:
                    cur.execute(
                        "INSERT INTO ServiceWarning (truck_id, warning_type, triggered_date, triggered_km) VALUES (?,?,?,?)",
                        (data["truck_id"], "Service Due", data["date"], new_odo),
                    )
                except Exception:
                    pass
                st.warning(f"⚠️ Service warning — {svc_gap:,.0f} km since last service. Fleet manager notified.")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False


def save_fuel_fillup(data):
    if not db_available():
        return False
    try:
        conn = get_conn()
        conn.execute(
            """INSERT INTO FuelConsumption
               (truck_id, date, trip_id, fuel_added, odometer,
                cost_per_liter, total_cost, fuel_type, station_location, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                data["truck_id"], data["date"], None,
                data["fuel_added"], data["odometer"],
                data["cost_per_liter"],
                round(data["fuel_added"] * data["cost_per_liter"], 2),
                "Diesel", data["station"], data["notes"],
            ),
        )
        if data["odometer"] > 0:
            conn.execute("UPDATE Truck SET mileage=? WHERE truck_id=?", (data["odometer"], data["truck_id"]))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False


def save_event(data):
    if not db_available():
        return False
    try:
        conn = get_conn()
        conn.execute(
            """INSERT INTO MaintenanceLog
               (truck_id, date, description, cost, odometer, service_type, notes)
               VALUES (?,?,?,?,?,?,?)""",
            (
                data["truck_id"], data["date"],
                f"[DRIVER EVENT] {data['event_type']}",
                0, data["odometer"], "DriverEvent",
                f"Severity: {data['severity']} | Location: {data['location']} | {data['description']}",
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False


# =============================================================================
# OFFLINE QUEUE
# =============================================================================

def enqueue(record, kind="trip"):
    key = f"offline_{kind}"
    if key not in st.session_state:
        st.session_state[key] = []
    st.session_state[key].append(record)


def offline_count(kind):
    return len(st.session_state.get(f"offline_{kind}", []))


def sync_all():
    results = {"trips": 0, "fuel": 0, "events": 0, "failed": 0}
    for rec in list(st.session_state.get("offline_trip", [])):
        if save_trip(rec):
            st.session_state["offline_trip"].remove(rec); results["trips"] += 1
        else:
            results["failed"] += 1
    for rec in list(st.session_state.get("offline_fuel", [])):
        if save_fuel_fillup(rec):
            st.session_state["offline_fuel"].remove(rec); results["fuel"] += 1
        else:
            results["failed"] += 1
    for rec in list(st.session_state.get("offline_event", [])):
        if save_event(rec):
            st.session_state["offline_event"].remove(rec); results["events"] += 1
        else:
            results["failed"] += 1
    return results


# =============================================================================
# AI ANALYSIS ENGINE
# =============================================================================

def estimate_distance(origin, destination):
    if origin in LOCATION_COORDS and destination in LOCATION_COORDS:
        p1, p2 = LOCATION_COORDS[origin], LOCATION_COORDS[destination]
        return round(math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2) * 111 * 1.2, 1)
    return 0.0


def detect_terrain(origin, destination):
    MOUNTAINOUS = {"Mbabane", "Piggs Peak", "Nelspruit"}
    FLAT = {"Lomahasha", "Lavumisa", "Maputo"}
    if origin in MOUNTAINOUS or destination in MOUNTAINOUS:
        return "Mountainous"
    if origin in FLAT and destination in FLAT:
        return "Flat"
    return "Rolling"


def compute_driver_score(hard_braking, idle_minutes, eff_ratio):
    score = 100
    score -= min(20, hard_braking * 2)
    if idle_minutes > 30:
        score -= min(15, idle_minutes / 10)
    if eff_ratio < 0.70:
        score -= 25
    elif eff_ratio < 0.88:
        score -= 10
    elif eff_ratio >= 1.10:
        score += 5
    return max(0, min(100, round(score)))


def ai_analyse(fuel_consumed, distance, load_kg, terrain, border_crossings, avg_eff, hard_braking, idle_minutes):
    if distance <= 0 or fuel_consumed <= 0:
        return {"rating": "Unknown", "efficiency": 0.0, "messages": [], "anomaly": False, "driver_score": None}
    efficiency   = round(distance / fuel_consumed, 2)
    terrain_adj  = {"Flat": 1.0, "Rolling": 0.85, "Mountainous": 0.70}.get(terrain, 0.85)
    load_ratio   = min(1.0, load_kg / MAX_PAYLOAD_KG)
    expected_eff = (100 / FUEL_BASE_L_PER_100) * terrain_adj * (1 - load_ratio * 0.28)
    eff_ratio    = efficiency / expected_eff if expected_eff > 0 else 1.0
    messages, anomaly = [], False
    if eff_ratio < 0.70:
        messages.append(("bad", f"High fuel usage — {(1-eff_ratio)*100:.0f}% above expected. Check injectors, air filter and tyre pressure."))
        rating = "Critical" if eff_ratio < 0.55 else "High"; anomaly = True
    elif eff_ratio < 0.88:
        messages.append(("warn", "Fuel usage slightly elevated. Check tyre pressure and reduce idle time.")); rating = "Elevated"
    elif eff_ratio >= 1.10:
        messages.append(("good", f"Efficient trip — {(eff_ratio-1)*100:.0f}% better than route baseline!")); rating = "Good"
    else:
        messages.append(("info", "Fuel consumption within normal range for this route and load.")); rating = "Normal"
    if avg_eff and avg_eff > 0:
        delta = (efficiency - avg_eff) / avg_eff
        if delta < -0.20:
            messages.append(("bad", f"{abs(delta)*100:.0f}% worse than 10-trip average ({avg_eff:.2f} km/L). Flag for inspection.")); anomaly = True
        elif delta > 0.15:
            messages.append(("good", f"Outperforming truck average ({avg_eff:.2f} km/L) by {delta*100:.0f}%."))
    if hard_braking >= 5:
        messages.append(("bad", f"{hard_braking} hard-braking events — increases brake wear and fuel use."))
    elif hard_braking >= 2:
        messages.append(("warn", f"{hard_braking} hard-braking events. Anticipate stops earlier."))
    elif hard_braking == 0:
        messages.append(("good", "Zero hard-braking events — smooth and efficient driving."))
    if idle_minutes >= 60:
        messages.append(("warn", f"{idle_minutes} min idling — ~{idle_minutes/60*6.5:.1f} L wasted. Switch off engine at stops."))
    elif idle_minutes >= 30:
        messages.append(("info", f"{idle_minutes} min idle. Switch engine off at long stops."))
    if border_crossings >= 2:
        messages.append(("info", f"{border_crossings} border crossings — factor delay time into scheduling."))
    return {"rating": rating, "efficiency": efficiency, "messages": messages, "anomaly": anomaly,
            "driver_score": compute_driver_score(hard_braking, idle_minutes, eff_ratio)}


# =============================================================================
# SESSION STATE DEFAULTS
# =============================================================================
ensure_driver_columns()

for _k, _v in [
    ("drv_authenticated", False), ("drv_driver_id", None), ("drv_driver_row", None),
    ("selected_truck_id", None), ("selected_truck_label", ""),
    ("current_odo", 0.0), ("last_feedback", None),
    ("offline_trip", []), ("offline_fuel", []), ("offline_event", []),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


# =============================================================================
# SECURITY — LOGIN SCREEN
# =============================================================================

def _render_login():
    BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(BASE_DIR, "image_2ff50a.png")

    # Header
    hA, hB = st.columns([1, 3])
    with hA:
        if os.path.exists(logo_path):
            st.image(logo_path, width=85)
    with hB:
        st.markdown("""
        <div style='padding-top:12px;'>
        <div style='font-size:1.3rem;font-weight:900;color:#60a5fa;letter-spacing:-0.5px;line-height:1;'>KSM DRIVER TERMINAL</div>
        <div style='font-size:0.72rem;font-weight:700;color:#34d399;letter-spacing:0.1em;margin-top:3px;'>SMART FREIGHT SOLUTIONS · SECURE ACCESS</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style='background:rgba(15,23,42,0.88);backdrop-filter:blur(20px);
                border:1px solid rgba(96,165,250,0.25);border-radius:16px;
                padding:28px 24px;margin-top:20px;'>
    <div style='color:#93c5fd;font-size:0.68rem;font-weight:700;letter-spacing:0.12em;
                text-transform:uppercase;margin-bottom:16px;text-align:center;border-bottom:1px solid rgba(96,165,250,0.15);padding-bottom:12px;'>
    🔐 Driver Authentication Required</div>
    """, unsafe_allow_html=True)

    with st.form("driver_login_form"):
        driver_id_input = st.text_input("Driver ID", placeholder="e.g. KSM-DRV-0001",
                                        help="Your official KSM Driver ID card number")
        pin_input = st.text_input("PIN", type="password", placeholder="Enter your PIN")
        submitted = st.form_submit_button("🔐 Sign In to Driver Terminal", type="primary", use_container_width=True)

    if submitted:
        drv_id = driver_id_input.strip().upper()
        expected_pin = DRIVER_PINS.get(drv_id)
        if expected_pin and pin_input == expected_pin:
            driver_row = get_driver_by_id(drv_id)
            st.session_state["drv_authenticated"] = True
            st.session_state["drv_driver_id"]     = drv_id
            st.session_state["drv_driver_row"]    = driver_row
            if driver_row:
                st.session_state["selected_truck_id"]    = driver_row[0]
                st.session_state["selected_truck_label"] = driver_row[1]
                st.session_state["current_odo"]          = float(driver_row[3] or 0)
            st.success(f"✅ Welcome! Authenticated as {drv_id}")
            st.rerun()
        else:
            st.error("❌ Invalid Driver ID or PIN. Contact your fleet manager.")

    st.markdown("""
    <div style='text-align:center;margin-top:16px;color:#475569;font-size:0.67rem;border-top:1px solid rgba(96,165,250,0.1);padding-top:12px;'>
    Demo — KSM-DRV-0001 / PIN: 1234 &nbsp;|&nbsp; Fleet Mgr: FLEET-MGR / ksm2025
    </div></div>
    """, unsafe_allow_html=True)


if not st.session_state.get("drv_authenticated"):
    _render_login()
    st.stop()


# =============================================================================
# MAIN APP — POST-LOGIN
# =============================================================================
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(BASE_DIR, "image_2ff50a.png")
drv_id    = st.session_state.get("drv_driver_id", "")
drv_row   = st.session_state.get("drv_driver_row")

# =============================================================================
# SLIM ORGANISED HEADER — Logo | Title + Driver Info | Time + Sign Out
# =============================================================================
hA, hB, hC = st.columns([1, 4, 1])
with hA:
    if os.path.exists(logo_path):
        st.image(logo_path, width=68)
    else:
        st.markdown("<div style='font-size:2rem;text-align:center;'>🚛</div>", unsafe_allow_html=True)
with hB:
    driver_name = drv_row[2] if drv_row else "Driver"
    truck_reg   = drv_row[1] if drv_row else "—"
    now = datetime.now()
    st.markdown(
        f"<div style='padding-top:4px;'>"
        f"<div style='font-size:0.72rem;font-weight:800;color:#60a5fa;letter-spacing:0.1em;line-height:1;'>KSM DRIVER TERMINAL</div>"
        f"<div style='font-size:1.0rem;font-weight:700;color:#fff;margin-top:3px;line-height:1;'>{driver_name}</div>"
        f"<div style='font-size:0.68rem;color:#64748b;margin-top:3px;'>"
        f"ID: <span style='color:#34d399;font-weight:700;font-family:JetBrains Mono,monospace;'>{drv_id}</span>"
        f" &nbsp;·&nbsp; Truck: <span style='color:#93c5fd;font-weight:700;'>{truck_reg}</span>"
        f" &nbsp;·&nbsp; {now.strftime('%d %b %Y %H:%M')}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
with hC:
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    if st.button("Sign Out", use_container_width=True, key="drv_signout"):
        for k in ["drv_authenticated", "drv_driver_id", "drv_driver_row",
                  "selected_truck_id", "selected_truck_label", "current_odo", "last_feedback"]:
            st.session_state.pop(k, None)
        st.rerun()

st.divider()

# =============================================================================
# TRUCK SELECTOR + CONNECTION STATUS
# =============================================================================
db_ok  = db_available()
trucks = load_trucks()
total_pending = offline_count("trip") + offline_count("fuel") + offline_count("event")

if db_ok and not total_pending:
    conn_html = '<span class="conn-badge conn-live">● LIVE — Connected to Main System</span>'
elif db_ok and total_pending:
    conn_html = f'<span class="conn-badge conn-pending">◑ {total_pending} pending sync</span>'
else:
    conn_html = '<span class="conn-badge conn-offline">○ OFFLINE — Data queued locally</span>'

st.markdown(
    '<div class="link-banner"><span style="font-size:1rem;margin-right:8px;">🔗</span>'
    '<span><b>Integrated with KSM Main System (yizo.py)</b> — Trip, fuel and event data writes'
    ' directly to <code style="background:rgba(0,0,0,0.3);padding:1px 5px;border-radius:4px;">fleet.db</code>'
    ' and is immediately visible in the fleet dashboard.</span></div>',
    unsafe_allow_html=True,
)

col_sel, col_status = st.columns([3, 1])
with col_sel:
    if trucks:
        labels = {f"{r[1]}  ({r[2] or 'No driver'})": r for r in trucks}
        default_label = None
        if drv_row:
            for lbl, r in labels.items():
                if r[0] == drv_row[0]:
                    default_label = lbl
                    break
        default_idx = list(labels.keys()).index(default_label) if default_label else 0
        chosen_label = st.selectbox("Select Truck", list(labels.keys()),
                                    index=default_idx, label_visibility="collapsed")
        chosen = labels[chosen_label]
        st.session_state.selected_truck_id    = chosen[0]
        st.session_state.selected_truck_label = chosen[1]
        st.session_state.current_odo          = float(chosen[3] or 0)
        tank_cap = float(chosen[4] or 300)
    else:
        st.warning("⚠️ No trucks found. Ensure fleet.db is in the same directory.")
        st.session_state.selected_truck_id = None
        tank_cap = 300.0
with col_status:
    st.markdown(conn_html, unsafe_allow_html=True)

tid         = st.session_state.selected_truck_id
current_odo = st.session_state.current_odo
sel_row     = next((r for r in trucks if r[0] == tid), None) if tid else None

# =============================================================================
# DRIVER ID CARD
# =============================================================================
if tid and sel_row:
    (t_id, t_reg, t_driver, t_mileage, t_tank, t_drv_id,
     t_license, t_phone, t_id_num, t_exp, t_routes, t_certs,
     t_status, t_model) = sel_row

    status_c = {"ACTIVE": "#34d399", "MAINTENANCE": "#fbbf24", "OUT_OF_SERVICE": "#f87171"}.get(t_status or "ACTIVE", "#34d399")

    st.markdown(
        f"""<div style="background:linear-gradient(135deg,rgba(5,150,105,0.2),rgba(6,78,59,0.35));
            border:1px solid rgba(52,211,153,0.35);border-radius:14px;padding:14px 18px;margin-bottom:0.8rem;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
            <div style="background:linear-gradient(135deg,#059669,#10b981);width:44px;height:44px;
                        border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;">🪪</div>
            <div>
                <div style="font-size:0.61rem;font-weight:800;letter-spacing:0.14em;color:#34d399;text-transform:uppercase;">Driver ID Card — KSM Smart Freight</div>
                <div style="font-size:1.0rem;font-weight:800;color:#fff;margin-top:1px;">{t_driver or "Unassigned"}</div>
                <div style="font-size:0.7rem;color:#94a3b8;margin-top:1px;">
                    ID: <span style="color:#6ee7b7;font-weight:700;font-family:'JetBrains Mono',monospace;">{t_drv_id or "—"}</span>
                    &nbsp;·&nbsp; <span style="color:{status_c};font-weight:700;">{t_status or "ACTIVE"}</span>
                </div>
            </div>
        </div>
        <div class="driver-profile-row">
            <div class="driver-profile-item"><b>Truck Reg.</b>{t_reg}</div>
            <div class="driver-profile-item"><b>Model</b>{t_model or "—"}</div>
            <div class="driver-profile-item"><b>Experience</b>{t_exp or "—"} yrs</div>
            <div class="driver-profile-item"><b>License No.</b>{t_license or "—"}</div>
            <div class="driver-profile-item"><b>ID Number</b>{t_id_num or "—"}</div>
            <div class="driver-profile-item"><b>Phone</b>{t_phone or "—"}</div>
            <div class="driver-profile-item"><b>Routes</b>{t_routes or "All routes"}</div>
            <div class="driver-profile-item"><b>Certifications</b>{t_certs or "Standard"}</div>
        </div></div>""",
        unsafe_allow_html=True,
    )

if tid:
    st.markdown(
        f'<div class="ksm-odometer">'
        f'<span style="font-size:0.62rem;font-weight:800;letter-spacing:0.14em;color:#93c5fd;text-transform:uppercase;">Current Odometer</span><br>'
        f'<span style="font-size:1.7rem;font-weight:800;color:#fff;font-family:JetBrains Mono,monospace;">'
        f'{current_odo:,.0f} km</span>'
        f'&nbsp;&nbsp;<span style="font-size:0.74rem;color:#60a5fa;">{st.session_state.selected_truck_label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.divider()

# =============================================================================
# TABS
# =============================================================================
tab_trip, tab_fuel, tab_events, tab_perf, tab_hist, tab_prof, tab_sync = st.tabs([
    "🚛 Trip Log", "⛽ Fuel", "🚨 Events", "📊 Performance", "📋 History", "👤 My Profile", "🔄 Sync"
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — TRIP LOG
# ─────────────────────────────────────────────────────────────────────────────
with tab_trip:
    st.markdown("### Log Trip")
    st.caption("Submit trip data directly to the KSM main system database.")

    if not tid:
        st.info("Select a truck above to start logging trips.")
    else:
        last_fuel, _ = get_truck_fuel_history(tid)
        avg_eff_val  = get_avg_efficiency(tid)
        auto_fuel    = last_fuel[0] if last_fuel else 0.0
        auto_odo     = last_fuel[1] if last_fuel else 0.0

        with st.form("trip_form", clear_on_submit=True):
            st.markdown('<div class="ksm-section-title">Route</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                origin = st.selectbox("Origin", LOCATIONS, index=0)
            with c2:
                dest_options = [l for l in LOCATIONS if l != origin]
                destination  = st.selectbox("Destination", dest_options, index=min(1, len(dest_options)-1))

            auto_dist    = estimate_distance(origin, destination)
            auto_terrain = detect_terrain(origin, destination)
            st.markdown(
                f'<div style="background:rgba(30,58,138,0.3);border:1px solid rgba(96,165,250,0.2);'
                f'border-radius:8px;padding:7px 12px;font-size:0.76rem;color:#93c5fd;margin-bottom:0.4rem;">'
                f'📍 Auto: <b>{auto_dist:.0f} km</b> &nbsp;|&nbsp; 🏔️ Terrain: <b>{auto_terrain}</b>'
                f' &nbsp;|&nbsp; ⛽ Expected: <b>~{auto_dist * FUEL_BASE_L_PER_100 / 100:.0f} L</b></div>',
                unsafe_allow_html=True,
            )

            st.markdown('<div class="ksm-section-title">Distance & Crossings</div>', unsafe_allow_html=True)
            c3, c4 = st.columns(2)
            with c3:
                distance = st.number_input("Distance (km)", min_value=0.0, value=float(auto_dist), step=1.0)
            with c4:
                border_crossings = st.number_input("Border Crossings", min_value=0, value=0, step=1)

            st.markdown('<div class="ksm-section-title">Cargo & Load</div>', unsafe_allow_html=True)
            c5, c6 = st.columns(2)
            with c5:
                load_kg = st.number_input("Cargo Load (kg)", min_value=0.0, value=5_000.0, step=100.0)
                if load_kg > MAX_PAYLOAD_KG:
                    st.warning(f"⚠️ Exceeds max payload of {MAX_PAYLOAD_KG:,} kg.")
            with c6:
                default_exp = int(sel_row[9] or 5) if sel_row and sel_row[9] else 5
                driver_exp = st.slider("Driver Experience (yrs)", 0, 30, default_exp)

            st.markdown('<div class="ksm-section-title">Fuel & Duration</div>', unsafe_allow_html=True)
            c7, c8 = st.columns(2)
            with c7:
                fuel_consumed = st.number_input("Fuel Consumed (L)", min_value=0.0, value=float(auto_fuel), step=0.5)
                duration_h    = st.number_input("Trip Duration (hours)", min_value=0.0, value=5.0, step=0.25)
            with c8:
                odometer = st.number_input("Odometer at Trip End (km)", min_value=0.0,
                                           value=float(auto_odo if auto_odo > 0 else current_odo), step=1.0)
                idle_min = st.number_input("Idle Time (minutes)", min_value=0, value=0, step=5)

            st.markdown('<div class="ksm-section-title">Driving Behaviour & Revenue</div>', unsafe_allow_html=True)
            c9, c10, c11 = st.columns(3)
            with c9:
                hard_braking = st.number_input("Hard Braking Events", min_value=0, value=0, step=1)
            with c10:
                revenue = st.number_input("Revenue (E)", min_value=0.0, value=0.0, step=50.0)
            with c11:
                on_time = st.selectbox("On-Time?", ["Yes", "No"], index=0)

            trip_date = st.date_input("Trip Date", value=date.today())
            submitted = st.form_submit_button("✅ Submit Trip Log", type="primary", use_container_width=True)

        if submitted:
            if distance <= 0:
                st.error("Distance must be greater than 0.")
            elif fuel_consumed <= 0:
                st.error("Fuel consumed must be greater than 0.")
            else:
                fb = ai_analyse(fuel_consumed, distance, load_kg, auto_terrain,
                                border_crossings, avg_eff_val, hard_braking, idle_min)
                fuel_cost   = fuel_consumed * FUEL_PRICE_DEFAULT
                maint_cost  = distance * MAINTENANCE_PER_KM
                border_cost = border_crossings * BORDER_COST_EACH
                profit      = revenue - fuel_cost - maint_cost - border_cost
                pm          = (profit / revenue * 100) if revenue > 0 else 0.0
                record = {
                    "truck_id": tid, "origin": origin, "destination": destination,
                    "distance": distance, "load_kg": load_kg, "date": trip_date.strftime("%Y-%m-%d"),
                    "fuel_consumed": fuel_consumed, "fuel_efficiency": fb["efficiency"],
                    "duration_hours": duration_h, "idle_minutes": idle_min,
                    "hard_braking": hard_braking, "border_crossings": border_crossings,
                    "revenue": revenue, "terrain": auto_terrain, "weather": "Clear",
                    "road_quality": 0.75, "anomaly": fb["anomaly"],
                    "profit_margin": round(pm, 1), "odometer": odometer,
                    "driver_exp": driver_exp, "on_time": (on_time == "Yes"),
                }
                if db_ok and save_trip(record):
                    st.success(f"✅ Trip saved to main system. Terrain: **{auto_terrain}** — visible in fleet dashboard immediately.")
                    if revenue > 0:
                        st.info(f"💰 Profit: **E {profit:,.2f}** &nbsp;|&nbsp; Revenue: E {revenue:,.2f} &nbsp;|&nbsp; Expenses: E {fuel_cost+maint_cost+border_cost:,.2f}")
                else:
                    enqueue(record, "trip")
                    st.warning("📶 Offline — trip queued locally. Will sync when reconnected.")
                st.session_state.last_feedback = fb
                st.rerun()

        fb = st.session_state.get("last_feedback")
        if fb and fb.get("efficiency", 0) > 0:
            rating    = fb["rating"]
            card_cls  = {"Good":"ai-card-good","Normal":"ai-card-info","Elevated":"ai-card-warn","High":"ai-card-bad","Critical":"ai-card-bad"}.get(rating, "ai-card-info")
            badge_cls = {"Good":"badge-good","Normal":"badge-info","Elevated":"badge-warn","High":"badge-bad","Critical":"badge-bad"}.get(rating, "badge-info")
            score     = fb.get("driver_score", "—")
            sc        = "#34d399" if (score and score >= 80) else ("#fbbf24" if (score and score >= 60) else "#f87171")
            st.markdown("---")
            st.markdown("#### 🤖 AI Trip Analysis")
            m1, m2, m3 = st.columns(3)
            m1.metric("Fuel Efficiency",    f"{fb['efficiency']:.2f} km/L")
            m2.metric("Performance Rating", rating)
            m3.metric("Driver Score",       f"{score}/100" if score else "—")
            st.markdown(f'<div class="ai-card {card_cls}">', unsafe_allow_html=True)
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
                f'<span style="font-size:1.55rem;font-weight:800;color:#fff;font-family:JetBrains Mono,monospace;">{fb["efficiency"]:.2f} km/L</span>'
                f'<span class="ai-badge {badge_cls}">{rating.upper()}</span>'
                f'<span style="margin-left:auto;font-size:1.5rem;font-weight:800;color:{sc};">{score}<span style="font-size:0.75rem;color:#94a3b8;">/100</span></span>'
                f'</div>', unsafe_allow_html=True,
            )
            pill_map = {"good":"badge-good","warn":"badge-warn","bad":"badge-bad","info":"badge-info"}
            for level, msg in fb["messages"]:
                st.markdown(
                    f'<div style="margin:5px 0;"><span class="ai-badge {pill_map.get(level,"badge-info")}">{level.upper()}</span>'
                    f'<p style="font-size:0.81rem;color:#e2e8f0;margin:3px 0 8px 0;">{msg}</p></div>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — FUEL FILL-UP
# ─────────────────────────────────────────────────────────────────────────────
with tab_fuel:
    st.markdown("### Log Fuel Fill-Up")
    st.caption("Record fill-ups with cost tracking. Feeds directly into fleet analytics.")

    if not tid:
        st.info("Select a truck above.")
    else:
        with st.form("fuel_form", clear_on_submit=True):
            st.markdown('<div class="ksm-section-title">Fill-Up Details</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                fuel_added   = st.number_input("Litres Added (L)", min_value=0.0, value=0.0, step=1.0, help=f"Tank capacity: {tank_cap:.0f} L")
                cost_per_ltr = st.number_input("Price per Litre (E)", min_value=0.0, value=FUEL_PRICE_DEFAULT, step=0.05)
            with c2:
                odo_fuel  = st.number_input("Odometer at Fill-Up (km)", min_value=0.0, value=float(current_odo), step=1.0)
                fuel_date = st.date_input("Date", value=date.today(), key="fuel_date_input")
            if fuel_added > 0:
                fill_pct  = min(100, (fuel_added / tank_cap) * 100)
                total_est = round(fuel_added * cost_per_ltr, 2)
                range_est = round(fuel_added / (FUEL_BASE_L_PER_100 / 100))
                st.markdown(
                    f'<div style="background:rgba(5,150,105,0.18);border:1px solid rgba(52,211,153,0.3);border-radius:8px;padding:7px 12px;font-size:0.77rem;color:#6ee7b7;margin-top:0.3rem;">'
                    f'💰 Cost: <b>E {total_est:,.2f}</b> &nbsp;|&nbsp; 🛢️ Fill: <b>{fill_pct:.0f}%</b> &nbsp;|&nbsp; 📏 Range: <b>~{range_est} km</b></div>',
                    unsafe_allow_html=True,
                )
            st.markdown('<div class="ksm-section-title">Station Info</div>', unsafe_allow_html=True)
            station_loc = st.text_input("Station Name / Location", placeholder="e.g. Total Matsapha")
            fuel_notes  = st.text_input("Notes (optional)", placeholder="e.g. Full tank, card payment")
            fuel_submit = st.form_submit_button("⛽ Log Fill-Up", type="primary", use_container_width=True)

        if fuel_submit:
            if fuel_added <= 0:
                st.error("Fuel amount must be greater than 0.")
            else:
                record = {
                    "truck_id": tid, "date": fuel_date.strftime("%Y-%m-%d"),
                    "fuel_added": fuel_added, "odometer": odo_fuel,
                    "cost_per_liter": cost_per_ltr, "station": station_loc, "notes": fuel_notes,
                }
                if db_ok and save_fuel_fillup(record):
                    st.success(f"✅ Fill-up saved to main system. Total: **E {fuel_added*cost_per_ltr:,.2f}**")
                    st.info(f"📏 {fuel_added:.0f} L → approx. **{fuel_added/(FUEL_BASE_L_PER_100/100):.0f} km** range.")
                else:
                    enqueue(record, "fuel")
                    st.warning("📶 Offline — fill-up queued for sync.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — DRIVING EVENTS
# ─────────────────────────────────────────────────────────────────────────────
with tab_events:
    st.markdown("### Log Driving Event / Incident")
    st.caption("Fleet manager sees critical events immediately in the main KSM system.")

    if not tid:
        st.info("Select a truck above.")
    else:
        with st.form("event_form", clear_on_submit=True):
            st.markdown('<div class="ksm-section-title">Incident Details</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                event_type = st.selectbox("Event Type", EVENT_TYPES)
            with c2:
                severity = st.selectbox("Severity", ["Low", "Medium", "High", "Critical"])
            sev_c = {"Low":"#60a5fa","Medium":"#fbbf24","High":"#f97316","Critical":"#f87171"}.get(severity,"#60a5fa")
            sev_i = {"Low":"ℹ️","Medium":"⚠️","High":"🔶","Critical":"🚨"}.get(severity,"ℹ️")
            st.markdown(
                f'<div style="background:rgba(15,23,42,0.5);border:1px solid {sev_c}40;border-radius:8px;padding:6px 12px;font-size:0.76rem;color:{sev_c};">'
                f'{sev_i} <b>{severity} severity</b> — {"Fleet manager alerted immediately." if severity in ("High","Critical") else "Logged in fleet system."}</div>',
                unsafe_allow_html=True,
            )
            event_loc  = st.text_input("Location / Nearest Town", placeholder="e.g. N2 near Oshoek border")
            event_desc = st.text_area("Description", placeholder="Describe what happened, action taken, and current status.", height=85)
            event_date = st.date_input("Date", value=date.today(), key="event_date_input")
            evt_submit = st.form_submit_button("🚨 Submit Event", type="primary", use_container_width=True)

        if evt_submit:
            if not event_desc.strip():
                st.error("Please provide a description.")
            else:
                record = {
                    "truck_id": tid, "date": event_date.strftime("%Y-%m-%d"),
                    "event_type": event_type, "severity": severity,
                    "location": event_loc, "description": event_desc, "odometer": current_odo,
                }
                if db_ok and save_event(record):
                    st.success("✅ Event logged — visible to fleet manager in the main KSM system.")
                    if severity in ("High", "Critical"):
                        st.error(f"🚨 {severity.upper()} event recorded. Fleet manager notified.")
                else:
                    enqueue(record, "event")
                    st.warning("📶 Offline — event queued. Will sync when reconnected.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — PERFORMANCE DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
with tab_perf:
    st.markdown("### Driver Performance Dashboard")
    st.caption("30-day performance summary powered by AI analysis of your trip data.")

    if not tid:
        st.info("Select a truck above.")
    elif not db_ok:
        st.warning("⚠️ Database not reachable.")
    else:
        stats   = get_driver_performance_stats(tid)
        avg_eff = get_avg_efficiency(tid)
        rev_30  = get_revenue_30d(tid)

        if not stats:
            st.info("No trip data in the last 30 days. Start logging trips to see performance here.")
        else:
            expected_base = 100 / FUEL_BASE_L_PER_100
            score_eff   = min(100, (stats["avg_eff"] / expected_base) * 100) if stats["avg_eff"] > 0 else 50
            score_brake = max(0, 100 - stats["avg_braking"] * 8)
            score_idle  = max(0, 100 - stats["avg_idle"] / 2)
            composite   = round(score_eff * 0.50 + score_brake * 0.30 + score_idle * 0.20)
            sc    = "#34d399" if composite >= 80 else ("#fbbf24" if composite >= 60 else "#f87171")
            label = "Excellent" if composite >= 85 else ("Good" if composite >= 70 else ("Average" if composite >= 55 else "Needs Improvement"))

            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(30,58,138,0.5),rgba(15,23,42,0.7));
                        border:1px solid rgba(96,165,250,0.22);border-radius:14px;
                        padding:1.1rem 1.4rem;margin-bottom:1.2rem;display:flex;align-items:center;gap:18px;">
                <div style="text-align:center;min-width:76px;">
                    <div style="font-size:2.7rem;font-weight:800;color:{sc};font-family:'JetBrains Mono',monospace;line-height:1;">{composite}</div>
                    <div style="font-size:0.63rem;font-weight:800;letter-spacing:0.12em;color:{sc};text-transform:uppercase;">{label}</div>
                </div>
                <div style="flex:1;">
                    <div style="font-size:0.97rem;font-weight:700;color:#fff;margin-bottom:4px;">Overall Driver Performance Score</div>
                    <div style="font-size:0.76rem;color:#94a3b8;">Based on {stats['trips_30d']} trips · Fuel 50% · Braking 30% · Idle 20%</div>
                </div>
            </div>""", unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Trips (30d)",     stats["trips_30d"])
            m2.metric("Avg Efficiency",  f"{stats['avg_eff']:.2f} km/L" if stats["avg_eff"] else "—")
            m3.metric("Avg Brakes/Trip", f"{stats['avg_braking']:.1f}")
            m4.metric("Revenue (30d)",   f"E {rev_30:,.0f}")

            st.markdown("#### 🤖 AI Performance Insights")
            expected = 100 / FUEL_BASE_L_PER_100
            if stats["avg_eff"] > 0:
                eff_pct = ((stats["avg_eff"] - expected) / expected) * 100
                if eff_pct >= 5:
                    st.markdown(f'<div class="insight-card"><b style="color:#34d399;">✅ Fuel Efficiency — Above Average</b><p style="font-size:0.79rem;color:#cbd5e1;margin-top:5px;">Your average of <b>{stats["avg_eff"]:.2f} km/L</b> is <b>{eff_pct:.1f}% above</b> fleet baseline. Keep it up!</p></div>', unsafe_allow_html=True)
                elif eff_pct < -10:
                    st.markdown(f'<div class="insight-card" style="border-color:rgba(220,38,38,0.4);"><b style="color:#f87171;">🔴 Fuel Efficiency — Below Average</b><p style="font-size:0.79rem;color:#cbd5e1;margin-top:5px;">Average of <b>{stats["avg_eff"]:.2f} km/L</b> is <b>{abs(eff_pct):.1f}% below</b> baseline. Check tyres, reduce load, avoid heavy acceleration.</p></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="insight-card"><b style="color:#60a5fa;">🔵 Fuel Efficiency — On Target</b><p style="font-size:0.79rem;color:#cbd5e1;margin-top:5px;">Average of <b>{stats["avg_eff"]:.2f} km/L</b> is within normal range.</p></div>', unsafe_allow_html=True)
            if stats["avg_braking"] >= 4:
                st.markdown(f'<div class="insight-card" style="border-color:rgba(245,158,11,0.4);"><b style="color:#fbbf24;">⚠️ Braking Behaviour — Needs Improvement</b><p style="font-size:0.79rem;color:#cbd5e1;margin-top:5px;">Averaging <b>{stats["avg_braking"]:.1f} hard braking events per trip</b>. Anticipate stops earlier.</p></div>', unsafe_allow_html=True)
            elif stats["avg_braking"] <= 1:
                st.markdown(f'<div class="insight-card"><b style="color:#34d399;">✅ Braking Behaviour — Excellent</b><p style="font-size:0.79rem;color:#cbd5e1;margin-top:5px;">Only <b>{stats["avg_braking"]:.1f} hard braking events per trip</b>. Outstanding smooth driving!</p></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — TRIP HISTORY
# ─────────────────────────────────────────────────────────────────────────────
with tab_hist:
    st.markdown("### Recent Trip History")
    st.caption("Your last 10 trips from the shared fleet database.")

    if not tid:
        st.info("Select a truck above.")
    elif not db_ok:
        st.warning("⚠️ Database not reachable.")
    else:
        avg_eff = get_avg_efficiency(tid)
        rows    = get_trip_history(tid)

        if avg_eff:
            m1, m2, m3 = st.columns(3)
            m1.metric("10-Trip Avg Efficiency", f"{avg_eff:.2f} km/L")
            m2.metric("Current Odometer",       f"{current_odo:,.0f} km")
            m3.metric("Trips Shown",             len(rows))

        if not rows:
            st.info("No trips found for this truck.")
        else:
            for row in rows:
                (trip_date_str, origin, dest, dist, fuel, eff, dur, load, brake, idle) = row
                eff_str  = f"{eff:.2f} km/L" if eff else "—"
                fuel_str = f"{fuel:.1f} L"   if fuel else "—"
                dist_str = f"{dist:.0f} km"  if dist else "—"
                dur_str  = f"{dur:.1f} h"    if dur  else "—"
                if eff and avg_eff:
                    d = (eff - avg_eff) / avg_eff
                    eff_c = "#34d399" if d >= 0.05 else ("#f87171" if d < -0.15 else "#fbbf24")
                    arrow = "↑" if d >= 0.05 else ("↓" if d < -0.10 else "→")
                else:
                    eff_c, arrow = "#94a3b8", ""
                brake_i = "🔴" if (brake or 0) >= 5 else ("🟡" if (brake or 0) >= 2 else "🟢")
                st.markdown(f"""
                <div class="history-row">
                    <div class="history-route">{origin} → {dest}<span style="float:right;font-size:0.71rem;color:#64748b;">{trip_date_str}</span></div>
                    <div class="history-meta">
                        <span>📏 {dist_str}</span><span>⛽ {fuel_str}</span><span>⏱️ {dur_str}</span>
                        <span style="color:{eff_c};font-weight:700;">{arrow} {eff_str}</span>
                        <span>{brake_i} {brake or 0} brakes</span>
                    </div>
                </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — MY PROFILE
# ─────────────────────────────────────────────────────────────────────────────
with tab_prof:
    st.markdown("### My Driver Profile")
    st.caption("Your personal details linked to your Driver ID. Managed by your fleet manager.")

    if not tid or not sel_row:
        st.info("Select a truck above.")
    else:
        (t_id, t_reg, t_driver, t_mileage, t_tank, t_drv_id,
         t_license, t_phone, t_id_num, t_exp, t_routes, t_certs,
         t_status, t_model) = sel_row

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(5,150,105,0.2),rgba(6,78,59,0.35));
                    border:1px solid rgba(52,211,153,0.35);border-radius:16px;padding:20px 22px;margin-bottom:1.2rem;">
            <div style="font-size:0.62rem;font-weight:800;letter-spacing:0.14em;color:#34d399;text-transform:uppercase;margin-bottom:14px;border-bottom:1px solid rgba(52,211,153,0.2);padding-bottom:8px;">
                🪪 Official Driver ID Card — KSM Smart Freight Solutions</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
                <div><div style="font-size:0.63rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">Full Name</div><div style="font-size:1.0rem;font-weight:700;color:#fff;">{t_driver or "—"}</div></div>
                <div><div style="font-size:0.63rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">Driver ID</div><div style="font-size:1.0rem;font-weight:700;color:#6ee7b7;font-family:'JetBrains Mono',monospace;">{t_drv_id or "—"}</div></div>
                <div><div style="font-size:0.63rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">Assigned Truck</div><div style="font-size:0.9rem;font-weight:700;color:#93c5fd;">{t_reg} — {t_model or ""}</div></div>
                <div><div style="font-size:0.63rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">Status</div><div style="font-size:0.9rem;font-weight:700;color:#34d399;">{t_status or "ACTIVE"}</div></div>
                <div><div style="font-size:0.63rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">License Number</div><div style="font-size:0.9rem;font-weight:600;color:#e2e8f0;">{t_license or "—"}</div></div>
                <div><div style="font-size:0.63rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">ID / Passport</div><div style="font-size:0.9rem;font-weight:600;color:#e2e8f0;">{t_id_num or "—"}</div></div>
                <div><div style="font-size:0.63rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">Phone</div><div style="font-size:0.9rem;font-weight:600;color:#e2e8f0;">{t_phone or "—"}</div></div>
                <div><div style="font-size:0.63rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">Experience</div><div style="font-size:0.9rem;font-weight:600;color:#e2e8f0;">{t_exp or 0} years</div></div>
                <div><div style="font-size:0.63rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">Assigned Routes</div><div style="font-size:0.9rem;font-weight:600;color:#e2e8f0;">{t_routes or "All routes"}</div></div>
                <div><div style="font-size:0.63rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">Certifications</div><div style="font-size:0.9rem;font-weight:600;color:#e2e8f0;">{t_certs or "Standard licence"}</div></div>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("#### Update My Contact Details")
        with st.form("profile_form", clear_on_submit=False):
            new_phone   = st.text_input("Phone Number", value=t_phone or "", placeholder="+268 7xxx xxxx")
            new_license = st.text_input("License Number", value=t_license or "")
            new_id_num  = st.text_input("National ID / Passport Number", value=t_id_num or "")
            new_certs   = st.text_input("Certifications", value=t_certs or "", placeholder="e.g. Hazmat, Refrigerated, Cross-border")
            new_routes  = st.text_input("Assigned Routes", value=t_routes or "", placeholder="e.g. Eswatini, South Africa, Mozambique")
            save_profile = st.form_submit_button("💾 Save Profile", type="primary", use_container_width=True)

        if save_profile and db_ok:
            try:
                conn = get_conn()
                conn.execute(
                    """UPDATE Truck SET driver_phone=?, driver_license=?, driver_id_number=?,
                       driver_certifications=?, driver_routes=? WHERE truck_id=?""",
                    (new_phone, new_license, new_id_num, new_certs, new_routes, tid)
                )
                conn.commit(); conn.close()
                st.success("✅ Profile updated successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — SYNC
# ─────────────────────────────────────────────────────────────────────────────
with tab_sync:
    st.markdown("### Sync & Connection Status")
    total_pending = offline_count("trip") + offline_count("fuel") + offline_count("event")

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("DB Status",     "🟢 Live" if db_ok else "🔴 Offline")
    s2.metric("Trips Pending",  offline_count("trip"))
    s3.metric("Fuel Pending",   offline_count("fuel"))
    s4.metric("Events Pending", offline_count("event"))

    if total_pending == 0:
        st.success("✅ All records synced with the main KSM system. No pending data.")
    else:
        if not db_ok:
            st.error("⚠️ Database not reachable. Ensure fleet.db is in the same directory.")
        else:
            if st.button("🔄 Sync All Pending Records Now", use_container_width=True):
                results = sync_all()
                synced  = results["trips"] + results["fuel"] + results["events"]
                if synced:
                    st.success(f"✅ Synced — {results['trips']} trip(s), {results['fuel']} fuel record(s), {results['events']} event(s).")
                if results["failed"]:
                    st.warning(f"⚠️ {results['failed']} record(s) remain in queue.")
                elif synced:
                    st.balloons()

    if total_pending:
        st.markdown("---"); st.markdown("#### 📋 Offline Queue")
        for rec in st.session_state.get("offline_trip", []):
            st.markdown(f'<div class="queue-item"><span style="color:#fbbf24;font-size:0.67rem;font-weight:800;">TRIP</span> &nbsp; {rec.get("origin","?")} → {rec.get("destination","?")} &nbsp;|&nbsp; {rec.get("date","")} &nbsp;|&nbsp; {rec.get("distance",0):.0f} km</div>', unsafe_allow_html=True)
        for rec in st.session_state.get("offline_fuel", []):
            st.markdown(f'<div class="queue-item"><span style="color:#fbbf24;font-size:0.67rem;font-weight:800;">FUEL</span> &nbsp; {rec.get("fuel_added",0):.0f} L @ {rec.get("station","?")} &nbsp;|&nbsp; {rec.get("date","")}</div>', unsafe_allow_html=True)
        for rec in st.session_state.get("offline_event", []):
            st.markdown(f'<div class="queue-item"><span style="color:#fbbf24;font-size:0.67rem;font-weight:800;">EVENT</span> &nbsp; {rec.get("event_type","?")} &nbsp;|&nbsp; {rec.get("severity","")} &nbsp;|&nbsp; {rec.get("date","")}</div>', unsafe_allow_html=True)

    st.markdown("---"); st.markdown("#### ⚙️ System Info")
    st.markdown(f"""
    <div class="sysinfo">
        <b style="color:#60a5fa;">Driver terminal</b> &emsp; driver_app.py — port 8502<br>
        <b style="color:#60a5fa;">Main system</b>     &emsp; yizo.py — port 8501<br>
        <b style="color:#60a5fa;">Database</b>        &emsp; {os.path.abspath(DB_PATH)}<br>
        <b style="color:#60a5fa;">DB status</b>       &emsp; {"✅ Live" if db_ok else "❌ Offline"}<br>
        <b style="color:#60a5fa;">Logged in</b>       &emsp; {drv_id}<br>
        <b style="color:#60a5fa;">Version</b>         &emsp; 4.0.0<br>
    </div>""", unsafe_allow_html=True)

# =============================================================================
# FOOTER
# =============================================================================
st.divider()
st.markdown(
    f"<div style='text-align:center;font-size:0.71rem;color:#475569;'>"
    f"KSM Smart AI Freight Solutions &nbsp;·&nbsp; Driver Terminal v4.0 &nbsp;·&nbsp; "
    f"Signed in: {drv_id} &nbsp;·&nbsp; Integrated with Main System (yizo.py)"
    f"</div>",
    unsafe_allow_html=True,
)
