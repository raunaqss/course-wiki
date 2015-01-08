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