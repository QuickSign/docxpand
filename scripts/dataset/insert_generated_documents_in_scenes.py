"""Script to process localization dataset and insert fake IDs in scenes."""
import logging
import os
import typing as tp

import click

from docxpand.scene_insertion import insert_generated_documents_in_scenes
from docxpand.svg_to_image import ChromeSVGRenderer

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "-dd",
    "--document-dataset",
    type=click.Path(dir_okay=False, file_okay=True, readable=True),
    required=True,
    help="Path to the dataset with generated documents that we put in scenes.",
)
@click.option(
    "-di",
    "--document-images",
    type=click.Path(dir_okay=True, file_okay=True, readable=True),
    required=True,
    help="Path to the directory containing documents dataset images.",
)
@click.option(
    "-sd",
    "--scene-dataset",
    type=click.Path(dir_okay=False, file_okay=True, readable=True),
    required=True,
    help=(
        "Path to the dataset with localised documents to be used as scene "
        "images."
    ),
)
@click.option(
    "-si",
    "--scene-images",
    type=click.Path(dir_okay=True, file_okay=False, readable=True),
    required=True,
    help=(
        "Path to directory containing scene dataset images (scene images)."
    ),
)
@click.option(
    "-o",
    "--output-directory",
    type=click.Path(dir_okay=True, file_okay=False, writable=True),
    required=True,
    help="Path to output directory where fake documents will be stored.",
)
@click.option(
    "-m",
    "--margins",
    type=float,
    required=False,
    default=None,
    help=(
        "Relative margins (between 0.0 and 1.0) to add around the localized "
        "quadrangle ."
    ),
)
@click.option(
    "--seed",
    type=int,
    required=False,
    default=None,
    help="Seed to initialize backgrounds shuffling.",
)
def main(
    document_dataset: str,
    document_images: str,
    scene_dataset: str,
    scene_images: str,
    output_directory: str,
    margins: tp.Optional[float],
    seed: tp.Optional[int]
) -> None:
    """Generate fake structured documents from an SVG template."""
    renderer = ChromeSVGRenderer()
    output_dataset_filename = insert_generated_documents_in_scenes(
        document_dataset,
        document_images,
        scene_dataset,
        scene_images,
        renderer,
        output_directory,
        margins,
        seed
    )
    logger.info(
        f"Dataset written in {os.path.abspath(output_directory)}. "
        f"See {output_dataset_filename}."
    )


if __name__ == "__main__":
    main()
