#!/usr/bin/env python3
"""
Analyze performance-test results (plan step 05).

    python3 analyze_results.py                 # reads testing/results.csv
    python3 analyze_results.py my_results.csv

Prints and saves (testing/results_summary.md):
  * overall classification accuracy
  * accuracy per trash arrangement and per true level
  * confusion matrix (true vs reported)
  * mean absolute error of fill % (if true_fill_pct was entered)
  * "off by more than one level" count (serious errors)
If matplotlib is installed, also saves accuracy_by_arrangement.png and confusion_matrix.png.
Standard library only otherwise.
"""
import csv
import os
import sys
from collections import Counter, defaultdict

LEVELS = ["25%", "50%", "75%", "Full"]
HERE = os.path.dirname(os.path.abspath(__file__))


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "n/a"


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results.csv")
    with open(path, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("true_level") and r.get("reported_level")]
    if not rows:
        sys.exit(f"No samples in {path}. Record some from the dashboard's Test mode first.")

    n = len(rows)
    correct = sum(r["true_level"] == r["reported_level"] for r in rows)
    idx = {l: i for i, l in enumerate(LEVELS)}
    far = sum(abs(idx.get(r["true_level"], 0) - idx.get(r["reported_level"], 0)) > 1 for r in rows)
    over = sum(idx.get(r["reported_level"], 0) > idx.get(r["true_level"], 0) for r in rows)
    under = sum(idx.get(r["reported_level"], 0) < idx.get(r["true_level"], 0) for r in rows)

    by_arr, by_lvl = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    conf = Counter()
    errs = []
    for r in rows:
        ok = r["true_level"] == r["reported_level"]
        for d, k in ((by_arr, r["arrangement"] or "(none)"), (by_lvl, r["true_level"])):
            d[k][0] += ok
            d[k][1] += 1
        conf[(r["true_level"], r["reported_level"])] += 1
        try:
            errs.append(abs(float(r["true_fill_pct"]) - float(r["reported_fill_pct"])))
        except (ValueError, TypeError, KeyError):
            pass

    out = ["# Performance test results", "",
           f"Source: `{os.path.basename(path)}` - {n} samples", "",
           f"**Overall accuracy: {correct}/{n} = {pct(correct, n)}**", "",
           f"- Reported too high (over-estimate): {over} ({pct(over, n)})",
           f"- Reported too low (under-estimate): {under} ({pct(under, n)})",
           f"- Off by more than one level: {far} ({pct(far, n)})"]
    if errs:
        errs.sort()
        out.append(f"- Fill % absolute error: mean {sum(errs)/len(errs):.1f} pts, "
                   f"median {errs[len(errs)//2]:.1f} pts, max {errs[-1]:.1f} pts ({len(errs)} samples)")
    out += ["", "## Accuracy by trash arrangement", "", "| Arrangement | Correct | Samples | Accuracy |", "|---|---|---|---|"]
    for k, (c, t) in sorted(by_arr.items()):
        out.append(f"| {k} | {c} | {t} | {pct(c, t)} |")
    out += ["", "## Accuracy by true level", "", "| True level | Correct | Samples | Accuracy |", "|---|---|---|---|"]
    for k in LEVELS:
        if k in by_lvl:
            c, t = by_lvl[k]
            out.append(f"| {k} | {c} | {t} | {pct(c, t)} |")
    out += ["", "## Confusion matrix (rows = true, columns = reported)", "",
            "| True \\ Reported | " + " | ".join(LEVELS) + " |", "|---" * (len(LEVELS) + 1) + "|"]
    for t in LEVELS:
        out.append(f"| **{t}** | " + " | ".join(str(conf[(t, p)]) for p in LEVELS) + " |")

    text = "\n".join(out) + "\n"
    print(text)
    md = os.path.join(os.path.dirname(os.path.abspath(path)), "results_summary.md")
    with open(md, "w") as f:
        f.write(text)
    print(f"Saved {md}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib not installed - skipping charts; `pip install matplotlib` to get PNGs)")
        return
    outdir = os.path.dirname(md)
    keys = sorted(by_arr)
    accs = [100 * by_arr[k][0] / by_arr[k][1] for k in keys]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.bar(keys, accs, color="#2a9d8f")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Classification accuracy by trash arrangement")
    for i, v in enumerate(accs):
        ax.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    fig.savefig(os.path.join(outdir, "accuracy_by_arrangement.png"), dpi=200)

    fig, ax = plt.subplots(figsize=(4.6, 4))
    m = [[conf[(t, p)] for p in LEVELS] for t in LEVELS]
    ax.imshow(m, cmap="Blues")
    ax.set_xticks(range(4), LEVELS)
    ax.set_yticks(range(4), LEVELS)
    ax.set_xlabel("Reported level")
    ax.set_ylabel("True level")
    ax.set_title("Confusion matrix")
    mx = max(max(r) for r in m) or 1
    for i in range(4):
        for j in range(4):
            ax.text(j, i, m[i][j], ha="center", va="center", color="white" if m[i][j] > mx / 2 else "black")
    plt.tight_layout()
    fig.savefig(os.path.join(outdir, "confusion_matrix.png"), dpi=200)
    print("Saved accuracy_by_arrangement.png and confusion_matrix.png")


if __name__ == "__main__":
    main()
