# glass-to-glass-latency

A small hardware rig to measure the local glass-to-glass latency of the teleop video path: from light entering the RealSense lens to light leaving the Vive headset display. Built for the [teleop-avatar](https://github.com/AlexanderWegenerRobotics/teleop-avatar) streaming pipeline, but it treats the system as a black box, so it works for any camera → display chain.

![Rig setup](docs/setup.jpg)

---

## How it works

An Arduino turns on an LED in front of the camera (t0). The frame goes through the normal pipeline: capture, encode, RTP, decode, Unreal, headset. A light sensor taped on the headset lens sees the display get brighter (t1). The Arduino measures t1 − t0 with its own clock, so there's no clock sync involved and the USB/serial link to the PC doesn't add to the number, it only carries the result afterwards.

![Concept](docs/concept.png)

One sample per 0.4–0.8 s (random gap so the LED doesn't phase-lock to the camera frame clock). A run of ~500 samples takes about 8 minutes.

---

## Hardware

| Part | Notes |
|---|---|
| Arduino Uno | any 5 V board with an analog pin works |
| TEMT6000 light sensor | taped flat on one headset lens, facing the display |
| Green 5 mm LED + 220 Ω | green because both the sensor and the camera are most sensitive to it |
| Jumper wires, black tape | tape also goes over the headset proximity sensor so the display stays on |

![Wiring](docs/wiring.png)

| Arduino | Goes to |
|---|---|
| 5V | TEMT6000 V |
| GND | TEMT6000 G |
| A0 | TEMT6000 S |
| D7 | 220 Ω → LED long leg |
| GND | LED short leg |

<img src="docs/sensor_on_lens.jpg" width="320" alt="Sensor taped on the headset lens">

---

## Running

1. Flash `firmware/photon_latency/photon_latency.ino` with the Arduino IDE (board: Arduino Uno). Once is enough, it stays on the board.
2. Start the streamer and Unreal so the camera feed is showing in the headset. This has to run **before** the logger, because opening the serial port resets the Uno and it calibrates right away.
3. Put the LED a few cm in front of the RealSense RGB lens so it fills a big part of the frame (blurry is fine). Tape the sensor on the lens where the LED blob shows up.
4. Log a run:

```bash
pip install -r requirements.txt
python tools/log_latency.py COM3 runs/<run_name>/samples.csv --label "d455 30fps exp100 jb0" --summary runs/results_summary.csv
```

Ctrl-C stops the run and prints n, median, p5, p95 and timeouts. The summary is also appended to `runs/results_summary.csv`, so runs with different settings end up in one table.

5. Plot it:

```bash
python tools/make_plots.py runs/<run_name>/samples.csv --out runs/<run_name>/plots
```

This writes a histogram, CDF and per-sample timeline, each as PNG and PDF (PDF for Keynote).

### Output per run

| File | Content |
|---|---|
| `samples.csv` | `idx, latency_ms, host_time_s, rejected, timeout` per sample |
| `samples.csv.log` | calibration values and Arduino messages with host time |
| `notes.md` | camera, fps, exposure, encoder, jitter buffer, teleop commit. Write this, numbers without settings are useless later |

---

## Things that matter

- **Fixed camera exposure.** With auto-exposure the camera normalizes LED off vs on and calibration fails (or the sketch reports "lit darker than dark"). It also adds a variable term to the latency. Set exposure and gain in the streamer and note them per run.
- **Calibration.** At start the sketch measures the display brightness with the LED off and on and sets the threshold halfway. It needs at least 15 ADC counts difference. The sketch uses the 1.1 V ADC reference because the headset display is dim at the lens.
- **Expect ~11 ms steps.** Results cluster in bands because the display only updates once per 90 Hz refresh. That's normal, the random gap makes the median correct anyway.
- **Timeouts are data.** A timeout means the display didn't change within 1 s (stream froze or dropped frames). Report the timeout rate next to the median.
- **Samples < 40 ms are rejected** as false triggers (stray light), nothing in the pipeline can be that fast.

---

## Results so far

| Run | Setup | N | Median | p5–p95 | Timeouts |
|---|---|---|---|---|---|
| `2026-09-25_run01_d455_30fps` | D455, 1280×722 @ 30 fps, auto-exposure, NVENC, localhost | 586 | 183 ms | 153–209 ms | 4.9 % |
| `2026-09-25_run02_d435_30fps_jb50` | D435, 30 fps, jitter buffer 50 ms | 446 | 202 ms | 163–421 ms | 9.3 % |

Both runs still had auto-exposure on, so treat them as a first look. Expected for this pipeline (GPU encode/decode, UE at 60 fps) is roughly 100–165 ms, so there is still an extra queue somewhere.

---

## Layout

```
firmware/photon_latency/   Arduino sketch
tools/                     log_latency.py (serial logger), make_plots.py (plots)
runs/                      one folder per run: samples, log, notes
docs/                      images used in this README
```

## License

Apache License 2.0, see [LICENSE](LICENSE).
