import json
import os
import logging

logger = logging.getLogger('BridgeConfig')

class BridgeConfig:

    def __init__(self, data: dict):
        # Wifi
        self.ssid = None
        self.password = None
        # Queue
        self.queue_size = 15
        self.queue_empty_sleep_seconds = 1
        self.averaging_period = 60 # 0 21000
        # Broadcast Data ranges
        self.temp_range_min = 32
        self.temp_range_max = 212
        self.gravity_range_min = 0.7
        self.gravity_range_max = 1.4
        # Webhook
        self.webhook_urls = list()
        self.webhook_limit_rate = 1
        self.webhook_limit_period = 1
        # File Path
        self.log_file_path = 'tilt_bridge.log'
        self.log_file_max_mb = 10
        # Prometheus
        self.prometheus_enabled = True
        self.prometheus_port = 8000
        # InfluxDB
        self.influxdb_hostname = None
        self.influxdb_database = None
        self.influxdb_port = None
        self.influxdb_username = None
        self.influxdb_password = None
        self.influxdb_batch_size = 10
        self.influxdb_timeout_seconds = 5
        # InfluxDB2
        self.influxdb2_url = None
        self.influxdb2_org = None
        self.influxdb2_token = None
        self.influxdb2_bucket = None
        # Brewfather
        self.brewfather_custom_stream_url = None
        self.brewfather_custom_stream_temp_unit = "F"
        # Taplist.io
        self.taplistio_url = None
        # Brewersfriend
        self.brewersfriend_api_key = None
        self.brewersfriend_temp_unit = "F"
        # Grainfather
        self.grainfather_temp_unit = "C"
        self.grainfather_averaging_period = 300
        # Grainfather custom (choose to send C or F)
        self.grainfather_custom_stream_urls = None
        # Grainfather (appear as Tilt device)
        self.grainfather_tilt_stream_urls = None
        # Azure IoT Hub
        self.azure_iot_hub_connectionstring = None
        self.azure_iot_hub_limit_rate = 8000 # free tier 8000msg per day
        self.azure_iot_hub_limit_period = 86400 # free tier 8000msg per day
        # Load user inputs from config file
        self.update(data)

    def update(self, data: dict):
        #self.__dict__.update(data)
        for key in data:
            setattr(self, key, data[key])
            #print(f"{key} : {data[key]}")

    def get_original_gravity(self, colour: str):
        return self.__dict__.get(colour + '_original_gravity')

    def get_gravity_offset(self, colour: str):
        return self.__dict__.get(colour + '_gravity_offset', 0)

    def get_temp_offset(self, colour: str):
        return 0 #self.__dict__.get(colour + '_temp_offset', 0) #does this return hang onto memory if so maybe because called async??

    def get_brew_name(self, colour: str):
        return self.__dict__.get(colour + '_name', colour)


    @staticmethod
    def load(additional_config: dict = None):
        file_path = "/config.json"
        config_raw = dict()

        try:
            with open(file_path, "r") as file:
                config_raw = json.load(file)
            logger.debug(f"got config {config_raw}")
        except OSError:
            logger.error(f"config file not found ({file_path})")
            pass

        config = BridgeConfig(config_raw)
        if additional_config is not None:
            config.update(additional_config)

        return config
