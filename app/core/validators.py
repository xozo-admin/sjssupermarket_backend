import re

PHONE_PATTERN = re.compile(r"^\+?[1-9]\d{7,14}$")


def is_valid_phone(value: str) -> bool:
    return bool(PHONE_PATTERN.fullmatch(value))
