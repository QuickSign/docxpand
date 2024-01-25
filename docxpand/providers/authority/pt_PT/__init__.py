import typing as tp
from collections import OrderedDict

from docxpand.providers.address.pt_PT import Provider as AddressProvider

class Provider(AddressProvider):
    __use_weighting__ = True
    
    authority_format = OrderedDict(
        (
            ("{{city}}*{{administrative_unit}}", 0.8),
            ("{{city}} ({{country}})", 0.1),
            ("Serv. Estr. e Fronteiras", 0.1)
        )
    )

    def authority(
        self,
        max_length: tp.Optional[int] = None,
    ):
        if self not in self.generator.providers:
            self.generator.add_provider(self)
        pattern: str = self.random_element(self.authority_format)

        value = self.generator.parse(pattern)
        if max_length is None:
            max_length = 255
        while len(value) > max_length:
            value = self.generator.parse(pattern)
        
        return value
