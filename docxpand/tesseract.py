"""Tesseract API wrapper."""

import typing as tp

import numpy as np
from tesserocr import OEM, PSM, PyTessBaseAPI, RIL

from docxpand.image import ColorSpace, Image

TESSDATA_PATH = "/usr/share/tesseract-ocr/4.00/tessdata/"


class Tesseract:
    """Class that provides a wrapper for Tesseract executable.

    Args:
        oem : recognition mode. (see :class:`tesserocr.OEM`)
        psm : page segmentation mode (see :`class:tesserocr.PSM`)
        languages: languages to use (using ISO 639-3 3-character language code)
        config : config dict (using tesseract's parameters)

    Attributes:
        _oem : recognition mode
        _psm :  page segmentation mode
        _languages: languages to use
        _config : config dict
        _loaded_models : cache to index models already loaded
    """

    def __init__(
        self,
        oem: OEM = OEM.DEFAULT,
        psm: PSM = PSM.AUTO_OSD,
        languages: tp.Tuple[str, ...] = (
            "ocrb", "eng", "fra", "deu", "nld", "por", "ita", "spa", "cat"
        ),
        config: tp.Optional[tp.Dict[str, tp.Any]] = None,
    ):
        """Init."""
        self._oem = oem
        self._psm = psm  # Automatic page segmentation with OSD.
        self._languages = languages
        self._config = config if config else {}
        self._loaded_apis: tp.Dict[str, PyTessBaseAPI] = {}
        self._current_api: PyTessBaseAPI = self._load_api(
            self._oem, self._psm, self._languages
        )

    def _load_api(
        self, oem: OEM, psm: PSM, languages: tp.Tuple[str, ...]
    ) -> PyTessBaseAPI:
        """Load and initialize Tesseract API knowing OEM, PSM and languages to use.

        Args:
            oem : recognition mode. (see :class:`tesserocr.OEM`)
            psm : page segmentation mode (see :`class:tesserocr.PSM`)
            languages: languages to use (using ISO 639-3 3-character code)
        """
        lang = "+".join(list(languages))
        key = f"{lang}_{psm}_{oem}"
        if key in self._loaded_apis:
            return self._loaded_apis[key]
        api = PyTessBaseAPI(init=False)
        config = {str(k): str(v) for k, v in self._config.items()}
        api.InitFull(path=TESSDATA_PATH, lang=lang, variables=config, oem=oem)
        api.SetPageSegMode(psm)
        self._loaded_apis[key] = api
        return api

    @property
    def config(self) -> tp.Optional[tp.Dict[str, tp.Any]]:
        """Return the config dict."""
        return self._config

    @property
    def oem(self) -> OEM:
        """Return oem parameter.
        
        Returns:
            oem parameter.
        """
        return self._oem
    
    @oem.setter
    def oem(self, value: OEM) -> None:
        """Set the oem parameter value.
        
        Args:
            value: the oem parameter value.
        """
        self._oem = value

    @property
    def psm(self) -> PSM:
        """Return psm parameter.
        
        Returns:
            psm parameter.
        """
        return self._psm
    
    @psm.setter
    def psm(self, value: PSM) -> None:
        """Set the psm parameter value.
        
        Args:
            value: the psm parameter value.
        """
        self._psm = value

    @property
    def languages(self) -> tp.Tuple[str, ...]:
        """Return languages parameter.
        
        Returns:
            languages parameter.
        """
        return self._languages
    
    @languages.setter
    def languages(self, value: tp.Tuple[str, ...]) -> None:
        """Set the languages parameter value.
        
        Args:
            value: the languages parameter value.
        """
        self._languages = value

    def _set_array(self, array: np.ndarray) -> None:
        """Define numpy array to use for recognition. Prefer using set_image.

        If the array has 2 dimensions (i.e. 1 channel), it is considered
        to be binary or grayscale depending on the type (bool or uint8). Else,
        if the array has 3 dimensions, 3 channels is considered BGR and
        4 channels is considered BGRA.

        Other values for number of dimensions and channels raise a RuntimeError.

        Args:
            array : numpy array
            recognizer : model to use as recognizer
        """
        self._set_image(Image.from_array(array))

    def _set_image(self, image: Image) -> None:
        """Define image to use for recognition.

        Args:
            image: image to use
            recognizer : model to use as recognizer
        """
        height = image.height
        width = image.width
        image_for_ocr = (
            image.convert_color(ColorSpace.GRAYSCALE)
            if image.channels == 1
            else image.convert_color(ColorSpace.RGB)
        )
        byte_per_pixel = image_for_ocr.channels
        bytes_per_line = byte_per_pixel * width
        image_data = image_for_ocr.array.tobytes()
        self._current_api.SetImageBytes(
            image_data, width, height, byte_per_pixel, bytes_per_line
        )

    def _set_image_file(self, image_file: str) -> None:
        """Define image file to use for recognition.

        Args:
            image_file: image file to use.
        """
        self._current_api.SetImageFile(str(image_file))

    def set_input(
        self, image: tp.Union[np.ndarray, str, Image]
    ) -> "Tesseract":
        """Set image in current Tesseract API.

        The image will be converted to RGB before ocr process.

        Args:
            image: numpy array or path to image on disk

        Returns:
            self object to chain with call to recognize
        """
        self._current_api = self._load_api(self._oem, self._psm, self._languages)
        if isinstance(image, str):
            self._set_image_file(image)
        elif isinstance(image, np.ndarray):
            self._set_array(image)
        elif isinstance(image, Image):
            self._set_image(image)
        return self
    
    def recognize(self) -> tp.Tuple[str, float]:
        """Recognize input image and return text and score.

        Returns:
            tuple containing text and score
        """
        text: str = self._current_api.GetUTF8Text()
        score: float = self._current_api.MeanTextConf() / 100
        return text, score
