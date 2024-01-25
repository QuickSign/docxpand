import os
import typing as tp

from docxpand.image import Image 

SPECIMENS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "specimens"
)

def load_specimen(specimen_name: str) -> tp.Optional[Image]:
    """Load document Prado specimen by name.

    Args:
        subtype: document classification subtype
        side: document classification side

    Returns:
         specimen image or None if it is not found
    """
    try:
        specimen_path = os.path.join(
            SPECIMENS_DIR,
            f"{specimen_name.lower().replace('_', '-')}.jpg",
        )
        if not os.path.exists(specimen_path):
            print(f"{specimen_path} not found")
            return None
        specimen_img = Image.read(specimen_path)
        return specimen_img
    except Exception:
        return None
