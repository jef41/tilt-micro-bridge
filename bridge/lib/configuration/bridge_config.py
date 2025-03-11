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
        self.wifi_check_interval = 3600
        # Debug log
        self.debug_log = [20, 1]
        # Defaults
        self.default_averaging_period = 30
        self.default_temp_unit = "C"
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
        self.csv_log_period = 60
        self.csv_bkp_count = 4
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
        #return getattr(self,colour + '_original_gravity', None)

    #def get_temp_offset(self, colour: str):
    #    return self.__dict__.get(colour + '_temp_offset', 0)

    def get_brew_name(self, colour: str):
        return self.__dict__.get(colour + '_name', colour)
        #return getattr(self, colour + '_name', colour)

    def get_gravity_offsets(self, colour: str):
        ''' return a list of offsets
            where in each pair 1st value = raw, 2nd value = reference point;
                [[1.002,1.000],[1.107,1.100]]
        '''
        cal_vals = self.__dict__.get(colour + '_gravity_offsets')
        #cal_vals = getattr(self, colour + '_gravity_offsets')
        return cal_vals

    def get_temp_offsets(self, colour: str):
        ''' return a list of offsets
            index 0 is 'F' or 'C'
            each following pair 1st value = raw, 2nd value = reference point;
                ['C', [5.5,5.0],[25.1,25.0]]
        '''
        #cal_vals = list(self.__dict__.get(colour + '_temp_offsets'))
        cal_vals = list(getattr(self, colour + '_temp_offsets', []))
        # make a new variable, not pointer to same one
        try:
            if cal_vals[0].upper() == 'C':
                #convert to F
                cal_vals.pop(0)
                cal_vals =[[(temp * 9/5) + 32 for temp in pair] for pair in cal_vals]
            else:
                cal_vals.pop(0)
        except Exception as e:
            cal_vals = None
            # print(e)
            raise type(e)(f"Error in bridge config: {e}") from e
        finally:
            #print(f"cal vals:{cal_vals}")
            return cal_vals

    def get_temp_unit(self, lookup_key, name=False):
        ''' Look up a provider temp_unit key in config, fall back to default config.temp_unit,
           and return either a single char or the full name (e.g., C or celsius).
        '''
        #temp_unit = self.__dict__.get(lookup_key, getattr(self, "default_temp_unit", "C"))
        temp_unit = getattr(self, lookup_key, self.default_temp_unit)

        if temp_unit not in ("C", "c", "F", "f"):
            raise ValueError(f"{lookup_key} temp unit must be specified as 'C' or 'F'")

        if temp_unit in ("C", "c"):
            return "celsius" if name else "C"
        
        return "fahrenheit" if name else "F"

    def get_averaging_period(self, lookup_key):
        ''' look up the provider averaging period,
            if not present fall back to the default averaging period
            return an integer of seconds
        '''
        #return self.__dict__.get(lookup_key, getattr(self, lookup_key, self.default_averaging_period))
        return getattr(self, lookup_key, self.default_averaging_period)
    
    @staticmethod
    def load(additional_config: dict = None):
        file_path = "/config.json"
        config_raw = dict()

        try:
            with open(file_path, "r") as file:
                config_raw = json.load(file)
            logger.debug(f"got config {config_raw}")
        except OSError:
            logger.critical(f"config file not found ({file_path})")
            raise

        config = BridgeConfig(config_raw)
        if additional_config is not None:
            config.update(additional_config)

        return config
