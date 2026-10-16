// Photon-to-photon latency: LED in front of the RealSense -> TEMT6000 on the headset lens.
// Output over serial (115200): "idx,latency_us" per sample, -1 on timeout. Lines starting with '#' are info.

const uint8_t LED_PIN = 7;
const uint8_t SENSOR_PIN = A0;

const uint32_t SETTLE_MS = 600;
const uint32_t CAL_WINDOW_MS = 1500;
const uint8_t CAL_CYCLES = 3;
const int MIN_CONTRAST = 15;
const uint32_t DARK_CHECK_MS = 15;
const uint32_t TIMEOUT_US = 1000000UL;
const uint32_t GAP_MIN_MS = 400;
const uint32_t GAP_MAX_MS = 800;

int threshold = 0;
uint32_t sampleIdx = 0;

int peakOver(uint32_t ms) {
  int peak = 0;
  uint32_t t0 = millis();
  while (millis() - t0 < ms) {
    int v = analogRead(SENSOR_PIN);
    if (v > peak) peak = v;
  }
  return peak;
}

bool calibrate() {
  int offMax = 0;
  int onMin = 1023;
  for (uint8_t i = 0; i < CAL_CYCLES; i++) {
    digitalWrite(LED_PIN, LOW);
    delay(SETTLE_MS);
    offMax = max(offMax, peakOver(CAL_WINDOW_MS));
    digitalWrite(LED_PIN, HIGH);
    delay(SETTLE_MS);
    onMin = min(onMin, peakOver(CAL_WINDOW_MS));
  }
  digitalWrite(LED_PIN, LOW);
  delay(SETTLE_MS);

  threshold = offMax + (onMin - offMax) / 2;
  Serial.print("# cal dark_peak=");
  Serial.print(offMax);
  Serial.print(" lit_peak=");
  Serial.print(onMin);
  Serial.print(" threshold=");
  Serial.println(threshold);

  if (onMin < offMax) {
    Serial.println("# ERROR lit darker than dark: camera auto-exposure is probably on (set fixed exposure)");
    return false;
  }
  if (onMin - offMax < MIN_CONTRAST) {
    Serial.println("# ERROR low contrast: check sensor position, LED in view, pipeline running");
    return false;
  }
  return true;
}

void setup() {
  analogReference(INTERNAL);
  analogRead(SENSOR_PIN);
  delay(10);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Serial.begin(115200);
  randomSeed(analogRead(A1));
  delay(500);
  Serial.println("# photon_latency start, calibrating");
  while (!calibrate()) {
    delay(5000);
    Serial.println("# retrying calibration");
  }
  Serial.println("# measuring");
}

void loop() {
  delay(random(GAP_MIN_MS, GAP_MAX_MS + 1));

  if (peakOver(DARK_CHECK_MS) > threshold) {
    Serial.println("# skip: sensor not dark");
    return;
  }

  digitalWrite(LED_PIN, HIGH);
  uint32_t t0 = micros();
  uint32_t dt = 0;
  bool hit = false;
  while ((dt = micros() - t0) < TIMEOUT_US) {
    if (analogRead(SENSOR_PIN) > threshold) {
      hit = true;
      break;
    }
  }
  digitalWrite(LED_PIN, LOW);

  sampleIdx++;
  Serial.print(sampleIdx);
  Serial.print(',');
  Serial.println(hit ? (long)dt : -1L);
}
