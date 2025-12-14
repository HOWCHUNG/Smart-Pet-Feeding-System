#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import signal
from collections import deque

import RPi.GPIO as GPIO
from smbus import SMBus

# =========================
# 專案固定設定
# =========================
CONFIG_PATH = "hx711_config.json"

# HX711（你固定用這組）
HX_DT_PIN = 5
HX_SCK_PIN = 6

# Servo（建議 GPIO18）
SERVO_PIN = 18

# I2C LCD
I2C_BUS_NO = 1
LCD_I2C_ADDR = 0x27  # 會被 config 覆蓋成 i2c_addr（十進位 39=0x27）

# =========================
# 上秤判斷 & 穩定判斷（你要的重點參數）
# =========================
ON_SCALE_MIN_G = 20.0        # >= 20g 視為「上秤」（依你秤台噪訊調整）
OFF_SCALE_MAX_G = 8.0        # <= 8g 視為「下秤」（要小於上秤，形成遲滯避免抖動）
STABLE_N = 10                # 連續 N 次穩定才算穩定
STABLE_THRESHOLD_G = 1.0     # 閾值：連續讀值差異 < 1.0g 算穩定
STABLE_SAMPLE_INTERVAL = 0.15  # 每次取樣間隔（秒）

# =========================
# 你要調的參數：重量區間與餵食量
# =========================
LOW_G = 60.0
HIGH_G = 90.0

FEED_TIME_LIGHT = 0.30
FEED_TIME_NORMAL = 0.20
FEED_TIME_HEAVY = 0.10

SERVO_CLOSE_ANGLE = 0
SERVO_OPEN_ANGLE = 90

# HX711 濾波
AVG_TIMES = 12
AVG_DELAY = 0.02

# =========================
# LCD (PCF8574) 基本驅動
# =========================
LCD_WIDTH = 16
LCD_CHR = 1
LCD_CMD = 0
LCD_LINE_1 = 0x80
LCD_LINE_2 = 0xC0
LCD_BACKLIGHT = 0x08
ENABLE = 0b00000100

def lcd_toggle_enable(bus, bits):
    time.sleep(0.0005)
    bus.write_byte(LCD_I2C_ADDR, (bits | ENABLE))
    time.sleep(0.0005)
    bus.write_byte(LCD_I2C_ADDR, (bits & ~ENABLE))
    time.sleep(0.0005)

def lcd_byte(bus, bits, mode):
    high = mode | (bits & 0xF0) | LCD_BACKLIGHT
    low  = mode | ((bits << 4) & 0xF0) | LCD_BACKLIGHT
    bus.write_byte(LCD_I2C_ADDR, high)
    lcd_toggle_enable(bus, high)
    bus.write_byte(LCD_I2C_ADDR, low)
    lcd_toggle_enable(bus, low)

def lcd_init(bus):
    lcd_byte(bus, 0x33, LCD_CMD)
    lcd_byte(bus, 0x32, LCD_CMD)
    lcd_byte(bus, 0x06, LCD_CMD)
    lcd_byte(bus, 0x0C, LCD_CMD)
    lcd_byte(bus, 0x28, LCD_CMD)
    lcd_byte(bus, 0x01, LCD_CMD)
    time.sleep(0.005)

def lcd_string(bus, msg, line):
    msg = msg.ljust(LCD_WIDTH, " ")
    lcd_byte(bus, line, LCD_CMD)
    for ch in msg[:LCD_WIDTH]:
        lcd_byte(bus, ord(ch), LCD_CHR)

def lcd_safe_write(bus, line1, line2, retries=3):
    for attempt in range(1, retries + 1):
        try:
            lcd_string(bus, line1[:16], LCD_LINE_1)
            lcd_string(bus, line2[:16], LCD_LINE_2)
            return True
        except OSError:
            try:
                lcd_init(bus)
            except Exception:
                pass
            time.sleep(0.05 * attempt)
    return False

# =========================
# HX711 讀取
# =========================
def hx711_read_raw():
    count = 0
    while GPIO.input(HX_DT_PIN) == 1:
        pass

    for _ in range(24):
        GPIO.output(HX_SCK_PIN, True)
        count = count << 1
        GPIO.output(HX_SCK_PIN, False)
        if GPIO.input(HX_DT_PIN) == 1:
            count += 1

    GPIO.output(HX_SCK_PIN, True)
    GPIO.output(HX_SCK_PIN, False)

    if (count & 0x800000):
        count |= ~0xFFFFFF
    return count

def hx711_read_average(times=AVG_TIMES, delay=AVG_DELAY):
    total = 0
    for _ in range(times):
        total += hx711_read_raw()
        time.sleep(delay)
    return total / times

# =========================
# Servo 控制
# =========================
def servo_angle(pwm, angle):
    duty = 2 + (angle / 18)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.35)
    pwm.ChangeDutyCycle(0)

def dispense_food(pwm, seconds):
    servo_angle(pwm, SERVO_OPEN_ANGLE)
    time.sleep(max(0.05, seconds))
    servo_angle(pwm, SERVO_CLOSE_ANGLE)

# =========================
# Config
# =========================
def load_config():
    global LCD_I2C_ADDR
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    offset = float(cfg["offset"])
    scale = float(cfg["scale"])
    LCD_I2C_ADDR = int(cfg.get("i2c_addr", 39))  # 39=0x27
    return offset, scale

# =========================
# Ctrl+C
# =========================
stop_flag = False
def handle_sigint(signum, frame):
    global stop_flag
    stop_flag = True

# =========================
# 決策：重量區間 → 餵食時間
# =========================
def decide_feed(weight_g):
    if weight_g < LOW_G:
        return ("LIGHT", FEED_TIME_LIGHT)
    elif weight_g > HIGH_G:
        return ("HEAVY", FEED_TIME_HEAVY)
    else:
        return ("OK", FEED_TIME_NORMAL)

# =========================
# 穩定判斷：連續 N 次差異 < threshold
# 這裡用「範圍」判斷：max-min <= threshold
# =========================
def stable_progress(buf: deque, threshold_g: float):
    if not buf:
        return (0, False, 0.0)
    mn = min(buf)
    mx = max(buf)
    span = mx - mn
    is_stable = span <= threshold_g and len(buf) >= STABLE_N
    return (len(buf), is_stable, span)

# =========================
# 主程式
# =========================
def main():
    global stop_flag
    signal.signal(signal.SIGINT, handle_sigint)

    offset, scale = load_config()

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    GPIO.setup(HX_DT_PIN, GPIO.IN)
    GPIO.setup(HX_SCK_PIN, GPIO.OUT)

    GPIO.setup(SERVO_PIN, GPIO.OUT)
    pwm = GPIO.PWM(SERVO_PIN, 50)
    pwm.start(0)
    servo_angle(pwm, SERVO_CLOSE_ANGLE)

    bus = SMBus(I2C_BUS_NO)
    try:
        lcd_init(bus)
    except Exception:
        pass

    lcd_safe_write(bus, "Hamster Feeder", "On+Stable Mode", retries=5)
    time.sleep(1)

    on_scale = False
    fed_this_visit = False
    stable_buf = deque(maxlen=STABLE_N)

    last_weight = None

    try:
        while not stop_flag:
            raw_avg = hx711_read_average()
            weight_g = (raw_avg - offset) / scale
            weight_g = round(weight_g, 1)

            # 方向若相反，保守取絕對值（demo 更直覺）
            if weight_g < 0:
                weight_g = abs(weight_g)

            # ---- 上秤 / 下秤判斷（遲滯）----
            if not on_scale and weight_g >= ON_SCALE_MIN_G:
                on_scale = True
                fed_this_visit = False
                stable_buf.clear()

            if on_scale and weight_g <= OFF_SCALE_MAX_G:
                on_scale = False
                fed_this_visit = False
                stable_buf.clear()

            # ---- 穩定緩衝更新 ----
            status = "IDLE"
            mode = "--"
            feed_sec = 0.0
            span = 0.0
            prog = 0
            is_stable = False

            if on_scale and not fed_this_visit:
                status = "ON"
                stable_buf.append(weight_g)
                prog, is_stable, span = stable_progress(stable_buf, STABLE_THRESHOLD_G)

                if is_stable:
                    status = "STABLE"
                    # 以穩定區間的平均值做決策（比單點更穩）
                    stable_w = round(sum(stable_buf) / len(stable_buf), 1)
                    mode, feed_sec = decide_feed(stable_w)

                    # 顯示「準備餵食」
                    line1 = f"W:{stable_w:6.1f}g {mode:>5}"
                    line2 = f"Feed {feed_sec:.2f}s..."
                    lcd_safe_write(bus, line1, line2, retries=3)

                    # 執行餵食（只餵一次，直到下秤）
                    dispense_food(pwm, feed_sec)
                    fed_this_visit = True

                    # 餵完稍等回穩
                    time.sleep(0.8)
            elif on_scale and fed_this_visit:
                status = "FED"
            else:
                status = "IDLE"

            # ---- LCD 顯示 ----
            # 第一行：目前重量 + 狀態
            # 第二行：穩定進度/跨度 or 時間
            line1 = f"W:{weight_g:7.1f}g {status:>4}"

            if status in ("ON", "STABLE"):
                # 例如：S: 7/10 d0.6
                line2 = f"S:{prog:2d}/{STABLE_N} d{span:3.1f}"
            elif status == "FED":
                # 顯示已餵
                line2 = "Done. step off!"
            else:
                line2 = time.strftime("%m/%d %H:%M:%S")

            # 避免 LCD 過度刷新（可選）
            if last_weight is None or abs(weight_g - last_weight) >= 0.1 or status != "IDLE":
                lcd_safe_write(bus, line1, line2, retries=3)
                last_weight = weight_g

            time.sleep(STABLE_SAMPLE_INTERVAL)

    finally:
        try:
            lcd_safe_write(bus, "Stopped", "Ctrl+C OK", retries=2)
            time.sleep(0.6)
            lcd_byte(bus, 0x01, LCD_CMD)
        except Exception:
            pass

        try:
            pwm.stop()
        except Exception:
            pass

        GPIO.cleanup()
        try:
            bus.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()

