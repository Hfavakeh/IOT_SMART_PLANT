import os
import cherrypy
import threading
import json
import requests
import paho.mqtt.client as mqtt

def register_service():
    try:
        response = requests.post(SERVICE_CATALOG_URL, json=SERVICE_INFO)
        if response.status_code == 201:
            print(f"Service registered successfully: {SERVICE_INFO}")
        elif response.status_code == 409:
            print("Service already registered.")
        # else:
        #     print(f"Failed to register service: {response.status_code}")
    except Exception as e:
        print(f"Error registering service: {e}")

def fetch_service_config(service_catalog_url):
    response = requests.get(service_catalog_url)
    response.raise_for_status()
    services = response.json()

    for service in services:
        if service.get("service_name") == "broker_address":
            broker = service.get("service_url")
        elif service.get("service_name") == "SENSORS_TOPIC":
            topic = service.get("service_url")

    if not broker or not topic:
        raise ValueError("Missing broker or topic in service catalog")
    return broker, topic


def send_to_thingspeak(sensor_data):
    device_id = sensor_data.get("device_id")
    if not device_id:
        print("Missing device_id in sensor data")
        return False, {"error": "Missing device_id"}

    # Get device info from Device Catalog
    try:
        response = requests.get(f"{CONFIG['device_registration_url']}/{device_id}")
        response.raise_for_status()
        device_info = response.json().get("device_info", {})
        ts_info = device_info.get("thingspeak", {})
    except Exception as e:
        print(f"Failed to fetch device info: {e}")
        return False, {"error": str(e)}

    payload = {
        "api_key": ts_info.get("write_api_key"),
        "field1": sensor_data.get("temperature"),
        "field2": sensor_data.get("light"),
        "field3": sensor_data.get("soil_moisture")
    }

    try:
        response = requests.post(THINGSPEAK_URL, data=payload)
        if response.status_code == 200:
            print(f"Data sent for {device_id}: {payload}")
            return True, payload
        else:
            print(f"ThingSpeak error {response.status_code}")
            return False, {"status_code": response.status_code}
    except Exception as e:
        print(f"ThingSpeak post error: {e}")
        return False, {"error": str(e)}


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(topic)
    else:
        print(f"Connection failed, code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received: {payload}")
        send_to_thingspeak(payload)
    except Exception as e:
        print(f"Message error: {e}")

def mqtt_loop(broker, topic):
    client = mqtt.Client()
    client.on_connect = lambda c, u, f, rc: (
        print("Connected to MQTT broker") if rc == 0 else print(f"Connection failed: {rc}"),
        c.subscribe(topic) if rc == 0 else None
    )
    client.on_message = on_message
    client.connect(broker)
    client.loop_forever()



### === CherryPy Web Server === ###
class ThingSpeakAdapterService(object):
    exposed = True

    def __init__(self):
        pass

    def GET(self, *uri, **params):
     try:
        # Check if path is '/data'
        if len(uri) > 0 and uri[0] == 'data':
            device_id = uri[1]
            if not device_id:
                raise ValueError("Missing device_id parameter")

            # Fetch device info from Device Catalog
            response = requests.get(f"{CONFIG['device_registration_url']}/{device_id}")
            response.raise_for_status()
            device_data = response.json()
            device_info = device_data.get("device_info", {}) 

            ts_info = device_info.get("thingspeak", {})
            channel_id = ts_info.get("channel_id")
            api_key = ts_info.get("read_api_key")

            if not channel_id or not api_key:
                raise ValueError("ThingSpeak channel_id or read_api_key not found for device")

            days = int(params.get("days", 7))

            # Fetch data from ThingSpeak
            url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.json"
            # if device_name:
            #     url += f"?field4={device_name}"
            print("Fetching data from ThingSpeak...")
            print("URL:", url)
            response = requests.get(url, params={
                "api_key": api_key,
                "results": days * 1000
            })
            response.raise_for_status()

            # Process feeds
            feeds = response.json().get("feeds", [])

            parsed_data = [{
                "timestamp": e.get("created_at"),
                "temperature": float(e["field1"]) if e.get("field1") else None,
                "light": float(e["field2"]) if e.get("field2") else None,
                "soil_moisture": float(e["field3"]) if e.get("field3") else None,
            } for e in feeds] 
            # Encode response to bytes
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps(parsed_data).encode('utf-8') 
        
        elif uri[0] == 'channel':
                # Return only channel_id
                channel_id = CONFIG["thingspeak"]["channel_id"]
                cherrypy.response.headers['Content-Type'] = 'application/json'
                return json.dumps({"channel_id": channel_id}).encode('utf-8')

        # Default response
        return "ThingSpeak Adaptor Ready".encode('utf-8')

     except Exception as e:
        cherrypy.response.status = 500
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps({"error": str(e)}).encode('utf-8')  




if __name__ == "__main__":

    with open("config.json", "r") as f:
        CONFIG = json.load(f)

    SERVICE_CATALOG_URL = CONFIG["service_catalog_url"]
    DEVICE_CATALOG_URL = CONFIG["device_registration_url"]
    SERVICE_INFO = CONFIG["service_info"]
    THINGSPEAK_URL = CONFIG["thingspeak"]["write_url"]
    register_service()

    broker, topic = fetch_service_config(SERVICE_CATALOG_URL)

    mqtt_thread = threading.Thread(target=mqtt_loop, args=(broker, topic))
    mqtt_thread.daemon = True
    mqtt_thread.start()

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': False
        }
    }

    cherrypy.tree.mount(ThingSpeakAdapterService(), '/', conf)
    cherrypy.config.update({'server.socket_host': os.environ.get('IP_ADDRESS', '0.0.0.0')})
    cherrypy.config.update({'server.socket_port': int('8081')})
    cherrypy.engine.start()
    cherrypy.engine.block()

