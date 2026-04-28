import time
import RPi.GPIO as GPIO

# GPIO pin assignments (BCM numbering) — UPDATE THESE once wiring is finalized
PIN_HEAT_PELTIER = 17
PIN_COOL_PELTIER = 27
PIN_PUMP = 22
PIN_MISTER = 23
PIN_GROW_LIGHT = 24

RELAY_PINS = [PIN_HEAT_PELTIER, PIN_COOL_PELTIER, PIN_PUMP, PIN_GROW_LIGHT]

# Mister button press timing
MISTER_PULSE_DURATION = 0.15   # seconds to hold LOW
MISTER_PULSE_GAP = 0.15        # seconds between presses

# Track mister state since we can only toggle it, not set it directly
_mister_is_on = False

def init_gpio():
    """Initialize GPIO pins. Relay pins as outputs (LOW). Mister pin as input (hi-Z)."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in RELAY_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    # Mister starts as hi-Z (input mode = not pressing the button)
    GPIO.setup(PIN_MISTER, GPIO.IN)

def set_peltier(state):
    """Set peltier state: 'off', 'heating', or 'cooling'. Maps to two relay pins."""
    if state == "heating":
        GPIO.output(PIN_HEAT_PELTIER, GPIO.HIGH)
        GPIO.output(PIN_COOL_PELTIER, GPIO.LOW)
    elif state == "cooling":
        GPIO.output(PIN_HEAT_PELTIER, GPIO.LOW)
        GPIO.output(PIN_COOL_PELTIER, GPIO.HIGH)
    else:
        GPIO.output(PIN_HEAT_PELTIER, GPIO.LOW)
        GPIO.output(PIN_COOL_PELTIER, GPIO.LOW)

def set_pump(state):
    """Set pump relay. state: True (on) or False (off)."""
    GPIO.output(PIN_PUMP, GPIO.HIGH if state else GPIO.LOW)

def _pulse_mister():
    """Simulate a button press: briefly drive LOW, then return to hi-Z."""
    GPIO.setup(PIN_MISTER, GPIO.OUT)
    GPIO.output(PIN_MISTER, GPIO.LOW)
    time.sleep(MISTER_PULSE_DURATION)
    GPIO.setup(PIN_MISTER, GPIO.IN)  # back to hi-Z

def set_mister(state):
    """Set mister on/off. Simulates button presses on the physical push button.
    Mister cycles: off -> on -> on -> off. So 1 press to turn on, 2 presses to turn off."""
    global _mister_is_on
    if state and not _mister_is_on:
        # Turn on: 1 press
        _pulse_mister()
        _mister_is_on = True
    elif not state and _mister_is_on:
        # Turn off: 2 presses (cycles through on -> on -> off)
        _pulse_mister()
        time.sleep(MISTER_PULSE_GAP)
        _pulse_mister()
        _mister_is_on = False

def set_grow_light(state):
    """Set grow light relay. state: True (on) or False (off)."""
    GPIO.output(PIN_GROW_LIGHT, GPIO.HIGH if state else GPIO.LOW)

def cleanup():
    """Turn off all relays, turn off mister if on, and clean up GPIO."""
    for pin in RELAY_PINS:
        GPIO.output(pin, GPIO.LOW)
    # Turn off mister if it's on
    if _mister_is_on:
        set_mister(False)
    GPIO.cleanup()
