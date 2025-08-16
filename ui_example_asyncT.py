# Section 1 - imports *******************************
import framebuf, gc
import squixl
import time
from time import ticks_ms, ticks_diff
from time import sleep_ms
import math
from writer import CWriter

from colors import *

import mqtt_ui as mqtt
import asyncio
import network
from secrets import SERVER, SSID, PW

# import fonts
from fonts import robotomono_light_16
from fonts import robotomono_bold_18
from fonts import robotomono_bold_22
from fonts import robotomono_bold_24

from fonts import courier20

from squixl_ui_EX import ( UIManager, UILabel, UITextBox, UITextOnly, UIButton,
    UISlider, UICheckBox, UIProgressBar,UIDial, TouchEvent, TOUCH_TAP, TOUCH_DRAG,
    TOUCH_DRAG_END, rgb_to_565, WriterDevice,
    ALIGNMENT_LEFT, ALIGNMENT_CENTER, ALIGNMENT_RIGHT )

gc.collect()


# Section 2 - set up squixl and fonts ***************************

# Create the display and get the screen buffer
buf = squixl.create_display()

# Bit bang the screen initialisation
squixl.screen_init_spi_bitbanged()

# Create a framebuf from the screen buffer
fb = framebuf.FrameBuffer(buf, 480, 480, framebuf.RGB565)

# Create a CWrite device for the screen using the same framebuf so we can have custom fonts
wbuf = WriterDevice(fb)
gc.collect()

font_light_16 = CWriter(wbuf, robotomono_light_16, fgcolor=WHITE, verbose=False)
font_bold_18 = CWriter(wbuf, robotomono_bold_18, fgcolor=WHITE, verbose=False)
font_bold_22 = CWriter(wbuf, robotomono_bold_22, fgcolor=WHITE, verbose=False)
font_bold_24 = CWriter(wbuf, robotomono_bold_24, fgcolor=WHITE, verbose=False)
font_courier20 = CWriter(wbuf, courier20, fgcolor=WHITE, verbose=False)

# Create the UI manager and pass it the CWrite buffer to enable custom fonts
# set Robotomono_Light_16 font as a default font.
mgr = UIManager(wbuf, font_light_16)

# Section 3 - create the logical screens *****************************
# create a screen called 'startup' used to show status
# of the initial connection to wifi and the mqtt broker
mgr.add_screen('startup', BLUE)

# create a screen called 'home'
# and set the default background screen colour to GREY
mgr.add_screen('home', GREY)

# create a screen called 'w_data'
# and set the default background screen colour to LIGHTGREY
mgr.add_screen('w_data', LIGHTGREY)

# set the initial screen
mgr.set_screen('startup')


# Section 4 - add widgets and controls to the screens *******************

# startup screen.


# 4.1 - for screen startup

prog_lbl = UILabel(20, 10, 440, 0, 'Demo Program', text_color=PINK)
prog_lbl.set_font(font_bold_22)
prog_lbl.align = ALIGNMENT_CENTER
mgr.add_control('startup',prog_lbl)

msg_lbl = UILabel(20,40, 440,0, 'Wait for wifi and mqtt startup', text_color=GREEN)
msg_lbl.set_font(font_bold_22)
msg_lbl.align = ALIGNMENT_CENTER
mgr.add_control('startup',msg_lbl)

sprint = UITextOnly(start_y=80)
mgr.add_control('startup', sprint)

# 4.2 - for screen home

# check boxes (4)
y_positions = [40, 40, 100, 100]
x_pos = 20
features = ['WiFi', 'Bluetooth', 'GPS', 'NFC']
for y, item in zip(y_positions, features):
    chk = UICheckBox(
        x=x_pos, y=y,
        text=item, size=35, checked=True,
        callback=lambda s, f=item: print(f"{f}: {s}"),
        fg_color=rgb_to_565(220, 220, 220),
        bg_color=rgb_to_565(60, 60, 60),
        check_color=rgb_to_565(100, 100, 100),
        label_color=rgb_to_565(220, 220, 220)
    )
    x_pos += 140
    if x_pos > 180:
        x_pos = 20
        
    mgr.add_control('home',chk)

#  Brightness slider
#  - a label
bright_lbl = UILabel(20, 200, 0, 0, 'Brightness: 50', text_color=BLACK, bg_color = PINK )
bright_lbl.font =font_bold_22
mgr.add_control('home',bright_lbl)
#  - a slider
bright_sld = UISlider( x=20, y=220, w=440, h=30, min_val=0, max_val=100, value=50,
    callback=lambda v: bright_lbl.set_text(f"Brightness: {int(v)}"),
    track_color=rgb_to_565(180, 180, 180),
    knob_color=rgb_to_565(0, 120, 255),
    bg_color=rgb_to_565(60, 60, 60) )
mgr.add_control('home', bright_sld)

#  Volume slider
#  - a label
vol_lbl = UILabel(20, 260, 440, 0, 'Volume: 50')
vol_lbl.set_alignment(ALIGNMENT_RIGHT)
mgr.add_control('home', vol_lbl)
#  - a slider
vol_sld = UISlider(x=20, y=280, w=440, h=30, min_val=0, max_val=100, value=50,
    callback=lambda v: vol_lbl.set_text(f"Volume: {int(v)}"),
    track_color=rgb_to_565(180, 180, 180),
    knob_color=rgb_to_565(255, 100, 100),
    bg_color=rgb_to_565(60, 60, 60) )
mgr.add_control('home', vol_sld)

#  Progress bar
#  - a label
cpu_lbl = UILabel(20, 320, 440, 0, 'Progress Bar', text_color=RED)
cpu_lbl.set_alignment(ALIGNMENT_CENTER)
mgr.add_control('home', cpu_lbl)
#  - a progress bar
cpu_pb = UIProgressBar( x=20, y=340, w=440, h=25, min_val=0, max_val=100, value=10,
    track_color=rgb_to_565(200, 200, 200), fill_color=rgb_to_565(255, 100, 0),
    bg_color=rgb_to_565(60, 60, 60) )
mgr.add_control('home', cpu_pb)

#  Action buttons and their callback functions
btn_y = 400
btn_w, btn_h = 120, 40
labels = ['Apply', 'Dials', 'Exit']
cbs = []
# callbacks
def on_apply():
    print('Apply Button activated')

def on_dials():
    mgr.set_screen('w_data')
    mgr.draw_all()
            
def on_exit():
    global exiting
    print('Exiting settings')
    exiting = True

#  Create 3 buttons in a loop
callbacks = [on_apply, on_dials, on_exit]
btn_x = 40
button_colours = [rgb_to_565(255, 0, 0), rgb_to_565(0, 255, 0), rgb_to_565(0, 0, 255)]
button_index = 0

for lbl, cb in zip(labels, callbacks):
    btn = UIButton(
        x=btn_x, y=btn_y,
        w=btn_w, h=btn_h,
        text=lbl, callback=cb,
        fg_color=rgb_to_565(220, 220, 220),
        bg_color=LIGHTGREY,
        text_color=button_colours[button_index]
    )
    btn.set_font(font_bold_18)
    mgr.add_control('home', btn)
    btn_x += btn_w + 20
    button_index += 1

#  TextBox
tb_lbl = UILabel(20,150,0,0, text= 'Touch coordinates')
tb_lbl.set_font(font_bold_24)
mgr.add_control('home', tb_lbl)

tb_1 = UITextBox(280, 150, 175, 26, text='Press Screen',
        fg_color=GREEN, bg_color=SQBLUE, text_color=PINK,
        bd_clearance = 2 )
tb_1.set_font(font_bold_24)
tb_1.set_alignment(ALIGNMENT_CENTER) 
mgr.add_control('home', tb_1)


# 4.2 - screen w_data
# 	-  labels
mqtt_lbl = UILabel(20, 10, 440, 0, text_color=BLACK, bg_color = PINK )
mqtt_lbl.text='Awaiting mqtt msg'
mqtt_lbl.set_font(font_bold_22)
mqtt_lbl.align = ALIGNMENT_CENTER
mgr.add_control('w_data',mqtt_lbl)

tbox_lbl = UILabel(x=40, y=60, w=440, h=0, text_color=BLACK )
tbox_lbl.text='Compass Degrees'
tbox_lbl.set_font(font_bold_22)
tbox_lbl.align = ALIGNMENT_CENTER
mgr.add_control('w_data',tbox_lbl)

#  - a textbox
msg_lbl = UITextBox(x=200, y=87, w=100, h=30, fg_color=GREEN, bg_color=SQBLUE, text_color=PINK)
msg_lbl.set_font(font_bold_24)
msg_lbl.align = ALIGNMENT_CENTER
mgr.add_control('w_data', msg_lbl)

#  - a dial as a compass
compass1 = UIDial(250,220,80,smallticks=16,bigticks=4,face_color=BLUE, text_color=GREEN, chr_list=('N','NE','E','SE','S','SW',' W','NW'))
compass1.font=font_bold_18
mgr.add_control('w_data', compass1)

#  - another dial
dial2 = UIDial(100,380,60,smallticks=8,bigticks=0,face_color=DARKGREEN, text_color=PINK, chr_list=('0','10','20','30','40','50',' 60','70'))
#compass1.font=font_bold_18
mgr.add_control('w_data', dial2)

#  - a button
#  button callback
def screen_home():
    mgr.set_screen('home')
    mgr.draw_all()
#  button    
go_home = UIButton(300,400,120,40,'Home', text_color=GREEN)
go_home.font=font_bold_18
go_home.callback=screen_home
mgr.add_control('w_data', go_home)


# Section 5  Touch events *******************************************
def screen_swipe(direction):
    if direction == 'D':
        pass
    if direction == 'U':
        pass
    if direction == 'L':
        mgr.set_screen('home')
        mgr.draw_all()
    if direction == 'R':
        mgr.set_screen('w_data')
        mgr.draw_all()
        
    
# If we got a screen tap, send coordinates to UIManager to see if a control on the current
# screen needs to take action
def screen_tap(x,y):
    tb_1.set_text(str(x)+':'+str(y))
    evt = TouchEvent(TOUCH_TAP, x, y)
    mgr.process_touch(evt)


async def touch_check():
    tap_move = 20 # threshold for tap finger movement. >20 means a deliberate drag.
    while True:
        n, points = squixl.touch.read_points()
        while n > 0:
            ts = ticks_ms()
            xStart = points[0][0]
            yStart = points[0][1]
            size = points[0][2]
            await asyncio.sleep_ms(100)
            n, points = squixl.touch.read_points()
            while n > 0:
                xEnd = points[0][0]
                yEnd = points[0][1]
                await asyncio.sleep_ms(100)
                n, points = squixl.touch.read_points()
            te = ticks_ms()
            tap_time = ticks_diff(te,ts)              
            yMove = yEnd - yStart
            xMove = xEnd - xStart      
            if yMove or xMove > tap_move:
                if abs(yMove) > abs(xMove):
                    if yMove > 0:
                        screen_swipe('D')
                    else:
                        screen_swipe('U')
                else:
                    if xMove > 0:
                        screen_swipe('R')
                    else:
                        screen_swipe('L')
            # So not a swipe - must be a press     
            else:
                if tap_time < 400:
                    #Short tap
                    screen_tap(xStart,yStart)
                elif tap_time < 700:
                    #Medium tap
                    screen_tap(xEnd,yEnd)
                else:
                    #Long tap
                    screen_tap(xEnd,yEnd)
        squixl.touch.clear_points()        
        await asyncio.sleep_ms(100)


# *****************************************************
# Section 6 MQTT related

# list of mqtt topics to subscribe to and the corresponding
# function to run when a topic msg is received.

mqtt.subscription_list = ('SQUiXL/Test/Test1',
                          'SQUiXL/Test/Test2'
                          )

# variable to hold the number of wifi of mqtt outages in this session.
# only normall of interest if the board is used on the outer ranges of
# wifi coverage.
outages = 0



# *****************************************************
# Section 7 - program functions

# ------------------------------------------------------
# functions to run depending on mqtt message received

async def func1(payload):
    msg_lbl.set_text(payload)
    compass1.set_value(int(payload))
    
async def func2(msg):
    pass


#-----------------------------------------------------------
# mqtt messages received 
async def messages(client):  # Respond to incoming messages
    async for topic, msg, retained in client.queue:
        msg = msg.decode()
        if topic == 'SQUiXL/Test/Test1':
            await func1(msg)
        elif topic == 'SQUiXL/Test/Test2':
            await func2(int(msg))


#-----------------------------------------------------------
        
# test functions to continually publish on the topics this program has
# subscribed to
async def test_publish(client, topic, wait_time):
    num = 0
    while True:
        await client.publish(topic, str(num))
        num += 10
        if num >= 360:
            num = 0
        
        await asyncio.sleep(wait_time)
    


async def demo_dial2():
    d = 0
    while True:
        dial2.set_value(d)
        d += 45
        if d >= 360:
            d = 0
        await asyncio.sleep(0.5)
 
async def demo_cpu_pb():
    val = 0
    while True:
        cpu_pb.set_value(val)
        val += 10
        if val > 100:
            val = 0
        await asyncio.sleep(1)

# ***********************************************************    


def wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        sprint.set_text('connecting to network...', font_bold_22, GREEN)
        wlan.connect(SSID, PW)
        while not wlan.isconnected():
            pass
    sprint.set_text('network connected:', font_bold_22, GREEN)
    #sprint.set_text(str( wlan.ifconfig()),font_bold_22, GREEN)


async def main(client):
    wifi()
    sprint.set_text('connecting to mqtt',font_bold_22, GREEN)
    await client.connect()
    sprint.set_text('subscribing topics to mqtt',font_bold_22, GREEN)
    asyncio.create_task(mqtt.up(client))
    asyncio.create_task(mqtt.down(client))
   
    sprint.set_text('creating tasks',font_bold_22, GREEN)
    asyncio.create_task(messages(client))
    asyncio.create_task(touch_check())
    
    # create demo async tasks
    sprint.set_text('creating test tasks',font_bold_22, GREEN)
    topic = 'SQUiXL/Test/Test1'
    wait_time = 1
    asyncio.create_task(test_publish(client, topic, wait_time))
    asyncio.create_task(demo_dial2())
    asyncio.create_task(demo_cpu_pb())
    
    # move from setup to home screen              
    mgr.set_screen('home')
    mgr.draw_all()
    
    
    while True:
        await asyncio.sleep(0)
    
# -------------------------------------

# *****************************************************
# Section 8 - Initialise mqtt, draw starup screen start program loop

# for  mqtt last will and testomy registration with broker
LWT_TOPIC = 'SQUiXL/LWT'  
mqtt.config['will'] = (LWT_TOPIC, 'Goodbye cruel world!', False, 0)

# configure for Event based interface (instead of callbacks)
# increase queue_len for bigger msg buffer if required.
mqtt.config["queue_len"] = 1  

mqtt.MQTTClient.DEBUG = False  # Optional: print diagnostic messages
client = mqtt.MQTTClient(mqtt.config)


# Initial draw of the current screen 
mgr.draw_all()

gc.collect()


try:
    asyncio.run(main(client))
except KeyboardInterrupt:
    print('Ctl C')
finally:
    print('finally')
    asyncio.new_event_loop() # to clear async on soft reset.
    squixl.screen_deinit() 


