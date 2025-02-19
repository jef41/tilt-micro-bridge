import json
import os
import logging

logger = logging.getLogger('BridgeConfig')

class BridgeConfig:

    def __init__(self, data: dict):
        # Wifi
        self.ssid = None
        self.password = None
        self.country_code = None
        self.wifi_check_interval = 600
        # Queue
        self.queue_size = 15
        self.queue_empty_sleep_seconds = 1
        self.averaging_period = 30 # 0 21000
        # Broadcast Data ranges
        self.temp_range_min = 32
        self.temp_range_max = 212
        self.gravity_range_min = 0.7
        self.gravity_range_max = 1.4
        # Webhook
        self.webhook_urls = list()
        self.webhook_limit_rate = 1
        self.webhook_limit_period = 1
        # CSV File
        self.csv_log_max_kb = 60
        self.csv_log_temp_unit = "C"
        self.csv_log_period = 60
        #self.csv_log_averaging_period = 60
        self.csv_log_tilt_colours = None
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
        #self.grainfather_averaging_period = 300
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

    #def get_gravity_offset(self, colour: str):
    #    return self.__dict__.get(colour + '_gravity_offset', 0)

    def get_temp_offset(self, colour: str):
        return self.__dict__.get(colour + '_temp_offset', 0)

    def get_brew_name(self, colour: str):
        return self.__dict__.get(colour + '_name', colour)

    def get_gravity_offsets(self, colour: str):
        ''' return a list of offsets
            where in each pair 1st value = raw, 2nd value = reference point
                [[1.000,1.000],[1.100,1.100]]
        '''
        #logger.debug(f"cal values: {self.__dict__.get(colour + '_gravity_offsets')}")
        #TODO add -0.0001 & 10**5 pairs and order the list here, convert to tuple
        #Tilt App does this:
        cal_vals = None
        cfg_cal_vals = self.__dict__.get(colour + '_gravity_offsets')
        if cfg_cal_vals:
            cal_vals = [ [-0.001,-0.001], [10**5,10**5] ] + cfg_cal_vals
            cal_vals.sort(key=lambda x: x[1]) # sort by 2nd value in list
        return cal_vals


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
