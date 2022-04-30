import json
import hashlib



class Hashable(object):
	'''Mixin to allow hashing'''
	
	def __hash__(self):
		return id(self)
	
	def __eq__(self, other):
		return id(self) == id(other)



def md5(s):
	if not isinstance(s, str):
		s = json.dumps(s, sort_keys=True)
	return hashlib.md5(s.encode('utf-8')).hexdigest()
