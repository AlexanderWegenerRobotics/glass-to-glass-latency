"""Slide plots from a log_latency.py CSV.

Usage: python make_plots.py run.csv --subtitle "D455 · 30 fps · UE 60 fps" [--out plots/run01] [--preview]
--preview adds a small footer marking the data as simulated (use for mock data only).
"""
import argparse, os, logging
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

for f in ["LiberationSans-Regular", "LiberationSans-Bold"]:
    p = f"/usr/share/fonts/truetype/liberation/{f}.ttf"
    if os.path.exists(p): fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": ["Arial", "Liberation Sans", "DejaVu Sans"], "font.size": 13,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#5F6368",
    "axes.labelcolor": "#202124", "xtick.color": "#5F6368", "ytick.color": "#5F6368",
    "axes.grid": True, "grid.color": "#E8EAED", "axes.axisbelow": True,
    "savefig.dpi": 220, "savefig.bbox": "tight", "pdf.fonttype": 42})
BLUE, BAND, INK, SUB, RED = "#1A73E8", "#D2E3FC", "#202124", "#5F6368", "#D93025"

ap = argparse.ArgumentParser()
ap.add_argument("csv"); ap.add_argument("--subtitle", default="")
ap.add_argument("--out", default="plot"); ap.add_argument("--min-ms", type=float, default=40)
ap.add_argument("--preview", action="store_true")
a = ap.parse_args()
if os.path.dirname(a.out): os.makedirs(os.path.dirname(a.out), exist_ok=True)

d = pd.read_csv(a.csv)
if "timeout" not in d: d["timeout"] = 0
if "rejected" not in d: d["rejected"] = 0
ok = d[(d.timeout == 0) & (d.rejected == 0) & (d.latency_ms >= a.min_ms)]
x = ok.latency_ms.values
n, nto = len(x), int(d.timeout.sum())
med, p5, p95 = np.median(x), np.percentile(x, 5), np.percentile(x, 95)
stat = f"N = {n}  ·  median {med:.0f} ms  ·  p5–p95 {p5:.0f}–{p95:.0f} ms  ·  timeouts {100*nto/(n+nto):.1f} %"

def finish(fig, ax, title, name):
    ax.set_title(title, loc="left", fontweight="bold", color=INK, pad=26)
    ax.text(0, 1.02, a.subtitle or stat, transform=ax.transAxes, color=SUB, fontsize=11.5)
    if a.preview:
        fig.text(0.01, -0.02, "Preview with simulated data", color="#9AA0A6", fontsize=8)
    fig.savefig(f"{a.out}_{name}.png"); fig.savefig(f"{a.out}_{name}.pdf"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.5))
lo = max(0, np.floor((p5 - 30) / 10) * 10); hi = np.ceil((p95 + 50) / 10) * 10
ax.axvspan(p5, p95, color=BAND, zorder=0)
ax.hist(x[x < hi], bins=np.arange(lo, hi, 2.5), color=BLUE)
ax.axvline(med, color=INK, lw=1.5, ls="--")
yt = ax.get_ylim()[1]
ax.text(med + 1.5, yt * 0.93, f"median {med:.0f} ms", color=INK, fontsize=12)
ax.text(p95 - 1, yt * 0.80, "p5–p95", ha="right", color=BLUE, fontsize=11)
ax.set_xlim(lo, hi); ax.set_xlabel("photon-to-photon latency (ms)"); ax.set_ylabel("samples")
if not a.subtitle: a.subtitle = stat
finish(fig, ax, "Local camera-to-eye latency", "histogram")

fig, ax = plt.subplots(figsize=(8, 4.5))
xs = np.sort(x); ax.plot(xs, np.arange(1, n + 1) / n, color=BLUE, lw=2.5)
for q, v in [(0.5, med), (0.95, p95)]:
    ax.plot([lo, v], [q, q], color=SUB, lw=1, ls=":"); ax.plot([v, v], [0, q], color=SUB, lw=1, ls=":")
    ax.text(v + 2, q - 0.06, f"{'median' if q == .5 else 'p95'} {v:.0f} ms", color=INK, fontsize=12)
ax.set_xlim(lo, hi); ax.set_ylim(0, 1.02)
ax.set_xlabel("photon-to-photon latency (ms)"); ax.set_ylabel("fraction of samples ≤ x")
finish(fig, ax, "Cumulative distribution", "cdf")

fig, ax = plt.subplots(figsize=(8, 3.8))
YMAX = max(250, np.ceil(p95 * 1.8 / 50) * 50)
allv = d[(d.timeout == 0)]
y = allv.latency_ms.values; i = allv.idx.values
ax.scatter(i[y <= YMAX], y[y <= YMAX], s=7, color=BLUE, lw=0)
ax.scatter(i[y > YMAX], np.full((y > YMAX).sum(), YMAX * 0.97), s=24, marker="^", color=BLUE)
ax.scatter(d.idx[d.timeout == 1], np.full(nto, YMAX * 0.97), s=30, marker="x", color=RED)
ax.axhline(med, color=INK, lw=1.2, ls="--")
ax.text(1.0, med, f" {med:.0f} ms", transform=ax.get_yaxis_transform(), va="center", color=INK, fontsize=11)
ax.set_ylim(0, YMAX); ax.set_xlabel("sample"); ax.set_ylabel("latency (ms)")
ax.text(0.99, 0.86, f"▲ > {YMAX:.0f} ms   × timeout", transform=ax.transAxes, ha="right", color=SUB, fontsize=10)
finish(fig, ax, "Latency per sample", "timeline")
print(stat)
