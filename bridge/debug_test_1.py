''' no memory leak with either Queue or ThreadSafe Queue
    minimal example
'''
import asyncio
from aioble import central as aioble_central
#import bluetooth
#from threadsafe import ThreadSafeQueue, Message, Context
from primitives import Queue
#import _thread
from machine import RTC
import time
import ntptime
import network
from models import TiltStatus
from providers import *
from configuration import BridgeConfig
from rate_limiter import RateLimitedException
import gc
import sys

config = BridgeConfig.load()
gc.threshold(2096)
uuid_to_colours = {
        "a495bb20-c5b1-4b44-b512-1370f02d74de": "green",
        "a495bb30-c5b1-4b44-b512-1370f02d74de": "black", 
        "a495bb10-c5b1-4b44-b512-1370f02d74de": "red",
        "a495bb60-c5b1-4b44-b512-1370f02d74de": "blue",
        "a495bb50-c5b1-4b44-b512-1370f02d74de": "orange",
        "a495bb70-c5b1-4b44-b512-1370f02d74de": "yellow",
        "a495bb40-c5b1-4b44-b512-1370f02d74de": "purple",
        "a495bb80-c5b1-4b44-b512-1370f02d74de": "pink",
        "a495bb40-c5b1-4b44-b512-1370f02d74df": "simulated"  # reserved for fake beacons during simulation mode
    }


async def main():
    bridge_q = Queue(maxsize=16) # ThreadSafeQueue(buf=16)  # seems to work with Queue
    #await scan_for_ibeacons(bridge_q)
    #scanner = asyncio.create_task(scan_for_ibeacons(bridge_q))
    #handler = asyncio.create_task(_handle_bridge_queue(bridge_q))
    #await handler
    scanner = asyncio.create_task(scan_for_ibeacons(bridge_q))
    while True:
        
        #await scanner
        #print("scanner started")
        handler = asyncio.create_task(_handle_bridge_queue(bridge_q))
        #print("handler started")
        await handler # wait for handler to return
        #print("handler returned")
        print(f"gc: {gc.mem_free()}\t qsize:{bridge_q.qsize()}")
        await asyncio.sleep_ms(200) # wait for scan interval to finish
        '''# maybe await scanner or gather?
        await asyncio.gather(handler)#, scanner)
        #print("loop")'''


async def scan_for_ibeacons(bridge_q):
    ''' '''
    #print("debug: starting scanner...")
    # Constants for iBeacon
    iBeacon_prefix = b'\x4C\x00\x02\x15'  # Apple company ID + iBeacon type
    # Start scanning for advertisements
    
    while True:
        async with aioble_central.scan(duration_ms=2000) as scanner:
            async for result in scanner:
                # Check if the advertisement contains the iBeacon prefix
                #if result.manufacturer and result.manufacturer.startswith(IBEACON_PREFIX):
                if iBeacon_prefix in result.manufacturer():
                    # Extract and process iBeacon data
                    adv_data = result.adv_data
                    uuid = adv_data[4:20]    # UUID (16 bytes)
                    major = int.from_bytes(adv_data[20:22], 'big')  # Major (2 bytes)
                    minor = int.from_bytes(adv_data[22:24], 'big')  # Minor (2 bytes)
                    tx_power = int.from_bytes(adv_data[24:25], 'big', signed=True)  # TX Power (1 byte)
                    rssi = result.rssi
                    print(f"MAC: {result.device.addr_hex()} Beacon: {result.name}")

                    # Call the callback function with the extracted data
                    _beacon_callback(uuid, major, minor, tx_power, rssi, bridge_q)
                    #_beacon_callback("a495bb40-c5b1-4b44-b512-1370f02d74df", 65, 1021, 0, 0, bridge_q)
                else:
                    #print(f"MAC: {result.device.addr_hex()} Not beacon: {result.rssi}")
                    # fake callback
                    #_beacon_callback("a495bb40-c5b1-4b44-b512-1370f02d74df", 65, 1021, 0, result.rssi, bridge_q)
                    await _beacon_callback("a495bb40-c5b1-4b44-b512-1370f02d74df", 65, 1021, 0, 0, bridge_q)
                    #pass # testing is it scanner or callback that causes issue? or maybe colours_to_uuid def?
            #result = None
    #return None


async def _beacon_callback(uuid, major, minor, tx_power, rssi, bridge_q):
    # todo: beacon data should be an object with attributes (including a timestamp)
    # When queue is full broadcasts should be ignored
    # this can happen because Tilt broadcasts very frequently, while Pitch must make network calls
    # to forward Tilt status info on and this can cause Pitch to fall behind
    # global cb_tilt_status
    #stg1 = gc.mem_free()
    if bridge_q.full():
        #print("debug: queue is full")
        return

    #uuid = packet.uuid
    #stg2 = gc.mem_free()
    colour = uuid_to_colours.get(uuid)
    #stg3 = gc.mem_free()
    if colour:
        # print("beacon_callback colour match, {}".format(colour))
        # iBeacon packets have major/minor attributes with data
        # major = degrees in F (int)
        # minor = gravity (int) - needs to be converted to float (e.g. 1035 -> 1.035)
        #start = gc.mem_free()
        beacon_data = TiltStatus(colour, major, minor * .001, config)
        #print("cb_tilt_status is:{} bytes".format(start - gc.mem_free()))
        #stg4 = gc.mem_free()
        #print("debug: tilt_status:\n{}".format(dir(beacon_data)))
        if not beacon_data.temp_valid:
            print("Ignoring broadcast due to invalid temperature: {}F".format(beacon_data.temp_fahrenheit))
        elif not beacon_data.gravity_valid:
            print("Ignoring broadcast due to invalid gravity: " + str(beacon_data.gravity))
        else:
            #print("debug: putting...\n {}".format(dir(beacon_data)))
            #bridge_q.put_nowait(tilt_status)
            #bridge_q.put_sync(beacon_data)
            await bridge_q.put(beacon_data)
            #print("{}\t beacon packet received".format(beacon_data.timestamp))
            #print("debug: bridge_q after {}".format(bridge_q.qsize()))
        #print("debug: end of if colour")
        #stg5 = gc.mem_free()
    else:
        print("beacon_callback no colour match")
    #print("debug: end of beacon_callback")
    #await asyncio.sleep_ms(0)
    beacon_data = None
    colour = None
    #stg6 = gc.mem_free()
    #print("gc:{}".format(gc.mem_free()))
    #print("mem free after beacon_callback:{}\t{}\t{}\t{}\t{}\t{}".format(stg1,stg2,stg3,stg4,stg5,stg6))
    # testing memory leak
    

async def _handle_bridge_queue(bridge_q):
    #while True:
    #print("handle queue")
    while config.queue_empty_sleep_seconds > 0 and bridge_q.empty():
        #time.sleep(config.queue_empty_sleep_seconds)
        await asyncio.sleep(1)
        return

    if bridge_q.full(): # testing memory leak
        length = bridge_q.qsize()
        print("Queue is full ({} events), scans will be ignored until the queue is reduced".format(length))
    #start = gc.mem_free()
    #print("waiting for data")
    tilt_status = await bridge_q.get()
    print(f"gc: {gc.mem_free()}\t qsize:{bridge_q.qsize()}")
    
    
asyncio.run(main())