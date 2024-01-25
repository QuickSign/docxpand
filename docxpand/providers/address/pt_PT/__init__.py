from collections import OrderedDict
import typing as tp

from faker.providers.address.pt_PT import Provider as AddressProvider


class Provider(AddressProvider):
    __use_weighting__ = True

    city_formats = OrderedDict(
        (
            ("{{first_name}}", 0.1),
            ("{{last_name}}", 0.5),
            ("{{city_prefix}} {{first_name}}", 0.05),
            ("{{city_prefix}} {{last_name}}", 0.05),
            ("{{last_name}} de {{last_name}}", 0.1),
            ("{{last_name}} do {{last_name}}", 0.1),
            ("{{city_prefix}} {{last_name}} de {{last_name}}", 0.05),
            ("{{city_prefix}} {{last_name}} do {{last_name}}", 0.05),
        )
    )

    city_prefixes = [
        "Santa",
        "Vila",
        "São"
    ]

    distritos = (
        "Binaurèm",
        "Bregoniá",
        "Carçalèm",
        "Castelo Bianca",
        "Colação",
        "Émiria",
        "Folacia",
        "Grandiá",
        "Lesboám",
        "Mereu",
        "Nolita",
        "Portalèm",
        "Ribeiro",
        "Santa Gaía",
        "Vila Francica",
    )

    place_of_birth_format = OrderedDict(
        (
            ("{{city}}*{{administrative_unit}}", 0.9),
            ("{{city}} ({{country}})", 0.05),
            ("{{country}}", 0.05),
        )
    )

    def city_prefix(self) -> str:
        return self.random_element(self.city_prefixes)

    def city_name(self) -> str:
        if self not in self.generator.providers:
            self.generator.add_provider(self)
        pattern: str = self.random_element(self.city_formats)
        return self.generator.parse(pattern)

    city = city_name

    def place_of_birth(self) -> str:
        if self not in self.generator.providers:
            self.generator.add_provider(self)
        pattern: str = self.random_element(self.place_of_birth_format)
        return self.generator.parse(pattern)
