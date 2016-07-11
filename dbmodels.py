import os
import logging
import string
import datetime

import jinja2

from google.appengine.ext import db
from google.appengine.ext import ndb
from google.appengine.api import memcache
from utils import *

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
							   autoescape = True)


def users_key(group = 'default'):
    return ndb.Key('users', group)


class WikiUser(ndb.Model):
	"""
	Datastore entity for each WikiUser.
	Email entry is not required.
	"""
	username = ndb.StringProperty(required = True)
	pw_hash = ndb.StringProperty(required = True)
	email = ndb.StringProperty(required = False)

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
		user = cls.query(cls.username == username,
						 ancestor = users_key()).get()
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
		set_cache(str(self.key.id()), self)


def render_str(template, **params):
	'''
	This method is being written again, for the render_content() method (of
	WikiPage) to use.
	'''
	t = jinja_env.get_template(template)
	return t.render(params)


def page_key(name = 'default'):
	'''
	This function returns the Key object for the ancestor of all WikiPages.
	We structure our data this way to achieve Strong Consistency.
	'''
	return ndb.Key('pages', name)


class WikiPage(ndb.Model):
	"""
	This is the 'WikiPage' entity on the Datastore.
	"""
	content = ndb.TextProperty(repeated = True)
	date_modified = ndb.DateTimeProperty(repeated = True)

	def render_content(self, version):
		"""
		Renders a single post in the templates 'content.html'.
		It converts each line break to the <br> tag to preserve line breaks.
		When called from the HTMl files, this function is not escaped (it's
		marked safe.)

		version: integer
		"""
		# 'version-1' because lists are indexed from 0 and versions start at 1
		self._render_text = markdown.markdown(cgi.escape(self.content[version - 1]))
		return render_str('content.html', wiki_page = self)

	def make_dict(self, version):
		"""
		Makes the dict that is then used by render_json() to render to JSON for
		each page when requested.
		The dict uses the content for the version requested.

		version: integer
		Returns: dictionary
		"""
		# 'version-1' because lists are indexed from 0 and versions start at 1
		d = {"content": self.content[version - 1],
			 "created": self.date_modified[0].strftime("%c"),
			 "last_modified": self.date_modified[version - 1].strftime("%c"),
			 "page_path": self.key.string_id()}
		return d

	def update(self, content):
		"""
		Updates the WikiPage object with the given content.
		Returns it without putting it to the database.
		"""
		date_mod = datetime.datetime.now()
		self.content.append(content)
		self.date_modified.append(date_mod)
		return self

	@classmethod
	def get_page(cls, page):
		"""Returns the WikiPage corresponding to the requested page, if it
		exists.

		Attempts getting from memcache first.
		If memcache get is not successful -> call the DB Query function.
		"""
		wiki_page = memcache.get(page)
		if not wiki_page:
			wiki_page = cls.by_page_key(page)
			if wiki_page:
				set_cache(page, wiki_page)
		return wiki_page

	@classmethod
	def by_page_key(cls, page):
		"""Returns the WikiPage corresponding to the requested page, if it
		exists.

		page: String
		Returns: WikiPage entity
		"""
		logging.error('DB Query')
		wiki_page = cls.get_by_id(page, parent = page_key())
		return wiki_page

	@classmethod
	def construct(cls, content, page):
		"""Constructs the WikiPage entity and Returns it without putting it."""
		date_mod = datetime.datetime.now()
		return cls(parent = page_key(), 
				   content = [content], 
				   date_modified = [date_mod], 
				   id = page)
