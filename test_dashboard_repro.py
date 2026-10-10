import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import RequestFactory
from journal.views import dashboard

try:
    factory = RequestFactory()
    request = factory.get('/')
    response = dashboard(request)
    print("Dashboard rendered. Status code:", response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()

