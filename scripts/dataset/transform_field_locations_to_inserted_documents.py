"""Script to transform field locations from generated to inserted documents."""
import datetime
import getpass
import logging
import os

import click
import tqdm

from docxpand.dataset import DocFakerDataset
from docxpand.geometry import Quadrangle, BoundingBox, estimate_doc_homography, project_quad_to_target_image


logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "-gd",
    "--generated-dataset",
    "generated_dataset_filename",
    type=click.Path(dir_okay=False, file_okay=True, readable=True),
    required=True,
    help="Path to the dataset with generated SVG documents.",
)
@click.option(
    "-id",
    "--inserted-dataset",
    "inserted_dataset_filename",
    type=click.Path(dir_okay=False, file_okay=True, readable=True),
    required=True,
    help="Path to the dataset with documents inserted on base scenes.",
)
@click.option(
    "-o",
    "--output-directory",
    type=click.Path(dir_okay=True, file_okay=False, writable=True),
    required=True,
    help="Path to output directory where new datasets will be stored.",
)
def transform_field_locations_to_inserted_documents(
    generated_dataset_filename: str,
    inserted_dataset_filename: str,
    output_directory: str,
) -> None:
    """Transform field locations from from generated to inserted documents."""
    documents = []
    generated_dataset = DocFakerDataset(
        dataset_input=generated_dataset_filename,
    )
    inserted_dataset = DocFakerDataset(
        dataset_input=inserted_dataset_filename,
    )
    progress = tqdm.tqdm(inserted_dataset.documents.items())
    progress.set_description("Transforming field coordinates")
    for doc_id, doc_entry in progress:
        annotation = doc_entry["annotations"][0]
        fields = annotation["fields"]
        original_doc_entry = generated_dataset.documents[doc_id]
        original_annotation = original_doc_entry["annotations"][0]
        original_fields = original_annotation["fields"]

        # Find homography from generated doc to inserted doc
        original_quad = Quadrangle.from_dict(original_annotation["position"])
        target_quad = Quadrangle.from_dict(annotation["position"])
        homography = estimate_doc_homography(original_quad, target_quad)

        for side in fields:
            # Only process the right side
            if not doc_id.endswith(side):
                continue
            for field_name, field_value in fields[side].items():
                original_field_value = original_fields[side][field_name]
                original_field_position = original_field_value.get("position")
                field_value["position"] = original_field_position
                if original_field_position:
                    original_bbox = BoundingBox.from_dict(original_field_position)
                    field_quad = project_quad_to_target_image(
                        original_bbox.to_quad(), homography
                    )
                    field_value["position"] = field_quad.to_dict()

        documents.append(doc_entry)

    output_dataset_dict = {
        "__class__": "DocFakerDataset",
        "documents": documents,
        "info": {
            "author": getpass.getuser(),
            "createdAt": datetime.datetime.utcnow().isoformat(),
            "description": inserted_dataset.info().get("description"),
            "name": inserted_dataset.info().get("name")
        }
    }
    output_dataset = DocFakerDataset(output_dataset_dict)
    filename = os.path.join(
        output_directory, os.path.basename(generated_dataset_filename)
    )
    output_dataset.save(filename)

if __name__ == "__main__":
    transform_field_locations_to_inserted_documents()
