from ninja import Router, Query
from ninja.security import django_auth
from sensorthings.api.schemas import Filters


router = Router(tags=['Things'])


@router.get(
    '/Things',
    auth=django_auth,
    # response=ThingsResponseBody,
    by_alias=True,
    url_name='list_thing'
)
def get_things(request, filters: Filters = Query(...)):
    """"""

    return {}


@router.get(
    '/Things({thing_id})',
    auth=django_auth,
    # response=ThingResponseBody,
    by_alias=True
)
def get_thing(request, thing_id: str):
    """"""

    return {}


@router.post(
    '/Things',
    auth=django_auth
)
def create_thing(request):
    """"""

    return {}


@router.patch(
    '/Things({thing_id})',
    auth=django_auth
)
def update_thing(request, thing_id: str):
    """"""

    return {}


@router.delete(
    '/Things({thing_id})',
    auth=django_auth
)
def delete_thing(request, thing_id: str):
    """"""

    return {}
