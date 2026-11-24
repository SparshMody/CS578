# START HERE – Complete Setup Guide (no experience needed)

**Smart Trash Bin – CS 578 Group 15**

This guide walks you through the whole project, one small step at a time: building the hardware, loading the code, opening the dashboard, and running every test for the final presentation. You don't need to know how to program. Do the parts **in order**, and don't skip a ✅ **Check**. Each one confirms that a part works before you move on.

> **Time needed:** about 2 hours for Parts 1–9, the first time.
> Testing (Part 11) takes 2–3 more hours and can be split across days.

---

## Contents
1. [What you are building](#part-1--what-you-are-building)
2. [Gather your parts](#part-2--gather-your-parts)
3. [Install the software](#part-3--install-the-software-one-time)
4. [Download the project files](#part-4--download-the-project-files)
5. [Prepare the sensor](#part-5--prepare-the-us-100-sensor)
6. [Connect the wires](#part-6--connect-the-wires)
7. [First test: does the sensor work?](#part-7--first-test-does-the-sensor-work)
8. [Connect to Wi-Fi and open the dashboard](#part-8--connect-to-wi-fi-and-open-the-dashboard)
9. [Mount it on the bin and calibrate](#part-9--mount-it-on-the-bin-and-calibrate)
10. [Everyday use and the live demo](#part-10--everyday-use-and-the-live-demo)
11. [Run the tests (for the results slides)](#part-11--run-the-tests-for-the-results-slides)
12. [Troubleshooting](#part-12--troubleshooting)
13. [Glossary](#part-13--glossary)

---

## Part 1 – What you are building

```
   ┌──────────── trash bin lid ────────────┐
   │   [ESP32] ── 4 wires ── [US-100 sensor]│  ← sensor points DOWN into the bin
   └───────────────────┬───────────────────┘
                       │  USB cable (power)
                  phone charger / power bank / laptop

   ESP32 ── Wi-Fi (phone hotspot) ──► Laptop running the dashboard
                                      (shows 25% / 50% / 75% / Full)
```

- The **US-100 sensor** works like a bat. It sends out a sound pulse too high-pitched to hear and times how long the echo takes to come back from the trash. From that, it knows the distance to the trash.
- The **ESP32** is a tiny computer with Wi-Fi built in. It turns the distance into "how full is the bin" and sends that over Wi-Fi.
- The **dashboard** is a web page on your laptop that shows each bin's fill level and when it last reported. It warns you if the bin goes quiet.

---

## Part 2 – Gather your parts

| ✔ | Item | Notes |
|---|---|---|
| ☐ | ESP32 board | The kind with a USB port on one end and rows of pins on both sides |
| ☐ | US-100 ultrasonic sensor | Has 5 pins and a small black jumper cap on the back |
| ☐ | 4 Dupont wires | Use **female-to-female** (holes on both ends) if both boards have pins sticking out |
| ☐ | USB cable that fits the ESP32 | ⚠ It must be a **data** cable. Many cheap cables only charge. If the laptop never "sees" the board, try a different cable first |
| ☐ | Laptop (Mac or Windows) | Runs the software and the dashboard |
| ☐ | Phone with a hotspot | The ESP32 can't join SDSU eduroam |
| ☐ | Trash bin (40–80 cm deep is ideal) | |
| ☐ | Tape or zip ties | To attach the sensor to the lid |
| ☐ | Tape measure or ruler | For calibration and tests |
| ☐ | Flat piece of cardboard | Larger than the bin opening, for calibration |
| ☐ | Test "trash" | Crumpled paper, plastic bags, small boxes, bottles, an old t-shirt |
| ☐ | Optional: USB power bank | So the bin works away from the laptop |

---

## Part 3 – Install the software (one time)

### 3.1 Arduino IDE
This is the free app that loads code onto the ESP32.

1. Go to **https://www.arduino.cc/en/software**
2. Download **Arduino IDE 2.x**:
   - **Mac:** choose *Apple Silicon* if your Mac has an M1/M2/M3/M4 chip, otherwise *Intel*. To check, click the Apple menu → **About This Mac** and look at "Chip".
   - **Windows:** choose *Windows Win 10 and newer, 64 bits*.
3. Install it the normal way. On a Mac, drag it into **Applications**. On Windows, run the installer and click **Yes** to any driver prompts.
4. Open **Arduino IDE**.

### 3.2 Add ESP32 support to Arduino
1. In Arduino IDE, click **Tools → Board → Boards Manager…** (or the circuit-board icon on the left edge).
2. In the search box type **esp32**.
3. Find **"esp32 by Espressif Systems"** and click **INSTALL**. Wait 2–5 minutes.

✅ **Check:** it now says **INSTALLED** under "esp32 by Espressif Systems".

### 3.3 USB driver (only if needed)
Look at the small chip right next to the USB port on your ESP32:
- **CP2102 / CP2104:** install the "CP210x VCP" driver from **https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers**, then restart the computer.
- **CH340 / CH9102:** recent Macs and Windows usually have the driver built in. If the board doesn't show up in Part 7, search "CH340 driver" from **wch-ic.com**.

You can also skip this for now and come back only if Part 7 can't find the board.

### 3.4 Python (runs the dashboard)
- **Mac:** open **Terminal** (press `Cmd + Space`, type *Terminal*, press Enter). Type `python3 --version` and press Enter.
  - If it shows something like `Python 3.x.x`, you're done.
  - If a box pops up offering to install "command line developer tools", click **Install**, wait, then try again.
- **Windows:** go to **https://www.python.org/downloads/** and download Python 3. When the installer opens, **tick "Add python.exe to PATH"** at the bottom, then click Install.
  Then open **Command Prompt** (Start → type *cmd*) and type `python --version`.

✅ **Check:** the version command prints `Python 3.something`.

> **Windows users:** everywhere this guide says `python3`, type **`python`** instead.

---

## Part 4 – Download the project files

The easy way, no Git needed:
1. Go to **https://github.com/SparshMody/CS578**
2. Click the green **Code** button → **Download ZIP**.
3. Open your **Downloads** folder and double-click the ZIP to unzip it. You'll get a folder called **CS578-main**.
4. Move that folder somewhere easy, for example your **Desktop**.

Inside it you'll find:

| Folder / file | What it is |
|---|---|
| `firmware/SmartBin/SmartBin.ino` | The code that goes onto the ESP32 |
| `server/server.py` | The program that runs the dashboard |
| `server/dashboard.html` | The dashboard page itself (the server opens it for you) |
| `tools/simulate_bins.py` | Fake bins, so you can try the dashboard with no hardware |
| `testing/…` | Scripts that turn your test data into results and charts |
| `README.md` | Technical details |
| `START_HERE.md` | This guide |

### Try the dashboard right now (no hardware)
1. Open Terminal (Mac) or Command Prompt (Windows).
2. Type `cd ` (with a space after it), **drag the `server` folder into the window**, and press Enter. Dragging fills in the folder's location for you.
3. Type `python3 server.py` and press Enter. You should see `Dashboard: http://localhost:8000`.
4. Open a **second** Terminal window (Mac: `Cmd + N`; Windows: open Command Prompt again). Type `cd `, drag the **`tools`** folder in, press Enter, then type `python3 simulate_bins.py` and press Enter.
5. Open a web browser and go to **http://localhost:8000**

✅ **Check:** you see three bins changing. After about 30 seconds, **bin-3** turns grey with a **STALE** warning. That's on purpose: it shows what happens when a bin stops reporting.

To stop either program, click its window and press **Ctrl + C**. Stop both before continuing.

---

## Part 5 – Prepare the US-100 sensor

1. Turn the US-100 over and look at the back. You'll see a **small black plastic cap (jumper)** sitting on two pins.
2. **Pull the jumper cap off** with your fingers or tweezers, and keep it somewhere safe.
   - *Why:* with the cap on, the sensor uses a different communication mode. Our code needs the cap **off**.
3. Read the 5 pin labels on the front:
   **VCC · Trig/TX · Echo/RX · GND · GND**

---

## Part 6 – Connect the wires

⚠ **Unplug the ESP32 from USB while wiring.**

Find these labels printed next to the ESP32's pins. Your board may write **D5** instead of **5**, or **D18** instead of **18**.

| Wire | From US-100 pin | To ESP32 pin |
|---|---|---|
| 1 (use red if you have it) | **VCC** | **3V3** (sometimes "3.3V") |
| 2 | **Trig/TX** | **5** (or D5 / GPIO5) |
| 3 | **Echo/RX** | **18** (or D18 / GPIO18) |
| 4 (use black if you have it) | **GND** (either one) | **GND** (any GND pin) |

```
   US-100 (front)                         ESP32
 ┌──────────────────┐
 │ VCC  ────────────┼──── wire 1 ────►  3V3
 │ Trig/TX ─────────┼──── wire 2 ────►  5   (D5)
 │ Echo/RX ─────────┼──── wire 3 ────►  18  (D18)
 │ GND  ────────────┼──── wire 4 ────►  GND
 │ GND  (leave empty)│
 └──────────────────┘
```

Double-check every wire against the table. **VCC to 3V3** and **GND to GND** matter most, because swapping them can damage the sensor.

📸 Take a photo of your wiring for the presentation.

---

## Part 7 – First test: does the sensor work?

### 7.1 Open the code
1. In Arduino IDE: **File → Open…**, go to `CS578-main/firmware/SmartBin/` and open **SmartBin.ino**.

### 7.2 Choose the board and port
1. Plug the ESP32 into the laptop with the USB cable. A small light on the board should turn on.
2. **Tools → Board → esp32 → ESP32 Dev Module**
3. **Tools → Port →** choose the new entry:
   - **Mac:** looks like `/dev/cu.usbserial-XXXX`, `/dev/cu.SLAB_USBtoUART` or `/dev/cu.wchusbserialXXXX`. **Not** "Bluetooth".
   - **Windows:** `COM3`, `COM4` or similar.
   - **No new port?** Try another USB cable, then install the driver from step 3.3.

### 7.3 Upload
1. Click the **→ (Upload)** arrow button at the top left.
2. Wait. The bottom panel shows "Compiling…" and then "Connecting…".
   - If it sits at **"Connecting……"**, **press and hold the BOOT button** on the ESP32 until numbers start appearing, then let go.
3. It's finished when you see **"Hard resetting via RTS pin…"** or **"Done uploading"**.

### 7.4 Watch the readings
1. Click **Tools → Serial Monitor**.
2. In the Serial Monitor's bottom right, set the speed to **115200 baud**.
3. Press the **EN** or **RST** button on the ESP32 once to restart it.
4. You'll see lines like this every second:
   ```
   CSV,12000,45.3,45.1,28.6,25%,1.00
   ```
   The 3rd number is the distance in **cm** (here 45.3).
   You'll also see "Connecting to Wi-Fi 'YOUR_WIFI_NAME'…". That's expected, because we haven't set up Wi-Fi yet.

✅ **Check:** point the sensor at a wall from about 50 cm away and measure with a tape measure. The distance number should match within about 1–2 cm. Move your hand closer and farther; the number should follow.

❌ If the distance shows **nan** or never changes, see [Troubleshooting](#part-12--troubleshooting). It's usually the jumper still on, or Trig and Echo swapped.

🎉 **The hardware works.**

---

## Part 8 – Connect to Wi-Fi and open the dashboard

### 8.1 Turn on a phone hotspot (2.4 GHz)
The ESP32 only understands **2.4 GHz** Wi-Fi.
- **iPhone:** Settings → **Personal Hotspot** → turn on **Allow Others to Join** **and** turn on **Maximize Compatibility**. The second setting is what makes it 2.4 GHz.
- **Android:** Settings → Hotspot → **AP band: 2.4 GHz**.

Write down the **hotspot name** and **password**. Avoid special characters like quotes in them.

### 8.2 Connect the laptop to the same hotspot
Join the hotspot from the laptop's Wi-Fi menu. **The laptop and the ESP32 must be on the same network.**

### 8.3 Find the laptop's address (IP address)
- **Mac:** in Terminal type `ipconfig getifaddr en0` and press Enter. You get something like `172.20.10.2`.
- **Windows:** in Command Prompt type `ipconfig` and find **IPv4 Address** under "Wireless LAN adapter Wi-Fi".

Write it down. ⚠ This address can change when you reconnect to the hotspot. If the dashboard ever stops receiving data, check it again.

### 8.4 Put your Wi-Fi details into the code
At the top of **SmartBin.ino** in Arduino IDE, find the section marked `USER SETTINGS` and change **only the text inside the quotes**:

```cpp
const char* WIFI_SSID     = "YourHotspotName";
const char* WIFI_PASSWORD = "YourHotspotPassword";
const char* SERVER_URL    = "http://172.20.10.2:8000/api/update";   // ← your IP from 8.3
const char* BIN_ID        = "bin-1";
const char* BIN_LOCATION  = "Lab hallway";
```

Keep the quotes and the semicolons `;`. Then click **Upload (→)** again.

> 🔒 **Never upload this edited file to GitHub.** The repository is public, so anyone could read your hotspot password. Keep your edits on your own computer only.

### 8.5 Start the dashboard
1. In Terminal / Command Prompt: type `cd `, drag the **server** folder in, and press Enter.
2. Type `python3 server.py` and press Enter.
3. **Mac:** if a popup asks *"Do you want python3 to accept incoming network connections?"*, click **Allow**.
   **Windows:** if a Firewall popup appears, tick **Private networks** and click **Allow access**.
4. Open **http://localhost:8000** in the browser.

✅ **Check:**
- In the Serial Monitor, the "Connecting to Wi-Fi" messages stop.
- In the Terminal window, a new line appears every 5 seconds, like `bin-1  25% fill= 10.0% d= 54.0cm`.
- On the dashboard, a **bin-1** card appears and its **Last update** says "0–5 s ago". Wave your hand under the sensor and the distance changes within a couple of seconds.

**Leave this Terminal window open the whole time you use the dashboard.** Closing it stops the dashboard.

---

## Part 9 – Mount it on the bin and calibrate

Calibration tells the system how deep **your** bin is and where "full" is.

### 9.1 Mount
1. Tape or zip-tie the sensor to the **underside of the lid, in the center**, with its two round "eyes" **pointing straight down**. Any tilt causes wrong readings.
2. Tape the ESP32 on top of the lid, or on the side of the bin, where it stays dry. Route the USB cable out under the lid's edge.
3. Close the lid.

### 9.2 Calibrate "empty"
1. Make sure the bin is **completely empty** and the lid is closed.
2. In Arduino's **Serial Monitor**, click the text box at the top, type **`e`**, and press **Enter**.
3. Keep everything still for about 5 seconds. It replies `EMPTY set to 58.4 cm (saved)` (your number will differ).

### 9.3 Calibrate "full"
1. Decide where "full / needs emptying" is, for example 10 cm below the lid. It **must be at least 5 cm below the sensor**, because the sensor can't measure closer than that.
2. Hold the **flat cardboard** level, inside the bin, at that height. A teammate can help.
3. Type **`f`** and press **Enter**, and hold still until it replies `FULL line set to 10.2 cm (saved)`.

### 9.4 Confirm
Type **`s`** and press Enter. Write these numbers down; you need them for testing and for the report:

| | Value |
|---|---|
| EMPTY distance (cm) | |
| FULL distance (cm) | |
| **Usable height** = EMPTY − FULL (cm) | |

✅ **Check:** put trash in, about half way up, and close the lid. Within about 5 seconds the dashboard should show **50%**. Fill it to the full line and it should show **Full** (red). The blue light on the ESP32 also turns on.

The settings are saved inside the ESP32, so unplugging it doesn't erase them. Only redo calibration if you move the sensor or change bins. (`r` resets to defaults.)

🎉 **At this point the system works exactly as described in your slides.**

---

## Part 10 – Everyday use and the live demo

### Starting everything (each session)
1. Turn on the phone hotspot (with Maximize Compatibility).
2. Connect the laptop to it, and re-check the IP (Part 8.3). If it changed, update `SERVER_URL` and re-upload.
3. Power the ESP32: plug it into the laptop, a charger or a power bank. It reconnects by itself.
4. Start the dashboard: `python3 server.py` in the `server` folder.
5. Open **http://localhost:8000**.

### What the dashboard shows
| On the card | Meaning |
|---|---|
| Colored badge (25% / 50% / 75% / Full) | The current fill level |
| Bin graphic | Estimated fill percentage |
| Distance | Sensor → trash surface in cm |
| **Last update** | How long ago the bin last reported. It should stay under 5 s |
| Wi-Fi dBm | Signal strength: −50 is strong, −70 is OK, −80 is weak |
| Valid pings | % of sound pulses that came back. Low means soft or angled trash |
| Missed pkts | Status messages that never arrived over Wi-Fi |
| **STALE** (grey + warning) | No report for 20 s, so the shown level may be out of date |
| Line at the bottom | Fill history over the last few minutes |

### Demo script for the presentation (about 3 minutes)
1. Show the dashboard with the empty bin: **25%**, "1 s ago".
2. Add trash in handfuls. The level climbs to 50%, then 75%, then **Full**, and the light turns on.
3. Stick your hand in the bin for a second. The level **does not flicker**, which shows the filtering works.
4. Pile all the trash to one side. The reading is now wrong, which is a known limitation you can explain.
5. Unplug the ESP32. About 20 seconds later the card turns **STALE**.
6. Plug it back in. Within about 15 seconds it's live again.

**Backup plan:** if Wi-Fi fails during class, run `python3 simulate_bins.py` to show the dashboard, and play a phone video of the real bin working. Record that video in advance.

---

## Part 11 – Run the tests (for the results slides)

You'll run four tests. Before you start, make sure the dashboard is running and bin-1 is reporting (**not** STALE).

Results are saved automatically into files inside the project folder:
- `testing/results.csv`: every Test A sample
- `server/logs/readings.csv`: every message the bin ever sent

### Test A – Accuracy with different kinds of trash ⭐ (main result)

**Goal:** see how often the reported level matches the real level, and which trash shapes fool the sensor.

**What you need:** the usable height from Part 9.4, a ruler, and all the test trash.

#### A.1 Work out the target heights
Using your **usable height** (EMPTY − FULL), the trash heights for each level are:

| Level | Target trash height |
|---|---|
| 25% | usable height × 0.25 |
| 50% | usable height × 0.50 |
| 75% | usable height × 0.75 |
| Full | usable height × 1.00 (right at the full line) |

*Example:* EMPTY = 60 cm and FULL = 8 cm give a usable height of 52 cm. The targets are **13 cm, 26 cm, 39 cm and 52 cm**.

#### A.2 The six trash arrangements
| Name in dashboard | How to arrange it |
|---|---|
| `flat` | Spread the trash so the top is level |
| `piled-center` | Heap it into a mound right under the sensor |
| `piled-side` | Push it all against one wall |
| `bulky-items` | Boxes and bottles with gaps between them |
| `bag-crumpled` | Crumpled plastic bags on top |
| `soft-fabric` | A t-shirt or cloth on top (it absorbs sound) |

#### A.3 Record one sample
1. Arrange the trash at roughly the target height.
2. **Measure the real height:** put the ruler straight down from the trash top to the bin bottom at **5 spots** (center plus 4 corners). Add the five numbers and divide by 5.
3. **Work out the true fill %:** average height ÷ usable height × 100.
   *Example:* average 27 cm ÷ 52 cm × 100 = **52%**
4. Pick the true level from the true fill %:

   | True fill % | True level |
   |---|---|
   | below 37.5 | 25% |
   | 37.5 – 62.5 | 50% |
   | 62.5 – 87.5 | 75% |
   | 87.5 or more | Full |

5. Close the lid and **wait 10 seconds**.
6. On the dashboard, click **"Test mode – record a sample"** at the bottom to open it. Fill in:
   - **Bin:** bin-1
   - **Trial #:** it counts up automatically
   - **Trash arrangement:** pick from the list
   - **True level:** from step 4
   - **True fill %:** from step 3
7. Click **Record sample**. You'll see ✅ (correct) or ❌ (wrong), and the sample is saved.

#### A.4 How many samples
Each of **4 levels × 6 arrangements × 5 tries = 120 samples**. Rearrange the trash a little between tries. With two people this takes about 2 hours. One person arranges and measures; the other enters the data.

If time is short, 3 tries each gives 72 samples, which is still fine. Use the same number for every combination.

#### A.5 Get the results
In a Terminal: `cd `, drag the **testing** folder in, press Enter, then type:
```bash
python3 analyze_results.py
```
It prints the results and saves them to **`testing/results_summary.md`**.

**Want charts (PNG images for the slides)?** Run this once, then run the line above again:
```bash
python3 -m pip install matplotlib
```
This creates **`accuracy_by_arrangement.png`** and **`confusion_matrix.png`** in the testing folder.

### Test B – Does the reading stay steady?
**Goal:** prove the status doesn't flicker when nothing changes.
1. Fill the bin to about **60%** (close to the 50%/75% border, which is the hardest case). Close the lid.
2. Write down the **exact start time** shown on the dashboard card, e.g. `2026-12-01 14:00:00`.
3. Don't touch anything for **10 minutes**.
4. Write down the end time.
5. In Terminal, in the **testing** folder, run this with your own times:
   ```bash
   python3 link_and_stability_stats.py --since "2026-12-01 14:00:00" --until "2026-12-01 14:10:00"
   ```
6. Record **"level changes"**. The goal is **0**.

*Optional comparison slide:* in `SmartBin.ino`, change `HYSTERESIS_PCT = 4.0` to `0.0` and `CONFIRM_COUNT = 3` to `1`, upload, and repeat. You'll likely see the level flicker, which shows why the filtering matters. **Change both back afterwards and re-upload.**

### Test C – How far does Wi-Fi reach?
**Goal:** measure signal strength and lost messages at different distances. This is the wireless-networking part of the course.
1. Power the bin from a **power bank** so it can move. Keep the laptop and hotspot in one place.
2. Put the bin at each position below for **3 minutes**, and write down the start and end time of each:

   | Position | Start time | End time |
   |---|---|---|
   | 1 m from the phone | | |
   | 5 m | | |
   | 10 m | | |
   | 20 m | | |
   | Behind 1 wall | | |
   | Behind 2 walls | | |

3. For each row, run:
   ```bash
   python3 link_and_stability_stats.py --since "START" --until "END"
   ```
4. Record **RSSI mean**, **delivery ratio**, and **update gap max** for each position.
5. For the slides, make a simple chart of RSSI (dBm) vs. distance in Google Sheets or Excel.

### Test D – Does it notice when the bin goes offline?
1. With everything running, **unplug the ESP32** and start a phone stopwatch.
2. Stop the stopwatch when the card turns **STALE**. You should get about 20 seconds.
3. Plug the ESP32 back in and time again until the card is live (no longer STALE). You should get about 10–20 seconds.
4. Do it 3 times and average the numbers.
5. Also try turning **off the hotspot** for 1 minute, then on again, and note what happens.

### Results table (fill in for the slides)
| Measurement | Result |
|---|---|
| Overall accuracy (Test A) | ___ % from ___ samples |
| Best arrangement / accuracy | |
| Worst arrangement / accuracy | |
| Average fill % error | |
| Level changes in 10 min, filtering ON (Test B) | |
| Level changes in 10 min, filtering OFF (optional) | |
| RSSI at 1 m / 10 m / 20 m (Test C) | |
| Delivery ratio at 1 m / 10 m / 20 m | |
| Time until STALE shown (Test D) | |
| Time to recover after power returns | |

**Expected findings, so you can explain them:** `piled-center` usually reads **too full** because the sensor sees the peak. `piled-side` reads **too empty** because the sensor misses the pile. `soft-fabric` may give low "valid pings", because the fabric soaks up the sound.

---

## Part 12 – Troubleshooting

| Problem | What to do |
|---|---|
| No port appears in Tools → Port | Try a different USB cable (most common cause!) → try a different USB port → install the driver (Part 3.3) → restart the computer |
| Upload stuck at "Connecting……" | Hold the **BOOT** button during upload until percentages appear |
| "Failed to connect to ESP32" | Same as above; also close the Serial Monitor and try again |
| Serial Monitor shows gibberish | Set the speed to **115200** (bottom right) |
| Distance is `nan` or never changes | Is the **jumper on the back removed**? Are **Trig → 5** and **Echo → 18** (not swapped)? Is VCC on **3V3** and GND on **GND**? Is a wire loose? |
| Distance jumps around in an empty bin | The sensor is tilted or hitting the bin wall. Re-center it and point it straight down |
| Keeps saying "Connecting to Wi-Fi…" | Is the hotspot on with **Maximize Compatibility / 2.4 GHz**? Is the name and password typed exactly (capitals matter)? Did you re-upload after editing? |
| Serial Monitor says `POST failed: -1` | The IP in `SERVER_URL` is wrong or changed (redo Part 8.3), the dashboard isn't running, the laptop is on a different network, or the firewall blocked it (allow Python) |
| Dashboard says "Waiting for the first update" | Same as `POST failed` above |
| Dashboard says "server unreachable" | The Terminal running `server.py` was closed. Start it again |
| `python3: command not found` (Windows) | Use `python` instead of `python3` |
| `address already in use` | The server is already running in another window. Use that one, or close it with Ctrl+C |
| Level stuck at 25% | Calibration went wrong. Type `r`, then redo Part 9.2 and 9.3 |
| Test mode says "reading is stale – not recorded" | The bin isn't reporting. Fix the Wi-Fi first |
| `No module named matplotlib` | Run `python3 -m pip install matplotlib` (charts are optional) |

Still stuck? Copy the **last 20 lines of the Serial Monitor** and the **Terminal** output and send them to a teammate (or to Claude). Those lines usually show exactly what's wrong.

---

## Part 13 – Glossary

| Word | Meaning |
|---|---|
| **ESP32** | The small Wi-Fi-capable computer board |
| **US-100** | The ultrasonic distance sensor (measures with echoes) |
| **Firmware** | The code that runs on the ESP32 (`SmartBin.ino`) |
| **Upload / flash** | Copy the firmware onto the ESP32 |
| **Serial Monitor** | Arduino window for reading messages from, and typing commands to, the ESP32 over USB |
| **Hotspot** | Your phone sharing its internet over Wi-Fi |
| **IP address** | The laptop's "street address" on the network, e.g. 172.20.10.2 |
| **Server / dashboard** | The program on the laptop and the web page it shows |
| **Calibration** | Teaching the system what "empty" and "full" look like for your bin |
| **RSSI (dBm)** | Wi-Fi signal strength; closer to 0 is stronger |
| **Stale** | Data that's too old to trust because the bin stopped reporting |
| **Hysteresis** | A small "dead zone" that stops the level jumping back and forth at a boundary |
| **Terminal / Command Prompt** | The text window where you type commands |
