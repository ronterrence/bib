"""WSGI config for bibliotheque_project."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bibliotheque_project.settings")

application = get_wsgi_application()
