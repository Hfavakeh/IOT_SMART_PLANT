import paho.mqtt.client as mqtt
import json
import requests

class ControlSystem:
    def __init__(self):
        self.broker = None
        self.sensors_topic = None
        self.alarms_topic = None
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def discover_services(self):
        services = requests.get("http://localhost:8080/ServiceCatalog").json()
        self.broker = next(s["service_url"] for s in services 
                          if s["service_name"] == "broker_address")
        self.sensors_topic = next(s["service_url"] for s in services 
                                 if s["service_name"] == "SENSORS_TOPIC")
        self.alarms_topic = next(s["service_url"] for s in services 
                                if s["service_name"] == "ALARMS_TOPIC")
        
    def on_connect(self, client, userdata, flags, rc):
        client.subscribe(self.sensors_topic)
        client.subscribe(self.alarms_topic)
        print(f"Connected to {self.broker}")

    def on_message(self, client, userdata, msg):
        payload = json.loads(msg.payload.decode())
        
        if msg.topic == self.sensors_topic:
            self.handle_sensor_data(payload)
        elif msg.topic == self.alarms_topic:
            self.handle_prediction(payload)

    def handle_sensor_data(self, data):
        """Process real-time sensor readings"""
        thresholds = requests.get(
            f"http://localhost:8080/DeviceCatalog/{data['device']}"
        ).json()["device_info"]["thresholds"]
        
        alerts = []
        for metric, value in data.items():
            if value < thresholds[metric]["min"]:
                alerts.append(f"LOW_{metric.upper()}")
            elif value > thresholds[metric]["max"]:
                alerts.append(f"HIGH_{metric.upper()}")
        
        if alerts:
            print(f"⚠️ Immediate alerts: {', '.join(alerts)}")

    def handle_prediction(self, prediction):
        """Process long-term predictions"""
        print(f"🔮 Prediction Alert: {prediction['prediction']}")
        print(f"   Thresholds: {prediction['thresholds']}")
        print(f"   Timestamp: {prediction['timestamp']}")

    def start(self):
        self.discover_services()
        broker_host = self.broker.split("//")[1].split(":")[0]
        broker_port = int(self.broker.split(":")[-1])
        self.client.connect(broker_host, broker_port)
        self.client.loop_forever()

if __name__ == "__main__":
    controller = ControlSystem()
    controller.start()