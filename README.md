# iot-project

## pins

pin 3, 5 : scl, sda for humidity + temp sensor

## required functions

- periodic image from camera every ~5 min
- perform segmentation on image (classical or ml) to identify plant size
- record humidty every 30

## data storage

- 30 sec
    - humidity
    - temperature

- 5 min
    - camera image

## controllables

- [PWM]  fan speed 1,2
- [PWM]  peltier throttle 1
- [PWM]  peltier throttle 2
- [GPIO] mister on/off
- [GPIO] pump on/off
- [GPIO] grow light on/off

## sensors


## computed metrics
    - camera -> biomass estimation
    - camera -> spectral analysis



