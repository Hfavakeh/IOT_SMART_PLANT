🌱 Smart Plant Care System

An IoT-based plant monitoring and care system that uses Raspberry Pi, sensors, microservices, and ThingSpeak to automate plant care. The system collects real-time data (temperature, soil moisture, light), stores it in the cloud, applies threshold-based alerts, and integrates with Telegram Bot for user interaction.

🚀 Features

📡 Sensor Monitoring

Soil moisture, temperature, and light sensors

Real-time MQTT data streaming

☁️ Microservices Architecture

Service & Device Catalog (CherryPy-based registry)

ThingSpeak Adapter (MQTT to ThingSpeak bridge)

Sensor Control Service (dynamic thresholds, Telegram alerts)

ML Predictor (7-day data analysis & plant condition prediction)

🤖 Automation & Alerts

Dynamic thresholds fetched from Device Catalog

Automatic watering predictions (via ML)

Telegram notifications for out-of-range values

💬 Telegram Bot (PlantBot)

Register plants with ThingSpeak Channel ID + API Key

Display live sensor data

Receive real-time alerts
