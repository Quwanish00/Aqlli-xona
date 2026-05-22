"""
mqtt_client.py — MQTT Broker integratsiyasi
Sensor ma'lumotlarini yuborish va buyruqlarni qabul qilish.
Broker: Mosquitto (lokal) yoki HiveMQ (bulut)

O'rnatish:
    pip install paho-mqtt
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Callable, Optional, Dict, Any

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logging.warning("paho-mqtt o'rnatilmagan. MQTT simulyatsiya rejimida ishlaydi.")

from config import Config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# MQTT MIJOZ
# ─────────────────────────────────────────

class MQTTClient:
    """
    MQTT orqali ESP32/Raspberry Pi va server o'rtasida xabar almashish.

    Mavzular:
        smartroom/sensors   ← sensorlardan keluvchi ma'lumotlar (ESP32 → Server)
        smartroom/commands  → serverdan qurilmaga buyruqlar  (Server → ESP32)
        smartroom/face      ← yuz tanish natijalari           (RPi → Server)
        smartroom/status    ↔ tizim holati                    (ikki tomonlama)
    """

    def __init__(self, on_message_cb: Optional[Callable] = None):
        self.on_message_cb = on_message_cb
        self._connected    = False
        self._client       = None
        self._lock         = threading.Lock()

        if MQTT_AVAILABLE:
            self._setup_client()

    def _setup_client(self):
        self._client = mqtt.Client(client_id="smart_room_server")
        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message    = self._on_message

        if Config.MQTT_USERNAME:
            self._client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            logger.info("MQTT brokerga ulandi: %s:%d", Config.MQTT_HOST, Config.MQTT_PORT)
            # Barcha mavzularga obuna bo'lish
            for topic in [Config.TOPIC_SENSORS, Config.TOPIC_FACE, Config.TOPIC_STATUS]:
                client.subscribe(topic)
                logger.info("MQTT mavzuga obuna: %s", topic)
        else:
            logger.error("MQTT ulanish xatosi, kod: %d", rc)

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        logger.warning("MQTT aloqasi uzildi (rc=%d), qayta ulanish...", rc)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.debug("MQTT xabar: %s → %s", msg.topic, payload)
            if self.on_message_cb:
                self.on_message_cb(msg.topic, payload)
        except json.JSONDecodeError:
            logger.error("MQTT xabar JSON emas: %s", msg.payload)

    # ── Ulanish ─────────────────────────────────────────

    def connect(self):
        if not MQTT_AVAILABLE:
            logger.info("MQTT simulyatsiya rejimi — haqiqiy broker yo'q.")
            return
        try:
            self._client.connect(Config.MQTT_HOST, Config.MQTT_PORT, Config.MQTT_KEEPALIVE)
            self._client.loop_start()
        except Exception as e:
            logger.error("MQTT ulanish xatosi: %s", e)

    def disconnect(self):
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()

    # ── Xabar yuborish ──────────────────────────────────

    def publish(self, topic: str, payload: Dict, qos: int = 1) -> bool:
        if not MQTT_AVAILABLE or not self._connected:
            logger.debug("MQTT simulyatsiya: %s → %s", topic, payload)
            return True
        try:
            msg = json.dumps(payload, ensure_ascii=False)
            result = self._client.publish(topic, msg, qos=qos)
            return result.rc == 0
        except Exception as e:
            logger.error("MQTT publish xatosi: %s", e)
            return False

    # ── Qulay yuborish metodlari ─────────────────────────

    def send_sensor_data(self, sensor_dict: Dict) -> bool:
        payload = {**sensor_dict, "timestamp": datetime.now().isoformat()}
        return self.publish(Config.TOPIC_SENSORS, payload)

    def send_command(self, device: str, action: str, value: Any = None) -> bool:
        """
        Qurilmaga buyruq yuborish.
        device: "ac", "humidifier", "curtain", "light"
        action: "on", "off", "set"
        value:  raqam yoki None
        """
        payload = {
            "device":    device,
            "action":    action,
            "value":     value,
            "timestamp": datetime.now().isoformat(),
        }
        return self.publish(Config.TOPIC_COMMANDS, payload)

    def send_curtain_command(self, pct: float) -> bool:
        return self.send_command("curtain", "set", round(pct, 1))

    def send_ac_command(self, on: bool, target_temp: float = 22.0) -> bool:
        return self.send_command("ac", "on" if on else "off", target_temp)

    def send_light_command(self, on: bool, intensity_pct: float = 80.0) -> bool:
        return self.send_command("light", "on" if on else "off", intensity_pct)

    def send_face_result(self, user_id: Optional[str], confidence: float) -> bool:
        payload = {
            "user_id":    user_id,
            "confidence": confidence,
            "identified": user_id is not None,
            "timestamp":  datetime.now().isoformat(),
        }
        return self.publish(Config.TOPIC_FACE, payload)

    @property
    def is_connected(self) -> bool:
        return self._connected or not MQTT_AVAILABLE   # simulyatsiyada har doim True


# ─────────────────────────────────────────
# SIMULYATSIYA: ESP32 dan kelgan xabarlar
# ─────────────────────────────────────────

class MQTTSimulator:
    """
    Haqiqiy ESP32 qurilmasi bo'lmaganda sensorlarni simulyatsiya qiladi.
    Faqat test va namoyish uchun.
    """

    def __init__(self, mqtt_client: MQTTClient, interval: float = 5.0):
        self.mqtt    = mqtt_client
        self.interval = interval
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("MQTT simulyator ishga tushdi (interval: %.0fs)", self.interval)

    def stop(self):
        self._running = False

    def _loop(self):
        import random
        while self._running:
            import math
            hour = datetime.now().hour
            # Kunning vaqtiga qarab realistik qiymatlar
            base_temp = 22 + 2 * math.sin((hour - 6) * math.pi / 12)
            base_lux  = max(0, 500 * math.sin(hour * math.pi / 12)) if 6 <= hour <= 20 else 0

            data = {
                "temperature": round(base_temp + random.gauss(0, 0.5), 1),
                "humidity":    round(50 + random.gauss(0, 3), 1),
                "lux":         round(abs(base_lux + random.gauss(0, 30))),
                "uv_index":    round(max(0, random.gauss(2, 0.8)), 1),
                "motion":      random.random() > 0.3,
                "occupancy":   random.choices([0, 1, 2], weights=[15, 60, 25])[0],
                "device_id":   "esp32_room1",
            }
            self.mqtt.send_sensor_data(data)
            time.sleep(self.interval)
