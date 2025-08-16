# squixl_ui.py
import framebuf
import math
import array

# import the CWriter class from Peter Hinch
# https://github.com/peterhinch/micropython-font-to-py
from writer import CWriter
from boolpalette import BoolPalette
from time import sleep_ms
from colors import *

# Configuration
TOUCH_PADDING = 10  # Extra pixels around each control for easier touching

# Touch event types
TOUCH_TAP        = 0
TOUCH_DOUBLE     = 1
TOUCH_LONG       = 2
TOUCH_SWIPE_UP   = 3
TOUCH_SWIPE_RIGHT= 4
TOUCH_SWIPE_DOWN = 5
TOUCH_SWIPE_LEFT = 6
TOUCH_DRAG       = 7
TOUCH_DRAG_END   = 8
TOUCH_UNKNOWN    = 9


ALIGNMENT_LEFT = 0
ALIGNMENT_CENTER = 1
ALIGNMENT_RIGHT = 2

# Helper: Convert 8-bit RGB to 16-bit RGB565
def rgb_to_565(r, g, b):
    """Convert 0–255 R,G,B to a 16-bit RGB565 value."""
    u16 = b >> 3
    u16 |= ((g >> 2) << 5)
    u16 |= ((r >> 3) << 11)
    return u16

# Create a CWrite device using the same Framebuf buffer that SQUiXL uses
class WriterDevice(framebuf.FrameBuffer):
    def __init__(self, buffer):
        self.width = 480
        self.height = 480
        self.buffer = buffer
        self.mode = framebuf.RGB565
        self.palette = BoolPalette(self.mode)
        super().__init__(self.buffer, self.width, self.height, self.mode)

     
# Function to print text to screen via CWriter device
def print_text(wbuf, font, text, x, y, fg_colour, bg_colour):
    CWriter.set_textpos(wbuf, y, x)
    font.setcolor(fgcolor=fg_colour, bgcolor=bg_colour)
    font.printstring(text)

# Touch event class for capturing touches
class TouchEvent:
    """Encapsulates a touch event."""
    def __init__(self, event_type, x, y):
        self.type = event_type
        self.x = x
        self.y = y

# Screen Control (widgets) **************************************************

# Base class for all UI items
class UIControl:
    """Base class for all controls."""
    def __init__(self, x, y, w, h, text=None, callback=None,
                 fg_color=0xFFFF, bg_color=None, text_color=WHITE):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.callback = callback
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.text_color = text_color
        self.font = None
        self.manager = None  # Set by UIManager
        self.assigned_screen = None # Set by UIManager
        self.align = ALIGNMENT_LEFT
        self.align_offset = 0

    def draw(self):
        raise NotImplementedError

    def within_bounds(self, x, y, w=None, h=None, pad=None):
        """Check if (x,y) is within padded bounds of this control."""
        w = w or self.w
        h = h or self.h
        pad = pad if pad is not None else TOUCH_PADDING
        return (self.x - pad <= x < self.x + w + pad) and (self.y - pad <= y < self.y + h + pad)

    def process_touch(self, evt: TouchEvent):
        """Handle touch event; return True if consumed."""
        return False
    
    def set_font(self, new_font):
        self.font = new_font

    def get_back_color(self):
        if self.bg_color is not None:
            return self.bg_color
        else:
            return self.manager.screens[self.manager.current_screen]['bg_color']
        
# ------------------------------------------------------------
class UILabel(UIControl):
    """A simple text label."""
    def __init__(self, x, y, w, h, text=None, callback=None,fg_color=None, bg_color=None, text_color=WHITE):
        super().__init__(x, y, w, h, text, callback,fg_color, bg_color, text_color)
        self.text_width_pixels = 0   

    def draw(self):
        if self.manager is None:
            return
        self.erase_text()
        _font = self.font if self.font is not None else self.manager.font
        self.text_width_pixels = len(self.text) * _font.font.max_width()        
        self.align_offset = 0
        if self.align != ALIGNMENT_LEFT and self.w > 0:
            if self.align == ALIGNMENT_RIGHT:
               self.align_offset = self.w - self.text_width_pixels
            elif self.align == ALIGNMENT_CENTER:
                self.align_offset = int(self.w/2 - self.text_width_pixels/2)
    
        print_text(self.manager.buf, _font, self.text, self.x + self.align_offset, self.y, self.text_color, self.get_back_color())

    def erase_text(self):
        # print existing text as background colour to obliterate
        #_font = self.font if self.font is not None else self.manager.font
        #print_text(self.manager.buf, _font, self.text, self.x + self.align_offset, self.y, self.get_back_color(), self.get_back_color())
        
        # draw a rec box over existing text in bg.color to obliterate
        _font = self.font if self.font is not None else self.manager.font
        self.manager.buf.rect(self.x + self.align_offset, self.y, self.text_width_pixels, _font.height, self.get_back_color(), True)
        
    def set_text(self, text):
        self.text = text
        #_font = self.font if self.font is not None else self.manager.font
        if self.manager.current_screen == self.assigned_screen:
            self.draw()

    def set_alignment(self, align):
        self.align = align

    def process_touch(self, evt: TouchEvent):
        # Labels don't consume touches, but log for debug
        # print(f"UILabel '{self.text}' touch at ({evt.x},{evt.y}) type={evt.type}")
        return False

# ------------------------------------------------------------
class UITextBox(UIControl):
    """A a container within which text is updated."""
    def __init__(self, x, y, w, h, text="", callback=None,
                 fg_color=None, bg_color=None, text_color=0xFFFF, bd_clearance = 2):
        super().__init__(x, y, w, h, text, callback, fg_color, bg_color, text_color)
        # bd_clearance is an allowance to keep text clear of writing on the text box boarder frame
        self.bd_clearance = bd_clearance

    def draw(self):
        if self.manager is None:
            return
        
        fill = self.bg_color
        border = self.fg_color
        textcol = self.text_color
        self.manager.buf.rect(self.x, self.y, self.w, self.h, fill, True)
        self.manager.buf.rect(self.x, self.y, self.w, self.h, border)

        _font = self.font if self.font is not None else self.manager.font
        
        #tw = len(self.text) * _font.font.max_width()
        #tx = self.x + (self.w - tw) // 2
        if (_font.height + self.bd_clearance) > self.h:
            print('WARNING - text too high for TextBox')
            print('text height + boarder clear', _font.height + self.bd_clearance)
            print('TextBox height:',self.h)
            return
        ty = self.y + (self.h - _font.height) // 2
            
        self.align_offset = 0
        if self.w > 0:
            text_width_pixels = (len(self.text) * _font.font.max_width())
            if text_width_pixels + self.bd_clearance >= self.w:
                print('WARNING - text too long for TextBox')
                print('text width pixels plus boarder clear:',text_width_pixels + self.bd_clearance + 1)
                print('TextBox width:',self.w)
                return
            if self.align == ALIGNMENT_LEFT:
                self.align_offset = self.bd_clearance
            elif self.align == ALIGNMENT_RIGHT:
               self.align_offset = self.w - text_width_pixels - self.bd_clearance
            elif self.align == ALIGNMENT_CENTER:
                self.align_offset = int(self.w/2 - text_width_pixels/2)
                         
        print_text(self.manager.buf, _font, self.text, self.x + self.align_offset, ty, textcol, self.get_back_color())
    
    
    def set_alignment(self, align):
        self.align = align
        
    def process_touch(self, evt: TouchEvent):
        # TextBox's don't consume touches, but log for debug
        # print(f"UITextBox '{self.text}' touch at ({evt.x},{evt.y}) type={evt.type}")
        return False

    def set_text(self, text):
        self.text = text
        if self.manager.current_screen == self.assigned_screen:
            self.draw()
            
# ------------------------------------------------------------
class UITextOnly(UIControl):
    def __init__(self, start_x=5, start_y=10, inc_y=20):
        self.text_list = []
        self.start_x = start_x
        self.start_y = start_y
        self.inc_y = inc_y
        
    def draw(self):
        for item in self.text_list:
            print_text(self.manager.buf, item[3], item[0], item[1], item[2], item[4], self.manager.screens[self.manager.current_screen]['bg_color'])
             
    def set_text(self, text, font, text_color):
        self.text_list.append((text, self.start_x, self.start_y, font, text_color))
        self.start_y += self.inc_y
        if self.manager.current_screen == self.assigned_screen:
            self.draw()


# ------------------------------------------------------------
class UIButton(UIControl):
    """A clickable button that flashes on tap."""
    def __init__(self, x, y, w, h, text="", callback=None,
                 fg_color=0xFFFF, bg_color=0x0000, text_color=0xFFFF):
        super().__init__(x, y, w, h, text, callback, fg_color, bg_color, text_color)
        self.flash = False

    def draw(self):
        if self.manager is None:
            return
        
        fill = self.fg_color if self.flash else self.bg_color
        border = self.text_color if self.flash else self.fg_color
        textcol = self.bg_color if self.flash else self.text_color
        self.manager.buf.rect_round(self.x, self.y, self.w, self.h, 10, fill, True)
        self.manager.buf.rect_round(self.x, self.y, self.w, self.h, 10, border)

        _font = self.font if self.font is not None else self.manager.font
        
        tw = len(self.text) * _font.font.max_width()
        tx = self.x + (self.w - tw) // 2
        ty = self.y + (self.h - _font.height) // 2
        print_text(self.manager.buf, _font, self.text, tx, ty, textcol, self.get_back_color())
        
    def process_touch(self, evt: TouchEvent):
        # print(f"UIButton '{self.text}' touch at ({evt.x},{evt.y}) type={evt.type}")
        if evt.type == TOUCH_TAP and self.within_bounds(evt.x, evt.y):
            self.flash = True
            #self.draw()
            if self.callback:
                self.callback()
            self.flash = False
            #self.draw()
            return True
        return False

    def set_text(self, text):
        self.text = text
        if self.manager.current_screen == self.assigned_screen:
            self.draw()
  
# ------------------------------------------------------------
class UISlider(UIControl):
    """A horizontal slider for selecting a value."""
    def __init__(self, x, y, w, h, min_val=0, max_val=100,
                 value=0, callback=None,
                 track_color=0xFFFF, knob_color=0xFFFF, bg_color=0x0000):
        super().__init__(x, y, w, h, "", callback,
                         track_color, bg_color, track_color)
        self.min = min_val
        self.max = max_val
        self.value = value
        self.knob_color = knob_color
        self.dragging = False

    def draw(self):
        if self.manager is None:
            return

        self.manager.buf.rect_round(self.x, self.y, self.w, self.h, 5, self.bg_color, True)
        mid_y = self.y + self.h // 2
        self.manager.buf.hline(self.x, mid_y, self.w, self.fg_color)
        rel = (self.value - self.min) / (self.max - self.min) if self.max != self.min else 0
        rel = max(0, min(1, rel))
        kx = self.x + int(rel * (self.w - 4))
        self.manager.buf.rect(kx, self.y + 1, 4, self.h - 2, self.knob_color, True)
        self.manager.buf.rect_round(self.x, self.y, self.w, self.h, 5, self.fg_color)

    def process_touch(self, evt: TouchEvent):
        #print(f"UISlider touch at ({evt.x},{evt.y}) type={evt.type} within bounds {self.within_bounds(evt.x, evt.y)}" )
        if evt.type in (TOUCH_TAP, TOUCH_DRAG) and self.within_bounds(evt.x, evt.y):
            rel = (evt.x - self.x) / float(self.w - 1 if self.w > 1 else 1)
            rel = max(0, min(1, rel))
            self.value = self.min + rel * (self.max - self.min)
            self.dragging = True
            self.draw()
            if self.callback:
                self.callback(self.value)
            return True
        if evt.type == TOUCH_DRAG_END and self.dragging:
            self.dragging = False
            self.draw()
            return True
        return False

    def set_value(self, val):
        self.value = max(self.min, min(self.max, val))
        self.draw()

# ------------------------------------------------------------
class UICheckBox(UIControl):
    """A checkbox with a label; dark style with clear on/off indication."""
    def __init__(self, x, y, text, size=20, checked=False, callback=None,
                 fg_color=0xFFFF, bg_color=0x0000, check_color=0xFFFF,
                 label_color=0xFFFF):
        super().__init__(x, y, size, size, text, callback,
                         fg_color, bg_color, label_color)
        self.checked = checked
        self.check_color = check_color

    def draw(self):
        if self.manager is None:
            return
        
        self.manager.buf.rect_round(self.x, self.y, self.w, self.h, 5, self.bg_color, True)
        self.manager.buf.rect_round(self.x, self.y, self.w, self.h, 5, self.fg_color)
        if self.checked:
            # Draw inner box
            pad = max(3, self.w // 5)
            self.manager.buf.rect_round(self.x + pad, self.y + pad,
                          self.w - 2 * pad, self.h - 2 * pad, 3,
                          self.check_color, True)
        # Center label vertically
        ly = self.y + (self.h - 8) // 2

        if self.font is not None:
            print_text(self.manager.buf, self.font, self.text, self.x + self.w + 6, ly, self.text_color, self.bg_color)
        elif self.manager:
            print_text(self.manager.buf, self.manager.font, self.text, self.x + self.w + 6, ly, self.text_color, self.bg_color)
        # buf.text(self.value, self.x + self.w + 6, ly, self.text_color)

    def process_touch(self, evt: TouchEvent):
        #print(f"UICheckBox '{self.value}' touch at ({evt.x},{evt.y}) type={evt.type}")
        #ext_w = self.w + 6 + len(self.text) * 8
        ext_w = self.w + 6
        if evt.type == TOUCH_TAP and self.within_bounds(evt.x, evt.y, ext_w, self.h):
            self.checked = not self.checked
            self.draw()
            if self.callback:
                self.callback(self.checked)
            return True
        return False

    def set_checked(self, checked):
        self.checked = checked
        self.draw()


# ------------------------------------------------------------------
class UIDial(UIControl):
    def __init__(self,x,y,radius, smallticks=0, bigticks=0, face_color = GREY, bg_color=None, fg_color=GREEN, smallticks_color=WHITE,
                 bigticks_color=WHITE, needle_color=RED, boss_color=PINK, text_color=None, chr_list=None):
        super().__init__(x, y, fg_color, bg_color, text_color)
        self.x = x
        self.y = y
        self.smallticks = smallticks
        self.bigticks = bigticks
        self.radius = radius
        self.face_color = face_color
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.text_color = text_color
        self.smallticks_color = smallticks_color
        self.bigticks_color = bigticks_color
        self.needle_color = needle_color
        self.boss_color = boss_color
        self.boss_size = int(radius * 0.1)
        self.needle_value = None
        self.chr_list = chr_list
        
    def _target_coords(self,ox,oy,radius,angle):
        x = radius * math.sin(math.radians(angle))
        y = radius * math.cos(math.radians(angle))
        #return(int(round(x,0)) + ox, (int(round(y,0)) - oy) *-1)
        return(int(round(x,0)) + ox, oy - (int(round(y,0))))
    
    def draw(self):
        # face
        self.manager.buf.ellipse(self.x,self.y,self.radius,self.radius,self.face_color, True)
        self.manager.buf.ellipse(self.x,self.y,self.radius,self.radius,self.fg_color)
        
        # small ticks
        if self.smallticks > 0:
            angle = 0
            segment = 360 / self.smallticks
            while angle < 360:
                tx, ty = self._target_coords(self.x,self.y,self.radius,angle)
                self.manager.buf.line(self.x,self.y,tx,ty,self.smallticks_color)
                angle += segment
                center_clear = int(self.radius * 0.1)
            self.manager.buf.ellipse(self.x,self.y,self.radius-center_clear,self.radius-center_clear,self.face_color, True)
        
        # big ticks
        if self.bigticks > 0:
            angle = 0
            segment = 360 / self.bigticks
            while angle < 360:
                tx, ty = self._target_coords(self.x,self.y,self.radius,angle)
                self.manager.buf.line(self.x,self.y,tx,ty,self.bigticks_color)
                angle += segment
                center_clear = int(self.radius * 0.2)   
            self.manager.buf.ellipse(self.x,self.y,self.radius-center_clear,self.radius-center_clear,self.face_color, True)
       
        # dial boss
        self.manager.buf.ellipse(self.x,self.y,self.boss_size,self.boss_size,self.boss_color, True)
        
        # show dial if legend charaters are provided
        if self.chr_list is not None:
            self.show_txt(self.chr_list)    
    
        # draw needle if needle has a current value stored
        if self.needle_value is not None:
            self.set_value(self.needle_value)
            
    # set the value (0 - 360) of dial circle - calculate the needle angel and draw the needle
    # if the control is on the current screen
    def set_value(self, angle):
        self.needle_value = angle
        if self.manager.current_screen != self.assigned_screen:
            return
        # calculate the needle angle
        needle_length = int(self.radius * 0.7)
        # blank previous
        center_clear = int(self.radius * 0.2)  
        self.manager.buf.ellipse(self.x,self.y,self.radius-center_clear,self.radius-center_clear,self.face_color, True)
        # sharp end of needle
        tx, ty = self._target_coords(self.x,self.y,needle_length,angle)
        
        # thin needle
        #self.manager.buf.line(self.x,self.y,tx,ty,self.needle_color)
        
        # fat needle
        sx, sy = self._target_coords(self.x,self.y,int(needle_length-10),angle-4)
        lx, ly = self._target_coords(self.x,self.y,int(needle_length-10),angle+4)
        fat_needle = array.array('h',[tx,ty,sx, sy, self.x, self.y, lx, ly, tx, ty])
        self.manager.buf.poly(0,0,fat_needle, self.needle_color, True)

        
        # dial boss
        self.manager.buf.ellipse(self.x,self.y,self.boss_size,self.boss_size,self.boss_color, True)    

    # display compass ledgend
    def show_txt(self,chr_list):
        _font = self.font if self.font is not None else self.manager.font
        num = len(chr_list)
        segment = 360 / num
        angle = 0
        for c in chr_list:
            pad = 20
            tx,ty = self._target_coords(self.x,self.y,self.radius+pad,angle)
            if angle >=0 and angle <= 22.5:
                tx -= 5
            elif angle >22.5 and angle <=45:
                tx -= 5
                ty -= 3
            elif angle >45 and angle <=112.5:
                tx -= 8
                ty -=8
            elif angle >112.5 and angle <=157.5:
                tx -= 5
                ty -= 8
            elif angle >157.5 and angle <=180:
                tx -= 5
                ty -= 12
            elif angle >180 and angle <=202.5:
                tx -= 8
                ty -= 12
            elif angle >202.5 and angle <=247.5:
                tx -= 8
                ty -= 8
            elif angle >247.5 and angle <=270:
                tx -= 12
                ty -= 8
            elif angle >270 and angle <=315:
                tx -= 8
                ty -= 8
            elif angle >315 and angle <=337.5:
                tx -= 12
                ty -= 3
            elif angle >337.5 and angle <=360:
                tx -= 8 
  
            print_text(self.manager.buf, _font, c, tx, ty, self.text_color, self.get_back_color())
            angle += segment


# ------------------------------------------------------------
class UIProgressBar(UIControl):
    """A non-interactive progress bar."""
    def __init__(self, x, y, w, h, min_val=0, max_val=100,
                 value=0, track_color=0xFFFF,
                 fill_color=0xFFFF, bg_color=0x0000):
        super().__init__(x, y, w, h, "", None,
                         track_color, bg_color, track_color)
        self.min = min_val
        self.max = max_val
        self.value = value
        self.fill_color = fill_color

    def draw(self):
        if self.manager is None:
            return
        
        self.manager.buf.rect_round(self.x, self.y, self.w, self.h, 5, self.bg_color, True)
        rel = (self.value - self.min) / (self.max - self.min) if self.max != self.min else 0
        rel = max(0, min(1, rel))
        fill_w = int(rel * (self.w - 2))
        self.manager.buf.rect_round(self.x + 1, self.y + 1, fill_w, self.h - 2, 5, self.fill_color, True)
        self.manager.buf.rect_round(self.x, self.y, self.w, self.h, 5, self.fg_color)

    def set_value(self, val):
        self.value = max(self.min, min(self.max, val))
        if self.manager.current_screen == self.assigned_screen:
            self.draw()


# Controls Manager **********************************************
class UIManager:
    """Manages multiple screens, assigns controls to screens, and dispatches
        touch events to controls on the current screen
        Only one instance of this class is required and it is initiallised with
        the frame buffer instance and a program default font.
        All the screens are held in a dictionary with a screen name : sub dictionary
        arrangement with the sub dictionary holding a background colour for the screen
        and another sub dictionary holding a list of controls assigned to the screen name"""
    
    def __init__(self, buf, def_font):
        self.buf = buf
        self.screens = {}
        self.current_screen = None
        self.font = def_font

    def add_screen(self, name, bg_color):
        self.screens.update({name : {'bg_color': bg_color, 'controls':[]}})
        if self.current_screen is None:
            self.current_screen = name
            
    def set_screen(self, name):
        if name in self.screens:
            self.current_screen = name
        else:
            print('error - screen name not in screen list')
            
    def add_control(self, screen_name, ctrl_obj):
        if screen_name in self.screens:
            if ctrl_obj not in self.screens[screen_name]['controls']:
                self.screens[screen_name]['controls'].append(ctrl_obj)
                ctrl_obj.manager = self
                ctrl_obj.assigned_screen = screen_name
            else:
                print('contol already assinged to screen')
        else:
            print('error - screen_name not in screen list')
            
    def draw_all(self):
        if self.current_screen is None:
            return
        self.buf.fill(self.screens[self.current_screen]['bg_color'])
        for ctrl in self.screens[self.current_screen]['controls']:
            ctrl.draw()
  
    def process_touch(self, evt: TouchEvent):
        if self.current_screen is None:
            return false
        for ctrl in self.screens[self.current_screen]['controls']:
            if ctrl.process_touch(evt):
                return True
        return False
    