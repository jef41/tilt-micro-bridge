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
        # print("brightness set")
        #self.WIDTH, self.HEIGHT = self.lcd.get_bounds()
        #print(f"some variables: {self.WIDTH}, {self.HEIGHT}, {getattr(self.config, 'lcd_brightness', 0.2)}")]
        # Create palette mapping dynamically
        self.colour_to_palette = {
            colour: self.lcd.create_pen(*get_color_values(colour, 1)) for colour in palette_cols
        }

        #except Exception as e:
        #    # print(f"error loading LCD GPIO pins {e}")
        #    raise
    
        #def start_cards(colours, devices):
        #    #
        #    pass
    
    async def card_stack(self, tilt_data_store: TiltHistory, cards: TiltDevice): #: TiltDevice
        # TODO backlight issue - when called with custom SPI set_backlight is not available
        # 		uncal values need scaling
        #		tidy up
        # better to look up config once & save value or look up each time?
        # LED v bright at startup
        # sort out waiting for data message - too big
        # test not having SPI pins in config - no LCD loaded & no task?
        # some sort of loading screen
        # handle extended info
        spacing = None
        sg, temp, uncal_sg, uncal_temp, rssi = None, None, None, None, None
        msg=bytearray(12)
        self.lcd.set_font("serif")
        #enabled_tilts.add("clock")
        #self.cards.append(TiltDevice('clock'))
        # TODO add a page for each Tilt that has OG, beer name
        while True:
            index = 0
            WIDTH, HEIGHT = self.lcd.get_bounds()
            for tilt in cards:
                #print(f"loop {enabled_colours}")
                #if tilt_colour == "clock":
                if index == 0:
                    # print("show clock")
                    await self.update_clock()
                #else:
                # TODO move this to a def
                # TODO some of this is static, calculate once & store
                t_start = time.ticks_ms()
                # TODO trap KeyError, log error & use white
                # TODO build TiltDevice object - colour, rssi
                #rssi = str(random.randint(10, 100)*-1)
                uncal_temp, uncal_sg, tilt_values = self.read_latest_vals(tilt_data_store, tilt.colour)
                n = 4 if tilt.hd else 3
                self.lcd.set_pen(self.colour_to_palette["BG"])
                self.lcd.clear()
                self.lcd.set_thickness(3)
                #lcd.text(text, x, y, wordwrap, scale, angle, spacing)
                self.lcd.set_pen(self.colour_to_palette[tilt.colour.upper()])
                if all([uncal_sg, uncal_temp, tilt_values]):
                    msg=f"SG:{tilt_values.gravity:.{n}f}"
                    self.lcd.text(msg, 0, 20, scale=1.5)
                    offset=46
                    temp = f"{tilt_values.temp_celsius:.1f}" if getattr(self.config, 'default_temp_unit') == "C" else f"{tilt_values.temp_fahrenheit:.1f}"
                    self.lcd.text(temp, offset, 65, scale=1.5)
                    spacing = self.lcd.measure_text(temp, 1.5) #, spacing, fixed_width)
                    #print(spacing)
                    msg="°"
                    self.lcd.text(msg, offset+spacing, 43, scale=0.75)
                    #lcd.character(176, spacing, 43, scale=1)
                    spacing += self.lcd.measure_text(msg, 0.75)
                    #print(spacing)
                    msg = getattr(self.config, 'default_temp_unit')
                    self.lcd.text(msg, offset+spacing, 65, scale=1.5)
                    spacing += self.lcd.measure_text(msg, 1.5)
                    #print(spacing)
                    self.lcd.set_thickness(1)
                    msg=f"RSSI:{tilt.rssi}"
                    self.lcd.text(msg, 0, 100, scale=0.8)
                    msg=f"{tilt.colour}"
                    spacing = WIDTH - self.lcd.measure_text(msg, 0.8)
                    msg=f"{tilt.colour}"
                    self.lcd.text(msg, spacing, 100, scale=0.8)
                    msg=f"{uncal_temp:.1f}  {uncal_sg:.{n}f}"
                    self.lcd.text(msg, 0, 120, scale=0.8)
                else:
                    #we are missing data
                    msg=f"Waiting for\nData"
                    self.lcd.text(msg, 0, 65, scale=1)
                gc.collect()
                t1 = time.ticks_ms()
                self.lcd.update()
                t2 = time.ticks_ms()
                # print(f"drawing took:{time.ticks_diff(t1, t_start)}, update took:{time.ticks_diff(t2, t1)}")
                await asyncio.sleep(getattr(self.config, 'display_update_secs', 3))
                og = self.config.get_original_gravity(tilt.colour)
                #f tilt.extended:
                #    # if og:
                #    # draw a page of extended attributes, OG, ABV, attenuation
                #    pass
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
            #tempC = tilt_status.temp_celsius
            #SG = tilt_status.gravity
            #uncal_SG *= 0.0001 if uncal_SG > 1200 else 0.001
        else:
            #logger.info(f"{colour} has no data")
            uncal_temp, uncal_gravity, tilt_status = None, None, None
        return (uncal_temp, uncal_gravity, tilt_status)

    async def update_clock(self):
        # show a clock or a MOTD or something
        #led.set_rgb(0, 0, 0)
        WIDTH, HEIGHT = self.lcd.get_bounds()
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
            offset  = (WIDTH - self.lcd.measure_text(time_now, 1.5)) // 2
            self.lcd.text(time_now, offset, 65, scale=1.5)
            self.lcd.update()
            await asyncio.sleep(1)
            # TODO subtract processing time from 1 second ticks_diff    


class RGB_Driver():
    def __new__(cls, config: BridgeConfig):
        if not getattr(config, 'rgb_led_gpio', None):
            return None  # Prevent instance creation
        return super().__new__(cls)
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self._led = None
        #rgb_led = self._loadRGBLED(getattr(config, 'rgb_led_gpio', False))
        #pins = getattr(config, 'rgb_led_gpio', False)
        #if pins:
        #    #self.rgb_led = self._loadRGBLED(6,7,8)
        #    self._led=RGBLED(*pins)
        #    #self._loadRGBLED(*pins)
        self._led = RGBLED(*pins) if (pins := getattr(config, 'rgb_led_gpio', None)) else None
        self._led and self._led.set_rgb(0, 0, 0)
    
    def _loadRGBLED(self, *pins):
        if pins:
            # print(f"***  {pins=}")
            self._led = RGBLED(*pins)
            #self.set_rgb(100,0,0)
            #asyncio.sleep_ms(500)
            self._led.set_rgb(0,0,0)
            #self.rgb_task = asyncio.create_task(self._init_rgb_task())
        #else:
        #    rgb_led = None
        #return rgb_led

    def off(self):
        # turn off
        self._led.set_rgb(0,0,0)
        
    #def _init_rgb_task(self):
    #    # ensure off at start
    #    self.rgb_led.set_rgb(0,0,0)

    async def _flash_rgb_task(self, rgb_colours):
        #print("Hi we are here now")
        self._led.set_rgb(*rgb_colours)
        await asyncio.sleep_ms(500)
        self._led.set_rgb(0,0,0)
    #while True:
    #    asyncio sleep(8)
    
    def flash(self, colour):
        if self._led:
            #if getattr(self, '_led_task', False):
            #    self._led_task.cancel()
            if (_task := getattr(self, '_led_task', None)):
                _task.cancel()
            #self.rgb_task = asyncio.create_task(self._flash_rgb_task(colour))
            #TODO load brightness here
            #vals=get_color_values(colour)
            #print(f"{vals=}")
            #self._led.set_rgb(*vals)
            #bns=getattr(self.config, 'rgb_brightness', 0.01)
            #print(f"{bns=}")
            #colval = get_color_values(colour, getattr(self.config, 'rgb_brightness', 0.5))
            #print(f"{colval=}")
            self._led_task = asyncio.create_task(self._flash_rgb_task(get_color_values(colour, getattr(self.config, 'rgb_brightness', 0.1))))
            #asyncio.sleep_ms(500)
            #self._led.set_rgb(0,0,0)

    