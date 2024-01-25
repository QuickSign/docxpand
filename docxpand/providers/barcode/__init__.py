"""Barcode and datamatrix provider."""
import typing as tp

import dateparser
import zxingcpp

from docxpand.image import ColorSpace, Image
from docxpand.normalizer import (
    cut_and_pad_right,
    normalize_name,
)
from docxpand.utils import get_field_from_any_side

BARCODE_MAPPING = {
    "Barcode": zxingcpp.BarcodeFormat.Code128,
    "Datamatrix": zxingcpp.BarcodeFormat.DataMatrix,
}


class Provider:
    """Barcode and datamatrix provider class."""

    def generate_barcode(
        self,
        document_code: str,
        barcode_format_name: str,
        width: int,
        height: int,
        existing_fields: tp.Optional[tp.Dict] = None,
    ) -> Image:
        """Generate a barcode or a datamatrix.

        Args:
            document_code: the doc code
            barcode_format_name: the format of the barcode
            width: width
            height: height
            existing_fields: the other fields of the doc

        Returns:
            barcode as an Image
        """
        if barcode_format_name not in BARCODE_MAPPING.keys():
            raise ValueError("Barcode format is not valid.")
        barcode_format = BARCODE_MAPPING[barcode_format_name]
        cut_document_code = cut_and_pad_right(document_code, 2)
        nationality = cut_and_pad_right(
            get_field_from_any_side(existing_fields, "nationality", "UTO"), 3
        )
        family_name = normalize_name(
            get_field_from_any_side(existing_fields, "family_name", "SAMPLE")
        )

        given_name = normalize_name(
            get_field_from_any_side(existing_fields, "given_name", "SAMPLE")[0]
        )

        birth_date = dateparser.parse(
            get_field_from_any_side(existing_fields, "birth_date", "01.01.1970")
        ).strftime("%Y%m%d")
        document_number = get_field_from_any_side(
            existing_fields, "document_number", "123456789"
        )
        generated_barcode = zxingcpp.write_barcode(
            barcode_format,
            "/".join(
                [
                    cut_document_code,
                    nationality,
                    family_name,
                    given_name,
                    birth_date,
                    document_number,
                ]
                if barcode_format_name == "Datamatrix"
                else [document_number]
            ),
            width,
            height,
        )

        return Image(generated_barcode, space=ColorSpace.GRAYSCALE)
