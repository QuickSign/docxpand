"""Script to extract image fields (photo, datamatrix, barcodes) from SVGs."""
import datetime
import getpass
import logging
import os

import click
import tqdm

from docxpand.canvas import Canvas, XLINK_NS
from docxpand.dataset import DocFakerDataset
from docxpand.image import Image
from docxpand.utils import guess_mimetype

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "-dd",
    "--document-dataset",
    type=click.Path(dir_okay=False, file_okay=True, readable=True),
    required=True,
    help="Path to the dataset with generated SVG documents.",
)
@click.option(
    "-di",
    "--document-images",
    type=click.Path(dir_okay=True, file_okay=True, readable=True),
    required=True,
    help="Path to the directory containing documents dataset images.",
)
@click.option(
    "-o",
    "--output-directory",
    type=click.Path(dir_okay=True, file_okay=False, writable=True),
    required=True,
    help="Path to output directory where extracted images will be stored.",
)
def extract_image_fields_from_svgs(
    document_dataset: str,
    document_images: str,
    output_directory: str,
) -> None:
    """Extract image fields (photo, datamatrix, barcodes) from SVGs."""
    documents = []
    input_dataset = DocFakerDataset(
        dataset_input=document_dataset,
        images_dir=document_images
    )
    progress = tqdm.tqdm(input_dataset.documents.items())
    progress.set_description("Extracting image fields from SVGs")
    for doc_id, doc_entry in progress:
        filename = os.path.join(document_images, doc_entry["filename"])
        basename, _ = os.path.splitext(doc_entry["filename"])
        basename = "-".join(basename.split("-")[:-1])  # remove side
        if guess_mimetype(filename) != 'image/svg+xml':
            raise RuntimeError(
                "Cannot extract image fields from non-SVG images."
            )
        canvas = Canvas(filename)
        fields = doc_entry["annotations"][0]["fields"]
        href_key = f"{{{XLINK_NS}}}href"
        factors = {  # resize factor to reduce output size
            "barcode": 1.0,
            "datamatrix": 0.25,
            "ghost": 0.5,
            "photo": 0.5,
            "default": 0.5
        }
        formats = {  # use "png" for barcodes and ghosts to reduce output size
            "barcode": "png",
            "datamatrix": "png",
            "ghost": "png",
            "photo": "jpg",
            "default": "jpg"
        }
        for side in fields:
            for field_name, field_value in fields[side].items():
                if (
                    isinstance(field_value, str) and
                    "Image object" in field_value
                ):
                    format = formats.get(field_name.lower(), formats["default"])
                    image_filename = f"{basename}-{side}-{field_name}.{format}"
                    fields[side][field_name] = {
                        "type": "image",
                        "filename": image_filename
                    }

                    if doc_id.endswith(side):  # don't do it on wrong side
                        # Load image from base64 encoded string in SVG
                        image_element = canvas.element_by_id(f"{field_name}_image")
                        encoded = image_element.attrib[href_key]
                        field_image = Image.base64decode(encoded)

                        # Resize and select format to optimize weight
                        factor = factors.get(field_name.lower(), factors["default"])
                        height, width = map(
                            lambda x: int(x*factor), field_image.shape[:2]
                        )
                        field_image = field_image.resize(height, width)

                        # Save image
                        field_image.write(os.path.join(
                            output_directory, image_filename
                        ))
                else:
                    fields[side][field_name] = {
                        "type": "text",
                        "value": field_value
                    }

        documents.append(doc_entry)

    output_dataset_dict = {
        "__class__": "DocFakerDataset",
        "documents": documents,
        "info": {
            "author": getpass.getuser(),
            "createdAt": datetime.datetime.utcnow().isoformat(),
            "description": input_dataset.info().get("description"),
            "name": input_dataset.info().get("name")
        }
    }
    output_dataset = DocFakerDataset(output_dataset_dict)
    filename = os.path.join(output_directory, os.path.basename(document_dataset))
    output_dataset.save(filename)

if __name__ == "__main__":
    extract_image_fields_from_svgs()
