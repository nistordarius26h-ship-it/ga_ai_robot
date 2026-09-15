#include <Arduino.h>
#include <DHT.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

#define MIC_ENABLED 0
#if MIC_ENABLED
#include <driver/i2s.h>
#endif

// --- UART & Communication Pins ---
#define rxd2 16
#define txd2 17

// --- INMP441 I2S Microphone Pins ---
#define I2S_WS   27
#define I2S_SD   32
#define I2S_SCK  14
#define I2S_PORT I2S_NUM_0

// --- Other Sensor Pins ---
// GPIO2 status LED is intentionally not used on PCB v1.
const int arm_switch_pin = 33; // external 10k pull-up to 3.3V, switch to GND
const int dhtpin = 4;         
const int buzzerpin = 25;     
const int watersensorpin = 26; 
const int voltagesensorpin = 35; 

// Light Sensor Pins
const int light_do_pin = 13;
const int light_ao_pin = 34;

// Ultrasonic Pins
const int trigpin = 18;       
const int echopin = 19;       

#define dhttype DHT11        
DHT dht(dhtpin, dhttype);    

Adafruit_PWMServoDriver pca9685 = Adafruit_PWMServoDriver(0x40);

const int PCA_OE_PIN = 23;

// PCA9685 Motor Channel Assignments
const int CH_FL_PWM = 0; const int CH_FL_DIR = 1;
const int CH_RL_PWM = 2; const int CH_RL_DIR = 3;
const int CH_FR_PWM = 4; const int CH_FR_DIR = 5;
const int CH_RR_PWM = 6; const int CH_RR_DIR = 7;

#define MPU6050_ADDR  0x68
#define QMC5883L_ADDR 0x0D
#define PCA9685_ADDR  0x40

const int SDA_PIN = 21;
const int SCL_PIN = 22;

bool mpu_ok = false;
bool qmc_ok = false;
bool pca_ok = false;
bool prev_i2c_healthy = false; 

// Timing Loops
unsigned long last_telemetry_time = 0;
const unsigned long telemetry_interval = 50; 

unsigned long last_dht_time = 0;
const unsigned long dht_interval = 2000;      

unsigned long last_ultra_time = 0;
const unsigned long ultra_interval = 60;      

unsigned long last_cmd_debug_time = 0;
const unsigned long cmd_debug_interval = 1000; 

// --- Slew-rate limiting ---
float ramped_throttle = 0.0;
float ramped_steering = 0.0;
int current_speed_limit = 100;  // 25 / 50 / 100 from the web UI
unsigned long last_ramp_time = 0;

// Throttle deliberately accelerates slowly but can decelerate quickly.
const float RAMP_RATE_ACCEL_PERCENT_PER_SEC = 60.0;
const float RAMP_RATE_DECEL_PERCENT_PER_SEC = 1000.0;

// Steering deliberately uses the SAME slew-rate function/rates as throttle.

// --- Deadzones ---
const int THROTTLE_DEADZONE = 1; 
const int STEERING_DEADZONE = 1; 

// Filtering & Sensor States
float filtered_pitch = 0.0;
float filtered_roll = 0.0;
float filtered_mx = 0.0;
float filtered_my = 0.0;
float filtered_db = 30.0;

const float alpha_imu = 0.15; 
const float alpha_mag = 0.15; 

float cached_temp = 0.0;
float cached_humid = 0.0;
float distance = 100.0;
bool brakeactive = false;
bool buzzer_on = false;
unsigned long last_buzzer_toggle = 0;

int current_throttle = 0;
int current_steering = 0;
unsigned long last_cmd_received_time = 0;
bool armed = false; // boot disarmed; neutral command is required before enabling drive
const unsigned long cmd_timeout_ms = 1000; 

// Function Declarations
#if MIC_ENABLED
void initI2S();
float readI2SDecibels();
#endif
float rampToward(float current, float target, float dt);
void setPcaMotor(int speedChannel, int dirChannel, int speedPercent);
void i2cBusRecovery();
void forceAllMotorsOff();
void driveTankSteering(int throttle, int steering);
void parsecommand(String cmd);
bool initMPU();
bool readMPUAccel(int16_t &ax, int16_t &ay, int16_t &az);
bool initQMC5883L();
bool readQMC5883L(int16_t &x, int16_t &y, int16_t &z);
void i2cScan();

void setup(void) 
{
  pinMode(arm_switch_pin, INPUT);

  pinMode(PCA_OE_PIN, OUTPUT);
  digitalWrite(PCA_OE_PIN, HIGH);
  
  pinMode(buzzerpin, OUTPUT);
  digitalWrite(buzzerpin, LOW); 
  
  pinMode(watersensorpin, INPUT);
  pinMode(voltagesensorpin, INPUT);
  pinMode(light_do_pin, INPUT);
  pinMode(light_ao_pin, INPUT);
  
  pinMode(trigpin, OUTPUT);
  pinMode(echopin, INPUT);
  
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, rxd2, txd2);
  delay(200); 

  Serial.println();
  Serial.println("=== GA AI ROBOT - ESP32 BOOT ===");
  
  Wire.begin(SDA_PIN, SCL_PIN);
  i2cScan();

  Wire.beginTransmission(PCA9685_ADDR);
  if (Wire.endTransmission() == 0) {
    pca_ok = true;
    Serial.println("[OK]   PCA9685 FOUND at 0x40");
  } else {
    pca_ok = false;
    Serial.println("[FAIL] PCA9685 NOT FOUND at 0x40 -- check SDA/SCL wiring and logic power!");
  }

  pca9685.begin();
  pca9685.setPWMFreq(1000); 

  // Keep outputs disabled until a fresh neutral command is seen.
  digitalWrite(PCA_OE_PIN, HIGH);
  prev_i2c_healthy = pca_ok;

  if (initMPU()) {
    mpu_ok = true;
    Serial.println("[OK]   MPU6050 Accel/Gyro Ready.");
  } else {
    Serial.println("[FAIL] MPU6050 not responding.");
  }
  
  if (initQMC5883L()) {
    qmc_ok = true;
    Serial.println("[OK]   QMC5883L Magnetometer Ready.");
  } else {
    Serial.println("[FAIL] QMC5883L not responding.");
  }

  dht.begin(); 
  Serial.println("--- PCA9685 4WD TANK STEERING & TELEMETRY READY ---");
}

void loop(void) 
{
  unsigned long now = millis();

  // 1. Ultrasonic Ranging
  if (now - last_ultra_time >= ultra_interval) {
    last_ultra_time = now;
    
    digitalWrite(trigpin, LOW);
    delayMicroseconds(2);
    digitalWrite(trigpin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigpin, LOW);
    
    long duration = pulseIn(echopin, HIGH, 6000); 
    distance = (duration > 0) ? (duration * 0.0343 / 2.0) : 100.0;    
    
    brakeactive = (distance > 0 && distance < 10.0);
  }

  if (brakeactive) {
    if (now - last_buzzer_toggle > 200) {
      buzzer_on = !buzzer_on;
      digitalWrite(buzzerpin, buzzer_on ? HIGH : LOW);
      last_buzzer_toggle = now;
    }
  } else {
    digitalWrite(buzzerpin, LOW);
    buzzer_on = false;
  }

  // 2. Serial Commands & Driving
  if (Serial2.available()) {
    String rxstring = Serial2.readStringUntil('\n');
    rxstring.trim();
    if (rxstring.length() > 0) {
      parsecommand(rxstring);
    }
  }

  bool cmd_is_fresh = (millis() - last_cmd_received_time <= cmd_timeout_ms);
  if (!cmd_is_fresh) {
    current_throttle = 0;
    current_steering = 0;
  }

  Wire.beginTransmission(PCA9685_ADDR);
  bool i2c_healthy = (Wire.endTransmission() == 0);
  pca_ok = i2c_healthy;

  if (i2c_healthy && !prev_i2c_healthy) {
    Serial.println("[RECOVERY] I2C restored -- forcing motors to 0.");
    i2cBusRecovery();
    pca9685.begin();
    pca9685.setPWMFreq(1000);
    forceAllMotorsOff();
    armed = false; 
  }
  prev_i2c_healthy = i2c_healthy;

  bool arm_switch_requested = (digitalRead(arm_switch_pin) == LOW);

  // Opening the physical ARM switch always disarms immediately.
  if (!arm_switch_requested) {
    if (armed) Serial.println("[ARM] DISARMED by physical switch.");
    armed = false;
    current_throttle = 0;
    current_steering = 0;
  }

  // To arm/re-arm, the switch must be ON and the controls must be neutral.
  if (arm_switch_requested && !armed) {
    if (cmd_is_fresh && i2c_healthy &&
        abs(current_throttle) < 5 && abs(current_steering) < 5) {
      armed = true;
      Serial.println("[ARM] ARMED - physical switch ON and controls neutral.");
    } else {
      current_throttle = 0;
      current_steering = 0;
    }
  }

  bool safe_to_run = cmd_is_fresh && i2c_healthy && armed && arm_switch_requested;
  digitalWrite(PCA_OE_PIN, safe_to_run ? LOW : HIGH);

  driveTankSteering(current_throttle, current_steering);

  if (now - last_cmd_debug_time >= cmd_debug_interval) {
    last_cmd_debug_time = now;
    Serial.print("[STATE] throttle="); Serial.print(current_throttle);
    Serial.print(" steering="); Serial.print(current_steering);
    Serial.print(" brake="); Serial.print(brakeactive ? "ON" : "off");
    Serial.print(" armSwitch="); Serial.print(arm_switch_requested ? "ON" : "off");
    Serial.print(" armed="); Serial.print(armed ? "yes" : "NO");
    Serial.print(" pca_ok="); Serial.println(pca_ok ? "yes" : "NO");
  }

  // 3. DHT11
  if (now - last_dht_time >= dht_interval) {
    last_dht_time = now;
    float t = dht.readTemperature();
    float h = dht.readHumidity();
    if (!isnan(t)) cached_temp = t;
    if (!isnan(h)) cached_humid = h;
  }

  // 4. Telemetry Output (20 Hz)
  if (now - last_telemetry_time >= telemetry_interval) {
    last_telemetry_time = now;

    // Average the battery ADC input. PCB v1 uses the simple 100k / 6.8k divider.
    uint32_t raw_sum = 0;
    const int BAT_SAMPLES = 16;
    for (int i = 0; i < BAT_SAMPLES; i++) {
      raw_sum += analogRead(voltagesensorpin);
    }
    float rawadc = (float)raw_sum / BAT_SAMPLES;
    float pin_volts = (rawadc / 4095.0) * 3.3;
    const float BAT_R_TOP_KOHM = 100.0;
    const float BAT_R_BOTTOM_KOHM = 6.8;
    const float BAT_ADC_CAL = 1.000; // calibrate against a trusted multimeter
    float batteryvoltage = pin_volts *
        ((BAT_R_TOP_KOHM + BAT_R_BOTTOM_KOHM) / BAT_R_BOTTOM_KOHM) *
        BAT_ADC_CAL;

    int light_analog = analogRead(light_ao_pin);
    int light_digital = digitalRead(light_do_pin);
    int watervalue = digitalRead(watersensorpin);

    float heading = 0.0;
    if (qmc_ok) {
      int16_t mx, my, mz;
      if (readQMC5883L(mx, my, mz)) {
        filtered_mx = (alpha_mag * (float)mx) + ((1.0 - alpha_mag) * filtered_mx);
        filtered_my = (alpha_mag * (float)my) + ((1.0 - alpha_mag) * filtered_my);
        heading = atan2(filtered_my, filtered_mx) * 180.0 / M_PI;
        if (heading < 0) heading += 360.0;
      }
    }

    if (mpu_ok) {
      int16_t ax, ay, az;
      if (readMPUAccel(ax, ay, az)) {
        float raw_pitch = atan2(-(float)ax, sqrt((float)ay * ay + (float)az * az)) * 180.0 / M_PI;
        float raw_roll  = atan2((float)ay, (float)az) * 180.0 / M_PI;

        filtered_pitch = (alpha_imu * raw_pitch) + ((1.0 - alpha_imu) * filtered_pitch);
        filtered_roll  = (alpha_imu * raw_roll)  + ((1.0 - alpha_imu) * filtered_roll);
      }
    }

    Serial2.print("TELEMETRY:");
    Serial2.print(batteryvoltage); Serial2.print(",");
    Serial2.print(filtered_db); Serial2.print(",");
    Serial2.print(cached_temp); Serial2.print(",");
    Serial2.print(cached_humid); Serial2.print(",");
    Serial2.print(distance); Serial2.print(",");
    Serial2.print(watervalue == HIGH ? "1" : "0"); Serial2.print(",");
    Serial2.print(light_analog); Serial2.print(",");
    Serial2.print(light_digital); Serial2.print(",");
    Serial2.print(heading); Serial2.print(",");
    Serial2.print(filtered_pitch); Serial2.print(",");
    Serial2.println(filtered_roll);
  }
}

void i2cBusRecovery() {
  pinMode(SCL_PIN, OUTPUT);
  pinMode(SDA_PIN, INPUT_PULLUP);

  for (int i = 0; i < 16; i++) {
    digitalWrite(SCL_PIN, LOW);
    delayMicroseconds(5);
    digitalWrite(SCL_PIN, HIGH);
    delayMicroseconds(5);
    if (digitalRead(SDA_PIN) == HIGH) break;
  }

  pinMode(SDA_PIN, OUTPUT);
  digitalWrite(SDA_PIN, LOW);
  delayMicroseconds(5);
  digitalWrite(SCL_PIN, HIGH);
  delayMicroseconds(5);
  digitalWrite(SDA_PIN, HIGH);
  delayMicroseconds(5);

  Wire.begin(SDA_PIN, SCL_PIN);
}

void forceAllMotorsOff() {
  for (int ch = 0; ch < 16; ch++) {
    pca9685.setPWM(ch, 0, 0);
  }
  current_throttle = 0;
  current_steering = 0;
  ramped_throttle = 0;
  ramped_steering = 0;
}

float rampToward(float current, float target, float dt) {
  bool accelerating = (fabs(target) > fabs(current)) && ((target >= 0) == (current >= 0) || current == 0);
  float rate = accelerating ? RAMP_RATE_ACCEL_PERCENT_PER_SEC : RAMP_RATE_DECEL_PERCENT_PER_SEC;
  float max_step = rate * dt;

  if (target > current) return min(target, current + max_step);
  else return max(target, current - max_step);
}


void setPcaMotor(int speedChannel, int dirChannel, int speedPercent) {
  speedPercent = constrain(speedPercent, -100, 100);

  if (abs(speedPercent) < 3) {
    // True 0% on the controller's P input.
    pca9685.setPWM(speedChannel, 0, 4096);
    return;
  }

  // Preserve the direction polarity used by the existing wiring:
  // positive speed -> DIR LOW, negative speed -> DIR HIGH.
  if (speedPercent > 0) {
    pca9685.setPWM(dirChannel, 0, 4096); // full OFF = logic LOW
  } else {
    pca9685.setPWM(dirChannel, 4096, 0); // full ON = logic HIGH
  }

  int pwmValue = map(abs(speedPercent), 1, 100, 200, 4095);
  pca9685.setPWM(speedChannel, 0, pwmValue);
}

void driveTankSteering(int throttle, int steering) {
  if (brakeactive && throttle > 0) {
    throttle = 0;
  }

  if (abs(throttle) < THROTTLE_DEADZONE) throttle = 0;
  if (abs(steering) < STEERING_DEADZONE) steering = 0;

  unsigned long now = millis();
  float dt = (now - last_ramp_time) / 1000.0;
  last_ramp_time = now;
  if (dt <= 0 || dt > 0.5) dt = 0.02;

  ramped_throttle = rampToward(ramped_throttle, (float)throttle, dt);
  ramped_steering = rampToward(ramped_steering, (float)steering, dt);

  int base_throttle = (int)roundf(ramped_throttle);
  int base_steering = (int)roundf(ramped_steering);

  int leftSpeed = 0;
  int rightSpeed = 0;

  if (base_throttle == 0) {
    // Zero throttle -> turn in place, with steering ramp applied.
    int mode_limit = constrain(current_speed_limit, 1, 100);
    leftSpeed  = constrain(base_steering, -mode_limit, mode_limit);
    rightSpeed = constrain(-base_steering, -mode_limit, mode_limit);
  } else {
    // Moving -> mode-aware differential steering.
    // LOW sends +/-25, MED sends +/-50, HIGH sends +/-100.
    // The selected mode limit is sent separately by the Pi, therefore
    // steering=25 is full lock in LOW, 50 is full lock in MED, etc.
    int mode_limit = constrain(current_speed_limit, 1, 100);
    float steer_ratio = (float)abs(base_steering) / (float)mode_limit;
    steer_ratio = constrain(steer_ratio, 0.0f, 1.0f);

    // Keep every wheel inside the selected speed ceiling. At full lock:
    // LOW  -> outer=25, inner=0
    // MED  -> outer=50, inner=0
    // HIGH -> outer=100, inner=0
    int throttle_mag = min(abs(base_throttle), mode_limit);
    int outer_speed = (int)roundf(throttle_mag + (mode_limit - throttle_mag) * steer_ratio);
    int inner_speed = (int)roundf(throttle_mag * (1.0f - steer_ratio));

    if (base_throttle > 0) {
      // Forward motion
      if (base_steering >= 0) {
        // Turning Right: Left outer, Right inner
        leftSpeed  = outer_speed;
        rightSpeed = inner_speed;
      } else {
        // Turning Left: Left inner, Right outer
        leftSpeed  = inner_speed;
        rightSpeed = outer_speed;
      }
    } else {
      // Reverse motion
      if (base_steering >= 0) {
        // Turning Right in reverse: Left outer, Right inner
        leftSpeed  = -outer_speed;
        rightSpeed = -inner_speed;
      } else {
        // Turning Left in reverse: Left inner, Right outer
        leftSpeed  = -inner_speed;
        rightSpeed = -outer_speed;
      }
    }
  }

  setPcaMotor(CH_FL_PWM, CH_FL_DIR, -leftSpeed);
  setPcaMotor(CH_RL_PWM, CH_RL_DIR, -leftSpeed);
  setPcaMotor(CH_FR_PWM, CH_FR_DIR, rightSpeed);
  setPcaMotor(CH_RR_PWM, CH_RR_DIR, rightSpeed);

  // --- DEBUG: show exactly what the steering math actually computed ---
  static unsigned long last_steer_debug = 0;
  unsigned long dbg_now = millis();
  if (dbg_now - last_steer_debug >= 300) {
    last_steer_debug = dbg_now;
    Serial.print("[STEER] in: throttle="); Serial.print(throttle);
    Serial.print(" steering="); Serial.print(steering);
    Serial.print(" modeLimit="); Serial.print(current_speed_limit);
    Serial.print(" | rampedThrottle="); Serial.print(base_throttle);
    Serial.print(" rampedSteering="); Serial.print(base_steering);
    Serial.print(" | computed leftSpeed="); Serial.print(leftSpeed);
    Serial.print(" rightSpeed="); Serial.println(rightSpeed);
  }
}

bool initMPU() {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x6B); Wire.write(0x00); 
  return (Wire.endTransmission() == 0);
}

bool readMPUAccel(int16_t &ax, int16_t &ay, int16_t &az) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x3B); 
  if (Wire.endTransmission() != 0) return false;

  Wire.requestFrom(MPU6050_ADDR, 6);
  if (Wire.available() == 6) {
    ax = (int16_t)((Wire.read() << 8) | Wire.read());
    ay = (int16_t)((Wire.read() << 8) | Wire.read());
    az = (int16_t)((Wire.read() << 8) | Wire.read());
    return true;
  }
  return false;
}

bool initQMC5883L() {
  Wire.beginTransmission(QMC5883L_ADDR);
  Wire.write(0x0B); Wire.write(0x01);
  if (Wire.endTransmission() != 0) return false;

  Wire.beginTransmission(QMC5883L_ADDR);
  Wire.write(0x09); Wire.write(0x1D);
  return (Wire.endTransmission() == 0);
}

bool readQMC5883L(int16_t &x, int16_t &y, int16_t &z) {
  Wire.beginTransmission(QMC5883L_ADDR);
  Wire.write(0x00);
  if (Wire.endTransmission() != 0) return false;

  Wire.requestFrom(QMC5883L_ADDR, 6);
  if (Wire.available() == 6) {
    x = (int16_t)(Wire.read() | (Wire.read() << 8));
    y = (int16_t)(Wire.read() | (Wire.read() << 8));
    z = (int16_t)(Wire.read() | (Wire.read() << 8));
    return true;
  }
  return false;
}

void i2cScan() {
  Serial.println("--- I2C Scan ---");
  int found = 0;
  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("  Device found at 0x");
      if (addr < 16) Serial.print("0");
      Serial.println(addr, HEX);
      found++;
    }
  }
  if (found == 0) {
    Serial.println("  No I2C devices found at all -- check Wire.begin(21,22) wiring / power.");
  }
  Serial.println("----------------");
}

void parsecommand(String cmd) 
{
  if (!cmd.startsWith("CMD:")) return;

  int comma1 = cmd.indexOf(',');
  if (comma1 <= 0) return;
  int comma2 = cmd.indexOf(',', comma1 + 1);

  int parsed_throttle = cmd.substring(4, comma1).toInt();
  int parsed_steering;
  int parsed_limit = 100; // backwards-compatible default

  if (comma2 > comma1) {
    parsed_steering = cmd.substring(comma1 + 1, comma2).toInt();
    parsed_limit = cmd.substring(comma2 + 1).toInt();
  } else {
    parsed_steering = cmd.substring(comma1 + 1).toInt();
  }

  if (parsed_throttle < -100 || parsed_throttle > 100 ||
      parsed_steering < -100 || parsed_steering > 100 ||
      (parsed_limit != 25 && parsed_limit != 50 && parsed_limit != 100)) {
    return;
  }

  parsed_throttle = constrain(parsed_throttle, -parsed_limit, parsed_limit);
  parsed_steering = constrain(parsed_steering, -parsed_limit, parsed_limit);

  current_throttle = parsed_throttle;
  current_steering = parsed_steering;
  current_speed_limit = parsed_limit;
  last_cmd_received_time = millis();
}

