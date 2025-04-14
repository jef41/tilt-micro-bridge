# Tilt Micro Bridge Display
Version 1.1 of this project introduces a limited option of adding a display to the device. At present this is implemented only for a [Pimoroni Pico Display](https://shop.pimoroni.com/products/pico-display-pack?variant=32368664215635). 

This is a 1.14" 240×135 IPS display, using a st7789 driver chip. The PCB will plug directly into the Pico headers and includes an RGB LED and 4 buttons. The buttons are currently not used in this project, though I like the idea of using a button to log a reading as a starting gravity (O.G.), or maybe to temporarily turn the display off/on.
I suggest purchasing their display, though if it is not available any 240×135 st7789 LCD should work. The font sizes and spacing are currently all calculated for a dispaly of this specific size.
The Pico Display has an integrated RGB LED and 4 (currently unused) buttons.

The RGB LED will flash an appropriate colour when data is received from a Tilt.

The display will show the most recent (calibrated) values from each configured Tilt. If present, the beer name will be shown. The RSSI (signal strength) is also displayed along with raw (uncalibrated) values and battery age in weeks. 

If an original gravity value is configured in the config.json an additional screen will show current ABV and Apparent Attenuation.

The default configuration is to not use a display. To enable the display, plug it in to the Pico, then in the config file add entries for:

1. `"display_type": "DISPLAY_PICO_DISPLAY"`
2. `"rgb_led_gpio": [6,7,8]`

## If you are using an LCD other than the Pimoroni Pico Display: 
1. `"display_type": "DISPLAY_PICO_DISPLAY"`
2. `"rgb_led_gpio": [6,7,8]` changing 6,7,8 to the appropriate R,G,B pins, or omit this entry if no RGB LED is present. 
3. `lcd_spi_gpio` set this to match the GPIO numbereding of the SPI pins in use, the defaults are: `{"cs": 17, "dc": 16, "sck": 18, "mosi": 19, "bl": 20}` where bl=backlight LED
 

## Optionally change these options
`lcd_backlight` The LCD backlight is PWM controlled set a value between 0 (off) and 1. The default is 0.7

`rgb_brightness` Similarly the RGB LED brightness can be set between 0 and 1. This is rather bright, the default is 0.05

`display_update_secs` The display will show at least 2 screens - a clock and configured values from a Tilt. If more Tilt devices are present then more dispaly pages will be present. By default the display will cycle every 5 seconds. If you wish to change the update frequency then change this value.

## minimal working exmaple:
```json
{
    "rgb_led_gpio": [6,7,8],
    "display_type": "DISPLAY_PICO_DISPLAY",
 
    "csv_log_tilt_colours": ["purple"]
}
```

## complete working example:
```json
{
    "rgb_led_gpio": [6,7,8],
    "display_type": "DISPLAY_PICO_DISPLAY",
    "lcd_spi_gpio": {"cs": 17, "dc": 16, "sck": 18, "mosi": 19, "bl": 20},
    "rgb_led_gpio": [6,7,8],
    "lcd_backlight":  0.9,
    "rgb_brightness":  0.1,
    "display_update_secs": 3,

    "default_temp_unit": "F",
    "grainfather_averaging_period": 0,
    
    "csv_log_tilt_colours": ["blue", "red", "green", "yellow", "purple"],
    "csv_log_period": 300,

    "ssid": "xxxx-yyyy",
    "password": "zzzzzzzzzz",
    "country_code": "GB",

    "blue_gravity_offsets" : [[1.0016,1.000], [1.0574,1.0560], [1.1070,1.1015]],
    "blue_temp_offsets" : [[12.7,11.7], [16.5,16.8]],
    "gravity_range_min" : 0.980,
    "gravity_range_max" : 1.210,
    "temp_range_min" : 35,
    "temp_range_max" : 120,

    "blue_original_gravity": 1.082,
    "simulated_name": "Festbier"
}
```