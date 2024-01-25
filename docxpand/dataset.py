"""DocFaker dataset."""

import datetime
import getpass
import json
import numpy as np
import os
import typing as tp

from pydantic import BaseModel, Field

from docxpand.image import ColorSpace, Image


class PointModel(BaseModel):
    """Typing for a point."""

    x: float
    """The x-coordinate of the point."""

    y: float
    """The y-coordinate of the point."""

    label: tp.Optional[str]
    """An optional name attached to the point (e.g. "top_left")."""


class QuadrangleModel(BaseModel):
    """Typing for a quadrangle.

    The points p1, p2, p3, p4 (in this order) must form a simple quadrangle.
    """

    p1: PointModel
    """First point of the quadrangle."""

    p2: PointModel
    """Second point of the quadrangle."""

    p3: PointModel
    """Third point of the quadrangle."""

    p4: PointModel
    """Fourth (and last) point of the quadrangle."""


class BaseDocumentModel(BaseModel):
    """Typing for data stored in `BaseDatasetModel.documents`.

    A document is either an image or a PDF file that is stored in MinIO,
    or in the old blobstore.
    """

    id: str = Field(..., alias="_id")
    """The identifier of this document in MongoDB (it is usually the md5 of the
    original document).
    """

    copy_name: tp.Optional[str]
    """The name of the copy to use to find the file from MongoDB. It may
    reference the original document (in this case, the copy name is in general
    "images") or the result of the transformation (crop, rectification,
    page split, ...) of the original document (in this case, the copy name is
    in general "extracted_images")."""

    md5: tp.Optional[str]
    """The MD5 hash of the document file, mainly used to distinguish between
    several transformations of the same original document (i.e. various copies)
    """

    url: tp.Optional[str]
    """The URL used to know the source of the image."""

    filename: str
    """The name of the file representing the document, with its extension
    (e.g.: "xxx.jpeg", "xxx.pdf"). When the the dataset is downloaded, each
    document is saved using this filename.
    """


class BaseAnnotationModel(BaseModel):
    """Typing for data stored in any annotation."""

    id: int = Field(..., alias="_id")
    """The identifier of the annotation"""

    annotator: str
    """The name or e-mail of the person who has labeled the document"""

    created_at: datetime.datetime
    """The date when the annotation has been created"""

    updated_at: datetime.datetime
    """The date when the annotation has been last updated"""


class DocFakerAnnotationModel(BaseAnnotationModel):
    """Typing for data stored in `DocFakerDocumentModel.annotations`."""

    fields: tp.Optional[tp.Dict[str, tp.Any]]
    """The list of labeled fields contained in the annotation."""

    position: QuadrangleModel
    """The list of points of interest, in the following format:
        {"p1" : {'x': 0.1, 'y': 0.2}, "p2" : {'x': 0.1, 'y': 0.2}, ...}
    """

    scene_image: tp.Optional[str]
    """The image of the scene."""

    template: str
    """The template used by the image."""


class DocFakerDocumentModel(BaseDocumentModel):
    """Typing for data stored in `DocFakerDatasetModel.documents`."""

    annotations: tp.Sequence[DocFakerAnnotationModel]
    """The list of Doc faker annotations on the given document."""


class BaseDatasetModel(BaseModel):
    """Typing for data stored in `BaseDataset.dataset`."""

    info: tp.Dict[str, tp.Any]
    """Information about the current dataset."""

    documents: tp.Sequence[BaseDocumentModel]
    """The list of documents contained in the dataset."""

    class Config:
        """Configuration to allow mutation especially during inheritance."""

        allow_mutation = True
        """Allows to easily change the type of documents when inheriting from
         BaseDatasetModel."""


class DocFakerDatasetModel(BaseDatasetModel):
    """Typing for data stored in `DocFakerDataset.dataset`."""

    documents: tp.Sequence[DocFakerDocumentModel]
    """The labeled documents contained in the dataset."""


class BaseDataset:
    """Base class for loading and handling a dataset.

    Attributes:
        dataset: the content of the dataset, represented as a dictionary and
            typed using pydantic and the data classes defined in this library
        images_dir: the destination directory to download document images
        _info: a copy of info contained in `dataset`, or some very basic info
            dictionary with placeholder name and description, and generated
            author and creation date.
        documents: a look-up table between document identifiers and documents
    """

    def __init__(
        self,
        dataset_input: tp.Union[str, dict],
        images_dir: str,
        validate: bool = True,
    ):
        """Init a dataset module from a path to a json file.

        Load said dataset and if validate = True, run pydantic type and
        format validation on the dataset.

        Args:
            dataset_input: can be either a path to local JSON dataset file, or
                a URL to a JSON dataset file stored on MinIO, or a dataset
                dictionary
            validate: Validate a dataset using pydantic. Defaults to True.
            images_dir: path to folder where to store images. Defaults to None.
        """
        self.dataset = (
            json.load(open(dataset_input, "r", encoding="utf-8"))
            if isinstance(dataset_input, str)
            else dataset_input
        )

        # validate dataset is in the correct format
        if validate:
            self._validate()

        # set images_dir, this where images will be downloaded
        self.images_dir = images_dir

        # set basic properties of a dataset
        self._info = self.dataset.get(
            "info",
            {
                "name": "basic_dataset",
                "createdAt": datetime.datetime.utcnow().isoformat(),
                "description": "basic_dataset_description",
                "author": getpass.getuser(),
            },
        )
        self.documents: tp.Dict[str, BaseDocumentModel] = dict()
        self._create_index()
        self._seed = None

    @property
    def _model(self) -> tp.Type[BaseDatasetModel]:
        """Return the dataset model associated to this dataset class."""
        return BaseDatasetModel

    def _validate(self) -> None:
        """Validate dataset dictionary using pydantic validators."""
        self._model.parse_obj(self.dataset)

    def _create_index(self) -> None:
        """Index the dataset documents to make them easily accessible."""
        self.documents = {
            document["_id"]: document for document in self.dataset["documents"]
        }

    def info(self) -> tp.Dict[str, tp.Any]:
        """Print information about the dataset."""
        cls = self.__class__
        info = {
            **self._info,
            "size": len(self.documents),
            "__class__": f"{cls.__module__}.{cls.__qualname__}",
        }
        return info

    def save(self, export_path: str, overwrite: bool = False) -> None:
        """Save the dataset to a json file.

        Args:
            export_path: path to json file to export to.
            overwrite: True if you want to overwrite file if it already exists.
        """
        export_path = os.path.abspath(export_path)
        if os.path.isfile(export_path) and not overwrite:
            raise OSError(
                f"The file {export_path} already exists",
                "if you want to overwrite, set overwrite parameter to True.",
            )
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        cls = self.__class__
        dataset_copy = {
            "__class__": f"{cls.__module__}.{cls.__qualname__}",
        }
        dataset_copy.update(self.dataset)
        with open(export_path, "w") as file:
            json.dump(dataset_copy, file, indent=2, sort_keys=True, default=str)

    def load_image(
        self,
        document_id,
        space: ColorSpace = ColorSpace.BGR,
        ignore_orientation: bool = True,
    ) -> np.ndarray:
        """Load and (optionally) resize document provided it's document_id.

        Args:
            document_id: _id of the document in dataset.
            images_dir: optional images_dir if it's defined or different
                from what is defined in dataset level
            space: the target color space of the image.
                Defaults to ColorSpace.BGR.
            ignore_orientation: if True, ignores the orientation flag
                    in EXIF metadata; else it is used to rotate the image
                    accordingly. Defaults to True.

        Returns:
            np.ndarray image
        """
        filepath = os.path.join(self.images_dir, self.documents[document_id].filename)
        return Image.read(filepath, space=space, ignore_orientation=ignore_orientation)


class DocFakerDataset(BaseDataset):
    """Specialization of BaseDataset class for Doc Faker."""

    def __init__(
        self,
        dataset_input: tp.Union[str, dict],
        validate: bool = True,
        images_dir: tp.Optional[str] = None,
    ):
        """Init a dataset module from a path to a json file or python dict.

        Load said dataset and if validate = True, run pydantic type and
        format validation on the dataset.

        Args:
            dataset_input: Can be either a path to json dataset,
                or a dataset_dict
            validate: Validate a dataset using pydantic.
                Defaults to True.
            images_dir: path to folder where to store images.
                Defaults to None.
            dataset_cache_dir: optional cache dir for downloaded dataset
                from minIO
        """
        super().__init__(
            dataset_input,
            validate=validate,
            images_dir=images_dir,
        )

    @property
    def _model(self) -> tp.Type[DocFakerDatasetModel]:
        """Return the dataset model associated to this dataset class."""
        return DocFakerDatasetModel
