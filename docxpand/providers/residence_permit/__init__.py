import typing as tp

from docxpand.providers import ChoiceProvider
from docxpand.translations.residence_permit import (
    RESIDENCE_PERMIT_OBSERVATIONS,
    RESIDENCE_PERMIT_TYPES_TRANSLATIONS,
    RESIDENCE_PERMIT_WORK_OBSERVATIONS,
)
from docxpand.utils import get_field_from_any_side


class Provider(ChoiceProvider):
    def generate_permit_type(
            self, locale: str, multiline: bool = True
        ) -> tp.Union[str, tp.List[str]]:
        permit_type_as_lines: tp.List[str] = (
            RESIDENCE_PERMIT_TYPES_TRANSLATIONS[self.choice()][locale]
        )
        return_val = (
            permit_type_as_lines
            if multiline
            else " ".join(permit_type_as_lines)
        )
        return return_val

    def generate_observations(self, locale: str):
        return RESIDENCE_PERMIT_OBSERVATIONS[self.choice()][locale]

    def generate_observations_multilines(self, locale, existing_fields):
        observations = [
            get_field_from_any_side(existing_fields, "observations", "")
        ]
        observations.extend(
            RESIDENCE_PERMIT_WORK_OBSERVATIONS[self.choice()][locale]
        )
        return observations
