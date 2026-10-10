import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from journal.cot_service import fetch_and_save_cot
try:
    saved = fetch_and_save_cot('002601')
    print("Saved:", saved)
except Exception as e:
    print("Error:", e)
