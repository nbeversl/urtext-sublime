import datetime

def make_reverse_date_filename(date):
    unyear = 10000 - int(date.strftime('%Y'))
    unmonth = 12 - int(date.strftime('%m'))
    unday = 31 - int(date.strftime('%d'))
    unhour = 23 - int(date.strftime('%H'))
    unminute = 59 - int(date.strftime('%M'))
    unsecond = 59 - int(date.strftime('%S'))
    undatetime = "{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}".format(
        unyear, unmonth, unday, unhour, unminute, unsecond)
    return undatetime


def date_from_reverse_date(undate):
    """
    This gets a datetime object back from reverse-dated filenames
    """
    year = 10000 - int(undate[0:4])
    month = 12 - int(undate[4:6])
    day = 31 - int(undate[6:8])
    hour = 23 - int(undate[8:10])
    minute = 59 - int(undate[10:12])
    second = 59 - int(undate[12:14])
    date = datetime.datetime(year, month, day, hour, minute, second)
    return date
