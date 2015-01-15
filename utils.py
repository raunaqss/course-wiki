import random
import string
import hashlib
import hmac
import re
import logging

from google.appengine.api import memcache


def set_cache(cache_key, value):
	"""
	Sets memcache using Check & Set.
	It uses only 'set' if the key is uninitialized.
	"""
	client = memcache.Client()
	try:
		while True:
			old_value = client.gets(cache_key)
			assert old_value, 'Uninitialized Key'
			if client.cas(cache_key, value):
				break
	except AssertionError:
		client.add(cache_key, value)
		logging.error('Initializing Key')


SECRET = 'this is a secret for hashing.'


def make_salt():
	"""	
	Returns a random 5 letter salt used for hashing the password.
	Helper function for: make_pw_hash()

	Input: NA
	Returns: String
	"""
	return ''.join(random.choice(string.letters) for x in xrange(5))


def make_pw_hash(name, pw, salt = make_salt()):
	"""
	Returns the valid password hash: 'string of password hash','salt'
	The hashed password has a comma , as the separator.

	name: String
	pw: String
	Salt: String

	Returns: String
	"""
	h = hashlib.sha256(name + pw + salt).hexdigest()
	return '%s,%s' % (h, salt)


def valid_pw(name, pw, h):
	"""
	Returns a boolean for whether the given password is valid.

	name: String
	pw: String
	h: String
	Returns: Boolean
	"""
	return h == make_pw_hash(name, pw, h.split(',')[-1])


def hash_str(val):
	"""
	Helper function for make_secure_val(). Hashes the val with the SECRET in
	the global environment.

	val: String
	Returns: String
	"""
	return hmac.new(SECRET, val).hexdigest()


def make_secure_val(val):
	"""
	Makes the hashed cookie for a given val.
	The hashed cookie uses a pipe | as the separator between the value and it's
	hash.

	val: String
	Returns: String
	"""
	return '%(value)s|%(hashed)s' % {'value': val, 'hashed': hash_str(val)}


def check_secure_val(h):
	"""
	Used to validate the hashed cookie when received from the browser in a
	request.
	if valid -> Returns the val of the cookie

	h: String
	Returns: String
	"""
	val = h.split('|')[0]
	if h == make_secure_val(val):
		return val


# The following functions are used by the SignupHandler
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASS_RE = re.compile(r"^.{3,20}$")
EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def valid_username(username):
    return USER_RE.match(username)


def valid_password(password):
    return PASS_RE.match(password)


def valid_email(email):
    return EMAIL_RE.match(email)