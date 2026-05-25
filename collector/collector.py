import json
import os
import time

from smbus2 import SMBus, i2c_msg
import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "airq")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

DEVICE_ID = os.getenv("DEVICE_ID", "kurt-adafruit-scd41")
DEVICE_NAME = os.getenv("DEVICE_NAME", "Adafruit SCD41")
PUBLISH_INTERVAL_SECONDS = int(os.getenv("PUBLISH_INTERVAL_SECONDS", "10"))

SCD41_ADDR = 0x62
I2C_BUS = 1

STATE_TOPIC = f"home/air_quality/{DEVICE_ID}/state"
AVAILABILITY_TOPIC = f"home/air_quality/{DEVICE_ID}/availability"


def crc8(data):
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def write_cmd(bus, cmd):
    bus.write_i2c_block_data(SCD41_ADDR, cmd >> 8, [cmd & 0xFF])


def read_measurement(bus):
    write_cmd(bus, 0xEC05)
    time.sleep(0.001)

    msg = i2c_msg.read(SCD41_ADDR, 9)
    bus.i2c_rdwr(msg)
    data = list(msg)

    for i in (0, 3, 6):
        if crc8(data[i:i + 2]) != data[i + 2]:
            raise RuntimeError("SCD41 CRC check failed")

    co2 = (data[0] << 8) | data[1]
    temp_raw = (data[3] << 8) | data[4]
    rh_raw = (data[6] << 8) | data[7]

    temp_c = -45 + 175 * temp_raw / 65535
    rh = 100 * rh_raw / 65535

    return int(co2), round(temp_c, 2), round(rh, 2)


def publish_discovery(client):
    device = {
        "identifiers": [DEVICE_ID],
        "name": DEVICE_NAME,
        "manufacturer": "kurtcms",
        "model": "Raspberry Pi 4 + Adafruit SCD41",
    }

    sensors = [
        {
            "key": "co2",
            "name": "CO2",
            "device_class": "carbon_dioxide",
            "unit": "ppm",
            "json_key": "co2_ppm",
        },
        {
            "key": "temperature",
            "name": "Temperature",
            "device_class": "temperature",
            "unit": "°C",
            "json_key": "temperature_c",
        },
        {
            "key": "humidity",
            "name": "Humidity",
            "device_class": "humidity",
            "unit": "%",
            "json_key": "relative_humidity",
        },
    ]

    for sensor in sensors:
        topic = f"homeassistant/sensor/{DEVICE_ID}/{sensor['key']}/config"
        payload = {
            "name": sensor["name"],
            "unique_id": f"{DEVICE_ID}_{sensor['key']}",
            "object_id": f"adafruit_scd41_{sensor['key']}",
            "state_topic": STATE_TOPIC,
            "availability_topic": AVAILABILITY_TOPIC,
            "payload_available": "online",
            "payload_not_available": "offline",
            "device_class": sensor["device_class"],
            "state_class": "measurement",
            "unit_of_measurement": sensor["unit"],
            "value_template": "{{ value_json." + sensor["json_key"] + " }}",
            "device": device,
        }

        client.publish(topic, json.dumps(payload), qos=1, retain=True)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.will_set(AVAILABILITY_TOPIC, "offline", retain=True)

    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    publish_discovery(client)
    client.publish(AVAILABILITY_TOPIC, "online", retain=True)

    with SMBus(I2C_BUS) as bus:
        try:
            write_cmd(bus, 0x3F86)
            time.sleep(0.5)
        except Exception:
            pass

        write_cmd(bus, 0x21B1)
        time.sleep(5)

        while True:
            co2, temp_c, rh = read_measurement(bus)

            payload = {
                "co2_ppm": co2,
                "temperature_c": temp_c,
                "relative_humidity": rh,
            }

            print(json.dumps(payload), flush=True)
            client.publish(STATE_TOPIC, json.dumps(payload), qos=1)

            time.sleep(PUBLISH_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
