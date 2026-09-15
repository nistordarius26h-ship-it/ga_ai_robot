# Custom PCB v1 — Simple Carrier / Sensor Backplane

## Design choice

PCB v1 keeps the robot's existing working modules and replaces loose point-to-point wiring with one robust carrier PCB. It does not attempt to integrate every function as bare ICs.

### Installed/removable modules

- ESP32 DevKit on female headers
- PCA9685 breakout/module on headers
- MPU6050 module
- QMC5883L remote module
- DHT11 module
- light sensor module
- water sensor module
- INMP441 microphone
- ultrasonic US1
- active buzzer module

### Not included in PCB v1

- LiDAR or ToF
- ACS758/current sensing
- MOSFET accessory outputs
- SN74AHCT125 buffers
- ULN2003A
- extra clamp/Schottky networks
- eight-sensor ultrasonic multiplexer/decoder logic
- traction-current distribution

## Motor-controller connector plan

Each motor-controller position should reserve a connector or pads for:

```text
P
DIR
GND
S       reserved for speed-pulse measurement
BRAKE   reserved
STOP    reserved / existing physical E-stop remains separate
```

Only `P`, `DIR` and `GND` are required by PCB v1. `P` and `DIR` each receive a 100-ohm series resistor from PCA channels 0–7.

## Remote QMC5883L cable

Use a locking 4-pin connector if possible:

```text
QMC
1 3V3
2 GND
3 SDA
4 SCL
```

Mount the QMC remotely from high-current/magnetic hardware. A plug connector is preferred over permanently soldered flying wires because the sensor can be replaced and the cable cannot easily tear a copper pad from the PCB.

## If you want direct-soldered wires instead of connectors

Use **plated through-holes**, not flat surface pads.

For each wire:

- finished hole: about 1.0–1.2 mm for typical thin sensor wire;
- copper pad diameter: around 2.4–3.0 mm;
- keep enough annular ring around the hole;
- put the pads near the board edge;
- add cable strain relief behind them.

Two easy strain-relief styles:

```text
board edge
   |  wire pads          mechanical holes
   |  o o o o               O     O
   |  3V G SDA SCL          cable/zip-tie
```

or route the cable through two holes before soldering:

```text
cable -> through hole A -> loop -> hole B -> solder pads
```

When the cable is pulled, the PCB holes/zip tie take the load instead of the soldered copper pads.

## Recommended connector family

For low-current sensors, use one consistent keyed family throughout the robot. JST-XH is easy to obtain and mechanically much better than Dupont jumpers. Use pre-crimped pigtails if you do not want to buy a crimp tool.

Suggested connector sizes:

- QMC5883L: 4-pin
- MPU6050: 4-pin
- ultrasonic: 4-pin
- light: 4-pin
- Pi UART: 4-pin
- INMP441: 6-pin
- DHT11: 3-pin
- water: 3-pin
- buzzer: 3-pin

## Ultrasonic expansion

US1 is wired directly to GPIO18/GPIO19. US2-US8 may be mechanically provided now, but their TRIG/ECHO lines terminate at an expansion header and are not connected to ESP32 GPIO in PCB v1.

This avoids unnecessary selector/multiplexer circuitry until the extra sensors are actually needed.
