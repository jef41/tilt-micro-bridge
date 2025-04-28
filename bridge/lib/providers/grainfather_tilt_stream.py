# GF expects an SG & Temp in Farenheit
# will display on GF website in user preferred units configured in preferences on that platform
# {
#     "SG": 1.034, //this must be a numeric value
#     "Temp: 70, //this must be numeric
# }

import logging
from models import TiltStatus
from models import TiltHistory
from abstractions import BridgeProviderBase
from configuration import BridgeConfig
import asyncio
import aiohttp
import json
import gc
from machine import Timer
import network
from .grainfather_custom_stream import GrainfatherCustomStreamCloudProvider  # Import base class

logger = logging.getLogger('GFtilt_pvdr')
logger.info("Startup")

class GrainfatherTiltStreamCloudProvider(GrainfatherCustomStreamCloudProvider):

    def __init__(self, config: BridgeConfig):
        super(GrainfatherTiltStreamCloudProvider, self).__init__(config)  # Call parent constructor
        self.col_dest = GrainfatherTiltStreamCloudProvider._normalise_colour_keys(config.grainfather_tilt_stream_urls)
        self.str_name = "Grainfather Tilt URL"

    def _get_payload(self, tilt_status: TiltStatus):
        # GF payload data format
        return {
            "SG": tilt_status.gravity,
            "Temp": tilt_status.temp_fahrenheit
        }