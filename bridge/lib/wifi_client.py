''' manage wifi & status led from indicator module
'''

import gc
import asyncio
import network
import logging
import time # time with strftime overrides
import ntptime
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
    def __init__(self, config, onboard_led, lcd=False):
        ''' manage & maintain the wifi connection '''
        self.nic = None
        self.keep_alive = None
        self._ssid = config.ssid
        self._wifi_pw = config.password
        self.display = lcd
        network.hostname("tilt-micro-bridge")
        try:
            #self._country = config.country_code
            network.country(config.country_code)
            #self.check_interval = config.wifi_check_interval
        except AttributeError:
            pass
        self.has_config = all((self._ssid, self._wifi_pw))
        self.status_led = onboard_led
        self.status_led.set_status(self.status_led.WIFI_DISCONNECTED)

    async def connect(self):
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
                # wifi not connected, some sort of error
                if self.display:
                    if attempt == 1:
                        await self.display.show_msg("Error connecting to wifi:")
                    else:
                        del self.display.startup_msg[-1] # remove try again msg
                    await self.display.show_msg(f" {error_codes_to_messages[result]} ({attempt})")
                if result == -3:
                    if self.display:
                        await self.display.show_msg("bad wifi password,\nstopping here.")
                    logger.error("bad wifi password, stopping here.")
                    raise OSError("Bad Password")
                else:
                    logger.debug("sleep 120 secs and try wifi again")
                    if self.display:
                        await self.display.show_msg("trying again after 2 mins")
                        #del self.display.startup_msg[-1] # remove that last message from list - it's hacky
                    self.nic.disconnect()
                    self.nic.active(False)
                    self.nic.deinit()
                    await asyncio.sleep(120) # 120 testing
                    self.nic.config(pm = network.WLAN.PM_PERFORMANCE)
                    self.nic.active(True)
                    self.nic.connect(self._ssid, self._wifi_pw)
                    if self.display:
                        del self.display.startup_msg[-1] # wifi err
                        del self.display.startup_msg[-1] # try again
                        await self.display.show_msg("trying connection again") # hacky, but overwrites a line
                
        if self.nic.isconnected() and not self.keep_alive:
            self.keep_alive = asyncio.create_task(self._keep_connected())
            logger.debug("keep_alive task created")
            # should be called once & run forever 

    async def wifi_connect(self):
        ''' internal function - call with an active & configured WLAN interface '''
        await self.status_led.set_status(self.status_led.WIFI_CONNECTING)
        
        self.nic.connect(self._ssid, self._wifi_pw)
        catch = 0
        for _ in range(30):  # 30 testing
            # Loop while connecting or no IP. Break out on fail or success. Check once per sec.
            await asyncio.sleep(1)
            catch = self.nic.status() # can be a fleeting status, so capture it
            # print(catch)
            if self.nic.isconnected():
                logger.info("wifi connected")
                await self.status_led.set_status(self.status_led.WIFI_CONNECTED)
                break
            if catch < 1:
                logger.warning(f"wifi reports {error_codes_to_messages[catch]}")
                await self.status_led.set_status(self.status_led.WIFI_DISCONNECTED)
                break
        else:  # Timeout: still in connecting state
            logger.warning(f"wifi connect timed out {error_codes_to_messages[catch]}")
            await self.status_led.set_status(self.status_led.WIFI_DISCONNECTED)
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
        #nic is proabbly active at start so could be while True:
        datefmt = "%Y-%m-%d %H:%M:%S"
        initial_run = True
        while True: # self.nic.active():
            logger.debug("running in _keep_connected")
            if not initial_run:
                self.display.startup_msg = [] # clear any stale connection messages
            if self.nic.isconnected():
                if self.display and initial_run:
                    initial_run = False
                await asyncio.sleep(50) #testing 50
            else:  # Link is down
                logger.warning("wifi connection is lost")
                if self.display:
                    #await self.display.show_msg("wifi connection down")
                    #t = time.gmtime()
                    await self.display.show_msg(f"wifi connection lost at")
                    #await self.display.show_msg(f"{t[2]}-{t[1]}-{t[0]} {t[3]:02}:{t[4]:02}:{t[5]:02} UTC")
                    if hasattr(time, "strftime"):
                        await self.display.show_msg(f"{time.strftime(datefmt, time.gmtime())} UTC")
                try:
                    await self.connect()
                    # Now has set ._isconnected and scheduled _connect_handler().
                    await self.status_led.set_status(self.status_led.STATUS_OK)
                    logger.info("Reconnect OK!")
                    if self.display:
                        await self.display.show_msg("wifi reconnected")
                except OSError:
                    logger.error("OSError in reconnect. {e}")
                    # Can get ECONNABORTED or -1. The latter signifies no or bad CONNACK received.
                    self.nic.disconnect()
                    self.nic.active(False)
                except Exception as e:
                    logger.error(f"Error in reconnect. {e}")
                    # some unkonwn error, try again
                    self.nic.disconnect()
                    self.nic.active(False)
                    del self.nic
                    self.nic = None
        logger.warning(f"exited _keep_connected {self.nic.isconnected()=}")

    def get_time(self):
        result = False
        ntptime.timeout = 5
        datefmt = "%Y-%m-%d %H:%M:%S"
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
        if self.display:
            if not result:
                await self.display.show_msg("Error getting time")
            #t = time.localtime()
            #await self.display.show_msg(f"time set {t[2]}-{t[1]}-{t[0]} {t[3]:02}:{t[4]:02}")
            if hasattr(time, "strftime"):
                await self.display.show_msg(f"time: {time.strftime(datefmt, time.gmtime())}")
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


