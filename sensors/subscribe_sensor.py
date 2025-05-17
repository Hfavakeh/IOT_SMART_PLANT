import paho.mqtt.client as mqtt
import json
import requests 

# URLs for the Service Registry and Device Registration endpoints
SERVICE_CATALOG_URL = "http://localhost:8080/ServiceCatalog"

def fetch_service_config():
    
    response = requests.get(SERVICE_CATALOG_URL)
    response.raise_for_status()  # Raise an exception for non-200 responses.
    services = response.json()  # Expecting a list of service objects.
   
    broker = None
    topic = None
    for service in services:
        if service.get("service_name") == "broker_address":
            broker = service.get("service_url")
        elif service.get("service_name") == "SENSORS_TOPIC":
            topic = service.get("service_url")
    
    if broker is None or topic is None:
        raise ValueError("Service registry response missing required service: "
                         "'broker_address' and/or 'mqtt_topic'")
    return broker, topic

# Retrieve the configuration from the service registry.
# This will raise an error if the registry response does not contain both services.
BROKER, TOPIC = fetch_service_config()

def on_message(client, userdata, message):
    """Callback for when a message is received."""
    data = json.loads(message.payload.decode())
    print(f"Received sensor data: {data}")

    

client = mqtt.Client("test_client_id")
client.on_message = on_message

if __name__ == "__main__":
    client.connect(BROKER)
    client.subscribe(TOPIC)
    print("Listening for sensor data...")
    client.loop_forever()
