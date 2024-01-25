import typing as tp
from datetime import datetime

import dateparser
from dateutil.relativedelta import relativedelta

from docxpand.utils import nested_get

DATE_PARSER_SETTINGS = {
    "DATE_ORDER": "DMY",
    "PARSERS": ["absolute-time"],
    "STRICT_PARSING": True,
}


class Provider:
    def date_plus_delta(
        self,
        field_path: tp.List[str],
        years: int,
        months: int,
        days: int,
        existing_fields: tp.Optional[tp.Dict] = None,
    ) -> tp.Optional[datetime]:
        if not existing_fields:
            return None

        field_value = nested_get(existing_fields, field_path, None)
        if not field_value:
            return None

        datetime = dateparser.parse(field_value, settings=DATE_PARSER_SETTINGS)
        return datetime + relativedelta(years=years, months=months, days=days)
