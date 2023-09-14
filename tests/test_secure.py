
from _util_test import get_adict
import omnibelt.secure as scr


def test_format_key():
	hash = 'test'
	b = scr.format_key(hash)
	assert scr.format_key(hash) == scr.format_key(hash)
	assert len(b) == 44


def test_format_key_no_change():
	hash = 'test'
	ans = b'J0xj59er4QOQoCxO1dQnMvCc5GNxA_LFKLXXLSpztPA='
	b = scr.format_key(hash)
	assert b == ans


def test_secure_key():
	hash = 'test'
	salt = 'salt'

	assert scr.secure_key(hash, salt) == scr.secure_key(hash, salt)
	assert scr.secure_key(hash) != scr.secure_key(hash, salt)
	assert scr.secure_key(hash) == scr.secure_key(hash) # using default master salt


def test_secure_key_no_change():
	hash = 'test'
	ans = '$2b$12$6FwLrxJb5mTPMASTERsaleceQ4HV33YWLgeLFmvCs4Kwedx6fmfRO'
	salt = 'salt'
	assert scr.secure_key(hash, salt) == ans


def test_encryption():

	data = b'aslkjqtest_encryption()2\4awsef'
	hsh = 'test'
	
	x = scr.encrypt(data, hsh)
	rec = scr.decrypt(x, hsh)
	
	assert data == rec
	

def test_secure_pack():
	
	hsh = 'test'
	
	data = get_adict()
	b = scr.secure_pack(data, hsh=hsh)
	rec = scr.secure_unpack(b, hsh=hsh)
	
	assert repr(data) == repr(rec)
	
