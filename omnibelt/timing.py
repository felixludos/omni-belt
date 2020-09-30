
from datetime import datetime
import time

STD_FMT = "%y%m%d-%H%M%S"

def get_now(fmt=STD_FMT):
	now = datetime.now()
	if fmt is None:
		return now
	return now.strftime(fmt)

def recover_date(raw, fmt=STD_FMT):
	return datetime.strptime(raw, fmt)

