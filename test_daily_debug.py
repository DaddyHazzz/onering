from fastapi.testclient import TestClient
from backend.main import app
from backend.features.collaboration.service import create_draft, append_segment, pass_ring, add_collaborator
from backend.models.collab import CollabDraftRequest, SegmentAppendRequest, RingPassRequest

client = TestClient(app)

# Create test draft
req = CollabDraftRequest(title='Test Draft', platform='x', initial_segment='First segment by alice')
draft = create_draft('alice', req)
draft_id = draft.draft_id

# Add collaborators
add_collaborator(draft_id, 'alice', 'bob', 'contributor')
add_collaborator(draft_id, 'alice', 'carol', 'contributor')

# Pass ring: alice -> bob
draft = pass_ring(draft_id, 'alice', RingPassRequest(to_user_id='bob', idempotency_key='pass1'))

# Bob adds segment
append_segment(draft_id, 'bob', SegmentAppendRequest(content='Second segment by bob', idempotency_key='seg1_bob'))

# Pass ring: bob -> carol
draft = pass_ring(draft_id, 'bob', RingPassRequest(to_user_id='carol', idempotency_key='pass2'))

# Carol adds segment
append_segment(draft_id, 'carol', SegmentAppendRequest(content='Third segment by carol', idempotency_key='seg2_carol'))

# Pass ring: carol -> alice
draft = pass_ring(draft_id, 'carol', RingPassRequest(to_user_id='alice', idempotency_key='pass3'))

# Test the endpoint
resp = client.get(f'/api/analytics/drafts/{draft_id}/daily', headers={'X-User-Id': 'alice'})
print(f'Status: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    print(f'Response keys: {data.keys()}')
    print(f'window_days: {data.get("window_days")}')
    print(f'daily list length: {len(data.get("daily", []))}')
    print(f'Sample day: {data.get("daily", [{}])[0] if data.get("daily") else "empty"}')
else:
    print(f'Error: {resp.text}')
