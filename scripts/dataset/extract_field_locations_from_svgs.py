"""Script to extract field locations from SVGs."""
import datetime
import getpass
import logging
import os

import click
import tqdm

from docxpand.dataset import DocFakerDataset
from docxpand.svg_to_image import ChromeSVGRenderer
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
    help="Path to output directory where new datasets will be stored.",
)
def extract_fields_locations_from_svgs(
    document_dataset: str,
    document_images: str,
    output_directory: str,
) -> None:
    """Extract fields locations from SVGs."""
    documents = []
    renderer = ChromeSVGRenderer()
    input_dataset = DocFakerDataset(
        dataset_input=document_dataset,
        images_dir=document_images
    )
    progress = tqdm.tqdm(input_dataset.documents.items())
    progress.set_description("Extracting field locations from SVGs")
    for doc_id, doc_entry in progress:
        filename = os.path.join(document_images, doc_entry["filename"])
        if guess_mimetype(filename) != 'image/svg+xml':
            raise RuntimeError(
                "Cannot extract field locations from non-SVG images."
            )
        fields = doc_entry["annotations"][0]["fields"]
        for side in fields:
            # Only process the right side
            if not doc_id.endswith(side):
                continue
            field_names_and_multiline = {
                field_name:
                (
                    (
                        f"{field_name}_field"
                        if field_value.get("type") == "text"
                        else f"{field_name}_image"
                    ),
                    isinstance(field_value.get("value"), list)
                )
                for field_name, field_value in fields[side].items()
            }
            positions = renderer.get_coordinates(
                filename,
                element_ids=list(field_names_and_multiline.values())
            )
            for field_name in field_names_and_multiline:
                element_id = field_names_and_multiline[field_name][0]
                position = positions[element_id]
                fields[side][field_name]["position"] = (
                    position.to_dict() if position else None
                )

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
    extract_fields_locations_from_svgs()
