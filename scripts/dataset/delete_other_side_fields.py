"""Script to delete fields from other side."""
import datetime
import getpass
import logging
import os

import click
import tqdm

from docxpand.dataset import DocFakerDataset


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
    "-o",
    "--output-directory",
    type=click.Path(dir_okay=True, file_okay=False, writable=True),
    required=True,
    help="Path to output directory where generated photos will be stored.",
)
def delete_other_side_fields(
    document_dataset: str,
    output_directory: str,
) -> None:
    """Delete fields from other side."""
    documents = []
    input_dataset = DocFakerDataset(
        dataset_input=document_dataset,
    )
    progress = tqdm.tqdm(input_dataset.documents.items())
    progress.set_description("Deleting other fields from annotations")
    for doc_id, doc_entry in progress:
        fields = doc_entry["annotations"][0]["fields"]
        for side in list(fields.keys()):
            # Only process the right side
            if not doc_id.endswith(side):
                del fields[side]
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
    delete_other_side_fields()
