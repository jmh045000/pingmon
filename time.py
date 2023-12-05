import datetime
import functools

EPOCH = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
UTC_NOW = functools.partial(datetime.datetime.now, tz=datetime.timezone.utc)
