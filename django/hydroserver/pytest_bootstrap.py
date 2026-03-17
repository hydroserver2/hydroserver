import os


# Some local shells export DEBUG=release, which decouple cannot cast to bool.
# Normalize only that invalid value before pytest-django imports settings.
if os.environ.get("DEBUG", "").strip().lower() == "release":
    os.environ["DEBUG"] = "False"
