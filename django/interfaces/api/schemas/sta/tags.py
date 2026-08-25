def reject_empty_tag_keys_and_values(tags: dict) -> dict:
    for key, value in tags.items():
        if key == "":
            raise ValueError("Tag keys must not be empty.")
        if value == "":
            raise ValueError("Tag values must not be empty.")
    return tags
