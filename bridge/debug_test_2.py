''' no memory leak with either Queue or ThreadSafe Queue
    minimal example
'''
import asyncio
from aioble import central as aioble_central
#import bluetooth
#from threadsafe import ThreadSafeQueue, Message, Context
from primitives import Queue
#import _thread
#from machine import RTC
#import time
#import ntptime
#import network
#from models import TiltStatus
#from providers import *
#from configuration import BridgeConfig
#from rate_limiter import RateLimitedException
import gc
#import sys
#gc.threshold(1024)
gc.collect()
gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())

async def main():
    bridge_q = Queue(maxsize=16) 
    scanner = asyncio.create_task(scan_for_ibeacons(bridge_q))
    while True:
        
        '''#await scanner
        #print("scanner started")
        handler = asyncio.create_task(_handle_bridge_queue(bridge_q))
        #print("handler started")
        await handler # wait for handler to return
        #print("handler returned")
        print(f"gc: {gc.mem_free()}\t qsize:{bridge_q.qsize()}")
        await asyncio.sleep_ms(200) # wait for scan interval to finish
        '''
        while bridge_q.empty():
        #time.sleep(config.queue_empty_sleep_seconds)
            await asyncio.sleep(1)

        if bridge_q.full(): # testing memory leak
            length = bridge_q.qsize()
            print("Queue is full ({} events), scans will be ignored until the queue is reduced".format(length))
        #start = gc.mem_free()
        #print("waiting for data")
        print(f"gc: {gc.mem_free()}\t qsize:{bridge_q.qsize()}")
        dumb_value = await bridge_q.get()
        dumb_value = None


async def scan_for_ibeacons(bridge_q):
    ''' '''
    #print("debug: starting scanner...")
    # Constants for iBeacon
    iBeacon_prefix = b'\x4C\x00\x02\x15'  # Apple company ID + iBeacon type
    # Start scanning for advertisements
    
    while True:
        #async with aioble_central.scan(duration_ms=2000) as scanner:
        async with aioble_central.scan(duration_ms=0) as scanner:
            async for result in scanner:
                # Check if the advertisement contains the iBeacon prefix
                #if result.manufacturer and result.manufacturer.startswith(IBEACON_PREFIX):
                await bridge_q.put(result.rssi)
                '''if iBeacon_prefix in result.manufacturer():
                    # Extract and process iBeacon data
                    #adv_data = result.adv_data
                    #uuid = adv_data[4:20]    # UUID (16 bytes)
                    #major = int.from_bytes(adv_data[20:22], 'big')  # Major (2 bytes)
                    #minor = int.from_bytes(adv_data[22:24], 'big')  # Minor (2 bytes)
                    #tx_power = int.from_bytes(adv_data[24:25], 'big', signed=True)  # TX Power (1 byte)
                    #rssi = result.rssi
                    #print(f"MAC: {result.device.addr_hex()} Beacon: {result.name}")

                    # Call the callback function with the extracted data
                    #_beacon_callback(uuid, major, minor, tx_power, rssi, bridge_q)
                    #_beacon_callback("a495bb40-c5b1-4b44-b512-1370f02d74df", 65, 1021, 0, 0, bridge_q)
                    
                    if bridge_q.full():
                        #print("debug: queue is full")
                        pass
                    else:
                        await bridge_q.put(result.rssi)
                else:
                    #print(f"MAC: {result.device.addr_hex()} Not beacon: {result.rssi}")
                    # fake callback
                    #_beacon_callback("a495bb40-c5b1-4b44-b512-1370f02d74df", 65, 1021, 0, result.rssi, bridge_q)
                    #await _beacon_callback("a495bb40-c5b1-4b44-b512-1370f02d74df", 65, 1021, 0, 0, bridge_q)
                    #pass # testing is it scanner or callback that causes issue? or maybe colours_to_uuid def?
                
                    if bridge_q.full():
                        #print("debug: queue is full")
                        pass
                    else:
                        await bridge_q.put(result.rssi)'''
            #result = None
    #return None
 

async def _handle_bridge_queue(bridge_q):
    #while True:
    #print("handle queue")
    while bridge_q.empty():
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
