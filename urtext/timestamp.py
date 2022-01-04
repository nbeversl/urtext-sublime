import datetime
from Urtext.dateutil.parser import *

default_date = datetime.datetime(1970,1,1, tzinfo=datetime.timezone.utc)

class UrtextTimestamp:
    def __init__(self, dt_string):
        if not dt_string:
            dt_string = ''
        self.datetime = date_from_timestamp(dt_string)
        self.string = dt_string
        if self.datetime == None:
            self.datetime = default_date


def date_from_timestamp(datestamp_string):
    if not datestamp_string:
        return default_date
    d = None
    try:
        d = parse(datestamp_string)
    except:
        return None
    if d.tzinfo == None:
        try:
            d = d.replace(tzinfo=datetime.timezone.utc)    
        except:
            print('cannot add timezone info to')
            print(datestamp_string)
            print(d)
    return d
