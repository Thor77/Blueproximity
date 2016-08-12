import gettext
from locale import getdefaultlocale
from os import environ

APP_NAME = 'blueproximity'

# Get the local directory since we are not installing anything
local_path = 'LANG/'

# Collect available languages
available_languages = [getdefaultlocale()[0]]  # system locale
available_languages += environ.get('LANGUAGE', '').split(':')  # environment
available_languages += ["en"]  # default language

gettext.bindtextdomain(APP_NAME, local_path)
gettext.textdomain(APP_NAME)
# Get the language to use
gettext_language = gettext.translation(
    APP_NAME, local_path, languages=available_languages, fallback=True
)
# create _-shortcut for translations
_ = gettext_language.gettext
