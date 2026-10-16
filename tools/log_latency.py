"""Log photon_latency.ino samples to CSV and print summary stats on Ctrl-C.

Usage:
    python log_latency.py <serial_port> <out.csv> [--label "jb20 d455 30fps"]
                          [--min-ms 40] [--summary results_summary.csv]

Each run writes its raw samples to <out.csv>. On Ctrl-C the summary (median, p5,
p95, ...) is printed and appended as one row to the summary CSV, together with the
label, so runs with different settings (jitter buffer, fps, exposure, camera) end
up side by side in one table.

Timeouts are written to the raw CSV too (timeout=1, empty latency) so stall bursts
keep their timestamps. All '#' info lines from the Arduino (calibration values,
errors, skips) are saved with host time to <out.csv>.log.

Samples below --min-ms are physically impossible for a camera -> encode -> display
chain (stray light, HUD flash) and are counted as rejects instead of being averaged
in. Large values are kept: they are real stalls and the median is robust to them.

Requires: pip install pyserial
"""
import argparse
import csv
import datetime
import os
import statistics
import time

import serial


def summarize(lat_ms, timeouts, rejects):
    """Print and return n, median, p5, p95, mean, stdev, min, max."""
    print(f"\nn={len(lat_ms)} timeouts={timeouts} rejected(<min)={rejects}")
    if len(lat_ms) < 20:
        print("too few samples for a summary (need >= 20)")
        return None
    q = statistics.quantiles(lat_ms, n=20)
    s = {
        "n": len(lat_ms),
        "median_ms": statistics.median(lat_ms),
        "p5_ms": q[0],
        "p95_ms": q[18],
        "mean_ms": statistics.fmean(lat_ms),
        "stdev_ms": statistics.stdev(lat_ms),
        "min_ms": min(lat_ms),
        "max_ms": max(lat_ms),
    }
    print(f"median={s['median_ms']:.1f} ms  p5={s['p5_ms']:.1f}  p95={s['p95_ms']:.1f}  "
          f"mean={s['mean_ms']:.1f}  sd={s['stdev_ms']:.1f}  "
          f"min={s['min_ms']:.1f}  max={s['max_ms']:.1f}")
    return s


def append_summary(path, label, out_path, s, timeouts, rejects):
    """Append one row per run to the shared summary CSV (header written once)."""
    fields = ["date", "label", "raw_file", "n", "median_ms", "p5_ms", "p95_ms",
              "mean_ms", "stdev_ms", "min_ms", "max_ms", "timeouts", "rejects"]
    new_file = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new_file:
            w.writeheader()
        row = {"date": datetime.datetime.now().isoformat(timespec="seconds"),
               "label": label, "raw_file": out_path,
               "timeouts": timeouts, "rejects": rejects}
        row.update({k: (f"{v:.1f}" if isinstance(v, float) else v) for k, v in s.items()})
        w.writerow(row)
    print(f"summary appended to {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", help="serial port, e.g. COM5")
    ap.add_argument("out", help="raw sample CSV for this run")
    ap.add_argument("--label", default="", help="settings of this run, e.g. 'jb20 d455 30fps exp100'")
    ap.add_argument("--min-ms", type=float, default=40.0, help="reject samples below this (default 40)")
    ap.add_argument("--summary", default="results_summary.csv", help="shared summary CSV (default results_summary.csv)")
    args = ap.parse_args()

    ser = serial.Serial(args.port, 115200, timeout=2)
    lat_ms, timeouts, rejects = [], 0, 0
    if args.label:
        print(f"run label: {args.label}")
    with open(args.out, "w", newline="") as f, open(args.out + ".log", "w") as logf:
        w = csv.writer(f)
        w.writerow(["idx", "latency_ms", "host_time_s", "rejected", "timeout"])
        if args.label:
            logf.write(f"{time.time():.3f} # label: {args.label}\n")
        try:
            while True:
                line = ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                if line.startswith("#"):
                    print(line)
                    logf.write(f"{time.time():.3f} {line}\n")
                    logf.flush()
                    continue
                try:
                    idx, us = line.split(",")
                    us = int(us)
                except ValueError:
                    print(f"unparsed line: {line!r}")
                    continue
                if us < 0:
                    timeouts += 1
                    w.writerow([idx, "", f"{time.time():.3f}", 0, 1])
                    f.flush()
                    print(f"{idx}: timeout")
                    continue
                ms = us / 1000.0
                rejected = ms < args.min_ms
                w.writerow([idx, f"{ms:.3f}", f"{time.time():.3f}", int(rejected), 0])
                f.flush()
                if rejected:
                    rejects += 1
                    print(f"{idx}: {ms:.1f} ms  REJECTED (< {args.min_ms:.0f} ms)")
                    continue
                lat_ms.append(ms)
                print(f"{idx}: {ms:.1f} ms  (running median {statistics.median(lat_ms):.1f})")
        except KeyboardInterrupt:
            s = summarize(lat_ms, timeouts, rejects)
            if s is not None:
                append_summary(args.summary, args.label, args.out, s, timeouts, rejects)


if __name__ == "__main__":
    main()