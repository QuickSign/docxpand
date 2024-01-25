import random
import typing as tp
from datetime import datetime

import dateparser
from dateutil.relativedelta import relativedelta
from faker import Faker
from faker.providers.date_time import Provider as DateTimeProvider

from docxpand.normalizer import (
    collapse_whitespace,
    normalize,
    replace_ligatures,
    rm_accents,
    rm_punct,
)
from docxpand.utils import get_field_from_any_side

# Settings for dateparser
DATE_PARSER_SETTING = {
    "DATE_ORDER": "DMY",
    "PARSERS": ["absolute-time"],
    "STRICT_PARSING": True,
}


class Provider:
    def __init__(self, generator: Faker) -> None:
        self.generator = generator
        self.date_time_provider = DateTimeProvider(generator)

    @staticmethod
    def normalize_name(name: str) -> str:
        return (
            normalize(
                name,
                [rm_accents, rm_punct, replace_ligatures, collapse_whitespace],
            )
            .strip()
            .upper()
            .replace(" ", "")
        )

    @staticmethod
    def document_number_full(
        existing_fields: tp.Optional[tp.Dict] = None,
    ) -> str:
        """Full document number generator for GBR driving license."""
        # Get names
        family_name = get_field_from_any_side(existing_fields, "family_name", "SAMPLE")
        family_name = Provider.normalize_name(family_name)
        if isinstance(family_name, list):
            family_name = " ".join(family_name)
        given_name = get_field_from_any_side(existing_fields, "given_name", "SAMPLE")
        if isinstance(given_name, list):
            given_name = " ".join(given_name)
        given_name = Provider.normalize_name(given_name)
        full_name = family_name + given_name

        # Get document number
        document_number = get_field_from_any_side(
            existing_fields, "document_number_short", "123456AB7CD"
        )

        # Make fake checksum
        checksum = f"{random.randint(0, 99):02d}"

        return f"{full_name[:5]}{document_number}  {checksum}"

    @staticmethod
    def allowed_categories(
        probabilities: tp.Optional[tp.Dict] = None,
    ) -> str:
        """Return a list of allowed categories separated by '/'."""
        if not probabilities:
            return ""

        allowed_categories = []
        for category, probability in probabilities.items():
            if random.random() <= probability:
                allowed_categories.append(category)

        return "/".join(allowed_categories)

    def license_date(
        self,
        category: str,
        date_type: str = "start",
        existing_fields: tp.Optional[tp.Dict] = None,
    ) -> tp.Optional[datetime]:
        if date_type not in ["start", "end"]:
            raise ValueError(
                f"The date_type must be 'start' or 'end', got {date_type}."
            )

        # We need special checks for f/k/l/n/p/q categories since the dates
        # are grouped in one single line in the table
        fklnpq = "fklnpq"
        categories = get_field_from_any_side(
            existing_fields, "license_categories", ""
        ).split("/")
        if category != fklnpq and category not in categories:
            return None
        if category == fklnpq and not any([cat in categories for cat in fklnpq]):
            return None

        start_date = None
        if date_type == "start":
            if existing_fields:
                for key, value in existing_fields.get("back", {}).items():
                    if "start_date" in key and key[0].lower() == category[0].lower():
                        start_date = dateparser.parse(
                            value, settings=DATE_PARSER_SETTING
                        )
                        if start_date:
                            return start_date
            birth_date = dateparser.parse(
                get_field_from_any_side(existing_fields, "birth_date", "01.01.1970"),
                settings=DATE_PARSER_SETTING,
            )
            end_date = dateparser.parse(
                get_field_from_any_side(existing_fields, "date_issued", ""),
                settings=DATE_PARSER_SETTING,
            )
            if not end_date:
                end_date = "today"

            return self.date_time_provider.date_between(
                start_date=birth_date + relativedelta(years=17),
                end_date=end_date,
            )

        # elif date_type == "end":
        if existing_fields:
            for key, value in existing_fields.get("back", {}).items():
                if "start_date" in key and key[0].lower() == category[0].lower():
                    start_date = dateparser.parse(value, settings=DATE_PARSER_SETTING)
                    if start_date:
                        break

        if not start_date:
            birth_date = dateparser.parse(
                get_field_from_any_side(existing_fields, "birth_date", "01.01.1970"),
                settings=DATE_PARSER_SETTING,
            )
            end_date = dateparser.parse(
                get_field_from_any_side(existing_fields, "date_issued", ""),
                settings=DATE_PARSER_SETTING,
            )
            if not end_date:
                end_date = "today"
            start_date = self.date_time_provider.date_between(
                start_date=birth_date + relativedelta(years=17),
                end_date=end_date,
            )

        return start_date + relativedelta(years=50, days=-1)

    @staticmethod
    def license_restrictions(
        category: str,
        max_restrictions: int = 5,
        existing_fields: tp.Optional[tp.Dict] = None,
    ) -> str:
        # We need special checks for f/k/l/n/p/q categories since the
        # restrictions are grouped in one single cell in the table
        fklnpq = "fklnpq"
        categories = get_field_from_any_side(
            existing_fields, "license_categories", ""
        ).split("/")
        if category != fklnpq and category not in categories:
            return ""
        if category == fklnpq and not any([cat in categories for cat in fklnpq]):
            return ""

        # Sources :
        # https://www.gov.uk/driving-licence-codes
        # https://www.thesun.co.uk/motors/4016787/codes-on-your-driving-licence-revealed-fine/
        probabilities = {
            "01": 0.05,
            "02": 0.05,
            "10": 0.01,
            "15": 0.01,
            "20": 0.01,
            "25": 0.01,
            "30": 0.01,
            "31": 0.01,
            "32": 0.01,
            "33": 0.01,
            "35": 0.01,
            "40": 0.05,
            "42": 0.01,
            "43": 0.01,
            "44": 0.01,
            "44(1)": 0.01,
            "44(2)": 0.01,
            "44(3)": 0.01,
            "44(4)": 0.01,
            "44(5)": 0.01,
            "44(6)": 0.01,
            "44(7)": 0.01,
            "44(8)": 0.01,
            "44(11)": 0.01,
            "44(12)": 0.01,
            "45": 0.01,
            "46": 0.01,
            "70": 0.01,
            "71": 0.01,
            "78": 0.01,
            "79": 0.01,
            "79(2)": 0.01,
            "79(3)": 0.01,
            "96": 0.01,
            "97": 0.01,
            "101": 0.05,
            "102": 0.01,
            "103": 0.01,
            "105": 0.05,
            "106": 0.05,
            "107": 0.02,
            "108": 0.01,
            "110": 0.01,
            "111": 0.02,
            "113": 0.01,
            "114": 0.01,
            "115": 0.02,
            "118": 0.01,
            "119": 0.01,
            "121": 0.01,
            "122": 0.02,
            "125": 0.02,
        }

        restrictions = []
        for retriction, probability in probabilities.items():
            if random.random() <= probability:
                restrictions.append(retriction)

        return ",".join(restrictions[:max_restrictions])

    @staticmethod
    def expires_short(
        existing_fields: tp.Optional[tp.Dict] = None,
    ) -> str:
        expires = get_field_from_any_side(existing_fields, "expires", None)
        if not expires:
            return ""

        expires_datetime = dateparser.parse(expires, settings=DATE_PARSER_SETTING)
        if not expires_datetime:
            return ""
        return expires_datetime.strftime("%b%y").upper()
