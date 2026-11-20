import re

import pytest
from django.utils.module_loading import import_string
from ninja import Router

from interfaces.api.collections import COLLECTIONS, get_collection
from interfaces.api.urls import api

COLLECTION_ITEMS_PATH = re.compile(r"/api/ogc/collections/(?P<id>[^/]+)/items")


def test_collection_ids_are_unique():
    ids = [collection.id for collection in COLLECTIONS]

    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("collection", COLLECTIONS, ids=lambda collection: collection.id)
def test_collection_id_is_a_url_segment(collection):
    assert re.fullmatch(r"[a-z]+(-[a-z]+)*", collection.id)


@pytest.mark.parametrize("collection", COLLECTIONS, ids=lambda collection: collection.id)
def test_collection_router_imports_to_a_router(collection):
    assert isinstance(import_string(collection.router), Router)


@pytest.mark.parametrize("collection", COLLECTIONS, ids=lambda collection: collection.id)
def test_collection_title_matches_its_router_tag(collection):
    assert import_string(collection.router).tags == [collection.title]


@pytest.mark.parametrize("collection", COLLECTIONS, ids=lambda collection: collection.id)
def test_collection_has_a_description(collection):
    assert collection.description.strip()


def test_every_collection_items_path_is_registered():
    paths = api.get_openapi_schema(path_prefix="/api/ogc/")["paths"]
    mounted = {
        match["id"] for path in paths if (match := COLLECTION_ITEMS_PATH.fullmatch(path))
    }

    assert mounted == {collection.id for collection in COLLECTIONS}


def test_get_collection_returns_the_registered_collection():
    assert get_collection("monitoring-sites").title == "Monitoring Sites"


def test_get_collection_returns_none_for_an_unknown_id():
    assert get_collection("not-a-collection") is None
