import pytest
from django.urls import reverse

from core.web.models import InstanceConfiguration
from interfaces.web.views import get_app_settings_context


def test_analytics_disabled_by_default():
    assert get_app_settings_context()["analyticsConfiguration"] == {
        "enableClarityAnalytics": False,
        "clarityProjectId": None,
        "enableGoogleAnalytics": False,
        "googleAnalyticsMeasurementId": None,
    }


@pytest.mark.parametrize("enable_google", [False, True])
@pytest.mark.parametrize("enable_clarity", [False, True])
def test_admin_can_configure_analytics_independently(
    admin_client, enable_google, enable_clarity
):
    instance = InstanceConfiguration.get_configuration()
    configuration = instance.analytics_configuration
    data = {
        "instance_configuration": instance.pk,
        "clarity_project_id": "clarity-project",
        "google_analytics_measurement_id": "G-TEST123456",
    }
    if enable_google:
        data["enable_google_analytics"] = "on"
    if enable_clarity:
        data["enable_clarity_analytics"] = "on"

    response = admin_client.post(
        reverse("admin:web_analyticsconfiguration_change", args=(configuration.pk,)),
        data,
    )

    assert response.status_code == 302
    assert get_app_settings_context()["analyticsConfiguration"] == {
        "enableClarityAnalytics": enable_clarity,
        "clarityProjectId": "clarity-project",
        "enableGoogleAnalytics": enable_google,
        "googleAnalyticsMeasurementId": "G-TEST123456",
    }


def test_admin_can_leave_analytics_ids_blank(admin_client):
    instance = InstanceConfiguration.get_configuration()
    response = admin_client.post(
        reverse(
            "admin:web_analyticsconfiguration_change",
            args=(instance.analytics_configuration.pk,),
        ),
        {
            "instance_configuration": instance.pk,
            "clarity_project_id": "",
            "google_analytics_measurement_id": "",
        },
    )

    assert response.status_code == 302
    configuration = get_app_settings_context()["analyticsConfiguration"]
    assert not configuration["enableGoogleAnalytics"]
    assert not configuration["googleAnalyticsMeasurementId"]
