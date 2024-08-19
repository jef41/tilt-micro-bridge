# Payload for Tilt expects a SG & Temp in Farenheit
# will display on GF website in user preferred units configured in preferences on that platform
# {
#     "SG": 1.034, //this must be a numeric value
#     "Temp: 70, //this must be numeric
# }

from ..models import TiltStatus
from ..abstractions import CloudProviderBase
from ..configuration import PitchConfig
from ..rate_limiter import DeviceRateLimiter
from interface import implements
import requests
import json


class GrainfatherTiltStreamCloudProvider(implements(CloudProviderBase)):

    def __init__(self, config: PitchConfig):
        self.color_urls = GrainfatherTiltStreamCloudProvider._normalize_color_keys(config.grainfather_tilt_stream_urls)
        self.temp_unit = GrainfatherTiltStreamCloudProvider._get_temp_unit(config)
        self.str_name = "Grainfather Tilt URL"
        self.rate_limiter = DeviceRateLimiter(rate=1, period=(60 * 15))  # 15 minutes

    def __str__(self):
        return self.str_name

    def start(self):
        pass

    def update(self, tilt_status: TiltStatus):
        # Skip if this color doesn't have a grainfather URL assigned
        if tilt_status.color not in self.color_urls.keys():
            return
        url = self.color_urls[tilt_status.color]
        self.rate_limiter.approve(tilt_status.color)
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        payload = self._get_payload(tilt_status)
        result = requests.post(url, headers=headers, data=json.dumps(payload))
        result.raise_for_status()

    def enabled(self):
        return True if self.color_urls else False
    
    def _get_payload(self, tilt_status: TiltStatus):
        return {
            "SG": tilt_status.gravity,
            "Temp": tilt_status.temp_fahrenheit
        }

    # takes dict of color->urls
    # returns dict with all colors in lowercase letters for easier matching later
    @staticmethod
    def _normalize_color_keys(color_urls):
        normalized_colors = dict()
        if color_urls is not None:
            for color in color_urls:
                normalized_colors[color.lower()] = color_urls[color]

        return normalized_colors
