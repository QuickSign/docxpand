"""Script to process localization dataset and insert fake IDs in scenes."""
import logging
import os
import typing as tp

import click
from docxpand.dataset import DocFakerDataset
from docxpand.geometry import Point, Quadrangle, estimate_doc_homography
from docxpand.image import ColorSpace, load_document
from docxpand.scene_insertion import color_transfer_reinhard, illumination_transfer, insert_image_in_background, rectify_document
from docxpand.specimen import load_specimen

#from docxpand.scene_insertion import insert_generated_documents_in_scenes,
from docxpand.svg_to_image import ChromeSVGRenderer
import tqdm

logger = logging.getLogger(__name__)


def load_documents(
    document_dataset_filename: str,
    document_images_directory: str,
) -> tp.List[tp.Tuple[str, str, tp.Dict[str, tp.Any]]]:
    """Loading documents images.

    Args:
        document_images_directory: path to directory containing document images.
        dataset_path: path to dataset containing images information if wanted.

    Returns:
        List of image path, document id, dataset entry.
    """
    documents = []
    dataset = DocFakerDataset(
        dataset_input=document_dataset_filename,
        images_dir=document_images_directory
    )
    progress = tqdm.tqdm(dataset.documents.items())
    progress.set_description("Loading documents dataset")
    for doc_id, entry in progress:
        image_path = (
            os.path.join(document_images_directory, entry["filename"])
        )
        image_path = image_path.replace(".jpg", ".svg")
        documents.append((image_path, doc_id, entry))
    return documents


def load_scenes(
    scene_images_directory: str,
) -> tp.Dict[str, str]:
    """Loading scene images.

    Args:
        scene_images_directory: path to directory containing scene images.

    Returns:
        Dict of doc_id to scene image path.
    """
    scenes = {}
    for filename in os.listdir(scene_images_directory):
        basename, _ = os.path.splitext(os.path.basename(filename))
        basename = basename.split("-")[0]
        scenes[basename] = os.path.join(scene_images_directory,filename)
    return scenes


@click.command()
@click.option(
    "-dd",
    "--document-dataset",
    type=click.Path(dir_okay=False, file_okay=True, readable=True),
    required=True,
    help="Path to the final dataset to regenerate.",
)
@click.option(
    "-di",
    "--document-images",
    type=click.Path(dir_okay=True, file_okay=True, readable=True),
    required=True,
    help="Path to the directory containing SVG document images.",
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
def main(
    document_dataset: str,
    document_images: str,
    scene_images: str,
    output_directory: str,
) -> None:
    """Generate fake structured documents from an SVG template."""
    renderer = ChromeSVGRenderer()
    os.makedirs(os.path.abspath(output_directory), exist_ok=True)

    # Read the documents dataset and the scenes directory
    documents = load_documents(document_dataset, document_images)
    scenes = load_scenes(scene_images)

    # Specimen image
    specimen_img = load_specimen("passport_fra_2006")

    # Iterate on documents
    progress = tqdm.tqdm(documents)
    progress.set_description("Re-inserting documents in scenes...")
    for svg_path, doc_id, doc_entry in progress:
        # Check template
        annotations = doc_entry["annotations"][0]
        template = annotations["template"]
        if template != "PP_TD3_C-front":
            continue

        # Check file is not already generated
        output_filename, _ = os.path.splitext(
            os.path.basename(doc_entry["filename"])
        )
        output_filename = os.path.join(output_directory, f"{output_filename}.jpg")
        if os.path.exists(output_filename):
            continue

        # Load images
        try:
            scene_path = scenes[annotations["scene_image"]]
        except:
            scene_path = os.path.join("/home/qsuser/Work/DocXPand/Data/DocXPand_Generated/JPG/images/", doc_entry["filename"])

        scene_img = load_document(
            scene_path, space=ColorSpace.BGRA, ignore_orientation=False
        )
        scene_quad = Quadrangle.from_dict(annotations["position"])
        scene_quad = scene_quad.rescale(scene_img.width, scene_img.height)

        doc_img = renderer.render(filename=svg_path)

        # Rectification
        document_in_scene_image = rectify_document(scene_img, scene_quad)

        # Color transfer
        document_img_transferred = (
            color_transfer_reinhard(
                scene=document_in_scene_image,
                specimen=specimen_img,
                document=doc_img
            )
        )

        # Illumination transfer
        document_img_transferred = illumination_transfer(
            scene=document_in_scene_image,
            specimen=specimen_img,
            document=document_img_transferred
        )

        # Insert document
        original_quad = Quadrangle(
            Point(0, 0),
            Point(doc_img.width, 0),
            Point(doc_img.width, doc_img.height),
            Point(0, doc_img.height),
        )
        homography = estimate_doc_homography(original_quad, scene_quad)
        inserted_img = insert_image_in_background(
            background_img=scene_img,
            img_to_insert=document_img_transferred,
            homography=homography,
            quad=scene_quad,
        )

        # Save result image
        inserted_img.write(output_filename)

if __name__ == "__main__":
    main()
