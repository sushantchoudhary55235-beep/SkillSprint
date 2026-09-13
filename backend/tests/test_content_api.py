"""API tests for content endpoints, repository/service layering, and error handling."""
import pytest


@pytest.fixture()
def seeded_topic(db):
    from app.models.content import Topic

    topic = Topic(name="Percentages", category="Quantitative", description="Pct basics")
    db.add(topic)
    db.commit()
    return topic


def test_list_topics(client, seeded_topic):
    resp = client.get("/api/topics")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Percentages"
    assert data[0]["category"] == "Quantitative"


def test_list_topics_category_filter(client, db):
    from app.models.content import Topic

    db.add_all(
        [
            Topic(name="Percentages", category="Quantitative"),
            Topic(name="Blood Relations", category="Logical"),
        ]
    )
    db.commit()
    resp = client.get("/api/topics", params={"category": "Logical"})
    assert resp.status_code == 200
    data = resp.json()
    assert [t["name"] for t in data] == ["Blood Relations"]


def test_get_topic_404(client):
    resp = client.get("/api/topics/999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error_code"] == "NOT_FOUND"
    assert "detail" not in body  # standard envelope, not FastAPI default


def test_list_companies(client, db):
    from app.models.content import Company

    db.add_all([Company(name="TCS"), Company(name="Infosys")])
    db.commit()
    resp = client.get("/api/companies")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert names == ["Infosys", "TCS"]  # alphabetical


def test_get_company_404(client):
    resp = client.get("/api/companies/12345")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_topic_create_conflict_logic(db):
    """Service layer rejects duplicate topic names (tested directly, no route yet)."""
    from app.core.exceptions import ConflictError
    from app.services.content import ContentService

    service = ContentService(db)
    service.create_topic(name="Probability", category="Quantitative")
    with pytest.raises(ConflictError):
        service.create_topic(name="Probability", category="Quantitative")
