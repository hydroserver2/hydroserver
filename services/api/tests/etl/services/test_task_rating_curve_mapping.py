import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from ninja.errors import HttpError

from domains.sta.models import Thing, ThingFileAttachment
from domains.etl.services import TaskService
from interfaces.api.schemas import TaskPatchBody


task_service = TaskService()
TASK_ID = uuid.UUID("019adbc3-35e8-7f25-bc68-171fb66d446e")
WORKSPACE_ID = uuid.UUID("b27c51a0-7374-462d-8a53-d97d47176c10")


def create_workspace_thing() -> Thing:
    return Thing.objects.create(
        workspace_id=WORKSPACE_ID,
        name="Test Thing",
        description="",
        sampling_feature_type="Site",
        sampling_feature_code="TEST_THING",
        site_type="Stream",
        is_private=False,
    )


def create_thing_rating_curve(
    thing: Thing, name: str = "Validation curve"
) -> ThingFileAttachment:
    return ThingFileAttachment.objects.create(
        thing=thing,
        name=name,
        description="",
        file_attachment_type="rating_curve",
        file_attachment=SimpleUploadedFile(
            "validation_curve.csv",
            b"input_value,output_value\n1.0,2.0\n2.0,4.0\n",
            content_type="text/csv",
        ),
    )


def test_update_task_accepts_thing_rating_curve_url(get_principal):
    thing = create_workspace_thing()
    rating_curve = create_thing_rating_curve(thing=thing)
    rating_curve_url = rating_curve.link

    updated = task_service.update(
        principal=get_principal("owner"),
        uid=TASK_ID,
        data=TaskPatchBody(
            mappings=[
                {
                    "sourceIdentifier": "test_value",
                    "paths": [
                        {
                            "targetIdentifier": "27c70b41-e845-40ea-8cc7-d1b40f89816b",
                            "dataTransformations": [
                                {
                                    "type": "rating_curve",
                                    "ratingCurveUrl": rating_curve_url,
                                }
                            ],
                        }
                    ],
                }
            ]
        ),
    )

    transform = updated["mappings"][0]["paths"][0]["data_transformations"][0]
    assert transform["type"] == "rating_curve"
    assert transform["ratingCurveUrl"] == rating_curve_url


def test_update_task_rejects_rating_curve_url_not_in_workspace_thing_attachments(
    get_principal,
):
    with pytest.raises(HttpError) as exc_info:
        task_service.update(
            principal=get_principal("owner"),
            uid=TASK_ID,
            data=TaskPatchBody(
                mappings=[
                    {
                        "sourceIdentifier": "test_value",
                        "paths": [
                            {
                                "targetIdentifier": "27c70b41-e845-40ea-8cc7-d1b40f89816b",
                                "dataTransformations": [
                                    {
                                        "type": "rating_curve",
                                        "ratingCurveUrl": "https://example.com/not-allowed.csv",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            ),
        )

    assert exc_info.value.status_code == 400
    assert "thing rating curve attachment" in exc_info.value.message


def test_update_task_rejects_rating_curve_without_rating_curve_url(get_principal):
    create_thing_rating_curve(thing=create_workspace_thing())

    with pytest.raises(HttpError) as exc_info:
        task_service.update(
            principal=get_principal("owner"),
            uid=TASK_ID,
            data=TaskPatchBody(
                mappings=[
                    {
                        "sourceIdentifier": "test_value",
                        "paths": [
                            {
                                "targetIdentifier": "27c70b41-e845-40ea-8cc7-d1b40f89816b",
                                "dataTransformations": [{"type": "rating_curve"}],
                            }
                        ],
                    }
                ]
            ),
        )

    assert exc_info.value.status_code == 400
    assert "ratingCurveUrl" in exc_info.value.message
