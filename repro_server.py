import os
import sys
import threading
import time
import requests
import uvicorn

root = r"c:\\Users\\SRLF\\Cricksy_Scorer"
backend_path = os.path.join(root, 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

os.environ['CRICKSY_IN_MEMORY_DB'] = '1'

config = uvicorn.Config('backend.main:app', host='127.0.0.1', port=8001, log_level='debug')
server = uvicorn.Server(config)

thread = threading.Thread(target=server.run, daemon=True)
thread.start()

for _ in range(80):
    try:
        resp = requests.get('http://127.0.0.1:8001/health', timeout=0.5)
        if resp.status_code == 200:
            break
    except Exception:
        pass
    time.sleep(0.5)

payload = {
    'team_a_name': 'Team Alpha',
    'team_b_name': 'Team Beta',
    'players_a': [f'Alpha Player {i}' for i in range(1, 12)],
    'players_b': [f'Beta Player {i}' for i in range(1, 12)],
    'match_type': 'limited',
    'overs_limit': 20,
    'dls_enabled': True,
    'toss_winner_team': 'Team Alpha',
    'decision': 'bat',
}

resp = requests.post('http://127.0.0.1:8001/games', json=payload)
print('status', resp.status_code)
print('text', resp.text)

server.should_exit = True
thread.join()
