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