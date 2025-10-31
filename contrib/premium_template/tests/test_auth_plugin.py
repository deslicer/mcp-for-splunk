from premium_server import plugins


def test_authorized_false_when_no_key(monkeypatch):
    monkeypatch.delenv("PREMIUM_API_KEY", raising=False)
    assert plugins._authorized({"x-api-key": "x"}) is False


def test_authorized_true_when_match(monkeypatch):
    monkeypatch.setenv("PREMIUM_API_KEY", "k")
    assert plugins._authorized({"x-api-key": "k"}) is True

