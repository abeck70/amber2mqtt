"""MQTT functions for Subscribing and publishing to MQTT"""

import json
import os
from paho.mqtt import client as mqtt_client
import mqttmessages as mm
from const import (
    AMBER_DEVICE_ID,
    AMBER_FORECAST_DEVICE_ID,
    AEMO_DEVICE_ID,
    AMBER_DISCOVERY_TOPIC,
    AMBER_FORECAST_DISCOVERY_TOPIC,
    AEMO_DISCOVERY_TOPIC,
    AMBER_STATE_TOPIC_CURRENT,
    AMBER_STATE_TOPIC_PERIODS,
    AMBER_STATE_TOPIC_5MIN_FORECASTS,
    AMBER_STATE_TOPIC_30MIN_FORECASTS,
    AMBER_STATE_TOPIC_USER_FORECASTS,
    AMBER_STATE_TOPIC_5MIN_EXTENDED_FORECASTS,
    AMBER_MQTT_PREFIX,
    SENSOR_LIST_CURRENT,
    AEMO_STATE_TOPIC_CURRENT,
)

#if os.path.isfile("options.json"):
#    with open("options.json", "r") as f:
#        config = json.load(f)

if os.path.isfile("/data/options.json"):
    with open("/data/options.json", "r") as f:
        config = json.load(f)
else: 
    with open("./data/options.json", "r") as f:
        config = json.load(f)

# amberSiteId = config["amber"]["site_id"]
username = None
password = None
broker = config["mqtt"]["broker"]
port = config["mqtt"]["port"]
client_id = config["mqtt"]["client_id"]
for key in config["mqtt"]:
    if key == "username":
        username = config["mqtt"]["username"]
    if key == "password":
        password = config["mqtt"]["password"]

amber5minForecast = False
amber30minForecast = False
amberUserForecast = False
amber288Forecast = False
for key in config["amber"]:
    if key == "forecast5min":
        amber5minForecast = True if config["amber"]["forecast5min"].lower() == "true" else False
    if key == "forecast30min":
        amber30minForecast = True if config["amber"]["forecast30min"].lower() == "true" else False
    if key == "forecastUser":
        amberUserForecast = True if config["amber"]["forecastUser"].lower() == "true" else False
    if key == "forecast288":
        amber288Forecast = True if config["amber"]["forecast288"].lower() == "true" else False  
if amber288Forecast:
    amber5minForecast = True
    amber30minForecast = True
def mqttConnectBroker():
    """Connect to the MQTT Broker"""
    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    def on_subscribe(client, userdata, mid, reason_code_list, properties):
        # Since we subscribed only for a single channel, reason_code_list contains
        # a single entry
        if reason_code_list[0].is_failure:
            print(f"Broker rejected you subscription: {reason_code_list[0]}")
        else:
            print(f"Broker granted the following QoS: {reason_code_list[0].value}")

    def on_message(client, userdata, message):
        # userdata is the structure we choose to provide, here it's a list()
        userdata = message.payload
        print(userdata)
        if userdata == b"online":
            amber5minForecast = False
            amber30minForecast = False
            amberUserForecast = False
            amber288Forecast = True
            for key in config["amber"]:
                if key == "forecast5min":
                    amber5minForecast = True if config["amber"]["forecast5min"].lower() == "true" else False
                if key == "forecast30min":
                    amber30minForecast = True if config["amber"]["forecast30min"].lower() == "true" else False
                if key == "forecastUser":
                    amberUserForecast = True if config["amber"]["forecastUser"].lower() == "true" else False
                if key == "forecast288":
                    amber288Forecast = True if config["amber"]["forecast288"].lower() == "true" else False
            if amber288Forecast == True:
                amber5minForecast = True
                amber30minForecast = True
            PublishDiscoveryAmberEntities(client)
            PublishDiscoveryAemoEntities(client)
            PublishDiscoveryAmberForecastEntities(client,amber5minForecast,amber30minForecast,amberUserForecast,amber288Forecast)
        # We only want to process 10 messages
        # if len(userdata) >= 10:
        #    client.unsubscribe("$SYS/#")

    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
    if username not in (None, ""):
        client.username_pw_set(username, password)
    # client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.connect(broker, port)
    return client


def PublishDiscoveryAmberEntities(client):
    """Publish the Amber Entities to Home Assistant using standard discovery format"""
    # Clear old discovery message format (if it exists)
    try:
        client.publish(AMBER_DISCOVERY_TOPIC, "", qos=0, retain=True)
    except:
        pass
    
    entities = mm.amberDiscoveryMessage()
    for entity in entities:
        # Standard Home Assistant discovery topic: homeassistant/sensor/<node_id>/<object_id>/config
        # Use object_id from entity if available, otherwise use unique_id
        object_id = entity.get('object_id', entity['unique_id'].replace(f"{AMBER_DEVICE_ID}_", ""))
        topic = f"homeassistant/sensor/{AMBER_DEVICE_ID}/{object_id}/config"
        # Remove object_id from payload (it's only for topic construction)
        payload = {k: v for k, v in entity.items() if k != 'object_id'}
        result = client.publish(topic, json.dumps(payload), qos=0, retain=True)
        status = result[0]
        if status != 0:
            print(f"Failed to send message to topic {topic}")

def PublishDiscoveryAmberForecastEntities(client,forecast5,forecast30,forecastUser,forecast288):
    """Publish all enabled Amber Forecast entities using standard discovery format"""
    # Clear old discovery message format (if it exists)
    try:
        client.publish(AMBER_FORECAST_DISCOVERY_TOPIC, "", qos=0, retain=True)
    except:
        pass
    
    entities = []
    if forecast5:
        entities.extend(mm.amberForecast5minDiscoveryMessage())
    if forecast30:
        entities.extend(mm.amberForecast30minDiscoveryMessage())
    if forecastUser:
        entities.extend(mm.amberForecastUserDiscoveryMessage())
    if forecast288:
        entities.extend(mm.amberForecast288DiscoveryMessage())
    
    for entity in entities:
        # Standard Home Assistant discovery topic: homeassistant/sensor/<node_id>/<object_id>/config
        # Use object_id from entity if available, otherwise use unique_id
        object_id = entity.get('object_id', entity['unique_id'].replace(f"{AMBER_FORECAST_DEVICE_ID}_", ""))
        topic = f"homeassistant/sensor/{AMBER_FORECAST_DEVICE_ID}/{object_id}/config"
        # Remove object_id from payload (it's only for topic construction)
        payload = {k: v for k, v in entity.items() if k != 'object_id'}
        result = client.publish(topic, json.dumps(payload), qos=0, retain=True)
        status = result[0]
        if status != 0:
            print(f"Failed to send message to topic {topic}")

def PublishDiscoveryAemoEntities(client):
    """Publish the AEMO Entities to Home Assistant using standard discovery format"""
    # Clear old discovery message format (if it exists)
    try:
        client.publish(AEMO_DISCOVERY_TOPIC, "", qos=0, retain=True)
    except:
        pass
    
    entities = mm.aemoDiscoveryMessage()
    for entity in entities:
        # Standard Home Assistant discovery topic: homeassistant/sensor/<node_id>/<object_id>/config
        # Use object_id from entity if available, otherwise use unique_id
        object_id = entity.get('object_id', entity['unique_id'].replace(f"{AEMO_DEVICE_ID}_", ""))
        topic = f"homeassistant/sensor/{AEMO_DEVICE_ID}/{object_id}/config"
        # Remove object_id from payload (it's only for topic construction)
        payload = {k: v for k, v in entity.items() if k != 'object_id'}
        result = client.publish(topic, json.dumps(payload), qos=0, retain=True)
        status = result[0]
        if status != 0:
            print(f"Failed to send message to topic {topic}")


def publishAmberStateCurrent(client, amberdata):
    """Publish the current Amber state to MQTT"""
    messageContent = mm.amberStateMessage(amberdata)
    # print(json.dumps(messageContent["state"]))
    result = client.publish(
        AMBER_STATE_TOPIC_CURRENT,
        json.dumps(messageContent["state"]),
        qos=0,
        retain=True,
    )
    status = result[0]
    if status != 0:
        print(f"Failed to send message to topic {AMBER_STATE_TOPIC_CURRENT}")
    # discoveryMsg = mm.amberDiscoveryMessage()
    # print(json.dumps(messageContent["attributes"]))
    for sensor in SENSOR_LIST_CURRENT:
        topic = f"{AMBER_MQTT_PREFIX}/{sensor.lower().replace(' ', '_')}/attributes"
        result = client.publish(
            topic, json.dumps(messageContent["attributes"]), qos=0, retain=True
        )
        status = result[0]
        if status != 0:
            print(f"Failed to send message to topic {topic}")


def publishAmberStatePeriods(client, amberdata):
    """Publish the Amber state to MQTT for the 12 periods"""
    messageContent = mm.amberState5MinPeriods(amberdata)
    # print(json.dumps(messageContent["state"]))
    result = client.publish(
        AMBER_STATE_TOPIC_PERIODS,
        json.dumps(messageContent["state"]),
        qos=0,
        retain=True,
    )
    status = result[0]
    if status != 0:
        print(f"Failed to send message to topic {AMBER_STATE_TOPIC_PERIODS}")
    for attributemsg in messageContent["attributes"]:
        topic = f"{AMBER_MQTT_PREFIX}/{attributemsg}/attributes"
        # test = json.dumps(messageContent["attributes"][attributemsg])
        result = client.publish(
            topic,
            json.dumps(messageContent["attributes"][attributemsg]),
            qos=0,
            retain=True,
        )
        status = result[0]
        if status != 0:
            print(f"Failed to send message to topic {topic}")

def publishAmberState5MinForecasts(client, amberdata):
    """Publish the Amber state to MQTT for the 12 periods"""
    messageContent = mm.amberState5MinForecasts(amberdata)
    # print(json.dumps(messageContent["state"]))
    result = client.publish(
        AMBER_STATE_TOPIC_5MIN_FORECASTS,
        json.dumps(messageContent["state"]),
        qos=0,
        retain=True,
    )
    status = result[0]
    if status != 0:
        print(f"Failed to send message to topic {AMBER_STATE_TOPIC_5MIN_FORECASTS}")
    for attributemsg in messageContent["attributes"]:
        topic = f"{AMBER_MQTT_PREFIX}/{attributemsg}/attributes"
        # test = json.dumps(messageContent["attributes"][attributemsg])
        result = client.publish(
            topic,
            json.dumps(messageContent["attributes"][attributemsg]),
            qos=0,
            retain=True,
        )
        status = result[0]
        if status != 0:
            print(f"Failed to send message to topic {topic}")

def publishAmberState5MinExtendedForecasts(client, amberdata):
    """Publish the Amber state to MQTT for the 12 periods"""
    messageContent = mm.amberState5MinExtendedForecasts(amberdata)
    # print(json.dumps(messageContent["state"]))
    result = client.publish(
        AMBER_STATE_TOPIC_5MIN_EXTENDED_FORECASTS,
        json.dumps(messageContent["state"]),
        qos=0,
        retain=True,
    )
    status = result[0]
    if status != 0:
        print(f"Failed to send message to topic {AMBER_STATE_TOPIC_5MIN_FORECASTS}")
    for attributemsg in messageContent["attributes"]:
        topic = f"{AMBER_MQTT_PREFIX}/{attributemsg}/attributes"
        # test = json.dumps(messageContent["attributes"][attributemsg])
        result = client.publish(
            topic,
            json.dumps(messageContent["attributes"][attributemsg]),
            qos=0,
            retain=True,
        )
        status = result[0]
        if status != 0:
            print(f"Failed to send message to topic {topic}")

            
def publishAmberState30MinForecasts(client, amberdata):
    """Publish the Amber state to MQTT for the 12 periods"""
    messageContent = mm.amberState30MinForecasts(amberdata)
    # print(json.dumps(messageContent["state"]))
    result = client.publish(
        AMBER_STATE_TOPIC_30MIN_FORECASTS,
        json.dumps(messageContent["state"]),
        qos=0,
        retain=True,
    )
    status = result[0]
    if status != 0:
        print(f"Failed to send message to topic {AMBER_STATE_TOPIC_30MIN_FORECASTS}")
    for attributemsg in messageContent["attributes"]:
        topic = f"{AMBER_MQTT_PREFIX}/{attributemsg}/attributes"
        # test = json.dumps(messageContent["attributes"][attributemsg])
        result = client.publish(
            topic,
            json.dumps(messageContent["attributes"][attributemsg]),
            qos=0,
            retain=True,
        )
        status = result[0]
        if status != 0:
            print(f"Failed to send message to topic {topic}")
            
def publishAmberStateUserForecasts(client, amberdata):
    """Publish the Amber state to MQTT for the 12 periods"""
    messageContent = mm.amberStateUserForecasts(amberdata)
    # print(json.dumps(messageContent["state"]))
    result = client.publish(
        AMBER_STATE_TOPIC_USER_FORECASTS,
        json.dumps(messageContent["state"]),
        qos=0,
        retain=True,
    )
    status = result[0]
    if status != 0:
        print(f"Failed to send message to topic {AMBER_STATE_TOPIC_USER_FORECASTS}")
    for attributemsg in messageContent["attributes"]:
        topic = f"{AMBER_MQTT_PREFIX}/{attributemsg}/attributes"
        # test = json.dumps(messageContent["attributes"][attributemsg])
        result = client.publish(
            topic,
            json.dumps(messageContent["attributes"][attributemsg]),
            qos=0,
            retain=True,
        )
        status = result[0]
        if status != 0:
            print(f"Failed to send message to topic {topic}")

def publishAemoStateCurrent(client, aemoData):
    """Publish the AEMO state to MQTT"""
    messageContent = mm.aemoCurrentStateMessage(aemoData)
    result = client.publish(
        AEMO_STATE_TOPIC_CURRENT,
        json.dumps(messageContent["state"]),
        qos=0,
        retain=True,
    )
    status = result[0]
    if status != 0:
        print(f"Failed to send message to topic {AMBER_STATE_TOPIC_CURRENT}")
    for attributeMsg in messageContent["attributes"]:
        topic = f"{AMBER_MQTT_PREFIX}/{attributeMsg}/attributes"
        result = client.publish(
            topic,
            json.dumps(messageContent["attributes"][attributeMsg]),
            qos=0,
            retain=True,
        )
        status = result[0]
        if status != 0:
            print(f"Failed to send message to topic {topic}")


# if __name__ == '__main__':
#    run()
