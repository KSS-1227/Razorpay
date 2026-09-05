from dotenv import load_dotenv
load_dotenv(override=True)
import asyncio, os, json, base64
from supabase._async.client import create_client
import urllib.request, urllib.error

PASSWORD = "YOUR_ACTUAL_PASSWORD"  # ← put your real password here

async def test():
    url = os.getenv('SUPABASE_URL')
    anon = os.getenv('SUPABASE_ANON_KEY')

    client = await create_client(url, anon)
    result = await client.auth.sign_in_with_password({
        'email': 'mateenmujawar21@gmail.com',
        'password': PASSWORD
    })

    if not result.session:
        print('Sign in FAILED — check password in test_auth.py')
        return

    token = result.session.access_token
    header = json.loads(base64.b64decode(token.split('.')[0] + '==').decode())
    print('Token alg:', header.get('alg'), '| kid:', header.get('kid', '')[:12])
    print()

    # Test GET
    req = urllib.request.Request('http://localhost:8000/api/workspaces',
        headers={'Authorization': f'Bearer {token}'})
    try:
        r = urllib.request.urlopen(req, timeout=10)
        print('GET /api/workspaces:', r.status)
        print('Body:', r.read().decode()[:300])
    except urllib.error.HTTPError as e:
        print('GET ERROR:', e.code, e.read().decode())

    print()

    # Test POST
    data = json.dumps({'name': 'Mateen Space'}).encode()
    req2 = urllib.request.Request('http://localhost:8000/api/workspaces', data=data,
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
    try:
        r2 = urllib.request.urlopen(req2, timeout=10)
        print('POST /api/workspaces:', r2.status)
        print('Body:', r2.read().decode()[:300])
    except urllib.error.HTTPError as e:
        print('POST ERROR:', e.code, e.read().decode())

asyncio.run(test())
