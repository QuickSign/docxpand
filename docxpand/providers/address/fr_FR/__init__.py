import random
import typing as tp
from collections import OrderedDict

from faker.providers.address.fr_FR import Provider as AddressProvider


class Provider(AddressProvider):
    __use_weighting__ = True

    city_suffixes = (
        "ville",
        "bourg",
        "-les-Bains",
        "-sur-Mer",
        "-la-Forêt",
        "boeuf",
        "nec",
        "dan",
    )

    city_prefixes = ("Le", "La", "Saint", "Sainte")

    street_prefixes = OrderedDict(
        (
            ("aire", 0.1),
            ("allée", 0.1),
            ("boulevard", 0.2),
            ("bourg", 0.1),
            ("carrefour", 0.1),
            ("chaussée", 0.1),
            ("chemin", 0.2),
            ("cité", 0.1),
            ("clos", 0.1),
            ("côte", 0.1),
            ("cour", 0.1),
            ("espace", 0.1),
            ("esplanade", 0.1),
            ("faubourg", 0.2),
            ("halle", 0.1),
            ("hameau", 0.1),
            ("impasse", 0.2),
            ("lieu-dit", 0.2),
            ("lotissement", 0.2),
            ("place", 0.2),
            ("promenade", 0.1),
            ("quai", 0.1),
            ("route", 0.2),
            ("ruelle", 0.2),
            ("rue", 1.0),
            ("sentier", 0.1),
            ("square", 0.1),
            ("voie", 0.2),
            ("zone", 0.1),
        )
    )

    building_number_extensions = OrderedDict(
        (
            ("bis", 0.7),
            ("ter", 0.2),
            ("quater", 0.05),
            ("quinquies", 0.05)
        )
    )

    building_number_formats = OrderedDict(
        (
            ("#", 0.2),
            ("##", 0.4),
            ("###", 0.1),
            ("####", 0.05),
            ("# {{building_number_extension}}", 0.2),
            ("## {{building_number_extension}}", 0.05),
        )
    )

    street_address_formats = OrderedDict(
        (
            ("{{building_number}} {{street_name}} ", 0.6),
            ("{{building_number}}, {{street_name}} ", 0.35),
            ("{{street_name}}", 0.05),
        )
    )

    address_formats = OrderedDict(
        (
            ("{{street_address}}\n{{postcode}} {{city}}", 0.8),
            (
                "{{street_address}}\n{{building_name}}\n{{postcode}} {{city}}",
                0.2,
            ),
        )
    )

    building_name_formats = OrderedDict(
        (
            ("Appartement {{building_number}}.", 0.2),
            ("Appt. {{building_number}}.", 0.1),
            ("Bâtiment {{building_number}}", 0.2),
            ("Bâtiment {{city}}", 0.1),
            ("Immeuble {{building_number}}", 0.2),
            ("Immeuble {{city}}", 0.1),
            ("Bâtiment {{city}}, Appt. {{building_number}}", 0.1),
            ("Immeuble {{city}}, Appt. {{building_number}}", 0.1),
            ("Villa {{city}}", 0.1),
            ("Résidence {{city}}", 0.2),
        )
    )


    place_of_birth_format = OrderedDict(
        (
            ("{{city}} ({{department_number}})", 0.95),
            ("{{city}} ({{country}})", 0.05),
        )
    )

    def department_number(self) -> str:
        choices = list(range(1, 96)) + list(range(971, 990))
        return str(random.choice(choices)).zfill(2)

    def place_of_birth(self) -> str:
        if self not in self.generator.providers:
            self.generator.add_provider(self)
        pattern: str = self.random_element(self.place_of_birth_format)
        return self.generator.parse(pattern)

    def building_number_extension(self) -> str:
        return self.random_element(self.building_number_extensions)
    
    def building_number(self) -> str:
        if self not in self.generator.providers:
            self.generator.add_provider(self)
        pattern: str = self.random_element(self.building_number_formats)
        return self.numerify(self.generator.parse(pattern))
    
    def building_name(self) -> str:
        if self not in self.generator.providers:
            self.generator.add_provider(self)
        pattern: str = self.random_element(self.building_name_formats)
        return self.generator.parse(pattern)
    
    def street_address(self) -> str:
        if self not in self.generator.providers:
            self.generator.add_provider(self)
        pattern: str = self.random_element(self.street_address_formats)
        return self.generator.parse(pattern)

    def address(self) -> str:
        if self not in self.generator.providers:
            self.generator.add_provider(self)
        pattern: str = self.random_element(self.address_formats)
        return self.generator.parse(pattern)
