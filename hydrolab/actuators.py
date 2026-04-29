import time
import RPi.GPIO as GPIO

# --- Module 1 GPIO pins (BCM) ---
M1_PIN_HEAT_PELTIER = 17
M1_PIN_COOL_PELTIER = 27
M1_PIN_PUMP = 22
M1_PIN_MISTER = 23
M1_PIN_GROW_LIGHT = 24

# --- Module 2 GPIO pins (BCM) ---
M2_PIN_HEAT_PELTIER = 5
M2_PIN_COOL_PELTIER = 6
M2_PIN_PUMP = 12
M2_PIN_MISTER = 13
M2_PIN_GROW_LIGHT = 16

MODULES = {
    "module_1": {
        "heat": M1_PIN_HEAT_PELTIER,
        "cool": M1_PIN_COOL_PELTIER,
        "pump": M1_PIN_PUMP,
        "mister": M1_PIN_MISTER,
        "grow_light": M1_PIN_GROW_LIGHT,
    },
    "module_2": {
        "heat": M2_PIN_HEAT_PELTIER,
        "cool": M2_PIN_COOL_PELTIER,
        "pump": M2_PIN_PUMP,
        "mister": M2_PIN_MISTER,
        "grow_light": M2_PIN_GROW_LIGHT,
    },
}

RELAY_PINS = [
    M1_PIN_HEAT_PELTIER, M1_PIN_COOL_PELTIER, M1_PIN_PUMP, M1_PIN_GROW_LIGHT,
    M2_PIN_HEAT_PELTIER, M2_PIN_COOL_PELTIER, M2_PIN_PUMP, M2_PIN_GROW_LIGHT,
]

MISTER_PULSE_DURATION = 0.15
MISTER_PULSE_GAP = 0.15

# Track mister state per module
_mister_is_on = {"module_1": False, "module_2": False}

def init_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in RELAY_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    for mod in MODULES.values():
        GPIO.setup(mod["mister"], GPIO.IN)

def set_peltier(module, state):
    pins = MODULES[module]
    if state == "heating":
        GPIO.output(pins["heat"], GPIO.HIGH)
        GPIO.output(pins["cool"], GPIO.LOW)
    elif state == "cooling":
        GPIO.output(pins["heat"], GPIO.LOW)
        GPIO.output(pins["cool"], GPIO.HIGH)
    else:
        GPIO.output(pins["heat"], GPIO.LOW)
        GPIO.output(pins["cool"], GPIO.LOW)

def set_pump(module, state):
    GPIO.output(MODULES[module]["pump"], GPIO.HIGH if state else GPIO.LOW)

def _pulse_mister(module):
    pin = MODULES[module]["mister"]
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)
    time.sleep(MISTER_PULSE_DURATION)
    GPIO.setup(pin, GPIO.IN)

def set_mister(module, state):
    global _mister_is_on
    if state and not _mister_is_on[module]:
        _pulse_mister(module)
        _mister_is_on[module] = True
    elif not state and _mister_is_on[module]:
        _pulse_mister(module)
        time.sleep(MISTER_PULSE_GAP)
        _pulse_mister(module)
        _mister_is_on[module] = False

def set_grow_light(module, state):
    GPIO.output(MODULES[module]["grow_light"], GPIO.HIGH if state else GPIO.LOW)

def cleanup():
    for pin in RELAY_PINS:
        GPIO.output(pin, GPIO.LOW)
    for module in MODULES:
        if _mister_is_on[module]:
            set_mister(module, False)
    GPIO.cleanup()
