# Docker Compose: Air Quality Monitoring with Home Assistant, MQTT and SCD41

This multi-container Docker app is orchestrated with [Docker Compose](https://docs.docker.com/compose/) for rapid and modular deployment that fits in any homelab and small-scale monitoring environments.

It creates a lightweight indoor air quality monitoring stack using an [Adafruit SCD41](https://www.adafruit.com/product/5190) CO2 sensor connected to a [Raspberry Pi](https://www.raspberrypi.com/) over I2C, with a Python collector publishing measurements to [MQTT](https://mqtt.org/) via [Eclipse Mosquitto](https://mosquitto.org/), and [Home Assistant](https://www.home-assistant.io/) for monitoring, automation and historical visualisation.

The stack is intentionally lightweight and focuses on long-term operational simplicity for small-scale home monitoring deployments.

## Architecture

```text
Adafruit SCD41
        │
        │ I2C
        ▼
Python Collector
        │
        │ MQTT
        ▼
Eclipse Mosquitto
        │
        │ MQTT Discovery
        ▼
Home Assistant
        │
        ├── Automation
        ├── Historical Graphs
        └── Notifications
```

The stack avoids additional telemetry infrastructure such as InfluxDB and Grafana in favour of Home Assistant's built-in recorder and visualisation capabilities.

The collector reads CO2, temperature and relative humidity measurements from the Adafruit SCD41 over I2C and publishes the measurements to MQTT via Eclipse Mosquitto.

Home Assistant automatically discovers the MQTT entities, stores historical measurements in SQLite through the recorder integration, and provides automation, graphing and mobile notifications.

## Table of Contents

- [Getting Started](#getting-started)
  - [Git Clone](#git-clone)
  - [Environment Variables](#environment-variables)
  - [Docker Compose](#docker-compose)
    - [Install](#install)
    - [I2C](#i2c)
    - [Mosquitto Password File](#mosquitto-password-file)
    - [Up and Down](#up-and-down)
- [Home Assistant](#home-assistant)
  - [MQTT Discovery](#mqtt-discovery)
  - [Recorder](#recorder)
  - [Automation](#automation)
- [Tailscale](#tailscale)
- [Backup and Restore](#backup-and-restore)
- [Reference](#reference)

## Getting Started

Get started in four simple steps:

1. [Download](#git-clone) a copy of the app;
2. Create the [environment variables](#environment-variables) for MQTT and the sensor collector;
3. Configure [I2C](#i2c) on the Raspberry Pi; and
4. [Docker Compose](#docker-compose) to start the app.

### Git Clone

Download a copy of the app with `git clone`.

```shell
$ git clone https://github.com/kurtcms/airq /app/airq/
```

### Environment Variables

Docker Compose expects the MQTT settings, device name and publish interval as environment variables in a `.env` file in the same directory.

Be sure to create the `.env` file.

```shell
$ nano /app/airq/.env
```

And define the variables accordingly.

```
# Timezone
TZ=America/Vancouver

# MQTT
MQTT_HOST=mosquitto
MQTT_PORT=1883
MQTT_USER=airq
MQTT_PASSWORD='(redacted)'

# Sensor device
DEVICE_ID=kurt-adafruit-scd41
DEVICE_NAME='Adafruit SCD41'

# Sensor publish interval in seconds
PUBLISH_INTERVAL_SECONDS=60
```

### Docker Compose

With Docker Compose, the stack may be started with a single command.

#### Install

Install [Docker](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/) with the [Bash](https://github.com/gitGNU/gnu_bash) script that comes with the app.

```shell
$ chmod +x /app/airq/docker-compose/docker-compose.sh \
    && /app/airq/docker-compose/docker-compose.sh
```

#### I2C

The SCD41 sensor communicates over I2C. I2C must therefore be enabled on the Raspberry Pi.

Enable I2C with `raspi-config`.

```shell
$ raspi-config
```

Navigate to:

```text
Interface Options
└── I2C
```

Enable and then reboot the Raspberry Pi.

Verify that the SCD41 sensor is visible on the I2C bus.

```shell
$ apt install -y i2c-tools
$ i2cdetect -y 1
```

The SCD41 should appear at address `0x62`.

#### Mosquitto Password File

Create the Mosquitto password file before starting the containers.

```shell
$ docker run --rm -it \
    -v /app/airq/mosquitto/config:/mosquitto/config \
    eclipse-mosquitto:2 \
    mosquitto_passwd -c /mosquitto/config/passwordfile airq
```

Enter the MQTT password when prompted.

#### Up and Down

Start the containers with Docker Compose.

```shell
$ docker compose -f /app/airq/docker-compose.yml up -d
```

Stopping the containers is as simple as a single command.

```shell
$ docker compose -f /app/airq/docker-compose.yml down
```

Verify that the containers are healthy.

```shell
$ docker ps
```

The Home Assistant web interface will be reachable at:

```text
http://<raspberry-pi-ip>:8123
```

## Home Assistant

Home Assistant automatically discovers the SCD41 sensor entities via MQTT discovery.

### MQTT Discovery

The Python collector publishes Home Assistant MQTT discovery payloads for the following entities:

- CO2
- Temperature
- Relative Humidity

The entities will automatically appear in Home Assistant after the collector container starts.

### Recorder

The Home Assistant recorder is configured for long-term historical storage with reduced storage churn.

```yaml
recorder:
  purge_keep_days: 360
  auto_purge: true
  commit_interval: 60
```

Only the relevant air quality entities are included in the recorder database.

### Automation

Example Home Assistant automation for elevated CO2.

```yaml
- id: "co2_high_alert"
  alias: CO2 High
  trigger:
    - platform: numeric_state
      entity_id: sensor.adafruit_scd41_co2
      above: 1000
      for:
        minutes: 10

  action:
    - service: notify.mobile_app_iphone
      data:
        message: 'CO2 has been above 1000 ppm for 10 mins. Current level: {{ states(''sensor.adafruit_scd41_co2'') }} ppm.'
```

## Tailscale

[Tailscale](https://tailscale.com/) may optionally be installed directly on the Raspberry Pi host operating system for secure remote access without exposing ports publicly.

Install Tailscale.

```shell
$ curl -fsSL https://tailscale.com/install.sh | sh
```

Authenticate the Raspberry Pi.

```shell
$ tailscale up
```

The Home Assistant web interface and SSH will then be reachable securely through the Tailscale mesh network.

## Backup and Restore

The Home Assistant configuration, Mosquitto configuration and Docker Compose stack may be backed up by making a copy of the app directory.

```shell
$ cp -r /app/airq /backup/
```

The Home Assistant SQLite database is stored under:

```text
/app/airq/homeassistant/home-assistant_v2.db
```

Backing up the database while Home Assistant is stopped is recommended.

```shell
$ docker compose down
$ cp /app/airq/homeassistant/home-assistant_v2.db /backup/
```

## Reference

- [Docker Compose](https://docs.docker.com/compose/)
- [Home Assistant](https://www.home-assistant.io/)
- [Eclipse Mosquitto](https://mosquitto.org/)
- [Adafruit SCD41](https://www.adafruit.com/product/5190)
- [Tailscale](https://tailscale.com/)
- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/)