import requests
import json
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LinearRegression
import numpy as np
import paho.mqtt.publish as publish
import os
import time
# Load configuration
with open("config.json", "r") as f:
    CONFIG = json.load(f)

WAIT_SECONDS = int(os.environ.get("wait_seconds", 3600))
THINGSPEAK_ADAPTOR_URL = os.environ.get("thingspeak_adaptor_url", CONFIG["thingspeak_adaptor_url"])
DEVICE_CATALOG_URL = os.environ.get("service_catalog", CONFIG["device_catalog_url"])+"/DeviceCatalog"
weeks = int(CONFIG.get("weeks"))
alarms_topic = CONFIG.get("ALARMS_TOPIC")
broker_address = os.environ.get("broker_address", CONFIG["broker_address"])

def predict():
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
            output_file = "prediction_results.txt"
            header = f"{datetime.now().isoformat()} | {'='*20} | Device ID: {device_id}\n"
            content = header + json.dumps(result, indent=2) + "\n\n"

            if not os.path.exists(output_file):
                with open(output_file, "w") as f:
                    f.write(content)
            else:
                with open(output_file, "a") as f:
                    f.write(content)
        except Exception as e:
            error_log_file = "prediction_errors.log"
            error_header = f"{datetime.now().isoformat()} | {'='*20} | Device ID: {device_id}\n"
            error_content = error_header + f"{str(e)}\n\n"
            with open(error_log_file, "a") as log_f:
                log_f.write(error_content)
            print(f"[ERROR] {str(e)}")


            print("\n=== All Device Predictions ===")
        print(json.dumps(results_by_device, indent=2))
if __name__ == "__main__":
    def should_run_this_week(flag_file="last_run.flag"):
        today = datetime.now().date()
        if os.path.exists(flag_file):
            with open(flag_file, "r") as f:
                last_run = f.read().strip()
            if last_run == str(today.isocalendar()[1]):
                print("[INFO] Prediction already run this week.")
                return False
        with open(flag_file, "w") as f:
            f.write(str(today.isocalendar()[1]))
        return True

    while True:
        if should_run_this_week():
            predict()
            print("[INFO] Waiting for 1 hour before next check...")
            time.sleep(WAIT_SECONDS)
        else:
            print("[INFO] Waiting for 1 hour before next check...")
            time.sleep(WAIT_SECONDS)