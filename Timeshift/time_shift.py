import requests
import json
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
from statsmodels.tsa.arima.model import ARIMA
import statsmodels.api as sm
# Load ML config
with open("ml_config.json") as f:
    config = json.load(f)

SERVICE_REGISTRY_URL = config["service_registry_url"]
DEVICE_NAME = config["device_name"]
CHANNEL_ID = config["channel_id"]
API_KEY = config["thingspeak_api_key"]

def get_service_url(service_name):
    print(f"Fetching service URL for {service_name} from registry...")
    """Fetch a service URL from the service registry."""
    response = requests.get(SERVICE_REGISTRY_URL)
    response.raise_for_status()
    services = response.json()
    print(f"Available services: {services}")
    for service in services:
        if service["service_name"] == service_name:
            return service["service_url"]
    raise ValueError(f"Service {service_name} not found in registry.")

def get_thresholds(device_catalog_url, device_name):
    """Fetch thresholds with better error handling"""
    try:
        response = requests.get(f"{device_catalog_url}/DeviceCatalog/{device_name}")
        response.raise_for_status()
        device = response.json()
        
        if not device.get("thresholds"):
            print("Warning: No thresholds found, using defaults")
            return {"soil_moisture": {"min": 40}}
            
        return device["thresholds"]
        
    except requests.exceptions.HTTPError:
        raise ValueError(f"Device {device_name} not found in catalog")

def get_thingspeak_data(thingspeak_adapter_url, channel_id, api_key):
    """Retrieve 7 days of sensor data from the ThingSpeak adapter."""
    params = {
        "channel_id": channel_id,
        "thingspeak_api_key": api_key,
        "days": config.get("data_window_days", 30),
    }
    print(f"Fetching data from: {thingspeak_adapter_url}/data with params {params}")
    response = requests.get(f"{thingspeak_adapter_url}/data", params=params)

    if response.status_code != 200:
            raise ConnectionError(f"ThingSpeak API Error: {response.text}")
    data = response.json()
    if not data or 'soil_moisture' not in data[0]:
            raise ValueError("Invalid/missing soil moisture data")
    return data

    # print("Status Code:", response.status_code)
    # print("Response Text:", response.text)  # Add this to see the content

    # response.raise_for_status()
    # return response.json()


def predict_watering_day(sensor_data, thresholds):

    if not sensor_data:
        raise ValueError("Empty sensor data received")
    
    df = pd.DataFrame(sensor_data)
    if 'soil_moisture' not in df.columns:
        raise ValueError("Soil moisture column missing")
    
    """Predict when the soil moisture will drop below the threshold."""
    df = pd.DataFrame(sensor_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp')

    df = df[['timestamp', 'soil_moisture']].dropna()
    df['days'] = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds() / (3600 * 24)

    if df.shape[0] < 2:
        return "Insufficient data for prediction."

    # Set datetime index
    df = df.set_index('timestamp')
    X = df[['days']]
    y = df['soil_moisture']

    # Convert to numpy array
    try:
        model = ARIMA(y, order=(1,1,1))
        model_fit = model.fit()
        
        # Forecast next 100 steps
        forecast_steps = 100
        forecast = model_fit.get_forecast(steps=forecast_steps)
        predictions = forecast.predicted_mean
        
        # Create future days array for plotting
        last_day = df['days'].iloc[-1]
        future_days = np.arange(last_day + 1, last_day + forecast_steps + 1)
        
    except Exception as e:
        return f"Prediction failed: {str(e)}"

    # Predict
    moisture_threshold = thresholds.get("soil_moisture", {}).get("min")
    if not moisture_threshold:
        raise ValueError("Soil moisture threshold not configured in DeviceCatalog")
    
    future_days = np.linspace(X['days'].max(), X['days'].max() + 10, 100).reshape(-1, 1)
    forecast = model_fit.get_forecast(steps=100)
    predictions = forecast.predicted_mean
    future_days = np.arange(last_day + 1, last_day + 101)


    below_threshold = np.where(predictions < moisture_threshold)[0]
    if len(below_threshold) == 0:
        return "Moisture will stay above threshold for the next 10 days."

    predicted_day = future_days[below_threshold[0]][0]
    days_until_watering = predicted_day - X['days'].max()

    # Plot
    plt.scatter(X, y, label='Observed')
    plt.plot(future_days, predictions, color='red', label='Prediction')
    plt.axhline(y=moisture_threshold, color='gray', linestyle='--', label='Threshold')
    plt.axvline(x=predicted_day, color='blue', linestyle='--', label=f'Predicted: {predicted_day:.1f} days')
    plt.xlabel('Days')
    plt.ylabel('Soil Moisture')
    plt.legend()
    plt.title('Soil Moisture Prediction')
    plt.savefig('soil_moisture_prediction.png')
    plt.close()
    print("Saved prediction plot to soil_moisture_prediction.png")

    return f"Watering likely needed in ~{days_until_watering:.1f} days."

# === Main Execution ===

# Discover services
thingspeak_url = get_service_url("ThingSpeak Adaptor")  
device_catalog_url = get_service_url("DeviceCatalog")


# Fetch thresholds and sensor data
thresholds = get_thresholds(device_catalog_url, DEVICE_NAME)
sensor_data = get_thingspeak_data(thingspeak_url, CHANNEL_ID, API_KEY)

# Predict and show results
message = predict_watering_day(sensor_data, thresholds)
print(message)
