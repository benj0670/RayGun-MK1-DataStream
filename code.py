# The Ray Gun Project - Ray Gun Mark I
# Code written by Andrew Lamson 11/28/23
# Designed for Adafruit RP2040 Propmaker Feather

import time
import board
import audiocore
import audiobusio
import sys
import json
import pwmio
from digitalio import DigitalInOut, Direction, Pull
import analogio
from analogio import AnalogIn
import neopixel
from adafruit_led_animation.animation.SparklePulse import SparklePulse
from adafruit_led_animation.color import BLUE, WHITE, CYAN, GREEN, RED, YELLOW
from adafruit_motor import servo
import adafruit_lis3dh

# enable external power pin
# provides power to the external components
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

led = DigitalInOut(board.LED)
led.direction = Direction.OUTPUT
led.value = True

# Set up trigger pin
trigger = DigitalInOut(board.D5)
trigger.direction = Direction.INPUT
trigger.pull = Pull.UP
trigger_state = False

# Set up potentiometer
pot_read = AnalogIn(board.A1)

# Set up HES
sensor = DigitalInOut(board.D6)
sensor.direction = Direction.INPUT
sensor.pull = Pull.UP

# Set up photocell
photocell = analogio.AnalogIn(board.A2)

# i2s playback
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
startup = audiocore.WaveFile(open("Startup.wav", "rb"))
shoot = audiocore.WaveFile(open("RayGunPew.wav", "rb"))
empty = audiocore.WaveFile(open("shoot_last.wav", "rb"))
quote1 = audiocore.WaveFile(open("Dempsey_1.wav", "rb"))
quote2 = audiocore.WaveFile(open("Dempsey_2.wav", "rb"))
quote3 = audiocore.WaveFile(open("Dempsey_3.wav", "rb"))
reloadOpen = audiocore.WaveFile(open("Reload_Open.wav", "rb"))
reloadClose = audiocore.WaveFile(open("Reload_Close.wav", "rb"))
batteryIn = audiocore.WaveFile(open("battery_in.wav", "rb"))
batteryOut = audiocore.WaveFile(open("battery_out.wav", "rb"))

# servo control
pwm = pwmio.PWMOut(board.D4, duty_cycle=2 ** 15, frequency=50)
prop_servo = servo.Servo(pwm)
needle_green = 65
needle_red = 10
prop_servo.angle = needle_green

# external button
switch = DigitalInOut(board.EXTERNAL_BUTTON)
switch.direction = Direction.INPUT
switch.pull = Pull.UP
switch_state = False

# external neopixels
dial_pixels = 3
dial = neopixel.NeoPixel(board.D9, dial_pixels)
dial.brightness = 0.8
fuse_pixels = 15
fuse = neopixel.NeoPixel(board.EXTERNAL_NEOPIXELS, fuse_pixels)
fuse.brightness = 0.5
cell = neopixel.NeoPixel(board.D10, 1)
cell.brightness = 1.0
cell[0] = WHITE
blue_wave = SparklePulse(fuse, speed=0.02, period=2, color=BLUE, min_intensity=0.7)
white_wave = SparklePulse(fuse, speed=0.02, period=2, color=WHITE, min_intensity=0.7)
cyan_wave = SparklePulse(fuse, speed=0.02, period=2, color=CYAN, min_intensity=0.7)
red_wave = SparklePulse(fuse, speed=0.02, period=2, color=RED, min_intensity=0.7)
green_wave = SparklePulse(fuse, speed=0.02, period=2, color=GREEN, min_intensity=0.7)

# onboard LIS3DH
HIT_THRESHOLD = 120
i2c = board.I2C()
int1 = DigitalInOut(board.ACCELEROMETER_INTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
# Accelerometer Range (can be 2_G, 4_G, 8_G, 16_G)
lis3dh.range = adafruit_lis3dh.RANGE_4_G
lis3dh.set_tap(1, HIT_THRESHOLD)
last_time = time.monotonic()

# Sensor data variables
barrel_open = False
bat = True
last_bat = bat
photostate = photocell.value
hallstate = sensor.value
trigger_count = 0
ct = 0
b = 0
needle_position = 0

def get_mode(mode):
    if mode <= 100:
        cyan_wave.animate()
    elif mode > 100 and mode <= 200:
        red_wave.animate()
    elif mode > 200 and mode <= 300:
        green_wave.animate()
    elif mode > 300 and mode <= 400:
        blue_wave.animate()
    else:
        white_wave.animate()

def bad_fire(i):
    if i == 0:
        audio.play(empty)
    elif i == 1:
        audio.play(quote1)
    elif i == 2:
        audio.play(quote2)
    elif i == 3:
        audio.play(quote3)

def send_data_serial():
    # Gather data
    reading = pot_read.value
    val = (reading * 500.0) / 65536
    
    # Accelerometer data
    x, y, z = lis3dh.acceleration
    
    # Current states
    current_hallstate = sensor.value
    current_photostate = (photocell.value * 1000) / 65536
    if barrel_open:
        current_barrelstate = 'Open'
    else:
        current_barrelstate = 'Closed'

    if trigger_count <= 20:
        ammo = trigger_count
    else: 
        ammo = 20

    # Prepare JSON payload
    data = {
        "pot_value": val,
        "hall_state": current_hallstate,
        "photo_state": current_photostate,
        "accel_x": x,
        "accel_y": y,
        "accel_z": z,
        "barrel_open": current_barrelstate,
        "battery_status": "Cells In Fuse" if bat else "Cells Removed From Fuse",
        "needle_position": needle_position,
        "ammo": ammo
    }
    
    # Send data over serial
    try:
        print(data)
    except Exception as e:
        print(f"Error sending data over serial: {e}")


def start():
    global needle_position
    dial[0] = RED
    dial[1] = YELLOW
    dial[2] = GREEN
    dial.show()
    if hallstate:
        audio.play(reloadOpen)
        prop_servo.angle = needle_red
        needle_position = needle_red
        return True
    if not hallstate:
        audio.play(startup)
        needle_position = needle_green
        return False


# Check status of Ray Gun and set starting conditions
barrel_open = start()
#  Main loop
while True:

    current_time = time.monotonic()
    delta_time = current_time - last_time
    x, y, z = lis3dh.acceleration
    accel_total = x * x + z * z
    if delta_time > 15.0 and barrel_open is False:
        prop_servo.angle = needle_red
        needle_position = needle_red
        if lis3dh.tapped:
            prop_servo.angle = needle_green
            needle_position = needle_green
            last_time = time.monotonic()
    reading = pot_read.value
    val = (reading * 500.0) / 65536
    get_mode(val)
    last_hallstate = hallstate
    hallstate = sensor.value
    photostate = (photocell.value * 1000) / 65536
    print(photostate)

    if not trigger.value and not sensor.value and trigger_state is False:
        if trigger_count < 20:
            audio.play(shoot)
            prop_servo.angle = needle_red
            needle_position = needle_red
        elif ct < 4:
            bad_fire(ct)
            ct += 1
        else:
            ct = 0
        trigger_count += 1
        trigger_state = True
        last_time = time.monotonic()
    if trigger.value and trigger_state is True:
        trigger_state = False
        prop_servo.angle = needle_green
        needle_position = needle_green
    elif hallstate and hallstate != last_hallstate:
        audio.play(reloadOpen)
        prop_servo.angle = needle_red
        needle_position = needle_red
        barrel_open = True
    elif hallstate and hallstate == last_hallstate and not audio.playing:
        if photostate < 500:
            led.value = False
            bat = True
        else:
            led.value = True
            bat = False
        if photostate > 500 and last_bat != bat and b < 1:
            audio.play(batteryOut)
            b += 1
        if photostate < 500 and last_bat != bat and not audio.playing:
            audio.play(batteryIn)
        last_bat = bat
    elif not hallstate and hallstate != last_hallstate:
        trigger_count = 0
        b = 0
        audio.play(reloadClose)
        prop_servo.angle = needle_green
        needle_position = needle_green
        barrel_open = False
        last_time = time.monotonic()

    # Send data periodically
    send_data_serial()

    time.sleep(0.02)