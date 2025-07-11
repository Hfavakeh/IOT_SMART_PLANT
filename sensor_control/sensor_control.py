import paho.mqtt.client as mqtt
import json
import requests
from datetime import datetime

def register_service():
    """Register this microservice with the Service and Device Registry."""
    try:
        response = requests.post(SERVICE_CATALOG_URL, json=SERVICE_INFO)
        if response.status_code == 201:
            print(f"Service registered successfully: {SERVICE_INFO}")
        elif response.status_code == 400:
            print("Service already registered.")
        else:
            print(f"Failed to register service: {response.status_code}")
    except Exception as e:
        print(f"Error registering service: {e}")

def fetch_service_config():
    
    response = requests.get(SERVICE_CATALOG_URL)
    response.raise_for_status()  # Raise an exception for non-200 responses.
    services = response.json()  # Expecting a list of service objects.
   
    broker = None
    topic = None
    control_topic = None
    for service in services:
        if service.get("service_name") == "broker_address":
            broker = service.get("service_url")
        elif service.get("service_name") == "SENSORS_TOPIC":
            topic = service.get("service_url")
        elif service.get("service_name") == "CONTROL_TOPIC":
            control_topic = service.get("service_url")
            
    
    if broker is None or topic is None:
        raise ValueError("Service registry response missing required service: "
                         "'broker_address' and/or 'mqtt_topic'")
    return broker, topic, control_topic



def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker."""
    if rc == 0:
        print("Connected to MQTT broker!")
        client.subscribe(TOPIC)
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """Callback when a message is received on the subscribed topic."""
    try:
        #print("start")
        #print(msg.payload.decode())
        # Decode and parse the sensor data
        sensor_data = json.loads(msg.payload.decode())
        #print(f"Received sensor data: {sensor_data}")

        # Validate the data against thresholds
        actions = validate_sensor_data(sensor_data)

        # Publish actions or alerts to the control topic
        if actions:
            publish_control_messages(actions)
    except Exception as e:
        print(f"Error processing message: {e}")

# === Determine current season based on month ===
def get_current_season():
    month = datetime.now().month
    return "summer" if 5 <= month <= 10 else "winter"        

def validate_sensor_data(sensor_data):
    """Fetch thresholds for the device and validate sensor data."""
    device_id = sensor_data.get("device_id")
    if not device_id:
        print("No device_id found in sensor data.")

    try:
        # Get plant thresholds from DeviceCatalog
        resp = requests.get(f"{DEVICE_INFO_URL}/{device_id}")
        resp.raise_for_status()
        plant_info = resp.json()
        plant_thresholds = plant_info.get("device_info", {}).get("thresholds", {})

        season = get_current_season()
        home_thresholds = CONFIG[season]

        actions = []

        for sensor, value in sensor_data.items():
            if sensor in plant_thresholds:
                if value < plant_thresholds[sensor]["min"]:
                    message_dict = {
                        "device_id": device_id,
                        "message" : f"[Plant] {sensor} too low ({value})"
                    }
                    actions.append(json.dumps(message_dict))

                elif value > plant_thresholds[sensor]["max"]:
                    message_dict = {
                        "device_id": device_id,
                        "message" : f"[Plant] {sensor} too high ({value})"
                    }
                    actions.append(json.dumps(message_dict))

            if sensor in home_thresholds:
                if value < home_thresholds[sensor]["min"]:
                    message_dict = {
                        "device_id": device_id,
                        "message" : f"[Home] {sensor} too low ({value})"
                    }
                    actions.append(json.dumps(message_dict))

                elif value > home_thresholds[sensor]["max"]:
                    message_dict = {
                        "device_id": device_id,
                        "message" : f"[Home] {sensor} too high ({value})"
                    }
                    actions.append(json.dumps(message_dict))
                    

        return actions
    except Exception as e:
        print(f"Failed to fetch device thresholds: {e}")
        return []

def publish_control_messages(actions):

    """Publish control messages to the MQTT broker."""
    for action in actions:
        client.publish(CONTROL_TOPIC, action)
        print(f"Published control message: {action}")

if __name__ == "__main__":
 
    # === Load thermal comfort config for the home ===
 with open("home_environment_config.json", "r") as f:
    CONFIG = json.load(f)


# URLs for the Service Registry and Device Registration endpoints
SERVICE_CATALOG_URL = CONFIG["service_catalog_url"]

# Service and Device Registry settings
SERVICE_INFO = CONFIG["service_info"]

# Sensor thresholds
# Device info endpoint (update as needed)
DEVICE_INFO_URL = CONFIG["device_info_url"]

# Retrieve the configuration from the service registry.
BROKER, TOPIC , CONTROL_TOPIC = fetch_service_config()

register_service()

    # Initialize MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

    # Connect to the MQTT broker
client.connect(BROKER)

    # Start the MQTT loop
client.loop_forever()
    