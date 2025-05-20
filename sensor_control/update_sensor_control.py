import cherrypy
import requests
import json
import logging

# Telegram config (replace with your bot's credentials)
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"  # Or dynamically manage users

# Service Registry base URL
SERVICE_REGISTRY_URL = "http://localhost:8080/services"

# Service information
SERVICE_NAME = "sensor-control"
SERVICE_PORT = 9091

logging.basicConfig(level=logging.INFO)

class SensorControlService:
    
    def __init__(self):
        # Register the service upon startup
        self.register_service()

    def register_service(self):
        try:
            # Register the Sensor Control service with the Service Registry
            service_info = {
                "name": SERVICE_NAME,
                "url": f"http://localhost:{SERVICE_PORT}",
                "description": "Handles sensor data and sends alerts"
            }

            response = requests.post(f"{SERVICE_REGISTRY_URL}/register", json=service_info)
            if response.status_code == 200:
                logging.info(f"Service {SERVICE_NAME} registered successfully.")
            else:
                logging.warning(f"Failed to register {SERVICE_NAME}: {response.text}")

        except Exception as e:
            logging.exception("Error registering service")

    @cherrypy.expose
    @cherrypy.tools.json_in()
    def sensor_data(self):
        try:
            input_data = cherrypy.request.json
            device_id = input_data.get("deviceID")
            sensor_data = input_data.get("sensorData")

            if not device_id or not sensor_data:
                cherrypy.response.status = 400
                return json.dumps({"error": "Missing deviceID or sensorData"})

            # Step 1: Fetch Device Info microservice URL from Service Registry
            device_info_service = self.get_service_url("device-info")
            if not device_info_service:
                cherrypy.response.status = 502
                return json.dumps({"error": "Device Info service not found"})

            # Step 2: Fetch thresholds from Device Info microservice
            threshold_response = requests.get(f"{device_info_service}/devices/{device_id}")
            if threshold_response.status_code != 200:
                cherrypy.response.status = 502
                return json.dumps({"error": "Failed to fetch thresholds from device info"})

            device_info = threshold_response.json()
            thresholds = device_info.get("thresholds", {})

            # Step 3: Compare and detect alarms
            out_of_range = []
            for sensor, value in sensor_data.items():
                th = thresholds.get(sensor)
                if not th:
                    continue
                if value < th["min"] or value > th["max"]:
                    out_of_range.append(f"{sensor}: {value} (expected {th['min']}–{th['max']})")

            # Step 4: Send alert if needed
            if out_of_range:
                alert_msg = f"🚨 Alert for device {device_id}:\n" + "\n".join(out_of_range)
                self.send_telegram_alert(alert_msg)

            return json.dumps({"status": "processed", "alerts": out_of_range})

        except Exception as e:
            logging.exception("Error processing sensor data")
            cherrypy.response.status = 500
            return json.dumps({"error": "Internal server error"})

    def get_service_url(self, service_name):
        try:
            # Query Service Registry for the service URL
            response = requests.get(f"{SERVICE_REGISTRY_URL}/services/{service_name}")
            if response.status_code == 200:
                service_info = response.json()
                return service_info.get("url")
            else:
                logging.warning(f"Service {service_name} not found in registry.")
                return None
        except Exception as e:
            logging.exception("Error fetching service URL from registry")
            return None

    def send_telegram_alert(self, message):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        try:
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                logging.warning(f"Failed to send Telegram alert: {response.text}")
        except Exception as e:
            logging.exception("Telegram alert failed")

if __name__ == '__main__':
    cherrypy.config.update({'server.socket_port': SERVICE_PORT})
    cherrypy.quickstart(SensorControlService(), '/', {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.json_in.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')],
        }
    })
