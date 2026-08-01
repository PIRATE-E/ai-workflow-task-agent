from collections import deque
import json


class Printer:
    """
    conver the data bytes to the string and then
    convert those strings to matched log_entry
    after which create and manage the console that can hanlde it !!
    """

    ##TODO: currently only raw printing
    ## using the pointer of queue with len of 1 and the attr is got setter triggers the printing !! of the appended queue

    queue_ptr: deque[bytes] = deque(maxlen=1)

    @classmethod
    def append(cls, value: bytes):
        cls.queue_ptr.append(value)
        ## for now we are just printing it up
        print(json.loads(value.decode()))
