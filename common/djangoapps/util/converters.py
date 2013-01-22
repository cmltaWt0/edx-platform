import time, datetime
import re
import calendar

def time_to_date(time_obj):
    """
    Convert a time.time_struct to a true universal time (can pass to js Date constructor)
    """
    # TODO change to using the isoformat() function on datetime. js date can parse those
    return calendar.timegm(time_obj) * 1000

def jsdate_to_time(field):
    """
    Convert a universal time (iso format) or msec since epoch to a time obj
    """
    if field is None:
        return field
    elif isinstance(field, basestring):  # iso format but ignores time zone assuming it's Z
        d=datetime.datetime(*map(int, re.split('[^\d]', field)[:6])) # stop after seconds. Debatable  
        return d.utctimetuple()
    elif isinstance(field, int) or isinstance(field, float):
        return time.gmtime(field / 1000)
    elif isinstance(field, time.struct_time):
        return field