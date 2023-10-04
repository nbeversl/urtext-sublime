import datetime
import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from Urtext.dateutil.parser import *
    import Urtext.urtext.syntax as syntax
else:
    from dateutil.parser import *
    import urtext.syntax as syntax

default_date = datetime.datetime(1970,1,1, tzinfo=datetime.timezone.utc)

class UrtextTimestamp:
    def __init__(self, 
        unwrapped_string, 
        start_position):

        self.wrapped_string = ''.join([
            syntax.timestamp_opening_wrapper,
            unwrapped_string,
            syntax.timestamp_closing_wrapper
            ])
        self.unwrapped_string = unwrapped_string
        self.datetime = date_from_timestamp(unwrapped_string)
        if self.datetime == None:
            self.datetime = default_date
        self.start_position=start_position
        self.end_position=start_position + len(self.wrapped_string)

    def __lt__(self, other):
        return self.datetime < other.datetime


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
