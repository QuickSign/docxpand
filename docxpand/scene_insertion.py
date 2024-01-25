import datetime
import getpass
import logging
import os
import random
import typing as tp
import tqdm

import cv2
import numpy as np
from deepface import DeepFace

from docxpand.dataset import DocFakerDataset
from docxpand.geometry import (
    BoundingBox, Point, Quadrangle, estimate_doc_homography,
    estimate_homography_without_target
)
from docxpand.image import ColorSpace, Image, load_document
from docxpand.specimen import load_specimen
from docxpand.svg_to_image import SVGRenderer
from docxpand.utils import guess_mimetype


logger = logging.getLogger(__name__)

# To clip the illumination correction, in order to keep only flashes and
# intense lights, and avoid keeping too large darkness difference because it
# tends to paste photos.
ILLUMINATION_CORRECTION_MIN_MAX_FACE = (0.9, 3.0, 1.5)


def rectify_document(
    image: Image,
    quad: Quadrangle,
    target_width: int = 720,
) -> Image:
    """Rectify document using its localization and the specified target width.

    Args:
        image: image containing the document
        quad: quadrangle localizing the document (with its four corners)
        target_width: width of the rectified image

    Returns:
         rectified image, original quadrangle, homography
    """
    homography, target_height = estimate_homography_without_target(
        quad, image.width, image.height, target_width
    )

    # Rectify the perspective
    rectified_array = cv2.warpPerspective(
        image.array, homography, (target_width, target_height),
        borderMode=cv2.BORDER_REPLICATE
    )

    return Image(rectified_array, Image.guess_space(rectified_array))


def color_transfer_reinhard(
    scene: Image, specimen: Image, document: Image
) -> Image:
    """Transfers the color distribution from the scene to the document image.

    It uses the mean and standard deviations in the L*a*b* color space.

    This implementation is partially based on to the "Color Transfer between
    Images" paper by Reinhard et al., 2001.

    Inspired by https://github.com/chia56028/Color-Transfer-between-Images.

    Args:
        scene: scene image
        specimen: specimen image
        document: document image

    Return:
        document image with transfered color distribution from scene
    """
    alpha_channel = document.array[:, :, 3] if document.channels == 4 else None

    def get_mean_and_std(img: np.ndarray) -> tp.Tuple[np.ndarray, np.ndarray]:
        img_mean, img_std = cv2.meanStdDev(img)
        img_mean = np.hstack(np.around(img_mean, 2))
        img_std = np.hstack(np.around(img_std, 2))
        return img_mean, img_std

    scene_lab = cv2.cvtColor(scene.array, cv2.COLOR_BGR2LAB)
    specimen_lab = cv2.cvtColor(specimen.array, cv2.COLOR_BGR2LAB)
    document_lab = cv2.cvtColor(document.array, cv2.COLOR_BGR2LAB)

    s_mean, s_std = get_mean_and_std(scene_lab)
    sp_mean, sp_std = get_mean_and_std(specimen_lab)
    _, _, channel = document_lab.shape
    for k in range(channel):
        ch_k = document_lab[:, :, k]
        ch_k = ((ch_k - sp_mean[k]) * (s_std[k] / sp_std[k])) + s_mean[k]
        # round or +0.5
        ch_k = np.round(ch_k)
        # boundary check
        ch_k = np.clip(ch_k, 0, 255)
        document_lab[:, :, k] = ch_k

    result_arr = cv2.cvtColor(document_lab, cv2.COLOR_LAB2BGR)
    if alpha_channel is not None:
        result_arr = np.concatenate(
            (result_arr, alpha_channel[:, :, np.newaxis]), axis=2
        )
    result_img = Image(array=result_arr, space=Image.guess_space(result_arr))
    return result_img


def detect_faces(image: Image) -> tp.List[BoundingBox]:
    """Detect faces on an image.
    
    Args:
        image: image on which the faces must be detected
    
    Returns:
        the list of BoundingBoxes containing faces
    """
    if image.space != ColorSpace.BGR:
        image = image.convert_color(ColorSpace.BGR)
    try:
        analysis = DeepFace.extract_faces(
            image.array,
            detector_backend="retinaface",
        )
    except:
        return []
    faces = []
    for result in analysis:
        region = result["facial_area"]
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
        bbox = bbox.clip(image.width, image.height)
        faces.append(bbox)
    return faces


def illumination_transfer(
    scene: Image,
    specimen: Image,
    document: Image,
    ksize: tp.Tuple[int, int] = (127, 127),
    sigma: float = 30.0,
    effect_power: float = 0.3
) -> Image:
    """Transfers the illumination from the scene to the document image.

    Args:
        scene: scene image
        specimen: specimen image
        document: document image
        ksize: gaussian blur kernel size
        sigma: gaussian blur variance
        effect_power: power of the effect of illumination transfer, between 0.0
          and 1.0

    Return:
        document image with transfered illumination from scene
    """
    alpha_channel = document.array[:, :, 3] if document.channels == 4 else None

    scene_lab = cv2.cvtColor(scene.array, cv2.COLOR_BGR2LAB)
    specimen_lab = cv2.cvtColor(specimen.array, cv2.COLOR_BGR2LAB)
    document_lab = cv2.cvtColor(document.array, cv2.COLOR_BGR2LAB)

    # Resize all luminosity channels to document size
    scene_lum = cv2.resize(
        scene_lab[:, :, 0],
        (document.width, document.height),
        interpolation=cv2.INTER_AREA
    )
    specimen_lum = cv2.resize(
        specimen_lab[:, :, 0],
        (document.width, document.height),
        interpolation=cv2.INTER_AREA
    )

    # Blur luminosity channels
    scene_lum = cv2.GaussianBlur(scene_lum, ksize, sigma)
    specimen_lum = cv2.GaussianBlur(specimen_lum, ksize, sigma)

    # Compute illumination correction.
    correction = scene_lum.astype("float32") / specimen_lum.astype("float32")
    corr_min, corr_max, corr_face_max = ILLUMINATION_CORRECTION_MIN_MAX_FACE
    correction = np.clip(correction, corr_min, corr_max) - 1.0

    # Detect photos and make the correction lighter in these regions
    faces = detect_faces(document)
    for face in faces:
        patch = correction[
            int(face.top):int(face.bottom),int(face.left):int(face.right)
        ]
        # Blur the correction even more
        patch = cv2.GaussianBlur(patch, ksize, sigma*4)
        # And clip it to lower values to avoid too much correction in the photo
        patch = np.clip(patch, corr_min - 1.0, corr_face_max - 1.0)
        correction[
            int(face.top):int(face.bottom),int(face.left):int(face.right)
        ] = patch

    # Apply correction
    document_lab[:, :, 0] = np.clip(
        document_lab[:, :, 0] + correction * effect_power * 255, 0, 255
    ).astype("uint8")

    result_arr = cv2.cvtColor(document_lab, cv2.COLOR_LAB2BGR)
    if alpha_channel is not None:
        result_arr = np.concatenate(
            (result_arr, alpha_channel[:, :, np.newaxis]), axis=2
        )
    result = Image(array=result_arr, space=Image.guess_space(result_arr))


    return result


def insert_image_in_background(
    background_img: Image,
    img_to_insert: Image,
    homography: np.ndarray,
    quad: Quadrangle,
) -> Image:
    """Insert image into the other image inside the quadrangle.

    Args:
        background_img: original image with the background
        img_to_insert: image to insert
        homography: homography to transform image corners to background position
        quad: original document quandrangle

    Returns:
        new image with inserted image on the origin bachground
    """
    inverted_img = cv2.warpPerspective(
        img_to_insert.array,
        homography,
        (background_img.width, background_img.height),
    )
    # convert foreground to BGR
    foreground = Image(inverted_img, Image.guess_space(inverted_img)).convert_color(
        ColorSpace.BGR
    )

    # Create alpha channel from original foreground alpha channel
    has_alpha = img_to_insert.space.has_alpha()
    background = background_img.convert_color(ColorSpace.BGR)
    alpha = (
        inverted_img[:, :, img_to_insert.channels - 1]
        if has_alpha
        else 255 * (inverted_img > 0).astype(np.uint8)
    )
    alpha = Image(alpha, ColorSpace.GRAYSCALE).convert_color(ColorSpace.BGR).array
    # Convert everything to float
    alpha_array = alpha.astype(float) / 255
    foreground_array = foreground.astype(float)
    background_array = background.astype(float)

    # Multiply the foreground with the alpha matte
    foreground_array = cv2.multiply(alpha_array, foreground_array)
    # Multiply the background with ( 1 - alpha_array )
    background_array = cv2.multiply(1.0 - alpha_array, background_array)

    # Add the masked foreground and background.
    out_image = cv2.add(foreground_array, background_array)

    final_img_arr = blur_document_edges(img_arr=out_image, quad=quad)

    final_img = Image(array=final_img_arr, space=Image.guess_space(final_img_arr))
    return final_img


def blur_document_edges(
    img_arr: np.ndarray,
    quad: Quadrangle,
    ksize: tp.Tuple[int, int] = (25, 25),
    sigma: float = 0.0
) -> np.array:
    """Add gaussian blur around the document edges.

    It helps integrating smoothly the document in the scene image, by hiding
    the image aliasing.

    Args:
        img_arr: image with inserted document
        quad: quadrangle around the document
        ksize: Gaussian kernel size for blurring

    Return:
        rectified image array with blurred boarders
    """
    blurred_arr = cv2.GaussianBlur(img_arr, ksize, sigma)
    height, width, channel = img_arr.shape
    mask = np.zeros((height, width, channel), dtype=np.uint8)
    edges_width = min(
        int((quad.p1.distance(quad.p2) + quad.p3.distance(quad.p4)) / 2 * 0.005),
        3,
    )
    pts = np.array(
        [
            [quad.p1.x, quad.p1.y],
            [quad.p2.x, quad.p2.y],
            [quad.p3.x, quad.p3.y],
            [quad.p4.x, quad.p4.y],
        ],
        np.int32,
    )
    pts = pts.reshape((-1, 1, 2))
    mask = cv2.polylines(mask, [pts], True, (255, 255, 255), edges_width)
    result_arr = np.where(mask != np.array([255, 255, 255]), img_arr, blurred_arr)
    return result_arr


def load_documents(
    document_dataset_filename: str,
    document_images_directory: str,
) -> tp.List[tp.Tuple[str, str, tp.Dict[str, tp.Any]]]:
    """Loading documents images.

    Args:
        document_images_directory: path to directory containing document images.
        dataset_path: path to dataset containing images information if wanted.

    Returns:
        List of loaded images with their document id, and the documents dataset.
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
        documents.append((image_path, doc_id, entry))
    return documents


def load_scenes(
    scene_dataset_filename: str,
    scene_images_directory: str,
) -> tp.List[tp.Tuple[str, str, tp.Dict[str, tp.Any]]]:
    """Loading scene images.

    Args:
        images_path : path to directory cointaining images.
        dataset_path : path to dataset containing images information if wanted.

    Returns:
        List of scene images with their positions where to put document image
        and their template, and the scenes dataset.
    """
    scenes = []
    dataset = DocFakerDataset(
        dataset_input=scene_dataset_filename, images_dir=scene_images_directory
    )
    progress = tqdm.tqdm(dataset.documents.items())
    progress.set_description("Loading scenes dataset")
    for doc_id, entry in progress:
        image_path = os.path.join(scene_images_directory, entry["filename"])
        quadrangle = Quadrangle.from_dict(entry["annotations"][0]["position"])
        specimen_name = entry["annotations"][0]["template"]
        scenes.append(
            (image_path, doc_id, quadrangle, specimen_name)
        )
    return scenes


def insert_generated_documents_in_scenes(
    document_dataset_filename: str,
    document_images_directory: str,
    scene_dataset_filename: str,
    scene_images_directory: str,
    renderer: tp.Optional[SVGRenderer],
    output_directory: str,
    margins: tp.Optional[float] = None,
    seed: tp.Optional[int] = None
) -> str:
    """Generate fake structured documents from an SVG template."""
    os.makedirs(os.path.abspath(output_directory), exist_ok=True)
    basename = os.path.basename(os.path.normpath(output_directory))
    output_dataset_filename = os.path.abspath(
        os.path.join(output_directory, f"{basename}.json")
    )
    if os.path.exists(output_dataset_filename):
        raise RuntimeError(
            f"A JSON dataset already exists in {output_directory}. "
            "Please set a new output directory, or remove the existing files."
        )

    # Read the document dataset, i.e documents that will be pasted in the
    # scenes.
    documents = load_documents(
        document_dataset_filename, document_images_directory
    )

    # Read the scene dataset, i.e scene images where the documents will be
    # pasted.
    scenes = load_scenes(
        scene_dataset_filename, scene_images_directory
    )

    # Shuffle the scenes dataset before starting.
    # Fix the seed to make it reproducible.
    if seed is not None:
        random.seed(seed)
    random.shuffle(scenes)

    # Initialize
    inserted_documents = []
    specimen_imgs = {}

    progress = tqdm.tqdm(range(len(documents)))
    progress.set_description("Inserting documents in scenes")
    for idx in progress:
        # Shuffle the scene images each time we have used them all
        if idx % len(scenes) == 0:
            random.shuffle(scenes)

        # Load or render document image
        doc_img_path, _, doc_entry = documents[idx]
        if guess_mimetype(doc_img_path) == 'image/svg+xml':
            if renderer is None:
                raise RuntimeError(
                    "Cannot process SVG images without a SVG renderer."
                )
            doc_img = renderer.render(filename=doc_img_path)
        else:
            doc_img = load_document(
                doc_img_path, space=ColorSpace.BGRA
            )

        # Load scene image
        scene_img_path, scene_id, scene_quad, specimen_name = scenes[
            idx % len(scenes)
        ]
        scene_img = load_document(
            scene_img_path, space=ColorSpace.BGRA, ignore_orientation=False
        )
        scene_quad = scene_quad.rescale(scene_img.width, scene_img.height)

        # Load specimen if not already loaded
        if specimen_name not in specimen_imgs:
            specimen_imgs[specimen_name] = load_specimen(specimen_name)

        try:
            # Rectification
            document_in_scene_image = rectify_document(scene_img, scene_quad)

            # Color transfer
            document_img_transferred = (
                color_transfer_reinhard(
                    scene=document_in_scene_image,
                    specimen=specimen_imgs[specimen_name],
                    document=doc_img
                )
            )

            # Illumination transfer
            document_img_transferred = illumination_transfer(
                scene=document_in_scene_image,
                specimen=specimen_imgs[specimen_name],
                document=document_img_transferred
            )

            # Insert document
            original_quad = Quadrangle(
                Point(0, 0),
                Point(doc_img.width, 0),
                Point(doc_img.width, doc_img.height),
                Point(0, doc_img.height),
            )
            if margins is not None:
                scene_quad = scene_quad.enlarge(
                    margins, (scene_img.width, scene_img.height)
                )
            homography = estimate_doc_homography(original_quad, scene_quad)
            inserted_img = insert_image_in_background(
                background_img=scene_img,
                img_to_insert=document_img_transferred,
                homography=homography,
                quad=scene_quad,
            )
            
            # Save result image
            output_basename, _ = os.path.splitext(
                os.path.basename(doc_entry["filename"])
            )
            doc_entry["filename"] = f"{output_basename}.jpg"
            inserted_img.write(
                os.path.join(output_directory, doc_entry["filename"])
            )

            # Update annotations
            annotation = doc_entry["annotations"][0]
            annotation["position"] = Quadrangle(
                *[
                    Point(p[0] / inserted_img.width, p[1] / inserted_img.height)
                    for p in scene_quad
                ]
            ).to_dict()
            if annotation["fields"]:
                for side in list(annotation["fields"].keys()):
                    if not doc_entry["_id"].endswith(side):
                        del annotation["fields"][side]
            annotation["scene_image"] = scene_id
            annotation["updated_at"] = (
                datetime.datetime.utcnow().isoformat()
            )
            inserted_documents.append(doc_entry)

        except Exception as err:
            logger.warning(
                f"Got an error while generating images ({type(err)}: {err}), "
                "continuing..."
            )
            continue

    dataset = DocFakerDataset(
        {
            "__class__": "DocFakerDataset",
            "documents": inserted_documents,
            "info": {
                "author": getpass.getuser(),
                "createdAt": datetime.datetime.utcnow().isoformat(),
                "description": (
                    f"Generated document images from document dataset "
                    f"{document_dataset_filename} and scene dataset "
                    f"{scene_dataset_filename}."
                ),
                "name": basename,
            },
        }
    )
    output_dataset_filename = os.path.join(output_directory, f"{basename}.json")
    dataset.save(output_dataset_filename)

    return output_dataset_filename
