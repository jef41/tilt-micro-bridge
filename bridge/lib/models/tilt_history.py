''' saves a history of temperature & SG values received per tilt device
    can be used for averaging
    in testing can hold up to 21,000 records (though will be less in real world situation)
    600 records per tilt (approx 10 mins of data) and 8 tilts = 4,800 records
    952bytes + 7 * no of records
    
    would be good to benchmark performance in retrieving records and subtract that time from the log interval
    i.e. if log period is 900 seconds and it takes 5ms to retrieve an averaged value, then log interval should be set to 899.995

    call this;
              at startup, to inititate bytearrays: test=TiltHistory(config, (2,3)), where 2,3 are configured tilt colours
              when data is received: test.add_data(colour='red', tempF=51, sg=1200, tstamp=1724432892)
              when a timer expires & upload is due: tempF, SG = test.get_data(colour='red'), from that create a TiltStatus & upload it
    
    todo: check all necessary defs are present - see primitives/ringbuffer_queue.py
    todo: check what happens if we pass data from a TiltPro in (4 decimcal places)
'''
from configuration import BridgeConfig
#from .json_serialize import JsonSerialize
import time
import asyncio
import gc
#import struct
import logging


logger = logging.getLogger('TiltHistory')


class TiltHistory():
    #def __init__(self, config: BridgeConfig, colour_dict): 
    def __init__(self, config: BridgeConfig, colours): #*kwargs): #colour, temp_fahrenheit, current_gravity):
        self.timestamp = time.time()
        #if kwargs:
        #    self.colour_idx = colour
        #    self.temp = temp_fahrenheit
        #    self.sg = current_gravity
        self.data_points = config.averaging_period # todo allow this per provider ...
        # for each colour in config find max averaging
        # get a list of colour:number
        self.ringbuffer_list = dict()
        self.initialise_ringbuffer(colours) # create appropriately sized buffer(s) #todo: colour_dict
        
    def initialise_ringbuffer(self, colours: str): #todo make this a dict colour:nbr_of_vals
        # create empty buffer(s)
        # todo: here find the largest number for averaging for this colour in config
        for colour_idx in colours: #todo: for colour, store_size in colour_dict
            if colour_idx not in self.ringbuffer_list:
                # No limiter for this device yet
                #logger.debug(f"creating {colour_idx}")
                self.ringbuffer_list[colour_idx] = self._get_new_ringbuffer() #todo: cpass store_size

    def _get_new_ringbuffer(self):
        #todo here pass store_size rather than parent
        return TiltRingBuffer(_parent=self) 
    
    def add_data(self, colour, tempF, sg, tstamp):
        # add to appropriate queue
        if colour not in self.ringbuffer_list:
            raise Exception("tried to store data for unconfigured Tilt!")
        # todo: could just create a new data archive here?
        try:
            self.ringbuffer_list[colour].add_data(tempF, sg, tstamp)
        except IndexError:
            # queue full, overwriting
            pass
    
    def get_data(self, colour, av_period, log_period):
        # todo: tidy up av_ & log_ periods & data_points
        # averaged or most recent?
        # filter appropriate colour on timestamp > now - (period/rate)
        # use a memoryview
        # return a tuple of temp & sg
        tempF, sg = None, None
        if av_period: # > 0 self.data_points:
            # get an average
            limit = time.time() - av_period # self.data_points
            #limit = 1724432992 - self.data_points # we have a match todo: time.time()
            tempF, sg = self.ringbuffer_list[colour].get_average(limit)
            #pass
        else:
            # get most recent todo: check how robust this is
            limit = time.time() - log_period
            #limit = 1724432992 - period # todo comment this out
            tempF, sg = self.ringbuffer_list[colour].get_most_recent(limit)
            #pass
        return [tempF, sg]


#class TiltRingBuffer(TiltHistory):
class TiltRingBuffer:
    #todo: self.storesize = store_size not parent
    def __init__(self, _parent):
        #add a data point, so = 1 if averging = 0
        # each record is 7 bytes; timestamp =4, sg & temp = 3
        #super().__init__()
        #logger.debug(TiltHistory.data_points)
        self.parent = _parent
        self.record_len = 7
        gc.collect()
        store_size = self.parent.data_points if self.parent.data_points else 1 # averaging is 0 store 1 data point
        self._q = bytearray(0 for _ in range(self.record_len * (store_size) ))
        self._size = len(self._q)
        self._wi = 0
        self._ri = 0
        self._evput = asyncio.Event()  # Triggered by put, tested by get
        self._evget = asyncio.Event()  # Triggered by get, tested by put
        self.hd = None
        # init TiltHistory here as parent
    
    def add_data(self, tempF, sg, tstamp):
        # pack 4byte timestamp & 2 x 12 bit numbers into 7 bytes
        #self.hd = sg > 2  # Tilt Pro?
        #todo: handle gravity in either 3 or 4 decimal places
        if sg <9900:
            sg = sg-990
            self.hd = False
        else:
            sg = sg-9900 #HD
            self.hd = True
        vals = sg<<12 | tempF
        #logger.debug(hex(vals))
        data = bytes([ (tstamp & 0xFF),
                    (tstamp >> 8) & 0xFF,
                    (tstamp >> 16) & 0xFF,
                    (tstamp >> 24) & 0xFF,
                    (vals & 0xFF),
                    (vals >> 8) & 0xFF,
                    (vals >> 16) & 0xFF ])
        #logger.debug(f"data{(data)}")
        self._put_nowait(data)
    
    def get_average(self, limit):
        # limit should be either averaging period, or, for most recent, (period/rate)/2
        mv_data = memoryview(self._q)
        #logger.debug("saved data is:{}".format( list(mv_data[0:]) ))
        start = 0
        step = self.record_len
        end = len(mv_data) #//step #todo reference via rbq?? 
        #logger.debug(f"matching looking for timestamp > {limit}:")   
        sum_sg = 0
        sum_tempf = 0
        num_results = 0
        t2 = time.ticks_ms()
        for i in range(start, end, step):
            #temp_out = (int.from_bytes(seven[4:], 'little')) & 0xFFF #0x7FF 
            #sg_out = 9900 + ((int.from_bytes(seven[4:], 'little')) >> 12 & 0xFFF) # shift back & bitmask
            q_timestmp = mv_data[0+i] | mv_data[1+i]<<8 | mv_data[2+i]<<16 | mv_data[3+i]<<24
            #logger.debug(test, i)
            if q_timestmp > limit: # we have a match todo:
                temp_match = mv_data[4+i] | ((mv_data[5+i] & 0x0F)<<8)
                sg_match = mv_data[6+i]<<4 | (mv_data[5+i] & 0xF0)>>4
                #logger.debug(f"{i}: {q_timestmp}, temp{ temp_match }, SG{sg_match}")
                #logger.debug(f"{mv_data[4+i]} {mv_data[5+i]} {mv_data[6+i]}")
                num_results += 1
                sum_sg += sg_match #(mv_data[5+i] & 0xF0) >>4 | mv_data[6+i]<<4
                sum_tempf += temp_match #mv_data[4+i] | ((mv_data[5+i] & 0x0F)<<8)
            
        #logger.debug(f"filtering took {time.ticks_diff(time.ticks_ms(), t2)}")
        if num_results:
            t3 = time.ticks_ms()
            min = 9900 if self.hd else 990
            rnd = 0 if self.hd else 1
            avg_sg = round((sum_sg / num_results ) , rnd) + min # round((sum_sg / num_results ) * 0.01, 4) + 0.99
            avg_tempf = round(sum_tempf / num_results, 1)
            #todo get colour index
            logger.debug(f"{num_results} averaged values, temp;{avg_tempf} SG:{avg_sg*0.001}")
            #averaged_data = TiltStatus(colour, avg_tempf, avg_sg, config)
            #logger.debug(f"averaged values:{averaged_data.colour} {averaged_data.temp_fahrenheit} {averaged_data.gravity}")
            #dump(averaged_data)
            #logger.debug(f"averaging took {time.ticks_diff(time.ticks_ms(), t3)}")
            return [avg_tempf, avg_sg*0.001]
        else:
            logger.debug("no matches")
            return [None, None]
        #pass
    
    def get_most_recent(self, limit):
        # find the most recent value and ensure it is within limit
        # limit should be log period/2 in tis casse
        # todo: add 9900 back to SG
        mv_data = memoryview(self._q)
        #logger.debug("saved data is:{}".format( list(mv_data[0:]) ))
        start = 0
        step = self.record_len
        end = len(mv_data)//step #todo reference via rbq?? 
        #logger.debug(f"matching looking for timestamp > {limit}:")
        num_results = 0
        t2 = time.ticks_ms()
        for i in range(start, end, step):
            #temp_out = (int.from_bytes(seven[4:], 'little')) & 0xFFF #0x7FF 
            #sg_out = 9900 + ((int.from_bytes(seven[4:], 'little')) >> 12 & 0xFFF) # shift back & bitmask
            q_timestmp = mv_data[0+i] | mv_data[1+i]<<8 | mv_data[2+i]<<16 | mv_data[3+i]<<24
            #logger.debug(test, i)
            if q_timestmp > limit: # we have a match todo:
                temp_match = mv_data[4+i] | ((mv_data[5+i] & 0x0F)<<8)
                sg_match = mv_data[6+i]<<4 | (mv_data[5+i] & 0xF0)>>4
                #logger.debug(f"{i}: {q_timestmp}, temp{ temp_match }, SG{sg_match}")
                #logger.debug(f"{mv_data[4+i]} {mv_data[5+i]} {mv_data[6+i]}")
                num_results += 1
            
        #logger.debug(f"filtering took {time.ticks_diff(time.ticks_ms(), t2)}")
        if num_results:
            #t3 = time.ticks_ms()
            #avg_sg = round((sum_sg / num_results ) , 1) + 990 # round((sum_sg / num_results ) * 0.01, 4) + 0.99
            #avg_tempf = round(sum_tempf / num_results, 1)
            #todo get colour index
            logger.debug(f"{num_results} most recent values, temp;{temp_match} SG:{(sg_match+990)*0.001}")
            #averaged_data = TiltStatus(colour, avg_tempf, avg_sg, config)
            #logger.debug(f"averaged values:{averaged_data.colour} {averaged_data.temp_fahrenheit} {averaged_data.gravity}")
            #dump(averaged_data)
            #logger.debug(f"averaging took {time.ticks_diff(time.ticks_ms(), t3)}")
            min = 9900 if self.hd else 990
            return [temp_match, (sg_match+min)*0.001]
        else:
            logger.debug("no matches")
            return [None, None]
        
    def _put_nowait(self, data):
        # put a bytearray onto the queue
        # todo add a check/raise an error if length of struct pack will exceed queue
        #logger.debug(f"got: {data}")
        '''fmt = 'BBBBBBB'
        data_archive = memoryview(self._q)
        struct.pack_into('BBBBBBB', data_archive, self._wi, *data)
        self._evput.set()  # Schedule any tasks waiting on get
        self._evput.clear()
        c = len(fmt)'''
        data_archive = memoryview(self._q)
        c = self.record_len #len(data)
        if not c == len(data):
            raise Exception(f"Invalid data: data length l{en(data)} does not match expected length {c}")
        data_archive[self._wi:self._wi+c] = data # add new data into next buffer point
        self._evput.set()  # Schedule any tasks waiting on get
        self._evput.clear()
        self._wi = (self._wi + c) % self._size
        if self._wi == self._ri:  # Would indicate empty
            self._ri = (self._ri + c) % self._size  # Discard a message
            raise IndexError  # Caller can ignore if overwrites are OK

    async def _put(self, data):  # Usage: await queue.put(item)
        while self.full():  # Queue full
            await self._evget.wait()  # May be >1 task waiting on ._evget
            # Task(s) waiting to get from queue, schedule first Task
        self.put_struct_nowait(data)   