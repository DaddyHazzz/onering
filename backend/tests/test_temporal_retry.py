from backend.workflows.content_workflow import _default_retry_policy, _idempotency_key, ContentRequest

def test_retry_policy_deterministic():
    p1 = _default_retry_policy()
    p2 = _default_retry_policy()
    assert p1.initial_interval == p2.initial_interval == p1.maximum_interval / 12
    assert p1.backoff_coefficient == p2.backoff_coefficient == 2.0
    assert p1.maximum_attempts == p2.maximum_attempts == 3


def test_idempotency_key_stable():
    req = ContentRequest(prompt="t", user_id="u", platform="X", schedule_delay_seconds=10)
    key1 = _idempotency_key(req)
    key2 = _idempotency_key(req)
    assert key1 == key2
    assert len(key1) == 64
