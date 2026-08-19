import requests
import os
import json

base_url = 'http://localhost:8000'
app_id = 1

requests.post(f'{base_url}/applications/{app_id}/approve')

test_url = 'https://job-boards.greenhouse.io/warp/jobs/4324888004'
print('Test URL:', test_url)

r = requests.post(f'{base_url}/applications/{app_id}/dry-run', params={'test_url': test_url})
print('Dry-run status:', r.status_code)

if r.status_code == 200:
    data = r.json()
    print('\n--- DRY RUN REPORT ---')
    print('Status:', data.get('status'))
    print('Submit Clicked:', data.get('submit_clicked'))
    print('Resume Uploaded:', data.get('resume_uploaded'))
    
    print('\nAudit Data:')
    print('Audit Dir:', data.get('audit_dir'))
    print('Screenshot:', data.get('screenshot_path'))
    print('HTML Page:', data.get('page_html_path'))
    print('JSON Report:', data.get('report_path'))
    print('Captcha Detected:', data.get('captcha_detected'))
    print('Submission Blocked:', data.get('submission_blocked'))
    
    print('\nSensitive Fields Detected:')
    for sf in data.get('sensitive_fields_detected', []):
        print('  -', sf.get('label'), sf.get('decision'))
        
    print('\nFields Filled:')
    for f in data.get('fields_filled', []):
        print('  -', f.get('label'), f.get('id'))
        
    print('\nUnknown Fields:')
    for f in data.get('unknown_fields', []):
        print('  -', f.get('label'), f.get('id'))
        
    print('\nUser Input Required:')
    for f in data.get('user_input_required', []):
        print('  -', f.get('label'), f.get('id'))
        
    print('\nUnsafe To Autofill:')
    for f in data.get('unsafe_to_autofill', []):
        print('  -', f.get('label'), f.get('id'))
else:
    print('Error:', r.text)

print('\nTesting other endpoints...')
for ep in ['/', '/health', '/candidate/me', '/jobs', '/jobs/ranked', '/applications']:
    print(ep, requests.get(f'{base_url}{ep}').status_code)
