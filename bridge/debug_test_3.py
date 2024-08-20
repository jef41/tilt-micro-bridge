import asyncio
from aioble import central as aioble_central
from primitives import Queue
import gc

gc.collect()
gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
#print(gc.threshold())
#gc.threshold(60)
# Tilt format based on iBeacon format with Tilt specific uuid preamble (a495)
TILT = "0215a495"

async def main():
    bridge_q = Queue(maxsize=16) 
    scanner = asyncio.create_task(scan_for_ibeacons(bridge_q))
    while True:
        while bridge_q.empty():
            await asyncio.sleep(1)

        if bridge_q.full(): 
            length = bridge_q.qsize()
            print("Queue is full ({} events), scans will be ignored until the queue is reduced".format(length))
        
        print(f"gc: {gc.mem_free()}\t qsize:{bridge_q.qsize()}")
        dumb_value = await bridge_q.get()
        dumb_value = None


async def scan_for_ibeacons(bridge_q):
    # Constants for iBeacon
    iBeacon_prefix = b'\x4C\x00\x02\x15'  
    while True:
    #async with aioble_central.scan(duration_ms=2000) as scanner:
        async with aioble_central.scan(duration_ms=50000, interval_us=160000, window_us=11250) as scanner:
            async for result in scanner:
                #if result.manufacturer and result.manufacturer.startswith(IBEACON_PREFIX):
                #scanner.cancel() #_duration_ms = None # stop scanning
                await bridge_q.put(result.rssi)
            #result = None
        await asyncio.sleep(0)
  
    
asyncio.run(main())

