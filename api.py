"""
api.py — Flask REST API Server
Barcha HTTP endpointlar shu yerda.

Ishga tushirish:
    python api.py

O'rnatish:
    pip install flask flask-cors
"""

import logging
from datetime import datetime
from functools import wraps
from typing import Tuple, Any

from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

from config import Config
from database import Database
from smart_room import (
    SmartRoomSystem, SensorData,
    FaceRecognitionModule, ProfileManager,
    CurtainController, MultiUserDecision,
    AdaptiveLearning, UserProfile
)

# ─────────────────────────────────────────
# FLASK ILOVASI
# ─────────────────────────────────────────

app  = Flask(__name__)
CORS(app)
app.secret_key = Config.SECRET_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ── Global ob'ektlar ────────────────────
db          = Database()
face_rec    = FaceRecognitionModule(db_path=Config.FACE_DB_PATH)
profiles    = ProfileManager(db_path=Config.PROFILES_DB)
curtain_ctl = CurtainController()
multi_user  = MultiUserDecision()
rl          = AdaptiveLearning(profiles)
sensors_sim = None   # MQTT simulyatori (ixtiyoriy)


# ─────────────────────────────────────────
# YORDAMCHI FUNKSIYALAR
# ─────────────────────────────────────────

def ok(data: Any = None, msg: str = "OK", code: int = 200):
    return jsonify({"success": True,  "message": msg,   "data": data}), code

def err(msg: str, code: int = 400):
    return jsonify({"success": False, "message": msg,   "data": None}), code

def require_json(f):
    """JSON body talab qiluvchi endpointlar uchun decorator"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return err("Content-Type: application/json bo'lishi kerak", 415)
        return f(*args, **kwargs)
    return wrapper


# ─────────────────────────────────────────
# ASOSIY SAHIFA (mini dashboard)
# ─────────────────────────────────────────

@app.route("/")
def index():
    stats = db.dashboard_stats()
    return render_template_string(DASHBOARD_HTML, stats=stats)


# ─────────────────────────────────────────
# SENSOR ENDPOINTLARI
# ─────────────────────────────────────────

@app.route("/api/sensors/current", methods=["GET"])
def sensors_current():
    """Joriy sensor qiymatlarini qaytarish"""
    from smart_room import SensorManager
    s = SensorManager()
    data = s.read_all()
    db.log_sensor(data.temperature, data.humidity, data.lux,
                  data.uv_index, data.motion, data.occupancy)
    return ok(data.__dict__)


@app.route("/api/sensors/history", methods=["GET"])
def sensors_history():
    """So'nggi sensor yozuvlarini qaytarish"""
    limit = min(int(request.args.get("limit", 50)), 500)
    return ok(db.get_sensor_history(limit))


@app.route("/api/sensors/stats", methods=["GET"])
def sensors_stats():
    """24 soatlik sensor statistikasi"""
    return ok(db.get_sensor_stats())


@app.route("/api/sensors/ingest", methods=["POST"])
@require_json
def sensors_ingest():
    """ESP32 dan MQTT o'rniga to'g'ridan-to'g'ri POST orqali ma'lumot qabul qilish"""
    d = request.json
    try:
        db.log_sensor(
            d["temperature"], d["humidity"], d["lux"],
            d.get("uv_index", 0), d.get("motion", False), d.get("occupancy", 0)
        )
        return ok(msg="Sensor ma'lumoti saqlandi")
    except KeyError as e:
        return err(f"Maydon yetishmayapti: {e}")


# ─────────────────────────────────────────
# YUZ TANISH ENDPOINTLARI
# ─────────────────────────────────────────

@app.route("/api/face/identify", methods=["POST"])
def face_identify():
    """Yuz tanish — foydalanuvchini identifikatsiya qilish"""
    user_id, confidence = face_rec.identify()
    db.log_face_event(user_id, confidence, "identify")

    if user_id:
        db.increment_visit(user_id)
        user = db.get_user(user_id)
        return ok({
            "identified":  True,
            "user_id":     user_id,
            "name":        user["name"] if user else user_id,
            "confidence":  round(confidence * 100, 1),
        })
    return ok({
        "identified":  False,
        "user_id":     None,
        "confidence":  round(confidence * 100, 1),
    })


@app.route("/api/face/register", methods=["POST"])
@require_json
def face_register():
    """Yangi foydalanuvchi yuzini ro'yxatga olish"""
    d = request.json
    uid  = d.get("user_id")
    name = d.get("name")
    if not uid or not name:
        return err("user_id va name majburiy")

    face_rec.register_user(uid)
    db.upsert_user(uid, name,
                   preferred_temp=d.get("preferred_temp", 22.0),
                   preferred_hum=d.get("preferred_hum", 50.0),
                   preferred_lux=d.get("preferred_lux", 400.0),
                   photosensitivity=d.get("photosensitivity", 0.5))
    return ok(msg=f"{name} muvaffaqiyatli ro'yxatga olindi", code=201)


@app.route("/api/face/events", methods=["GET"])
def face_events():
    limit = min(int(request.args.get("limit", 30)), 200)
    return ok(db.get_face_events(limit))


# ─────────────────────────────────────────
# FOYDALANUVCHI PROFILLARI
# ─────────────────────────────────────────

@app.route("/api/users", methods=["GET"])
def users_list():
    return ok(db.get_all_users())


@app.route("/api/users/<user_id>", methods=["GET"])
def user_get(user_id: str):
    user = db.get_user(user_id)
    if not user:
        return err("Foydalanuvchi topilmadi", 404)
    return ok(user)


@app.route("/api/users/<user_id>/profile", methods=["PATCH"])
@require_json
def user_update_profile(user_id: str):
    """Foydalanuvchi qulaylik profilini yangilash"""
    user = db.get_user(user_id)
    if not user:
        return err("Foydalanuvchi topilmadi", 404)

    allowed = {"preferred_temp", "preferred_hum", "preferred_lux",
               "photosensitivity", "curtain_pct"}
    updates = {k: v for k, v in request.json.items() if k in allowed}

    if not updates:
        return err("Yangilanadigan maydon topilmadi")

    db.update_user_preference(user_id, **updates)
    return ok(msg="Profil yangilandi", data=updates)


@app.route("/api/users/<user_id>/feedback", methods=["POST"])
@require_json
def user_feedback(user_id: str):
    """
    Foydalanuvchi mamnuniyati feedbacki.
    reward: -1.0 (yomon) ~ 0.0 (neytral) ~ +1.0 (yaxshi)
    """
    reward = float(request.json.get("reward", 0.0))
    reward = max(-1.0, min(1.0, reward))

    from smart_room import SensorManager
    sensor = SensorManager().read_all()

    profile = profiles.get(user_id)
    if not profile:
        return err("Profil topilmadi", 404)

    rl.feedback(user_id, sensor, reward)
    state_key = f"{round(sensor.temperature)}_{round(sensor.lux, -1)}"
    db.log_rl_feedback(user_id, reward, state_key, 0, 0)

    return ok(msg="Feedback saqlandi va RL modeli yangilandi")


# ─────────────────────────────────────────
# XONA BOSHQARUVI
# ─────────────────────────────────────────

@app.route("/api/room/apply/<user_id>", methods=["POST"])
def room_apply_profile(user_id: str):
    """Bitta foydalanuvchi profilini xonaga qo'llash"""
    user = db.get_user(user_id)
    if not user:
        return err("Foydalanuvchi topilmadi", 404)

    from smart_room import SensorManager
    sensor = SensorManager().read_all()

    curtain_pct = curtain_ctl.calculate_curtain_position(
        sensor.uv_index,
        user["photosensitivity"],
        sensor.lux,
        user["preferred_lux"]
    )

    settings = {
        "temp":        user["preferred_temp"],
        "humidity":    user["preferred_hum"],
        "lux":         user["preferred_lux"],
        "curtain_pct": curtain_pct,
        "ac_on":       sensor.temperature > user["preferred_temp"] + 0.5,
        "lights_on":   sensor.lux < user["preferred_lux"] * 0.8,
        "servo_cmd":   curtain_ctl.servo_command(curtain_pct),
    }

    db.log_room_settings(user_id, settings["temp"], settings["humidity"],
                         settings["lux"], curtain_pct)

    return ok(data=settings, msg=f"{user['name']} profili qo'llandi")


@app.route("/api/room/multi", methods=["POST"])
@require_json
def room_multi_user():
    """Ko'p foydalanuvchi uchun kompromis sozlamalarni hisoblash"""
    user_ids = request.json.get("user_ids", [])
    if not user_ids:
        return err("user_ids ro'yxati bo'sh")

    profile_objs = []
    for uid in user_ids:
        p = profiles.get(uid)
        if p:
            profile_objs.append(p)

    if not profile_objs:
        return err("Hech bir profil topilmadi", 404)

    result = multi_user.resolve(profile_objs)

    db.log_room_settings(
        applied_by=",".join(user_ids),
        temp=result["temp"], hum=result["humidity"],
        lux=result["lux"], curtain=result["curtain_pct"], multi=True
    )
    return ok(data=result)


@app.route("/api/room/curtain", methods=["POST"])
@require_json
def room_set_curtain():
    """Pardani to'g'ridan-to'g'ri boshqarish"""
    pct = float(request.json.get("pct", 0))
    pct = max(0, min(100, pct))
    cmd = curtain_ctl.servo_command(pct)
    return ok({"curtain_pct": pct, "servo_cmd": cmd})


@app.route("/api/room/settings/history", methods=["GET"])
def room_settings_history():
    limit = min(int(request.args.get("limit", 30)), 200)
    return ok(db.get_room_settings_history(limit))


# ─────────────────────────────────────────
# DASHBOARD STATISTIKA
# ─────────────────────────────────────────

@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    return ok(db.dashboard_stats())


@app.route("/api/rl/stats", methods=["GET"])
def rl_stats():
    return ok(db.get_rl_stats())


# ─────────────────────────────────────────
# SOGLOM HOLAT TEKSHIRUVI
# ─────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return ok({
        "status":    "healthy",
        "version":   "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "modules": {
            "database":       True,
            "face_rec":       True,
            "rl":             True,
            "curtain":        True,
            "multi_user":     True,
        }
    })


# ─────────────────────────────────────────
# MINI DASHBOARD HTML (browser orqali ko'rish)
# ─────────────────────────────────────────

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aqlli Xona — API</title>
<style>
  body{font-family:system-ui,sans-serif;margin:0;padding:2rem;background:#f5f5f5;color:#111}
  h1{margin:0 0 1.5rem;font-size:1.5rem}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin-bottom:2rem}
  .card{background:#fff;border:1px solid #e5e5e5;border-radius:10px;padding:1rem}
  .card .label{font-size:12px;color:#888;margin-bottom:4px}
  .card .val{font-size:26px;font-weight:600}
  table{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden}
  th,td{padding:10px 14px;text-align:left;font-size:13px;border-bottom:1px solid #eee}
  th{background:#f9f9f9;font-weight:500;color:#555}
  code{background:#f0f0f0;padding:2px 6px;border-radius:4px;font-size:12px}
  .badge{padding:2px 10px;border-radius:20px;font-size:11px;font-weight:500}
  .green{background:#e6f4ee;color:#0a6e4a}
  .blue{background:#e6f0fb;color:#1a5fa0}
</style>
</head>
<body>
<h1>🏠 Aqlli Xona Boshqaruv Tizimi — API</h1>
<div class="grid">
  <div class="card"><div class="label">Foydalanuvchilar</div><div class="val">{{ stats.users_count }}</div></div>
  <div class="card"><div class="label">Bugungi hodisalar</div><div class="val">{{ stats.events_today }}</div></div>
  <div class="card"><div class="label">O'rtacha harorat</div><div class="val">{{ stats.sensor_stats.get('avg_temp','—') }}°C</div></div>
  <div class="card"><div class="label">Energiya tejash</div><div class="val">{{ stats.energy_savings }}%</div></div>
</div>
<h2 style="font-size:1.1rem;margin-bottom:1rem">API Endpointlar</h2>
<table>
<thead><tr><th>Metod</th><th>URL</th><th>Tavsif</th></tr></thead>
<tbody>
{% for row in [
  ('GET','  /api/health',              'Tizim holati'),
  ('GET','  /api/sensors/current',     'Joriy sensor qiymatlari'),
  ('GET','  /api/sensors/history',     'Sensor tarixi'),
  ('GET','  /api/sensors/stats',       '24 soatlik statistika'),
  ('POST', '/api/sensors/ingest',      'ESP32 dan ma\'lumot qabul qilish'),
  ('POST', '/api/face/identify',       'Yuz tanish'),
  ('POST', '/api/face/register',       'Yangi foydalanuvchi ro\'yxatga olish'),
  ('GET',  '/api/face/events',         'Yuz tanish hodisalari'),
  ('GET',  '/api/users',               'Barcha foydalanuvchilar'),
  ('GET',  '/api/users/<id>',          'Bitta foydalanuvchi'),
  ('PATCH','/api/users/<id>/profile',  'Profilni yangilash'),
  ('POST', '/api/users/<id>/feedback', 'RL feedback'),
  ('POST', '/api/room/apply/<id>',     'Profil qo\'llash'),
  ('POST', '/api/room/multi',          'Ko\'p foydalanuvchi'),
  ('POST', '/api/room/curtain',        'Parda boshqaruvi'),
  ('GET',  '/api/dashboard',           'Dashboard statistika'),
  ('GET',  '/api/rl/stats',            'RL model statistikasi'),
] %}
<tr>
  <td><span class="badge {{ 'green' if row[0]=='GET' else 'blue' }}">{{ row[0] }}</span></td>
  <td><code>{{ row[1] }}</code></td>
  <td>{{ row[2] }}</td>
</tr>
{% endfor %}
</tbody>
</table>
</body>
</html>
"""


# ─────────────────────────────────────────
# ISHGA TUSHIRISH
# ─────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Aqlli Xona API serveri ishga tushmoqda...")
    logger.info("Dashboard: http://localhost:%d", Config.PORT)
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
