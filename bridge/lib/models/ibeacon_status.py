from bluetooth import UUID

uuid_to_colours = {
    UUID("a495bb20-c5b1-4b44-b512-1370f02d74de"): "green",
    UUID("a495bb30-c5b1-4b44-b512-1370f02d74de"): "black",
    UUID("a495bb10-c5b1-4b44-b512-1370f02d74de"): "red",
    UUID("a495bb60-c5b1-4b44-b512-1370f02d74de"): "blue",
    UUID("a495bb50-c5b1-4b44-b512-1370f02d74de"): "orange",
    UUID("a495bb70-c5b1-4b44-b512-1370f02d74de"): "yellow",
    UUID("a495bb40-c5b1-4b44-b512-1370f02d74de"): "purple",
    UUID("a495bb80-c5b1-4b44-b512-1370f02d74de"): "pink",
    UUID(
        "a495bb90-c5b1-4b44-b512-1370f02d74de"
    ): "simulated",  # reserved for fake beacons during simulation mode
}

colours_to_uuid = dict((v, k) for k, v in uuid_to_colours.items())


class iBeaconStatus:

    def __init__(self, adv_data, rssi, mac_rdm):
        self.rssi = rssi
        self.uuid = UUID("".join(["{:02X}".format(b) for b in adv_data[9:25]]))
        self.major = int.from_bytes(adv_data[25:27], "big")  # Major (2 bytes) Temp
        self.minor = int.from_bytes(adv_data[27:29], "big")  # Minor (2 bytes) SG
        if int.from_bytes(adv_data[29:30], "big") > 152:
            self.tx_power = (255 - adv_data[29] +1 ) * -1 # TX Power (1 byte) 2's complement?
        else:
            self.batt_weeks = int.from_bytes(adv_data[29:30], "big") # (255 - adv_data[29] +1 ) * -1 # TX Power (1 byte) 2's complement?
        #print(f"{adv_data[29:]=} {self.tx_power=}")
        # think this is tx_power from which rssi can be calculated, one source suggests weeks since battery change + other info codes >152
        self.mac = mac_rdm
        self.colour = uuid_to_colours.get(self.uuid)
