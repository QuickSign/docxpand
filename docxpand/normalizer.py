"""Module that defines string normalization."""

import re
import string
import typing as tp
import unicodedata as ud

LIGATURES = {"Æ": "AE", "Œ": "OE", "æ": "oe", "œ": "oe"}


def rm_accents(value: str) -> str:
    """Remove accents.

    Args:
        value: text to normalize

    Returns:
        text without accents
    """
    return ud.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def rm_punct(value: str) -> str:
    """Remove punctuation and special chars.

    Args:
        value: text to normalize

    Returns:
        text without punctuation
    """
    return re.sub(rf"[{string.punctuation}]", " ", value)


def collapse_whitespace(value: str) -> str:
    """Collapses whitespaces.

    Args:
        value: text to normalize

    Returns:
        text without multi spaces
    """
    return re.sub(rf"[{string.whitespace}]+", " ", value).strip()


def replace_ligatures(value: str) -> str:
    """Replace the ligatures of a text by their 2-characters counterparts.

    Args:
        value: text to normalize

    Returns:
        normalized text
    """
    for ligature, replacement in LIGATURES.items():
        if ligature in value:
            value = value.replace(ligature, replacement)
    return value


def normalize(value: str, operations: tp.Optional[tp.List[tp.Callable]] = None) -> str:
    """Apply a list of operations to normalize a text.

    Args:
        value: text to normalize
        operations: list of operations

    Returns:
        normalized text
    """
    if operations:
        for operation in operations:
            value = operation(value)
    return value


def cut_and_pad_right(string: str, length: int, padding_string: str = "") -> str:
    cut = string[:length]
    padded = cut + padding_string * (length - len(cut))
    return padded.upper()


def normalize_name(name: tp.Union[str, tp.List[str]], padding_string: str = "") -> tp.Union[str, tp.List[str]]:
    if isinstance(name, list):
        return [normalize_name(val, padding_string) for val in name]
    return (
        normalize(
            name,
            [rm_accents, rm_punct, replace_ligatures, collapse_whitespace],
        )
        .strip()
        .upper()
        .replace(" ", padding_string)
    )
