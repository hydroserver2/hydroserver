import re

from email.message import Message
from email.utils import collapse_rfc2231_value

import pytest

from interfaces.api.http.links import link_header, quoted_string

# Formats that can't carry links in the body send them in an RFC 8288 Link header. Parameter values are quoted
# strings (RFC 9110), and non-ASCII titles use title* (RFC 8288 Section 3.4.1, RFC 8187), so the header stays ASCII.

UNITS_PATH = "/api/ogc/collections/units/items"


def _parse(header):
    """Reads an RFC 8288 Link header back into (href, {parameter: value}) pairs with the standard library."""

    links = []
    for match in re.finditer(r"<([^>]*)>((?:;\s*[^;,]+=(?:\"(?:[^\"\\\\]|\\\\.)*\"|[^;,]*))*)", header):
        message = Message()
        message["Link"] = "link" + match[2]
        params = {name: collapse_rfc2231_value(message.get_param(name, header="Link")) for name, _ in message.get_params(header="Link")[1:]}
        links.append((match[1], params))
    return links


@pytest.mark.parametrize(
    "value, quoted",
    [("plain", '"plain"'), ('say "hi"', '"say \\"hi\\""'), ("back\\slash", '"back\\\\slash"')],
)
def test_quoted_string_escapes_quotes_and_backslashes(value, quoted):
    assert quoted_string(value) == quoted


def test_link_header_serializes_each_link():
    header = link_header([
        {"href": "https://example.org/items?f=csv&properties=a,b", "rel": "self", "type": "text/csv"},
        {"href": "https://hydroserver.org/profiles/observations/row", "rel": "profile", "title": "Rows"},
    ])

    assert header == (
        '<https://example.org/items?f=csv&properties=a,b>; rel="self"; type="text/csv", '
        '<https://hydroserver.org/profiles/observations/row>; rel="profile"; title="Rows"'
    )


def test_titles_with_quotes_and_non_ascii_characters_keep_the_header_ascii_and_parseable():
    links = [
        {"href": "https://example.org/a", "rel": "self", "type": "text/csv", "title": 'Sites "north" \\ south'},
        {"href": "https://example.org/b", "rel": "alternate", "type": "application/json", "title": "Débit – station"},
    ]

    header = link_header(links)

    assert header.isascii()
    assert "title*=UTF-8''D%C3%A9bit%20%E2%80%93%20station" in header
    assert _parse(header) == [
        ("https://example.org/a", {"rel": "self", "type": "text/csv", "title": 'Sites "north" \\ south'}),
        # The standard library decodes title* back into the title.
        ("https://example.org/b", {"rel": "alternate", "type": "application/json", "title": "Débit – station"}),
    ]


@pytest.mark.django_db
def test_responses_send_parseable_link_headers(client, plain_text_format):
    plain_text_format(links_in_body=False)

    response = client.get(UNITS_PATH, headers={"Accept": "text/plain"})

    assert response.status_code == 200, response.content
    assert response["Link"].isascii()
    assert {params["rel"] for _, params in _parse(response["Link"])} == {"self", "alternate"}
