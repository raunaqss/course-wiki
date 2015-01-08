import webapp2
import jinja2

import os
import json
import string
import logging
import datetime

from google.appengine.ext import db
from google.appengine.api import memcache

from utils import *
from dbmodels import *

# initializing jinja2
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
							   autoescape = True)


class Handler(webapp2.RequestHandler):

	def write(self, *a, **kw):
		self.response.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, **params):
		self.write(self.render_str(template, **params))


class WikiParent(Handler):

	def set_secure_cookie(self, cookie_name, val):
		'''
		Takes the name and val of the cookie.
		Makes the secure value of the cookie by using the val in the input.
		Sets the Cookie with the name provided and the secure cookie value.

		cookie_name: String
		nal = String
		'''
		cookie_val = make_secure_val(val)
		self.response.headers.add_header('Set-Cookie',
			"%s=%s; Path=/" % (cookie_name, cookie_val))

	def read_secure_cookie(self, cookie_name):
		'''
		Returns the Value of the cookie (without the hash) if the cookie value
		is valid.

		Name: String
		'''
		browser_cookie = self.request.cookies.get(cookie_name)
		#logging.info('browser cookie is %s' % browser_cookie)
		return browser_cookie and check_secure_val(browser_cookie)

	def read_secure_version(self, wiki_page):
		'''
		Returns the correct version integer, according user inputs.

		Checks if user has queried the version number.
		if yes -> checks if the version is valid and returns it.
		if not -> returns the latest version

		wiki_page: WikiPage entity
		'''
		if wiki_page:
			version = self.request.get('v')
			if (version and version.isdigit() and
				int(version) <= len(wiki_page.content)):
				version = int(version)
			else:
				# if version is not a digit, we default to the latest version
				version = len(wiki_page.content)
			return version

	def login(self, user):
		'''
		Uses the funciton set_secure_cookie() to set the secure cookie value in
		order to login the user.

		user: WikiUser entity
		'''
		self.set_secure_cookie('user_id', str(user.key().id()))

	def logout(self):
		'''Sets the cookie to blank'''
		self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

	def initialize(self, *a, **kw):
		'''
		Overrides webapp2's initialize function. This function is run with
		every request to our blog.
		This function calls webapp2's initialize function to maintain important
		functionality.

		It reads secure val of the cookie: 
		if it exists: 
		it sets the corresponding user to the variable self.logged_in_user.
		'''
		webapp2.RequestHandler.initialize(self, *a, **kw)
		uid = self.read_secure_cookie('user_id')
		#logging.info('uid is %s' % uid)
		self.logged_in_user = uid and WikiUser.get_user(uid)

	def render_json(self, d):
		'''
		Renders the JSON for the given dictionary d.
		Sets the headers for the content type to the appropriate type (for
		rendering JSON.)
		'''
		dumped_json = json.dumps(d)
		self.response.headers[
			'Content-Type'] = 'application/json; charset=UTF-8'
		self.write(dumped_json)