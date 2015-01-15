#!/usr/bin/env python
import webapp2
from handlers import *

class MainPage(WikiParent):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        if self.logged_in_user:
        	self.response.write('Hello, ' + self.logged_in_user.username + '!')
        else:
        	self.response.write('Hello, World!')

application = webapp2.WSGIApplication([
    ('/', MainPage),
    (r'^/signup/?$', SignupHandler)
], debug=True)
