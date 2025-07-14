import random
import time
import json
import requests
import paho.mqtt.publish as publish
import sys
import os

class DeviceInfo:

    def simulate_temperature_sensor(self):
        return round(random.uniform(15.0, 30.0), 2) #various temperatures in Celsius

    def simulate_soil_moisture_sensor(self):
        return round(random.uniform(30.0, 70.0), 2)

    def simulate_light_sensor(self):
        return round(random.uniform(100.0, 1000.0), 2)

    def read_sensors(self):
        return {
            "temperature": self.simulate_temperature_sensor(),
            "soil_moisture": self.simulate_soil_moisture_sensor(),
            "light": self.simulate_light_sensor(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def send_sensor_data(self):
        while True:
            sensor_data = self.read_sensors()
            sensor_data["device_id"] = DEVICE_INFO["device_id"]
            payload = json.dumps(sensor_data)
            try:
                print("connecting to MQTT broker at", BROKER)
                publish.single(TOPIC+'/'+sensor_data["device_id"], payload, hostname=BROKER)
                print("Published sensor data:", payload," on topic ", TOPIC+'/'+sensor_data["device_id"])
            except Exception as e:
                print("Failed to publish sensor data:", e)
            time.sleep(PUBLISH_INTERVAL)

    def register_device(self):
        try:
            response = requests.get(DEVICE_REGISTRATION_URL)
            response.raise_for_status()
            registered_devices = response.json()

            device_id = DEVICE_INFO["device_id"]
            DEVICE_INFO["last_seen"] = time.time()

            # Check if the device is already registered
            existing_device = next((device for device in registered_devices if device.get("device_name") == device_id), None)

            # Prepare payload in the expected format
            payload = {
                "device_name": device_id,
                "device_info": DEVICE_INFO
            }

            if existing_device:
                update_url = f"{DEVICE_REGISTRATION_URL}"
                response = requests.put(update_url, json=payload, headers={"Content-Type": "application/json"})
                if response.status_code == 200:
                    print("Device updated successfully.")
                else:
                    print(f"Failed to update device, status: {response.status_code}")
                    print("Response content:", response.text)
            else:
                print("Sending device registration payload:")
                print(json.dumps(payload, indent=2))
                response = requests.post(DEVICE_REGISTRATION_URL, json=payload, headers={"Content-Type": "application/json"})
                if response.status_code == 201:
                    print("Device registered successfully.")
                else:
                    print(f"Failed to register device, status: {response.status_code}")
                    print("Response content:", response.text)

        except Exception as e:
            print("Error during device registration:", e)

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


def main():
    print("Starting device script")
    my_device = DeviceInfo()
    my_device.register_device()
    my_device.send_sensor_data()

if __name__ == "__main__": 
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    if "config_file" in os.environ and os.environ["config_file"]:
        config_path = os.environ["config_file"]
    with open(config_path, "r") as config_file:
        config = json.load(config_file)

    # Device information (dynamic from config)
    DEVICE_INFO = {
        "device_name": config["device"]["device_name"],  
        "device_id": config["device"]["device_info"]["device_id"],  
        "type": config["device"]["device_info"]["type"],
        "location": config["device"]["device_info"]["location"],
        "status": config["device"]["device_info"]["status"],
        "registration_date": time.strftime("%Y-%m-%d %H:%M:%S"), 
        "thresholds": config["device"]["device_info"]["thresholds"],
        "last_seen": time.time()
    }

    # URLs
    SERVICE_CATALOG_URL = os.environ.get("service_catalog", config["device"]["service_catalog_url"])+"/ServiceCatalog"
    DEVICE_REGISTRATION_URL = os.environ.get("service_catalog", config["device"]["device_registration_url"])+"/DeviceCatalog"
    PUBLISH_INTERVAL = config.get("publish_interval", 2)

    BROKER, TOPIC = fetch_service_config()

    main()
