import typing as tp

import dateparser

from docxpand.normalizer import (
    cut_and_pad_right,
    normalize_name,
)
from docxpand.utils import get_field_from_any_side


class Provider:
    filler: str = "<"

    @staticmethod
    def checksum(string: str) -> str:
        """Checksum of a string in a MRZ.

        Code inspired from section "Clés de contrôle" in
        http://fr.wikipedia.org/wiki/Carte_nationale_d%27identit%C3%A9_en_France

        Args:
            s: string to check

        Returns:
            checksum value for string s
        """
        checker = 0
        weights = [7, 3, 1]
        for position, char in enumerate(string):
            weight = weights[position % 3]
            if char == "<":
                val = 0
            elif char.isdigit():
                val = int(char)
            else:
                val = ord(char) - 55
            checker += val * weight
        return str(checker % 10)

    def td1(
        self,
        document_code: str,
        gender: str,
        existing_fields: tp.Optional[tp.Dict] = None,
    ) -> tp.List[str]:
        """Generate a TD1 MRZ.

        See Also:
            ICAO Doc 9303 Part 5, paragraph 4.2.2
        """
        line_length = 30

        # Line 1
        document_code = cut_and_pad_right(document_code, 2, self.filler)
        nationality = cut_and_pad_right(
            get_field_from_any_side(existing_fields, "nationality", "UTO"),
            3,
            self.filler,
        )
        document_number = get_field_from_any_side(
            existing_fields, "document_number", "123456789"
        )
        document_number_check_digit = self.checksum(document_number)
        if len(document_number) <= 9:
            document_number += document_number_check_digit
        else:  # long document number (see paragraph 4.2.4)
            document_number = (
                document_number[:9]
                + self.filler
                + document_number[9:]
                + document_number_check_digit
            )
        line_1 = document_code + nationality + document_number
        line_1 = cut_and_pad_right(line_1, line_length, self.filler)

        # Line 2
        birth_date = dateparser.parse(
            get_field_from_any_side(existing_fields, "birth_date", "01.01.1970")
        ).strftime("%y%m%d")
        sex = {"male": "M", "female": "F", "nonbinary": self.filler}[gender]
        expires = dateparser.parse(
            get_field_from_any_side(existing_fields, "expires", "31.12.2030")
        ).strftime("%y%m%d")
        line_2 = (
            birth_date
            + self.checksum(birth_date)
            + sex
            + expires
            + self.checksum(expires)
            + nationality
        )
        line_2 = cut_and_pad_right(line_2, line_length - 1, self.filler)
        composite_check_digit = self.checksum(
            line_1[5:] + line_2[0:7] + line_2[8:15] + line_2[18:29]
        )
        line_2 += composite_check_digit

        # Line 3
        family_name = get_field_from_any_side(existing_fields, "family_name", "SAMPLE")
        if isinstance(family_name, list):
            family_name = ", ".join(family_name)
        family_name = normalize_name(family_name, self.filler)
        given_name = get_field_from_any_side(existing_fields, "given_name", "SAMPLE")
        if isinstance(given_name, list):
            given_name = ", ".join(given_name)
        given_name = normalize_name(given_name, self.filler)
        line_3 = family_name + self.filler * 2 + given_name
        line_3 = cut_and_pad_right(line_3, line_length, self.filler)

        return [line_1, line_2, line_3]

    def td2(
        self,
        document_code: str,
        gender: str,
        existing_fields: tp.Optional[tp.Dict] = None,
    ) -> tp.List[str]:
        """Generate a TD2 MRZ.

        See Also:
            ICAO Doc 9303 Part 5, paragraph 4.2.2
        """
        line_length = 36

        document_code = cut_and_pad_right(document_code, 2, self.filler)
        nationality = cut_and_pad_right(
            get_field_from_any_side(existing_fields, "nationality", "UTO"),
            3,
            self.filler,
        )
        document_number = get_field_from_any_side(
            existing_fields, "document_number", "123456789"
        )
        birth_date = dateparser.parse(
            get_field_from_any_side(existing_fields, "birth_date", "01.01.1970")
        ).strftime("%y%m%d")
        sex = {"male": "M", "female": "F", "nonbinary": self.filler}[gender]
        expires = dateparser.parse(
            get_field_from_any_side(existing_fields, "expires", "31.12.2030")
        ).strftime("%y%m%d")
        family_name = get_field_from_any_side(existing_fields, "family_name", "SAMPLE")
        if isinstance(family_name, list):
            family_name = ", ".join(family_name)
        family_name = normalize_name(family_name, self.filler)
        given_name = get_field_from_any_side(existing_fields, "given_name", "SAMPLE")
        if isinstance(given_name, list):
            given_name = ", ".join(given_name)
        given_name = normalize_name(given_name, self.filler)

        # line_1
        line_1 = (
            document_code + nationality + family_name + self.filler * 2 + given_name
        )
        line_1 = cut_and_pad_right(line_1, line_length, self.filler)
        # line_2
        line_2 = (
            document_number
            + self.checksum(document_number)
            + nationality
            + birth_date
            + self.checksum(birth_date)
            + sex
            + expires
            + self.checksum(expires)
        )
        line_2 = cut_and_pad_right(line_2, line_length - 1, self.filler)
        line_2 += self.checksum(
            line_2[0:10] + line_2[13:20] + line_2[21:35],
        )

        return [line_1, line_2]

    def td3(
        self,
        document_code: str,
        gender: str,
        existing_fields: tp.Optional[tp.Dict] = None,
    ) -> tp.List[str]:
        """Generate a TD3 MRZ.

        See Also:
            ICAO Doc 9303 Part 5, paragraph 4.2.2
        """
        line_length = 44

        document_code = cut_and_pad_right(document_code, 2, self.filler)
        nationality = cut_and_pad_right(
            get_field_from_any_side(existing_fields, "nationality", "UTO"),
            3,
            self.filler,
        )
        document_number = get_field_from_any_side(
            existing_fields, "document_number", "123456789"
        )
        birth_date = dateparser.parse(
            get_field_from_any_side(existing_fields, "birth_date", "01.01.1970")
        ).strftime("%y%m%d")
        sex = {"male": "M", "female": "F", "nonbinary": self.filler}[gender]
        expires = dateparser.parse(
            get_field_from_any_side(existing_fields, "expires", "31.12.2030")
        ).strftime("%y%m%d")
        family_name = get_field_from_any_side(existing_fields, "family_name", "SAMPLE")
        if isinstance(family_name, list):
            family_name = ", ".join(family_name)
        family_name = normalize_name(family_name, self.filler)
        given_name = get_field_from_any_side(existing_fields, "given_name", "SAMPLE")
        if isinstance(given_name, list):
            given_name = ", ".join(given_name)
        given_name = normalize_name(given_name, self.filler)

        # line_1
        line_1 = (
            document_code + nationality + family_name + self.filler * 2 + given_name
        )
        line_1 = cut_and_pad_right(line_1, line_length, self.filler)
        # line_2
        line_2 = (
            document_number
            + self.checksum(document_number)
            + nationality
            + birth_date
            + self.checksum(birth_date)
            + sex
            + expires
            + self.checksum(expires)
        )
        line_2 = cut_and_pad_right(line_2, line_length - 1, self.filler)
        line_2 += self.checksum(line_2[0:10] + line_2[13:20] + line_2[21:44])

        return [line_1, line_2]
