#include <Arduino.h>
#include <DHT.h>
#include <Wire.h>

#define rxd2 16
#define txd2 17

const int micpin = 32;        
const int ledpin = 2;         
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

const int beeptone = 1500;     

#define dhttype DHT11        
DHT dht(dhtpin, dhttype);    

#define MPU6050_ADDR  0x68
#define QMC5883L_ADDR 0x0D

bool mpu_ok = false;
bool qmc_ok = false;

unsigned long lastread = 0;
const unsigned long interval = 1000;

const int samplewin = 25; 
float decibels = 0.0;
bool wateralarm = false;
bool brakeactive = false; 
float distance = 0.0;

int current_throttle = 0;
int current_steering = 0;

void parsecommand(String cmd);
bool initMPU();
bool readMPUAccel(int16_t &ax, int16_t &ay, int16_t &az);
bool initQMC5883L();
bool readQMC5883L(int16_t &x, int16_t &y, int16_t &z);

void setup(void) 
{
  pinMode(ledpin, OUTPUT);
  digitalWrite(ledpin, LOW);
  
  pinMode(watersensorpin, INPUT);
  pinMode(voltagesensorpin, INPUT);
  pinMode(light_do_pin, INPUT);
  pinMode(light_ao_pin, INPUT);
  
  pinMode(trigpin, OUTPUT);
  pinMode(echopin, INPUT);
  
  // Attach buzzer PWM and explicitly silence it (duty = 0)
  ledcAttach(buzzerpin, beeptone, 8); 
  ledcWrite(buzzerpin, 0); 
  
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, rxd2, txd2);
  
  // Initialize I2C Bus (SDA: GPIO 21, SCL: GPIO 22)
  Wire.begin(21, 22);
  
  // Native Raw I2C Init for MPU (0x68) and QMC (0x0D)
  if (initMPU()) {
    mpu_ok = true;
    Serial.println("MPU-9250 Accel/Gyro Initialized.");
  } else {
    Serial.println("MPU-9250 Init Failed!");
  }
  
  if (initQMC5883L()) {
    qmc_ok = true;
    Serial.println("QMC5883L Magnetometer Initialized.");
  } else {
    Serial.println("QMC5883L Init Failed!");
  }

  dht.begin(); 
  Serial.println("--- ROBOT LIVE: ESP32 READY ---");
}

void loop(void) 
{
  // Ultrasonic Ranging
  digitalWrite(trigpin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigpin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigpin, LOW);
  
  long duration = pulseIn(echopin, HIGH, 30000); 
  distance = duration * 0.0343 / 2.0;    
  
  if (distance > 0 && distance < 10.0) {
    brakeactive = true; 
  } else if (brakeactive && distance >= 10.0) {
    brakeactive = false;
  }

  // Serial Command Input
  if (Serial2.available()) {
    String rxstring = Serial2.readStringUntil('\n');
    rxstring.trim();
    if (rxstring.length() > 0) {
      parsecommand(rxstring);
    }
  }

  // Water Sensor Check
  int watervalue = digitalRead(watersensorpin);
  wateralarm = (watervalue == HIGH);

  // Sound Sampling
  unsigned long startmillis = millis(); 
  unsigned int signalmax = 0;
  unsigned int signalmin = 4095;

  while (millis() - startmillis < samplewin) {
    unsigned int sample = analogRead(micpin);
    if (sample > signalmax) signalmax = sample;
    if (sample < signalmin) signalmin = sample;
  }
  unsigned int peaktopeak = signalmax - signalmin;
  float peakvolts = (peaktopeak * 3.3) / 4095.0;
  decibels = (peakvolts > 0.001) ? (20.0 * log10(peakvolts / 0.003) + 40.0) : 30.0;

  // Telemetry Transmission Loop
  if (millis() - lastread >= interval) {
    lastread = millis();
    
    float temperature = dht.readTemperature(); 
    float humidity = dht.readHumidity();        
    int rawadc = analogRead(voltagesensorpin);
    float batteryvoltage = (rawadc / 4095.0) * 3.3 * 5.0;

    int light_analog = analogRead(light_ao_pin);
    int light_digital = digitalRead(light_do_pin);

    // Compass Heading (QMC5883L)
    float heading = 0.0;
    if (qmc_ok) {
      int16_t mx, my, mz;
      if (readQMC5883L(mx, my, mz)) {
        heading = atan2((float)my, (float)mx) * 180.0 / M_PI;
        if (heading < 0) heading += 360.0;
      }
    }

    // Pitch & Roll (Direct Raw I2C Read from MPU @ 0x68)
    float pitch = 0.0;
    float roll = 0.0;
    if (mpu_ok) {
      int16_t ax, ay, az;
      if (readMPUAccel(ax, ay, az)) {
        pitch = atan2(-(float)ax, sqrt((float)ay * ay + (float)az * az)) * 180.0 / M_PI;
        roll  = atan2((float)ay, (float)az) * 180.0 / M_PI;
      }
    }

    // TELEMETRY: batt,mic,temp,humid,dist,water,light_adc,light_dig,heading,pitch,roll
    Serial2.print("TELEMETRY:");
    Serial2.print(batteryvoltage); Serial2.print(",");
    Serial2.print(decibels); Serial2.print(",");
    Serial2.print(temperature); Serial2.print(",");
    Serial2.print(humidity); Serial2.print(",");
    Serial2.print(distance); Serial2.print(",");
    Serial2.print(watervalue == HIGH ? "1" : "0"); Serial2.print(",");
    Serial2.print(light_analog); Serial2.print(",");
    Serial2.print(light_digital); Serial2.print(",");
    Serial2.print(heading); Serial2.print(",");
    Serial2.print(pitch); Serial2.print(",");
    Serial2.println(roll);
  }
}

// Direct MPU Raw Driver
bool initMPU() {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x6B); // Power Management 1 Register
  Wire.write(0x00); // Wake up MPU
  return (Wire.endTransmission() == 0);
}

bool readMPUAccel(int16_t &ax, int16_t &ay, int16_t &az) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x3B); // ACCEL_XOUT_H
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

// Direct QMC5883L Driver
bool initQMC5883L() {
  Wire.beginTransmission(QMC5883L_ADDR);
  Wire.write(0x0B); 
  Wire.write(0x01);
  if (Wire.endTransmission() != 0) return false;

  Wire.beginTransmission(QMC5883L_ADDR);
  Wire.write(0x09); 
  Wire.write(0x1D);
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

void parsecommand(String cmd) 
{
  if (cmd.startsWith("CMD:")) {
    int commaindex = cmd.indexOf(',');
    if (commaindex > 0) {
      current_throttle = cmd.substring(4, commaindex).toInt();
      current_steering = cmd.substring(commaindex + 1).toInt();
    }
  }
}
