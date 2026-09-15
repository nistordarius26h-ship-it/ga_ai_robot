# ESP32 Firmware

## Role

The ESP32 remains the real-time control and safety layer. It receives motion commands from the Pi over UART, controls the PCA9685, reads sensors, sends telemetry and locally stops/blocks motion when required.

## Current control protocol

The Raspberry Pi sends:

```text
CMD:<throttle>,<steering>,<speed_limit>\n
```

where `speed_limit` is `25`, `50` or `100`.

LOW/MED/HIGH intentionally scale **both throttle and steering**. Firmware normalizes steering against the active mode limit, so full steering still means full steering within the selected speed mode:

```text
LOW  full lock: outer=25,  inner=0
MED  full lock: outer=50,  inner=0
HIGH full lock: outer=100, inner=0
```

The two-field legacy `CMD:<throttle>,<steering>` form is still accepted with a default limit of 100.

## Ramping

Throttle and steering use the **same slew-rate function and the same rates**. The current tuning is:

- increasing magnitude: 60 %/s;
- reducing magnitude / returning toward zero: 1000 %/s.

This means steering no longer jumps instantly, and it follows the same ramp behavior requested for throttle.

## Physical ARM switch

GPIO33 is connected to a 10 kΩ pull-up to 3.3 V and a switch to GND.

- switch open: disarmed;
- switch closed: ARM requested.

The firmware only arms when:

- ARM switch is closed;
- command heartbeat is fresh;
- PCA/I2C communication is healthy;
- throttle and steering are near neutral.

Opening the ARM switch immediately zeros commands and disables PCA outputs through OE.

## Safety behavior

- PCA OE on GPIO23 defaults disabled during startup;
- >1 s without commands zeros throttle and steering;
- Pi sends a 100 ms heartbeat;
- browser disconnect is zeroed by the Pi application;
- I2C/PCA recovery forces motors off and requires re-arm;
- ultrasonic obstacle detection blocks forward motion below the configured threshold;
- reverse remains available to back away from an obstacle.

## Sensor pins

| Device | ESP32 |
|---|---|
| Pi UART | RX16 / TX17 |
| PCA/MPU/QMC I2C | SDA21 / SCL22 |
| PCA OE | GPIO23 |
| ARM | GPIO33 |
| DHT11 | GPIO4 |
| buzzer | GPIO25 |
| water | GPIO26 |
| battery ADC | GPIO35 |
| light DO/AO | GPIO13 / GPIO34 |
| US1 TRIG/ECHO | GPIO18 / GPIO19 |
| INMP441 | WS27 / SD32 / BCLK14 |

GPIO2 is intentionally unused on PCB v1.

## Battery measurement

Firmware averages 16 ADC samples and uses the existing 100 kΩ / 6.8 kΩ divider ratio plus a calibration constant. Calibrate the final assembled board against a trusted multimeter.
