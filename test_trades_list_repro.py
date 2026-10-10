import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import RequestFactory
from journal.views import trades_list

try:
    factory = RequestFactory()
    request = factory.get('/trades/')
    response = trades_list(request)
    print("Trades list rendered. Status code:", response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
