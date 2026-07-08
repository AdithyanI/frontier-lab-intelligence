from fastapi.testclient import TestClient

from fli.web.app import app

client = TestClient(app)


def test_home():
    r = client.get("/")
    assert r.status_code == 200
    assert "Frontier Lab Intelligence" in r.text


def test_architecture_renders_doc_with_mermaid():
    r = client.get("/architecture")
    assert r.status_code == 200
    assert "System pipeline" in r.text
    assert 'class="mermaid"' in r.text


def test_static_css():
    r = client.get("/static/app.css")
    assert r.status_code == 200
    assert "--primary" in r.text
