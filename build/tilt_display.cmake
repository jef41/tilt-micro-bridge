include_directories(${CMAKE_CURRENT_LIST_DIR}/../../pimoroni-pico/)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../../pimoroni-pico/micropython/modules/")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../../pimoroni-pico/micropython/")
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/../../pimoroni-pico/")

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

#include(micropython-common)

# C++ Magic Memory
#include(cppmem/micropython)

# Disable build-busting C++ exceptions
#include(micropython-disable-exceptions)





# Essential
include(pimoroni_i2c/micropython)
include(pimoroni_bus/micropython)

# Pico Graphics Essential
include(hershey_fonts/micropython)
include(bitmap_fonts/micropython)
include(picographics/micropython)

# Pico Graphics Extra
#include(pngdec/micropython)
#include(jpegdec/micropython)
include(picovector/micropython)
#include(qrcode/micropython/micropython)

# Sensors & Breakouts
#include(micropython-common-breakouts)

# Packs & Bases
#include(pico_unicorn/micropython)
#include(pico_scroll/micropython)
#include(pico_rgb_keypad/micropython)
#include(pico_explorer/micropython)

# LEDs & Matrices
#include(plasma/micropython)
#include(hub75/micropython)

# Servos & Motors
#include(pwm/micropython)
#include(servo/micropython)
#include(encoder/micropython)
#include(motor/micropython)

# Utility
#include(adcfft/micropython)

# RTC (Badger 2040W, Enviro)
#if(PICO_BOARD STREQUAL "pico_w")
#    include(pcf85063a/micropython)
#endif()

include(modules_py/modules_py)

# Most board specific ports wont need all of these
#copy_module(gfx_pack.py)
copy_module(pimoroni.py)
# if building the Pimoroni image (not the custom boot.py release image) then uncomment the line below
# if this is left in on release builds, then when building we get an error: redefinition of 'frozen_module_boot'
# but it is probably required for Pimoroni builds?!
#copy_module(boot.py)
# copy_module(interstate75.py)
# if(PICO_BOARD STREQUAL "pico_w")
#     copy_module(automation.py)
#     copy_module(inventor.py)
# endif()


# Must call `enable_ulab()` to enable
#include(micropython-common-ulab)
#enable_ulab()
#include(micropython-common)
include(micropython-common-ulab)
enable_ulab()

# C++ Magic Memory
include(cppmem/micropython)

# Disable build-busting C++ exceptions
include(micropython-disable-exceptions)