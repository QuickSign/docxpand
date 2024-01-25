"""Templates definition."""
import enum
import json
import os.path as osp
import typing as tp

TEMPLATES_DIR = osp.join(osp.dirname(__file__), "templates")


class FieldType(enum.Enum):
    """Enum class representing the field type.

    Attributes:
        FieldType.ADDRESS (int): an address field (composite places, zip, ...)
        FieldType.DATE (int): a date field
        FieldType.MRZ (int): a MRZ field
        FieldType.NAME (int): a name field
        FieldType.PHOTO (int): an identity photo, or a ghost image
        FieldType.TEXT (int): a generic text field
    """

    ADDRESS = 0
    DATE = 1
    MRZ = 2
    NAME = 3
    PHOTO = 4
    TEXT = 5

    @staticmethod
    def from_name(name: str) -> "FieldType":
        """Return the enum from its name (case-insensitive).

        Args:
            name: the name of the enum to return

        Returns:
            the corresponding enum

        Raises:
            ValueError: if the name doesn't correspond to a known enum.
        """
        return FieldType[name.upper()]


class Named:
    """Defines a named object.

    Attributes:
        _name: name of the object
    """

    def __init__(
        self,
        name: tp.Optional[str] = None,
    ) -> None:
        """Initialize a Named.

        Args:
            name: name of the object
        """
        self._name = name

    @property
    def name(self) -> str:
        """Property for name.

        Returns:
            name of the field position
        """
        assert self._name is not None
        return self._name

    @name.setter
    def name(self, value) -> None:
        self._name = value

    def fill_from_dict(self, dictionary: tp.Dict[str, tp.Any]) -> None:
        """Fill a named zone object from a dict.

        Args:
            dictionary: dict containing whole information
        """
        if "name" in dictionary:
            self.name = dictionary["name"]


class Field(Named):
    """Defines a field."""

    def __init__(
        self,
        name: tp.Optional[str] = None,
        field_type: tp.Optional[FieldType] = None,
        field_format: tp.Optional[str] = None,
        default: tp.Optional[str] = None,
        provider: tp.Optional[tp.Dict] = None,
        parts: tp.Optional[tp.Dict] = None,
        separator: tp.Optional[str] = None,
        max_chars_per_line: tp.Optional[int] = None,
        lines: tp.Optional[int] = None,
        conditional: tp.Optional[tp.Dict] = None
    ) -> None:
        """Initialize a Field."""
        super().__init__(name)
        self.type = field_type
        self.format = field_format
        self.default = default
        self.provider = provider
        self.parts = parts
        self.separator = separator
        self.max_chars_per_line = max_chars_per_line
        self.lines = lines
        self.conditional = conditional

    @staticmethod
    def from_dict(dictionary: tp.Dict[str, tp.Any]) -> "Field":
        """Create a field from a dict containing needed data.

        Args:
            dictionary: dict containing data

        Returns:
            field containing needed data
        """
        field = Field()
        super(Field, field).fill_from_dict(dictionary)
        for key, value in dictionary.items():
            if key not in ["name", "type"]:
                setattr(field, key, value)
            elif key == "type":
                field.type = FieldType.from_name(value)

        return field


class DocumentSide:
    """Defines a document side.

    Attributes:
        fields: fields to search
        template: path to the template vectorial (SVG) image
    """

    def __init__(self):
        """Initialize a DocumentSide."""
        self.fields: tp.List[Field] = []
        self.template: tp.Optional[str] = None
        self.translatable_labels: tp.List[str] = []

    @staticmethod
    def from_dict(dictionary: tp.Dict[str, tp.Any]) -> "DocumentSide":
        """Create a DocumentSide from a dict containing needed data.

        Args:
            dictionary: dict containing data

        Returns:
            DocumentSide containing needed data
        """
        side = DocumentSide()
        side.fields = [Field.from_dict(entry) for entry in dictionary.get("fields", [])]
        side.template = dictionary.get("template")
        side.translatable_labels = dictionary.get("translatable_labels", [])
        return side

    def get_field(self, name: str) -> Field:
        """Get back a field definition using its name.

        Args:
            name: the name of the field

        Returns:
            the field definition

        Raises:
            KeyError: when the requested field is not defined
        """
        for field in self.fields:
            if field.name == name:
                return field
        raise KeyError(f"No field definition found with name {name}.")


class DocumentTemplate(Named):
    """Defines a document template.

    Attributes:
        width: width of the template image
        height: height of template image
        dpi: dpi of the template image
        default_side: default side of document
        sides: possible sides of document
    """

    def __init__(
        self,
        name: tp.Optional[str] = None,
        size: tp.Optional[tp.Tuple[int, int]] = None,
        dpi: tp.Optional[int] = None,
        context: tp.Optional[tp.Dict] = None,
    ):
        """Initialize a DocumentTemplate.

        Args:
            name: name of the template
            size: (width, height) of the template image
            dpi: dpi of the template image
            context: list of context variables to generate prior to fields
        """
        self.name = name
        self.width = -1
        self.height = -1
        self.dpi = dpi if dpi else None
        self.context = context
        self.sides: tp.Dict[str, DocumentSide] = {}
        self.filename: tp.Optional[str] = None

        if size:
            try:
                self.width, self.height = size
            except Exception as err:
                raise ValueError(
                    "The given size doesn't have the form (width, height)"
                ) from err

    @staticmethod
    def from_dict(dictionary: tp.Dict[str, tp.Any]) -> "DocumentTemplate":
        """Create a DocumentTemplate from a dict containing needed data.

        Args:
            dictionary: dict containing data

        Returns:
            template containing needed data
        """
        template = DocumentTemplate()
        super(DocumentTemplate, template).fill_from_dict(dictionary)

        for key, value in dictionary.items():
            if key == "sides":
                for sub_key, sub_value in value.items():
                    template.sides[sub_key] = DocumentSide.from_dict(sub_value)
            elif key not in ["name"]:
                setattr(template, key, value)

        return template

    def search_field_side(self, name: str) -> str:
        """Get back the document side containing a field name.

        Args:
            name: the name of the field

        Returns:
            the field side

        Raises:
            KeyError: when the requested field is not defined
        """
        for side in self.sides:
            for field in self.sides[side].fields:
                if field.name == name:
                    return side
        raise KeyError(f"No field {name} found.")

    @staticmethod
    def load(filename: str) -> "DocumentTemplate":
        """Load the template from a file.

        Args:
            filename: path to the file containing the template description,
                or name of the file of an existing template in the packaged ones

        Returns:
            Loaded template
        """
        if not osp.exists(filename) and osp.exists(osp.join(TEMPLATES_DIR, filename)):
            filename = osp.join(TEMPLATES_DIR, filename)

        if osp.isdir(filename):
            filename = osp.join(filename, "generator.json")

        with open(filename, "r", encoding="utf-8") as f_in:
            data = json.load(f_in)

        template = DocumentTemplate.from_dict(data)

        # Set relative path from TEMPLATES_DIR to filename
        template.filename = osp.relpath(filename, TEMPLATES_DIR)

        return template
