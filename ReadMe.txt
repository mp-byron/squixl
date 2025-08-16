Adding to the example micropython files as per the Unexpected Maker squixel github this demo code includes textbox and dial controls or widgets 

The UIManager from the UM example has been modified and the UIScreen class has been deleted and incorporated into the UIManager class (just a personal preference nothing wrong with the original :-)  ) 

To enable the drawing of the controls on the screen only when they have been assigned to the current screen being displayed, each control is assigned to a named screen when they are added via the UIManager.

The sequence to creating and assigning the controls is as follows:

create the ui_manager
	- the framebuffer buffer
	- a default font for all controls
	e.g. mgr = UIManager(wbuf, font_light_16)

create and add screens to the ui_manager
	- screen name as text string
	- a background colour for the screen
	e.g. mgr.add_screen('startup', BLUE)

create controls (widgets)
	- create an instance of the desired UI class
	e.g. go_home = UIButton(300,400,120,40,'Home', text_color=CYAN)

add control instance to the desired screen
	e.g. mgr.add_control('startup', go_home)

The demo is not meant as a fully robust code for newbies, for example only a singleton UIManager instance is appropriate but the code does not restrict this.  And the textbox and dial widgets display will suffer miserably if overly small or large fonts are used, though they should be good for the sort of font sizes one would use on a screen of squixl proportions.

The demo program (ui_example_asyncT.py) has 2 logical screens (three if the startup screen is counted).  A screen swipe to right will show the dials screen a swipe to the left will go back to the home screen.   Alternatively each screen has a button that will go to the other screen.

The demo needs to have a mqtt broker running on the network.  I use an old raspberry pi to run the mosquitto mqtt broker.   The demo will publish messages to the broker on the topics that the demo has subscribed to.  This shows the dial controls being continually updated with updated data even when those controls are not visible on the current screen.  Moving to the screen on which the dials are assign to will then show the current value of the dial controls.   

The secrets.py file will need to be amended for the mqtt broker address and the wifi ssid and pw as appropriate.


