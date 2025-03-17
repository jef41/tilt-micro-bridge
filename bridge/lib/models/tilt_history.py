"""saves a history of temperature & SG values received per tilt device
can be used for averaging
in testing can hold up to 21,000 records (though will be less in real world situation)
600 records per tilt (approx 10 mins of data) and 8 tilts = 4,800 records
952bytes + 7 * no of records

temp & gravity are packed into 24bits, time into 32 bits = 56bits, 7bytes per record

would be good to benchmark performance in retrieving records and subtract that time from the log interval
i.e. if log period is 900 seconds and it takes 5ms to retrieve an averaged value, then log interval should be set to 899.995

call this;
          at startup, to inititate bytearrays: test=TiltHistory(config, (2,3)), where 2,3 are configured tilt colours
          when data is received: test.add_data(colour='red', tempF=51, sg=1200, tstamp=1724432892)
          when a timer expires & upload is due: tempF, SG = test.get_data(colour='red'), from that create a TiltStatus & upload it
"""

import time
import asyncio
import gc
import logging


logger = logging.getLogger("TiltHistory")


class TiltHistory:
    """stores received raw (uncalibrated) sample data for each Tilt device
    in a binary format, in a circular buffer
    """

    def __init__(self, colour_dict):
        # colour dict is; colour: max of averaging period
        # print values to std out for n secs (less if debugging)
        self.results_secs = 15 if logging.getLogger().level < 20 else 60 * 60
        self.print_raw = asyncio.create_task(
            self.timeout_raw(self.results_secs)
        )  # True
        self.ringbuffer_list = dict()
        self.initialise_ringbuffer(colour_dict)  # create appropriately sized buffer(s)

    async def timeout_raw(self, timeout):
        # stop printing data: statements to serial
        self.print_raw = True
        # print("***  self print raw started")
        await asyncio.sleep(timeout)  # show received packets for n secs
        # print("***  self print raw finished")
        self.print_raw = False

    def initialise_ringbuffer(self, colour_dict):
        # create empty buffer(s)
        # here find the largest number for averaging for this colour in config
        # logger.debug(f"initialise ringbuffer {colour_dict}")
        # try:
        # print(f"***  {colour_dict}") 
        #20250313 TODO rename colour_dict
        # for colour, av_period in colour_dict.items():
        #values = [getattr(item, colour) for item in colour_dict] 
        #for colour, av_period in values:
        #    # for colour in colour_dict.keys()
        for colour, av_period in colour_dict.items():
            if colour not in self.ringbuffer_list:
                # No limiter for this device yet
                # max = TODO: find max for this colour
                logger.debug(
                    f"creating ringbuffer for {colour} Tilt with {av_period} records"
                )
                #self.ringbuffer_list[colour] = self._get_new_ringbuffer(
                #    av_period
                # 20250313
                self.ringbuffer_list.update({colour: self._get_new_ringbuffer(av_period)})
                #)  # TODO: ensure we check store_size
        """ elif colour in self.ringbuffer_list and self.ringbuffer_list[colour].len < av_period:
                    self.ringbuffer_list[colour] = self._get_new_ringbuffer(av_period)
        """

    def _get_new_ringbuffer(self, av_period):
        return TiltRingBuffer(av_period)

    def add_data(self, colour, tempF, sg, tstamp):
        # add to appropriate queue
        if colour not in self.ringbuffer_list:
            raise Exception("tried to store data for unconfigured Tilt!")
        # TODO: could just create a new data archive here?
        try:
            self.ringbuffer_list[colour].add_data(tempF, sg, tstamp)
        except IndexError:
            # queue full, overwriting
            pass

    def get_data(self, colour, av_period, log_period):
        # TODO: tidy up av_ & log_ periods & data_points
        # averaged or most recent?
        # filter appropriate colour on timestamp > now - (period/rate)
        # use a memoryview
        # return a tuple of temp & sg
        tempF, sg = None, None
        now = time.time()
        if av_period:  # > 0 self.data_points:
            # get an average
            logger.debug(f"averaging period set, get average {av_period} secs")
            time_limit = now - int(
                av_period
            )  # ensure an integer, float leads to rounding
            tempF, sg = self.ringbuffer_list[colour].get_average(time_limit)
            # pass
        else:
            # get most recent
            logger.debug(
                f"averaging not set, get most recent data, newer than {now - log_period}"
            )
            time_limit = now - int(
                log_period
            )  # ensure an integer, float leads to rounding errors
            tempF, sg = self.ringbuffer_list[colour].get_most_recent(time_limit)
        return [tempF, sg]


class TiltRingBuffer:
    # TODO should really override TiltRingbufQueue
    def __init__(self, data_points):
        # each record is 7 bytes; timestamp =4, sg & temp = 3
        # logger.debug(TiltHistory.data_points)
        self.record_len = 7
        gc.collect()
        store_size = (
            data_points if data_points else 1
        )  # averaging is 0 store 1 data point
        self._q = bytearray(0 for _ in range(self.record_len * (store_size)))
        self._size = len(self._q)
        self._wi = 0
        self._ri = 0
        self._evput = asyncio.Event()  # Triggered by put, tested by get
        self._evget = asyncio.Event()  # Triggered by get, tested by put
        self.hd = None

    def add_data(self, tempF, sg, tstamp):
        # pack 4byte timestamp & 2 x 12 bit numbers into 7 bytes
        # subtract the minimum possible value from SG, to keep integer as small as possible
        if sg < 9900:
            sg = sg - 990
            self.hd = False
        else:
            sg = sg - 9900  # HD
            self.hd = True
        vals = sg << 12 | tempF
        # logger.debug(hex(vals))
        data = bytes(
            [
                (tstamp & 0xFF),
                (tstamp >> 8) & 0xFF,
                (tstamp >> 16) & 0xFF,
                (tstamp >> 24) & 0xFF,
                (vals & 0xFF),
                (vals >> 8) & 0xFF,
                (vals >> 16) & 0xFF,
            ]
        )
        # logger.debug(f"data{(data)}")
        self._put_nowait(data)

    def peekq(self):  
        # Return memoryview of the whole queue without altering it.
        return memoryview(self._q)

    def get_average(self, limit):
        # limit should be either averaging period, or, for most recent, (period/rate)/2
        mv_data = memoryview(self._q)
        # logger.debug("saved data is:{}".format( list(mv_data[0:]) ))
        start = 0
        step = self.record_len
        end = len(mv_data)  # //step #TODO reference via rbq??
        # logger.debug(f"matching looking for timestamp > {limit}:")
        sum_sg = 0
        sum_tempf = 0
        num_results = 0
        for i in range(start, end, step):
            q_timestmp = (
                mv_data[0 + i]
                | mv_data[1 + i] << 8
                | mv_data[2 + i] << 16
                | mv_data[3 + i] << 24
            )
            # logger.debug(test, i)
            if q_timestmp > limit:  # we have a match TODO:
                temp_match = mv_data[4 + i] | ((mv_data[5 + i] & 0x0F) << 8)
                sg_match = mv_data[6 + i] << 4 | (mv_data[5 + i] & 0xF0) >> 4
                # logger.debug(f"{i}: {q_timestmp}, temp{ temp_match }, SG{sg_match}")
                # logger.debug(f"{mv_data[4+i]} {mv_data[5+i]} {mv_data[6+i]}")
                num_results += 1
                sum_sg += sg_match  # (mv_data[5+i] & 0xF0) >>4 | mv_data[6+i]<<4
                sum_tempf += temp_match  # mv_data[4+i] | ((mv_data[5+i] & 0x0F)<<8)

        # logger.debug(f"filtering took {time.ticks_diff(time.ticks_ms(), t2)}")
        if num_results:
            min = 9900 if self.hd else 990
            avg_sg = round((sum_sg / num_results), 0) + min

            avg_tempf = round(sum_tempf / num_results, 1)
            # TODO get colour index for debug statement
            n = 4 if self.hd else 3
            logger.debug(
                f"{num_results} averaged raw (uncal) values, temp;{avg_tempf:.1f} SG:{avg_sg * 0.001:.{n}f}"
            )
            # logger.debug(f"averaging took {time.ticks_diff(time.ticks_ms(), t3)}")
            return [avg_tempf, avg_sg * 0.001]
        else:
            logger.debug("no matches (get_average)")
            return [None, None]
        # pass

    def get_most_recent(self, limit):
        # find the most recent value and ensure it is within limit
        # limit should be log period/2 in this casse
        mv_data = memoryview(self._q)
        """#logger.debug("saved data is:{}".format( list(mv_data[0:]) ))
        start = 0
        step = self.record_len
        end = len(mv_data)//step #todo reference via rbq?? 
        #logger.debug(f"matching looking for timestamp > {limit}:")"""
        num_results = 0
        # t2 = time.ticks_ms()
        try:
            # latest_i = (self._ri + self.record_len) % self._size
            # read backwards until we get below timestamp limit
            startb = self._wi - self.record_len
            latest_i = 0 if startb < 0 else startb
            # print(f"start, stop, step {startb}, {stopb}, {stepb}")
            steps = self._size / self.record_len
            # print(f"steps:{steps}, mv:{self._size}")
            for i in range(steps):
                # Loop through it 7 bytes at a time, starting from index 0 and then moving backwards
                # Loop: Start from index 0, then move backwards in steps of 7
                q_timestmp = (
                    mv_data[0 + latest_i]
                    | mv_data[1 + latest_i] << 8
                    | mv_data[2 + latest_i] << 16
                    | mv_data[3 + latest_i] << 24
                )
                logger.debug(f"timestamp:{q_timestmp} limit:{limit}")
                if q_timestmp > int(limit):  # we have a match
                    temp_match = mv_data[4 + latest_i] | (
                        (mv_data[5 + latest_i] & 0x0F) << 8
                    )
                    sg_match = (
                        mv_data[6 + latest_i] << 4 | (mv_data[5 + latest_i] & 0xF0) >> 4
                    )
                    # logger.debug(f"{i}: {q_timestmp}, temp{ temp_match }, SG{sg_match}")
                    # logger.debug(f"{mv_data[4+i]} {mv_data[5+i]} {mv_data[6+i]}")
                    num_results += 1
                    break
                # Move backwards with wrap-around
            latest_i = (latest_i - self.record_len) % self._size
        except Exception as e:
            logger.debug(f"Error in get_most_recent: {e}")
            raise e
        if num_results:
            min = 9900 if self.hd else 990
            sg_match = (sg_match + min) * 0.001

            logger.debug(
                f"{num_results} most recent raw (uncal) value, temp;{temp_match:.g} SG:{sg_match:.3f}"
            )
            return [temp_match, sg_match]

        else:
            logger.debug("no matches in get_most_recent")
            return [None, None]

    def _put_nowait(self, data):
        # put a bytearray onto the queue
        # TODO add a check/raise an error if length of struct pack will exceed queue
        # logger.debug(f"got: {data}")
        """fmt = 'BBBBBBB'
        data_archive = memoryview(self._q)
        struct.pack_into('BBBBBBB', data_archive, self._wi, *data)
        self._evput.set()  # Schedule any tasks waiting on get
        self._evput.clear()
        c = len(fmt)"""
        data_archive = memoryview(self._q)
        c = self.record_len  # len(data)
        if not c == len(data):
            raise Exception(
                f"Invalid data: data length {len(data)} does not match expected length {c}"
            )
        data_archive[self._wi : self._wi + c] = (
            data  # add new data into next buffer point
        )
        self._evput.set()  # Schedule any tasks waiting on get
        self._evput.clear()
        self._wi = (self._wi + c) % self._size
        if self._wi == self._ri:  # Would indicate empty
            self._ri = (self._ri + c) % self._size  # Discard a message
            raise IndexError  # Caller can ignore if overwrites are OK
