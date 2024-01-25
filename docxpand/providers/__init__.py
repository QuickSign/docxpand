import typing as tp
from collections import OrderedDict
import gettext
import numpy as np
import random

from faker import Faker
import pycountry

from docxpand.instantiable import Instantiable
from docxpand.utils import get_field_from_any_side

GENERIC_FAKER = Faker()


class ChoiceProvider:
    def __init__(self, choices: tp.Union[tp.Dict[str, float], tp.List[str]]) -> None:
        self.choices = choices

    def choice(self) -> str:
        return ChoiceProvider.random_choice(self.choices)

    @staticmethod
    def random_choice(choices: tp.Any) -> tp.Any:
        if isinstance(choices, (list, tuple, set, OrderedDict)):
            return GENERIC_FAKER.random_elements(
                choices, length=1, use_weighting=True
            )[0]
        if isinstance(choices, dict):
            return GENERIC_FAKER.random_elements(
                OrderedDict(choices), length=1, use_weighting=True
            )[0]
        return choices


class CopyProvider:
    @staticmethod
    def copy(
        field_name: str,
        default: tp.Union[str, tp.List[str]],
        existing_fields: tp.Optional[tp.Dict] = None,
    ) -> tp.Any:
        if not existing_fields:
            return default
        return get_field_from_any_side(existing_fields, field_name, default)


class FormatProvider:
    @staticmethod
    def format(
        formatter: str,
        existing_fields: tp.Optional[tp.Dict] = None,
    ) -> tp.Any:
        formatter = formatter.replace("|", "{").replace("&", "}")
        if not existing_fields:
            raise ValueError
        fields = {}
        for v in existing_fields.values():
            fields.update(v)
        return formatter.format(**fields)


class InitialsProvider:
    @staticmethod
    def initials(existing_fields: tp.Optional[tp.Dict] = None) -> str:
        if not existing_fields:
            raise ValueError

        family_name = get_field_from_any_side(existing_fields, "family_name", None)
        given_name = get_field_from_any_side(existing_fields, "given_name", None)
        if family_name and isinstance(family_name, list):
            family_name = family_name[0]
        if not family_name:
            family_name = "?"
        if given_name and isinstance(given_name, list):
            given_name = given_name[0]
        if not given_name:
            given_name = "?"
        return f"{family_name[0]}{given_name[0]}"


class GenderProvider:
    @staticmethod
    def get_gender_letter(gender: tp.Optional[str] = None) -> str:
        if not gender:
            raise ValueError("Gender is needed.")
        first_letter = gender[0].upper()
        return first_letter if first_letter in ["M", "F"] else "U"


class HeightProvider:
    # Source: https://ourworldindata.org/human-height
    stats = {
        "male": (178.4, 7.6),  # mean, std
        "female": (164.7, 7.1)  # mean, std
    }

    @staticmethod
    def height_in_centimeters(gender: str) -> str:
        if gender == "nonbinary":
            gender = random.choice(list(HeightProvider.stats.keys()))
        
        mean, std = HeightProvider.stats[gender]
        return "%d cm" % round(np.random.normal(mean, std))

    @staticmethod
    def height_in_meters(gender: str) -> str:
        if gender == "nonbinary":
            gender = random.choice(list(HeightProvider.stats.keys()))
        
        mean, std = HeightProvider.stats[gender]
        return "%.2f m" % (np.random.normal(mean, std) / 100)


class NationalityProvider:
    @staticmethod
    def nationality_from_locale(locale: str) -> str:
        country = pycountry.countries.get(alpha_2=locale.split("_")[1])
        return country.alpha_3


class ResidencePermitBirthPlaceProvider:
    @staticmethod
    def birth_city(
        locale: str, name_locale: str
    ) -> str:
        address_provider = Instantiable.instantiate(
            {
                "__class__": f"faker.providers.address.{name_locale}.Provider",
                "init_args": {
                    "generator": Faker(name_locale)
                }
            }
        )
        return address_provider.city()
    
    @staticmethod
    def birth_country(
        locale: str, name_locale: str
    ) -> str:
        country_code = name_locale.split("_")[1]
        country = pycountry.countries.get(alpha_2=country_code)

        translator = gettext.translation(
            "iso3166", pycountry.LOCALES_DIR, languages=[locale]
        )
        translator.install()
        return translator.gettext(country.name)