from rapidfuzz.distance import Levenshtein
from shapely.geometry import Polygon

from docxpand.geometry import Quadrangle


def iou(quad_detected: Quadrangle, quad_ground_truth: Quadrangle):
    """Calculate iou between two quadrangles."""
    polygon_detected = Polygon(quad_detected)
    polygon_ground_truth = Polygon(quad_ground_truth)
    polygon_intersection = polygon_detected.intersection(
        polygon_ground_truth
    ).area
    polygon_union = polygon_detected.union(polygon_ground_truth).area
    if polygon_union:
        return polygon_intersection / polygon_union
    else:
        return 0


def character_error_rate(prediction: str, ground_truth: str):
    """Calculate character error rate between two strings."""
    return Levenshtein.distance(prediction, ground_truth) / len(ground_truth)
