# Settings Specific to wifi conenction

To configure a wifi conenction a config.json example looks like:
```
{
    "ssid": "AAAA-BBB",
    "password": "abcdefghijklmn",
    "country_code": "GB"
}
```

`ssid` a string representing the broadcast name of your WLAN network

`password` a string representing your wifi connection password

`country_code` a 2 character string representing your ISO 3166-1 alpha-2 character country code. This is not mandatory, but may aid getting the most appropriate channel or a more siwft or reliable connection.

<!-- `wifi_check_interval` expressed in seconds, at about this interval (randomised beween 80% &ndash; 120%) the bridge will attempt a DNS lookup of Google (8.8.8.8), this is a rudimentary check that we can connect to the internet (or at least a router). If this fails the tilt-bridge will try to reconnect to wifi. If `check_interval` is set to 0 then the wifi checks will be disabled. --->
