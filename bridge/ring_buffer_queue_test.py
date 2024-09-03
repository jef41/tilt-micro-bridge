''' use a ringbuffer queue tested with up to 9600 records (1152000 bytes)
    this is seriously slow 5 seconds with 480 records
    (1<<56|50<<48|1220<<32|1724432892) bit shift to get same result
    bytearray((1,0,0x32,0,1220,1724432892))
    seems that it is the array creation that takes time, shouldn't be such an issue in practice?
    
'''
from tiltringbuf_queue import TiltRingbufQueue
from models import TiltStatus
from configuration import BridgeConfig
import gc
import time, random, array, struct
gc.collect()
start = gc.mem_alloc()

# if using an array in a ringbuffer
gc.collect()
start = gc.mem_alloc()
tilt_history_arr = bytearray(12 * 600)
#ring_bug = bytearray(200)
#tsq = ThreadSafeQueue(ring_bug)
rbq = TiltRingbufQueue(tilt_history_arr)
print("allocated:{}bytes for ring buffer queue".format(gc.mem_alloc() - start ))

config = BridgeConfig.load()
tilt_history = []
colours = [
        "green",
        "black", 
        "red",
        "blue",
        "orange",
        "yellow",
        "purple",
        "pink",
        "simulated"  # reserved for fake beacons during simulation mode
    ] #[] list not {} set


def test_tilt_bytearray(how_many):
    # check size of a byte array of arrays instead of a list of objects
    global rbq
    #global tilt_history_arr
    global colours
    gc.collect()
    start = gc.mem_alloc()
    #tilt_history_arr = array.array()
    for _ in range(how_many):
        colour = colours.index(random.choice(colours))
        temp = random.randrange(50, 100)
        sg = random.randrange(990, 1200) #* .001
        # 1800 = 30 mins old
        tstamp = random.randrange(time.time() - 1800, time.time())
        #fake_data = array.array('I',[colour, temp, sg, tstamp])
        '''fake_data = bytearray((colour).to_bytes(2, 'big')+
                              (temp).to_bytes(2, 'big')+
                              (sg).to_bytes(2, 'big')+
                              (tstamp).to_bytes(2, 'big'))
        tilt_history_arr.extend(fake_data)'''
        #struct.pack_into(fmt, buffer, offset, v1, v2, ...)
        #struct.pack('BHHI', 1,50,1220,1724432892)
        #test = memoryview(tilt_history_arr)
        #test.extend(fake_data)
        #return fake_data
        rbq.put_struct_nowait('HHHI', colour, temp, sg, tstamp)
        
        gc.collect()
        now = gc.mem_alloc()
        #print("rbq is:{}bytes".format( now - start ))
        #print("Tilt history is:{}".format( tilt_history_arr[0:4] ))
        #return memoryview(tilt_history_arr)
    

def test_queue(how_many):
    #
    global colours
    global tilt_history_arr
    t1 = time.ticks_ms()
    try:
        test_tilt_bytearray(how_many)
    except IndexError:
        pass
        #overwrite oldest data
    #saved_data_arr = memoryview(tilt_history_arr)
    print(f"array creation took {time.ticks_diff(time.ticks_ms(), t1)}")
    allowance = 900
    limit = time.time() - allowance
    colour = random.choice(colours)
    colour_to_match = colours.index(colour)
    #print(f"looking for {colour}")
    data = memoryview(tilt_history_arr)
    #print("saved data is:{}".format( list(data[0:]) ))
    start = 0
    step = 12
    end = len(tilt_history_arr)//step #todo reference via rbq??
    print(f"matching looking for {colour}({colour_to_match}) data is:")  
    print(f"matching looking for timestamp > {limit}:")   
    #for i in range(start, end, step):
    #    #print(i, end, step)
    #    if data[i] == colour_to_match: # and saved_data_arr[(i*step)+step] > limit:
    #        print(list(data[i:i+step]), i)
    sum_sg = 0
    sum_tempf = 0
    num_results = 0
    t2 = time.ticks_ms()
    for i in range(start, end, step):
        test = struct.unpack_from('BHHI', data, i)
        #print(test, i)
        if test[0] == colour_to_match and test[3] > limit:
            print(test, i)
            num_results += 1
            sum_tempf += test[1]
            sum_sg += test[2]
    
    print(f"filtering took {time.ticks_diff(time.ticks_ms(), t2)}")
    if num_results:
        t3 = time.ticks_ms()
        avg_sg = round((sum_sg / num_results ) * 0.001, 4)
        avg_tempf = round(sum_tempf / num_results, 1)
        averaged_data = TiltStatus(colour, avg_tempf, avg_sg, config)
        print(f"averaged values:{averaged_data.colour} {averaged_data.temp_fahrenheit} {averaged_data.gravity}")
        #dump(averaged_data)
        print(f"averaging took {time.ticks_diff(time.ticks_ms(), t3)}")
    else:
        print("no matches")


test_queue(620)
hb = 0xff00
lb = 0x00ff
b1 = 0xff000000
b2 = 0x00ff0000
b3 = 0x0000ff00
b4 = 0x000000ff
b5 = 0x00000000ff
bytearray((1,0,50&lb,(50&hb)>>8,(1220&lb),(1220&hb)>>8, 0, 0, (1724432892&b4), (1724432892&b3)>>8, (1724432892&b2)>>16, (1724432892&b1)>>24))