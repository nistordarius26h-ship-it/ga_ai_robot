#include <Arduino.h>
#include <DHT.h>

#define rxd2 16
#define txd2 17

const int micpin = 32;       
const int ledpin = 2;            
const int dhtpin = 4;            
const int buzzerpin = 25;        
const int watersensorpin = 26;    
const int voltagesensorpin = 35;  

const int trigpin = 18;          
const int echopin = 19;          

const int pinena = 14;           
const int pinin1 = 12;           
const int pinin2 = 13;           
const int pinin3 = 22;           
const int pinin4 = 23;           
const int pinenb = 27;           

const int channelena = 0;
const int channelenb = 1;
const int pwmfrq = 1000;
const int pwmres = 8;

const int beeptone = 1500;      

#define dhttype DHT11       
DHT dht(dhtpin, dhttype);   

unsigned long lastread = 0;
const unsigned long interval = 1000;

const int threshold = 200;   
const int samplewin = 25; 
bool ledstate = false;
bool sounddet = false; 
float decibels = 0.0;

const float maxtemp = 50.0;         
const float mintemp = 4.0;          
const float maxhum = 60.0;    

bool wateralarm = false;
bool brakeactive = false; 
float distance = 0.0;

float lefttrim = 0.82; 
float righttrim = 1.00; 

const int minpwm = 60; 

void moveforward(int pwm);
void movebackward(int pwm);
void turnleft(int pwm);
void turnright(int pwm);
void stopmotors(void);
void drivevector(int angle, int speed);
void parsecommand(String cmd);
int scalepwm(int basepwm, float trim);

void setup(void) 
{
  pinMode(ledpin, OUTPUT);
  digitalWrite(ledpin, ledstate);
  
  pinMode(watersensorpin, INPUT);
  pinMode(voltagesensorpin, INPUT);
  
  pinMode(trigpin, OUTPUT);
  pinMode(echopin, INPUT);
  
  pinMode(pinin1, OUTPUT);
  pinMode(pinin2, OUTPUT);
  pinMode(pinin3, OUTPUT);
  pinMode(pinin4, OUTPUT);
  
  ledcAttachChannel(pinena, pwmfrq, pwmres, channelena);
  ledcAttachChannel(pinenb, pwmfrq, pwmres, channelenb);

  ledcAttach(buzzerpin, beeptone, 8); 
  
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, rxd2, txd2);
  
  dht.begin(); 
  Serial.println("--- ROBOT LIVE: ESP32 READY ---");
}

void loop(void) 
{
  digitalWrite(trigpin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigpin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigpin, LOW);
  
  long duration = pulseIn(echopin, HIGH, 30000); 
  distance = duration * 0.0343 / 2.0;    
  
  if (distance > 0 && distance < 10.0) {
    if (!brakeactive) {
      stopmotors();
      brakeactive = true; 
    }
  } else {
    if (brakeactive && distance >= 10.0) {
      brakeactive = false;
    }
  }

  if (Serial2.available() && !brakeactive) {
    String rxstring = Serial2.readStringUntil('\n');
    rxstring.trim();
    if (rxstring.length() > 0) {
      parsecommand(rxstring);
    }
  }

  int watervalue = digitalRead(watersensorpin);
  if (watervalue == HIGH && !wateralarm) { 
    stopmotors(); 
    wateralarm = true;     
  } else if (watervalue == LOW) {
    wateralarm = false;
  }

  unsigned long startmillis = millis(); 
  unsigned int signalmax = 0;
  unsigned int signalmin = 4095;

  while (millis() - startmillis < samplewin) {
    unsigned int sample = analogRead(micpin);
    if (sample > signalmax) {
      signalmax = sample;
    }
    if (sample < signalmin) {
      signalmin = sample;
    }
  }
  unsigned int peaktopeak = signalmax - signalmin;
  float peakvolts = (peaktopeak * 3.3) / 4095.0;
  decibels = (peakvolts > 0.001) ? (20.0 * log10(peakvolts / 0.003) + 40.0) : 30.0;

  if (millis() - lastread >= interval) {
    lastread = millis();
    
    float temperature = dht.readTemperature(); 
    float humidity = dht.readHumidity();        
    int rawadc = analogRead(voltagesensorpin);
    float batteryvoltage = (rawadc / 4095.0) * 3.3 * 5.0;

    Serial2.print("TELEMETRY:");
    Serial2.print(batteryvoltage); Serial2.print(",");
    Serial2.print(decibels); Serial2.print(",");
    Serial2.print(temperature); Serial2.print(",");
    Serial2.print(humidity); Serial2.print(",");
    Serial2.print(distance); Serial2.print(",");
    Serial2.println(watervalue == HIGH ? "1" : "0");
  }
}

void parsecommand(String cmd) 
{
  if (cmd.startsWith("CMD:")) {
    int commaindex = cmd.indexOf(',');
    if (commaindex > 0) {
      int angle = cmd.substring(4, commaindex).toInt();
      int speed = cmd.substring(commaindex + 1).toInt();
      drivevector(angle, speed);
    }
  }
}

void drivevector(int angle, int speed) 
{
  if (speed == 0) {
    stopmotors();
    return;
  }

  int pwmspeed = map(speed, 0, 100, 0, 255);

  if (angle >= 45 && angle <= 135) {
    moveforward(pwmspeed);
  } else if (angle >= 225 && angle <= 315) {
    movebackward(pwmspeed);
  } else if (angle > 135 && angle < 225) {
    turnleft(pwmspeed);
  } else {
    turnright(pwmspeed);
  }
}

int scalepwm(int basepwm, float trim) 
{
  if (basepwm == 0) {
    return 0;
  }
  int calculated = (int)(basepwm * trim);
  
  calculated = max(calculated, minpwm);
  return min(calculated, 255);
}

void moveforward(int pwm) 
{
  int leftpwm = scalepwm(pwm, lefttrim);
  int rightpwm = scalepwm(pwm, righttrim);
  ledcWrite(pinena, leftpwm);
  ledcWrite(pinenb, rightpwm);
  digitalWrite(pinin1, HIGH); digitalWrite(pinin2, LOW);
  digitalWrite(pinin3, HIGH); digitalWrite(pinin4, LOW);
}

void movebackward(int pwm) 
{
  int leftpwm = scalepwm(pwm, lefttrim);
  int rightpwm = scalepwm(pwm, righttrim);
  ledcWrite(pinena, leftpwm);
  ledcWrite(pinenb, rightpwm);
  digitalWrite(pinin1, LOW); digitalWrite(pinin2, HIGH);
  digitalWrite(pinin3, LOW); digitalWrite(pinin4, HIGH);
}

void turnleft(int pwm) 
{
  int leftpwm = scalepwm(pwm, lefttrim);
  int rightpwm = scalepwm(pwm, righttrim);
  ledcWrite(pinena, leftpwm);
  ledcWrite(pinenb, rightpwm);
  digitalWrite(pinin1, LOW); digitalWrite(pinin2, HIGH);
  digitalWrite(pinin3, HIGH); digitalWrite(pinin4, LOW);
}

void turnright(int pwm) 
{
  int leftpwm = scalepwm(pwm, lefttrim);
  int rightpwm = scalepwm(pwm, righttrim);
  ledcWrite(pinena, leftpwm);
  ledcWrite(pinenb, rightpwm);
  digitalWrite(pinin1, HIGH); digitalWrite(pinin2, LOW);
  digitalWrite(pinin3, LOW); digitalWrite(pinin4, HIGH);
}

void stopmotors(void) 
{
  digitalWrite(pinin1, LOW); digitalWrite(pinin2, LOW);
  digitalWrite(pinin3, LOW); digitalWrite(pinin4, LOW);
  ledcWrite(pinena, 0);
  ledcWrite(pinenb, 0);
}
