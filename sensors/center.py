import random
import time
import json
import requests
import paho.mqtt.publish as publish
import sys


config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
with open(config_path, "r") as config_file:
    config = json.load(config_file)


# Device information (dynamic from config)
DEVICE_INFO = {
    "device_name": config["device"]["device_name"],  
    "device_info": {
        "id": config["device"]["device_info"]["id"],  
        "type": config["device"]["device_info"]["type"],
        "location": config["device"]["device_info"]["location"],
        "status": config["device"]["device_info"]["status"],
        "registration_date": time.strftime("%Y-%m-%d %H:%M:%S"), 
        "thresholds": config["device"]["device_info"]["thresholds"]  
    },

    "last_seen": time.time()
}

# URLs
SERVICE_CATALOG_URL = config["service_catalog_url"]
DEVICE_REGISTRATION_URL = config["device_registration_url"]
PUBLISH_INTERVAL = config.get("publish_interval", 2)

def fetch_service_config():
    response = requests.get(SERVICE_CATALOG_URL)
    response.raise_for_status()
    services = response.json()

    broker = None
    topic = None
    for service in services:
        if service.get("service_name") == "broker_address":
            broker = service.get("service_url")
        elif service.get("service_name") == "SENSORS_TOPIC":
            topic = service.get("service_url")
    
    if broker is None or topic is None:
        raise ValueError("Missing 'broker_address' or 'SENSORS_TOPIC' in service catalog.")
    
    return broker, topic

BROKER, TOPIC = fetch_service_config()

def simulate_temperature_sensor():
    return round(random.uniform(15.0, 30.0), 2)

def simulate_soil_moisture_sensor():
    return round(random.uniform(30.0, 70.0), 2)

def simulate_light_sensor():
    return round(random.uniform(100.0, 1000.0), 2)

def read_sensors():
    return {
        "temperature": simulate_temperature_sensor(),
        "soil_moisture": simulate_soil_moisture_sensor(),
        "light": simulate_light_sensor(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

def send_sensor_data():
    while True:
        sensor_data = read_sensors()
        sensor_data["device_name"] = DEVICE_INFO["device_name"]
        payload = json.dumps(sensor_data)
        try:
            publish.single(TOPIC, payload, hostname=BROKER)
            print("Published sensor data:", payload)
        except Exception as e:
            print("Failed to publish sensor data:", e)
        time.sleep(PUBLISH_INTERVAL)

def register_device():
    try:
        response = requests.get(DEVICE_REGISTRATION_URL)
        response.raise_for_status()
        registered_devices = response.json()

        device_id = DEVICE_INFO["device_info"]["id"]
        existing_device = next((device for device in registered_devices if device["device_info"]["id"] == device_id), None)

        DEVICE_INFO["last_seen"] = time.time()

        if existing_device:
            update_url = f"{DEVICE_REGISTRATION_URL}/{device_id}"
            response = requests.put(update_url, json=DEVICE_INFO, headers={"Content-Type": "application/json"})
            print("Device updated successfully." if response.status_code == 200 else f"Failed to update device, status: {response.status_code}")
        else:
            response = requests.post(DEVICE_REGISTRATION_URL, json=DEVICE_INFO, headers={"Content-Type": "application/json"})
            print("Device registered successfully." if response.status_code == 201 else f"Failed to register device, status: {response.status_code}")
    except Exception as e:
        print("Error during device registration:", e)

def main():
    print("Starting device script")
    register_device()
    send_sensor_data()

if __name__ == "__main__":
    main()
