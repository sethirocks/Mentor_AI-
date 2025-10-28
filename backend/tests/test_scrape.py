# backend/tests/test_scrape.py
# run using PYTHONPATH=. pytest tests/test_scrape.py -v
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_scrape_endpoint():
    response = client.post(
        "/api/v1/scrape",
        json={"url": "https://h-da.de/studium/orientierungssemester"},
    )

    assert response.status_code == 200, "Scrape endpoint failed"

    data = response.json()

    assert "base_url" in data
    assert "page_count" in data
    assert "pages" in data
    assert isinstance(data["pages"], list)
    assert data["page_count"] == len(data["pages"])

    # Check structure of first page (optional)
    first_page = data["pages"][0]
    for field in ["url", "title", "headings", "paragraphs", "content", "source", "retrieved_at"]:
        assert field in first_page, f"Missing field: {field}"