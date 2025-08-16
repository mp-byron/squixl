import asyncio
from mqtt_as import MQTTClient, config
import network
from secrets import SERVER, SSID, PW

# mqtt server
config['server'] = SERVER  
# WiFi
config['ssid'] = SSID
config['wifi_pw'] = PW


# list of mqtt topics to subscrib to
subscription_list = []


# variable to hold the number of wifi of mqtt outages in this session.
# only normall of interest if the board is used on the outer ranges of
# wifi coverage.
outages = 0

# ------------------------------------------------------
# mqtt messages received
# set in calling code
#e.g.
"""
async def messages(client):  # Respond to incoming messages
    async for topic, msg, retained in client.queue:
        msg = msg.decode()
        print(msg)
"""
# ------------------------------------------------------
# set in calling code
# publish mqtt messages
# e.g
"""
async def publish(client, topic, msg):
    await client.publish(topic, msg)        
"""
#-------------------------------------------------------------



#-----------------------------------------------------------
# mqtt connection and subscribing to subsciptions

async def up(client):  # Respond to connectivity being (re)established
    while True:
        await client.up.wait()  # Wait on an Event
        client.up.clear()
        #await wifi_led(True)
        print('subribing topics to broker.')
        for item in subscription_list:
            await client.subscribe(item, 0)  
               
        
async def down(client):
    global outages
    while True:
        await client.down.wait()  # Pause until connectivity changes
        client.down.clear()
        #await wifi_led(False)
        outages += 1 # record the outage occurance. 
        print('WiFi or broker is down. Trying to reconnect')
        
        
#-------------------------------------------------------------


# ***********************************************************

def wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(SSID, PW)
        while not wlan.isconnected():
            pass
    print('network connected:')




