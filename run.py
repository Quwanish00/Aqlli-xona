"""
run.py — Tizimni ishga tushirish
Foydalanish:
    python run.py            # to'liq tizim (API + sensor simulyatsiya)
    python run.py --demo     # faqat 5 tsikl demo
    python run.py --api      # faqat API server
"""

import sys
import logging
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# DEMO REJIMI — to'liq tizimni 5 tsikl sinash
# ─────────────────────────────────────────

def run_demo():
    from smart_room import SmartRoomSystem
    import pprint

    print("\n" + "═" * 55)
    print("  AQLLI XONA BOSHQARUV TIZIMI — DEMO")
    print("  Nukus Davlat Texnika Universiteti, 2025")
    print("═" * 55 + "\n")

    system = SmartRoomSystem()

    print("📊 Tizim holati:")
    pprint.pprint(system.status(), width=60)

    print("\n🔄 5 ta tsikl ishga tushirilmoqda...\n")
    for i in range(5):
        print(f"─── Tsikl {i+1}/5 " + "─" * 35)
        system.run_once()
        time.sleep(0.5)

    print("\n✅ Demo muvaffaqiyatli yakunlandi!")


# ─────────────────────────────────────────
# API SERVER REJIMI
# ─────────────────────────────────────────

def run_api():
    from api import app
    from config import Config
    logger.info("API server ishga tushmoqda: http://localhost:%d", Config.PORT)
    app.run(host=Config.HOST, port=Config.PORT, debug=False)


# ─────────────────────────────────────────
# TO'LIQ REJIM — API + Sensor simulyatsiya
# ─────────────────────────────────────────

def run_full():
    from api import app
    from smart_room import SmartRoomSystem
    from config import Config

    # Sensor tizimini alohida thread da ishga tushirish
    system = SmartRoomSystem()

    def sensor_loop():
        logger.info("Sensor tsikli boshlandi (har %d soniyada)", system.LOOP_INTERVAL)
        while True:
            system.run_once()
            time.sleep(system.LOOP_INTERVAL)

    sensor_thread = threading.Thread(target=sensor_loop, daemon=True)
    sensor_thread.start()

    logger.info("API server ishga tushmoqda: http://localhost:%d", Config.PORT)
    app.run(host=Config.HOST, port=Config.PORT, debug=False)


# ─────────────────────────────────────────
# ISHGA TUSHIRISH
# ─────────────────────────────────────────

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--full"

    if mode == "--demo":
        run_demo()
    elif mode == "--api":
        run_api()
    else:
        run_full()
