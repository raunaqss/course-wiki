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
		self.set_secure_cookie('user_id', str(user.key.id()))

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
		logging.info(datetime.datetime.now())
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


class SignupHandler(WikiParent):

	def write_signup_form(self, username = "",
								username_error = "",
								password_error = "",
								verify_error = "",
								email = "",
								email_error = ""):

		self.render('signup.html', title = "Wiki - Signup",
								   username = username,
								   username_error = username_error,
								   password_error = password_error,
								   verify_error = verify_error,
								   email = email,
								   email_error = email_error)

	def get(self):
		self.response.headers['Content-Type'] = 'text/html'
		if self.logged_in_user:
			self.redirect('/')
		else:
			self.write_signup_form()

	def post(self):
		self.response.headers['Content-Type'] = 'text/html'
		username = self.request.get('username')
		password = self.request.get('password')
		verify = self.request.get('verify')
		email = self.request.get('email')

		all_errors  = {"username_error": "",
					   "password_error": "",
					   "verify_error": "",
					   "email_error": ""}
		valid_entries = True

		if not valid_username(username):
			all_errors["username_error"] = "That's not a valid username."
			valid_entries = False

		if not valid_password(password):
			all_errors["password_error"] = "That wasn't a valid password."
			valid_entries = False
		elif password != verify:
			all_errors["verify_error"] = "Your passwords didn't match."
			valid_entries = False

		if email and (not valid_email(email)):
			all_errors["email_error"] = "That's not a valid email."
			valid_entries = False

		if not valid_entries:
			self.response.headers
			self.write_signup_form(username, 
								   all_errors["username_error"],
								   all_errors["password_error"],
								   all_errors["verify_error"],
								   email,
								   all_errors["email_error"])
		else:
			existing_user = WikiUser.get_user(username)

			if existing_user:
				msg = 'This username is already taken!'
				self.write_signup_form(username,
									   msg,
									   '',
									   '',
									   email,
									   '')
			else:
				new_user = WikiUser.register(username, password, email)
				new_user.put()
				new_user.set_user_caches()
				self.login(new_user)
				self.redirect('/')


class LoginHandler(WikiParent):

	def get(self):
		if self.logged_in_user:
			self.redirect('/')
		else:
			self.render('login.html', title='Wiki - Login')

	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')
		user = WikiUser.valid_login(username, password)
		if user:
			self.login(user)
			self.redirect('/')
		else:
			self.render('login.html', 
						title="Login",
						error="Username or Password is incorrect.",
						username = username)


class LogoutHandler(WikiParent):

	def get(self):
		self.logout()
		self.redirect('/') # redirect to the front page after logout


class PageHandler(WikiParent):

	def get(self, page, req_json):
		wiki_page = WikiPage.get_page(page) # db query
		if not wiki_page:
			self.redirect('/_edit%s' % page)
		else:
			# attempts to read version requested from the URL (default: latest)
			version = self.read_secure_version(wiki_page)

			if req_json: # if the url ends with .json
				self.render_json(wiki_page.make_dict(version))
			else:
				self.render("page.html", 
							title = page[1:], 
							user = self.logged_in_user, 
							wiki_page = wiki_page, 
							version = version)


class EditHandler(WikiParent):

	def get(self, page):
		# this was giving you trouble when you had self.logged_in_user == None
		if self.logged_in_user:
			wiki_page = WikiPage.get_page(page)
			version = self.read_secure_version(wiki_page)
			self.render("edit.html", title = 'Edit - %s' % page[1:], 
									 user = self.logged_in_user, 
									 wiki_page = wiki_page, 
									 version = version,
									 error = self.request.get('error'))
		else:
			self.redirect('/login') # redirect to login page if not logged in

	def post(self, page):
		if self.logged_in_user:
			content = self.request.get('content')
			wiki_page = WikiPage.get_page(page)
			if wiki_page:
				valid = content and (content != wiki_page.content[-1])
			else:
				valid = content
			if valid:
				# if the page exists -> update it | if it doesn't -> create it
				if wiki_page:
					wiki_page = wiki_page.update(content)
				else: 
					wiki_page = WikiPage.construct(content, page)
				wiki_page.put()
				set_cache(page, wiki_page)
				self.redirect(page)
			else:
				if valid == '':
					error = 'Content Required !!'
				elif valid == False:
					error = 'Page not modified !!'
				self.redirect('/_edit' + page + '?error=%s' % error)
				# error = "Content Required !!"
				# self.render("edit.html", title = 'Edit - %s' % page[1:], 
				# 	error = error, user = self.logged_in_user)
		else:
			self.redirect('/login') # handling the edge case or cookie deletion


class HistoryHandler(WikiParent):
	
	def get(self, page):
		wiki_page = WikiPage.get_page(page)
		self.render("history.html", title = 'History - %s' % page[1:], 
			user = self.logged_in_user, wiki_page = wiki_page)