"""
embedded/main.py — ESP32 MicroPython kodi
Sensor o'qish + MQTT orqali serverga yuborish + buyruqlarni bajarish

Qurilmalar:
  - DHT22   → GPIO4  (harorat/namlik)
  - BH1750  → I2C    (yorug'lik)
  - PIR     → GPIO14 (harakat)
  - Parda servo → GPIO13 (PWM)
  - Chiroq relesi  → GPIO12

O'rnatish:
  MicroPython firmware ESP32 ga yuklab, bu faylni main.py sifatida saqlang.
  Talab: umqtt.simple, dht, bh1750 kutubxonalari

Haqiqiy Python (Raspberry Pi) da ishlatish uchun:
  pip install adafruit-circuitpython-dht smbus2 RPi.GPIO paho-mqtt
"""

# ─────────────────────────────────────────
# SOZLAMALAR
# ─────────────────────────────────────────

WIFI_SSID     = "UyWifi"
WIFI_PASSWORD = "wifisir2025"

MQTT_HOST     = "192.168.1.100"    # Server IP manzili
MQTT_PORT     = 1883
MQTT_USER     = ""
MQTT_PASS     = ""
DEVICE_ID     = "esp32_room1"

TOPIC_PUB_SENSORS = "smartroom/sensors"
TOPIC_SUB_CMDS    = "smartroom/commands"

DHT_PIN       = 4
PIR_PIN       = 14
SERVO_PIN     = 13
LIGHT_PIN     = 12
I2C_SDA       = 21
I2C_SCL       = 22

SEND_INTERVAL = 5    # soniya

# ─────────────────────────────────────────
# MICROPYTHON KODI
# ─────────────────────────────────────────

MICROPYTHON_CODE = '''
import network, time, json, machine, dht
from umqtt.simple import MQTTClient
from machine import Pin, PWM, I2C, SoftI2C

# ── Wi-Fi ulanish ───────────────────────
def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Wi-Fi ga ulanmoqda:", WIFI_SSID)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 15
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
    if wlan.isconnected():
        print("Wi-Fi ulandi:", wlan.ifconfig()[0])
        return True
    print("Wi-Fi ulanmadi!")
    return False

# ── BH1750 yorug'lik sensori ────────────
class BH1750:
    ADDR = 0x23
    def __init__(self, i2c):
        self.i2c = i2c
    def read_lux(self):
        self.i2c.writeto(self.ADDR, bytes([0x10]))  # 1 lx resolution
        time.sleep_ms(200)
        data = self.i2c.readfrom(self.ADDR, 2)
        return ((data[0] << 8) | data[1]) / 1.2

# ── Servo motor (parda) ─────────────────
class ServoController:
    """0–100% → 1000–2000 µs PWM"""
    def __init__(self, pin):
        self.pwm = PWM(Pin(pin), freq=50)

    def set_position(self, pct):
        pct   = max(0, min(100, pct))
        us    = int(1000 + pct * 10)     # 1000–2000 µs
        duty  = int(us / 20000 * 1023)   # 50Hz → 20ms period
        self.pwm.duty(duty)

    def release(self):
        self.pwm.deinit()

# ── MQTT xabarlarni qayta ishlash ────────
curtain_servo = None
light_relay   = None

def on_message(topic, msg):
    global curtain_servo, light_relay
    try:
        data = json.loads(msg)
        device = data.get("device")
        action = data.get("action")
        value  = data.get("value")
        print(f"Buyruq: {device} → {action} = {value}")

        if device == "curtain" and action == "set" and curtain_servo:
            curtain_servo.set_position(float(value))
            print(f"Parda: {value}% yopiq")

        elif device == "light" and light_relay:
            if action == "on":
                light_relay.value(1)
            elif action == "off":
                light_relay.value(0)
            print(f"Chiroq: {action}")

        elif device == "ac":
            print(f"AC: {action}, harorat={value}")
            # Haqiqiy implementatsiyada: IR remote yoki relay

    except Exception as e:
        print("Xabar xatosi:", e)

# ── Asosiy tsikl ────────────────────────
def main():
    global curtain_servo, light_relay

    if not wifi_connect():
        machine.reset()

    # Sensorlar
    dht_sensor = dht.DHT22(Pin(DHT_PIN))
    pir        = Pin(PIR_PIN, Pin.IN)
    i2c        = SoftI2C(sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=400000)
    bh1750     = BH1750(i2c)

    # Aktuatorlar
    curtain_servo = ServoController(SERVO_PIN)
    light_relay   = Pin(LIGHT_PIN, Pin.OUT)

    # MQTT
    client = MQTTClient(
        client_id=DEVICE_ID,
        server=MQTT_HOST,
        port=MQTT_PORT,
        user=MQTT_USER or None,
        password=MQTT_PASS or None
    )
    client.set_callback(on_message)
    client.connect()
    client.subscribe(TOPIC_SUB_CMDS)
    print("MQTT ulandi →", MQTT_HOST)

    last_send = 0
    while True:
        client.check_msg()    # buyruqlarni qabul qilish

        now = time.time()
        if now - last_send >= SEND_INTERVAL:
            try:
                dht_sensor.measure()
                temp  = dht_sensor.temperature()
                hum   = dht_sensor.humidity()
                lux   = bh1750.read_lux()
                motion = pir.value()

                payload = json.dumps({
                    "device_id":   DEVICE_ID,
                    "temperature": temp,
                    "humidity":    hum,
                    "lux":         round(lux),
                    "uv_index":    0.0,       # UV sensor qo\'shilsa yangilang
                    "motion":      bool(motion),
                    "occupancy":   1 if motion else 0,
                })
                client.publish(TOPIC_PUB_SENSORS, payload)
                print(f"Yuborildi: {temp}°C | {hum}% | {lux:.0f}lux | motion={motion}")
                last_send = now

            except OSError as e:
                print("Sensor xatosi:", e)

        time.sleep_ms(100)

main()
'''

# ─────────────────────────────────────────
# RASPBERRY PI (Python 3) versiyasi
# ─────────────────────────────────────────

RASPBERRY_PI_CODE = '''
#!/usr/bin/env python3
"""
Raspberry Pi 4 uchun sensor va yuz tanish kodi.
pip install adafruit-circuitpython-dht smbus2 RPi.GPIO
    paho-mqtt face_recognition opencv-python
"""

import time, json, logging, threading
import RPi.GPIO as GPIO
import board, adafruit_dht
import smbus2, paho.mqtt.client as mqtt
import cv2, face_recognition
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RPi_SmartRoom")

# ── GPIO sozlash ────────────────────────
GPIO.setmode(GPIO.BCM)
PIR_PIN   = 14
SERVO_PIN = 13
LIGHT_PIN = 12
GPIO.setup(PIR_PIN,   GPIO.IN)
GPIO.setup(LIGHT_PIN, GPIO.OUT)
GPIO.setup(SERVO_PIN, GPIO.OUT)

servo_pwm = GPIO.PWM(SERVO_PIN, 50)
servo_pwm.start(0)

# ── BH1750 I2C ──────────────────────────
bus    = smbus2.SMBus(1)
BH1750 = 0x23

def read_lux():
    bus.write_byte(BH1750, 0x10)
    time.sleep(0.2)
    data = bus.read_i2c_block_data(BH1750, 0x10, 2)
    return round(((data[0] << 8) | data[1]) / 1.2, 1)

# ── DHT22 ───────────────────────────────
dht = adafruit_dht.DHT22(board.D4)

def read_dht():
    try:
        return dht.temperature, dht.humidity
    except RuntimeError:
        return None, None

# ── Servo (parda) ───────────────────────
def set_curtain(pct):
    """0% ochiq → 100% yopiq"""
    duty = 2.5 + pct / 100 * 10    # 2.5–12.5%
    servo_pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    servo_pwm.ChangeDutyCycle(0)

# ── Yuz tanish ───────────────────────────
class FaceRec:
    def __init__(self):
        self.known_ids  = []
        self.known_encs = []

    def load_user(self, uid, image_path):
        img = face_recognition.load_image_file(image_path)
        enc = face_recognition.face_encodings(img)
        if enc:
            self.known_ids.append(uid)
            self.known_encs.append(enc[0])

    def identify(self, frame):
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locs  = face_recognition.face_locations(rgb, model="cnn")
        encs  = face_recognition.face_encodings(rgb, locs)
        for enc in encs:
            dists = face_recognition.face_distance(self.known_encs, enc)
            if len(dists) > 0:
                idx = np.argmin(dists)
                if dists[idx] < 0.5:
                    conf = round((1 - dists[idx]) * 100, 1)
                    return self.known_ids[idx], conf
        return None, 0.0

# ── MQTT ────────────────────────────────
client   = mqtt.Client("rpi_smart_room")
face_rec = FaceRec()

def on_command(mqttc, obj, msg):
    data   = json.loads(msg.payload)
    device = data.get("device")
    if device == "curtain":
        set_curtain(float(data.get("value", 0)))
    elif device == "light":
        GPIO.output(LIGHT_PIN, data.get("action") == "on")

client.on_message = on_command
client.connect("localhost", 1883)
client.subscribe("smartroom/commands")
client.loop_start()

cap = cv2.VideoCapture(0)

logger.info("Raspberry Pi tizimi ishga tushdi")

while True:
    ret, frame = cap.read()
    if ret:
        user_id, conf = face_rec.identify(frame)
        client.publish("smartroom/face", json.dumps({
            "user_id": user_id, "confidence": conf
        }))

    temp, hum = read_dht()
    if temp:
        payload = json.dumps({
            "device_id": "rpi_room1",
            "temperature": temp, "humidity": hum,
            "lux": read_lux(),
            "motion": GPIO.input(PIR_PIN),
            "uv_index": 0.0, "occupancy": 1,
        })
        client.publish("smartroom/sensors", payload)

    time.sleep(5)
'''


# ─────────────────────────────────────────
# FAYLGA YOZISH
# ─────────────────────────────────────────

if __name__ == "__main__":
    import os

    os.makedirs("embedded", exist_ok=True)

    with open("embedded/esp32_main.py", "w", encoding="utf-8") as f:
        f.write("# ESP32 MicroPython — Aqlli Xona\n")
        f.write("# Bu faylni ESP32 ga main.py sifatida yuklang\n\n")
        f.write(f"WIFI_SSID     = '{WIFI_SSID}'\n")
        f.write(f"WIFI_PASSWORD = '{WIFI_PASSWORD}'\n")
        f.write(f"MQTT_HOST     = '{MQTT_HOST}'\n")
        f.write(f"MQTT_PORT     = {MQTT_PORT}\n")
        f.write(f"DEVICE_ID     = '{DEVICE_ID}'\n\n")
        f.write(MICROPYTHON_CODE)

    with open("embedded/rpi_main.py", "w", encoding="utf-8") as f:
        f.write("# Raspberry Pi 4 — Aqlli Xona\n")
        f.write(RASPBERRY_PI_CODE)

    print("Embedded kodlar yozildi:")
    print("  → embedded/esp32_main.py  (MicroPython)")
    print("  → embedded/rpi_main.py    (Raspberry Pi Python 3)")
