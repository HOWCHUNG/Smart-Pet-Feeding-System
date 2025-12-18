# 智慧寵物體重監控與自動餵食系統  
Smart Pet Weight Monitoring and Automatic Feeding System

---

## 一、專案簡介（Project Overview）
本專案建置一套 **智慧寵物體重監控與自動餵食系統**，  
透過 Raspberry Pi 結合重量感測模組（HX711 + Load Cell），即時量測寵物體重，
並依據量測結果自動控制伺服馬達（SG90）進行餵食。

為符合實作需求與效益考量，本系統使用 **5kg Load Cell** 模擬小型寵物
（例如倉鼠）之體重變化，驗證智慧餵食邏輯與系統運作流程。

---

## 二、系統架構與流程（System Architecture）
本系統採用 **事件導向（Event-driven）與規則式（Rule-based）控制架構**，
整體流程如下：

1. **上秤偵測（On-scale detection）**  
   系統偵測是否有寵物站上秤台。

2. **重量穩定判斷（Weight stability verification）**  
   只有在重量連續多次量測皆落於允許誤差範圍內時，才視為有效體重。

3. **餵食決策判斷（Rule-based decision）**  
   依據穩定體重所屬區間，判斷本次應餵食的份量。

4. **自動餵食（Automatic feeding）**  
   透過 SG90 伺服馬達控制飼料出口，完成一次餵食動作。

5. **防止重複餵食機制**  
   系統要求寵物需離開秤台後，才允許下一次餵食判斷。

---

## 三、硬體設備清單（Hardware Components）
- Raspberry Pi  
- HX711 重量感測放大模組  
- 5kg Load Cell（用於小型寵物模擬）  
- 16x2 I2C LCD 顯示器（PCF8574）  
- SG90 伺服馬達  

---

## 四、接線與 GPIO 對照表（Wiring & GPIO Mapping）
### 接線示意圖
下圖為本專案實際使用之接線示意圖，用以輔助說明各硬體模組與 Raspberry Pi 之連接方式：

![系統接線圖](docs/wiring_diagram.jpg)

| 模組 | Raspberry Pi GPIO |
|-----|------------------|
| HX711 DT | GPIO 5 |
| HX711 SCK | GPIO 6 |
| LCD SDA | GPIO 2 |
| LCD SCL | GPIO 3 |
| SG90 控制訊號 | GPIO 18 |

---

## 五、軟體邏輯說明（Software Logic）
本系統核心邏輯包含以下設計重點：

- 只有在偵測到寵物站上秤台時，才啟動重量判斷流程  
- 重量必須通過「穩定判斷機制」，避免瞬間晃動造成誤判  
- 餵食量依據體重區間進行調整：
  - 體重偏低 → 增加餵食量  
  - 體重正常 → 標準餵食量  
  - 體重偏高 → 減少餵食量  
- 每次餵食後，需等待寵物離開秤台，防止重複餵食  

---

## 六、執行方式（How to Run）

### 1. 啟用 I2C 功能
使用 `raspi-config` 啟用 I2C，並確認裝置存在：
```
bash
ls /dev/i2c*
sudo i2cdetect -y 1
```

## 2. 安裝必要套件
```
sudo apt-get update
sudo apt-get install -y python3-smbus i2c-tools
```
---

### 3. 重量感測校正
在正式執行系統前，需先校正 Load Cell：
```
sudo python3 hx711_calibrate.py
```

---
## 4. 執行主程式
```
sudo python3 src/main_feed_by_weight.py
```
---

## 七、系統展示影片
YouTube 展示影片:
https://www.youtube.com/watch?v=-sbke4Zren4
---


## 八、專案開發過程中遇到種種問題與解決方式

### 1. 重量感測數值不穩定
初期使用 HX711 讀取重量時，量測數值非常容易因重量感測本身、外力或晃動而產生誤差。
為解決此問題，注意到HX711的供電穩定性，有著相當大程度的影響，若讀取到的config數值僅落在2900~3300，高機率是供電不穩定，需確認電源情況。
後續為避免此情況，加入「重量穩定判斷機制」，僅在連續多次量測
皆落於允許誤差範圍內時，才視為有效重量，避免誤判。

### 2. 誤觸造成重複餵食
若未設計防呆機制，寵物可能在同一次站上秤台時觸發多次餵食。
因此系統加入「需離開秤台後才能再次餵食」的邏輯，
有效防止短時間內重複投放飼料。

### 3. I2C LCD 通訊問題
在 LCD 初期測試時，曾遇到 I2C 裝置無法被偵測的情況。
經由檢查線路、更換杜邦線(換了很多次...)，並使用 `i2cdetect` 工具確認裝置位址後，
成功排除通訊問題並正常顯示資訊。

---
## 九、專案延伸與未來發展願景（Future Work & Extensions）

本專案目前已完成以體重為基礎的智慧餵食控制流程，
未來仍具備多項可延伸與擴充之發展方向，說明如下：

### 1. 體重歷史紀錄與趨勢分析
目前以「單次穩定體重」作為餵食決策依據，
未來可將每次量測結果儲存至本地資料庫或雲端平台，
進一步分析寵物體重的長期變化趨勢，
例如依據「週平均體重變化」動態調整每日餵食策略。

### 2. 網頁或行動裝置監控介面
可結合 Web Server 或 IoT 平台，
提供飼主透過瀏覽器或行動裝置即時查看：
- 寵物體重變化
- 餵食紀錄
- 系統運作狀態  
提升系統的互動性與實用性。

### 3. 多感測器整合
除體重感測外，未來可加入：
- 溫溼度感測
- 活動量感測（紅外線或加速度計）
透過多感測資料整合，建立更完整的寵物行為分析模型。

### 4. 個別寵物識別機制
可搭配 RFID 或影像辨識技術，
讓系統能夠辨識不同寵物個體，
實現「多寵物」環境下的個別化餵食控制。

### 5. 智慧化餵食策略
未來可結合機器學習或資料分析方法，
根據歷史體重、活動量與餵食結果，
自動學習最適合寵物的餵食模型，
進一步提升系統的智慧化程度。

透過上述延伸方向，本系統可由基礎的智慧餵食裝置，
逐步發展為具備監控、分析與預測能力的完整智慧寵物照護系統。

---


## 十、參考資料

Raspberry Pi GPIO Documentation
https://www.raspberrypi.com/documentation/computers/raspberry-pi.html

HX711 Datasheet and Tutorials
https://learn.sparkfun.com/tutorials/load-cell-amplifier-hx711-hookup-guide

I2C LCD (PCF8574) Tutorials
https://wiki.sunfounder.cc/index.php?title=I2C_LCD1602

RPi.GPIO Python Library
https://sourceforge.net/p/raspberry-gpio-python/wiki/Home/
