"""Provide a basic function to read images."""

import base64
import os
import typing as tp
from enum import Enum

import cv2
import math
import numpy as np

from docxpand.geometry import BoundingBox

SUPPORTED_IMAGE_FORMATS: tp.List[str] = [
    "image/jpeg",
    "image/png",
    "image/tiff",
]
# list of supported formats for single-frame image reading and writing

WHITE = (255, 255, 255)


class ColorSpace(Enum):
    """Enum for supported color spaces."""

    BINARY = "BINARY"  # dtype=bool
    GRAYSCALE = "GRAY"  # dtype=uint8
    RGB = "RGB"  # dtype=uint8, channels=3 (red, green, blue)
    BGR = "BGR"  # dtype=uint8, channels=3 (blue, green, red)
    RGBA = "RGBA"  # dtype=uint8, channels=4 (red, green, blue, alpha)
    BGRA = "BGRA"  # dtype=uint8, channels=4 (blue, green, red, alpha)
    HSV = "HSV"  # dtype=uint8, channels=3 (hue, saturation, value)
    LAB = "LAB"  # dtype=uint8, channels=3 (lightness, a*, b*)

    def has_alpha(self):
        """Indicate whether the ColorSpace has an alpha channel.

        Currently, only RGBA and BGRA spaces have an alpha channel.

        Returns:
            True if the ColorSpace has an alpha channel, else False.
        """
        return self in [ColorSpace.BGRA, ColorSpace.RGBA]

    def has_color(self):
        """Indicate whether the ColorSpace has color channels.

        Currently, only BINARY and GRAYSCALE spaces don't have color channels.

        Returns:
            True if the ColorSpace has color channels, else False.
        """
        return self in [
            ColorSpace.BGR,
            ColorSpace.RGB,
            ColorSpace.BGRA,
            ColorSpace.RGBA,
            ColorSpace.HSV,
            ColorSpace.LAB,
        ]


class Image:
    """Class representing an image loaded as a numpy array using OpenCV.

    An Image object has a ColorSpace attribute, in order to keep track of
    what is the order of its channels, mainly to avoid bad usage of BGR vs RGB
    in our workers. It provides convenient methods to convert from  the original
    color space to another target color space, also dealing with alpha channels,
    and provides some additional properties (e.g. height and width) not
    accessible in numpy array interface.

    Attributes:
        _array: the image as a numpy array
        _space: the color space of the image
    """

    def __init__(self, array: np.ndarray, space: ColorSpace):
        """Initialize an Image object.

        Args:
            array: the image as a numpy array
            space: the color space of the image
        """
        self._array = array
        self._space = space

    @property
    def height(self) -> int:
        """Return the height of the image.

        Returns:
            the height of the image
        """
        return self.shape[0]

    @property
    def width(self) -> int:
        """Return the width of the image.

        Returns:
            the width of the image
        """
        return self.shape[1]

    @property
    def channels(self) -> int:
        """Return the number of channels of the image.

        Returns:
            the number of channels of the image
        """
        if len(self.shape) <= 2:
            return 1
        return self.shape[2]

    @property
    def space(self) -> ColorSpace:
        """Return the color space of the image.

        Returns:
            the color space of the image
        """
        return self._space

    @property
    def array(self) -> np.ndarray:
        """Return the array representing the image.

        Returns:
            the array representing the image
        """
        return self._array

    def convert_color(
        self,
        target_space: ColorSpace,
    ) -> "Image":
        """Converts the color space of the current image.

        If the target color space is the same as the current image color space,
        the image itself is returned without modification.

        Args:
            target_space: target color space

        Returns:
            a new image with the requested ColorSpace, or the same image when
            target color space matches the current image color space
        """
        if target_space == self._space:
            return self
        mode = f"COLOR_{self._space.value}2{target_space.value}"
        converted_array = cv2.cvtColor(self._array, getattr(cv2, mode))
        return Image(converted_array, target_space)

    def crop(self, bounding_box: BoundingBox) -> "Image":
        """Crop a bounding box from the image, and return the cropped image.

        Args:
            bounding_box: Bounding box containing the coordinates of the
                sub-image to crop.
            relative: If true, the coordinates are considered relative to the
                image coordinates and must be floats between 0 and 1. Else,
                they are considered absolute coordinates and are rounded to
                the nearest integers.
        Returns:
            the cropped image
        Raises:
            ValueError: if the bounding box is invalid
        """
        bounding_box = bounding_box.clip(self.width, self.height)

        return Image(
            self._array[
                int(round(bounding_box.top)) : int(round(bounding_box.bottom)),
                int(round(bounding_box.left)) : int(round(bounding_box.right)),
                ...,
            ],
            self._space,
        )

    def __getattr__(self, item: str) -> tp.Any:
        return getattr(self._array, item)

    def resize(
        self,
        height: int = 0,
        width: int = 0,
        max_side: int = 0,
        interpolation: int = cv2.INTER_AREA,
    ) -> "Image":
        """Return a resized image.

        The method will return a new image.

        Args:
            height: target height, deduced automatically if <=0.
            width: target width, deduced automatically if <=0.
            max_side: maximum value for height or width, ignored if <=0.
            interpolation: specify the interpolation method to use.
                (default to INTER_AREA method)

        Returns:
            the resized image, in a new Image object
        Raises:
            ValueError: if no valid args are passed
        """
        if height > 0 and width <= 0:
            width = math.ceil(
                float(self.width) * (float(height) / float(self.height))
            )
        elif height <= 0 and width > 0:
            height = math.ceil(
                float(self.height) * (float(width) / float(self.width))
            )
        elif max_side > 0:
            width, height = self.width, self.height
        elif not (width > 0 and height > 0):
            raise ValueError(
                "A positive int value for at least one argument is needed"
            )
        if max_side > 0:
            ratio = 1.0
            if height > max_side:
                ratio = max_side / height
                height = max_side
                width = round(width * ratio)
            if width > max_side:
                ratio = max_side / width
                width = max_side
                height = round(ratio * height)
        return Image(
            cv2.resize(
                self.array, dsize=(width, height), interpolation=interpolation
            ),
            self.space,
        )

    def rotate90(self, angle: tp.Optional[int]) -> "Image":
        """Rotate the image by multiples of 90° counter-clockwise.

        Args:
            angle: the rotation angle, which must be a multiple of 90°. If 0°
                or None is given, a copy of the image is returned.
        """
        if angle is None or angle % 360 == 0:
            return Image(self.array.copy(), self.space)
        assert angle is not None
        if angle % 90:
            raise ValueError(
                f"The angle parameter must be a multiple of 90°, got {angle}."
            )
        angle = angle % 360
        angle_to_cv2_arg = {
            90: cv2.ROTATE_90_COUNTERCLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_CLOCKWISE,
        }
        return Image(cv2.rotate(self.array, angle_to_cv2_arg[angle]), self.space)

    @staticmethod
    def guess_space(image: np.ndarray) -> ColorSpace:
        """Guess the color space used by the numpy array just after reading.

        Args:
            image: the array loaded by OpenCV's imread or imdecode

        Returns:
            the guessed color space
        """
        if len(image.shape) == 2:
            if image.dtype == "bool":
                return ColorSpace.BINARY
            if image.dtype == "uint8":
                return ColorSpace.GRAYSCALE
        elif len(image.shape) == 3:
            if image.shape[2] == 3:
                return ColorSpace.BGR
            if image.shape[2] == 4:
                return ColorSpace.BGRA

        raise RuntimeError(
            f"Cannot guess color space of image with shape={image.shape} "
            f"and dtype={image.dtype}."
        )

    @staticmethod
    def read(
        filename: str,
        space: ColorSpace = ColorSpace.BGR,
        ignore_orientation: bool = True,
    ) -> "Image":
        """Read an image file using OpenCV, and return an Image object.

        Args:
            filename: path to the image file or content to decode
            space: target color space of the loaded image
            ignore_orientation: if True, ignores the orientation flag
                in EXIF metadata; else it is used to rotate the image
                accordingly. Defaults to True.

        Returns:
            the read Image object

        Raises:
            FileNotFoundError: when the image does not exist
            RuntimeError: when the image cannot be read by OpenCV
        """
        return Image._decode(filename, space, ignore_orientation)

    def write(self, filename: str, params: tp.Optional[tp.List] = None) -> None:
        """Write an image file using OpenCV.

        The image format is guessed from the filename extension. Additional
        encoding parameters may be given, see OpenCV ImwriteFlags for details.

        Args:
            filename: path to the image file
            params: format-specific parameters encoded as pairs, like
                (paramId_1, paramValue_1, paramId_2, paramValue_2, ... .).
        """
        if params is None:
            params = []
        cv2.imwrite(filename, self.array, params)

    def base64encode(self, format: str = "png") -> str:
        """Encode an image in base64 format.

        Args:
            format: image format (default is png)
        """
        _, buffer = cv2.imencode(f".{format}", self.array)
        encoded = base64.b64encode(buffer)
        encoded_str = encoded.decode("ascii")
        mime = f"data:image/{format};base64"
        return f"{mime},{encoded_str}"
    
    @staticmethod
    def base64decode(encoded_str: str) -> "Image":
        """Decode an image in base64 format.

        Args:
            encoded_str: the base64 encoded image
        """
        # _, buffer = cv2.imencode(f".{format}", self.array)
        _, encoded_image = encoded_str.split(",")
        encoded_buffer = encoded_image.encode("ascii")
        decoded_buffer = base64.b64decode(encoded_buffer)
        return Image.from_buffer(decoded_buffer)

    @staticmethod
    def from_buffer(
        buffer: bytes,
        space: ColorSpace = ColorSpace.BGR,
        ignore_orientation: bool = True,
        background=WHITE,
    ) -> "Image":
        """Read a buffer containing image data, and return an Image object.

        Args:
            buffer: buffer containing image data. Must have a uint8 data type.
            space: target color space of the loaded image
            ignore_orientation: if True, ignores the orientation flag
                in EXIF metadata; else it is used to rotate the image
                accordingly. Defaults to True.
            background: background color to use to blend with transparent
                zones, when loading images with alpha channel in color spaces
                not supporting alpha (BINARY, GRAYSCALE, BGR, RGB).

        Returns:
            the read Image object

        Raises:
            FileNotFoundError: when the image does not exist
            RuntimeError: when the image cannot be read by OpenCV
        """
        return Image._decode(buffer, space, ignore_orientation, background)

    @staticmethod
    def _decode(
        data: tp.Union[str, bytes],
        space: ColorSpace = ColorSpace.BGR,
        ignore_orientation: bool = True,
        background=WHITE,
    ) -> "Image":
        """Load an image using OpenCV, from file or bytes; return Image object.

        Args:
            data: filename or byte array to decode
            space: target color space of the loaded image
            ignore_orientation: if True, ignores the orientation flag
                in EXIF metadata; else it is used to rotate the image
                accordingly. Defaults to True.
            background: background color to use to blend with transparent
                zones, when loading images with alpha channel in color spaces
                not supporting alpha (BINARY, GRAYSCALE, BGR, RGB).

        Returns:
            the read Image object

        Raises:
            FileNotFoundError: when the image does not exist
            RuntimeError: when the image cannot be read by OpenCV
        """
        if isinstance(data, str):
            if not os.path.exists(data):
                raise FileNotFoundError(f"Image file {data} does not exist")

        if space in [ColorSpace.HSV, ColorSpace.LAB]:
            raise NotImplementedError(
                f"Cannot create an image from {space} source for now."
            )

        if space.has_color() and space.has_alpha():
            if not ignore_orientation:
                raise RuntimeError(
                    "Loading images with alpha channel and using EXIF "
                    "orientation tag is currently impossible."
                )
            flags = cv2.IMREAD_UNCHANGED
        elif space.has_color():
            flags = cv2.IMREAD_COLOR
        else:
            flags = cv2.IMREAD_GRAYSCALE

        if ignore_orientation:
            flags = flags | cv2.IMREAD_IGNORE_ORIENTATION
        if isinstance(data, bytes):
            array: np.ndarray = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), flags)
        else:
            array = cv2.imread(data, flags)

        if array is None:
            raise RuntimeError("Image cannot be loaded by OpenCV")

        guessed_space = Image.guess_space(array)
        image = Image(array, guessed_space)
        if guessed_space != space:
            return image.convert_color(space)

        return image

    def show(
        self,
        window_name: str = "Image",
        destroy_on_exit: bool = True,
        blocking: bool = True,
    ):
        """Show an image.

        Args:
            window_name: Name of the window to show image
            destroy_on_exit: True to destroy the window after the function.
            blocking: True to make the call to this function blocking.
        """
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, self.array)
        if blocking:
            cv2.waitKey()
        if destroy_on_exit:
            cv2.destroyWindow(window_name)


def load_document(
    filepath: str, space=ColorSpace.BGR, ignore_orientation=True
) -> Image:
    """Load a document into the Image format.

    It supports loading images with alpha channel (in BGRA color space), and
    ignoring image orientation in Exif metadata. 

    Args:
        filepath: the path to the file to load
        space: the ColorSpace of the resulting loaded image
        ignore_orientation: if True, ignores the orientation flag in EXIF
            metadata; else it is used to rotate the image accordingly.
            Defaults to True.

    Returns:
        the corresponding loaded image
    """
    if space == ColorSpace.BGRA and not ignore_orientation:
        img = Image.read(
            filepath,
            space=ColorSpace.BGR,
            ignore_orientation=ignore_orientation,
        )
        return img.convert_color(ColorSpace.BGRA)
    return Image.read(
        filepath,
        space=space,
        ignore_orientation=ignore_orientation,
    )
