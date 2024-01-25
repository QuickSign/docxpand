import re
import typing as tp
from collections import OrderedDict

from docxpand.providers import ChoiceProvider
from docxpand.utils import get_field_from_any_side


class Provider:
    signature_formats = OrderedDict(
        (
            ("{family_name}", 1.0),

            ("{family_name} {given_name:1.1}.", 0.1),
            ("{given_name:1.1}. {family_name}", 0.1),
            ("{given_name:1.1}.{family_name}", 0.1),
            ("{given_name:1.1} {family_name}", 0.1),

            ("{given_name:1.1}{family_name:.1}", 0.1),
            ("{given_name:1.1}.{family_name:.1}.", 0.1),
            ("{given_name:1.1} {family_name:.1}", 0.1),
            ("{given_name:1.1}. {family_name:.1}.", 0.1),

            ("{family_name:1.1}{given_name:1.1}", 0.1),
            ("{family_name:1.1}.{given_name:1.1}.", 0.1),
            ("{family_name:1.1} {given_name:1.1}", 0.1),
            ("{family_name:1.1}. {given_name:1.1}.", 0.1),
        )
    )

    def signature(self, existing_fields: tp.Dict) -> str:
        pattern: str = ChoiceProvider.random_choice(self.signature_formats)
        arguments = {}
        if "family_name" in pattern:
            name = existing_fields["front"]["family_name"]
            if isinstance(name, list):
                name = name[0]
            if "given_name" in pattern and ("-" in name or " " in name):
                separator = "-" if "-" in name else " "
                arguments["family_name"] = (
                    name[0] + separator + name.split(separator)[1][0]
                )
            else:
                arguments["family_name"] = name

        if "given_name" in pattern:
            arguments["given_name"] = existing_fields["front"]["given_name"]
            if isinstance(arguments["given_name"], list):
                arguments["given_name"] = arguments["given_name"][0]
        
        return pattern.format(**arguments)

    def signature_knowing_key(self, existing_fields: tp.Dict, key: str) -> str:
        field = get_field_from_any_side(existing_fields, key, None)

        # Particular case of Leobrit (Name, ...)
        if "," in field:
            field = field.split(",")[0]

        # Particular case of "Préfecture de ..." / "Sous-préfecture de ..."
        for prefix in ["Préfecture de", "Sous-préfecture de"]:
            if prefix in field:
                field = field.replace(prefix, "")
                # Remove departement number from: {city} ({department_number})
                field = re.sub("[\(\[].*?[\)\]]", "", field).strip()
                break

        if not field:
            raise ValueError(f"{key} doesn't exist in existing_fields")

        return field
