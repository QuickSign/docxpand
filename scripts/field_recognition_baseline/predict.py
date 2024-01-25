"""Script to run field recognition using Tesseract."""
import logging
import os

import click
import tqdm

from docxpand.dataset import DocFakerDataset
from docxpand.scene_insertion import rectify_document
from docxpand.geometry import Point, Quadrangle
from docxpand.image import Image
from docxpand.tesseract import Tesseract, PSM


logger = logging.getLogger(__name__)

ENLARGE_FACTOR = 0.02

LANGUAGES_PER_TEMPLATE = {
    "ID_CARD_TD1_A-back": ("deu", ),
    "ID_CARD_TD1_A-front": ("deu", ),
    "ID_CARD_TD1_B-back": ("eng", ),
    "ID_CARD_TD1_B-front": ("eng", ),
    "ID_CARD_TD2_A-back": ("fra", ),
    "ID_CARD_TD2_A-front": ("fra", ),
    "ID_CARD_TD2_B-back": ("spa", ),
    "ID_CARD_TD2_B-front": ("spa", ),
    "PP_TD3_A-front": ("fra", ),
    "PP_TD3_B-front": ("por", ),
    "PP_TD3_C-front": ("nld", ),
    "RP_CARD_TD1-back": ("nld", "fra", "deu", ),
    "RP_CARD_TD1-front": ("nld", "fra", "deu", ),
    "RP_CARD_TD2-back": ("ita", ),
    "RP_CARD_TD2-front": ("ita", )
}

@click.command()
@click.option(
    "-td",
    "--test-dataset",
    type=click.Path(dir_okay=False, file_okay=True, readable=True),
    required=True,
    help="Path to the input test dataset, with generated documents and ground-truth values.",
)
@click.option(
    "-di",
    "--document-images",
    type=click.Path(dir_okay=True, file_okay=True, readable=True),
    required=True,
    help="Path to the directory containing documents dataset images.",
)
@click.option(
    "-pd",
    "--prediction-dataset",
    type=click.Path(dir_okay=False, file_okay=True, writable=True),
    required=True,
    help="Path to the output prediction dataset, with field predictions.",
)
def predict(
    test_dataset: str,
    document_images: str,
    prediction_dataset: str,
) -> None:
    """Run field recognition using Tesseract."""
    input_dataset = DocFakerDataset(
        dataset_input=test_dataset,
        images_dir=document_images
    )
    progress = tqdm.tqdm(input_dataset.documents.values())
    progress.set_description("Recognizing text fields")
    tesseract = Tesseract(psm = PSM.SINGLE_BLOCK)
    for doc_entry in progress:
        filename = os.path.join(document_images, doc_entry["filename"])
        image = Image.read(filename)
        annotations = doc_entry["annotations"][0]
        template = annotations["template"]
        fields = annotations["fields"]
        side = list(fields.keys())[0]
        fields = fields[side]
        for field_name, field in fields.items():
            if (
                (field["type"] != "text") or
                ("signature" in field_name) or  # signatures (not evaluated)
                (field["position"] is None) or  # intermediary fields (to generate mixed fields)
                (field["value"] is None)        # empty fields (not evaluated)
            ):
                continue
            position = Quadrangle.from_dict(field["position"])
            position = Quadrangle(*[
                Point(pt.x * image.width, pt.y * image.height)
                for pt in position
            ])
            position = position.enlarge(ENLARGE_FACTOR, viewport=(image.width, image.height))
            field_width = int(position.estimate_length())
            field_image = rectify_document(image, position, field_width)

            # Set the right model for tesseract
            if "mrz" in field_name.lower():
                tesseract.languages = ("ocrb", )
            else:
                tesseract.languages = LANGUAGES_PER_TEMPLATE[template]
            
            # Handle rotated field
            if field_image.width < field_image.height:
                text_scores = {}
                for angle in [0, 90, 270]:
                    text, score = tesseract.set_input(field_image.rotate90(angle)).recognize()
                    text_scores[text] = score
                text = max(text_scores, key=text_scores.__getitem__)
            # Normal field
            else:
                text, _ = tesseract.set_input(field_image).recognize()

            if "\n" in text:
                text = [
                    sub_text.strip()
                    for sub_text in text.split("\n")
                    if sub_text.strip()
                ]

            field["prediction"] = text

    input_dataset.save(prediction_dataset)

if __name__ == "__main__":
    predict()
