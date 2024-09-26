''' manage wifi
    todo: reboot device if wifi not working?
'''
import gc
import asyncio

gc.collect()
import network
import logging
from sys import platform

# debug/test: todo: remove
#import config
VERSION = (0, 0, 2)

RP2 = platform == "rp2"

#cyw43_wifi_link_status
error_codes_to_messages = {
   0: 'CYW43_LINK_DOWN',
   1: 'CYW43_LINK_JOIN',
   2: 'CYW43_LINK_NOIP',
   3: 'CYW43_LINK_UP',
   -1: 'CYW43_LINK_FAIL',
   -2: 'CYW43_LINK_NONET',
   -3: 'CYW43_LINK_BADAUTH'
   }

logger = logging.getLogger(__name__)

class WifiClient():
    def __init__(self, config):
        #self._isconnected = False  # Current connection state
        #self._ping_interval = 20000
        #self._in_connect = False
        #self._has_connected = False  # Define 'Clean Session' value to use.
        self.check_interval = 60 # check every n seconds
        self._sta_if = network.WLAN(network.STA_IF)
        self._ssid = config.ssid
        self._wifi_pw = config.password
        self._country = config.country_code
        # todo: allow _country is None

    async def wifi_connect(self, quick=False):
        s = self._sta_if
        s.active(True)
        if RP2:  # Disable auto-sleep.
            # https://datasheets.raspberrypi.com/picow/connecting-to-the-internet-with-pico-w.pdf
            # para 3.6.3
            s.config(pm=0xA11140)
            import rp2
            # todo: check if _country is None
            rp2.country(self._country)
        s.connect(self._ssid, self._wifi_pw)
        for _ in range(60):  # Break out on fail or success. Check once per sec.
            await asyncio.sleep(1)
            # Loop while connecting or no IP
            if s.isconnected():
                logger.info("Wifi connected")
                break
            if RP2:  # 1 is joining. 2 is No IP, ie in process of connecting
                if not 1 <= s.status() <= 3:
                    logger.debug(f"Wifi reports {error_codes_to_messages[s.status()]}")
                    break
        else:  # Timeout: still in connecting state
            s.disconnect()
            await asyncio.sleep(1)

        if not s.isconnected():  # Timed out
            logger.warning("Wifi connect timed out")
            raise OSError("Wi-Fi connect timed out")
        if not quick:  # Skip on first connection only if power saving
            # Ensure connection stays up for a few secs.
            #self.dprint("Checking WiFi integrity.")
            logger.info("Checking WiFi integrity.")
            for _ in range(5):
                if not s.isconnected():
                    logger.warning("Connection Unstable")
                    raise OSError("Connection Unstable")  # in 1st 5 secs
                await asyncio.sleep(1)
            #self.dprint("Got reliable connection")
            logger.info("Got reliable connection")

    async def connect(self, *, quick=False):  # Quick initial connect option for battery apps
        '''if not self._has_connected:
            await self.wifi_connect(quick)  # On 1st call, caller handles error
            # Note this blocks if DNS lookup occurs. Do it once to prevent
            # blocking during later internet outage:
            self._addr = socket.getaddrinfo(self.server, self.port)[0][-1]
        self._in_connect = True  # Disable low level ._isconnected check

        # If we get here without error broker/LAN must be up.
        self._isconnected = True
        self._in_connect = False  # Low level code can now check connectivity.
        if not self._events:
            asyncio.create_task(self._wifi_handler(True))  # User handler.
        if not self._has_connected:
            self._has_connected = True  # Use normal clean flag on reconnect.
        '''
        s = self._sta_if
        if not s.isconnected():
            await self.wifi_connect(quick)
        if s.isconnected():
            asyncio.create_task(self._keep_connected())
            # Runs forever unless user issues .disconnect()

    # Scheduled on 1st successful connection. Runs forever maintaining wifi and
    # broker connection. Must handle conditions at edge of WiFi range.
    async def _keep_connected(self):
        s = self._sta_if
        while True: # s.active():
            logger.debug("running in _keep_connected")
            if s.isconnected():  # Pause for 1 second
                #await asyncio.sleep(1) # todo: self.check_interval
                await asyncio.sleep(self.check_interval)
                gc.collect()
            else:  # Link is down
                try:
                    s.disconnect()
                except OSError:
                    #self.dprint("Wi-Fi not started, unable to disconnect interface")
                    logger.error("Wi-Fi not started, unable to disconnect interface")
                await asyncio.sleep(1)
                try:
                    await self.wifi_connect()
                except OSError:
                    continue
                #if not s.active():  # User has issued the terminal cmd to power off
                #    #self.dprint("Disconnected, exiting _keep_connected")
                #    logger.warning("Disconnected, exiting _keep_connected")
                #    break
                try:
                    await self.connect()
                    # Now has set ._isconnected and scheduled _connect_handler().
                    #self.dprint("Reconnect OK!")
                    logger.info("Reconnect OK!")
                except OSError as e:
                    #self.dprint("Error in reconnect. %s", e)
                    logger.error(f"Error in reconnect. {e}")
                    # Can get ECONNABORTED or -1. The latter signifies no or bad CONNACK received.
                    s.disconnect()
                    #self._close()  # Disconnect and try again.
                    #self._in_connect = False
                    #self._isconnected = False
        #self.dprint("Disconnected, exited _keep_connected")
        logger.warning("Disconnected, exited _keep_connected")



# Check internet connectivity by sending DNS lookup to Google's 8.8.8.8
async def wan_ok(
    self,
    packet=b"$\x1a\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03www\x06google\x03com\x00\x00\x01\x00\x01",
):
    if not self.isconnected():  # WiFi is down
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
