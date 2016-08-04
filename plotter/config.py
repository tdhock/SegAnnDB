# This file is for the configuration of oauth2 providers.
# We only need the email scope, google+ social api has been configured in app
# confi in developer console
# config.py
from authomatic.providers import oauth2

CONFIG = {

    'google': {
        'class_': oauth2.Google,
        'consumer_key': '1044248525718-jfoomqus2i9p6h8sisldodg1dhc6fjtj.apps.googleusercontent.com',
        'consumer_secret': 'FXQ0fTetQngK3zeRO7Sd8hph',
        'scope': ['email'],
    }
}
