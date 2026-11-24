#!/usr/bin/env python3
"""
Fake ESP32 bins for testing the dashboard WITHOUT hardware.

    python3 simulate_bins.py                    # 3 bins -> http://localhost:8000
    python3 simulate_bins.py --url http://192.168.1.50:8000 --bins 2

bin-1 slowly fills up, bin-2 sits around 50% with sensor noise,
bin-3 stops sending after ~30 s so you can see the STALE flag.
Uses the same filtering/classification logic as the firmware.
"""
import argparse
import json
import random
import time
import urllib.request

LEVELS = ["25%", "50%", "75%", "Full"]
BOUNDS = [37.5, 62.5, 87.5]
HYST, CONFIRM, ALPHA = 4.0, 3, 0.3
EMPTY, FULL = 60.0, 8.0


def raw_level(p):
    l = 0
    while l < 3 and p >= BOUNDS[l]:
        l += 1
    return l


def level_hyst(p, cur):
    raw = raw_level(p)
    if raw > cur and p < BOUNDS[raw - 1] + HYST:
        return max(cur, raw - 1)
    if raw < cur and p > BOUNDS[raw] - HYST:
        return min(cur, raw + 1)
    return raw


class FakeBin:
    def __init__(self, bin_id, loc, start_pct, rate, noise, dies_after=None):
        self.id, self.loc, self.true_pct, self.rate, self.noise = bin_id, loc, start_pct, rate, noise
        self.dies_after, self.seq, self.ema, self.level = dies_after, 0, None, 0
        self.cand, self.cnt, self.t0 = 0, 0, time.time()

    def step(self):
        self.true_pct = min(100, self.true_pct + self.rate)
        true_d = EMPTY - self.true_pct / 100 * (EMPTY - FULL)
        pings = [true_d + random.gauss(0, self.noise) for _ in range(7)]
        if random.random() < 0.1:
            pings[0] = random.uniform(2, 300)  # occasional echo glitch
        med = sorted(pings)[3]
        self.ema = med if self.ema is None else ALPHA * med + (1 - ALPHA) * self.ema
        pct = max(0, min(100, (EMPTY - self.ema) / (EMPTY - FULL) * 100))
        prop = level_hyst(pct, self.level)
        if prop != self.level:
            self.cnt = self.cnt + 1 if prop == self.cand else 1
            self.cand = prop
            if self.cnt >= CONFIRM:
                self.level, self.cnt = prop, 0
        else:
            self.cand, self.cnt = self.level, 0
        self.seq += 1
        return {"bin_id": self.id, "location": self.loc, "seq": self.seq,
                "uptime_ms": int((time.time() - self.t0) * 1000), "distance_cm": round(self.ema, 1),
                "raw_median_cm": round(med, 1), "fill_pct": round(pct, 1), "level": LEVELS[self.level],
                "empty_cm": EMPTY, "full_cm": FULL, "valid_ratio": 1.0, "rssi": random.randint(-72, -48)}

    def alive(self):
        return self.dies_after is None or time.time() - self.t0 < self.dies_after


def post(url, data):
    req = urllib.request.Request(url + "/api/update", data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=3).read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--bins", type=int, default=3)
    ap.add_argument("--interval", type=float, default=2.0)
    a = ap.parse_args()
    bins = [FakeBin("bin-1", "Library entrance", 10, 0.8, 0.8),
            FakeBin("bin-2", "Cafeteria", 50, 0.0, 2.5),
            FakeBin("bin-3", "Parking lot", 70, 0.2, 1.0, dies_after=30)][: a.bins]
    print(f"Sending to {a.url}  (Ctrl+C to stop)")
    while True:
        for b in bins:
            if b.alive():
                d = b.step()
                try:
                    post(a.url, d)
                    print(f"{d['bin_id']}: {d['level']:>4s} {d['fill_pct']:5.1f}%")
                except Exception as e:
                    print(f"{b.id}: send failed ({e})")
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
