import os
import logging
import string
import datetime

import jinja2

from google.appengine.ext import db
from google.appengine.api import memcache
from utils import *

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
							   autoescape = True)


def users_key(group = 'default'):
    return db.Key.from_path('users', group)


class WikiUser(db.Model):
	"""
	Datastore entity for each WikiUser.
	Email entry is not required.
	"""
	username = db.StringProperty(required = True)
	pw_hash = db.StringProperty(required = True)
	email = db.EmailProperty(required = False)

	@classmethod
	def get_user(cls, uid_or_username):
		"""
		uid_or_username: String
		Returns WikiUser

		Attempts memcache get first.
		If memcache get is not successful -> Calls the appropriate DB Query
		funciton (And sets to memcache.)
		"""
		user = memcache.get(uid_or_username)
		if not user:
			if uid_or_username.isdigit():
				user = cls.by_id(uid_or_username)
			else:
				user = cls.by_username(uid_or_username)
				
			if user:
				user.set_user_caches()
		return user

	@classmethod
	def by_id(cls, uid):
		'''
		Returns the user with the id uid.

		uid: String
		Returns: WikiUser entity
		'''
		logging.error('DB QUERY')
		return cls.get_by_id(long(uid), parent = users_key())

	@classmethod
	def by_username(cls, username):
		'''
		Returns the user with the given username.

		username: String
		Returns: WikiUser entity
		'''
		logging.error('DB QUERY')
		user = cls.all().ancestor(users_key()).filter("username = ",
													  username).get()
		return user

	@classmethod
	def register(cls, username, pw, email = None):
		'''
		Hashes the given password (pw).
		Constructs a WikiUser entity for the given information.
		Returns the construted WikiUser entity.

		name: String
		pw: String
		email: String (optional)

		Returns: WikiUser entity
		'''
		pw_hash = make_pw_hash(username, pw)
		if email:
			return cls(parent = users_key(),
						username = username,
						pw_hash = pw_hash,
						email = email)
		else:
			return cls(parent = users_key(),
					   username = username,
					   pw_hash = pw_hash)

	@classmethod
	def valid_login(cls, username, pw):
		'''
		if user exits and if login is valid: Returns WikiUser

		name: String
		pw: String

		Returns: WikiUser entity
		'''
		user = cls.get_user(username)
		if user and valid_pw(username, pw, user.pw_hash):
			return user

	def set_user_caches(self):
		set_cache(self.username, self)
		set_cache(str(self.key().id()), self)