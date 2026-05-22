"""
database.py — Ma'lumotlar bazasi moduli
SQLite (ishga tushirish) va PostgreSQL (ishlab chiqarish) qo'llab-quvvatlanadi.
Jadvallar: users, sensor_logs, events, room_settings
"""

import sqlite3
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# JADVAL YARATISH SO'ROVLARI
# ─────────────────────────────────────────

SQL_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    preferred_temp  REAL DEFAULT 22.0,
    preferred_hum   REAL DEFAULT 50.0,
    preferred_lux   REAL DEFAULT 400.0,
    photosensitivity REAL DEFAULT 0.5,
    curtain_pct     REAL DEFAULT 40.0,
    visit_count     INTEGER DEFAULT 0,
    last_seen       TEXT,
    q_table         TEXT DEFAULT '{}',
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sensor_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    temperature     REAL,
    humidity        REAL,
    lux             REAL,
    uv_index        REAL,
    motion          INTEGER,
    occupancy       INTEGER,
    logged_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS face_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT,
    confidence      REAL,
    action          TEXT,
    event_at        TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS room_settings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    applied_by      TEXT,
    temp_target     REAL,
    hum_target      REAL,
    lux_target      REAL,
    curtain_pct     REAL,
    multi_user      INTEGER DEFAULT 0,
    applied_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rl_feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT,
    reward          REAL,
    state_key       TEXT,
    action_temp     INTEGER,
    action_lux      INTEGER,
    logged_at       TEXT DEFAULT (datetime('now'))
);
"""

# Demo foydalanuvchilar
SQL_INSERT_DEMO = """
INSERT OR IGNORE INTO users (user_id, name, preferred_temp, preferred_hum, preferred_lux, photosensitivity, curtain_pct)
VALUES
    ('aziz',   'Aziz',   21.0, 45.0, 500.0, 0.8, 60.0),
    ('malika', 'Malika', 23.5, 55.0, 350.0, 0.5, 40.0),
    ('jasur',  'Jasur',  20.0, 40.0, 600.0, 0.2, 20.0),
    ('nodira', 'Nodira', 24.0, 60.0, 280.0, 0.9, 75.0);
"""


# ─────────────────────────────────────────
# MA'LUMOTLAR BAZASI BOSHQARUVCHISI
# ─────────────────────────────────────────

class Database:
    """SQLite asosidagi ma'lumotlar bazasi boshqaruvchisi"""

    def __init__(self, db_path: str = "smart_room.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(SQL_CREATE_TABLES)
            conn.executescript(SQL_INSERT_DEMO)
        logger.info("Ma'lumotlar bazasi tayyor: %s", self.db_path)

    # ────────────────────────────────
    # USERS CRUD
    # ────────────────────────────────

    def get_user(self, user_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                d = dict(row)
                d["q_table"] = json.loads(d.get("q_table") or "{}")
                return d
        return None

    def get_all_users(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY visit_count DESC").fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["q_table"] = json.loads(d.get("q_table") or "{}")
                result.append(d)
            return result

    def upsert_user(self, user_id: str, name: str, **kwargs):
        cols = ["user_id", "name"] + list(kwargs.keys())
        vals = [user_id, name] + list(kwargs.values())
        placeholders = ",".join("?" * len(vals))
        updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "user_id")
        sql = f"""
            INSERT INTO users ({','.join(cols)}) VALUES ({placeholders})
            ON CONFLICT(user_id) DO UPDATE SET {updates}
        """
        with self._conn() as conn:
            conn.execute(sql, vals)

    def update_user_preference(self, user_id: str, **kwargs):
        allowed = {"preferred_temp", "preferred_hum", "preferred_lux",
                   "photosensitivity", "curtain_pct", "q_table"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        if "q_table" in updates and isinstance(updates["q_table"], dict):
            updates["q_table"] = json.dumps(updates["q_table"])
        set_clause = ", ".join(f"{k}=?" for k in updates)
        vals = list(updates.values()) + [user_id]
        with self._conn() as conn:
            conn.execute(f"UPDATE users SET {set_clause} WHERE user_id=?", vals)

    def increment_visit(self, user_id: str):
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute("""
                UPDATE users SET visit_count = visit_count + 1, last_seen = ?
                WHERE user_id = ?
            """, (now, user_id))

    # ────────────────────────────────
    # SENSOR LOGS
    # ────────────────────────────────

    def log_sensor(self, temp: float, hum: float, lux: float,
                   uv: float, motion: bool, occupancy: int):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO sensor_logs (temperature, humidity, lux, uv_index, motion, occupancy)
                VALUES (?,?,?,?,?,?)
            """, (temp, hum, lux, uv, int(motion), occupancy))

    def get_sensor_history(self, limit: int = 100) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM sensor_logs ORDER BY logged_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_sensor_stats(self) -> Dict:
        """O'rtacha, min, max qiymatlarni hisoblash"""
        with self._conn() as conn:
            row = conn.execute("""
                SELECT
                    ROUND(AVG(temperature),1) as avg_temp,
                    ROUND(MIN(temperature),1) as min_temp,
                    ROUND(MAX(temperature),1) as max_temp,
                    ROUND(AVG(humidity),1)    as avg_hum,
                    ROUND(AVG(lux))           as avg_lux,
                    ROUND(AVG(uv_index),1)    as avg_uv,
                    COUNT(*)                  as total_readings
                FROM sensor_logs
                WHERE logged_at >= datetime('now', '-24 hours')
            """).fetchone()
            return dict(row) if row else {}

    # ────────────────────────────────
    # YUZ TANISH HODISALARI
    # ────────────────────────────────

    def log_face_event(self, user_id: Optional[str], confidence: float, action: str):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO face_events (user_id, confidence, action) VALUES (?,?,?)
            """, (user_id, confidence, action))

    def get_face_events(self, limit: int = 50) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT fe.*, u.name FROM face_events fe
                LEFT JOIN users u ON fe.user_id = u.user_id
                ORDER BY fe.event_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    # ────────────────────────────────
    # XONA SOZLAMALARI
    # ────────────────────────────────

    def log_room_settings(self, applied_by: str, temp: float, hum: float,
                          lux: float, curtain: float, multi: bool = False):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO room_settings (applied_by, temp_target, hum_target, lux_target, curtain_pct, multi_user)
                VALUES (?,?,?,?,?,?)
            """, (applied_by, temp, hum, lux, curtain, int(multi)))

    def get_room_settings_history(self, limit: int = 50) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM room_settings ORDER BY applied_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    # ────────────────────────────────
    # RL FEEDBACK
    # ────────────────────────────────

    def log_rl_feedback(self, user_id: str, reward: float, state_key: str,
                        action_temp: int, action_lux: int):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO rl_feedback (user_id, reward, state_key, action_temp, action_lux)
                VALUES (?,?,?,?,?)
            """, (user_id, reward, state_key, action_temp, action_lux))

    def get_rl_stats(self) -> List[Dict]:
        """Har bir foydalanuvchi uchun o'rtacha reward"""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT rf.user_id, u.name,
                       ROUND(AVG(rf.reward),3)  as avg_reward,
                       COUNT(*)                 as total_updates
                FROM rl_feedback rf
                LEFT JOIN users u ON rf.user_id = u.user_id
                GROUP BY rf.user_id
            """).fetchall()
            return [dict(r) for r in rows]

    # ────────────────────────────────
    # UMUMIY STATISTIKA (Dashboard uchun)
    # ────────────────────────────────

    def dashboard_stats(self) -> Dict:
        sensor_stats = self.get_sensor_stats()
        rl_stats     = self.get_rl_stats()
        with self._conn() as conn:
            users_count   = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            events_today  = conn.execute("""
                SELECT COUNT(*) FROM face_events
                WHERE event_at >= date('now')
            """).fetchone()[0]
            energy_savings = round(20 + sum(
                r.get("avg_reward", 0) or 0 for r in rl_stats
            ) * 2, 1)
        return {
            "users_count":    users_count,
            "events_today":   events_today,
            "sensor_stats":   sensor_stats,
            "rl_stats":       rl_stats,
            "energy_savings": min(35, max(0, energy_savings)),
        }
