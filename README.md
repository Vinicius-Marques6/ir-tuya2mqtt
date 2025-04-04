# ir-tuya2mqtt
Simple IR Tuya controller via MQTT.

This is a simple python application for controlling IR Tuya based devices using MQTT, good for Home Assistant and OpenHAB.

## Config
```
cp config.json.sample config.json \
cp devices.json.sample device.json
```

Customize your `template.txt` file following the existing template, the left value is an alias for the entire tuya payload (on the right).

## Publishing commands
Commands can be published using the topic example below:
```
tuya/yourDeviceID/ir/command <-- your alias
```
