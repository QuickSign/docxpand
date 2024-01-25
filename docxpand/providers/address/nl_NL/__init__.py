from collections import OrderedDict
import typing as tp

from faker.providers.address.nl_NL import Provider as AddressProvider


class Provider(AddressProvider):
    __use_weighting__ = True

    city_formats = OrderedDict(
        (
            ("{{first_name}}", 0.1),
            ("{{last_name}}", 0.6),
            ("{{city_prefix}} {{first_name}}", 0.05),
            ("{{city_prefix}} {{last_name}}", 0.1),
            ("{{city_prefix}}{{first_name}}", 0.05),
            ("{{city_prefix}}{{last_name}}", 0.1),
            ("{{city_prefix}}-{{first_name}}", 0.05),
            ("{{city_prefix}}-{{last_name}}", 0.1),

        )
    )

    city_prefixes = [
        "'s",
        "'t",
        "De",
        "Den",
        "Nieuw",
        "Oost",
        "Noord",
        "Oud",
        "Sint",
        "Ten",
        "Ter",
        "West",
        "Zuid",
    ]

    building_number_extensions = OrderedDict(
        (
            ("A", 0.5),
            ("B", 0.2),
            ("C", 0.1),
            ("½", 0.1),
            ("¼", 0.05),
            ("¾", 0.05),
        )
    )

    building_number_formats = OrderedDict(
        (
            ("#", 0.2),
            ("##", 0.4),
            ("###", 0.1),
            ("####", 0.05),
            ("#/#", 0.1),
            ("##/#", 0.05),
            ("#{{building_number_extension}}", 0.05),
            ("##{{building_number_extension}}", 0.05),
        )
    )

    street_address_formats = OrderedDict(
        (
            ("{{building_number}} {{street_name}}", 0.95),
            ("{{street_name}}", 0.05),
        )
    )

    address_formats = OrderedDict(
        (
            ("{{postcode}} {{city}}\n{{street_address}}", 0.7),
            (
                "{{postcode}} {{city}}\n{{building_name}}\n{{street_address}}",
                0.2,
            ),
        )
    )

    building_name_formats = OrderedDict(
        (
            ("Gebouw {{building_number}}", 0.4),
            ("Gebouw {{city}}", 0.4),
            ("Huis {{building_number}}", 0.2),
            ("Appartement {{building_number}}", 0.2),
        )
    )

    provinces = (
        "Bakkermol",
        "Culemtrop",
        "Dekkerstal",
        "Fietslie",
        "Gemertland",
        "Martrijk",
        "Noord-Bremdal",
        "Prontijse",
        "Ugodeek",
        "Zeemania",
        "Zuid-Bremdal",
    )

    place_of_birth_format = OrderedDict(
        (
            ("{{city}} ({{administrative_unit}})", 0.9),
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
        return self.generator.parse(pattern).title()

    city = city_name

    def administrative_unit(self) -> str:
        return self.random_element(self.provinces)

    province = administrative_unit

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

    def place_of_birth(self) -> str:
        if self not in self.generator.providers:
            self.generator.add_provider(self)
        pattern: str = self.random_element(self.place_of_birth_format)
        return self.generator.parse(pattern)


