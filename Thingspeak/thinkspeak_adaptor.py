import os
import cherrypy
import threading
import json
import requests
import paho.mqtt.client as mqtt

SERVICE_CATALOG_URL = ""
# DEVICE_CATALOG_URL = None
# SERVICE_INFO = None
# THINGSPEAK_URL = None
# THINGSPEAK_TOCKEN=None

def create_thingspeak_channel(user_api_key, name): 
    payload = {
        'api_key': user_api_key,
        'name': name,
        'description': 'Created via Python',
        'field1': "Temperature",
        'field2': "Light",
        'field3': "Moisture",
        'public_flag': False
    }
    response = requests.post('https://api.thingspeak.com/channels.json', data=payload)    
    channel_id,api_keys = response.json().get('id'),response.json().get('api_keys', [])
    return channel_id,api_keys

def channel_exists(api_key, target_name):
    url = f"https://api.thingspeak.com/channels.json?api_key={api_key}"
    response = requests.get(url)

    if response.status_code != 200:
        print("Failed to retrieve channels:", response.status_code)
        return False

    channels = response.json()

    for channel in channels:
        if channel.get("name") == target_name:
            return True,channel  # Found the channel

    return False,None  # Not found

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
    api_keys=""
    channel_id=None
    channel_exist,chnnel_data=channel_exists(THINGSPEAK_TOCKEN,device_id)
    if channel_exist==False:
        channel_id,api_keys=create_thingspeak_channel(THINGSPEAK_TOCKEN,device_id)
    else:
        channel_id=chnnel_data.get("id")
        api_keys=chnnel_data.get("api_keys", [])
        if len(api_keys) < 2:
            print(f"Channel {device_id} does not have enough API keys.")
            return False, {"error": "Insufficient API keys for channel"}
    # Get device info from Device Catalog
    try:
        response = requests.get(DEVICE_CATALOG_URL+f"/{device_id}")
        print(f"Fetching device info for {device_id} from Device Catalog")
        response.raise_for_status()
        device_info = response.json().get("device_info", {})
        ts_info = device_info.get("thingspeak", {})
        if not ts_info:
            print(api_keys)
            thing_speak_config=json.dumps({"channel_id": channel_id, "write_api_key": api_keys[0].get("api_key"), "read_api_key": api_keys[1].get("api_key")})
            # Update device info in Device Catalog with new ThingSpeak config
            print(type(thing_speak_config))
            device_info["thingspeak"]= json.loads(thing_speak_config)
            update_payload = {
                "device_name": device_id,
                "device_info": device_info
            }
            print(json.dumps(update_payload))
            update_response = requests.put(DEVICE_CATALOG_URL, json=update_payload)
            update_response.raise_for_status()
            ts_info = json.loads(thing_speak_config)
        
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
        c.subscribe(topic+"/#") if rc == 0 else None
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
            response = requests.get(DEVICE_CATALOG_URL+f"/{device_id}")
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
    SERVICE_CATALOG_URL=os.environ.get("service_catalog", CONFIG["service_catalog_url"])+"/ServiceCatalog"
    DEVICE_CATALOG_URL= os.environ.get("service_catalog", CONFIG["device_registration_url"])+"/DeviceCatalog"
    SERVICE_INFO = CONFIG["service_info"]
    THINGSPEAK_URL = CONFIG["thingspeak"]["write_url"]
    THINGSPEAK_TOCKEN=CONFIG["thingspeak"]["token"]
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

