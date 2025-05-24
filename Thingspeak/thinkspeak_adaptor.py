import os
import cherrypy
import threading
import json
import requests
import paho.mqtt.client as mqtt

# Load config
with open("config.json", "r") as f:
    CONFIG = json.load(f)

THINGSPEAK_API_KEY = CONFIG["thingspeak"]["write_api_key"]
THINGSPEAK_URL = CONFIG["thingspeak"]["url"]
SERVICE_CATALOG_URL = CONFIG["service_catalog_url"]
SERVICE_INFO = CONFIG["service_info"]

BROKER = None
TOPIC = None

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

def fetch_service_config():
    response = requests.get(SERVICE_CATALOG_URL)
    response.raise_for_status()
    services = response.json()

    broker, topic = None, None
    for service in services:
        if service.get("service_name") == "broker_address":
            broker = service.get("service_url")
        elif service.get("service_name") == "SENSORS_TOPIC":
            topic = service.get("service_url")

    if not broker or not topic:
        raise ValueError("Missing 'broker_address' or 'SENSORS_TOPIC'")
    return broker, topic

def send_to_thingspeak(sensor_data):
    print("Sensor data:", sensor_data)
    payload = {
        "api_key": THINGSPEAK_API_KEY,
        "field1": sensor_data.get("temperature"),
        "field2": sensor_data.get("light"),
        "field3": sensor_data.get("soil_moisture"),
        "field4": sensor_data.get("device_name"),
    }

    try:
        response = requests.post(THINGSPEAK_URL, data=payload)
        if response.status_code == 200:
            print("Data sent to ThingSpeak:", payload)
            return True, payload
        else:
            print(f"ThingSpeak failed with status code: {response.status_code}")
            return False, {"status_code": response.status_code}
    except Exception as e:
        print(f"ThingSpeak error: {e}")
        return False, {"error": str(e)}

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(TOPIC)
    else:
        print(f"Connection failed, code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received: {payload}")
        send_to_thingspeak(payload)
    except Exception as e:
        print(f"Message error: {e}")

def mqtt_loop():
    global BROKER, TOPIC
    BROKER, TOPIC = fetch_service_config()

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER)
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
            channel_id = CONFIG["thingspeak"]["channel_id"]
            api_key =  CONFIG["thingspeak"]["read_api_key"]
            # device_name=""
            # if len(uri)>1 and uri[1]:
            #     device_name = uri[1]
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
                "device_name": e["field4"] if e.get("field4") else None,
            } for e in feeds] #if e.get("field4") == device_name]

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

     except Exception as e:
        cherrypy.response.status = 500
        return json.dumps({"error": str(e)})

    def POST(self, *uri, **params):
        return {"status": "Service is running"}
    
    def PUT(self, *uri, **params):
        return {"status": "Service is running"}

    def DELETE(self, *uri, **params):
        return {"status": "Service is running"}

if __name__ == "__main__":
    register_service()

    # Start MQTT client in background thread
    mqtt_thread = threading.Thread(target=mqtt_loop)
    mqtt_thread.daemon = True
    mqtt_thread.start()

    # Start CherryPy REST server
    conf = {
        '/': {  
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': False,
            # 'cors.expose.on': False,
        }
    }
    # cherrypy.quickstart(ThingSpeakAdapterService())
    
    cherrypy.tree.mount(ThingSpeakAdapterService(), '/', conf)
    cherrypy.config.update({'server.socket_host': os.environ.get('IP_ADDRESS','0.0.0.0')})
    # cherrypy.config.update({'server.socket_port': int(os.environ.get('IP_PORT','8081'))})
    cherrypy.config.update({'server.socket_port': int('8081')})
    cherrypy.engine.start()
    #while True:
    #    time.sleep(1)
    cherrypy.engine.block()
