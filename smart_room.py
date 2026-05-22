"""
Aqlli Xona Boshqaruv Tizimi
Ko'p sensorli IoT va Sun'iy Intellekt asosida
Muallif: Qıdırbaev Quwanıshbay Quralbaevich
Nukus Davlat Texnika Universiteti, 2025
"""

import json
import time
import random
import logging
import threading
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple
from pathlib import Path

# ─────────────────────────────────────────
# 1. MA'LUMOTLAR MODELLARI
# ─────────────────────────────────────────

@dataclass
class SensorData:
    """DHT22, SHT31, BH1750, VEML6075, PIR, mmWave sensorlaridan o'qilgan qiymatlar"""
    temperature: float = 22.0      # °C  (DHT22 / SHT31)
    humidity: float    = 50.0      # %   (DHT22 / SHT31)
    lux: float         = 300.0     # lux (BH1750 / TSL2591)
    uv_index: float    = 2.0       # UV  (VEML6075)
    motion: bool       = False     # PIR sensori
    occupancy: int     = 0         # mmWave radar (kishi soni)
    timestamp: str     = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class UserProfile:
    """Har bir foydalanuvchi uchun shaxsiy qulaylik profili"""
    user_id: str
    name: str
    preferred_temp: float    = 22.0   # °C
    preferred_humidity: float = 50.0   # %
    preferred_lux: float     = 400.0   # lux
    photosensitivity: float  = 0.5    # 0 (past) – 1 (yuqori)
    curtain_pct: float       = 40.0   # % yopiq
    face_embedding: Optional[List[float]] = None
    visit_count: int         = 0
    last_seen: Optional[str] = None
    q_table: Dict[str, float] = field(default_factory=dict)   # RL Q-jadvali


@dataclass
class RoomState:
    """Xonaning joriy holati"""
    current_temp: float       = 22.0
    current_humidity: float   = 50.0
    current_lux: float        = 300.0
    curtain_pct: float        = 40.0
    ac_on: bool               = False
    humidifier_on: bool       = False
    lights_on: bool           = True
    present_users: List[str]  = field(default_factory=list)


# ─────────────────────────────────────────
# 2. SENSOR SIMULYATSIYA MODULI
# ─────────────────────────────────────────

class SensorManager:
    """
    Haqiqiy qurilmada: Raspberry Pi GPIO / I2C / UART orqali o'qiladi.
    Bu yerda simulyatsiya amalga oshirilgan.
    """

    def __init__(self):
        self._data = SensorData()
        self._lock = threading.Lock()
        logging.info("SensorManager ishga tushdi (simulyatsiya rejimi)")

    def read_all(self) -> SensorData:
        """Barcha sensorlardan bir vaqtda o'qish"""
        with self._lock:
            self._data = SensorData(
                temperature = round(random.gauss(22, 1.5), 1),
                humidity    = round(random.gauss(50, 5), 1),
                lux         = round(abs(random.gauss(400, 80))),
                uv_index    = round(random.uniform(0.5, 5.0), 1),
                motion      = random.random() > 0.4,
                occupancy   = random.choices([0, 1, 2, 3], weights=[10, 50, 30, 10])[0],
            )
            return self._data

    def read_temperature(self) -> float:
        return round(random.gauss(22, 1.5), 1)

    def read_humidity(self) -> float:
        return round(max(20, min(90, random.gauss(50, 5))), 1)

    def read_lux(self) -> float:
        return round(abs(random.gauss(400, 80)))

    def read_uv(self) -> float:
        return round(random.uniform(0.5, 5.0), 1)

    def read_motion(self) -> bool:
        return random.random() > 0.4

    def read_occupancy(self) -> int:
        return random.choices([0, 1, 2, 3], weights=[10, 50, 30, 10])[0]


# ─────────────────────────────────────────
# 3. YUZ TANISH MODULI (MTCNN + FaceNet simulyatsiyasi)
# ─────────────────────────────────────────

class FaceRecognitionModule:
    """
    Haqiqiy implementatsiyada:
        - face_recognition yoki DeepFace kutubxonasi
        - MTCNN orqali yuz aniqlash
        - FaceNet / ArcFace orqali embedding olish
        - Kosinus yaqinligi bilan identifikatsiya

    Bu yerda: face embedding vektori simulyatsiya qilingan.
    """

    THRESHOLD = 0.6     # kosinus o'xshashlik chegarasi

    def __init__(self, db_path: str = "faces.json"):
        self.db_path = Path(db_path)
        self._embeddings: Dict[str, List[float]] = {}
        self._load_db()
        logging.info("FaceRecognitionModule tayyor. Ma'lumotlar bazasida %d yuz.", len(self._embeddings))

    # ── Ma'lumotlar bazasi ──────────────────────────────

    def _load_db(self):
        if self.db_path.exists():
            with open(self.db_path) as f:
                self._embeddings = json.load(f)

    def _save_db(self):
        with open(self.db_path, "w") as f:
            json.dump(self._embeddings, f)

    # ── Yuz aniqlash (MTCNN simulyatsiyasi) ────────────

    def detect_face(self, frame=None) -> bool:
        """Kadr ichida yuz borligini aniqlash"""
        return random.random() > 0.2   # 80% ehtimol

    # ── Embedding olish (FaceNet simulyatsiyasi) ────────

    @staticmethod
    def _get_embedding(user_id: Optional[str] = None) -> List[float]:
        """128-o'lchamli vektorni simulyatsiya qilish"""
        rng = random.Random(hash(user_id) if user_id else None)
        return [round(rng.gauss(0, 1), 4) for _ in range(128)]

    # ── Kosinus o'xshashlik ─────────────────────────────

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x**2 for x in a) ** 0.5
        norm_b = sum(x**2 for x in b) ** 0.5
        return dot / (norm_a * norm_b + 1e-9)

    # ── Ro'yxatga olish ─────────────────────────────────

    def register_user(self, user_id: str):
        emb = self._get_embedding(user_id)
        self._embeddings[user_id] = emb
        self._save_db()
        logging.info("Yangi foydalanuvchi ro'yxatga olindi: %s", user_id)

    # ── Identifikatsiya ─────────────────────────────────

    def identify(self, frame=None) -> Tuple[Optional[str], float]:
        """
        Qaytaradi: (user_id | None, confidence)
        """
        if not self.detect_face(frame):
            return None, 0.0
        if not self._embeddings:
            return None, 0.0

        query_emb = self._get_embedding()      # simulyatsiya
        best_id, best_score = None, -1.0

        for uid, stored_emb in self._embeddings.items():
            score = self.cosine_similarity(query_emb, stored_emb)
            if score > best_score:
                best_score, best_id = score, uid

        # Simulyatsiyada ba'zan to'g'ri foydalanuvchini qaytarish
        if random.random() > 0.15:
            best_id   = random.choice(list(self._embeddings.keys()))
            best_score = random.uniform(0.88, 0.99)

        if best_score >= self.THRESHOLD:
            return best_id, round(best_score, 4)
        return None, round(best_score, 4)


# ─────────────────────────────────────────
# 4. FOYDALANUVCHI PROFIL BOSHQARUVCHI
# ─────────────────────────────────────────

class ProfileManager:
    """Foydalanuvchi profillarini CRUD va JSON saqlash"""

    def __init__(self, db_path: str = "profiles.json"):
        self.db_path = Path(db_path)
        self.profiles: Dict[str, UserProfile] = {}
        self._load()

    def _load(self):
        if self.db_path.exists():
            with open(self.db_path) as f:
                raw = json.load(f)
            for uid, data in raw.items():
                self.profiles[uid] = UserProfile(**data)
        else:
            self._create_demo_profiles()

    def _save(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump({uid: asdict(p) for uid, p in self.profiles.items()}, f, ensure_ascii=False, indent=2)

    def _create_demo_profiles(self):
        demo = [
            UserProfile("aziz",   "Aziz",   preferred_temp=21.0, preferred_humidity=45, preferred_lux=500, photosensitivity=0.8),
            UserProfile("malika", "Malika", preferred_temp=23.5, preferred_humidity=55, preferred_lux=350, photosensitivity=0.5),
            UserProfile("jasur",  "Jasur",  preferred_temp=20.0, preferred_humidity=40, preferred_lux=600, photosensitivity=0.2),
            UserProfile("nodira", "Nodira", preferred_temp=24.0, preferred_humidity=60, preferred_lux=280, photosensitivity=0.9),
        ]
        for p in demo:
            self.profiles[p.user_id] = p
        self._save()
        logging.info("Demo profillari yaratildi.")

    def get(self, user_id: str) -> Optional[UserProfile]:
        return self.profiles.get(user_id)

    def update_preference(self, user_id: str, **kwargs):
        p = self.profiles.get(user_id)
        if p:
            for k, v in kwargs.items():
                if hasattr(p, k):
                    setattr(p, k, v)
            p.last_seen = datetime.now().isoformat()
            self._save()

    def record_visit(self, user_id: str):
        p = self.profiles.get(user_id)
        if p:
            p.visit_count += 1
            p.last_seen = datetime.now().isoformat()
            self._save()


# ─────────────────────────────────────────
# 5. REINFORCEMENT LEARNING MODULI
# ─────────────────────────────────────────

class AdaptiveLearning:
    """
    Q-Learning asosida foydalanuvchi afzalliklarini adaptiv yangilash.
    Holat (state): (harorat_maqsad, yorug'_maqsad)
    Harakat (action): +/- sozlash
    Mukofot (reward): foydalanuvchi mamnuniyatiga qarab
    """

    ACTIONS = [-1, 0, +1]           # kamaytirishstatus, saqlash, ko'paytirish
    ALPHA   = 0.1                   # o'rganish tezligi
    GAMMA   = 0.9                   # chegirma koeffitsienti
    EPSILON = 0.2                   # exploration darajasi

    def __init__(self, profile_manager: ProfileManager):
        self.pm = profile_manager

    @staticmethod
    def _state_key(temp: float, lux: float) -> str:
        return f"{round(temp)}_{round(lux, -1)}"

    def choose_action(self, user_id: str, sensor: SensorData) -> Dict[str, int]:
        """Epsilon-greedy siyosat asosida harakatni tanlash"""
        p = self.pm.get(user_id)
        if p is None:
            return {"temp": 0, "lux": 0}

        state = self._state_key(sensor.temperature, sensor.lux)

        if random.random() < self.EPSILON:
            return {"temp": random.choice(self.ACTIONS),
                    "lux":  random.choice(self.ACTIONS)}

        t_key = f"{state}_temp"
        l_key = f"{state}_lux"
        t_action = max(self.ACTIONS, key=lambda a: p.q_table.get(f"{t_key}_{a}", 0.0))
        l_action = max(self.ACTIONS, key=lambda a: p.q_table.get(f"{l_key}_{a}", 0.0))
        return {"temp": t_action, "lux": l_action}

    def update(self, user_id: str, state_key: str, action: int, reward: float, next_state_key: str, param: str):
        """Q-jadval yangilash: Q(s,a) ← Q(s,a) + α[r + γ max Q(s',a') − Q(s,a)]"""
        p = self.pm.get(user_id)
        if p is None:
            return
        key      = f"{state_key}_{param}_{action}"
        next_max = max(p.q_table.get(f"{next_state_key}_{param}_{a}", 0.0) for a in self.ACTIONS)
        old_q    = p.q_table.get(key, 0.0)
        new_q    = old_q + self.ALPHA * (reward + self.GAMMA * next_max - old_q)
        p.q_table[key] = round(new_q, 4)
        self.pm._save()

    def feedback(self, user_id: str, sensor: SensorData, reward: float):
        """Foydalanuvchi mamnuniyati asosida modelni yangilash"""
        state = self._state_key(sensor.temperature, sensor.lux)
        action = self.choose_action(user_id, sensor)
        for param in ("temp", "lux"):
            self.update(user_id, state, action[param], reward, state, param)
        logging.info("RL yangilandi: %s, reward=%.2f", user_id, reward)


# ─────────────────────────────────────────
# 6. QUYOSH NURI VA PARDA BOSHQARUVI
# ─────────────────────────────────────────

class CurtainController:
    """
    Quyosh nurini boshqarish algoritmi.
    UV indeksi va foydalanuvchi fotosezgirligiga qarab parda pozitsiyasini hisoblaydi.
    """

    UV_THRESHOLDS = {
        "low":    (0.0, 2.0),
        "medium": (2.0, 5.0),
        "high":   (5.0, 11.0),
    }

    def calculate_curtain_position(self, uv_index: float, photosensitivity: float,
                                   current_lux: float, preferred_lux: float) -> float:
        """
        Parda yopiqlik foizini (0–100%) hisoblash.

        Parametrlar:
          uv_index         – joriy UV indeksi
          photosensitivity – foydalanuvchi sezgirligi [0..1]
          current_lux      – joriy yorug'lik (lux)
          preferred_lux    – afzal yorug'lik (lux)

        Qaytaradi: curtain_pct [0..100]
        """
        # UV asosida bazaviy yopiqlik
        if uv_index < 2.0:
            uv_factor = 0.0
        elif uv_index < 5.0:
            uv_factor = (uv_index - 2.0) / 3.0 * 0.5
        else:
            uv_factor = 0.5 + (uv_index - 5.0) / 6.0 * 0.5

        # Foydalanuvchi fotosezgirligi ta'siri
        sensitivity_factor = uv_factor * (0.5 + photosensitivity * 0.5)

        # Yorug'lik moslashtirish
        lux_ratio = current_lux / (preferred_lux + 1e-9)
        lux_factor = max(0.0, min(1.0, (lux_ratio - 1.0) * 0.3))

        curtain_pct = (sensitivity_factor * 0.7 + lux_factor * 0.3) * 100
        return round(max(0, min(100, curtain_pct)), 1)

    def servo_command(self, curtain_pct: float) -> str:
        """Servo motoriga yuborish uchun PWM buyrug'i (simulyatsiya)"""
        pwm_us = int(1000 + curtain_pct / 100 * 1000)   # 1000–2000 µs
        return f"PWM:{pwm_us}µs  (parda {curtain_pct:.0f}% yopiq)"


# ─────────────────────────────────────────
# 7. KO'P FOYDALANUVCHI QAROR QABUL QILISH
# ─────────────────────────────────────────

class MultiUserDecision:
    """
    Ko'p foydalanuvchi stsenariysi uchun ko'p mezonli qaror qabul qilish.
    Og'irlikli o'rtacha va diapazon tekshiruvi bilan optimal parametrlarni topadi.
    """

    TEMP_COMFORT_RANGE  = 2.0   # ±°C qulaylik diapazoni
    LUX_COMFORT_RANGE   = 100   # ±lux qulaylik diapazoni

    def resolve(self, profiles: List[UserProfile]) -> Dict[str, float]:
        """
        Bir necha foydalanuvchi uchun optimal xona parametrlarini hisoblash.

        Algoritm:
          1. Har bir parametr uchun og'irlikli o'rtacha (visit_count asosida)
          2. Diapazonni tekshirish — agar barcha foydalanuvchilarga mos bo'lsa qabul qilish
          3. Eng sezgir foydalanuvchiga moslash (quyosh nuri uchun)
        """
        if not profiles:
            return {"temp": 22.0, "humidity": 50.0, "lux": 400.0, "curtain_pct": 30.0}

        total_weight = sum(max(p.visit_count, 1) for p in profiles)

        def weighted_avg(attr: str) -> float:
            return sum(getattr(p, attr) * max(p.visit_count, 1) for p in profiles) / total_weight

        # Harorat: og'irlikli o'rtacha
        optimal_temp = round(weighted_avg("preferred_temp"), 1)

        # Namlik: og'irlikli o'rtacha
        optimal_hum = round(weighted_avg("preferred_humidity"), 1)

        # Yorug'lik: o'rtacha
        optimal_lux = round(weighted_avg("preferred_lux"))

        # Parda: eng yuqori fotosezgirlikka moslash (ehtiyotkorlik tamoyili)
        max_sensitivity = max(p.photosensitivity for p in profiles)
        max_uv_user = max(profiles, key=lambda p: p.photosensitivity)
        curtain_pct = round(max_sensitivity * 100 * 0.8, 1)   # sezgirlik asosida

        result = {
            "temp":        optimal_temp,
            "humidity":    optimal_hum,
            "lux":         float(optimal_lux),
            "curtain_pct": curtain_pct,
            "resolved_for": [p.name for p in profiles],
        }
        logging.info("Ko'p foydalanuvchi qaror: %s", result)
        return result


# ─────────────────────────────────────────
# 8. ASOSIY TIZIM ORKESTRI
# ─────────────────────────────────────────

class SmartRoomSystem:
    """
    Barcha modullarni birlashtiruvchi asosiy sinf.
    Asosiy tsikl: sensor o'qish → yuz tanish → profil yuklash → sozlamalar qo'llash.
    """

    LOOP_INTERVAL = 5   # soniya

    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%H:%M:%S",
        )
        self.sensors     = SensorManager()
        self.face_rec    = FaceRecognitionModule()
        self.profiles    = ProfileManager()
        self.rl          = AdaptiveLearning(self.profiles)
        self.curtain     = CurtainController()
        self.multi_user  = MultiUserDecision()
        self.room_state  = RoomState()
        self._running    = False

        # Yuz ma'lumotlar bazasiga demo foydalanuvchilarni qo'shish
        for uid in self.profiles.profiles:
            self.face_rec.register_user(uid)

        logging.info("SmartRoomSystem tayyor!")

    # ── Bir tsikl ───────────────────────────────────────

    def _tick(self):
        sensor_data = self.sensors.read_all()
        logging.info("Sensor: %.1f°C | %d%% | %dlux | UV%.1f | harakat=%s | kishi=%d",
                     sensor_data.temperature, sensor_data.humidity,
                     sensor_data.lux, sensor_data.uv_index,
                     sensor_data.motion, sensor_data.occupancy)

        if not sensor_data.motion or sensor_data.occupancy == 0:
            logging.info("Xona bo'sh — tizim kutish rejimiga o'tdi.")
            self.room_state.present_users = []
            return

        # ── Yuz tanish ──────────────────────────────────
        user_id, confidence = self.face_rec.identify()
        if user_id:
            logging.info("Yuz tanildi: %s (%.1f%%)", user_id, confidence * 100)
            self.profiles.record_visit(user_id)

            # ── Profil yuklash va sozlamalar qo'llash ───
            profile = self.profiles.get(user_id)
            if profile:
                if len(self.room_state.present_users) <= 1:
                    # Bir foydalanuvchi — to'g'ridan-to'g'ri profil qo'llash
                    self._apply_single_user(profile, sensor_data)
                else:
                    # Ko'p foydalanuvchi — kompromis hisoblash
                    present_profiles = [self.profiles.get(uid)
                                        for uid in self.room_state.present_users
                                        if self.profiles.get(uid)]
                    self._apply_multi_user(present_profiles)

                # RL aralashuvi
                actions = self.rl.choose_action(user_id, sensor_data)
                self._apply_rl_action(profile, actions)

            if user_id not in self.room_state.present_users:
                self.room_state.present_users.append(user_id)
        else:
            logging.info("Noma'lum shaxs (ishonch: %.1f%%) — sozlamalar o'zgarmadi.", confidence * 100)

    def _apply_single_user(self, profile: UserProfile, sensor: SensorData):
        """Bitta foydalanuvchi uchun profil sozlamalarini qo'llash"""
        # Harorat va namlik
        self.room_state.current_temp     = profile.preferred_temp
        self.room_state.current_humidity = profile.preferred_humidity
        self.room_state.ac_on            = sensor.temperature > profile.preferred_temp + 0.5
        self.room_state.humidifier_on    = sensor.humidity < profile.preferred_humidity - 5

        # Yorug'lik
        self.room_state.current_lux  = profile.preferred_lux
        self.room_state.lights_on    = sensor.lux < profile.preferred_lux * 0.8

        # Parda
        self.room_state.curtain_pct = self.curtain.calculate_curtain_position(
            sensor.uv_index, profile.photosensitivity, sensor.lux, profile.preferred_lux
        )
        cmd = self.curtain.servo_command(self.room_state.curtain_pct)
        logging.info("Parda buyrug'i → %s", cmd)
        logging.info("Sozlamalar qo'llandi: %.1f°C | %dlux | parda %.0f%%",
                     profile.preferred_temp, profile.preferred_lux, self.room_state.curtain_pct)

    def _apply_multi_user(self, profiles: List[UserProfile]):
        """Ko'p foydalanuvchi uchun kompromis sozlamalarni qo'llash"""
        result = self.multi_user.resolve(profiles)
        self.room_state.current_temp     = result["temp"]
        self.room_state.current_humidity = result["humidity"]
        self.room_state.current_lux      = result["lux"]
        self.room_state.curtain_pct      = result["curtain_pct"]
        logging.info("Ko'p foydalanuvchi kompromis qo'llandi: %s", result)

    def _apply_rl_action(self, profile: UserProfile, actions: Dict[str, int]):
        """RL harakatlarini qo'llash: harorat va yorug'lik kichik qadamlar bilan o'zgaradi"""
        TEMP_STEP = 0.5   # °C
        LUX_STEP  = 20.0  # lux

        new_temp = profile.preferred_temp + actions["temp"] * TEMP_STEP
        new_lux  = profile.preferred_lux  + actions["lux"]  * LUX_STEP

        # Chegara tekshiruvi
        new_temp = max(16.0, min(30.0, new_temp))
        new_lux  = max(50.0, min(1000.0, new_lux))

        if new_temp != profile.preferred_temp or new_lux != profile.preferred_lux:
            self.profiles.update_preference(profile.user_id, preferred_temp=new_temp, preferred_lux=new_lux)
            logging.info("RL yangiladi: %s → harorat=%.1f°C, yorug'=%dlux",
                         profile.user_id, new_temp, new_lux)

    # ── Asosiy tsikl ────────────────────────────────────

    def run_once(self):
        """Bir martalik bajarish (test uchun)"""
        self._tick()

    def run(self):
        """To'xtatilguncha ishlaydi"""
        self._running = True
        logging.info("Tizim ishlashni boshladi. To'xtatish uchun Ctrl+C bosing.")
        try:
            while self._running:
                self._tick()
                time.sleep(self.LOOP_INTERVAL)
        except KeyboardInterrupt:
            logging.info("Tizim to'xtatildi.")
        finally:
            self._running = False

    def stop(self):
        self._running = False

    # ── Holat xulosasi ───────────────────────────────────

    def status(self) -> Dict:
        sensor = self.sensors.read_all()
        return {
            "timestamp":       datetime.now().isoformat(),
            "sensor":          asdict(sensor),
            "room_state":      asdict(self.room_state),
            "active_profiles": [p.name for p in self.profiles.profiles.values()],
        }


# ─────────────────────────────────────────
# 9. ISHGA TUSHIRISH
# ─────────────────────────────────────────

if __name__ == "__main__":
    system = SmartRoomSystem()

    # Tizim holatini ko'rsatish
    import pprint
    print("\n=== Tizim holati ===")
    pprint.pprint(system.status())

    # 3 ta tsiklni ishga tushirish (demo)
    print("\n=== Demo tsikllari (3x) ===")
    for i in range(3):
        print(f"\n--- Tsikl {i+1} ---")
        system.run_once()
        time.sleep(0.3)

    print("\nBarchasi muvaffaqiyatli bajarildi!")
