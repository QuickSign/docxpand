import base64
import json
import os
import random
import typing as tp
from urllib.request import Request, urlopen

import cv2
import dateparser
import imagehash
import numpy as np
from dateutil.relativedelta import relativedelta
from deepface import DeepFace

from docxpand.geometry import BoundingBox, Point
from docxpand.image import ColorSpace, Image
from docxpand.providers.photo.halftone import halftone
from docxpand.specimen import SPECIMENS_DIR
from docxpand.utils import get_field_from_any_side

ID_PHOTO_BANK_LOCATION = os.path.abspath(
    os.path.join(os.path.dirname(__file__), *(os.pardir,) * 5, "id_photos")
)


class IDPhoto(tp.NamedTuple):
    filename: tp.Optional[str]
    gender: str
    age: int
    ethnicity: str
    image: tp.Optional[Image]

    @property
    def filepath(self) -> str:
        if self.filename:
            filename = filename
        elif self.image is not None:
            filename = IDPhoto.generate_filename(
                self.generate_filename, self.age, self.ethnicity, self.image
            )
        else:
            raise RuntimeError("Cannot generate filepath without filename nor image")
        return os.path.join(ID_PHOTO_BANK_LOCATION, self.filename)

    @staticmethod
    def generate_filename(
        gender: str, age: int, ethnicity: str, image: Image, image_format="jpg"
    ) -> str:
        ethnicity = ethnicity.replace(" ", "-")
        image_hash = imagehash.average_hash(image.array)
        return f"{gender}_{age}_{ethnicity}_{image_hash}.{image_format}"

    @staticmethod
    def from_filepath(filepath: str) -> "IDPhoto":
        filename = os.path.basename(filepath)
        basename, _ = os.path.splitext(filename)
        gender, age, ethnicity, _ = basename.split("_")
        ethnicity = ethnicity.replace("-", " ")
        age = int(age)
        return IDPhoto(filename, gender, ethnicity, age, None)

    @staticmethod
    def from_image(
        image: Image, gender: str = "", age: str = "", ethnicity: str = ""
    ) -> "IDPhoto":
        # We set emotion by default, because no actions means no face detection...
        # emotion model is the smallest model of all
        actions = ["emotion"]
        if not gender:
            actions.append("gender")
        if not age:
            actions.append("age")
        if not ethnicity:
            actions.append("ethnicity")
        try:
            analysis = DeepFace.analyze(
                image.array,
                actions=actions,
                detector_backend="retinaface",
            )
        except Exception:
            return IDPhoto(None, "", -1, "", None), None
        if not gender:
            gender = {"Woman": "female", "Man": "male"}[analysis["gender"]]
        if not age:
            age = int(analysis["age"])
        if not ethnicity:
            ethnicity = analysis["race"]
        region = analysis[0]["region"]
        top_left = Point(region["x"], region["y"])
        bottom_right = Point(
            int(region["x"] + region["w"]), (region["y"] + region["h"])
        )
        bbox = BoundingBox(top_left, bottom_right)
        bbox = bbox.enlarge(
            (
                0.2 * bbox.width,
                0.5 * bbox.height,
                0.2 * bbox.width,
                0.2 * bbox.height
            ),
            (image.width, image.height),
        )
        image = image.crop(bbox)
        id_photo = IDPhoto(None, gender, age, ethnicity, image)
        return id_photo, image

    def load(self) -> Image:
        if self.image is not None:
            return self.image
        return Image.read(self.filepath)

    def save(self, image: tp.Optional[Image]) -> None:
        if self.image:
            image = self.image
        if image is None:
            raise RuntimeError("Cannot save without input image")
        cv2.imwrite(self.filepath, image.array)

    def remove(self) -> None:
        os.remove(self.filepath)

    def corresponds(
        self, age: int, gender: str, ethnicity: str, age_tolerance: int = 5
    ) -> bool:
        if age_tolerance < 0:
            return ValueError(
                f"The age tolerance must be positive (got {age_tolerance})."
            )
        return (
            gender in ["nonbinary", self.gender]
            and ethnicity == self.ethnicity
            and abs(age - self.age) <= age_tolerance
        )


class Provider:
    def __init__(self) -> None:
        os.makedirs(ID_PHOTO_BANK_LOCATION, exist_ok=True)
        self._bank: tp.List[IDPhoto] = [
            IDPhoto.from_filepath(filename)
            for filename in os.listdir(ID_PHOTO_BANK_LOCATION)
        ]

    def generate_id_photo(
        self,
        target_gender: str,
        target_age: int,
        target_ethnicity: str,
        url: str,
    ) -> IDPhoto:
        raise NotImplementedError

    def get_image_from_bank_or_new(
        self,
        gender: str,
        age: int,
        ethnicity: str,
        age_tolerance: int = 5,
        max_tries: int = 10,
        url: str = "",
    ) -> Image:
        if max_tries <= 0:
            return ValueError(
                "The maximum number of tries must be strictly positive "
                f"(got {max_tries})."
            )
        print(
            f"Requesting photo with age={age} gender={gender} "
            f"ethnicity={ethnicity}, and with age_tolerance={age_tolerance}"
        )
        # Search in bank
        for id_photo in list(self._bank):
            if id_photo.corresponds(age, gender, ethnicity, age_tolerance):
                # Delete the file, remove the entry from bank and load the image
                image = id_photo.load()
                id_photo.remove()
                self._bank.remove(id_photo)
                return image

        # No corresponding id photo in bank, get a new id photo
        for _ in range(max_tries):
            id_photo = (
                self.generate_id_photo(gender, age, ethnicity)
                if not url
                else self.generate_id_photo(gender, age, ethnicity, url)
            )
            if id_photo.corresponds(age, gender, ethnicity, age_tolerance):
                # Simply return the image without saving it
                return id_photo.image

            # Persist the id photo in the bank for later
            if id_photo.image is not None:
                id_photo.save()
                self._bank.append(id_photo)
                print(
                    f"Got new photo with age={id_photo.age} "
                    f"gender={id_photo.gender} ethnicity={id_photo.etnicity}, "
                    f"saved to {id_photo.filepath}."
                )

        # If not correspondance after "max_tries" tries, try with a larger age
        # tolerance.
        return self.get_image_from_bank_or_new(
            gender, age, 2 * age_tolerance, max_tries, url=url
        )

    @staticmethod
    def get_age_from_existing_fields(existing_fields: tp.Dict[str, tp.Any]) -> int:
        if not existing_fields:
            raise RuntimeError("Cannot get age, existing fields are missing.")

        birth_date_str = get_field_from_any_side(existing_fields, "birth_date", None)
        if birth_date_str is None:
            raise RuntimeError("Cannot get age, birth_date is missing.")
        birth_date = dateparser.parse(birth_date_str)

        date_issued_str = get_field_from_any_side(existing_fields, "date_issued", None)
        if date_issued_str is None:
            expires_str = get_field_from_any_side(existing_fields, "expires", None)
            if expires_str is None:
                raise RuntimeError(
                    "Cannot get age, date_issued and expires are missing."
                )
            expires = dateparser.parse(expires_str)
            # Use default expiration delay of 10 years
            date_issued = expires + relativedelta(years=-10, months=0, days=1)
        else:
            date_issued = dateparser.parse(date_issued_str)

        # Compute age at issue date
        return relativedelta(date_issued, birth_date).years

    @staticmethod
    def _scale_if_needed(image: Image, width: int, height: int) -> Image:
        if image.width == width and image.height == height:
            return image
        scale_factor = max(width / image.width, height / image.height)
        resized = cv2.resize(image.array, None, fx=scale_factor, fy=scale_factor)
        return Image(resized, image.space)

    @staticmethod
    def _center_crop_if_needed(image: Image, width: int, height: int) -> Image:
        if width >= image.width and height >= image.height:
            return image

        margin_width = (image.width - width) / 2
        margin_height = (image.height - height) / 2
        bbox = BoundingBox(
            Point(margin_width, margin_height),
            Point(image.width - margin_width, image.height - margin_height),
        )
        return image.crop(bbox)

    def id_photo(
        self,
        width: int,
        height: int,
        gender: str = "nonbinary",
        ethnicity: str = "west european",
        url: str = "",
        existing_fields: tp.Optional[tp.Dict[str, tp.Any]] = None,
    ) -> np.ndarray:
        age = Provider.get_age_from_existing_fields(existing_fields)
        image = self.get_image_from_bank_or_new(gender, age, ethnicity, url=url)
        image = self._scale_if_needed(image, width, height)
        return self._center_crop_if_needed(image, width, height)

    def ghost_image(
        self,
        width: int,
        height: int,
        mode: str = "normal",
        original_photo: str = "photo",
        brightness: tp.Optional[float] = None,
        existing_fields: tp.Optional[tp.Dict[str, tp.Any]] = None,
    ) -> Image:
        image = get_field_from_any_side(existing_fields, original_photo, None)
        if image is None:
            raise RuntimeError(
                "Cannot find original ID photo to generate the ghost image"
            )
        if mode == "halftone":
            image = Image(halftone(image.array), image.space)
        elif mode == "grayscale":
            image = image.convert_color(ColorSpace.GRAYSCALE)
        elif mode == "desaturate":
            raise NotImplementedError
        # elif mode == "normal":
        #   do nothing :)

        if brightness is not None:
            brighter = image.array.astype("float64")
            brighter = brighter * brightness / np.mean(brighter)
            brighter[brighter >= 255] = 255
            image = Image(brighter.astype("uint8"), image.space)

        image = self._scale_if_needed(image, width, height)
        return self._center_crop_if_needed(image, width, height)


class StableDiffusionProvider(Provider):
    GENDERS = {
        "male": "man",
        "female": "woman",
        "nonbinary": "non-binary person",
    }

    SOURCE_PHOTOS = {
        "male": ["man_1.jpg", "man_2.jpg"],
        "female": ["woman_1.jpg", "woman_2.jpg"],
    }

    @staticmethod
    def get_random_source_photo() -> Image:
        all_sources = []
        for sources in StableDiffusionProvider.SOURCE_PHOTOS.values():
            all_sources.extend(sources)
        filename = os.path.join(SPECIMENS_DIR, "photos", random.choice(sources))
        return Image.read(filename)

    @staticmethod
    def get_sdapi_url_from_hostname_port(hostname_and_port: str):
        url = hostname_and_port.strip().strip("/")

        # Nothing: add localhost
        if not url:
            url = "localhost"

        # No port, add stable diffusion default port
        if ":" not in url:
            url = f"{url}:7860"  # default stable diffusion API port

        # No protocol, add http protocol
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"

        # Missing endpoint, add it
        if not url.endswith("/sdapi/v1"):
            url = f"{url}/sdapi/v1"

        return url

    def generate_id_photo(
        self,
        target_gender: str,
        target_age: int,
        target_ethnicity: str,
        url: str = "",
    ) -> IDPhoto:
        headers: tp.Dict[str, str] = {"Content-Type": "application/json"}
        prompt_template = (
            "face of a {gender}, {ethnicity}, {age} years old, neutral "
            "expression, body facing the camera, centered face, "
            "eyes looking front to the camera, clear background, "
            "color photography"
        )
        negative_prompt = (
            "(((text))), (((watermark))), (((black and white))), "
            "glasses, hat, jewelry, smiling, naked"
        )

        gender = {
            "male": "man",
            "female": "woman",
            "nonbinary": "non-binary person",
        }[target_gender]
        custom_prompt = prompt_template.format(
            gender=gender,
            age=target_age,
            ethnicity=target_ethnicity,
        )
        parameters = {
            "prompt": custom_prompt,
            "negative_prompt": negative_prompt,
            # affects the quality, but also the processing time
            "steps": 20,
            "width": 448,
            "height": 576,
            # gives better faces
            "restore_faces": True,
            # controls the fact that the generated photos looks like the source
            "denoising_strength": 0.9,
            "init_images": [
                self.get_random_source_photo().base64encode()
            ],
        }
        url = self.get_sdapi_url_from_hostname_port(url)

        # Call img2img with custom prompt
        request = Request(
            url=f"{url}/img2img",
            headers=headers,
            data=json.dumps(parameters).encode("utf-8"),
        )
        response = json.loads(urlopen(request).read().decode("utf-8"))

        # We asked only for one image, decoding it using OpenCV
        image = Image.from_buffer(base64.b64decode(response["images"][0]))
        return IDPhoto.from_image(
            image, target_gender, target_age, target_ethnicity
        )[0]


class ThisPersonDoesNotExistProvider(Provider):
    def generate_id_photo(
        self,
        target_gender: str,
        target_age: int,
        target_ethnicity: str,
        url: str = "http://thispersondoesnotexist.com/image",
    ) -> IDPhoto:
        headers: tp.Dict[str, str] = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/83.0.4103.116 Safari/537.36"
            )
        }
        # Cannot use the targets to control the source...
        request = Request(url=url, headers=headers)
        image = Image.from_buffer(urlopen(request).read())
        return IDPhoto.from_image(image)
