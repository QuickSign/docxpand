from collections import OrderedDict
import typing as tp

from faker.providers.address.en_GB import Provider as AddressProvider

class Provider(AddressProvider):
    __use_weighting__ = True

    authority_format = OrderedDict(
        (
            ("{{last_name}}, Prefecture Officer of {{city}}shire", 0.2),
            ("{{last_name}}, Civil Status Officer in {{city}}", 0.5),
            ("{{last_name}}, Mayor of {{city}}", 0.1),
            ("{{last_name}}, Ambassador of Leobrit in {{country}}", 0.05),
            ("{{last_name}}, Prime Minister", 0.05),
            ("{{last_name}}, Home Secretary", 0.05),
            ("{{last_name}}, Department of Defense", 0.05)
        )
    )

    def authority(
        self,
        max_length: tp.Optional[int] = None,
    ) -> str:
        if self not in self.generator.providers:
            self.generator.add_provider(self)
        pattern: str = self.random_element(self.authority_format)
        value = self.generator.parse(pattern)
        if max_length is None:
            max_length = 255
        while len(value) > max_length:
            value = self.generator.parse(pattern)
        return value
