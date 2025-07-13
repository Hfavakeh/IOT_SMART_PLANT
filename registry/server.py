import cherrypy
import json
import requests
import time
import sys
import os
import cherrypy_cors 


# Load config
with open("config.json", "r") as f:
    CONFIG = json.load(f)

class ServiceCatalog():
    exposed = True

    def __init__(self):
        pass

    def GET(self, *uri, **params):
        file_path = 'data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)
            services = data.get('services', {})
            return json.dumps(services)
        else:
            cherrypy.response.status = 404
            return "File not found"

    def POST(self, *uri):
        data_to_insert = cherrypy.request.body.read()
        converted_data = json.loads(data_to_insert)
        service_name = converted_data.get('service_name')
        service_url = converted_data.get('service_url')
        data = {'services': []}
        if not service_name or not service_url:
            cherrypy.response.status = 400
            return "Missing service_name or service_url"

        file_path = 'data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)
        else:
            data = {'services': []}

        services = data.get('services', [])

        for service in services:
            if service.get('service_name') == service_name:
                cherrypy.response.status = 409
                return "Service already exists"

        services.append({'service_name': service_name, 'service_url': service_url})
        data['services'] = services

        with open(file_path, 'w') as json_file:
            json.dump(data, json_file)

        cherrypy.response.status = 201
        return "Service added successfully"

    def PUT(self, *uri):
        data_to_update = cherrypy.request.body.read()
        converted_data = json.loads(data_to_update)
        service_name = converted_data.get('service_name')
        service_url = converted_data.get('service_url')
        if not service_name or not service_url:
            cherrypy.response.status = 400
            return "Missing service_name or service_url"

        file_path = 'data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)
        else:
            cherrypy.response.status = 404
            return "File not found"

        services = data.get('services', [])
        for service in services:
            if service.get('service_name') == service_name:
                service['service_url'] = service_url
                with open(file_path, 'w') as json_file:
                    json.dump(data, json_file)
                cherrypy.response.status = 200
                return "Service updated successfully"

        cherrypy.response.status = 404
        return "Service not found"

    def DELETE(self, *uri):
        service_name = uri[0] if len(uri) > 0 else None
        if not service_name:
            cherrypy.response.status = 400
            return "Missing service_name"

        file_path = 'data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)
        else:
            cherrypy.response.status = 404
            return "File not found"

        services = data.get('services', [])
        for service in services:
            if service.get('service_name') == service_name:
                services.remove(service)
                with open(file_path, 'w') as json_file:
                    json.dump(data, json_file)
                cherrypy.response.status = 200
                return "Service deleted successfully"

        cherrypy.response.status = 404
        return "Service not found"

class DeviceCatalog():
    exposed = True

    def __init__(self):
        pass

    def GET(self, *uri, **params):
        file_path = 'data.json'
        if not os.path.exists(file_path):
            cherrypy.response.status = 404
            return "File not found"

        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
        devices = data.get('devices', [])

        # If a specific device_name is requested
        if len(uri) == 1:
            requested_device = uri[0]
            for device in devices:
                if device.get('device_name') == requested_device:
                    return json.dumps(device)
            cherrypy.response.status = 404
            return "Device not found"
    
    # Otherwise return all devices
        return json.dumps(devices)


    def POST(self, *uri):
        data_to_insert = cherrypy.request.body.read()
        converted_data = json.loads(data_to_insert)
        device_name = converted_data.get('device_name')
        device_info = converted_data.get('device_info')
        data = {'devices': []}
        if not device_name or not device_info:
            cherrypy.response.status = 400
            return "Missing device_name or device_info"

        file_path = 'data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)
        else:
            data = {'devices': []}

        devices = data.get('devices', [])

        for device in devices:
            if device.get('device_name') == device_name:
                cherrypy.response.status = 409
                return "Device already exists"

        devices.append({'device_name': device_name, 'device_info': device_info})
        data['devices'] = devices

        with open(file_path, 'w') as json_file:
            json.dump(data, json_file)

        cherrypy.response.status = 201
        return "Device added successfully"

    def PUT(self, *uri):
        data_to_update = cherrypy.request.body.read()
        print(data_to_update)
        converted_data = json.loads(data_to_update)
        device_name = converted_data.get('device_name')
        device_info = converted_data.get('device_info')
        if not device_name or not device_info:
            cherrypy.response.status = 400
            return "Missing device_name or device_info"

        file_path = 'data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)
        else:
            cherrypy.response.status = 404
            return "File not found"

        devices = data.get('devices', [])
        for device in devices:
            if device.get('device_name') == device_name:
                device['device_info'] = device_info
                with open(file_path, 'w') as json_file:
                    json.dump(data, json_file)
                cherrypy.response.status = 200
                return "Device updated successfully"

        cherrypy.response.status = 404
        return "Device not found"

    def DELETE(self, *uri):
        device_name = uri[0] if len(uri) > 0 else None
        if not device_name:
            cherrypy.response.status = 400
            return "Missing device_name"

        file_path = 'data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)
        else:
            cherrypy.response.status = 404
            return "File not found"

        devices = data.get('devices', [])
        for device in devices:
            if device.get('device_name') == device_name:
                devices.remove(device)
                with open(file_path, 'w') as json_file:
                    json.dump(data, json_file)
                cherrypy.response.status = 200
                return "Device deleted successfully"

        cherrypy.response.status = 404
        return "Device not found"

class TelegramUsers():
    exposed = True

    def __init__(self):
        pass

    def GET(self, *uri, **params):
        file_path = 'data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)
            if 'telegram_users' not in data:
                data['telegram_users'] = []
                with open(file_path, 'w') as json_file:
                    json.dump(data, json_file)
            telegram_users = data.get('telegram_users', [])
            chat_id = params.get('chat_id')
            user_name = params.get('user_name')

            if chat_id:
                telegram_users = [user for user in telegram_users if user.get('chat_id') == chat_id]
            if user_name:
                telegram_users = [user for user in telegram_users if user.get('user_name') == user_name]

            return json.dumps(telegram_users)
        else:
            cherrypy.response.status = 404
            return "File not found"

    def POST(self, *uri):
        data_to_insert = cherrypy.request.body.read()
        converted_data = json.loads(data_to_insert)
        chat_id = converted_data.get('chat_id')
        user_name = converted_data.get('user_name')
        devices = converted_data.get('devices', [])
        
        if not chat_id or not user_name:
            cherrypy.response.status = 400
            return "Missing chat_id or user_name"

        file_path = 'data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)
        else:
            data = {'telegram_users': []}

        telegram_users = data.get('telegram_users', [])

        for user in telegram_users:
            if user.get('chat_id') == chat_id or user.get('user_name') == user_name:
                cherrypy.response.status = 409
                return "User already exists"

        telegram_users.append({'chat_id': chat_id, 'user_name': user_name, 'devices': devices})
        data['telegram_users'] = telegram_users

        with open(file_path, 'w') as json_file:
            json.dump(data, json_file)

        cherrypy.response.status = 201
        return "User added successfully"

    def PUT(self, *uri):
        data_to_update = cherrypy.request.body.read()
        converted_data = json.loads(data_to_update)
        chat_id = converted_data.get('chat_id')
        user_name = converted_data.get('user_name')
        devices = converted_data.get('devices', [])

        if not chat_id or not user_name or not devices:
            cherrypy.response.status = 400
            return "Missing chat_id, user_name or devices"

        file_path = 'data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)
        else:
            cherrypy.response.status = 404
            return "File not found"

        telegram_users = data.get('telegram_users', [])
        user_found = False
        for user in telegram_users:
            if user.get('chat_id') == chat_id or user.get('user_name') == user_name:
                for device in devices:
                    device_id = device.get('device_id')
                    device_name = device.get('device_name')
                    if not device_id or not device_name:
                        cherrypy.response.status = 400
                        return "Missing device_id or device_name"
                    if device not in user['devices']:
                        user['devices'].append(device)
                user_found = True
                break

        if not user_found:
            cherrypy.response.status = 404
            return "User not found"

        data['telegram_users'] = telegram_users

        with open(file_path, 'w') as json_file:
            json.dump(data, json_file)

        cherrypy.response.status = 200
        return "Devices added to user successfully"
    
    def DELETE(self, *uri):
        if len(uri) < 2:
            cherrypy.response.status = 400
            return "Missing chat_id or user_name"

        chat_id = uri[0]
        user_name = uri[1]

        file_path = 'data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                data = json.load(json_file)
        else:
            cherrypy.response.status = 404
            return "File not found"

        telegram_users = data.get('telegram_users', [])
        user_found = False
        for user in telegram_users:
            if user.get('chat_id') == chat_id or user.get('user_name') == user_name:
                telegram_users.remove(user)
                user_found = True
                break

        if not user_found:
            cherrypy.response.status = 404
            return "User not found"

        data['telegram_users'] = telegram_users

        with open(file_path, 'w') as json_file:
            json.dump(data, json_file)

        cherrypy.response.status = 200
        return "User deleted successfully"

def add_default_service():
    service_name = "broker_address"
    service_url = os.getenv('BROKER_ADDRESS', 'localhost')

    file_path = 'data.json'
    if os.path.exists(file_path):
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
    else:
        data = {'services': [],'devices': [],'telegram_users': []}

    services = data.get('services', [])
    for service in services:
        if service.get('service_name') == service_name:
            service['service_url'] = service_url
            break
    for default_service in [
        {'service_name': service_name, 'service_url': service_url},
        {'service_name': 'SENSORS_TOPIC', 'service_url': "plant_care/sensors"},
        {'service_name': 'ALARMS_TOPIC', 'service_url': "plant_care/alarms"},
        {'service_name': 'CONTROL_TOPIC', 'service_url': "sensor/control"},
        {'service_name': 'DeviceCatalog', 'service_url': CONFIG['service_info']["service_url"]}
    ]:
        existing_service = next((s for s in services if s['service_name'] == default_service['service_name']), None)
        if existing_service:
            existing_service['service_url'] = default_service['service_url']
        else:
            services.append(default_service)
            
    data['services'] = services

    with open(file_path, 'w') as json_file:
        json.dump(data, json_file)

    return "Default service added successfully"
        
        
def CORS():
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
if __name__ == '__main__':
    
    try:
        add_default_service()
    except:
        pass

    try:
        if os.environ['IP_ADDRESS'] == None:
            os.environ['IP_ADDRESS'] = "0.0.0.0"
    except:
        os.environ['IP_ADDRESS'] = "0.0.0.0"
    try:
        if os.environ['IP_PORT'] == None:
            os.environ['IP_PORT'] = "8080"
    except:
        os.environ['IP_PORT'] = "8080"
    try:
        if os.environ['environment'] == None:
            os.environ['environment'] = 'debugging'
    except:
        os.environ['environment'] = 'debugging' 

    relational_database_dal_service = ServiceCatalog()
    cherrypy_cors.install()
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'cors.expose.on': True,
        }
    }

    cherrypy.tree.mount(TelegramUsers(), '/' + type(TelegramUsers()).__name__, conf)
    cherrypy.tree.mount(ServiceCatalog(), '/' + type(ServiceCatalog()).__name__, conf)
    cherrypy.tree.mount(DeviceCatalog(), '/' + type(DeviceCatalog()).__name__, conf)
    print("current server addresss: ",os.environ['IP_ADDRESS'],os.environ['IP_ADDRESS'])
    cherrypy.config.update({'server.socket_host': os.environ['IP_ADDRESS']})
    cherrypy.config.update({'server.socket_port': int(os.environ['IP_PORT'])})
    cherrypy.engine.start()
    #while True:
    #    time.sleep(1)
    cherrypy.engine.block()