"""manage the Pico onboard LED
TODO could verify that we are on a Pico & if not try to import the pin number from pin_mapping
"""

from machine import Pin
import time
import asyncio


class Status:
    STATUS_OK = (10, 3000)
    WIFI_CONNECTING = (10, 400)
    WIFI_CONNECTED = (200, 800)
    WIFI_DISCONNECTED = (800, 200)
    STARTUP = (500, 0)
    STATUS_ERROR = (500, 0)
    """ 
        an indicator LED
    """

    def __init__(self, status=STARTUP):
        self.led = Pin("LED", Pin.OUT)
        self.on_period = status[0]  # ms
        self.off_period = status[1]  # ms
        self.blinky = asyncio.create_task(self._blink_led())
        # asyncio.run(self._start())

    async def _blink_led(self):
        # led = Pin('LED', Pin.OUT)
        # print("called led blink")
        while True:
            if self.off_period == 0:
                # print("led solid on")
                self.led.on()  # otherwsie acts as a sort of 'busy' indicator
                await asyncio.sleep_ms(self.on_period + 10)
            else:
                # print("led blink")
                self.led.on()
                await asyncio.sleep_ms(self.on_period)
                self.led.off()
                await asyncio.sleep_ms(self.off_period)

    async def change_rate(self, on_ms, off_ms):
        self.on_period = on_ms
        self.off_period = off_ms
        # self.blinky.cancel()
        # self.blinky = asyncio.create_task(self._blink_led())

    async def set_status(self, status):
        # probably use this instead of change rate
        on_ms, off_ms = status
        self.on_period = on_ms
        self.off_period = off_ms

    async def off(self):
        self.blinky.cancel()
        self.led.off()

    # async def _start(self):
    #    self.blinky = asyncio.create_task(self._blink_led())

    def on(self):
        self.led.on()


async def test():
    # call this with:
    # import indicator, asyncio
    # asyncio.run(indicator.test())
    ob_led = Status()
    await asyncio.sleep_ms(2_000)
    await ob_led.change_rate(800, 200)
    await asyncio.sleep_ms(4_500)
    await ob_led.off()


__version__ = "1.0.0"
