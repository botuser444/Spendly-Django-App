import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spendly_project.settings')
import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from budget.views import download_report

User = get_user_model()

# Try to find a superuser or any user
user = User.objects.filter(is_superuser=True).first() or User.objects.first()
if not user:
    print('No users found in DB; create a user first')
    sys.exit(1)

rf = RequestFactory()
req = rf.post('/download-report/')
req.user = user
# Ensure message storage is available on the fake request so views can add messages
# Provide a minimal dummy message storage so view calls to messages.* won't fail in this test context
class _DummyMessages:
    def __init__(self):
        self._list = []
    def add(self, level, message, extra_tags=''):
        self._list.append((level, message))
    def __iter__(self):
        return iter(self._list)

setattr(req, '_messages', _DummyMessages())

print('Testing download_report as user:', user.username)

resp = download_report(req)

# If it's a FileResponse, write it out
out_dir = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(out_dir, exist_ok=True)

content_type = resp.get('Content-Type', 'unknown')
print('Response Content-Type:', content_type)

# Determine filename
filename = getattr(resp, 'filename', None) or 'downloaded_report'
out_path = os.path.join(out_dir, filename)

# If response has streaming_content
if hasattr(resp, 'streaming_content'):
    with open(out_path, 'wb') as f:
        for chunk in resp.streaming_content:
            f.write(chunk)
else:
    # Fallback: attempt to read resp.content
    try:
        with open(out_path, 'wb') as f:
            f.write(resp.content)
    except Exception as e:
        print('Could not write response content:', e)
        sys.exit(1)

print('Saved report to:', out_path)
