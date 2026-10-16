"""Plots and a results table for one run of log_latency.py.

Usage: python tools/make_plots.py runs/<run>/samples.csv [--subtitle "..."] [--min-ms 40]

Writes next to the data:
  runs/<run>/plots/histogram|cdf|timeline .png and .pdf
  runs/<run>/results.csv   (one row: label, N, median, percentiles, timeouts, ...)
"""
import argparse
import csv
import logging
import os

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

for f in ["LiberationSans-Regular", "LiberationSans-Bold"]:
    p = f"/usr/share/fonts/truetype/liberation/{f}.ttf"
    if os.path.exists(p):
        fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": ["Arial", "Liberation Sans", "DejaVu Sans"], "font.size": 13,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#5F6368",
    "axes.labelcolor": "#202124", "xtick.color": "#5F6368", "ytick.color": "#5F6368",
    "axes.grid": True, "grid.color": "#E8EAED", "axes.axisbelow": True,
    "savefig.dpi": 220, "savefig.bbox": "tight", "pdf.fonttype": 42})
BLUE, BAND, INK, SUB, RED = "#1A73E8", "#D2E3FC", "#202124", "#5F6368", "#D93025"


def read_label(csv_path):
    """Return the --label stored in <csv>.log by log_latency.py, or ''."""
    log = csv_path + ".log"
    if not os.path.exists(log):
        return ""
    with open(log, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "# label:" in line:
                return line.split("# label:", 1)[1].strip()
    return ""


def write_results(path, run, label, d, x, nto, nrej):
    """Write the one-row results.csv for this run."""
    t = d.host_time_s.dropna()
    row = {
        "run": run,
        "label": label,
        "n": len(x),
        "timeouts": nto,
        "timeout_pct": round(100 * nto / (len(x) + nto), 2),
        "rejects": nrej,
        "median_ms": np.median(x),
        "p5_ms": np.percentile(x, 5),
        "p25_ms": np.percentile(x, 25),
        "p75_ms": np.percentile(x, 75),
        "p95_ms": np.percentile(x, 95),
        "p99_ms": np.percentile(x, 99),
        "mean_ms": x.mean(),
        "sd_ms": x.std(ddof=1),
        "min_ms": x.min(),
        "max_ms": x.max(),
        "duration_min": round((t.iloc[-1] - t.iloc[0]) / 60, 1) if len(t) > 1 else "",
    }
    row = {k: (round(v, 1) if isinstance(v, (float, np.floating)) else v) for k, v in row.items()}
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        w.writeheader()
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--min-ms", type=float, default=40)
    a = ap.parse_args()

    run_dir = os.path.dirname(os.path.abspath(a.csv))
    plot_dir = os.path.join(run_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)

    d = pd.read_csv(a.csv)
    if "timeout" not in d:
        d["timeout"] = 0
    if "rejected" not in d:
        d["rejected"] = 0
    valid = d[(d.timeout == 0) & d.latency_ms.notna()]
    ok = valid[(valid.rejected == 0) & (valid.latency_ms >= a.min_ms)]
    x = ok.latency_ms.values
    n, nto, nrej = len(x), int(d.timeout.sum()), len(valid) - len(ok)
    med, p5, p95 = np.median(x), np.percentile(x, 5), np.percentile(x, 95)
    stat = f"N = {n}  ·  median {med:.0f} ms  ·  p5–p95 {p5:.0f}–{p95:.0f} ms  ·  timeouts {100*nto/(n+nto):.1f} %"
    sub = a.subtitle or stat

    def finish(fig, ax, title, name):
        ax.set_title(title, loc="left", fontweight="bold", color=INK, pad=26)
        ax.text(0, 1.02, sub, transform=ax.transAxes, color=SUB, fontsize=11.5)
        for ext in ("png", "pdf"):
            fig.savefig(os.path.join(plot_dir, f"{name}.{ext}"))
        plt.close(fig)

    lo = max(0, np.floor((p5 - 30) / 10) * 10)
    hi = np.ceil((p95 + 50) / 10) * 10

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.axvspan(p5, p95, color=BAND, zorder=0)
    ax.hist(x[x < hi], bins=np.arange(lo, hi, 2.5), color=BLUE)
    ax.axvline(med, color=INK, lw=1.5, ls="--")
    yt = ax.get_ylim()[1]
    ax.text(med + 1.5, yt * 0.93, f"median {med:.0f} ms", color=INK, fontsize=12)
    ax.text(p95 - 1, yt * 0.80, "p5–p95", ha="right", color=BLUE, fontsize=11)
    ax.set_xlim(lo, hi)
    ax.set_xlabel("glass-to-glass latency (ms)")
    ax.set_ylabel("samples")
    finish(fig, ax, "Local camera-to-eye latency", "histogram")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    xs = np.sort(x)
    ax.plot(xs, np.arange(1, n + 1) / n, color=BLUE, lw=2.5)
    for q, v in [(0.5, med), (0.95, p95)]:
        ax.plot([lo, v], [q, q], color=SUB, lw=1, ls=":")
        ax.plot([v, v], [0, q], color=SUB, lw=1, ls=":")
        ax.text(v + 2, q - 0.06, f"{'median' if q == .5 else 'p95'} {v:.0f} ms", color=INK, fontsize=12)
    ax.set_xlim(lo, hi)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("glass-to-glass latency (ms)")
    ax.set_ylabel("fraction of samples ≤ x")
    finish(fig, ax, "Cumulative distribution", "cdf")

    fig, ax = plt.subplots(figsize=(8, 3.8))
    ymax = max(250, np.ceil(p95 * 1.8 / 50) * 50)
    y, i = valid.latency_ms.values, valid.idx.values
    ax.scatter(i[y <= ymax], y[y <= ymax], s=7, color=BLUE, lw=0)
    ax.scatter(i[y > ymax], np.full((y > ymax).sum(), ymax * 0.97), s=24, marker="^", color=BLUE)
    ax.scatter(d.idx[d.timeout == 1], np.full(nto, ymax * 0.97), s=30, marker="x", color=RED)
    ax.axhline(med, color=INK, lw=1.2, ls="--")
    ax.text(1.0, med, f" {med:.0f} ms", transform=ax.get_yaxis_transform(), va="center", color=INK, fontsize=11)
    ax.set_ylim(0, ymax)
    ax.set_xlabel("sample")
    ax.set_ylabel("latency (ms)")
    ax.text(0.99, 0.86, f"▲ > {ymax:.0f} ms   × timeout", transform=ax.transAxes, ha="right", color=SUB, fontsize=10)
    finish(fig, ax, "Latency per sample", "timeline")

    write_results(os.path.join(run_dir, "results.csv"), os.path.basename(run_dir), read_label(a.csv), d, x, nto, nrej)
    print(stat)
    print(f"plots   -> {plot_dir}")
    print(f"results -> {os.path.join(run_dir, 'results.csv')}")


if __name__ == "__main__":
    main()
