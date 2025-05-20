import cherrypy
import requests
import json
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LinearRegression
import numpy as np
import paho.mqtt.publish as publish

# بارگذاری تنظیمات
with open("config.json", "r") as f:
    CONFIG = json.load(f)

THINGSPEAK_ADAPTOR_URL = CONFIG["thingspeak_adaptor_url"]
DEVICE_CATALOG_URL = CONFIG["device_catalog_url"]
alarms_topic = CONFIG.get("ALARMS_TOPIC", "plant_care/alarms")
broker_address = CONFIG.get("broker_address", "localhost")

class TimeShiftPredictor:
    exposed = True

    def GET(self, *uri, **params):
        try:
            device_id = params.get("device_name")
            weeks = int(params.get("weeks", 2))

            if not device_id:
                raise ValueError("Missing device_id")

            url = f"{THINGSPEAK_ADAPTOR_URL}/data"
            response = requests.get(url, params={"days": weeks * 7})
            response.raise_for_status()
            data = response.json()

            df = pd.DataFrame(data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.dropna(subset=["temperature", "soil_moisture"])

            threshold_resp = requests.get(f"{DEVICE_CATALOG_URL}/{device_id}")
            threshold_resp.raise_for_status()
            thresholds = threshold_resp.json()["device_info"]["thresholds"]

            result = {}
            alarms = []

            for variable in ["temperature", "soil_moisture"]:
                df[f"{variable}_day"] = (df["timestamp"] - df["timestamp"].min()).dt.total_seconds() / (3600*24)
                X = df[[f"{variable}_day"]].values
                y = df[variable].values

                model = LinearRegression()
                model.fit(X, y)

                future_days = np.array([[X[-1][0] + i] for i in range(1, 8)])
                predictions = model.predict(future_days)

                pred_list = []
                for day_offset, pred in enumerate(predictions, start=1):
                    status = "normal"
                    if pred < thresholds[variable]["min"]:
                        status = "too low"
                        alarms.append(f"[Prediction Alarm] {variable} will be too low (Day {day_offset}: {round(pred, 2)})")
                    elif pred > thresholds[variable]["max"]:
                        status = "too high"
                        alarms.append(f"[Prediction Alarm] {variable} will be too high (Day {day_offset}: {round(pred, 2)})")
                    pred_list.append({
                        "day": day_offset,
                        "prediction": round(pred, 2),
                        "status": status
                    })

                result[variable] = {
                    "threshold_min": thresholds[variable]["min"],
                    "threshold_max": thresholds[variable]["max"],
                    "predictions": pred_list
                }

            for alarm in alarms:
                publish.single(alarms_topic, alarm, hostname=broker_address)

            cherrypy.response.headers["Content-Type"] = "application/json"
            return json.dumps(result).encode('utf-8')

        except Exception as e:
            cherrypy.response.status = 500
            return json.dumps({"error": str(e)}).encode('utf-8')


if __name__ == "__main__":
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        }
    }
    cherrypy.tree.mount(TimeShiftPredictor(), '/', conf)
    cherrypy.config.update({'server.socket_host': '0.0.0.0'})
    cherrypy.config.update({'server.socket_port': 8082})
    cherrypy.engine.start()
    cherrypy.engine.block()