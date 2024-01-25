import os
import magic
import typing as tp

from docxpand.image import ColorSpace, Image



def guess_mimetype(
    filename: tp.Optional[str] = None, filecontent: tp.Optional[bytes] = None
) -> str:
    """Guess the mime type of a file or a binary content.

    Either filename or filecontent must be set.

    Args:
        filename: path to the file on which the type must be guessed
        filecontent: binary content on which the type must be guessed

    Returns:
        the mimetype of the file or binary content (e.g.: 'application/pdf').

    Raises:
        ValueError: if both arguments are not set
    """
    if filecontent:
        return str(magic.from_buffer(filecontent, mime=True))
    if not filename:
        raise ValueError("You should set either filename or filecontent")
    return str(magic.from_file(filename, mime=True))


def nested_get(
    dictionary: tp.Dict[str, tp.Any], keys: tp.List[str], default: tp.Any
) -> tp.Any:
    """Get a value in a dictionary using nested string keys.

    Args:
        dictionary: the dictionary from which the value must be extracted
        keys: the list of keys
        default: the default value to return if the path does not exist

    Returns:
        the value contained in the dictionary after getting the nested keys,
        or the default value if the path does not exist
    """
    current = dictionary
    for key in keys:
        if key not in current:
            return default
        current = current.get(key)
    return current


def get_field_from_any_side(
    dictionary: tp.Dict[str, tp.Any],
    key: str,
    default: tp.Any,
    side_names: tp.Optional[tp.List[str]] = None,
) -> tp.Any:
    """Search a value using its key in second-level nested dictionaries.

    A side name is used as first key. If `side_names` is not given, then
    `["front", "back"]` is used.

    Args:
        dictionary: the dictionary from which the value must be extracted
        key: the key of the field to get
        default: the default value to return if the field does not exist
        side_names: name of the sides

    Returns:
        the value contained in one of the second-level dictionaries,
        or the default value if the path does not exist
    """
    if side_names is None:
        side_names = ["front", "back"]

    for side_name in side_names:
        if side_name not in dictionary:
            continue
        if key in dictionary[side_name]:
            return dictionary[side_name][key]

    return default


def floor_to_multiple(number: float, base: int) -> int:
    """Return the closest integer multiple of a base less than an upper bound.

    Only works for positive numbers.

    Args:
        number: the upper bound
        base: the output must be a multiple of this base number

    Returns:
        the closest integer multiple of the base less than the upper bound

    Raises:
        NotImplementedError: for negative numbers
    """
    if number < 0:
        raise NotImplementedError(
            "floor_to_multiple not implemented for negative numbers"
        )
    return int(number / base) * base
