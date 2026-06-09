"""The configuration-driven tool registry.

This is the single source of truth for what tools exist and how they behave.
The frontend renders every tool dynamically from these configs — there is NO
per-tool hardcoded UI or hardcoded backend route. To add a tool:

    1. Append a ToolConfig to TOOLS below.
    2. Register its processor with @register("<slug>") in the matching *_tools.py.

The architecture is designed to scale from 50 tools to 500+ unchanged.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import Enum

# --- Categories -------------------------------------------------------------


@dataclass(frozen=True)
class Category:
    slug: str
    name: str
    description: str
    icon: str


CATEGORIES: list[Category] = [
    Category("pdf-tools", "PDF Tools", "Merge, split, convert and manage PDF files.", "file-text"),
    Category("image-tools", "Image Tools", "Compress, convert, resize and edit images.", "image"),
    Category("text-tools", "Text Tools", "Count, convert, sort and transform text.", "type"),
    Category("developer-tools", "Developer Tools", "Format, minify, encode and generate.", "code"),
]


# --- Tool input declarations ------------------------------------------------


class InputKind(str, Enum):
    file = "file"          # one or more uploaded files
    text = "text"          # a textarea / text input
    options = "options"    # settings panel fields (handled via `options`)


class OptionType(str, Enum):
    select = "select"
    number = "number"
    text = "text"
    boolean = "boolean"
    color = "color"


@dataclass
class Option:
    key: str
    label: str
    type: OptionType
    default: object = None
    choices: list[str] = field(default_factory=list)
    min: float | None = None
    max: float | None = None


@dataclass
class ToolConfig:
    name: str
    slug: str
    category: str
    description: str
    seo_keywords: list[str] = field(default_factory=list)
    how_to_use: list[str] = field(default_factory=list)

    # Capabilities — drive the dynamically rendered UI.
    input_kind: InputKind = InputKind.file
    supports_single_upload: bool = True
    supports_multi_upload: bool = False
    supports_preview: bool = True
    supports_download: bool = True
    supports_zip_download: bool = False
    supports_reset: bool = True
    supports_background_edit: bool = False  # post-result background color/image editor
    client_side: bool = False  # processed entirely in the browser (no backend call)

    accepted_extensions: list[str] = field(default_factory=list)  # empty = any
    max_upload_mb: int | None = None  # per-tool size cap; None = global default
    options: list[Option] = field(default_factory=list)

    def public_dict(self) -> dict:
        d = asdict(self)
        d["input_kind"] = self.input_kind.value
        for opt in d["options"]:
            opt["type"] = opt["type"].value if isinstance(opt["type"], OptionType) else opt["type"]
        return d


# --- Processor result -------------------------------------------------------


@dataclass
class ResultFile:
    token: str        # filename token within /tmp/results, used for download
    name: str         # display / download filename
    size: int
    mime: str


@dataclass
class ToolResult:
    """Returned by every processor. Either text output, files, or both."""

    text: str | None = None
    files: list[ResultFile] = field(default_factory=list)
    meta: dict = field(default_factory=dict)  # arbitrary stats for preview (counts, etc.)

    def public_dict(self) -> dict:
        return {
            "text": self.text,
            "files": [asdict(f) for f in self.files],
            "meta": self.meta,
        }


# A processor receives uploaded file paths, raw text, and parsed options.
Processor = Callable[..., ToolResult]


# --- The registry ----------------------------------------------------------

REGISTRY: dict[str, ToolConfig] = {}
PROCESSORS: dict[str, Processor] = {}


def define(config: ToolConfig) -> None:
    if config.slug in REGISTRY:
        raise ValueError(f"Duplicate tool slug: {config.slug}")
    REGISTRY[config.slug] = config


def register(slug: str) -> Callable[[Processor], Processor]:
    """Decorator binding a processor function to a tool slug."""

    def wrapper(fn: Processor) -> Processor:
        PROCESSORS[slug] = fn
        return fn

    return wrapper


def get_tool(slug: str) -> ToolConfig | None:
    return REGISTRY.get(slug)


def get_processor(slug: str) -> Processor | None:
    return PROCESSORS.get(slug)


def list_tools(category: str | None = None) -> list[ToolConfig]:
    tools = list(REGISTRY.values())
    if category:
        tools = [t for t in tools if t.category == category]
    return sorted(tools, key=lambda t: t.name)


def list_categories() -> list[Category]:
    return CATEGORIES


# ---------------------------------------------------------------------------
# TOOL DEFINITIONS
# Processors with implementations live in the *_tools.py modules. Tools listed
# here without an implemented processor are surfaced by the API as "coming soon"
# so the full 50+ catalogue is visible while implementations land incrementally.
# ---------------------------------------------------------------------------


def _opt(*args, **kwargs) -> Option:
    return Option(*args, **kwargs)


# ---- PDF TOOLS ----
define(ToolConfig(
    name="PDF Merge", slug="pdf-merge", category="pdf-tools",
    description="Combine multiple PDF files into a single document.",
    seo_keywords=["Merge PDF Online", "Combine PDF Files", "Join PDF Documents"],
    how_to_use=["Upload PDFs", "Arrange order", "Click Merge", "Download file"],
    supports_single_upload=False, supports_multi_upload=True, accepted_extensions=["pdf"],
))
define(ToolConfig(
    name="PDF Split", slug="pdf-split", category="pdf-tools",
    description="Split a PDF into separate pages or extract a page range.",
    seo_keywords=["Split PDF Online", "Extract PDF Pages", "Separate PDF Pages"],
    how_to_use=["Upload PDF", "Select pages", "Split PDF", "Download result"],
    accepted_extensions=["pdf"], supports_zip_download=True,
    options=[
        _opt("ranges", "Page range (e.g. 1-3,5)", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="PDF Rotate", slug="pdf-rotate", category="pdf-tools",
    description="Rotate all pages of a PDF by 90, 180 or 270 degrees.",
    seo_keywords=["Rotate PDF Online", "Turn PDF Pages"],
    how_to_use=["Upload PDF", "Choose angle", "Rotate", "Download"],
    accepted_extensions=["pdf"],
    options=[_opt("angle", "Rotation", OptionType.select, default="90", choices=["90", "180", "270"])],
))
define(ToolConfig(
    name="PDF Extract Pages", slug="pdf-extract-pages", category="pdf-tools",
    description="Pull a selection of pages out of a PDF into a new file.",
    seo_keywords=["Extract PDF Pages", "Get Pages From PDF"],
    how_to_use=["Upload PDF", "Enter pages", "Extract", "Download"],
    accepted_extensions=["pdf"],
    options=[_opt("ranges", "Pages (e.g. 2-4,7)", OptionType.text, default="1")],
))
define(ToolConfig(
    name="PDF Metadata Viewer", slug="pdf-metadata-viewer", category="pdf-tools",
    description="Inspect title, author, page count and other PDF metadata.",
    seo_keywords=["PDF Metadata", "PDF Info Viewer"],
    how_to_use=["Upload PDF", "View metadata"],
    accepted_extensions=["pdf"], supports_download=False,
))
define(ToolConfig(
    name="PDF Compress", slug="pdf-compress", category="pdf-tools",
    description="Reduce PDF file size by compressing streams and cleaning unused objects.",
    seo_keywords=["Compress PDF Online", "Reduce PDF Size", "Shrink PDF"],
    how_to_use=["Upload PDF", "Click Compress", "Download smaller PDF"],
    accepted_extensions=["pdf"],
))
define(ToolConfig(
    name="PDF To JPG", slug="pdf-to-jpg", category="pdf-tools",
    description="Render each page of a PDF to a JPG or PNG image.",
    seo_keywords=["PDF to JPG", "Convert PDF to Image"],
    how_to_use=["Upload PDF", "Choose format and quality", "Convert", "Download images"],
    accepted_extensions=["pdf"], supports_zip_download=True,
    options=[
        _opt("format", "Image format", OptionType.select, default="jpg", choices=["jpg", "png"]),
        _opt("dpi", "Resolution (DPI)", OptionType.number, default=150, min=72, max=400),
    ],
))
define(ToolConfig(
    name="JPG To PDF", slug="jpg-to-pdf", category="pdf-tools",
    description="Combine one or more images into a single PDF document.",
    seo_keywords=["JPG to PDF", "Image to PDF", "Convert JPG to PDF"],
    how_to_use=["Upload images", "Arrange order", "Convert", "Download PDF"],
    supports_single_upload=False, supports_multi_upload=True,
    accepted_extensions=["jpg", "jpeg", "png", "webp"],
))
define(ToolConfig(
    name="Word To PDF", slug="word-to-pdf", category="pdf-tools",
    description="Convert a Word (.docx) document to PDF (text content).",
    seo_keywords=["Word to PDF", "DOCX to PDF Converter"],
    how_to_use=["Upload .docx", "Convert", "Download PDF"],
    accepted_extensions=["docx"],
))
define(ToolConfig(
    name="PDF To Word", slug="pdf-to-word", category="pdf-tools",
    description="Extract the text of a PDF into an editable Word (.docx) document.",
    seo_keywords=["PDF to Word", "PDF to DOCX Converter"],
    how_to_use=["Upload PDF", "Convert", "Download .docx"],
    accepted_extensions=["pdf"],
))
define(ToolConfig(
    name="PDF Unlock", slug="pdf-unlock", category="pdf-tools",
    description="Remove password protection from a PDF you own.",
    seo_keywords=["Unlock PDF", "Remove PDF Password"],
    how_to_use=["Upload PDF", "Enter password", "Unlock", "Download"],
    accepted_extensions=["pdf"],
    options=[_opt("password", "PDF password", OptionType.text, default="")],
))
define(ToolConfig(
    name="PDF Protect", slug="pdf-protect", category="pdf-tools",
    description="Add password protection (encryption) to a PDF.",
    seo_keywords=["Protect PDF", "Password Protect PDF", "Encrypt PDF"],
    how_to_use=["Upload PDF", "Set a password", "Protect", "Download"],
    accepted_extensions=["pdf"],
    options=[_opt("password", "New password", OptionType.text, default="")],
))
define(ToolConfig(
    name="PDF Watermark", slug="pdf-watermark", category="pdf-tools",
    description="Stamp a text watermark diagonally across every page.",
    seo_keywords=["Watermark PDF", "Add Watermark to PDF"],
    how_to_use=["Upload PDF", "Enter watermark text", "Apply", "Download"],
    accepted_extensions=["pdf"],
    options=[
        _opt("text", "Watermark text", OptionType.text, default="CONFIDENTIAL"),
        _opt("opacity", "Opacity %", OptionType.number, default=15, min=5, max=80),
    ],
))
define(ToolConfig(
    name="PDF Organizer", slug="pdf-organizer", category="pdf-tools",
    description="Reorder or keep a subset of PDF pages (e.g. 3,1,2 or 1-2,5).",
    seo_keywords=["Organize PDF Pages", "Reorder PDF", "Rearrange PDF"],
    how_to_use=["Upload PDF", "Enter new page order", "Apply", "Download"],
    accepted_extensions=["pdf"],
    options=[_opt("order", "Page order (e.g. 3,1,2)", OptionType.text, default="")],
))
define(ToolConfig(
    name="PDF Page Numbering", slug="pdf-page-numbering", category="pdf-tools",
    description="Add page numbers to every page of a PDF.",
    seo_keywords=["Add Page Numbers to PDF", "Number PDF Pages"],
    how_to_use=["Upload PDF", "Choose position", "Apply", "Download"],
    accepted_extensions=["pdf"],
    options=[_opt("position", "Position", OptionType.select, default="bottom-center",
                  choices=["bottom-center", "bottom-right", "bottom-left"])],
))


# ---- IMAGE TOOLS ----
define(ToolConfig(
    name="Image Compressor", slug="image-compressor", category="image-tools",
    description="Compress JPG, PNG and WebP images while keeping good quality.",
    seo_keywords=["Compress Image Online", "Reduce Image Size", "Free Image Compressor", "Image Optimizer"],
    how_to_use=["Upload image", "Select compression level", "Click Compress", "Download optimized image"],
    supports_multi_upload=True, supports_zip_download=True,
    accepted_extensions=["jpg", "jpeg", "png", "webp"],
    options=[_opt("quality", "Quality", OptionType.number, default=70, min=10, max=95)],
))
define(ToolConfig(
    name="Image Resize", slug="image-resize", category="image-tools",
    description="Resize images to exact pixel dimensions.",
    seo_keywords=["Resize Image Online", "Change Image Dimensions"],
    how_to_use=["Upload image", "Set width and height", "Resize", "Download"],
    accepted_extensions=["jpg", "jpeg", "png", "webp"],
    options=[
        _opt("width", "Width (px)", OptionType.number, default=800, min=1, max=10000),
        _opt("height", "Height (px)", OptionType.number, default=600, min=1, max=10000),
        _opt("keep_aspect", "Keep aspect ratio", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Image Rotate", slug="image-rotate", category="image-tools",
    description="Rotate an image by a chosen angle.",
    seo_keywords=["Rotate Image Online"],
    how_to_use=["Upload image", "Choose angle", "Rotate", "Download"],
    accepted_extensions=["jpg", "jpeg", "png", "webp"],
    options=[_opt("angle", "Rotation", OptionType.select, default="90", choices=["90", "180", "270"])],
))
define(ToolConfig(
    name="JPG To PNG", slug="jpg-to-png", category="image-tools",
    description="Convert JPG images to PNG format.",
    seo_keywords=["JPG to PNG", "Convert JPG to PNG Online"],
    how_to_use=["Upload JPG", "Convert", "Download PNG"],
    supports_multi_upload=True, supports_zip_download=True, accepted_extensions=["jpg", "jpeg"],
))
define(ToolConfig(
    name="PNG To JPG", slug="png-to-jpg", category="image-tools",
    description="Convert PNG images to JPG format.",
    seo_keywords=["PNG to JPG", "Convert PNG to JPG Online"],
    how_to_use=["Upload PNG", "Convert", "Download JPG"],
    supports_multi_upload=True, supports_zip_download=True, accepted_extensions=["png"],
))
define(ToolConfig(
    name="PNG To WEBP", slug="png-to-webp", category="image-tools",
    description="Convert PNG images to modern WebP format.",
    seo_keywords=["PNG to WebP", "Convert to WebP"],
    how_to_use=["Upload PNG", "Convert", "Download WebP"],
    supports_multi_upload=True, supports_zip_download=True, accepted_extensions=["png"],
))
define(ToolConfig(
    name="WEBP To PNG", slug="webp-to-png", category="image-tools",
    description="Convert WebP images to PNG format.",
    seo_keywords=["WebP to PNG", "Convert WebP"],
    how_to_use=["Upload WebP", "Convert", "Download PNG"],
    supports_multi_upload=True, supports_zip_download=True, accepted_extensions=["webp"],
))
define(ToolConfig(
    name="Image Metadata Viewer", slug="image-metadata-viewer", category="image-tools",
    description="View EXIF and basic metadata of an image.",
    seo_keywords=["Image Metadata", "EXIF Viewer"],
    how_to_use=["Upload image", "View metadata"],
    accepted_extensions=["jpg", "jpeg", "png", "webp"], supports_download=False,
))
define(ToolConfig(
    name="Image To Base64", slug="image-to-base64", category="image-tools",
    description="Convert an image into a Base64 data URI.",
    seo_keywords=["Image to Base64", "Base64 Image Encoder"],
    how_to_use=["Upload image", "Copy Base64 string"],
    accepted_extensions=["jpg", "jpeg", "png", "webp", "gif"], supports_download=False,
))
define(ToolConfig(
    name="QR Code Generator", slug="qr-code-generator", category="image-tools",
    description="Generate a QR code from any text or URL.",
    seo_keywords=["QR Code Generator", "Free QR Maker", "Online QR Generator"],
    how_to_use=["Enter URL", "Customize design", "Generate QR", "Download"],
    input_kind=InputKind.text, supports_single_upload=False,
    options=[
        _opt("fill_color", "Foreground color", OptionType.color, default="#000000"),
        _opt("back_color", "Background color", OptionType.color, default="#ffffff"),
        _opt("box_size", "Size", OptionType.number, default=10, min=4, max=40),
    ],
))
define(ToolConfig(
    name="Image Crop", slug="image-crop", category="image-tools",
    description="Crop an image to a chosen rectangle.",
    seo_keywords=["Crop Image Online", "Image Cropper"],
    how_to_use=["Upload image", "Set crop box", "Crop", "Download"],
    accepted_extensions=["jpg", "jpeg", "png", "webp"],
    options=[
        _opt("x", "X (px)", OptionType.number, default=0, min=0, max=20000),
        _opt("y", "Y (px)", OptionType.number, default=0, min=0, max=20000),
        _opt("width", "Width (px)", OptionType.number, default=400, min=1, max=20000),
        _opt("height", "Height (px)", OptionType.number, default=400, min=1, max=20000),
    ],
))
define(ToolConfig(
    name="Image Watermark", slug="image-watermark", category="image-tools",
    description="Add a text watermark to one or more images.",
    seo_keywords=["Watermark Image", "Add Watermark to Photo"],
    how_to_use=["Upload images", "Enter watermark text", "Apply", "Download"],
    supports_multi_upload=True, supports_zip_download=True,
    accepted_extensions=["jpg", "jpeg", "png", "webp"],
    options=[
        _opt("text", "Watermark text", OptionType.text, default="© Toolkit Pro"),
        _opt("position", "Position", OptionType.select, default="bottom-right",
             choices=["bottom-right", "bottom-left", "top-right", "top-left", "center"]),
        _opt("opacity", "Opacity %", OptionType.number, default=50, min=10, max=100),
    ],
))
define(ToolConfig(
    name="Background Remover", slug="background-remover", category="image-tools",
    description="Remove an image background with AI — runs privately in your browser.",
    seo_keywords=["Background Remover", "Remove Image Background", "AI Background Remover"],
    how_to_use=["Upload image", "Click Remove", "Add a background (optional)", "Download PNG"],
    supports_single_upload=True, supports_multi_upload=False, supports_background_edit=True,
    accepted_extensions=["jpg", "jpeg", "png", "webp"], max_upload_mb=10,
    client_side=True,
    options=[],
))
define(ToolConfig(
    name="Base64 To Image", slug="base64-to-image", category="image-tools",
    description="Decode a Base64 string or data URI back into an image file.",
    seo_keywords=["Base64 to Image", "Decode Base64 Image"],
    how_to_use=["Paste Base64 / data URI", "Decode", "Download image"],
    input_kind=InputKind.text, supports_single_upload=False,
))
define(ToolConfig(
    name="Barcode Generator", slug="barcode-generator", category="image-tools",
    description="Generate a barcode (Code128, Code39, EAN-13) from text.",
    seo_keywords=["Barcode Generator", "Free Barcode Maker"],
    how_to_use=["Enter value", "Choose type", "Generate", "Download"],
    input_kind=InputKind.text, supports_single_upload=False,
    options=[_opt("type", "Barcode type", OptionType.select, default="code128",
                  choices=["code128", "code39", "ean13"])],
))


# ---- TEXT TOOLS ----
define(ToolConfig(
    name="Word Counter", slug="word-counter", category="text-tools",
    description="Count words, characters, sentences, paragraphs and reading time.",
    seo_keywords=["Word Counter", "Character Counter", "Text Counter"],
    how_to_use=["Paste text", "View statistics"],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
))
define(ToolConfig(
    name="Character Counter", slug="character-counter", category="text-tools",
    description="Count characters with and without spaces.",
    seo_keywords=["Character Counter", "Letter Count"],
    how_to_use=["Paste text", "View character count"],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
))
define(ToolConfig(
    name="Case Converter", slug="case-converter", category="text-tools",
    description="Convert text between upper, lower, title and sentence case.",
    seo_keywords=["Case Converter", "Uppercase Lowercase Converter"],
    how_to_use=["Paste text", "Choose case", "Convert", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
    options=[_opt("mode", "Case", OptionType.select, default="upper",
                  choices=["upper", "lower", "title", "sentence"])],
))
define(ToolConfig(
    name="Duplicate Line Remover", slug="duplicate-line-remover", category="text-tools",
    description="Remove duplicate lines from a block of text.",
    seo_keywords=["Remove Duplicate Lines", "Dedupe Text"],
    how_to_use=["Paste text", "Remove duplicates", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
    options=[_opt("case_sensitive", "Case sensitive", OptionType.boolean, default=False)],
))
define(ToolConfig(
    name="Text Sorter", slug="text-sorter", category="text-tools",
    description="Sort lines of text alphabetically, ascending or descending.",
    seo_keywords=["Sort Text Lines", "Alphabetize Text"],
    how_to_use=["Paste text", "Choose order", "Sort", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
    options=[_opt("order", "Order", OptionType.select, default="asc", choices=["asc", "desc"])],
))
define(ToolConfig(
    name="Text Reverser", slug="text-reverser", category="text-tools",
    description="Reverse text by characters, words, or lines.",
    seo_keywords=["Reverse Text", "Backwards Text Generator"],
    how_to_use=["Paste text", "Choose mode", "Reverse", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
    options=[_opt("mode", "Reverse by", OptionType.select, default="characters",
                  choices=["characters", "words", "lines"])],
))
define(ToolConfig(
    name="URL Encoder", slug="url-encoder", category="text-tools",
    description="Percent-encode text for safe use in URLs.",
    seo_keywords=["URL Encoder", "Percent Encode"],
    how_to_use=["Paste text", "Encode", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
))
define(ToolConfig(
    name="URL Decoder", slug="url-decoder", category="text-tools",
    description="Decode percent-encoded URL text.",
    seo_keywords=["URL Decoder", "Percent Decode"],
    how_to_use=["Paste encoded text", "Decode", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
))
define(ToolConfig(
    name="Lorem Ipsum Generator", slug="lorem-ipsum-generator", category="text-tools",
    description="Generate placeholder Lorem Ipsum paragraphs.",
    seo_keywords=["Lorem Ipsum Generator", "Placeholder Text"],
    how_to_use=["Choose paragraph count", "Generate", "Copy result"],
    input_kind=InputKind.options, supports_single_upload=False, supports_preview=True,
    options=[_opt("paragraphs", "Paragraphs", OptionType.number, default=3, min=1, max=50)],
))
define(ToolConfig(
    name="Random Text Generator", slug="random-text-generator", category="text-tools",
    description="Generate random strings of a chosen length.",
    seo_keywords=["Random Text Generator", "Random String"],
    how_to_use=["Choose length", "Generate", "Copy result"],
    input_kind=InputKind.options, supports_single_upload=False,
    options=[_opt("length", "Length", OptionType.number, default=32, min=1, max=2000)],
))


# ---- DEVELOPER TOOLS ----
define(ToolConfig(
    name="JSON Formatter", slug="json-formatter", category="developer-tools",
    description="Pretty-print and indent JSON.",
    seo_keywords=["JSON Formatter", "JSON Beautifier"],
    how_to_use=["Paste JSON", "Format", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
    options=[_opt("indent", "Indent", OptionType.number, default=2, min=0, max=8)],
))
define(ToolConfig(
    name="JSON Validator", slug="json-validator", category="developer-tools",
    description="Validate JSON and report syntax errors.",
    seo_keywords=["JSON Validator", "JSON Lint"],
    how_to_use=["Paste JSON", "Validate"],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
))
define(ToolConfig(
    name="JSON Minifier", slug="json-minifier", category="developer-tools",
    description="Minify JSON by removing whitespace.",
    seo_keywords=["JSON Minifier", "Compress JSON"],
    how_to_use=["Paste JSON", "Minify", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
))
define(ToolConfig(
    name="Base64 Encoder", slug="base64-encoder", category="developer-tools",
    description="Encode text to Base64.",
    seo_keywords=["Base64 Encoder", "Encode Base64 Online"],
    how_to_use=["Paste text", "Encode", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
))
define(ToolConfig(
    name="Base64 Decoder", slug="base64-decoder", category="developer-tools",
    description="Decode Base64 back to text.",
    seo_keywords=["Base64 Decoder", "Decode Base64 Online"],
    how_to_use=["Paste Base64", "Decode", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
))
define(ToolConfig(
    name="UUID Generator", slug="uuid-generator", category="developer-tools",
    description="Generate one or more random UUID v4 values.",
    seo_keywords=["UUID Generator", "GUID Generator"],
    how_to_use=["Choose count", "Generate", "Copy result"],
    input_kind=InputKind.options, supports_single_upload=False,
    options=[_opt("count", "How many", OptionType.number, default=1, min=1, max=500)],
))
define(ToolConfig(
    name="Password Generator", slug="password-generator", category="developer-tools",
    description="Generate strong random passwords.",
    seo_keywords=["Password Generator", "Strong Password Maker"],
    how_to_use=["Choose length and options", "Generate", "Copy result"],
    input_kind=InputKind.options, supports_single_upload=False,
    options=[
        _opt("length", "Length", OptionType.number, default=16, min=4, max=128),
        _opt("symbols", "Include symbols", OptionType.boolean, default=True),
        _opt("digits", "Include digits", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="CSS Minifier", slug="css-minifier", category="developer-tools",
    description="Minify CSS by stripping comments and whitespace.",
    seo_keywords=["CSS Minifier", "Compress CSS Online"],
    how_to_use=["Paste CSS", "Minify", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
))
define(ToolConfig(
    name="JS Minifier", slug="js-minifier", category="developer-tools",
    description="Basic JavaScript minifier (removes comments and extra whitespace).",
    seo_keywords=["JS Minifier", "JavaScript Minifier"],
    how_to_use=["Paste JavaScript", "Minify", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
))
define(ToolConfig(
    name="HTML Formatter", slug="html-formatter", category="developer-tools",
    description="Pretty-print and indent HTML.",
    seo_keywords=["HTML Formatter", "HTML Beautifier"],
    how_to_use=["Paste HTML", "Format", "Copy result"],
    input_kind=InputKind.text, supports_single_upload=False,
    options=[_opt("indent", "Indent", OptionType.number, default=2, min=0, max=8)],
))
