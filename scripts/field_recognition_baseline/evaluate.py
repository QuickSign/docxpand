"""Script to evaluate field recognition."""
from enum import Enum
import logging
import typing as tp

import click
from docxpand.normalizer import collapse_whitespace
import numpy as np
import tqdm

from docxpand.dataset import DocFakerDataset
from docxpand.metrics import character_error_rate

logger = logging.getLogger(__name__)


class FieldCategory(Enum):
    ALPHA = "ALPHA"
    NUMERIC = "NUMERIC"
    ALPHANUMERIC = "ALPHANUM"
    MRZ = "MRZ"


FIELD_CATEGORIES_PER_TEMPLATE = {
    "ID_CARD_TD1_A-back":{
        "address" : FieldCategory.ALPHANUMERIC,
        "authority" : FieldCategory.ALPHA,
        "date_issued" : FieldCategory.NUMERIC,
        "height" : FieldCategory.ALPHANUMERIC,
        "mrz" : FieldCategory.MRZ
    },
    "ID_CARD_TD1_A-front":{
        "birth_date" : FieldCategory.NUMERIC,
        "birth_name" : FieldCategory.ALPHA,
        "birth_place" : FieldCategory.ALPHA,
        "card_access_number" : FieldCategory.NUMERIC,
        "document_number" : FieldCategory.ALPHANUMERIC,
        "expires" : FieldCategory.NUMERIC,
        "family_name" : FieldCategory.ALPHA,
        "given_name" : FieldCategory.ALPHA,
        "nationality" : FieldCategory.ALPHA
    },
    "ID_CARD_TD1_B-back":{
        "authority" : FieldCategory.ALPHA,
        "can_number" : FieldCategory.NUMERIC,
        "date_and_place_issued" : FieldCategory.ALPHANUMERIC,
        "mrz" : FieldCategory.MRZ
    },
    "ID_CARD_TD1_B-front":{
        "birth_date_and_place" : FieldCategory.ALPHANUMERIC,
        "birth_name" : FieldCategory.ALPHA,
        "can" : FieldCategory.NUMERIC,
        "document_number" : FieldCategory.ALPHANUMERIC,
        "expires" : FieldCategory.NUMERIC,
        "family_name" : FieldCategory.ALPHA,
        "gender" : FieldCategory.ALPHA,
        "given_name" : FieldCategory.ALPHA,
        "nationality" : FieldCategory.ALPHA,
        "personal_number" : FieldCategory.ALPHANUMERIC
    },
    "ID_CARD_TD2_A-back":{
        "address" : FieldCategory.ALPHANUMERIC,
        "authority" : FieldCategory.ALPHANUMERIC,
        "date_issued" : FieldCategory.NUMERIC,
        "expires" : FieldCategory.NUMERIC
    },
    "ID_CARD_TD2_A-front":{
        "birth_date" : FieldCategory.NUMERIC,
        "birth_place" : FieldCategory.ALPHANUMERIC,
        "document_number" : FieldCategory.ALPHANUMERIC,
        "family_name" : FieldCategory.ALPHA,
        "gender" : FieldCategory.ALPHA,
        "given_name" : FieldCategory.ALPHA,
        "height" : FieldCategory.ALPHANUMERIC,
        "initials" : FieldCategory.ALPHA,
        "mrz" : FieldCategory.MRZ
    },
    "ID_CARD_TD2_B-back":{
        "address" : FieldCategory.ALPHANUMERIC,
        "birth_place" : FieldCategory.ALPHA,
        "parents" : FieldCategory.ALPHA
    },
    "ID_CARD_TD2_B-front":{
        "birth_date" : FieldCategory.NUMERIC,
        "document_number" : FieldCategory.ALPHANUMERIC,
        "expires" : FieldCategory.NUMERIC,
        "family_name" : FieldCategory.ALPHA,
        "gender" : FieldCategory.ALPHA,
        "given_name" : FieldCategory.ALPHA,
        "mrz" : FieldCategory.MRZ,
        "nationality" : FieldCategory.ALPHA,
        "second_family_name" : FieldCategory.ALPHA
    },
    "PP_TD3_A-front":{
        "address" : FieldCategory.ALPHANUMERIC,
        "authority" : FieldCategory.ALPHANUMERIC,
        "birth_date" : FieldCategory.NUMERIC,
        "birth_place" : FieldCategory.ALPHANUMERIC,
        "country_code" : FieldCategory.ALPHA,
        "date_issued" : FieldCategory.NUMERIC,
        "document_number" : FieldCategory.ALPHANUMERIC,
        "document_number_bis" : FieldCategory.ALPHANUMERIC,
        "expires" : FieldCategory.NUMERIC,
        "eyes_color" : FieldCategory.ALPHA,
        "family_name" : FieldCategory.ALPHA,
        "gender" : FieldCategory.ALPHA,
        "given_name" : FieldCategory.ALPHA,
        "height" : FieldCategory.ALPHANUMERIC,
        "mrz" : FieldCategory.MRZ,
        "nationality" : FieldCategory.ALPHA,
        "type" : FieldCategory.ALPHA
    },
    "PP_TD3_B-front":{
        "authority" : FieldCategory.ALPHA,
        "birth_date" : FieldCategory.NUMERIC,
        "birth_place" : FieldCategory.ALPHA,
        "country_code" : FieldCategory.ALPHA,
        "date_issued" : FieldCategory.NUMERIC,
        "document_number" : FieldCategory.ALPHANUMERIC,
        "expires" : FieldCategory.NUMERIC,
        "family_name" : FieldCategory.ALPHA,
        "gender" : FieldCategory.ALPHA,
        "given_name" : FieldCategory.ALPHA,
        "height" : FieldCategory.ALPHANUMERIC,
        "mrz" : FieldCategory.MRZ,
        "nationality" : FieldCategory.ALPHA,
        "personal_number" : FieldCategory.NUMERIC,
        "type" : FieldCategory.ALPHA
    },
    "PP_TD3_C-front":{
        "authority" : FieldCategory.ALPHA,
        "birth_date" : FieldCategory.NUMERIC,
        "birth_place" : FieldCategory.ALPHA,
        "country_code" : FieldCategory.ALPHA,
        "date_issued" : FieldCategory.NUMERIC,
        "document_number" : FieldCategory.ALPHANUMERIC,
        "expires" : FieldCategory.NUMERIC,
        "family_name" : FieldCategory.ALPHA,
        "gender" : FieldCategory.ALPHA,
        "given_name" : FieldCategory.ALPHA,
        "height" : FieldCategory.ALPHANUMERIC,
        "mrz" : FieldCategory.MRZ,
        "nationality" : FieldCategory.ALPHA,
        "photo_birth_month" : FieldCategory.NUMERIC,
        "photo_birth_year" : FieldCategory.NUMERIC,
        "type" : FieldCategory.ALPHA
    },
    "RP_CARD_TD1-back":{
        "birth_place" : FieldCategory.ALPHA,
        "date_issued" : FieldCategory.NUMERIC,
        "mrz" : FieldCategory.MRZ,
        "observations" : FieldCategory.ALPHA,
        "place_issued" : FieldCategory.ALPHA
    },
    "RP_CARD_TD1-front":{
        "birth_date" : FieldCategory.NUMERIC,
        "document_number" : FieldCategory.ALPHANUMERIC,
        "expires" : FieldCategory.NUMERIC,
        "family_name" : FieldCategory.ALPHA,
        "foreign_nationality" : FieldCategory.ALPHA,
        "gender" : FieldCategory.ALPHA,
        "given_name" : FieldCategory.ALPHA,
        "observations" : FieldCategory.ALPHA,
        "permit_type" : FieldCategory.ALPHA
    },
    "RP_CARD_TD2-back":{
        "birth_place" : FieldCategory.ALPHA,
        "date_issued" : FieldCategory.NUMERIC,
        "observations" : FieldCategory.ALPHA,
        "place_issued" : FieldCategory.ALPHA
    },
    "RP_CARD_TD2-front":{
        "birth_date" : FieldCategory.NUMERIC,
        "document_number" : FieldCategory.ALPHANUMERIC,
        "expires" : FieldCategory.NUMERIC,
        "family_name" : FieldCategory.ALPHA,
        "foreign_nationality" : FieldCategory.ALPHA,
        "gender" : FieldCategory.ALPHA,
        "given_name" : FieldCategory.ALPHA,
        "mrz" : FieldCategory.MRZ,
        "observations" : FieldCategory.ALPHA,
        "permit_type" : FieldCategory.ALPHA
    }
}


@click.command()
@click.option(
    "-pd",
    "--prediction-dataset",
    type=click.Path(dir_okay=False, file_okay=True, writable=True),
    required=True,
    help="Path to the output prediction dataset, with field predictions.",
)
def evaluate(
    prediction_dataset: str,
) -> None:
    """Run field recognition using Tesseract."""
    output_dataset = DocFakerDataset(prediction_dataset)
    progress = tqdm.tqdm(output_dataset.documents.values())
    progress.set_description("Evaluating text fields recognition")

    results_per_category: tp.Dict[
            FieldCategory, tp.Dict[str, tp.List[tp.Union[bool, float]]]
    ] = {}
    results_per_field_name: tp.Dict[
            str, tp.Dict[str, tp.Dict[str, tp.List[tp.Union[bool, float]]]]
    ] = {}
    for doc_entry in progress:
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

            # Join to GT and prediction to single string.
            # Collapse multiple whitespaces to single space.
            ground_truth = field["value"]
            if isinstance(ground_truth, list):
                ground_truth = collapse_whitespace(" ".join(ground_truth))
            prediction = field["prediction"]
            if isinstance(prediction, list):
                prediction = collapse_whitespace(" ".join(prediction))

            # Get field category from pre-computed list
            field_category = FIELD_CATEGORIES_PER_TEMPLATE[template][field_name]
            if field_category not in results_per_category:
                results_per_category[field_category] = {
                        "accuracy": [],
                        "cer": []
                }
            
            if template not in results_per_field_name:
                results_per_field_name[template] = {}
            if field_name not in results_per_field_name[template]:
                results_per_field_name[template][field_name] = {
                        "accuracy": [],
                        "cer": []
                }

            # Field accuracy
            # Only tolerance on accuracy = multiple spaces count as one.
            results_per_category[field_category]["accuracy"].append(
                prediction == ground_truth
            )
            results_per_field_name[template][field_name]["accuracy"].append(
                results_per_category[field_category]["accuracy"][-1]
            )

            # CER
            results_per_category[field_category]["cer"].append(
                character_error_rate(prediction, ground_truth)
            )
            results_per_field_name[template][field_name]["cer"].append(
                results_per_category[field_category]["cer"][-1]
            )

    # Per template and field
    for template in sorted(results_per_field_name.keys()):
        print("="*48)
        print(template)
        overall_accuracy = []
        overall_cer = []
        for field_name in sorted(results_per_field_name[template].keys()):
            acc = results_per_field_name[template][field_name]["accuracy"]
            overall_accuracy.extend(acc)
            cer = results_per_field_name[template][field_name]["cer"]
            overall_cer.extend(cer)
            print(f"  - {field_name}:")
            print("    - number: ", len(acc))
            print("    - accuracy: ", 100*np.mean(acc), "%")
            print("    - cer: ", 100*np.mean(cer), "%")
        print("  - Overall")
        print("    - number: ", len(overall_accuracy))
        print("    - accuracy: ", 100*np.mean(overall_accuracy), "%")
        print("    - cer: ", 100*np.mean(overall_cer), "%")

    # Per field type over the dataset
    print("="*48)
    print("All templates:")
    overall_accuracy = []
    overall_cer = []
    for field_category in results_per_category:
        acc = results_per_category[field_category]["accuracy"]
        overall_accuracy.extend(acc)
        cer = results_per_category[field_category]["cer"]
        overall_cer.extend(cer)
        print(f"  - {field_category}:")
        print("    - number: ", len(acc))
        print("    - accuracy: ", 100*np.mean(acc), "%")
        print("    - cer: ", 100*np.mean(cer), "%")
    print("  - Overall")
    print("    - number: ", len(overall_accuracy))
    print("    - accuracy: ", 100*np.mean(overall_accuracy), "%")
    print("    - cer: ", 100*np.mean(overall_cer), "%")


if __name__ == "__main__":
    evaluate()
