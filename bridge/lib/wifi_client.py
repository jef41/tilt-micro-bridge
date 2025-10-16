"""manage wifi
todo: reboot device if wifi not working?
"""

import gc
import asyncio
import network
import logging
import time
import ntptime
import indicator
gc.collect()

# cyw43_wifi_link_status
error_codes_to_messages = {
    0: "STAT_IDLE",
    1: "STAT_CONNECTING",
    2: "STAT_GOT_IP",
    3: "STAT_LINK_UP",
    -1: "CYW43_CONNECT_FAIL",
    -2: "CYW43_NO_AP_FOUND",
    -3: "CYW43_WRONG_PASSWORD",
}

logger = logging.getLogger(__name__)

class WifiClient:
    def __init__(self, config):
        ''' manage & maintain the wifi connection '''
        self.nic = None
        self._ssid = config.ssid
        self._wifi_pw = config.password
        network.hostname("tilt_micro_bridge")
        try:
            #self._country = config.country_code
            network.country(config.country_code)
            #self.check_interval = config.wifi_check_interval
        except AttributeError:
            pass
        self.has_config = all((self._ssid, self._wifi_pw))
        self.onboard_led = indicator.Status(indicator.Status.WIFI_DISCONNECTED)

    async def connect(self, display=False):
        ''' externally call this method after testing has_config'''
        # ensure nic object exists & is active
        try:
            if self.nic.active():
                self.nic.active(False)
        except NameError:
            self.nic = network.WLAN(network.STA_IF)
        except AttributeError:
            self.nic = network.WLAN(network.STA_IF)
        finally:
            # here we have an inactive nic
            self.nic.config(pm = network.WLAN.PM_PERFORMANCE)
            self.nic.active(True)
            self.nic.connect(self._ssid, self._wifi_pw)
        # here could test _has_config & raise an error if not
        logger.info("Attempting to connect to wifi")    
        attempt = 0
        while not self.nic.isconnected():
            attempt += 1
            result = await self.wifi_connect()
            if result < 3:
                # wifi not connected
                if display:
                    if attempt == 1:
                        display.show_msg("Error connecting to WIFI:")
                    display.show_msg(f" {error_codes_to_messages[result]} ({attempt})")
                if result == -3:
                    if display:
                        display.show_msg("bad wifi password,\nstopping here.")
                    logger.error("bad wifi password, stopping here.")
                    raise OSError("Bad Password")
                else:
                    logger.debug("sleep 120 secs and try wifi again")
                    if display:
                        display.show_msg("trying again in 2 minutes.")
                        del display.startup_msg[-1] # remove that last message from list - it's hacky
                    self.nic.disconnect()
                    self.nic.active(False)
                    self.nic.deinit()
                    await asyncio.sleep(120) # 120 testing
                    self.nic.config(pm = network.WLAN.PM_PERFORMANCE)
                    self.nic.active(True)
                    self.nic.connect(self._ssid, self._wifi_pw)
                    if display:
                        display.show_msg("trying connection again") # hacky, but overwrites a line
                        del display.startup_msg[-1]
                        del display.startup_msg[-1]
                
        if self.nic.isconnected():
            asyncio.create_task(self._keep_connected())
            # Runs forever unless user issues .disconnect() TODO: test if cancelled

    async def wifi_connect(self):
        ''' internal function - call with an active & configured WLAN interface '''
        await self.onboard_led.set_status(indicator.Status.WIFI_CONNECTING)
        
        self.nic.connect(self._ssid, self._wifi_pw)
        catch = 0
        for _ in range(30):  # 30 testing
            # Loop while connecting or no IP. Break out on fail or success. Check once per sec.
            await asyncio.sleep(1)
            catch = self.nic.status() # can be a fleeting status, so capture it
            # print(catch)
            if self.nic.isconnected():
                logger.info("wifi connected")
                await self.onboard_led.set_status(indicator.Status.WIFI_CONNECTED)
                break
            if catch < 1:
                logger.warning(f"wifi reports {error_codes_to_messages[catch]}")
                await self.onboard_led.set_status(indicator.Status.WIFI_DISCONNECTED)
                break
        else:  # Timeout: still in connecting state
            logger.warning(f"wifi connect timed out {error_codes_to_messages[catch]}")
            await self.onboard_led.set_status(indicator.Status.WIFI_DISCONNECTED)
        #else:
        if self.nic.isconnected():
                # Ensure connection stays up for a few secs.
                logger.info("Checking wifi integrity")
                for _ in range(5):
                    if not self.nic.isconnected():
                        logger.warning("Connection Unstable")
                        #raise OSError("Connection Unstable")  # in 1st 5 secs
                    await asyncio.sleep(1)
                logger.info("Got reliable connection")
        #else:  # connection failed
        return catch #nic.status()

    async def _keep_connected(self):
        ''' Scheduled on 1st successful connection. Runs forever maintaining wifi '''
        while self.nic.active():
            logger.debug("running in _keep_connected")
            if self.nic.isconnected():  
                await asyncio.sleep(50)
            else:  # Link is down
                logger.warning("wifi connection is lost")
                try:
                    await self.connect()
                    # Now has set ._isconnected and scheduled _connect_handler().
                    self.onboard_led.set_status(indicator.Status.STATUS_OK)
                    logger.info("Reconnect OK!")
                except OSError as e:
                    logger.error(f"Error in reconnect. {e}")
                    # Can get ECONNABORTED or -1. The latter signifies no or bad CONNACK received.
                    self.nic.disconnect()
                    self.nic.active(False)
        logger.warning(f"exited _keep_connected {self.nic.isconnected()=}")

    def get_time(self, display):
        result = False
        ntptime.timeout = 5
        if self.nic.isconnected():
            try:
                ntptime.settime()
                logger.info("time set to UTC")
                result = True
            except Exception as e:
                # todo catch more specific exception
                logger.error(f"npttime.settime() timeout: {e}")
        else:
            logger.warning("npttime.settime() failed, no network connection")
        if display:
            if not result:
                display.show_msg("Error getting time")
            t = time.localtime()
            display.show_msg(f"time set {t[2]}-{t[1]}-{t[0]} {t[3]:02}:{t[4]:02}")
        return result


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


__version__ = "1.2.0"

