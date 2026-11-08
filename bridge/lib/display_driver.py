""" Classes to mediate between bridge_main and LCD LED devices
    16,17,18,19 SPI0_RX, SPI0_CSN, SPI0_SCK, SPI0_TX GPIO numbering
    
    v1.3.0  moved from hershey to vector fonts
    
    TODO ideas:
        add support for °Plato
        blinky only required if extended info not present
"""

import gc
import time
import asyncio
from machine import Pin
import picographics
from picographics import PicoGraphics  # , DISPLAY_PICO_DISPLAY, PEN_P4
from picovector import PicoVector, ANTIALIAS_NONE, ANTIALIAS_X4, ANTIALIAS_X16, HALIGN_CENTER, HALIGN_LEFT, HALIGN_RIGHT
from pimoroni_bus import SPIBus
from pimoroni import RGBLED
from models import TiltDevice, TiltStatus, TiltHistory
from configuration import BridgeConfig

# from bridge_main import TiltDevice

# 16 colours
# Define color palette, used by LED & palette
palette_cols = {
    "BLACK": [200, 200, 200],  # obv white
    "BLUE": [0x0, 0x80, 0xFE],  # AZURE
    "RED": [0xD3, 0x00, 0x00],
    "ORANGE": [0xFF, 0x4D, 0x00],
    "PURPLE": [0xA0, 0x20, 0xF0],
    "GREEN": [0x0, 0xEE, 0x00],
    "PINK": [0xFF, 0x14, 0x93],
    "YELLOW": [0xFF, 0xF0, 0x17],
    "SIMULATED": [0x93, 0xA3, 0x92],
    "BEER": [0xFF, 0xA7, 0x00],  # CHROME YELLOW
    "WHITE": [255, 255, 255],
    "BG": [40, 40, 40],
    "HAL": [160, 20, 20], # blinky heartbeat indicator
}


def get_color_values(color_name, brightness=0.01):
    """Returns RGB values adjusted by brightness, led is much brighter than LCD"""
    rgb = palette_cols.get(color_name.upper(), [0, 0, 0])
    return [int(c * brightness) for c in rgb]


class LCD_Display:
    def __new__(cls, config: BridgeConfig):
        if not getattr(config, "display_type", None):
            return None  # Prevent instance creation
        return super().__new__(cls)

    def __init__(self, config: BridgeConfig):
        import vfs_fonts
        self.config = config
        self.lcd = None  # getattr gpio pins
        self.update_intvl = getattr(self.config, "display_update_secs", 3)
        self.brightness = None  # getattr
        self.indicator = True
        self.startup_msg = []
        (
            self._check_for_display(display_type)
            if (display_type := getattr(self.config, "display_type", None))
            else None
        )

    def _check_for_display(self, display_type):
        # get GPIO details
        spibus = SPIBus(**(self.parse_gpio()))
        self.lcd = PicoGraphics(
            display=getattr(picographics, display_type),
            bus=spibus,
            pen_type=picographics.PEN_P4,
            rotate=0,
        )
        self.vector = PicoVector(self.lcd)
        self.vector.set_antialiasing(ANTIALIAS_X16)
        
        # Create palette mapping dynamically
        self.colour_to_palette = {
            colour: self.lcd.create_pen(*get_color_values(colour, 1))
            for colour in palette_cols
        }
        self.lcd.set_backlight(getattr(self.config, "lcd_backlight", 0.5))
        self.lcd.set_pen(self.colour_to_palette["BG"])
        self.lcd.clear()

    def parse_gpio(self):
        # check for a reset pin value & strip it
        vals = getattr(
                    self.config,
                    "lcd_gpio",
                    {"cs": 17, "dc": 16, "sck": 18, "mosi": 19, "bl": 20}
               )
        rst = vals.pop('rst', None)
        if rst:
            # if using cheap Chinese set the RES/Reset pin here:
            rst = Pin(rst, Pin.IN, Pin.PULL_UP)
        # return SPI & backlight pins
        return vals
        
    async def card_stack(
        self, tilt_data_store: TiltHistory, cards: TiltDevice
    ):  #: TiltDevice
        # display the most recent data as basic & extended info for each tilt
        # some sort of loading screen
        self.startup_msg = [] # clear startup messages
        while True:
            self.vector.set_font("/vfs/OpenSans-SemiBold.af", 62)
            for tilt in cards:
                # show standard info for each configured tilt colour
                # & test for extended info
                extended_info = await self.display_sg_t(tilt, tilt_data_store)
                # return a tilt_status object or None
                if extended_info:
                    await self.display_extended(tilt, extended_info)
                if len(self.startup_msg):
                    # there's probably a wifi disconnection
                    await self.show_msg()

    def read_latest_vals(self, tilt_data_store, tilt_colour):
        # read latest values & return a tuple
        uncal_tempF, uncal_SG = tilt_data_store.get_data(
            tilt_colour,
            av_period=0,
            log_period=(3 * self.update_intvl),
        )
        if uncal_tempF and uncal_SG:
            tilt_status = TiltStatus(
                tilt_colour, uncal_tempF, uncal_SG, self.config, apply_calibration=False
            )
            uncal_temp = (
                tilt_status.temp_celsius
                if (getattr(self.config, "default_temp_unit") == "C")
                else tilt_status.temp_fahrenheit
            )
            uncal_gravity = tilt_status.gravity
            tilt_status = TiltStatus(
                tilt_colour, uncal_tempF, uncal_SG, self.config, apply_calibration=True
            )
            # data offsets/calibration is applied here in TiltStatus
        else:
            # logger.info(f"{colour} has no data")
            uncal_temp, uncal_gravity, tilt_status = None, None, None
        return (uncal_temp, uncal_gravity, tilt_status)

    async def display_sg_t(self, tilt, tilt_data_store):
        #
        WIDTH, HEIGHT = self.lcd.get_bounds()
        # t_start = time.ticks_ms()
        line1_v = 40
        line2_v = 80
        line3_v = 105
        line4_v = 130
        uncal_temp, uncal_sg, tilt_values = self.read_latest_vals(
            tilt_data_store, tilt.colour
        )
        n = 4 if tilt.hd else 3
        self.lcd.set_pen(self.colour_to_palette["BG"])

        self.lcd.clear()
        self.lcd.set_pen(self.colour_to_palette[tilt.colour.upper()])
        self.vector.set_font_align(HALIGN_CENTER)
        self.vector.set_font("/vfs/OpenSans-SemiBold.af", 62)
        if all([uncal_temp, uncal_sg, tilt_values]):
            # line1 gravity centred, SG:0.0000 or SG:0.000
            msg = f"SG:{tilt_values.gravity:.{n}f}"
            self.vector.text(msg, 0, line1_v, max_width=WIDTH)
            #x, y, w, h = bridge.display.vector.measure_text(msg, x=0, y=0, angle=None)
            #print(f"{x:},{y:},{w:},{h:}")
            
            if getattr(self.config, "default_temp_unit") == "C":
                unit = "C"
                tval = tilt_values.temp_celsius
            else:
                tval = tilt_values.temp_fahrenheit
                unit = "F"
            self.vector.text(f"{tval:.1f}°{unit}", 0, line2_v, max_width=WIDTH)
            
            self.vector.set_font("/vfs/OpenSans-Light.af", 33)
            # line4 uncal SG & temp
            self.vector.text(f"{uncal_sg:.{n}f}  {uncal_temp:.1f}", 0, line4_v, max_width=WIDTH)
            
            # RSSI line3
            self.vector.set_font_align(HALIGN_LEFT)
            self.vector.text(f"RSSI:{tilt.rssi}", 3, line3_v, max_width=WIDTH)
            # colour line3
            self.vector.set_font_align(HALIGN_RIGHT)
            self.vector.text(f"{tilt.colour}", 0, line3_v, max_width=WIDTH-3)            
            
            # line 4 battery age, if present
            msg = f"{batt_weeks}" if (batt_weeks := tilt.batt_weeks) else ""
            if msg:
                self.vector.set_font("/vfs/OpenSans-Light.af", 20)
                self.vector.text(f"{msg}", 0, line4_v, max_width=WIDTH-3)
        else:
            # no data
            self.vector.set_font("/vfs/OpenSans-SemiBold.af", 50)
            self.vector.text("waiting for", 0, 60, max_width=WIDTH)
            #self.vector.text("for", 0, line2_v, max_width=WIDTH)
            self.vector.text("data", 0, 100, max_width=WIDTH)
            self.vector.set_font("/vfs/OpenSans-Light.af", 33)
            self.vector.set_font_align(HALIGN_RIGHT)
            self.vector.text(f"{tilt.colour}", 0, 125, max_width=WIDTH-3)
        gc.collect()
        self.update_indicator() # blinky
        # t1 = time.ticks_ms()
        self.lcd.update()
        # t2 = time.ticks_ms()
        # print(f"standard drawing took:{time.ticks_diff(t1, t_start)}, update took:{time.ticks_diff(t2, t1)}")
        await asyncio.sleep(self.update_intvl)
        return tilt_values if getattr(tilt_values, "original_gravity", None) else None

    async def display_extended(self, tilt, tilt_values):
        #
        #self.lcd.set_font("serif")
        self.lcd.set_pen(self.colour_to_palette["BG"])
        self.lcd.clear()
        self.lcd.set_pen(self.colour_to_palette[tilt.colour.upper()])
        self.vector.set_font_align(HALIGN_CENTER)
        self.vector.set_font("/vfs/OpenSans-SemiBold.af", 62)
        # t1 = time.ticks_ms()
        WIDTH, HEIGHT = self.lcd.get_bounds()
        # t_start = time.ticks_ms()
        line1_v = 40
        line2_v = 80
        line3_v = 105
        line4_v = 130
        # ABV
        self.vector.text(f"ABV:{tilt_values.alcohol_by_volume:.1f}%", 0, line1_v, max_width=WIDTH)
        # AA
        self.vector.text(f"AA:{tilt_values.apparent_attenuation:.0f}%", 0, line2_v, max_width=WIDTH)
        
        self.vector.set_font("/vfs/OpenSans-Light.af", 33)
        # colour line3
        self.vector.set_font_align(HALIGN_RIGHT)
        self.vector.text(f"{tilt.colour}", 0, line3_v, max_width=WIDTH-3)
        # RSSI line3
        self.vector.set_font_align(HALIGN_LEFT)
        self.vector.text(f"RSSI:{tilt.rssi}", 3, line3_v, max_width=WIDTH)
        
        # OG
        n = 4 if tilt.hd else 3
        self.vector.text(f"OG:{tilt_values.original_gravity:.{n}f}", 3, line4_v, max_width=WIDTH)
        
        gc.collect()
        self.update_indicator() # blinky
        # t1 = time.ticks_ms()
        self.lcd.update()
        # t2 = time.ticks_ms()
        # print(f"extended drawing took:{time.ticks_diff(t1, t_start)}, update took:{time.ticks_diff(t2, t1)}")
        await asyncio.sleep(self.update_intvl)

    def update_indicator(self):
        # alternate a little indicator so we know values are being received even if they are not changing
        if self.indicator:
            self.lcd.set_pen(self.colour_to_palette["HAL"])
        else:
            self.lcd.set_pen(self.colour_to_palette["BG"])
        self.indicator = not self.indicator
        self.lcd.circle(10, 60, 5) # x, y, r
    
    async def show_msg(self, msg=None, append=True):
        ''' if msg then add to list
            display text
        '''
        intvl = 1 # 
        if msg:
            if append:
                # not currently used, could remove append() property
                try:
                    self.startup_msg.append(msg)
                except NameError:
                    self.startup_msg = [msg]
            else:
                # overwrite last line
                try:
                    self.startup_msg[-1] = msg
                except NameError:
                    self.startup_msg = [msg]
        else:
            # not adding a message
            intvl = self.update_intvl
        self.lcd.set_font("bitmap8")
        self.lcd.set_pen(self.colour_to_palette["BG"])
        self.lcd.clear()
        self.lcd.set_thickness(1)
        self.lcd.set_pen(self.colour_to_palette["WHITE"])
        #self.lcd.text(msg, 0, 65, scale=1)
        #self.lcd.text(self.startup_msg, 0, 0)
        while len(self.startup_msg) > 7:
            # remove oldest messages
            del self.startup_msg[0]
        self.lcd.text('\n'.join([item for item in self.startup_msg]), 0, 0)
        self.lcd.update()
        #time.sleep(1)
        await asyncio.sleep(intvl)
    
    def blocking_show_msg(self, msg, append=True):
        ''' allow a synchronous display method  - used from main.py '''
        asyncio.run(self.show_msg(msg, append))
        

class RGB_Driver:
    def __new__(cls, config: BridgeConfig):
        if not getattr(config, "rgb_led_gpio", None):
            return None  # Prevent instance creation
        return super().__new__(cls)

    def __init__(self, config: BridgeConfig):
        self.config = config
        self._led = None
        self._led = (
            RGBLED(*pins) if (pins := getattr(config, "rgb_led_gpio", None)) else None
        )
        self._led and self._led.set_rgb(0, 0, 0)

    def _loadRGBLED(self, *pins):
        if pins:
            # print(f"***  {pins=}")
            self._led = RGBLED(*pins)
            self._led.set_rgb(0, 0, 0)

    def off(self):
        # turn off
        self._led.set_rgb(0, 0, 0)

    async def _flash_rgb_task(self, rgb_colours):
        #
        self._led.set_rgb(*rgb_colours)
        await asyncio.sleep_ms(500)
        self._led.set_rgb(0, 0, 0)

    def flash(self, colour):
        if self._led:
            #
            if _task := getattr(self, "_led_task", None):
                _task.cancel()
            self._led_task = asyncio.create_task(
                self._flash_rgb_task(
                    get_color_values(
                        colour, getattr(self.config, "rgb_brightness", 0.1)
                    )
                )
            )


def c_align(lcd_obj, txt, sz, width):
    # return a offset from left
    return int((width - lcd_obj.measure_text(txt, sz)) // 2)


def r_align(lcd_obj, txt, sz, width):
    # return a offset from left
    return int(width - lcd_obj.measure_text(txt, sz))


__version__ = "1.3.0"
