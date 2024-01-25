from collections import OrderedDict

from faker.providers.person.es_ES import Provider as PersonProvider


class Provider(PersonProvider):
    __use_weighting__ = True

    parents_names_format = OrderedDict(
        (
            ("{{first_name_male}} / {{first_name_female}}", 0.9),
            ("{{first_name_male}} / NC", 0.04),
            ("NC / {{first_name_female}}", 0.04),
            ("NC", 0.02),
        )
    )

    def parents_names(self) -> str:
        if self not in self.generator.providers:
            self.generator.add_provider(self)
        pattern: str = self.random_element(self.parents_names_format)
        return self.generator.parse(pattern)
