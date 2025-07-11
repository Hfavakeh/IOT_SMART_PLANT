import requests
import json
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LinearRegression
import numpy as np
import paho.mqtt.publish as publish

# Load configuration
with open("config.json", "r") as f:
    CONFIG = json.load(f)

THINGSPEAK_ADAPTOR_URL = CONFIG["thingspeak_adaptor_url"]
DEVICE_CATALOG_URL = CONFIG["device_catalog_url"]
weeks = int(CONFIG.get("weeks"))
alarms_topic = CONFIG.get("ALARMS_TOPIC")
broker_address = CONFIG.get("broker_address")

results_by_device = {}

# Fetch all registered devices from the catalog
device_list_resp = requests.get(DEVICE_CATALOG_URL)
device_list_resp.raise_for_status()
device_list = device_list_resp.json()

# Validate and iterate over devices
for entry in device_list:
    device_info = entry.get("device_info", {})
    device_id = device_info.get("device_id")

    if not device_id:
        continue  

    print(f"\n[INFO] Processing device: {device_id}")


try:
    print("[INFO] Fetching sensor data...")
    response = requests.get(f"{THINGSPEAK_ADAPTOR_URL}/data/{device_id}", params={"days": weeks * 7})
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, list) or not data:
        raise ValueError("Data format invalid or empty.")

    df = pd.DataFrame(data)

    if "timestamp" not in df.columns:
        raise ValueError("'timestamp' key missing in fetched data.")

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.dropna(subset=["temperature", "soil_moisture"])

    print("[INFO] Fetching thresholds from device catalog...")
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
                message_dict = {
                    "device_id": device_id,
                    "message" : f"[Prediction Alarm] {device_id} - {variable} will be too low (Day {day_offset}: {round(pred, 2)})"
                }
                alarms.append(json.dumps(message_dict))
            elif pred > thresholds[variable]["max"]:
                status = "too high"
                message_dict = {
                    "device_id": device_id,
                    "message" : f"[Prediction Alarm] {device_id} - {variable} will be too high (Day {day_offset}: {round(pred, 2)})"
                }
                alarms.append(json.dumps(message_dict))
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
        results_by_device[device_id] = result

    print("[INFO] Sending alarms via MQTT...")
    for alarm in alarms:
        publish.single(alarms_topic, alarm, hostname=broker_address)
        print(f"[ALARM SENT] {alarm}")

    print("[DONE] Prediction completed successfully.")
    print(json.dumps(result, indent=2))

except Exception as e:
    print(f"[ERROR] {str(e)}")


    print("\n=== All Device Predictions ===")
print(json.dumps(results_by_device, indent=2))
