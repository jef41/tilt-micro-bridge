# an informal interface to ensure any proividers have the minimum functionality
from configuration import BridgeConfig

class BridgeProviderBase(BridgeConfig):
    
    def start(self):
        pass

    #def update(self, tilt_status: TiltStatus):
    def update(self):
        pass

    def enabled(self):
        return False