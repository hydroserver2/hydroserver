"""Compatibility imports used by historical migrations."""

from .monitoring_site import (
    monitoring_site_file_attachment_storage_path as thing_file_attachment_storage_path,
)


__all__ = ["thing_file_attachment_storage_path"]
