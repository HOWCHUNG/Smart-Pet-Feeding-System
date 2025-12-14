# Smart Pet Feeding System

## Project Overview
This project implements a **Smart Pet Weight Monitoring and Automatic Feeding System** using a Raspberry Pi.
A load cell with HX711 amplifier is used to continuously measure the pet’s weight, and an SG90 servo motor
is controlled to dispense different amounts of food based on the measured weight.
A 5kg load cell is used to simulate small pets (e.g., hamster) for demonstration purposes.

---

## System Architecture
The system follows an event-driven and rule-based control architecture:

1. **On-scale detection**: The system detects when a pet steps onto the scale.
2. **Weight stability verification**: Feeding decisions are made only after the weight remains stable
   for a predefined number of samples.
3. **Rule-based decision**: The feeding amount is determined by the stable weight range.
4. **Automatic feeding**: Food is dispensed once per visit. The pet must step off the scale before
   the next feeding is allowed.

---

## Hardware Components
- Raspberry Pi
- HX711 Load Cell Amplifier
- 5kg Load Cell (used for simulation)
- 16x2 I2C LCD (PCF8574, I2C address typically 0x27)
- SG90 Servo Motor

---

## Wiring and GPIO Mapping

| Component | Raspberry Pi GPIO |
|----------|-------------------|
| HX711 DT | GPIO 5 |
| HX711 SCK | GPIO 6 |
| LCD SDA | GPIO 2 |
| LCD SCL | GPIO 3 |
| SG90 Signal | GPIO 18 |

---

## Software Logic
The system adopts a **rule-based intelligence mechanism**:

- Feeding is triggered only when the pet is detected on the scale.
- Weight measurements must be stable (N consecutive samples within a threshold)
  before being considered valid.
- Feeding amount is adjusted according to the weight range:
  - Underweight → more food
  - Normal weight → normal feeding
  - Overweight → reduced feeding
- After feeding, the system requires the pet to step off the scale to prevent repeated feeding.

---

## How to Run

### 1. Enable I2C
Enable I2C using `raspi-config`, then verify:
```bash
ls /dev/i2c*
sudo i2cdetect -y 1
# Smart-Pet-Feeding-System
```

---

## 2. Install Required Packages
```
sudo apt-get update
sudo apt-get install -y python3-smbus i2c-tools
```
---

### 3. Calibration
Before running the system, calibrate the load cell:
```
sudo python3 hx711_calibrate.py
```

---
## 4. Run the Main Program
```
sudo python3 src/main_feed_by_weight.py
```
---

## Demo Video
```YouTube demo video:
```
---

## References

Raspberry Pi GPIO Documentation
https://www.raspberrypi.com/documentation/computers/raspberry-pi.html

HX711 Datasheet and Tutorials
https://learn.sparkfun.com/tutorials/load-cell-amplifier-hx711-hookup-guide

I2C LCD (PCF8574) Tutorials
https://wiki.sunfounder.cc/index.php?title=I2C_LCD1602

RPi.GPIO Python Library
https://sourceforge.net/p/raspberry-gpio-python/wiki/Home/
