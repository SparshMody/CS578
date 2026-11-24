/*
 * Smart Trash Bin – Fill-Level Monitoring System (CS 578, Group 15)
 * ----------------------------------------------------------------
 * ESP32 + ultrasonic distance sensor (HC-SR04 / HC-SR04P / JSN-SR04T)
 *
 *  1. Measures distance from the lid to the trash surface.
 *  2. Filters readings (median of a burst + exponential moving average).
 *  3. Converts distance -> fill % using a calibrated EMPTY and FULL distance.
 *  4. Classifies the level as 25% / 50% / 75% / Full with hysteresis
 *     and a confirmation count so the status does not flicker.
 *  5. Sends a JSON status to the laptop dashboard over Wi-Fi (HTTP POST).
 *
 * Board: "ESP32 Dev Module" (Arduino IDE, esp32 core 2.x or 3.x)
 * No extra libraries needed (WiFi, HTTPClient, Preferences ship with the core).
 *
 * Serial monitor @115200 – commands (type a letter + Enter):
 *   e  = calibrate EMPTY (bin empty, lid closed)
 *   f  = calibrate FULL line (hold a flat board at the "needs emptying" height)
 *   s  = print status / calibration
 *   r  = reset calibration to defaults
 *   h  = help
 * Holding the BOOT button for 3 s also calibrates EMPTY.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Preferences.h>

// ======================= USER SETTINGS =======================
const char* WIFI_SSID     = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
// IP of the laptop running server/server.py (run `ipconfig` / `ifconfig`)
const char* SERVER_URL    = "http://192.168.1.100:8000/api/update";
const char* BIN_ID        = "bin-1";
const char* BIN_LOCATION  = "Lab hallway";

// Pins
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;   // HC-SR04 (5 V) needs a voltage divider on ECHO!
const int BOOT_BTN = 0;    // on-board BOOT button
const int LED_PIN  = 2;    // on-board LED on most dev boards (lit when Full)

// Default calibration (cm) – overwritten by 'e' / 'f' and saved to flash
const float DEFAULT_EMPTY_CM = 60.0;  // sensor -> bin bottom
const float DEFAULT_FULL_CM  = 8.0;   // sensor -> "needs emptying" line (keep >= 5 cm, sensor blind zone)

// Timing
const uint32_t MEASURE_INTERVAL_MS   = 1000;  // one filtered measurement per second
const uint32_t HEARTBEAT_INTERVAL_MS = 5000;  // send at least this often
const int      BURST_SIZE            = 7;     // raw pings per measurement (median)
const int      PING_GAP_MS           = 60;    // HC-SR04 needs ~60 ms between pings

// Filtering / classification
const float EMA_ALPHA          = 0.30;  // 0..1, lower = smoother but slower
const float HYSTERESIS_PCT     = 4.0;   // must cross a boundary by this much
const int   CONFIRM_COUNT      = 3;     // consecutive measurements before level changes
const float MAX_VALID_CM       = 400.0;
const float MIN_VALID_CM       = 2.0;

// Level boundaries on fill % (nearest-level rounding):
//   < 37.5 -> "25%" (25% or less) | 37.5–62.5 -> "50%" | 62.5–87.5 -> "75%" | >= 87.5 -> "Full"
const int   NUM_LEVELS = 4;
const char* LEVEL_NAMES[NUM_LEVELS] = {"25%", "50%", "75%", "Full"};
const float LEVEL_BOUNDS[NUM_LEVELS - 1] = {37.5, 62.5, 87.5};
// =============================================================

Preferences prefs;
float emptyCm = DEFAULT_EMPTY_CM;
float fullCm  = DEFAULT_FULL_CM;

float filteredCm = NAN;
float fillPct    = 0;
int   level      = 0;      // index into LEVEL_NAMES
int   candidate  = 0;
int   candidateCount = 0;
float lastValidRatio = 0;
float lastMedianCm   = NAN;

uint32_t lastMeasure = 0, lastSend = 0, seq = 0;
uint32_t sendOk = 0, sendFail = 0;
bool levelChangedSinceSend = true;

// ---------- sensor ----------
float pingOnceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(3);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long us = pulseIn(ECHO_PIN, HIGH, 30000UL);  // 30 ms ~ 5 m
  if (us == 0) return NAN;
  float cm = us * 0.0343f / 2.0f;
  if (cm < MIN_VALID_CM || cm > MAX_VALID_CM) return NAN;
  return cm;
}

void sortFloats(float* a, int n) {
  for (int i = 1; i < n; i++) {
    float k = a[i]; int j = i - 1;
    while (j >= 0 && a[j] > k) { a[j + 1] = a[j]; j--; }
    a[j + 1] = k;
  }
}

// Median of a burst; returns NAN if fewer than half the pings were valid.
float medianBurstCm(int n, float* validRatio) {
  float v[32]; int k = 0;
  n = min(n, 32);
  for (int i = 0; i < n; i++) {
    float d = pingOnceCm();
    if (!isnan(d)) v[k++] = d;
    delay(PING_GAP_MS);
  }
  if (validRatio) *validRatio = (float)k / n;
  if (k < (n + 1) / 2) return NAN;
  sortFloats(v, k);
  return (k % 2) ? v[k / 2] : (v[k / 2 - 1] + v[k / 2]) / 2.0f;
}

// ---------- estimation ----------
float distanceToFillPct(float cm) {
  float span = emptyCm - fullCm;
  if (span < 1) return 0;
  float p = (emptyCm - cm) / span * 100.0f;
  return constrain(p, 0.0f, 100.0f);
}

int rawLevelFor(float pct) {
  int l = 0;
  while (l < NUM_LEVELS - 1 && pct >= LEVEL_BOUNDS[l]) l++;
  return l;
}

// Hysteresis: to move up past a boundary you must exceed it by HYSTERESIS_PCT,
// to move down you must drop below it by HYSTERESIS_PCT.
int levelWithHysteresis(float pct, int current) {
  int raw = rawLevelFor(pct);
  if (raw > current) {
    float b = LEVEL_BOUNDS[raw - 1];
    if (pct < b + HYSTERESIS_PCT) return max(current, raw - 1);
  } else if (raw < current) {
    float b = LEVEL_BOUNDS[raw];
    if (pct > b - HYSTERESIS_PCT) return min(current, raw + 1);
  }
  return raw;
}

void measureAndClassify() {
  float vr;
  float med = medianBurstCm(BURST_SIZE, &vr);
  lastValidRatio = vr;
  lastMedianCm = med;
  if (isnan(med)) return;  // keep previous state on a bad burst

  filteredCm = isnan(filteredCm) ? med : EMA_ALPHA * med + (1 - EMA_ALPHA) * filteredCm;
  fillPct = distanceToFillPct(filteredCm);

  int proposed = levelWithHysteresis(fillPct, level);
  if (proposed != level) {
    if (proposed == candidate) candidateCount++;
    else { candidate = proposed; candidateCount = 1; }
    if (candidateCount >= CONFIRM_COUNT) {
      level = proposed;
      candidateCount = 0;
      levelChangedSinceSend = true;
    }
  } else {
    candidate = level; candidateCount = 0;
  }
  digitalWrite(LED_PIN, level == NUM_LEVELS - 1 ? HIGH : LOW);
}

// ---------- calibration ----------
void loadCalibration() {
  prefs.begin("smartbin", true);
  emptyCm = prefs.getFloat("empty", DEFAULT_EMPTY_CM);
  fullCm  = prefs.getFloat("full",  DEFAULT_FULL_CM);
  prefs.end();
}

void saveCalibration() {
  prefs.begin("smartbin", false);
  prefs.putFloat("empty", emptyCm);
  prefs.putFloat("full",  fullCm);
  prefs.end();
}

float averageForCalibration() {
  Serial.println(F("Calibrating – keep everything still..."));
  float sum = 0; int n = 0;
  for (int i = 0; i < 5; i++) {
    float m = medianBurstCm(9, nullptr);
    if (!isnan(m)) { sum += m; n++; }
  }
  if (n == 0) { Serial.println(F("  FAILED: no valid readings. Check wiring/aim.")); return NAN; }
  return sum / n;
}

void calibrateEmpty() {
  float d = averageForCalibration();
  if (isnan(d)) return;
  if (d <= fullCm + 5) { Serial.println(F("  Rejected: empty distance must be > full line + 5 cm")); return; }
  emptyCm = d; saveCalibration(); filteredCm = NAN;
  Serial.printf("  EMPTY set to %.1f cm (saved)\n", emptyCm);
}

void calibrateFull() {
  float d = averageForCalibration();
  if (isnan(d)) return;
  if (d >= emptyCm - 5) { Serial.println(F("  Rejected: full line must be < empty distance - 5 cm")); return; }
  if (d < 4) Serial.println(F("  Warning: < 4 cm is in the sensor blind zone; readings may be unreliable"));
  fullCm = d; saveCalibration(); filteredCm = NAN;
  Serial.printf("  FULL line set to %.1f cm (saved)\n", fullCm);
}

void printStatus() {
  Serial.printf("bin=%s  empty=%.1fcm  full=%.1fcm  filtered=%.1fcm  fill=%.1f%%  level=%s\n",
                BIN_ID, emptyCm, fullCm, filteredCm, fillPct, LEVEL_NAMES[level]);
  Serial.printf("wifi=%s  ip=%s  rssi=%d dBm  sent ok=%lu fail=%lu\n",
                WiFi.status() == WL_CONNECTED ? "up" : "down",
                WiFi.localIP().toString().c_str(), WiFi.RSSI(), sendOk, sendFail);
}

void printHelp() {
  Serial.println(F("Commands: e=cal EMPTY, f=cal FULL line, s=status, r=reset cal, h=help"));
}

void handleSerial() {
  while (Serial.available()) {
    char c = tolower(Serial.read());
    if (c == 'e') calibrateEmpty();
    else if (c == 'f') calibrateFull();
    else if (c == 's') printStatus();
    else if (c == 'r') { emptyCm = DEFAULT_EMPTY_CM; fullCm = DEFAULT_FULL_CM; saveCalibration(); filteredCm = NAN; Serial.println(F("Calibration reset.")); }
    else if (c == 'h' || c == '?') printHelp();
  }
}

void handleBootButton() {
  static uint32_t pressedAt = 0;
  if (digitalRead(BOOT_BTN) == LOW) {
    if (pressedAt == 0) pressedAt = millis();
    else if (millis() - pressedAt > 3000) { calibrateEmpty(); pressedAt = 0; while (digitalRead(BOOT_BTN) == LOW) delay(10); }
  } else pressedAt = 0;
}

// ---------- Wi-Fi ----------
void ensureWifi() {
  static uint32_t lastAttempt = 0;
  if (WiFi.status() == WL_CONNECTED) return;
  if (lastAttempt != 0 && millis() - lastAttempt < 10000) return;  // retry every 10 s
  lastAttempt = millis();
  Serial.printf("Connecting to Wi-Fi '%s'...\n", WIFI_SSID);
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void sendStatus() {
  if (WiFi.status() != WL_CONNECTED) { sendFail++; return; }
  char body[512];
  snprintf(body, sizeof(body),
    "{\"bin_id\":\"%s\",\"location\":\"%s\",\"seq\":%lu,\"uptime_ms\":%lu,"
    "\"distance_cm\":%.1f,\"raw_median_cm\":%.1f,\"fill_pct\":%.1f,\"level\":\"%s\","
    "\"empty_cm\":%.1f,\"full_cm\":%.1f,\"valid_ratio\":%.2f,\"rssi\":%d}",
    BIN_ID, BIN_LOCATION, (unsigned long)seq++, (unsigned long)millis(),
    isnan(filteredCm) ? -1.0f : filteredCm, isnan(lastMedianCm) ? -1.0f : lastMedianCm,
    fillPct, LEVEL_NAMES[level], emptyCm, fullCm, lastValidRatio, WiFi.RSSI());

  HTTPClient http;
  http.setTimeout(3000);
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  int code = http.POST((uint8_t*)body, strlen(body));
  http.end();
  if (code == 200) sendOk++; else { sendFail++; Serial.printf("POST failed: %d\n", code); }
}

// ---------- main ----------
void setup() {
  Serial.begin(115200);
  delay(300);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BOOT_BTN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  loadCalibration();
  Serial.println(F("\n=== Smart Trash Bin ==="));
  printHelp();
  WiFi.mode(WIFI_STA);
  ensureWifi();
  // Serial CSV header for logging tests from the serial monitor
  Serial.println(F("CSV,ms,median_cm,filtered_cm,fill_pct,level,valid_ratio"));
}

void loop() {
  handleSerial();
  handleBootButton();
  ensureWifi();

  uint32_t now = millis();
  if (now - lastMeasure >= MEASURE_INTERVAL_MS) {
    lastMeasure = now;
    measureAndClassify();
    Serial.printf("CSV,%lu,%.1f,%.1f,%.1f,%s,%.2f\n", (unsigned long)now,
                  lastMedianCm, filteredCm, fillPct, LEVEL_NAMES[level], lastValidRatio);
  }
  if (levelChangedSinceSend || now - lastSend >= HEARTBEAT_INTERVAL_MS) {
    sendStatus();
    lastSend = now;
    levelChangedSinceSend = false;
  }
}
