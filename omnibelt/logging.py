import sys, os
import logging

LIB_PATH = os.path.dirname(__file__)

log_levels = {
	'debug': logging.DEBUG,
	'info': logging.INFO,
	'warning': logging.WARNING,
	'error': logging.ERROR,
	'critical': logging.CRITICAL,
}

global_settings = {  # primarily for logging
	'level': 'warning',
	# 'logfile': os.path.join(os.path.dirname(LIB_PATH), 'logs', 'test.log'),
	'format': '%(levelname)s:%(name)s: %(msg)s',
	'stream': True,
	
}

_printers = []

def get_printer(name, level=None, format=None, formatter=None,

                no_file=None, file_handler=None,
                filelevel=None, fileformatter=None, filepath=None,

                include_stream=None, stream_handler=None,
                stream_level=None, stream_formatter=None,

                ):
	'''
	Create a logger possibly writing records to both a file and stdout (aka streaming).
	For any unspecified arguments, the global settings are consulted.

	:param name:
	:param level:
	:param format:
	:param formatter:
	:param no_file:
	:param file_handler:
	:param filelevel:
	:param fileformatter:
	:param filepath:
	:param include_stream:
	:param stream_handler:
	:param stream_level:
	:param stream_formatter:
	:return:
	'''
	
	if include_stream is None:
		include_stream = global_settings['stream']
	if no_file is None:
		no_file = 'logfile' in global_settings and global_settings['logfile'] is not None
	
	assert not no_file or include_stream, 'Not logging anywhere'
	
	logger = logging.getLogger(name)
	
	if level is None:
		level = global_settings['level']
	
	logger.setLevel(log_levels[level] if level in log_levels else level)
	
	if format is None:  # default formatter
		format = global_settings['format']
	if formatter is None:
		formatter = logging.Formatter(format)
	
	if filepath is None and 'logfile' in global_settings and global_settings['logfile'] is not None:
		filepath = global_settings['logfile']
	
	if file_handler is None and not no_file and filepath is not None:  # create default file_handler
		
		if fileformatter is None:
			fileformatter = formatter
		
		if filelevel is None:
			filelevel = level
		
		file_handler = logging.FileHandler(filepath)
		file_handler.setLevel(log_levels[filelevel] if filelevel in log_levels else filelevel)
		file_handler.setFormatter(fileformatter)
	
	if file_handler is not None:
		logger.addHandler(file_handler)
	
	if stream_handler is None and include_stream:  # create default stream_handler
		
		if stream_level is None:
			stream_level = level
		
		if stream_formatter is None:
			stream_formatter = formatter
		
		stream_handler = logging.StreamHandler()
		stream_handler.setLevel(log_levels[stream_level] if stream_level in log_levels else stream_level)
		stream_handler.setFormatter(stream_formatter)
	
	if stream_handler is not None:
		logger.addHandler(stream_handler)
	
	_printers.append(logger)
	
	return logger



def get_global_settings():
	return global_settings.copy()


def get_global_setting(key):
	# if key not in _global_settings:
	# 	prt.error(f'Could not find {key} in global settings')
	return global_settings.get(key, None)


def set_global_setting(key, value):
	
	if key == 'level':
		for prt in _printers:
			prt.setLevel(log_levels[value] if value in log_levels else value)
	
	global_settings[key] = value
