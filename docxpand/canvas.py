"""Helper functions to manipulate Inkscape SVG content.

Original version can be found at https://github.com/letuananh/pyinkscape

@author: Le Tuan Anh <tuananh.ke@gmail.com>
@license: MIT
"""

# Copyright (c) 2017, Le Tuan Anh <tuananh.ke@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

########################################################################

import logging
import os
import typing as tp
from xml.dom.minidom import Element

from lxml import etree
from lxml.etree import XMLParser

_BLANK_CANVAS = os.path.join(os.path.dirname(os.path.realpath(__file__)), "blank.svg")

logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.INFO)

INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
SVG_NS = "http://www.w3.org/2000/svg"
SVG_NAMESPACES = {
    "ns": SVG_NS,
    "svg": SVG_NS,
    "dc": "http://purl.org/dc/elements/1.1/",
    "cc": "http://creativecommons.org/ns#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
    "inkscape": INKSCAPE_NS,
}
XLINK_NS = "http://www.w3.org/1999/xlink"


class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


class Dimension:
    def __init__(self, width, height):
        self.width = width
        self.height = height


class BBox:
    """A bounding box represents by a top-left anchor (x1, y1) and a dimension (width, height)"""

    def __init__(self, x, y, width, height):
        self._anchor = Point(x, y)
        self._dimension = Dimension(width, height)

    @property
    def width(self):
        """Width of the bounding box"""
        return self._dimension.width

    @property
    def height(self):
        """Height of the bounding box"""
        return self._dimension.height


class Canvas:
    """This class represents an Inkscape drawing page (i.e. a SVG file)."""

    def __init__(self, filepath=tp.Optional[str], *args, **kwargs):
        """Create a new blank canvas or read from an existing file.

        To create a blank canvas, just ignore the filepath property.
        >>> c = Canvas()

        To open an existing file, use
        >>> c = Canvas("/path/to/file.svg")

        Arguments:
            filepath: Path to an existing SVG file.
        """
        self._filepath = filepath
        self._tree = None
        self._root = None
        self._units = "mm"
        self._width = 0
        self._height = 0
        self._viewbox = None
        self._scale = 1.0
        self._elem_group_map = {}
        self._elements_by_ids = {}
        if filepath is not None:
            self._load_file(*args, **kwargs)

    def _load_file(self, remove_blank_text=True, encoding="utf-8", **kwargs):
        with open(
            _BLANK_CANVAS if not self._filepath else self._filepath,
            encoding=encoding,
        ) as infile:
            kwargs["remove_blank_text"] = remove_blank_text  # lxml specific
            parser = XMLParser(**kwargs)
            self._tree = etree.parse(infile, parser)
            self._root = self._tree.getroot()
            self._update_svg_info()

    def _update_svg_info(self):
        # load SVG information
        if self._svg_node.get("viewBox"):
            self._viewbox = BBox(
                *(float(x) for x in self._svg_node.get("viewBox").split())
            )
            if not self._width:
                self._width = self._viewbox.width
            if not self._height:
                self._width = self._viewbox.height
        if self.viewBox and self._width:
            self._scale = self.viewBox.width / self._width

    @property
    def _svg_node(self):
        return self._root

    @property
    def viewBox(self):
        return self._viewbox

    def to_xml_string(self, encoding="utf-8", pretty_print=True, **kwargs):
        return etree.tostring(
            self._root,
            encoding=encoding,
            pretty_print=pretty_print,
            **kwargs,
        ).decode("utf-8")

    def _xpath_query(self, query_string, namespaces=None):
        return self._root.xpath(query_string, namespaces=namespaces)

    def element_by_id(self, id: str) -> tp.Optional[Element]:
        """Get one XML element by its ID.

        Arguments:
            id: the ID of the element

        Raises:
            RuntimeError: when more than two elements share the exact same ID
        """
        elements = self._xpath_query(f".//ns:*[@id='{id}']", namespaces=SVG_NAMESPACES)
        if not elements:
            return None
        if len(elements) > 1:
            raise RuntimeError(f"Found {len(elements)} elements with the same id {id}")
        return elements[0]

    def render(self, outpath, overwrite=False, encoding="utf-8"):
        if not overwrite and os.path.isfile(outpath):
            logger.warning(f"File {outpath} exists. SKIPPED")
        else:
            output = self.to_xml_string(pretty_print=False)
            with open(outpath, mode="w", encoding=encoding) as outfile:
                outfile.write(output)
                logger.info("Written output to {}".format(outfile.name))
