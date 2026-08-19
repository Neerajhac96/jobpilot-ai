import requests
import json
import os

base_url = 'http://localhost:8000'
app_id = 1

print('Creating test application or setting to APPROVED...')
requests.post(f'{base_url}/applications/{app_id}/approve')

test_url = 'file:///' + os.path.abspath('test_submit_form.html').replace('\\\\', '/')
print('Test URL:', test_url)

print('Sending confirm-submission...')
r = requests.post(f'{base_url}/applications/{app_id}/confirm-submission', json={'confirm': True, 'test_url': test_url})
print('Response Status:', r.status_code)
try:
    data = r.json()
    print(json.dumps(data, indent=2))
except Exception as e:
    print('Failed to parse json:', e)

print('\nChecking DB application state...')
r2 = requests.get(f'{base_url}/applications/{app_id}')
print(json.dumps(r2.json(), indent=2))
