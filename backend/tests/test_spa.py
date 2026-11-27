from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.spa import SpaStaticFiles


def _client(tmp_path):
    (tmp_path / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    app.mount("/", SpaStaticFiles(directory=str(tmp_path), html=True), name="frontend")
    return TestClient(app)


def test_client_side_route_serves_index_html_on_refresh(tmp_path):
    client = _client(tmp_path)
    for path in ("/decks", "/decks/3", "/review/5", "/cards/12/edit"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert r.text == "<html>app</html>"


def test_existing_files_are_served_as_is(tmp_path):
    client = _client(tmp_path)
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/").text == "<html>app</html>"


def test_missing_file_and_unknown_api_path_stay_404(tmp_path):
    client = _client(tmp_path)
    assert client.get("/assets/missing.js").status_code == 404
    assert client.get("/api/nope").status_code == 404
    assert client.get("/api/health").json() == {"status": "ok"}
