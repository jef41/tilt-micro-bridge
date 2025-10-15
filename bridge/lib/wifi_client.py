"""manage wifi
todo: reboot device if wifi not working?
"""

import gc
import asyncio

gc.collect()
import network
import logging
from random import randrange
from sys import platform

RP2 = platform == "rp2"
'''
# cyw43_wifi_link_status
error_codes_to_messages = {
    0: "CYW43_LINK_DOWN",
    1: "CYW43_LINK_JOIN",
    2: "CYW43_LINK_NOIP",
    3: "CYW43_LINK_UP",
    -1: "CYW43_LINK_FAIL",
    -2: "CYW43_LINK_NONET",
    -3: "CYW43_LINK_BADAUTH",
}'''
# cyw43_wifi_link_status
error_codes_to_messages = {
    0: "STAT_IDLE",
    1: "STAT_CONNECTING",
    2: "STAT_GOT_IP",
    3: "CYW43_LINK_UP",
    -1: "STAT_CONNECT_FAIL",
    -2: "STAT_NO_AP_FOUND",
    -3: "STAT_WRONG_PASSWORD",
}

logger = logging.getLogger(__name__)


class WifiClient:
    def __init__(self, config):
        # self._isconnected = False  # Current connection state
        # self._ping_interval = 20000
        # self._in_connect = False
        # self._has_connected = False  # Define 'Clean Session' value to use.
        self.nic = network.WLAN(network.STA_IF)
        self._ssid = config.ssid
        self._wifi_pw = config.password
        try:
            self._country = config.country_code
            self.check_interval = config.wifi_check_interval
        except AttributeError:
            self._country = None
            self.check_interval = 3600  # check every n seconds
        self.has_config = all((self._ssid, self._wifi_pw))

    async def wifi_connect(self, onboard_led, quick=False):
        await onboard_led.set_status(onboard_led.WIFI_CONNECTING)
        #nic = self._sta_if
        #nic.disconnect()
        #nic.active(False)
        '''if RP2:  # Disable auto-sleep.
            # https://datasheets.raspberrypi.com/picow/connecting-to-the-internet-with-pico-w.pdf
            # para 3.6.3
            nic.config(pm=0xA11140)
            import rp2

            if self._country:
                rp2.country(self._country)'''
        self.nic.deinit()
        self.nic = network.WLAN(network.STA_IF)
        network.hostname("tilt_micro_bridge")
        self.nic.config(pm = network.WLAN.PM_PERFORMANCE)
        if self._country:
            network.country(self._country)
        logger.info("Attempting to connect to wifi")
        self.nic.active(True)
        self.nic.connect(self._ssid, self._wifi_pw)
        catch = 0
        for _ in range(30):  # Break out on fail or success. Check once per sec.
            catch = self.nic.status() # can be a fleeting status, so capture it
            # print(catch)
            # Loop while connecting or no IP
            if self.nic.isconnected():
                logger.info("wifi connected")
                await onboard_led.set_status(onboard_led.WIFI_CONNECTED)
                break
            #if RP2:  # 1 is joining. 2 is No IP, ie in process of connecting
            #    if not 1 <= nic.status() <= 3:
            if catch < 1:
                logger.warning(f"wifi reports {error_codes_to_messages[catch]}")
                break
            await asyncio.sleep(1)
        else:  # Timeout: still in connecting state
            await onboard_led.set_status(onboard_led.WIFI_DISCONNECTED)
            await asyncio.sleep(1)
            #if not nic.isconnected():  # Timed out
            logger.warning(f"wifi connect timed out {error_codes_to_messages[catch]}")
            #raise OSError("Wi-Fi connect timed out")
        #else:
        if self.nic.isconnected():
            if not quick:  # Skip on first connection only if power saving
                # Ensure connection stays up for a few secs.
                logger.info("Checking wifi integrity")
                for _ in range(5):
                    if not self.nic.isconnected():
                        logger.warning("Connection Unstable")
                        #raise OSError("Connection Unstable")  # in 1st 5 secs
                    await asyncio.sleep(1)
                logger.info("Got reliable connection")
        else:  # reset nic
            self.nic.disconnect()
            self.nic.active(False)
            self.nic.deinit()
        return catch #nic.status()

    async def connect(
        self, onboard_led, display=False, quick=False
    ):  # Quick initial connect option for battery apps
        #nic = self._sta_if
        attempt = 0
        while not self.nic.isconnected():
            if attempt > 0 and display:
                display.show_msg("trying connection again")
                del display.startup_msg[-1]
            attempt += 1
            result = await self.wifi_connect(onboard_led, quick)
            if result < 2:
                # wifi not connected
                if display:
                    display.show_msg(f"{error_codes_to_messages[result]} ({attempt})", append = (False if attempt>1 else True))
                if result == -3:
                    if display:
                        display.show_msg("bad wifi password,\nstopping here.")
                    logger.error("bad wifi password, stopping here.")
                    raise OSError("Bad Password")
                else:
                    logger.debug("sleep 120 secs and try wifi again")
                    if display:
                        display.show_msg("trying again in 2 minutes.")
                        del display.startup_msg[-1] #remove that last message from list - it's hacky
                    await asyncio.sleep(120)
                
        if self.nic.isconnected():
            if self.check_interval > 0:
                asyncio.create_task(self._keep_connected())
                # Runs forever unless user issues .disconnect()
            else:
                logger.info("wifi connection checks disabled")

    # Scheduled on 1st successful connection. Runs forever maintaining wifi and
    # broker connection. Must handle conditions at edge of wifi range.
    async def _keep_connected(self):
        #nic = self._sta_if
        while True:  # nic.active():
            logger.debug("running in _keep_connected")
            if self.nic.isconnected():  # Pause for 1 second
                # await asyncio.sleep(1) # debug
                await asyncio.sleep(
                    randrange(
                        int(self.check_interval * 0.8), int(self.check_interval * 1.2)
                    )
                )
                gc.collect()
            else:  # Link is down
                try:
                    self.nic.disconnect()
                except OSError:
                    logger.error("Wi-Fi not started, unable to disconnect interface")
                await asyncio.sleep(1)
                try:
                    await self.wifi_connect()
                except OSError:
                    continue
                try:
                    await self.connect()
                    # Now has set ._isconnected and scheduled _connect_handler().
                    logger.info("Reconnect OK!")
                except OSError as e:
                    logger.error(f"Error in reconnect. {e}")
                    # Can get ECONNABORTED or -1. The latter signifies no or bad CONNACK received.
                    self.nic.disconnect()
        logger.warning("Disconnected, exited _keep_connected")


# Check internet connectivity by sending DNS lookup to Google's 8.8.8.8
async def wan_ok(
    self,
    packet=b"$\x1a\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03www\x06google\x03com\x00\x00\x01\x00\x01",
):
    if not self.isconnected():  # wifi is down
        return False
    length = 32  # DNS query and response packet size
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setblocking(False)
    s.connect(("8.8.8.8", 53))
    await asyncio.sleep(1)
    try:
        await self._as_write(packet, sock=s)
        await asyncio.sleep(2)
        res = await self._as_read(length, s)
        if len(res) == length:
            return True  # DNS response size OK
    except OSError:  # Timeout on read: no connectivity.
        return False
    finally:
        s.close()
    return False


__version__ = "1.0.2"
