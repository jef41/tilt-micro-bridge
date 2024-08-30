import gc, random, time
gc.mem_free()
from models.tilt_history import TiltHistory
from configuration import BridgeConfig
config = BridgeConfig.load()
gc.collect()
before = gc.mem_free()
test=TiltHistory(config, (2,))
gc.collect()
after_init = gc.mem_free()
print(f"mem used:{before-after_init}, free:{after_init}")
test.add_data(colour=2, sg=1200, tempF=51, tstamp=1724432892)
test.add_data(colour=2, sg=1200, tempF=52, tstamp=1724432792)
test.add_data(colour=2, sg=1200, tempF=53, tstamp=1724432692)
test.add_data(colour=2, sg=1200, tempF=54, tstamp=1724432592)
test.add_data(colour=2, sg=1200, tempF=55, tstamp=1724432992)
test.get_data(colour=2)
t0 = time.ticks_us()
for _ in range(1000):
    #colour = colours.index(random.choice(colours))
    vtemp = random.randrange(50, 100)
    vsg = random.randrange(990, 1200) #* .001
    # 1800 = 30 mins old
    vtstamp = random.randrange(time.time() - 1800, time.time())
    test.add_data(colour=2, sg=vsg, tempF=vtemp, tstamp=vtstamp)
print(f"adding data took {time.ticks_diff(time.ticks_us(), t0)/1000}ms")
t0 = time.ticks_us()
tempF, SG = test.get_data(colour=2)
print(f"retrieving data took {time.ticks_diff(time.ticks_us(), t0)/1000}ms")
print(f"TempF={tempF} SG={SG}")