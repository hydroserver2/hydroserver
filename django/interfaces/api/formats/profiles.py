from dataclasses import dataclass
from typing import Iterable, Optional

from interfaces.api.collections import CollectionDefinition

# Profile URIs identify profiles (RFC 6906, Section 3); nothing is served at them. OGC API - Common Part 3 requires
# profiles outside the OGC Profile Register to be identified by HTTP(S) URIs (/req/profile-parameter/profile-param).
PROFILE_URI_BASE = "https://hydroserver.org/profiles"

PROFILE_PARAMETER_CONFORMANCE = "http://www.opengis.net/spec/ogcapi-common-3/1.0/conf/profile-parameter"


@dataclass(frozen=True)
class Profile:
    """
    A variation of a format's representation of a collection's items (OGC API - Common Part 3), selected by the
    profile parameter with its URI. The key names it within the API, e.g. in CollectionDefinition.formats; clients
    only see the URI.
    """

    key: str
    uri: str
    title: str


PROFILES: dict[str, Profile] = {
    profile.key: profile
    for profile in (
        Profile("row", f"{PROFILE_URI_BASE}/observations/row", "Observations as rows grouped by datastream"),
        Profile("column", f"{PROFILE_URI_BASE}/observations/column", "Observations as columns grouped by datastream"),
    )
}


def resolve_profile(uri: str) -> Optional[Profile]:
    """The profile a profile parameter value names (/req/profile-parameter/profile-param B)."""

    return next((profile for profile in PROFILES.values() if profile.uri == uri), None)


def collection_profiles(collection: CollectionDefinition, format_key: str) -> list[Profile]:
    """
    The profiles a collection supports in a format. A response is in one of them only if the client requests it;
    otherwise it's in the format's standard representation, without a profile.
    """

    return [PROFILES[key] for key in collection.formats.get(format_key, ())]


def has_profiles(collection: CollectionDefinition) -> bool:
    return any(collection.formats.values())


def profiles_conformance(collections: Iterable[CollectionDefinition]) -> list[str]:
    return [PROFILE_PARAMETER_CONFORMANCE] if any(has_profiles(collection) for collection in collections) else []
