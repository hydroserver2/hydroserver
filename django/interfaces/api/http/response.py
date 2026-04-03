from django.http import HttpResponse


def apply_response_pagination_headers(
    response: HttpResponse,
    count: int,
    page_size: int,
    page: int,
):
    """
    Applies pagination headers to an HTTP response object to enable pagination metadata.

    Adds informational headers related to pagination, such as the total count of items, the
    page size, the current page number, and the total number of pages.
    """

    response["X-Total-Count"] = str(count)
    response["X-Page-Size"] = str(page_size)

    if page_size > 0:
        response["X-Page"] = str(page)
        response["X-Total-Pages"] = str((count + page_size - 1) // page_size)

    return response
