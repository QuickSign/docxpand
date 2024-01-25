import datetime
import os
import typing as tp
import uuid

import numpy as np
from faker import Faker

from docxpand.canvas import SVG_NS, XLINK_NS, Canvas
from docxpand.image import Image
from docxpand.instantiable import CallableInstantiable
from docxpand.providers import GENERIC_FAKER, ChoiceProvider
from docxpand.svg_to_image import SVGRenderer
from docxpand.template import (
    TEMPLATES_DIR,
    DocumentTemplate,
    Field,
    FieldType,
)
from docxpand.translations.labels import LABELS_TRANSLATION


class Generator:
    def __init__(
        self,
        template: tp.Union[str, DocumentTemplate],
        renderer: tp.Optional[SVGRenderer],
        photo_url_request: str = "",
    ) -> None:
        self.photo_url_request = photo_url_request
        self.template = (
            template
            if isinstance(template, DocumentTemplate)
            else DocumentTemplate.load(template)
        )
        self.renderer = renderer

    def generate_name(
        self,
        field: Field,
        faker: Faker,
        context: tp.Dict,
    ) -> tp.Union[str, tp.List[str]]:
        nb_parts = int(ChoiceProvider.random_choice(field.parts)) if field.parts else 1
        separator = field.separator or " "
        nb_lines = field.lines or 1
        max_chars_per_line = field.max_chars_per_line or 36
        method = CallableInstantiable.get_methods(
            field.provider, generator=faker, **context
        )
        generated_lines = self.generate_multi_line_multi_part(
            method, nb_parts, separator, nb_lines, max_chars_per_line
        )
        while not generated_lines:
            generated_lines = self.generate_multi_line_multi_part(
                method, nb_parts, separator, nb_lines, max_chars_per_line
            )
        if nb_lines == 1:
            return generated_lines[0]
        return generated_lines

    def generate_multi_line_multi_part(
        self,
        method: tp.Callable,
        nb_parts: int,
        separator: str,
        nb_lines: int,
        max_chars_per_line: int,
    ) -> tp.List[str]:
        parts = [method() for _ in range(nb_parts)]
        if nb_lines < 1:
            raise ValueError(
                f"Cannot generate a field on {nb_lines} line, need at least 1."
            )
        complete_value = separator.join(parts)
        if nb_lines == 1:
            return [complete_value[:max_chars_per_line]]
        lines = []
        for _ in range(nb_lines):
            partial_value = None
            for selected in range(len(parts)):
                candidate = separator.join(parts[: selected + 1]) + separator
                if len(candidate) > max_chars_per_line:
                    break
                partial_value = candidate
            if partial_value:
                lines.append(partial_value.strip())
            parts = parts[selected + 1 :]
            if not parts:
                break

        if lines:
            lines[-1] = lines[-1].strip(separator)
        return lines

    def generate_address(
        self,
        field: Field,
        faker: Faker,
        context: tp.Dict,
    ) -> tp.List[str]:
        separator = field.separator or "\n"
        nb_lines = field.lines or 4
        address_values = CallableInstantiable.call(
            field.provider, generator=faker, **context
        )
        if field.format:
            address_values = field.format.format(**address_values)
        address_lines = address_values.split(separator)
        return address_lines[:nb_lines]

    def generate_date(
        self,
        field: Field,
        faker: Faker,
        existing_fields: tp.Dict,
        context: tp.Dict,
    ) -> str:
        date_obj = CallableInstantiable.call(
            field.provider,
            generator=faker,
            existing_fields=existing_fields,
            **context,
        )
        if date_obj is not None:
            return date_obj.strftime(field.format)
        if field.default is not None:
            return field.default
        return ""

    def generate_text(
        self,
        field: Field,
        faker: Faker,
        existing_fields: tp.Dict,
        context: tp.Dict,
    ) -> str:
        values = CallableInstantiable.call(
            field.provider,
            generator=faker,
            existing_fields=existing_fields,
            **context,
        )
        if field.format:
            values = field.format.format(**values)
        return values

    def generate_photo(
        self,
        field: Field,
        existing_fields: tp.Dict,
        context: tp.Dict,
    ) -> np.ndarray:
        context_copy = context.copy()
        context_copy["url"] = self.photo_url_request
        return CallableInstantiable.call(
            field.provider, existing_fields=existing_fields, **context_copy
        )

    def generate_mrz(
        self,
        field: Field,
        existing_fields: tp.Dict,
        context: tp.Dict,
    ) -> tp.List[str]:
        return CallableInstantiable.call(
            field.provider,
            existing_fields=existing_fields,
            **context,
        )

    def generate_data(
        self,
    ) -> tp.Tuple[tp.Dict[str, tp.Dict[str, tp.Any]], tp.Dict[str, tp.Any]]:
        """Generate random data from providers.

        Returns:
            tuple containing generated fields and context
        """
        # Generating context
        context = {}
        if self.template.context:
            for key, value in self.template.context.items():
                context[key] = ChoiceProvider.random_choice(value)

        # Initialize generated data
        data = {}

        # Iterate on sides
        for side in self.template.sides:
            data[side] = {}

            # Iterate on fields
            for field in self.template.sides[side].fields:
                if field.type == FieldType.NAME and "name_locale" in context:
                    faker = Faker(context["name_locale"])
                elif "locale" in context:
                    faker = Faker(context["locale"])
                else:
                    faker = GENERIC_FAKER

                values = None

                # Check if field should be generated or not
                if field.conditional is not None:
                    if not CallableInstantiable.call(
                        field.conditional, **context
                    ):
                        data[side][field.name] = None
                        continue

                # Generate field value according to type
                if field.type == FieldType.NAME:
                    values = self.generate_name(field, faker, context)
                elif field.type == FieldType.DATE:
                    values = self.generate_date(field, faker, data, context)
                elif field.type == FieldType.ADDRESS:
                    values = self.generate_address(field, faker, context)
                elif field.type == FieldType.TEXT:
                    values = self.generate_text(field, faker, data, context)
                elif field.type == FieldType.PHOTO:
                    values = self.generate_photo(field, data, context)
                elif field.type == FieldType.MRZ:
                    values = self.generate_mrz(field, data, context)
                else:
                    raise RuntimeError(
                        f"Field type {field.type} not currently supported"
                    )
                data[side][field.name] = values

        return data, context

    def fill_text_field(
        self,
        canvas: Canvas,
        field_name: str,
        field_values: tp.Union[str, tp.List[str]],
        line_idx: tp.Optional[int] = None,
        element_type="field",
    ) -> None:
        element_id = f"{field_name}_{element_type}"
        if line_idx is not None:
            element_id = f"{element_id}_{line_idx + 1}"
        text_element = canvas.element_by_id(element_id)
        if text_element is None or text_element.tag != f"{{{SVG_NS}}}text":
            print(f"Cannot get text element from id {element_id}, ignoring.")
            return
        tspan = text_element[0]
        if tspan.tag != f"{{{SVG_NS}}}tspan":
            raise RuntimeError(
                "Cannot get tspan from text element with id " f"{element_id}"
            )
        if line_idx is not None:
            if line_idx < len(field_values):
                tspan.text = field_values[line_idx]
            else:
                tspan.text = ""
        else:
            tspan.text = field_values if field_values else ""

    def fill_image_field(
        self,
        canvas: Canvas,
        field_name: str,
        field_values: Image,
        format: str = "png",
    ) -> None:
        element_id = f"{field_name}_image"
        image_element = canvas.element_by_id(element_id)
        if image_element is None:
            print(f"Cannot get image element from id {element_id}, ignoring.")
            return
        href_key = f"{{{XLINK_NS}}}href"
        image_element.attrib[href_key] = field_values.base64encode(format)

    def generate_images(
        self,
        output_directory: str,
    ) -> tp.List[tp.Dict]:
        """Generate images using random data generators.

        Args:
            output_directory: directory where images are stored

        Returns:
            list of output files
        """
        generated_fields, context = self.generate_data()
        output_fields = {}
        document_id = str(uuid.uuid4())
        locale = context.get("locale")


        # Resize factors and formats optimized to reduce image fields output size
        factors = {
            "barcode": 1.0,
            "datamatrix": 0.25,
            "ghost": 0.5,
            "photo": 0.5,
            "default": 0.5
        }
        formats = {
            "barcode": "png",
            "datamatrix": "png",
            "ghost": "png",
            "photo": "jpg",
            "default": "jpg"
        }

        # Iterate on sides
        output_filenames = []
        entries = []
        for side_name in self.template.sides:
            output_fields[side_name] = {}
            # Get SVG template
            side = self.template.sides[side_name]
            filename = os.path.join(
                TEMPLATES_DIR,
                os.path.dirname(self.template.filename),
                side.template,
            )
            canvas = Canvas(filename)

            for label_name in side.translatable_labels:
                label_translation = LABELS_TRANSLATION.get(
                    label_name, {}
                ).get(locale, None)
                if label_translation:
                    self.fill_text_field(
                        canvas,
                        label_name,
                        label_translation,
                        element_type="label",
                    )
            for field_name in generated_fields[side_name]:
                # Get element
                field = side.get_field(field_name)
                field_values = generated_fields[side_name][field_name]

                # Case of text fields
                if field.type in [
                    FieldType.ADDRESS,
                    FieldType.DATE,
                    FieldType.MRZ,
                    FieldType.NAME,
                    FieldType.TEXT,
                ]:
                    if field.lines and field.lines > 1:
                        for line_idx in range(field.lines):
                            self.fill_text_field(
                                canvas, field_name, field_values, line_idx
                            )
                    else:
                        self.fill_text_field(canvas, field_name, field_values)
                    output_fields[side_name][field_name] = {
                        "type": "text",
                        "value": field_values
                    }

                # Case of image fields
                elif field.type in [
                    FieldType.PHOTO,
                ]:
                    self.fill_image_field(canvas, field_name, field_values)
                    format = formats.get(field_name.lower(), formats["default"])
                    factor = factors.get(field_name.lower(), factors["default"])
                    height, width = map(
                        lambda x: int(x*factor), field_values.shape[:2]
                    )
                    image_filename = (
                        f"{document_id}-{self.template.name}-{side_name}-"
                        f"{field_name}.{format}"
                    )
                    field_image = field_values.resize(height, width)
                    field_image.write(os.path.join(
                        output_directory, image_filename
                    ))
                    output_fields[side_name][field_name] = {
                        "type": "image",
                        "filename": image_filename
                    }
                else:
                    raise RuntimeError(
                        f"Field type {field.type} not currently supported"
                    )

            output_filename = os.path.join(
                output_directory,
                f"{document_id}-{self.template.name}-{side_name}.svg",
            )
            output_filename = os.path.join(
                output_directory,
                f"{document_id}-{self.template.name}-{side_name}.svg",
            )
            canvas.render(output_filename, True)
            if self.renderer:
                png_output = output_filename.replace(".svg", ".png")
                img = self.renderer.render(output_filename)
                img.write(png_output)
                os.remove(output_filename)
                output_filename = png_output
            output_filenames.append(output_filename)
            creation_date = datetime.datetime.utcnow().isoformat()
            entries.append(
                {
                    "_id": f"{document_id}-{side_name}",
                    "annotations": [
                        {
                            "_id": 0,
                            "annotator": "automatic",
                            "created_at": creation_date,
                            "fields": output_fields,
                            "position": {
                                "p1": {"x": 0.0, "y": 0.0},
                                "p2": {"x": 1.0, "y": 0.0},
                                "p3": {"x": 1.0, "y": 1.0},
                                "p4": {"x": 0.0, "y": 1.0},
                            },
                            "template": f"{self.template.name}-{side_name}",
                            "updated_at": creation_date,
                        }
                    ],
                    "filename": os.path.basename(output_filename),
                }
            )
        return entries
