import datetime
import getpass
import logging
import typing as tp

import click
from docxpand.dataset import DocFakerDataset

from docxpand.generator import Generator
from docxpand.svg_to_image import ChromeSVGRenderer

logger = logging.getLogger(__name__)
import os


@click.command()
@click.option(
    "-t",
    "--template",
    type=click.Path(dir_okay=True, file_okay=True, readable=True),
    required=True,
    help="Name of input template directory (containing SVG and JSON files).",
)
@click.option(
    "-n",
    "--number",
    type=int,
    required=False,
    default=1,
    help="Number of documents to generate.",
)
@click.option(
    "-o",
    "--output-directory",
    type=click.Path(dir_okay=True, file_okay=False, writable=True),
    required=True,
    help="Path to output directory where fake documents will be stored.",
)
@click.option(
    "-s",
    "--stable-diffusion-api-url",
    type=str,
    required=True,
    help="URL pointing to Stable Diffusion API, used to generate identity photos.",
)
def generate_fake_structured_documents(
    template: str,
    number: int,
    output_directory: str,
    stable_diffusion_api_url: str,
) -> None:
    """Generate fake structured documents from an SVG template."""
    os.makedirs(os.path.abspath(output_directory), exist_ok=True)
    basename = os.path.basename(os.path.normpath(output_directory))
    output_dataset_filename = os.path.abspath(
        os.path.join(output_directory, f"{basename}.json")
    )
    if os.path.exists(output_dataset_filename):
        raise RuntimeError(
            f"A JSON dataset already exists in {output_directory}. "
            "Please set a new output directory, or remove the existing files."
        )
    generator = Generator(template, None, stable_diffusion_api_url or "")
    all_docs = []
    for _ in range(number):
        try:
            side_entries = generator.generate_images(output_directory)
        except Exception as err:
            logger.warning(
                f"Got an error while generating images ({type(err)}: {err}), "
                "continuing..."
            )
            continue
        all_docs.extend(side_entries)
    dataset = DocFakerDataset(
        {
            "__class__": "DocFakerDataset",
            "documents": all_docs,
            "info": {
                "author": getpass.getuser(),
                "createdAt": datetime.datetime.utcnow().isoformat(),
                "description": (
                    f"Generated document images for template {template}."
                ),
                "name": basename,
            },
        }
    )
    dataset.save(output_dataset_filename)
    logger.info(
        f"Dataset written in {os.path.abspath(output_directory)}. "
        f"See {output_dataset_filename}."
    )


if __name__ == "__main__":
    generate_fake_structured_documents()
