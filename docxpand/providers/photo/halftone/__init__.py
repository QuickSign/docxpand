"""Largely inspired from https://github.com/GravO8/halftone. MIT LICENSE."""
import typing as tp
from math import ceil

import cv2
import numpy as np

from docxpand.image import Image


def halftone(
    image: Image,
    side: int = 20,
    jump: tp.Optional[int] = None,
    bg_color: tp.Tuple[int, int, int] = (255, 255, 255),
    fg_color: tp.Tuple[int, int, int] = (0, 0, 0),
    alpha: float = 1.4,
) -> Image:
    """Generate an half-tone image.

    Args:
        image: input image
        side: length (in pixels) of the side of each square that composes the
            output image (default is 20)
        jump: length (in pixels) of the side of each square the program will
            scan from original image (default is 1% of the minimum between
            the width and height)
        bg_color: rgb value of the background color of the output image
            (default is white)
        fg_color: rgb value of the color of the circles of the output image
            (default is black)
        alpha: coefficient that determines how big the circles can be; when
            alpha is 1, the maximum radius is side/2 (default is 1.4)

    Returns:
        the half-toned image
    """
    if side <= 0:
        raise ValueError(f"side must be strictly positive (got {side}).")
    if alpha <= 0:
        raise ValueError(f"alpha must be strictly positive (got {alpha}).")
    height, width = image.shape[:2]
    if jump is None:
        jump = ceil(min(height, height) * 0.01)
    if jump <= 0:
        raise ValueError(f"jump must be strictly positive (got {jump}).")
    bg_color = bg_color[::-1]
    fg_color = fg_color[::-1]

    height_output, width_output = side * ceil(height / jump), side * ceil(
        width / jump
    )
    canvas = np.zeros((height_output, width_output, 3), np.uint8)
    output_square = np.zeros((side, side, 3), np.uint8)

    x_output, y_output = 0, 0
    for y in range(0, height, jump):
        for x in range(0, width, jump):
            output_square[:] = bg_color
            intensity = 1 - np.mean(image[y : y + jump, x : x + jump]) / 255
            radius = int(alpha * intensity * side / 2)
            cv2.circle(
                output_square, (side // 2, side // 2), radius, fg_color, -1
            )
            canvas[
                y_output : y_output + side, x_output : x_output + side
            ] = output_square
            x_output += side
        y_output += side
        x_output = 0

    return canvas
