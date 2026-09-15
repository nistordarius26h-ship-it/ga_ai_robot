# Electrical Engineering & Single-PCB Design

## 1. PCB goal

PCB v1 is intentionally simple: it is a **low-voltage carrier/backplane PCB** for the existing ESP32 DevKit, PCA9685 module, sensors, Raspberry Pi UART and clean connectors. It does **not** carry traction current and does not add current sensing, MOSFET accessory stages, discrete buffer ICs, clamp networks, or extra motor-driver electronics.

```text
36 V battery system
  +-- external high-current harness -> 4 BLDC controllers -> 4 hub motors
  +-- external 36 V -> 5 V buck
         +-- Raspberry Pi power
         +-- custom PCB 5 V / logic supply
```

The previous melted common feeder showed why the four-controller traction current must stay in properly sized external wiring, not on this board.

## 2. Grounding

All low-voltage/control electronics need one electrical reference:

- ESP32 GND
- PCA9685 GND
- Raspberry Pi UART GND
- sensor GND
- motor-controller **signal** GND
- buck-converter output GND
- battery negative reference

The metal chassis does **not** need to be used as electrical ground. Keep the chassis floating unless there is a deliberate later reason to bond it.

High motor return current must travel through the heavy battery/controller harness, not through PCB ground traces.

## 3. Exact ESP32 pin map

| Function | ESP32 pin |
|---|---:|
| Pi UART RX | GPIO16 |
| Pi UART TX | GPIO17 |
| I2C SDA | GPIO21 |
| I2C SCL | GPIO22 |
| PCA9685 OE | GPIO23 |
| DHT11 data | GPIO4 |
| Buzzer module signal | GPIO25 |
| Water sensor signal | GPIO26 |
| Light sensor DO | GPIO13 |
| Light sensor AO | GPIO34 |
| Ultrasonic US1 TRIG | GPIO18 |
| Ultrasonic US1 ECHO | GPIO19 through divider |
| INMP441 SCK/BCLK | GPIO14 |
| INMP441 WS/LRCLK | GPIO27 |
| INMP441 SD | GPIO32 |
| ARM switch | GPIO33 |
| Battery ADC | GPIO35 |
| GPIO2 | intentionally unused on PCB v1 |

## 4. I2C bus

```text
ESP32 GPIO21 -> PCA9685 SDA
             -> MPU6050 SDA
             -> QMC5883L SDA

ESP32 GPIO22 -> PCA9685 SCL
             -> MPU6050 SCL
             -> QMC5883L SCL
```

PCA9685 module logic VCC is 3.3 V and GND is common. `OE` is connected to GPIO23 so firmware can hardware-disable PCA outputs.

The QMC5883L remains a **remote module** on a cable because hub-motor magnets, high-current battery/phase wiring, motor controllers, the buck converter, and steel parts can disturb compass readings.

## 5. Motor-controller signals

The controller's PWM input `P` is documented for approximately 2.5–5 V amplitude and 50 Hz–20 kHz. The existing PCA9685 setup runs at 1 kHz and already works with the controllers.

PCB v1 keeps the same direct interface with a small series resistor:

```text
PCA CH0 -> 100 ohm -> FL P
PCA CH1 -> 100 ohm -> FL DIR
PCA CH2 -> 100 ohm -> RL P
PCA CH3 -> 100 ohm -> RL DIR
PCA CH4 -> 100 ohm -> FR P
PCA CH5 -> 100 ohm -> FR DIR
PCA CH6 -> 100 ohm -> RR P
PCA CH7 -> 100 ohm -> RR DIR
```

Each controller also receives PCB/control GND.

Do not tie together the four controller `5V` terminals. The controller `0-5V` analog throttle input is unused because the project uses `P` PWM control.

Reserve `BRAKE` and `S` on pads/connectors for later measurement. The existing physical E-stop remains separate from this PCB.

## 6. Battery voltage divider

PCB v1 uses the simple existing divider:

```text
BAT+
 |
100k 1%
 |
 +------ GPIO35
 |
6.8k 1%
 |
PCB GND / battery-negative reference
```

At roughly 42 V maximum battery voltage, the ADC node is about 2.67 V. Firmware averages multiple samples and applies a software calibration factor against a trusted multimeter.

No current sensor is included in PCB v1.

## 7. ARM switch

```text
3.3V
 |
10k
 |
 +------ GPIO33
 |
ARM switch
 |
GND
```

Switch closed = GPIO33 LOW = ARM request. Firmware still requires fresh communication, working PCA/I2C and neutral throttle/steering before enabling outputs.

## 8. Ultrasonic sensors

US1 is the only ultrasonic sensor electrically connected to the ESP32 in PCB v1:

```text
US1 VCC  -> 5V
US1 GND  -> GND
US1 TRIG -> GPIO18

US1 ECHO -> 10k ->+-> GPIO19
                  |
                 20k
                  |
                 GND
```

Do **not** connect eight TRIG lines to GPIO18; that would fire every sensor together and cause acoustic cross-talk.

The PCB may include US2-US8 connectors for future expansion. Their 5 V and GND can be wired, while TRIG/ECHO go only to an unconnected expansion header/pads. No mux/decoder IC is required for PCB v1.

## 9. Sensor connectors

- DHT11 module: `3V3, DATA(GPIO4), GND`
- Water sensor: `3V3, SIGNAL(GPIO26), GND`
- Light module: `3V3, GND, AO(GPIO34), DO(GPIO13)`
- INMP441: `3V3, GND, SCK(GPIO14), WS(GPIO27), SD(GPIO32), L/R(GND)`
- MPU6050 module: I2C; mark `ROBOT FRONT` on the PCB/silkscreen
- QMC5883L remote cable: `VCC, GND, SDA(GPIO21), SCL(GPIO22)`
- Pi UART: `GND, PI_TX->GPIO16, PI_RX<-GPIO17, NC`
- Buzzer module: supply as required by the working module, `GND, SIGNAL(GPIO25)`

## 10. Mechanical wire retention

Do not solder thin remote-sensor wires to flat SMD copper pads with no strain relief. Preferred order:

1. **locking through-hole connector** (recommended), e.g. JST-XH for QMC, ultrasonic, DHT, etc.;
2. plated through-hole solder pads plus two strain-relief holes/slots behind the pads;
3. through-hole pads plus a nearby zip-tie anchor pair.

For direct-soldered 26–28 AWG sensor wire, a practical starting geometry is a ~1.0–1.2 mm finished plated hole with a roughly 2.4–3.0 mm pad, placed near the board edge. Add two ~2 mm mechanical holes or a slot 5–10 mm behind the electrical pads. Pass the cable through the strain-relief holes first, then solder the conductors. The mechanical pull is then taken by the cable loop/zip tie instead of the solder joints.

For the QMC5883L specifically, the preferred solution is a 4-pin locking connector labelled `3V3 / GND / SDA / SCL`, mounted near a board edge.

## 11. Expansion

Expose:

- PCA CH8–CH15 on a header/pads;
- US2–US8 TRIG/ECHO on an unconnected expansion header;
- spare 3.3 V, 5 V, GND, SDA and SCL pads/header.

Expansion is intentionally simple and does not add extra active ICs in PCB v1.
