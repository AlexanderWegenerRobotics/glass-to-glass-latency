# run01, 2026-09-25

Baseline before any changes, ~17:50 Boston time, 8.6 min.

- Camera: RealSense D455, serial 151422255086, firmware 5.14.0
- Stream: 1280x722 RGB @ 30 fps, auto-exposure on
- Encoder: nvh264enc, preset low-latency-hq, CBR 4000 kbps, GOP 30
- RTP: rtph264pay config-interval=1, ULP FEC 10 %, udpsink 127.0.0.1:5004
- Sender queue: 2 buffers, leaky downstream
- Receiver: UE side, jitter buffer / sink sync / decoder not recorded
- Display: Vive Pro Eye 90 Hz, TEMT6000 on lens, 1.1 V ADC reference
- Rig: LED a few cm in front of the RGB lens, dark background, daylight room

Result: 617 attempts, 587 valid, 30 timeouts (4.9 %, in 4 bursts). Median 183 ms, p5-p95 153-209 ms.
4 false triggers below 140 ms. Logged with the old logger, so timeouts are only visible as gaps in idx.
