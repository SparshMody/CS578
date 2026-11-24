# Smart Trash Bin – Fill-Level Monitoring System
**CS 578 Wireless Networks · Group 15** – Hongzhen Xu, Sparsh Mody, Chinmay Patel

> 👉 **New to this? Open [START_HERE.md](START_HERE.md)**. It's a step-by-step setup guide for our exact parts (ESP32 + US-100 + Dupont wires). With the **US-100 at 3.3 V** you don't need the voltage divider described below.

An ultrasonic sensor on the lid measures the distance to the trash surface. An ESP32 filters that, estimates the fill level, classifies it as **25% / 50% / 75% / Full**, and sends it over **Wi-Fi** to a **web dashboard on a laptop**. The dashboard shows the last update time and flags **stale** data.

```
USB power ──► Ultrasonic sensor ◄─trigger/echo─► ESP32 ──Wi-Fi HTTP POST (JSON)──► Laptop: server.py + dashboard
```

## What's in this folder

| Path | What it is | Plan step |
|---|---|---|
| `firmware/SmartBin/SmartBin.ino` | ESP32 code: sensing, filtering, calibration, classification, Wi-Fi | 02, 03, 04 |
| `server/server.py` | Laptop server (Python standard library only, nothing to install) | 04 |
| `server/dashboard.html` | Live dashboard plus a **Test mode** panel for recording ground truth | 04, 05 |
| `tools/simulate_bins.py` | Fake bins, so the dashboard can be built and demoed before the hardware works | 04 |
| `testing/analyze_results.py` | Accuracy, confusion matrix, per-arrangement results, charts | 05 |
| `testing/link_and_stability_stats.py` | Packet delivery, RSSI, update gaps, level flicker | 05 |
| `testing/results_template.csv` | Column layout for test samples, in case you log by hand | 05 |

---

## 01 · Research & design (everyone)

### Bill of materials
| Qty | Part | Notes |
|---|---|---|
| 1 | ESP32 dev board (ESP32-WROOM-32 DevKit) | Wi-Fi built in |
| 1 | Ultrasonic sensor: **HC-SR04P** or RCWL-1601 (3.3 V-safe) *or* HC-SR04 (5 V) | The plain HC-SR04 needs the voltage divider below. JSN-SR04T is waterproof but has a ~20 cm blind zone |
| 2 | Resistors, 1 kΩ + 2 kΩ (only for the 5 V HC-SR04) | ECHO level shifter |
| 1 | Breadboard + jumper wires | |
| 1 | USB cable + USB power bank or charger | Powers everything (slide 3) |
| 1 | Trash bin, ~40–80 cm deep | Wider bins mean fewer echoes off the walls |
| – | Mounting: tape, zip ties or a 3D-printed bracket; tape measure; ruler | |
| – | Test "trash": paper, crumpled bags, boxes, bottles, cloth | For the arrangement tests |

### Fill-level categories (decided)
Fill % = (empty distance − measured distance) / (empty distance − full-line distance) × 100

| Fill % | Reported level |
|---|---|
| < 37.5 | **25%** (this means "25% or less") |
| 37.5 – 62.5 | **50%** |
| 62.5 – 87.5 | **75%** |
| ≥ 87.5 | **Full** (needs emptying) |

Each fill % is rounded to the nearest level. The "Full line" is the height where staff should empty the bin, and you set it during calibration. To change the categories, edit `LEVEL_BOUNDS` and `LEVEL_NAMES` in the firmware.

---

## 02 · Hardware assembly (Sparsh)

### Wiring
| Sensor pin | ESP32 pin |
|---|---|
| VCC | **VIN / 5V** for the HC-SR04; **3V3** for the HC-SR04P or RCWL-1601 |
| GND | GND |
| TRIG | **GPIO 5** |
| ECHO | **GPIO 18**. For the 5 V HC-SR04 it **must** go through a divider: |

```
HC-SR04 ECHO ──[1 kΩ]──┬── GPIO 18
                       │
                     [2 kΩ]
                       │
                      GND          (5 V × 2/3 ≈ 3.3 V – protects the ESP32)
```

### Mounting
- Mount the sensor at the **center of the lid's underside, pointing straight down**. Tilt produces wrong distances.
- The beam is a cone of about 15°. If readings jump around in an empty bin, the walls are reflecting the signal. Move the sensor closer to the center or use a wider bin.
- Keep the full line **at least 5 cm below the sensor**, because the sensor can't measure anything closer than that.
- Take photos of the mounting for the presentation.

---

## 03 · Detection algorithm (Hongzhen, with Sparsh for calibration)

### Flashing the ESP32
1. Install the Arduino IDE. In Boards Manager, install **"esp32 by Espressif"**.
2. Open `firmware/SmartBin/SmartBin.ino`. In **USER SETTINGS**, fill in `WIFI_SSID`, `WIFI_PASSWORD`, `SERVER_URL` (the laptop's IP, see step 04), `BIN_ID` and `BIN_LOCATION`.
3. Select the board **ESP32 Dev Module** and the right COM port, then click Upload. If it hangs on "Connecting…", hold BOOT.
4. Open Serial Monitor at **115200** and type `h` to see the commands.

> **Wi-Fi note:** the ESP32 only connects to **2.4 GHz** networks. It **can't log in to SDSU's eduroam (WPA2-Enterprise)** with this code. Use a phone hotspot or a home router, and put the laptop on the same network.

### How the algorithm works (use this to explain it on the slides)
1. **Burst + median.** Each second the ESP32 sends 7 pings, 60 ms apart. It discards invalid echoes (none, < 2 cm or > 400 cm) and takes the **median**, which removes outliers like a single echo off a wall. If fewer than half the pings are valid, it skips that cycle and keeps the last state.
2. **Exponential moving average** (α = 0.3). This smooths the remaining noise.
3. **Distance → fill %** using the calibrated empty and full distances, clamped to 0–100.
4. **Hysteresis (±4%).** To change level, the reading must pass a boundary by 4 points. This stops flicker right at a boundary.
5. **Confirmation count (3).** The new level has to hold for 3 measurements in a row before it's reported. A hand reaching in or a lid bump won't change the status.
6. **Send.** The ESP32 sends a JSON status right away when the level changes, and otherwise every 5 s as a heartbeat.

On the slides, steps 1–2 and 4–5 are the answer to **"Stable readings"**.

### Calibration procedure (slide 4: "Calibration")
1. Mount the sensor in its final position and close the lid on the **empty** bin. Type **`e`** in Serial Monitor, or hold BOOT for 3 s. This sets the **empty reference**.
2. Hold a flat piece of cardboard level at the **"needs emptying" height**, then type **`f`**. This sets the **full line**.
3. Type **`s`** to check the values. They're saved to flash and survive a power cycle. `r` resets them to the defaults.
4. Write down the empty and full distances and the bin's inner depth for the report.

Every second the Serial Monitor also prints a `CSV,...` line (median, filtered, fill %, level). You can copy it into a spreadsheet to plot raw vs. filtered readings, which makes a good slide.

---

## 04 · Wireless & dashboard (Chinmay)

### Run the server on the laptop
```bash
cd server
python3 server.py            # options: --port 8000  --stale 20
```
- Open **http://localhost:8000**.
- Find the laptop's IP address: run `ipconfig` on Windows, or `ipconfig getifaddr en0` / `ip a` on Mac/Linux. Put `http://<that IP>:8000/api/update` into `SERVER_URL` in the firmware.
- If the ESP32's POST fails, **allow Python through the laptop firewall** for private networks.

### Without hardware
```bash
python3 tools/simulate_bins.py          # 3 fake bins; bin-3 stops after 30 s → shows STALE
```

### What the dashboard shows (slide 4: "Connection reliability")
For each bin: the level badge, a fill graphic, estimated fill %, distance, **last update time ("x s ago" + timestamp)**, Wi-Fi RSSI, valid-ping ratio, **missed packets** (worked out from sequence-number gaps), and a fill-history line.
If no update has arrived for **20 s** (4 missed heartbeats), the badge changes to **STALE** and a warning appears. Everything that arrives is logged to `server/logs/readings.csv`.

### Message format (ESP32 → server)
`POST /api/update`
```json
{"bin_id":"bin-1","location":"Lab hallway","seq":42,"uptime_ms":210345,
 "distance_cm":31.2,"raw_median_cm":31.0,"fill_pct":55.4,"level":"50%",
 "empty_cm":60.0,"full_cm":8.0,"valid_ratio":1.00,"rssi":-58}
```

---

## 05 · Performance testing (Chinmay leads; everyone helps)

### Test A – Classification accuracy under different trash arrangements (the main result)
**Ground truth.** With a ruler, measure the trash height from the bin bottom at **5 points** (center + 4 quadrants) and average them.
True fill % = average height / (bin depth − full-line distance from the lid) × 100. Map it to a level using the table in step 01.

**Arrangements** (these are in the Test-mode dropdown):
`flat` · `piled-center` (a peak under the sensor) · `piled-side` (a peak away from the sensor) · `bulky-items` (boxes or bottles with gaps) · `bag-crumpled` · `soft-fabric` (sound-absorbing)

**Matrix.** 4 levels × 6 arrangements × **5 trials = 120 samples**. Rearrange the trash between trials.

**Procedure for each sample:**
1. Arrange the trash, close the lid, and **wait ~10 s** for the filter to settle.
2. On the dashboard, open **Test mode** and choose the bin, arrangement, true level and true fill %.
3. Click **Record sample**. This saves the true and reported values to `testing/results.csv`. The server refuses stale readings.

**Analyze:**
```bash
python3 testing/analyze_results.py        # writes results_summary.md (+ PNG charts if matplotlib is installed)
```
You get overall accuracy, accuracy per arrangement and per level, a confusion matrix, over- vs. under-estimates, and fill % error.

**What to expect, so you can explain it:** the sensor measures the **closest point under its beam**. A `piled-center` arrangement will over-estimate and `piled-side` will under-estimate. Soft or angled surfaces can absorb or deflect the echo, which shows up as a low valid-ping ratio. Those are your "uneven trash surfaces" findings.

### Test B – Reading stability
Leave the bin untouched for **10 min** at a level near a boundary, for example about 60%. Then run
`python3 testing/link_and_stability_stats.py --since "YYYY-MM-DD HH:MM:SS" --until "..."`
The goal is **0 level changes**. For a comparison slide, repeat with `HYSTERESIS_PCT = 0` and `CONFIRM_COUNT = 1` (filtering off) and show the difference.

### Test C – Wi-Fi link quality (the wireless part of the course)
Put the bin at **1, 5, 10, 20 m** and behind 1–2 walls, **3 min each**. Note the start and end time of each run. For each position, run `link_and_stability_stats.py` with `--since/--until` and record the **mean RSSI, packet delivery ratio and max update gap**. Plot RSSI vs. distance.

### Test D – Stale-data detection
While data is flowing, unplug the ESP32 or turn off the hotspot. Time how long it takes until **STALE** appears. With the defaults this should be about 20 s. Then restore power and time how long it takes for the ESP32 to reconnect (it retries every 10 s) and for the warning to clear.

### Results table for the slides
| Metric | Value |
|---|---|
| Overall classification accuracy (120 samples) | |
| Worst arrangement / its accuracy | |
| Mean fill % error | |
| Level changes in 10-min static test (filter on / off) | |
| Packet delivery ratio @ 1 m / 10 m / 20 m | |
| RSSI @ 1 m / 10 m / 20 m | |
| Time to STALE flag / time to recover | |

---

## 06 · Integration & demonstration (everyone)

### Live demo script (~3 min)
1. Show the dashboard with the bin empty: **25%**, updated "1 s ago".
2. Add trash in stages. The level goes to 50%, then 75%, then **Full**, and the board LED lights up.
3. Reach a hand in briefly. The level **doesn't flicker**, thanks to confirmation and hysteresis.
4. Pile trash to one side. The estimate is wrong, which shows a known limitation.
5. Unplug the ESP32. After about 20 s the card shows **STALE**.
6. Plug it back in. It reconnects and the warning clears.

**Backup:** if the Wi-Fi in the room fails, use a phone hotspot. If everything fails, run `simulate_bins.py` and show a recorded video of the hardware.

### Final presentation outline (about 10 slides, extending your proposal deck)
1. Title
2. Problem & goal (reuse slide 2)
3. System architecture (reuse the slide 3 diagram) + a photo of the real build
4. Hardware & wiring (photo, the divider, sensor mounting)
5. Algorithm: median → EMA → fill % → hysteresis + confirmation (a raw vs. filtered plot from the serial CSV)
6. Wireless design: HTTP POST over Wi-Fi, 5 s heartbeat, sequence numbers, stale detection
7. Dashboard screenshot
8. Results: accuracy by arrangement (chart) + confusion matrix
9. Results: stability (filter on/off) + Wi-Fi RSSI and delivery ratio vs. distance
10. Limitations & future work, then the demo

### Limitations to state honestly
- A single-point sensor can't see an uneven surface. It measures the peak under the beam, not the average fill.
- Soft or angled trash can absorb or deflect the ultrasound. Temperature changes the speed of sound slightly (about 0.17% per °C).
- Wi-Fi is 2.4 GHz WPA2-Personal only. It needs infrastructure and isn't power-efficient enough for battery use.
- HTTP has no authentication or encryption. A real deployment would need TLS and per-device keys.
- The server keeps the latest state in memory; only the CSV log survives a restart.

### Future work ideas
Several sensors or a ToF array (VL53L5CX) for a surface map · deep sleep + battery operation · LoRa/LoRaWAN or BLE for longer range or lower power · MQTT broker · a temperature-compensated speed of sound · route optimization for staff

---

## Team checklist
| Who | Task | Done |
|---|---|---|
| Sparsh | Buy/collect parts; wire the sensor (divider!); mount it on the lid | ☐ |
| Sparsh | Calibrate empty and full; record the distances and bin depth | ☐ |
| Hongzhen | Flash the firmware; verify the serial CSV; tune `EMA_ALPHA`, `HYSTERESIS_PCT`, `CONFIRM_COUNT` | ☐ |
| Hongzhen | Raw-vs-filtered plot for the algorithm slide | ☐ |
| Chinmay | Run the server and dashboard; test with the simulator; connect the real ESP32 | ☐ |
| Chinmay | Lead Tests A–D; run the analysis scripts; make the charts | ☐ |
| All | Integration run-through; demo rehearsal; final slides; limitations | ☐ |

## Troubleshooting
| Symptom | Fix |
|---|---|
| Distance is always NaN / "no valid readings" | Check TRIG/ECHO pins and the divider. The sensor needs 5 V unless it's the P version |
| Readings jump in an empty bin | Wall echoes: center the sensor, aim it straight down, try a wider bin |
| ESP32 never connects | It needs a 2.4 GHz WPA2-Personal network (not eduroam); check the SSID and password |
| "POST failed: -1" | Wrong `SERVER_URL` IP, laptop firewall, or the laptop is on a different network |
| Dashboard empty but the ESP32 says it sent | You opened a different server/port; check the server console for lines |
| Level stuck at 25% | Calibration was done with trash inside, or the empty/full values were swapped. Type `s`, then `r`, and recalibrate |
