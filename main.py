# main.py

import time
from services.mqtt_client import connect_mqtt, publish
from services.thingspeak_client import send_to_thingspeak
from services.telegram_bot import send_alert
from sensors.temperature_sensor import read_temperature_and_humidity
from sensors.moisture_sensor import read_moisture
from sensors.light_sensor import read_light
from config.config import (
    MQTT_TOPIC_TEMPERATURE,
    MQTT_TOPIC_HUMIDITY,
    MQTT_TOPIC_MOISTURE,
    MQTT_TOPIC_LIGHT,
    TEMPERATURE_THRESHOLD,
    HUMIDITY_THRESHOLD,
    MOISTURE_THRESHOLD,
    LIGHT_THRESHOLD
)

def check_thresholds(temperature, humidity, moisture, light):
    if temperature < TEMPERATURE_THRESHOLD:
        send_alert(f"Temperature is low: {temperature}°C. Turning on heater.")
        # Add code to turn on heater
    if humidity < HUMIDITY_THRESHOLD:
        send_alert(f"Humidity is low: {humidity}%. Consider humidifying the environment.")
        # Add code to control humidifier
    if moisture < MOISTURE_THRESHOLD:
        send_alert(f"Soil moisture is low: {moisture}. Watering the plant.")
        # Add code to control water pump
    if light < LIGHT_THRESHOLD:
        send_alert(f"Light level is low: {light} lx. Turning on artificial light.")
        # Add code to control lighting system

def main():
    connect_mqtt()
    while True:
        temperature, humidity = read_temperature_and_humidity()
        moisture = read_moisture()
        light = read_light()

        if temperature is not None and humidity is not None:
            publish(MQTT_TOPIC_TEMPERATURE, temperature)
            publish(MQTT_TOPIC_HUMIDITY, humidity)
            print(f"Temperature: {temperature}°C, Humidity: {humidity}%")
        else:
            print("Failed to read temperature and humidity data.")

        publish(MQTT_TOPIC_MOISTURE, moisture)
        print(f"Soil Moisture: {moisture}")

        publish(MQTT_TOPIC_LIGHT, light)
        print(f"Light Level: {light} lx")

        send_to_thingspeak(temperature, humidity, moisture, light)

        check_thresholds(temperature, humidity, moisture, light)

        time.sleep(30)  # Wait for 1 minute before next reading

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Program terminated.")
