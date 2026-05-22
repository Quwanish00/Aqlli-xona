# 🏠 Aqlli Xona Boshqaruv Tizimi

**Ko'p sensorli IoT va Sun'iy Intellekt asosida foydalanuvchiga mos aqlli xona muhitini boshqarish**

> Nukus Davlat Texnika Universiteti | Magistratura dissertatsiyasi | 2025
> Muallif: Qıdırbaev Quwanıshbay Quralbaevich

---

## 📁 Loyiha tuzilmasi

```
smart_room/
├── smart_room.py          # Asosiy tizim modullari (sensorlar, yuz tanish, RL, parda)
├── database.py            # SQLite/PostgreSQL ma'lumotlar bazasi
├── api.py                 # Flask REST API (barcha HTTP endpointlar)
├── mqtt_client.py         # MQTT broker integratsiyasi
├── config.py              # Konfiguratsiya (sozlamalar)
├── run.py                 # Ishga tushirish skripti
├── embedded_generator.py  # ESP32 + Raspberry Pi kodlarini generatsiya qilish
├── requirements.txt       # Python kutubxonalari
└── README.md              # Bu fayl
```

---

## 🚀 Tezkor boshlash

### 1. Kutubxonalarni o'rnatish
```bash
pip install flask flask-cors paho-mqtt numpy opencv-python-headless
```

### 2. Demo rejimi (har qanday kompyuterda ishlaydi)
```bash
python run.py --demo
```

### 3. Faqat API server
```bash
python run.py --api
# http://localhost:5000 da API ishlaydi
```

### 4. To'liq rejim (API + sensor tsikli)
```bash
python run.py
```

---

## 🔌 API Endpointlar

| Metod | URL | Tavsif |
|-------|-----|--------|
| GET | `/api/health` | Tizim holati |
| GET | `/api/sensors/current` | Joriy sensor qiymatlari |
| GET | `/api/sensors/history` | Sensor tarixi |
| GET | `/api/sensors/stats` | 24 soatlik statistika |
| POST | `/api/sensors/ingest` | ESP32 dan ma'lumot qabul |
| POST | `/api/face/identify` | Yuz tanish |
| POST | `/api/face/register` | Yangi foydalanuvchi |
| GET | `/api/users` | Barcha foydalanuvchilar |
| PATCH | `/api/users/<id>/profile` | Profilni yangilash |
| POST | `/api/users/<id>/feedback` | RL feedback (mamnuniyat) |
| POST | `/api/room/apply/<id>` | Profil qo'llash |
| POST | `/api/room/multi` | Ko'p foydalanuvchi kompromis |
| POST | `/api/room/curtain` | Parda boshqaruvi |
| GET | `/api/dashboard` | Dashboard statistika |

---

## 📡 API Misollari (curl)

### Yuz tanish:
```bash
curl -X POST http://localhost:5000/api/face/identify
```

### Yangi foydalanuvchi ro'yxatga olish:
```bash
curl -X POST http://localhost:5000/api/face/register \
  -H "Content-Type: application/json" \
  -d '{"user_id":"ali","name":"Ali","preferred_temp":21,"photosensitivity":0.7}'
```

### Profilni xonaga qo'llash:
```bash
curl -X POST http://localhost:5000/api/room/apply/aziz
```

### Ko'p foydalanuvchi kompromis:
```bash
curl -X POST http://localhost:5000/api/room/multi \
  -H "Content-Type: application/json" \
  -d '{"user_ids":["aziz","malika"]}'
```

### Mamnuniyat feedbacki (RL uchun):
```bash
curl -X POST http://localhost:5000/api/users/aziz/feedback \
  -H "Content-Type: application/json" \
  -d '{"reward": 0.8}'
```

### Parda boshqaruvi:
```bash
curl -X POST http://localhost:5000/api/room/curtain \
  -H "Content-Type: application/json" \
  -d '{"pct": 60}'
```

---

## 🔧 Modul tavsiflari

### `smart_room.py` — Asosiy modullar
| Sinf | Vazifa |
|------|--------|
| `SensorManager` | DHT22, BH1750, PIR, mmWave simulyatsiyasi |
| `FaceRecognitionModule` | MTCNN + FaceNet yuz tanish |
| `ProfileManager` | Foydalanuvchi profillari CRUD |
| `AdaptiveLearning` | Q-Learning RL moduli |
| `CurtainController` | Parda servo boshqaruvi |
| `MultiUserDecision` | Ko'p mezonli qaror qabul qilish |
| `SmartRoomSystem` | Barcha modullarni birlashtiruvchi orkestir |

### `database.py` — Jadvallar
| Jadval | Tavsif |
|--------|--------|
| `users` | Foydalanuvchi profillari va Q-jadval |
| `sensor_logs` | Sensor o'qish tarixi |
| `face_events` | Yuz tanish hodisalari |
| `room_settings` | Qo'llangan sozlamalar tarixi |
| `rl_feedback` | RL feedback yozuvlari |

---

## 🤖 Apparat talablari

### Server (minimal):
- CPU: 2 yadro+, RAM: 2GB+
- Python 3.10+, SQLite yoki PostgreSQL

### Sensor tuguni (ESP32):
- ESP32-WROOM-32
- DHT22 (harorat/namlik) — GPIO4
- BH1750 (yorug'lik) — I2C (SDA=21, SCL=22)
- PIR sensori — GPIO14
- Servo motor (parda) — GPIO13
- Chiroq relesi — GPIO12

### Yuz tanish (Raspberry Pi):
- Raspberry Pi 4 (4GB RAM)
- Pi Camera Module v3
- DHT22, BH1750 sensorlar
- Python face_recognition + OpenCV

---

## 📊 Kutilayotgan natijalar

| Ko'rsatkich | Qiymat |
|-------------|--------|
| Yuz tanish aniqligi | 97%+ (FaceNet, LFW benchmark) |
| Reaktsiya vaqti | < 200ms |
| Energiya tejash | 20–35% |
| RL moslashish vaqti | 7–14 kun |
| Ko'p foydalanuvchi kompromis | Og'irlikli o'rtacha (MCDM) |

---

## 📚 Asosiy texnologiyalar

- **Yuz tanish**: MTCNN (aniqlash) + FaceNet/DeepFace (identifikatsiya)
- **RL**: Q-Learning, epsilon-greedy siyosat
- **Protokol**: MQTT v5 (IoT), REST API (Flask)
- **Ma'lumotlar bazasi**: SQLite (ishga tushirish) / PostgreSQL (ishlab chiqarish)
- **Embedded**: MicroPython (ESP32) + Python 3 (Raspberry Pi)
- **Edge Computing**: Raspberry Pi 4 (lokal AI hisoblash)

---

*Aqlli Xona Boshqaruv Tizimi — 2025, NDTU*
