## Build Notes

Some early build notes, because I will forget /these may be of use to someone else

There is definitely a better way of doing this, in particular the Github workflows at:

https://github.com/pimoroni/pimoroni-pico/tree/feature/picovector2-and-layers/.github/workflows

and https://github.com/pimoroni/pimoroni-pico/blob/feature/picovector2-and-layers/ci/micropython.sh

However, the following does work to freeze the modules into the latest micropython UF2

from shell:

```
F_MANIFEST='/mnt/d/Users/jef41/Documents/GitHub/tilt-micro-bridge/build'

cd /mnt/d/Users/jef41/Documents/GitHub/micropython/ports/rp2/build-RPI_PICO_W && \
cmake -DMICROPY_BOARD=RPI_PICO_W -DMICROPY_FROZEN_MANIFEST=$F_MANIFEST/manifest_RPI_PICO_W.py .. && \
make -j $(nproc) && picotool info -a firmware.uf2

cd ../build-RPI_PICO2_W && \
cmake -DMICROPY_BOARD=RPI_PICO2_W -DMICROPY_FROZEN_MANIFEST=$F_MANIFEST/manifest_RPI_PICO2_W.py .. && \
make -j $(nproc) && picotool info -a firmware.uf2
```

on errors the first step is either `make clean` or just delete the contents of the current build dir

## Initial config

From memory, (using WSL) the process is:

```
WSL Ubuntu:

sudo apt-get update
sudo apt-get install -y cmake build-essential libffi-dev git pkg-config gcc-arm-none-eabi -y
sudo apt install build-essential cmake -y
sudo apt install gcc-arm-none-eabi libnewlib-arm-none-eabi -y

cd /mnt/d/Users/jef41/Documents/GitHub/
git clone https://github.com/micropython/micropython.git --branch master
cd micropython
git submodule update --init
export PICO_SDK_PATH='/mnt/d/Users/jef41/Documents/GitHub/micropython/lib/pico-sdk'
make -C mpy-cross
sudo ln -s mpy-cross/build/mpy-cross /usr/local/bin/mpy-cross
cd ../
sudo apt install libusb-1.0-0-dev
git clone https://github.com/raspberrypi/picotool.git
cd picotool && mkdir build && cd build
cmake ..
make
sudo make install
sudo ln -s /mnt/d/Users/jef41/Documents/GitHub/picotool/build/picotool /usr/local/bin/picotool
cd ../
```
