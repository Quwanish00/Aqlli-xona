"""
config.py — Tizim konfiguratsiyasi
Barcha o'zgaruvchilar shu yerda boshqariladi.
"""

import os

class Config:
    # ── Server ─────────────────────────────
    HOST            = os.getenv("HOST", "0.0.0.0")
    PORT            = int(os.getenv("PORT", 5000))
    DEBUG           = os.getenv("DEBUG", "false").lower() == "true"
    SECRET_KEY      = os.getenv("SECRET_KEY", "smart-room-secret-2025")

    # ── Ma'lumotlar bazasi ─────────────────
    # SQLite (oddiy, faylga asoslangan) — ishga tushirish uchun
    DATABASE_URL    = os.getenv("DATABASE_URL", "sqlite:///smart_room.db")
    # PostgreSQL uchun: "postgresql://user:pass@localhost/smart_room"

    # ── MQTT Broker ────────────────────────
    MQTT_HOST       = os.getenv("MQTT_HOST", "localhost")
    MQTT_PORT       = int(os.getenv("MQTT_PORT", 1883))
    MQTT_USERNAME   = os.getenv("MQTT_USERNAME", "")
    MQTT_PASSWORD   = os.getenv("MQTT_PASSWORD", "")
    MQTT_KEEPALIVE  = 60

    # MQTT mavzulari (topics)
    TOPIC_SENSORS   = "smartroom/sensors"
    TOPIC_COMMANDS  = "smartroom/commands"
    TOPIC_FACE      = "smartroom/face"
    TOPIC_STATUS    = "smartroom/status"

    # ── Sensorlar ──────────────────────────
    SENSOR_INTERVAL = 5       # soniya (o'qish oralig'i)
    TEMP_MIN        = 16.0
    TEMP_MAX        = 30.0
    HUM_MIN         = 30.0
    HUM_MAX         = 70.0
    LUX_MIN         = 50.0
    LUX_MAX         = 1000.0

    # ── Yuz tanish ─────────────────────────
    FACE_THRESHOLD  = 0.60    # kosinus o'xshashlik chegarasi
    FACE_DB_PATH    = "data/faces.json"
    UNKNOWN_TIMEOUT = 10      # soniya (noma'lum shaxs uchun kutish)

    # ── RL parametrlari ────────────────────
    RL_ALPHA        = 0.10    # o'rganish tezligi
    RL_GAMMA        = 0.90    # chegirma koeffitsienti
    RL_EPSILON      = 0.20    # exploration darajasi
    RL_TEMP_STEP    = 0.5     # °C qadami
    RL_LUX_STEP     = 20.0    # lux qadami

    # ── Parda ──────────────────────────────
    CURTAIN_SERVO_MIN_PWM = 1000   # µs
    CURTAIN_SERVO_MAX_PWM = 2000   # µs

    # ── Fayl yo'llari ──────────────────────
    PROFILES_DB     = "data/profiles.json"
    LOGS_DIR        = "logs/"
    MODELS_DIR      = "models/"
