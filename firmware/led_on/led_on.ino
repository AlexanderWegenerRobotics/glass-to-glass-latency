// Keeps the LED on and prints the sensor value, for positioning the sensor on the lens.

const uint8_t LED_PIN = 7;
const uint8_t SENSOR_PIN = A0;

void setup() {
  analogReference(INTERNAL);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  Serial.begin(115200);
}

void loop() {
  int peak = 0;
  uint32_t t0 = millis();
  while (millis() - t0 < 100) {
    peak = max(peak, analogRead(SENSOR_PIN));
  }
  Serial.println(peak);
}
