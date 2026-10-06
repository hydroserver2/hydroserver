import pytest
from django.test import override_settings


@pytest.mark.django_db
@override_settings(CORS_ORIGIN_ALLOW_ALL=True)
def test_observation_checksum_header_is_readable_cross_origin(client):
    response = client.get(
        "/api/data/datastreams/27c70b41-e845-40ea-8cc7-d1b40f89816b/observations",
        HTTP_ORIGIN="http://qc.example.org",
    )

    assert response.status_code == 200
    assert response["X-Checksum"]
    exposed = response["Access-Control-Expose-Headers"].lower().split(", ")
    assert "x-checksum" in exposed
