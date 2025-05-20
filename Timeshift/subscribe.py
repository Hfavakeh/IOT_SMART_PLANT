import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    print("Connected to broker.")
    client.subscribe("plant_care/alarms")  # یا هر تاپیکی که استفاده می‌کنی

def on_message(client, userdata, msg):
    print(f"[ALARM RECEIVED] Topic: {msg.topic} → Message: {msg.payload.decode()}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost")  # یا آدرس بروکر MQTT
client.loop_forever()