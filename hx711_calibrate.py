import RPi.GPIO as GPIO
import time

# ==============================
#  基本設定：GPIO 腳位（BCM 編號）
# ==============================
DT_PIN = 5    # HX711 DT
SCK_PIN = 6   # HX711 SCK

GPIO.setmode(GPIO.BCM)
GPIO.setup(DT_PIN, GPIO.IN)
GPIO.setup(SCK_PIN, GPIO.OUT)

# ==============================
#  低階讀取 HX711 raw 函式
# ==============================
def read_hx711_raw():
    """
    讀取 HX711 的 24-bit 原始數值（signed）
    """
    count = 0

    # 等待 DT 變 LOW（資料 ready）
    while GPIO.input(DT_PIN) == 1:
        pass

    # 讀 24 bit
    for _ in range(24):
        GPIO.output(SCK_PIN, True)
        count = count << 1
        GPIO.output(SCK_PIN, False)

        if GPIO.input(DT_PIN) == 1:
            count += 1

    # 補一個 clock，設定下一次的增益
    GPIO.output(SCK_PIN, True)
    GPIO.output(SCK_PIN, False)

    # 轉成 signed 24-bit
    if (count & 0x800000):   # 若最高位為 1，代表負數
        count |= ~0xFFFFFF   # 做 sign extend

    return count

# ==============================
#  多次取樣平均，減少抖動
# ==============================
def read_raw_average(times=10, delay=0.02):
    total = 0
    for _ in range(times):
        total += read_hx711_raw()
        time.sleep(delay)
    return total / times

# ==============================
#  歸零（Tare）：取得 offset
# ==============================
def calibrate_offset():
    print("【步驟 1】請先確認秤台上『沒有任何物品』，然後按 Enter 開始歸零 ...")
    input()
    offset = read_raw_average(times=30, delay=0.05)
    print(f"歸零完成，offset = {offset:.2f}")
    return offset

# ==============================
#  校正 scale：用一個已知重量算比例
# ==============================
def calibrate_scale(offset):
    print("\n【步驟 2】請在秤台上放上一個『已知重量』的物品，例如 500g 或 600g，放好後按 Enter ...")
    input()
    raw_with_weight = read_raw_average(times=30, delay=0.05)
    print(f"量測到的 raw (含重量) = {raw_with_weight:.2f}")

    known_weight = float(input("請輸入該物品的實際重量（單位：g，只輸數字，例如 500）："))
    scale = (raw_with_weight - offset) / known_weight
    print(f"\n校正完成：scale = {scale:.6f} (raw per g)")
    return scale

# ==============================
#  把 raw 轉成 g，並做平均＋四捨五入
# ==============================
def get_weight_grams(offset, scale, samples=15, sample_delay=0.02):
    """
    回傳經過平均濾波後的重量（單位：g），保留一位小數
    """
    raw_avg = read_raw_average(times=samples, delay=sample_delay)
    weight = (raw_avg - offset) / scale
    # 只保留 0.1g，避免小數一直跳
    return round(weight, 1), raw_avg

# ==============================
#  主程式流程
# ==============================
def main():
    try:
        print("==== HX711 完整測試＋校正程式 ====\n")

        # 步驟 1：歸零
        offset = calibrate_offset()

        # 步驟 2：校正 scale
        scale = calibrate_scale(offset)

        print("\n【步驟 3】開始連續顯示重量（Ctrl + C 結束）\n")
        print("提示：請嘗試放上／拿開物品，觀察重量變化。")

        last_weight = None   # 上一次顯示的重量（做死區用）
        deadband = 0.5       # 小於 0.5 g 的變化就不更新顯示，可自行調整

        while True:
            weight_g, raw_avg = get_weight_grams(offset, scale, samples=15, sample_delay=0.02)

            # 如果前後差太小，就當成沒變，避免畫面一直刷新
            if last_weight is None or abs(weight_g - last_weight) >= deadband:
                print(f"Raw_avg = {raw_avg:10.2f}  ->  Weight = {weight_g:7.1f} g")
                last_weight = weight_g

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n結束量測，清理 GPIO ...")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()

