🌱 Smart Plant Care System

An IoT-based plant monitoring and care system that uses Raspberry Pi, sensors, microservices, and ThingSpeak to automate plant care. The system collects real-time data (temperature, soil moisture, light), stores it in the cloud, applies threshold-based alerts, and integrates with a Telegram Bot for user interaction.

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

🛠️ Technologies

Programming: Python

Framework: CherryPy

Communication: MQTT, REST APIs

Cloud: ThingSpeak

Database: JSON-based storage (for registry & thresholds)

Machine Learning: Scikit-learn (linear regression for predictions)

Containerization: Docker (multi-service setup)

Messaging: Telegram Bot

⚙️ Setup & Installation
1. Clone the repo
   https://github.com/Hfavakeh/IOT_SMART_PLANT
2. Install dependencies
   pip install -r requirements.txt
3. Run with Docker
   docker-compose up --build

📊 Machine Learning Module

Fetches 7 days of sensor data from ThingSpeak

Predicts when the plant will need water

Supports multi-sensor predictions (temperature, light, moisture)

📱 Telegram Bot Commands

/register <channel_id> <api_key> → Register a new plant

/status → Show live plant status

/alerts → Enable/disable alerts

/predict → Get next watering prediction
