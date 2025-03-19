''' Classes to mediate between bridge_main and LCD LED devices
16,17,18,19 SPI0_RX, SPI0_CSN, SPI0_SCK, SPI0_TX GPIO numbering
'''
import gc
import time
import asyncio
from machine import Pin
import picographics
from picographics import PicoGraphics #, DISPLAY_PICO_DISPLAY, PEN_P4
from pimoroni_bus import SPIBus
from pimoroni import RGBLED
from models import TiltDevice, TiltStatus, TiltHistory
from configuration import BridgeConfig
#from bridge_main import TiltDevice

# 16 colours
# Define color palette, used by LED & palette
palette_cols = {
    "BLACK": [200, 200, 200],  # obv white
    "BLUE": [0x0, 0x80, 0xFE],  # AZURE
    "RED": [0xD3, 0x00, 0x00],
    "ORANGE": [0xFF, 0x4D, 0x00],
    "PURPLE": [0xA0, 0x20, 0xF0],
    "GREEN": [0x0, 0xFF, 0x00],
    "PINK": [0xFF, 0x14, 0x93],
    "YELLOW": [0xFF, 0xF0, 0x17],
    "SIMULATED": [0x93, 0xA3, 0x92],
    "BEER": [0xFF, 0xA7, 0x00],  # CHROME YELLOW
    "WHITE": [255, 255, 255],
    "BG": [40, 40, 40]
}

def get_color_values(color_name, brightness=0.01):
    """Returns RGB values adjusted by brightness, led is much brighter than LCD"""
    rgb = palette_cols.get(color_name.upper(), [0, 0, 0])
    return [int(c * brightness) for c in rgb]

# Create palette mapping dynamically
#colour_to_palette = {
#    colour: lcd.create_pen(*get_color_values(colour, 1)) for colour in palette_cols
#}
#def colour_to_palette(lcd, colour):
#    lcd.create_pen(*get_color_values(colour, 1)) for colour in palette_cols

class LCD_Display:
    def __new__(cls, config: BridgeConfig):
        if not getattr(config, 'display_type', None):
            return None  # Prevent instance creation
        return super().__new__(cls)

    def __init__(self, config: BridgeConfig):
        self.config = config
        self.lcd = None#getattr gpio pins
        self.update_intvl = None
        self.brightness = None#getattr
        #lcd = PicoGraphics(display=DISPLAY_PICO_DISPLAY, pen_type=PEN_P4,rotate=0)
        #lcd.set_backlight(1.0)
        #update_frequency = 3 # seconds to cycle through each screen
        #self._check_for_display(pins) if (pins := getattr(config, 'lcd_spi_gpio', None)) else None
        self._check_for_display(display_type) if (display_type := getattr(self.config, 'display_type', None)) else None

    def _check_for_display(self, display_type):
        #try:
        # print(f"***  {pins=}")
        spibus = SPIBus(**(getattr(self.config, 'lcd_spi_gpio', {"cs": 17, "dc": 16, "sck": 18, "mosi": 19,"bl": 20}))) #(cs=17, dc=16, sck=18, mosi=19, bl=20)
        self.lcd = PicoGraphics(display=getattr(picographics, display_type), bus=spibus, pen_type=picographics.PEN_P4, rotate=0)
        #self.lcd = PicoGraphics(display=DISPLAY_PICO_DISPLAY, pen_type=PEN_P4,rotate=0)
        self.lcd.set_backlight(getattr(self.config, 'lcd_backlight', 0.5))
        self.lcd.clear()
        # Create palette mapping dynamically
        self.colour_to_palette = {
            colour: self.lcd.create_pen(*get_color_values(colour, 1)) for colour in palette_cols
        }

    async def card_stack(self, tilt_data_store: TiltHistory, cards: TiltDevice): #: TiltDevice
        # display the most recent data as basic & extended info for each tilt
        # some sort of loading screen
        spacing = None
        sg, temp, uncal_sg, uncal_temp, rssi = None, None, None, None, None
        self.lcd.set_font("serif")
        while True:
            index = 0
            for tilt in cards:
                if index == 0:
                    # print("show clock")
                    await self.display_clock()
            # show standard info for each configured tilt colour
            extended_info = await self.display_sg_t(tilt, tilt_data_store)
            # return a tilt_status object or None
            if extended_info:
                await self.display_extended(tilt, extended_info)
            index = (index + 1) % len(cards)

    def read_latest_vals(self, tilt_data_store, tilt_colour):
        # read latest values & return a tuple
        # TODO include C or F for display in config - also Plato?
        uncal_tempF, uncal_SG = tilt_data_store.get_data(tilt_colour, av_period=0, log_period=(3*getattr(self.config, 'display_update_secs', 3)))
        if uncal_tempF and uncal_SG:
            tilt_status = TiltStatus(tilt_colour, uncal_tempF, uncal_SG, self.config, apply_calibration=False)
            uncal_temp = tilt_status.temp_celsius if (getattr(self.config, 'default_temp_unit') == "C") else tilt_status.temp_fahrenheit
            uncal_gravity = tilt_status.gravity
            tilt_status = TiltStatus(tilt_colour, uncal_tempF, uncal_SG, self.config, apply_calibration=True)
            # data offsets/calibration is applied here in TiltStatus
        else:
            #logger.info(f"{colour} has no data")
            uncal_temp, uncal_gravity, tilt_status = None, None, None
        return (uncal_temp, uncal_gravity, tilt_status)

    async def display_clock(self):
        # show a clock or a MOTD or something
        width, height = self.lcd.get_bounds()
        offset = None
        for _ in range(getattr(self.config, 'display_update_secs', 3)):
            self.lcd.set_pen(self.colour_to_palette["BG"])
            self.lcd.clear()
            self.lcd.set_thickness(2)
            self.lcd.set_pen(self.colour_to_palette["WHITE"])
            current_time = time.localtime()
            #year = current_time[0]
            #month = current_time[1]
            #day = current_time[2]
            hour = current_time[3]
            minute = current_time[4]
            second = current_time[5]
            time_now = f"{hour:02d}:{minute:02d}:{second:02d}"
            #time_now = "16:27:00" # centred:
            #offset  = (WIDTH - self.lcd.measure_text(time_now, 1.5)) // 2
            offset = c_align(self.lcd, time_now, 1.5, width) if offset is None else offset
            self.lcd.text(time_now, offset, 65, scale=1.5)
            self.lcd.update()
            await asyncio.sleep(1)
            # TODO subtract processing time from 1 second ticks_diff

    async def display_sg_t(self, tilt, tilt_data_store):
        #
        width, height = self.lcd.get_bounds()
        #t_start = time.ticks_ms()
        line1_v = 20
        line2_v = 60
        line3_v = 95 #100
        line4_v = 125
        uncal_temp, uncal_sg, tilt_values = self.read_latest_vals(tilt_data_store, tilt.colour)
        n = 4 if tilt.hd else 3
        self.lcd.set_pen(self.colour_to_palette["BG"])
        self.lcd.clear()
        self.lcd.set_pen(self.colour_to_palette[tilt.colour.upper()])
        if all([uncal_temp, uncal_sg, tilt_values]):
            self.lcd.set_thickness(3)
            txt_scale = 1.5
            # line1 gravity centred, SG:0.0000 or SG:0.000
            msg=f"SG:{tilt_values.gravity:.{n}f}"
            self.lcd.text(msg, c_align(self.lcd, msg, txt_scale, width), line1_v, scale=txt_scale)
            # line2 temp centred, <value> <degree> <unit>, -10.3°C
            msg = f"{tilt_values.temp_celsius:.1f}" if getattr(self.config, 'default_temp_unit') == "C" else f"{tilt_values.temp_fahrenheit:.1f}"
            #msg = f"{msg}°{getattr(self.config, 'default_temp_unit')}"
            h_offset = c_align(self.lcd, msg, txt_scale, width) - ((15+31)//2) # fudge for °C or °F
            self.lcd.text(msg, h_offset, line2_v, scale=txt_scale)
            spacing = self.lcd.measure_text(msg, scale=txt_scale)
            msg="°"
            self.lcd.text(msg, h_offset + spacing, line2_v - 15, scale=0.75)
            msg = getattr(self.config, 'default_temp_unit')
            self.lcd.text(msg, h_offset + spacing + 15, line2_v, scale=1.5)
            self.lcd.set_thickness(1)
            # line3 rssi left aligned, RSSI:-52
            msg=f"RSSI:{tilt.rssi}"
            self.lcd.text(msg, 0, line3_v, scale=1)#0.8)
            # line3 tilt colour right aligned, blue
            msg = tilt.colour
            self.lcd.text(msg, r_align(self.lcd, msg, 1, width), line3_v, scale=1)#0.8)
            # line4 uncal values & tx_power?
            msg=f"{uncal_temp:.1f}"# {uncal_sg:.{n}f}"
            msg2=f"{uncal_sg:.{n}f}"
            msg3="52" # tilt.tx_power
            self.lcd.text(msg, 0, line4_v, scale=1)#0.8)
            # line4 tx_power field?
            self.lcd.text(msg3, r_align(self.lcd, msg3, 1, width), line4_v, scale=1)#0.8)
            # line 4 uncal sg centred beween temp & tx_power
            spacing = (width - self.lcd.measure_text(f"{msg}{msg2}{msg3}", scale=1)) // 2
            spacing += self.lcd.measure_text(f"{msg}", scale=1)
            self.lcd.text(f"{uncal_sg:.{n}f}", spacing, line4_v, scale=1)
        else:
            # no data
            self.lcd.set_thickness(2)
            msg=f"waiting"
            self.lcd.text(msg, c_align(self.lcd, msg, 1, width), 30, scale=1)
            msg=f"for"
            self.lcd.text(msg, c_align(self.lcd, msg, 1, width), 60, scale=1)
            msg=f"data"
            self.lcd.text(msg, c_align(self.lcd, msg, 1, width), 90, scale=1)
            self.lcd.set_thickness(1)
            msg=tilt.colour
            self.lcd.text(msg, r_align(self.lcd, msg, 1, width), line4_v-5, scale=1)
        gc.collect()
        #t1 = time.ticks_ms()
        self.lcd.update()
        #t2 = time.ticks_ms()
        #print(f"standard drawing took:{time.ticks_diff(t1, t_start)}, update took:{time.ticks_diff(t2, t1)}")
        await asyncio.sleep(getattr(self.config, 'display_update_secs', 3))
        return tilt_values if getattr(tilt_values, 'original_gravity', None) else None

    async def display_extended(self, tilt, tilt_values):
        #
        self.lcd.set_pen(self.colour_to_palette["BG"])
        self.lcd.clear()
        self.lcd.set_pen(self.colour_to_palette[tilt.colour.upper()])
        #t1 = time.ticks_ms()
        width, height = self.lcd.get_bounds()
        #t_start = time.ticks_ms()
        line1_v = 20
        line2_v = 60
        line3_v = 95 #100
        line4_v = 125
        self.lcd.set_thickness(3)
        # ABV
        self.lcd.text(f"ABV:{tilt_values.alcohol_by_volume:.1f}%", 0, line1_v, scale=1.5)
        # AA
        msg="AA:100%"
        spacing = 33 # display.lcd.measure_text("ABV", 1.5) - display.lcd.measure_text("AA", 1.5)
        self.lcd.text(f"AA:{tilt_values.apparent_attenuation:.0f}%", spacing, line2_v, scale=1.5)
        self.lcd.set_thickness(1)
        # line3 rssi left aligned, RSSI:-52
        msg=f"RSSI:{tilt.rssi}"
        self.lcd.text(msg, 0, line3_v, scale=1)#0.8)
        # tilt colour
        msg=tilt.colour
        self.lcd.text(msg, r_align(self.lcd, msg, 1, width), line3_v, scale=1)#0.8)
        # OG
        n = 4 if tilt.hd else 3
        self.lcd.text(f"OG:{tilt_values.original_gravity:.{n}f}", 0, line4_v, scale=1)
        gc.collect()
        #t1 = time.ticks_ms()
        self.lcd.update()
        #t2 = time.ticks_ms()
        #print(f"extended drawing took:{time.ticks_diff(t1, t_start)}, update took:{time.ticks_diff(t2, t1)}")
        await asyncio.sleep(getattr(self.config, 'display_update_secs', 3))


class RGB_Driver():
    def __new__(cls, config: BridgeConfig):
        if not getattr(config, 'rgb_led_gpio', None):
            return None  # Prevent instance creation
        return super().__new__(cls)
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self._led = None
        self._led = RGBLED(*pins) if (pins := getattr(config, 'rgb_led_gpio', None)) else None
        self._led and self._led.set_rgb(0, 0, 0)
    
    def _loadRGBLED(self, *pins):
        if pins:
            # print(f"***  {pins=}")
            self._led = RGBLED(*pins)
            self._led.set_rgb(0,0,0)

    def off(self):
        # turn off
        self._led.set_rgb(0,0,0)
        
    #def _init_rgb_task(self):
    #    # ensure off at start
    #    self.rgb_led.set_rgb(0,0,0)

    async def _flash_rgb_task(self, rgb_colours):
        #
        self._led.set_rgb(*rgb_colours)
        await asyncio.sleep_ms(500)
        self._led.set_rgb(0,0,0)
    
    def flash(self, colour):
        if self._led:
            #
            if (_task := getattr(self, '_led_task', None)):
                _task.cancel()
            self._led_task = asyncio.create_task(self._flash_rgb_task(get_color_values(colour, getattr(self.config, 'rgb_brightness', 0.1))))


def c_align(lcd_obj, txt, sz, width):
    # return a offset from left 
    return int((width - lcd_obj.measure_text(txt, sz)) // 2)

def r_align(lcd_obj, txt, sz, width):
    # return a offset from left 
    return int(width - lcd_obj.measure_text(txt, sz))

__version__ = '0.0.1'
