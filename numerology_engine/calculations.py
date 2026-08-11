from __future__ import annotations

import re
from datetime import date


MASTER_NUMBERS = {11, 22, 33}


def reduce_number(value: int, *, preserve_master: bool = True) -> int:
    number = abs(int(value))
    while number > 9:
        if preserve_master and number in MASTER_NUMBERS:
            return number
        number = sum(int(char) for char in str(number))
    return number


def birth_number(date_of_birth: date) -> int:
    return reduce_number(date_of_birth.day)


def life_path_number(date_of_birth: date) -> int:
    digits = [int(char) for char in date_of_birth.isoformat() if char.isdigit()]
    return reduce_number(sum(digits))


def property_number(identifier: str) -> int:
    digits = re.findall(r"\d", identifier or "")
    if not digits:
        raise ValueError(
            "Property identifier must contain at least one digit."
        )
    return reduce_number(sum(int(digit) for digit in digits))
