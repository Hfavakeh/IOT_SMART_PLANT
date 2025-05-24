import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
import json
import requests
import time
from MyMQTT import *
import ssl
import os

from dotenv import load_dotenv
load_dotenv()

ssl._create_default_https_context = ssl._create_unverified_context

class TestNotifier:
    def __init__(self, bot, alarm_topic, emergency_topic, users_file):
        self.bot = bot
        self.alarm_topic = alarm_topic
        self.emergency_topic = emergency_topic
        self.users_file = users_file

    def get_chatIDs_by_productID(self, product_ID):
        with open(self.users_file, 'r') as file:
            data = json.load(file)
        
        chatIDs = []
        for item in data["data"]:
            if item["product_ID"] == product_ID:
                chatIDs.append(item["chat_ID"])
        return chatIDs
    
    def notify(self, topic, message):
        try:
            print(f"Received message on topic {topic}: {message.decode()}")
            if topic == self.alarm_topic:
                message_json = json.loads(message.decode())
                device_id = message_json["device_id"]
                alert_text = message_json.get("message", "No details provided.")

                formatted_message = (
                    f"🚨 *Plant Alert(Future as Predicted)!*\n\n"
                    f"🪴 *Plant ID:* `{device_id}`\n"
                    f"⚠️ *Alert:* {alert_text}"
                )

                with open(self.users_file, 'r') as file:
                    data = json.load(file)

                for item in data["data"]:
                    if item["product_ID"] == device_id and item.get("alarm_permission", True):
                        self.bot.sendMessage(item["chat_ID"], text=formatted_message)
            
            elif topic == self.emergency_topic:
                message_json = json.loads(message.decode())
                device_id = message_json["device_id"]
                alert_text = message_json.get("message", "No details provided.")

                formatted_message = (
                    f"🚨 *Emergency Alert!*\n\n"
                    f"🪴 *Plant ID:* `{device_id}`\n"
                    f"⚠️ *Alert:* {alert_text}"
                )

                with open(self.users_file, 'r') as file:
                    data = json.load(file)

                for item in data["data"]:
                    if item["product_ID"] == device_id and item.get("alarm_permission", True):
                        self.bot.sendMessage(item["chat_ID"], text=formatted_message, parse_mode="Markdown")

        except Exception as e:
            print(f"Error in notify(): {e}")
            

class PlantBot:
    def __init__(self, token, broker, alarm_topic, emergency_topic, users_file):
        self.tokenBot = token
        self.bot = telepot.Bot(self.tokenBot)
        self.alarm_topic = alarm_topic
        self.emergency_topic = emergency_topic
        self.users_file = users_file
        MessageLoop(self.bot, {'chat': self.on_chat_message, 'callback_query': self.on_callback_query}).run_as_thread()
        self.client = MyMQTT("PlantBotClient", broker, 1883, TestNotifier(self.bot, self.alarm_topic, self.emergency_topic, self.users_file))
        self.client.start()
        self.client.mySubscribe(self.alarm_topic)
        self.client.mySubscribe(self.emergency_topic)
                
    def on_chat_message(self, msg):
        content_type, chat_type, chat_ID = telepot.glance(msg)
        message = msg['text']

        main_menu = ReplyKeyboardMarkup(
            keyboard=[
                ['🌿 My Plants', '➕ Add Plant'],
                ['📩 Contact Developer']
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )

        if message == "/start":
            if self.is_user_exist(chat_ID):
                self.get_products(chat_ID)
                self.bot.sendMessage(chat_ID, text="Choose an option from the keyboard below or send a Product ID and Name to register your plant:\n\nExample: `Raspberry Pi 1, Aloe Vera`", reply_markup=main_menu)
            else:
                self.bot.sendMessage(chat_ID, text="🌱 Welcome to MyPlant Bot!\n\nSend a Product ID and Name to register your plant:\n\nExample: `Raspberry Pi 1, Aloe Vera`", reply_markup=main_menu)

        elif message == "🌿 My Plants":
            self.get_products(chat_ID)

        elif message == "➕ Add Plant":
            self.bot.sendMessage(chat_ID, text="Send a Product ID and Name to register your plant:\n\nExample: `Raspberry Pi 1, Aloe Vera`")

        elif message == "📩 Contact Developer":
            dev_button = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Message @merirad96", url="https://t.me/merirad96")]
            ])
            self.bot.sendMessage(chat_ID, text="Need help? Contact the developer:", reply_markup=dev_button)

        elif "," in message:
            try:
                parts = [part.strip() for part in message.split(",")]
                if len(parts) != 2:
                    raise ValueError("Incorrect format")

                plant_id, plant_name = parts
                self.add_plant(chat_ID, plant_id.strip(), plant_name.strip())
            except ValueError:
                self.bot.sendMessage(chat_ID, text="⚠️ Incorrect format! Please use the format: `Raspberry Pi 1, MyPlant` with a comma and space separating the ID and name.")
            except Exception as e:
                print(f"Error processing the plant add message: {e}")
                self.bot.sendMessage(chat_ID, text="⚠️ Something went wrong. Please try again.")
        else:
            self.bot.sendMessage(chat_ID, text="Command not supported. Please use the menu buttons or /start.")

    def on_callback_query(self, msg):
        query_ID, chat_ID, query_data = telepot.glance(msg, flavor='callback_query')
        action, plant_id = query_data.split('|')

        if action == "delete":
            self.delete_plant(chat_ID, plant_id)

        elif action == "edit":
            self.bot.sendMessage(chat_ID, text=f"✏️ To rename plant `{plant_id}`, send:\n`{plant_id}, NewName`", parse_mode="Markdown")

        elif action == "setting":
            self.show_settings(chat_ID, plant_id)

        elif action in ["alarm_on", "alarm_off"]:
            state = True if action == "alarm_on" else False
            self.update_alarm_setting(chat_ID, plant_id, state)

        elif action == "check_status":
            with open(self.users_file, 'r') as file:
                data = json.load(file)

            plant_name = plant_id
            for item in data["data"]:
                if item["chat_ID"] == chat_ID and item["product_ID"] == plant_id:
                    plant_name = item.get("product_name", plant_id)
                    break

            thingspeak_URL = fetch_service_config("ThingSpeak Adaptor")
            try:
                response = requests.get(thingspeak_URL + "/data" + "/" + plant_id)
                if response.status_code == 200:
                    data = response.json()
                    status = data[-1]
                    message = (
                        f"🌿 *{plant_name}*\n\n"
                        f"📅 Timestamp: {status['timestamp']}\n"
                        f"🌡️ Temperature: {status['temperature']}°C\n"
                        f"💡 Light: {status['light']} lx\n"
                        f"🌱 Soil Moisture: {status['soil_moisture']}%"
                    )

                    self.bot.sendMessage(chat_ID, text=message, parse_mode="Markdown")
                else:
                    self.bot.sendMessage(chat_ID, text="⚠️ Failed to fetch plant data. Please try again later.")
            except Exception as e:
                print(f"Error in check_status: {e}")
                self.bot.sendMessage(chat_ID, text="⚠️ Error while fetching status.")

    def is_user_exist(self, chat_id):
        with open(self.users_file, 'r') as file:
            data = json.load(file)
        return any(entry["chat_ID"] == chat_id for entry in data["data"])

    def add_plant(self, chat_ID, plant_id, plant_name):
        with open(self.users_file, 'r') as file:
            data = json.load(file)

        for item in data["data"]:
            if item["chat_ID"] == chat_ID and item["product_ID"] == plant_id:
                item["product_name"] = plant_name
                with open(self.users_file, 'w') as file:
                    json.dump(data, file, indent=4)
                self.bot.sendMessage(chat_ID, text=f"✏️ Plant name updated to **{plant_name}** (ID: {plant_id})", parse_mode="Markdown")
                return

        data["data"].append({
            "chat_ID": chat_ID,
            "product_ID": plant_id,
            "product_name": plant_name,
            "alarm_permission": True
        })

        with open(self.users_file, 'w') as file:
            json.dump(data, file, indent=4)

        self.bot.sendMessage(chat_ID, text=f"✅ Plant **{plant_name}** (ID: {plant_id}) added successfully!", parse_mode="Markdown")

    def delete_plant(self, chat_ID, plant_id):
        with open(self.users_file, 'r') as file:
            data = json.load(file)

        original_len = len(data["data"])
        data["data"] = [entry for entry in data["data"] if not (entry["chat_ID"] == chat_ID and entry["product_ID"] == plant_id)]

        if len(data["data"]) < original_len:
            with open(self.users_file, 'w') as file:
                json.dump(data, file, indent=4)
            self.bot.sendMessage(chat_ID, text=f"🗑 Plant with ID `{plant_id}` has been deleted.", parse_mode="Markdown")
        else:
            self.bot.sendMessage(chat_ID, text="⚠️ Plant not found.")

    def get_products(self, chat_ID):
        with open(self.users_file, 'r') as file:
            data = json.load(file)

        user_plants = [item for item in data["data"] if item["chat_ID"] == chat_ID]

        if not user_plants:
            self.bot.sendMessage(chat_ID, text="🌱 You have no plants registered.\n\nSend a Product ID and Name to add one:\nExample: `Raspberry Pi 1, Aloe Vera`")
            return

        for item in user_plants:
            buttons = [
                [InlineKeyboardButton(text='Check Status 📊', callback_data=f'check_status|{item["product_ID"]}')],
                [
                    InlineKeyboardButton(text='✏️ Edit', callback_data=f'edit|{item["product_ID"]}'),
                    InlineKeyboardButton(text='🗑 Delete', callback_data=f'delete|{item["product_ID"]}'),
                    InlineKeyboardButton(text='⚙️ Setting', callback_data=f'setting|{item["product_ID"]}')
                ]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            self.bot.sendMessage(chat_ID, text=f"Plant ID: {item['product_ID']}\nPlant Name: {item['product_name']}", reply_markup=keyboard)

    def show_settings(self, chat_ID, plant_id):
        with open(self.users_file, 'r') as file:
            data = json.load(file)

        for item in data["data"]:
            if item["chat_ID"] == chat_ID and item["product_ID"] == plant_id:
                current_status = "ON ✅" if item.get("alarm_permission", True) else "OFF ❌"
                buttons = [
                    [
                        InlineKeyboardButton(text='🔔 Turn ON', callback_data=f'alarm_on|{plant_id}'),
                        InlineKeyboardButton(text='🔕 Turn OFF', callback_data=f'alarm_off|{plant_id}')
                    ]
                ]
                self.bot.sendMessage(chat_ID, text=f"🔧 Alarm notifications for `{plant_id}` are currently: **{current_status}**\n\nChoose an option below:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
                return

    def update_alarm_setting(self, chat_ID, plant_id, state):
        with open(self.users_file, 'r') as file:
            data = json.load(file)

        for item in data["data"]:
            if item["chat_ID"] == chat_ID and item["product_ID"] == plant_id:
                item["alarm_permission"] = state
                with open(self.users_file, 'w') as file:
                    json.dump(data, file, indent=4)
                status_str = "ON ✅" if state else "OFF ❌"
                self.bot.sendMessage(chat_ID, text=f"🔔 Alarm notification for `{plant_id}` is now: **{status_str}**", parse_mode="Markdown")
                return


def fetch_service_config(service_name):
    response = requests.get(service_catalogue_URL)
    response.raise_for_status()
    services = response.json()

    service_url = None
    for service in services:
        if service.get("service_name") == service_name:
            service_url = service.get("service_url")
        
    return service_url

if __name__ == "__main__":
    configuration = json.load(open('settings.json'))
    service_catalogue_URL = configuration['service_catalogue_URL']
    token_bot = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token_bot:
        raise EnvironmentError("TELEGRAM_BOT_TOKEN environment variable not set.")

    users_path = configuration['users_file']
    BROKER = fetch_service_config("broker_address")
    Alarm_Topic = fetch_service_config("ALARMS_TOPIC")
    Emergancy_Topic = fetch_service_config("CONTROL_TOPIC")
    plantbot = PlantBot(token_bot, BROKER, Alarm_Topic, Emergancy_Topic, users_path)

    while True:
        time.sleep(3)
