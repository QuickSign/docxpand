"""Module defining Bounding Box for images.

There is some type: ignore because of the use of NamedTuple. See
https://github.com/python/mypy/issues/4507.
"""

import typing as tp

import cv2

"""Module defining points."""

import math
import typing as tp

import numpy as np


class Point(tp.NamedTuple):
    """Defines a point."""

    x: float
    y: float

    @staticmethod
    def from_dict(input_dict: tp.Dict[str, tp.Union[str, float]]) -> "Point":
        """Import point from a dict.

        Args:
            input_dict: dict containing point information

        Returns:
            Point with information found in dict

        Raises:
            RuntimeError: Dictionary doesn't have information to create a point
        """
        return Point(*[float(input_dict[key]) for key in Point._fields])

    def to_dict(self) -> tp.Dict[str, float]:
        """Export point to a dict.

        Returns:
            dict containing point information
        """
        return {key: getattr(self, key) for key in self._fields}

    def distance(self, other_point: "Point") -> float:
        """Compute the distance between two points.

        Args:
            other_point: second point

        Returns:
            distance between two points

        Raises:
            RuntimeError: the two points have not the same dimension
        """
        return math.sqrt(sum((px - qx) ** 2.0 for px, qx in zip(self, other_point)))


class Segment(tp.NamedTuple):
    """Defines a segment."""

    p1: Point
    p2: Point

    @property
    def length(self) -> float:
        """Return the length af the segment.

        Returns:
            length of the segment
        """
        dist: float = self.p1.distance(self.p2)
        return dist


class Quadrangle(tp.NamedTuple):
    r"""Define a quadrangle (i.e. a quadrilateral).

    It may represent convex quadrangles, such as :
          p1 ------ p2
        /             \
      /                \
    p4 --------------- p3

    Concave quadrangles are supported too, such as this one :
          p1
        /   \
      /  p3  \
    p4⸍     ⸌ p2

    Finally, crossed quadrangles are also allowed, such as this one :
          p1 -- p2
           \  ⸍
          ⸍ \
      p3 -- p4

    A quadrangle is either convex, concave or crossed but can't be of two types
    at the same time.
    """

    p1: Point
    p2: Point
    p3: Point
    p4: Point

    @staticmethod
    def from_dict(
        input_dict: tp.Dict[str, tp.Union[Point, tp.Dict[str, tp.Union[str, float]]]]
    ) -> "Quadrangle":
        """Import quadrangle from a dict.

        Args:
            input_dict: dict containing quadrangle information

        Returns:
            quadrangle with information found in dict

        Raises:
            RuntimeError: Dictionary doesn't have information to create a
            quadrangle
        """
        return Quadrangle(
            *[
                input_dict[key]
                if isinstance(input_dict[key], Point)
                else Point.from_dict(input_dict[key])
                for key in Quadrangle._fields
            ]
        )

    def to_dict(self) -> tp.Dict[str, tp.Dict[str, float]]:
        """Export quadrangle to a dict.

        Returns:
            dict containing quadrangle information
        """
        return {key: getattr(self, key).to_dict() for key in self._fields}

    def guess_aspect_ratio(
        self, img_width: float, img_height: float, epsilon=0.01
    ) -> tp.Optional[float]:
        """Estimate the aspect ratio of a rectangle viewed by a mobile camera.

        This is used to get back the aspect ratio of a rectangular zone
        (most probably a random paper document). It is based on "Whiteboard
        Scanning and Image Enhancement". The numbers between parentheses in
        comments refer to equations of this paper.

        Args:
            img_width: width of the image containing the quadrangle
            img_height: height of the image containing the quadrangle
            epsilon: tolerance for sides parallelism

        Returns:
            aspect ratio of the rectangle when the perspective is corrected
        """
        # Original image center
        half_w = img_width / 2.0
        half_h = img_height / 2.0

        # Translate quadrangle points and make 3-d vectors (x, y, 1)
        # The ordering of points 3 and 4 is not the same between our codebase
        # and the paper, hence the inversion.
        point_1, point_2, point_4, point_3 = [
            np.array([point.x - half_w, point.y - half_h, 1], dtype=float)
            for point in self
        ]

        # (11) - (12)
        coeff_2 = np.cross(point_1, point_4).dot(point_3) / np.cross(
            point_2, point_4
        ).dot(point_3)
        coeff_3 = np.cross(point_1, point_4).dot(point_2) / np.cross(
            point_3, point_4
        ).dot(point_2)
        if math.isinf(coeff_2) or math.isinf(coeff_3):
            return None

        # (14) - (16)
        vec_2 = coeff_2 * point_2 - point_1
        vec_3 = coeff_3 * point_3 - point_1
        if (vec_2[2] == 0) and (vec_3[2] == 0):
            # Parallelogram case, the aspect ratio can be derived directly
            return math.sqrt(vec_2.dot(vec_2) / vec_3.dot(vec_3))

        if (abs(vec_2[2]) < epsilon) or (abs(vec_3[2]) < epsilon):
            # At least two sides are almost parallel,
            # so the computation of f is not reliable
            width_1 = self.p1.distance(self.p2)
            width_2 = self.p3.distance(self.p4)
            height_1 = self.p1.distance(self.p4)
            height_2 = self.p2.distance(self.p3)

            def estimate_parallel_sides_length(side1, side2):
                min_s = min(side1, side2)
                max_s = max(side1, side2)
                return min_s + pow((min_s / max_s), 4) * (max_s - min_s)

            return_value: float
            if abs(vec_2[2]) < epsilon:
                # "Horizontal" sides are almost parallel
                average_h = (height_1 + height_2) / 2.0
                estimated_w = estimate_parallel_sides_length(width_1, width_2)
                return_value = estimated_w / average_h
                return return_value

            # "Vertical" sides are almost parallel
            average_w = (width_1 + width_2) / 2.0
            estimated_h = estimate_parallel_sides_length(height_1, height_2)
            return_value = average_w / estimated_h
            return return_value

        # General case
        f_squared = abs(
            (-1.0 / (vec_2[2] * vec_3[2])) * (vec_2[0] * vec_3[0] + vec_2[1] * vec_3[1])
        )
        vec_2_norm = (
            vec_2[0] * vec_2[0] + vec_2[1] * vec_2[1] + vec_2[2] * vec_2[2] * f_squared
        )
        vec_3_norm = (
            vec_3[0] * vec_3[0] + vec_3[1] * vec_3[1] + vec_3[2] * vec_3[2] * f_squared
        )
        return math.sqrt(vec_2_norm / vec_3_norm)

    def clip(
        self,
        max_x: float,
        max_y: float,
        min_x: float = 0,
        min_y: float = 0,
    ) -> "Quadrangle":
        """Clips x coords in (min_x, max_x) and y coords in (min_y, max_y).

        Args:
            max_x: maximum allowed x coordinate
            max_y: maximum allowed y coordinate
            min_x: minimum allowed x coordinate (default: 0)
            min_y: minimum allowed y coordinate (default: 0)
        """
        return Quadrangle(
            *[
                Point(np.clip(p.x, min_x, max_x), np.clip(p.y, min_y, max_y))
                for p in self
            ]
        )

    def rescale(
        self,
        image_width: float,
        image_height: float,
    ) -> "Quadrangle":
        """Rescale a quadrangle with [0;1] coordinates to original coordinates.

        Args:
            quad: original quadrangle
            image_width: original image width
            image_height: original image height

        Returns:
            Rescaled quadrangle.
        """
        quad = Quadrangle(
            *[
                Point(int(p.x * image_width), int(p.y * image_height))
                for p in self
            ]
        )
        return quad.clip(image_width, image_height)

    def enlarge(
        self,
        margins: tp.Union[float, tp.Tuple[float, float, float, float]],
        viewport: tp.Tuple[float, float],
        target_width: float = 720
    ) -> "Quadrangle":
        """Add some margin to a quadrangle.

        Args:
            margins: if a single float is provided, adds/removes a margin with
                this value to each coordinate; if four floats are provided as a
                tuple (margin_left, margin_top, margin_right, margin_bottom), adds
                each margin to the corresponding coordinate
            viewport: the two floats provided as tuple (max_x, max_y) are used to
                clip the resulting Quadrangle
            target_width : target width (720 by default)

        Raises:
            ValueError: when margins or viewport argument has unsupported type
                or has a wrong size

        Returns:
            the enlarged BoundingBox (with margins applied)
        """
        if not isinstance(viewport, tuple) or len(viewport) != 2:
            raise ValueError(
                f"The viewport {viewport} has unsupported type or has wrong size."
            )
        max_x, max_y = viewport


        if isinstance(margins, float):
            margin_left, margin_top, margin_right, margin_bottom = (margins,) * 4
        elif isinstance(margins, tuple):
            if len(margins) != 4:
                raise ValueError(f"The margins tuple {margins} has a wrong size")
            margin_left, margin_top, margin_right, margin_bottom = margins
        else:
            raise ValueError(f"The margins {margins} has unsupported type")

        # Intermediate width used to compute temp quads
        homography, target_height = estimate_homography_without_target(
            self, max_x, max_y, target_width
        )

        # Process relative margins
        margin_left = (
            margin_left * target_width
            if 0 < margin_left < 1
            else margin_left
        )
        margin_top = (
            margin_top * target_height
            if 0 < margin_top < 1
            else margin_top
        )
        margin_right = (
            margin_right * target_width
            if 0 < margin_right < 1
            else margin_right
        )
        margin_bottom = (
            margin_bottom * target_height
            if 0 < margin_bottom < 1
            else margin_bottom
        )

        # Create quad with margin
        quad = Quadrangle(
            Point(-margin_left, -margin_top),
            Point(target_width + margin_right, -margin_top),
            Point(target_width + margin_right, target_height + margin_bottom),
            Point(-margin_left, target_height + margin_bottom),
        )
        return project_quad_back_to_original_image(quad, homography, to_int=True)

    def get_sides(self) -> tp.Tuple[Segment, Segment, Segment, Segment]:
        """Return the four sides of the perspective rectangle.

        Returns:
            a tuple containing the four segments that compose the perspective
            rectangle
        """
        return (
            Segment(self.p1, self.p2),
            Segment(self.p2, self.p3),
            Segment(self.p3, self.p4),
            Segment(self.p4, self.p1),
        )

    def _get_corresponding_sides(self, length=True) -> tp.Tuple[Segment, Segment]:
        """Return a pair of corresponding sides.

        Args:
            length: if True, return the length sides, else return the width
                sides

        Returns:
            a tuple containing a pair of corresponding sides
        """
        sides = self.get_sides()
        if (sides[0].length + sides[2].length) > (
            sides[1].length + sides[3].length
        ):
            if length:
                return (sides[0], sides[2])
            return (sides[1], sides[3])
        if length:
            return (sides[1], sides[3])
        return (sides[0], sides[2])
    
    def get_length_sides(self) -> tp.Tuple[Segment, Segment]:
        """Return the pair of length sides.

        Returns:
            a tuple containing the pair of length sides
        """
        return self._get_corresponding_sides(True)

    def get_width_sides(self) -> tp.Tuple[Segment, Segment]:
        """Return the pair of width sides.

        Returns:
            a tuple containing the pair of width sides
        """
        return self._get_corresponding_sides(False)

    def estimate_length(self) -> float:
        """Estimate the length of the perspective rectangle.

        Returns:
            an estimation of the length of the perspective rectangle
        """
        sides = self.get_length_sides()
        estimated_length: float = (sides[0].length + sides[1].length) / 2
        return estimated_length

    def estimate_width(self) -> float:
        """Estimate the width of the perspective rectangle.

        Returns:
            an estimation of the width of the perspective rectangle
        """
        sides = self.get_width_sides()
        estimated_width: float = (sides[0].length + sides[1].length) / 2
        return estimated_width


class BoundingBox(tp.NamedTuple):
    """Class that defines a bounding box (non-oriented rectangle) for images.

    Attributes:
        top_left: top left point of bounding box
        bottom_right: bottom right point of bounding box
    """

    top_left: Point
    bottom_right: Point

    @staticmethod
    def from_dict(
        input_dict: tp.Dict[str, tp.Union[Point, tp.Dict[str, tp.Union[str, float]]]]
    ) -> "BoundingBox":
        """Import bounding box from a dict.

        Args:
            input_dict: dict containing bounding box information

        Returns:
            bounding box with information found in dict

        Raises:
            RuntimeError: Dictionary doesn't have information to create a bounding
            box
        """
        return BoundingBox(
            *[
                input_dict[key]
                if isinstance(input_dict[key], Point)
                else Point.from_dict(input_dict[key])
                for key in BoundingBox._fields
            ]
        )

    def to_dict(self) -> tp.Dict[str, tp.Dict[str, float]]:
        """Export bounding box to a dict.

        Returns:
            dict containing quadrangle information
        """
        return {key: getattr(self, key).to_dict() for key in self._fields}

    @property
    def right(self) -> float:
        """Get right coordinate of bounding box.

        Returns:
            right coordinate of bounding box
        """
        return self.bottom_right.x  # type:ignore

    @property
    def left(self) -> float:
        """Get left coordinate of bounding box.

        Returns:
            left coordinate of bounding box
        """
        return self.top_left.x  # type:ignore

    @property
    def top(self) -> float:
        """Get top coordinate of bounding box.

        Returns:
            top coordinate of bounding box
        """
        return self.top_left.y  # type:ignore

    @property
    def bottom(self) -> float:
        """Get right coordinate of bounding box.

        Returns:
            right coordinate of bounding box_bottom
        """
        return self.bottom_right.y  # type:ignore

    @property
    def width(self) -> float:
        """Get width of bounding box (distance between right and left).

        Returns:
            width of bounding box (distance between right and left)
        """
        return self.right - self.left

    @property
    def height(self) -> float:
        """Get height of bounding box (distance between top and bottom).

        Returns:
            height of bounding box (distance between top and bottom)
        """
        return self.bottom - self.top

    def clip(
        self,
        max_x: float,
        max_y: float,
        min_x: float = 0,
        min_y: float = 0,
    ) -> "BoundingBox":
        """Clips x coords in (min_x, max_x) and y coords in (min_y, max_y).

        Args:
            max_x: maximum allowed x coordinate
            max_y: maximum allowed y coordinate
            min_x: minimum allowed x coordinate (default: 0)
            min_y: minimum allowed y coordinate (default: 0)
        """
        top_left = Point(max(self.left, min_x), max(self.top, min_y))
        bottom_right = Point(min(self.right, max_x), min(self.bottom, max_y))
        return BoundingBox(top_left, bottom_right)

    def union(self, other_bbox: "BoundingBox") -> tp.Optional["BoundingBox"]:
        """Create a new BoundingBox formed by the union of two boxes.

        Beware, this method does not produce the union of the two boxes in the
        common topological sense, but rather the bounding box of the two boxes.

        If the union is empty, which is only possible when the two bounding
        boxes are the exact same "empty" bouding boxes (=points), return None.

        Args:
            other_bbox: another bounding box to union with the current box

        Returns:
            the bounding box unioned from the current box and another one, or
            None when the union is empty
        """
        left = min(self.left, other_bbox.left)
        top = min(self.top, other_bbox.top)
        right = max(self.right, other_bbox.right)
        bottom = max(self.bottom, other_bbox.bottom)

        union_bbox = BoundingBox(Point(left, top), Point(right, bottom))
        return None if union_bbox.is_empty() else union_bbox
    
    def enlarge(
        self,
        margins: tp.Union[float, tp.Tuple[float, float, float, float]],
        viewport: tp.Tuple[float, float]
    ) -> "BoundingBox":
        """Add some margin to a bounding box.

        Args:
            margins: if a single float is provided, adds/removes a margin with
                this value to each coordinate; if four floats are provided as a
                tuple (margin_left, margin_top, margin_right, margin_bottom), adds
                each margin to the corresponding coordinate
            viewport: the two floats provided as tuple (max_x, max_y) are used to
                clip the resulting BoundingBox

        Raises:
            ValueError: when margins or viewport argument has unsupported type
                or has a wrong size

        Returns:
            the enlarged BoundingBox (with margins applied)
        """
        if not isinstance(viewport, tuple) or len(viewport) != 2:
            raise ValueError(
                f"The viewport {viewport} has unsupported type or has wrong size."
            )
        max_x, max_y = viewport
    
        if isinstance(margins, float):
            margin_left, margin_top, margin_right, margin_bottom = (margins,) * 4
        elif isinstance(margins, tuple):
            if len(margins) != 4:
                raise ValueError(f"The margins tuple {margins} has a wrong size")
            margin_left, margin_top, margin_right, margin_bottom = margins
        else:
            raise ValueError(f"The margins {margins} has unsupported type")

        bounding_box = BoundingBox(
            Point(self.left - margin_left, self.top - margin_top),
            Point(
                self.right + margin_right,
                self.bottom + margin_bottom,
            ),
        )

        bounding_box = bounding_box.clip(max_x, max_y)

        return bounding_box

    def is_empty(self) -> bool:
        """Check is the bounding box is empty (i.e area <= 0).

        Returns:
            True if the bounding box is empty
        """
        return self.left >= self.right or self.top >= self.bottom

    @staticmethod
    def from_quad(quad: Quadrangle) -> "BoundingBox":
        """Create a bounding box from a quadrangle.

        Args:
            quad: quadrangle containing 4 points

        Returns:
            the smallest bounding box containing those 4 points
        """
        return BoundingBox(
            Point(min(pt[0] for pt in quad), min(pt[1] for pt in quad)),
            Point(max(pt[0] for pt in quad), max(pt[1] for pt in quad)),
        )

    def to_quad(self) -> Quadrangle:
        """Create a quadrangle from bounding box.

        Returns:
            Quadrangle containing top-left, top-right, bottom-right and
            bottom-left points
        """
        return Quadrangle(
            Point(self.left, self.top),
            Point(self.right, self.top),
            Point(self.right, self.bottom),
            Point(self.left, self.bottom),
        )


def to_array(points: tp.Sequence[Point]) -> np.ndarray:
    """Transform points to array.

    Args:
        points: Points

    Returns:
        array with points coordinates
    """
    return np.array([[x, y] for x, y in points])


def estimate_doc_homography(
    source: Quadrangle,
    target: Quadrangle,
) -> np.ndarray:
    """Estimates document homography.

    Quadrangle ordering:
    p1 ------ p2
    |          |
    p4 ------ p3

    Args:
        source: source position of document
        target: target position of document
        orientation : orientation of document

    Returns:
        Homography and mask to transform source points to destinations points
    """
    # Convert to numpy arrays
    np_source = to_array(source)
    np_target = to_array(target)

    # Estimate homography. Using cv2.RANSAC algorithm could make it faster
    homography, _ = cv2.findHomography(np_source, np_target)
    return homography


def estimate_homography_without_target(
    quad: Quadrangle,
    image_width: float,
    image_height: float,
    target_width: float = 720,
):
    """Estimate homography without clear idea of output size.

    It will use a 720 pixel target width by default.

    Args:
        quad: original quad you want to transform
        image_width: width of original image in 
        image_height: height of original image to keep ratio
        target_width : target width (720 by default)

    Returns:
        Homography to transform the quadrangle to a quadrangle
         of target_width, and the associated target height
    """
    ratio = quad.guess_aspect_ratio(image_width, image_height)
    target_height = int(target_width / ratio)
    target_quad = Quadrangle(
        Point(0, 0),
        Point(target_width, 0),
        Point(target_width, target_height),
        Point(0, target_height),
    )
    # Computing transform
    # Homography to transform corners to template
    homography = estimate_doc_homography(quad, target_quad)
    return homography, target_height


def project_quad_to_target_image(
    quadrangle: Quadrangle,
    homography: np.ndarray,
    to_int: bool = False,
) -> Quadrangle:
    """Project a quadrangle to the target image.

    Args:
        quadrangle: quadrangle to project
        homography: homography from original image to new image
        to_int: if True, casts coordinates to integers, else leave them as floats

    Returns:
        Quadrangle corresponding to the projection in the target image.
    """
    np_points_bbox = np.float32([[[pt.x, pt.y] for pt in quadrangle]])
    projected_bbox = cv2.perspectiveTransform(np_points_bbox, homography)[0]
    if to_int:
        pts_bbox = [Point(int(p[0]), int(p[1])) for p in projected_bbox]
    else:
        pts_bbox = [Point(*p) for p in projected_bbox]
    return Quadrangle(*pts_bbox)


def project_quad_back_to_original_image(
    quadrangle: Quadrangle,
    homography: np.ndarray,
    to_int: bool = False,
) -> Quadrangle:
    """Project a quadrangle to the original image.

    Args:
        quadrangle: quadrangle to project
        homography: homography from original image to new image
        to_int: if True, casts coordinates to integers, else leave them as floats


    Returns:
        Quadrangle corresponding to the projection in the original image.
    """
    return project_quad_to_target_image(
        quadrangle, np.linalg.inv(homography), to_int
    )
