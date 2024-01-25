import typing as tp
import random
from collections import OrderedDict

from docxpand.providers.address.fr_FR import Provider as AddressProvider

class Provider(AddressProvider):
    __use_weighting__ = True
    
    authority_format = OrderedDict(
        (
            ("Préfecture de {{city}} ({{department_number}})", 0.70),
            ("Sous-préfecture de {{city}} ({{department_number}})", 0.25),
            ("Ministère de l'intérieur", 0.03),
            ("Ministère des affaires étrangères", 0.02),
        )
    )

    def department_number(self) -> str:
        choices = list(range(1, 96)) + list(range(971, 990))
        return str(random.choice(choices)).zfill(2)

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
