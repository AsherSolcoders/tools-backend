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
    meta_title: str = ""
    meta_description: str = ""
    content: str = ""  # HTML shown on the category landing page


_PDF_CONTENT = """
<p>ToolSimpli's free online PDF tools give you everything you need to manage PDF files without installing any software. Whether you want to merge PDF files into one, split a PDF into smaller files, or compress a PDF to save storage space, our all in one PDF tools suite handles it in seconds, directly from your browser.</p>
<p>Working with documents often means switching between formats. Our platform lets you convert PDF to Word for easy editing, or use the convert Word to PDF tool to turn reports, resumes and contracts into a shareable, universally readable format. Need images instead? The convert PDF to JPG tool extracts pages as high quality images, while the convert JPG to PDF tool lets you combine photos or scanned pages into a single polished document.</p>
<p>Security and organization matter too. Add a PDF watermark to protect your brand or confidential material, password protect a PDF using our PDF protect tool, or organize PDF pages before sharing. Every tool runs quickly, works on desktop and mobile, and requires no sign-up, so you can get your files ready and move on with your day.</p>
<p>ToolSimpli is built as a free online PDF editor alternative for everyday tasks, with no watermarked downloads, no hidden fees, and no complicated menus. Files you upload are processed securely and are not stored longer than necessary, giving you peace of mind while you merge, split, compress or convert. Explore the full set of PDF tools below and find the one that fits your task in just a couple of clicks.</p>
"""

_IMAGE_CONTENT = """
<p>Images are everywhere on the web, and ToolSimpli's image tools make it simple to prepare them for any purpose. Use the resize an image tool to fit exact dimensions for social media, or compress an image to shrink file size without visibly reducing quality, perfect for faster loading websites and easier email attachments.</p>
<p>Need precise control over composition? Our crop an image tool and rotate an image tool let you fine-tune photos in a few clicks, right from your browser. When file formats don't match what you need, the convert PNG to JPG tool and convert JPG to PNG tool handle quick, lossless-looking conversions, while the convert WebP to PNG tool and convert PNG to WebP tool keep your images compatible with modern, fast-loading web formats.</p>
<p>For creators and businesses, protecting original work matters. Add a watermark to an image to stamp text or logos onto photos before sharing them publicly, while our remove image background tool uses smart detection to cut out subjects cleanly for product photos, profile pictures, or design projects, with no design software or manual masking required.</p>
<p>Every tool on this page works instantly in your browser, supports common formats like JPG, PNG and WebP, and keeps your files private during processing. There's no cost, no account needed, and no limit on how many images you can edit. Browse the full toolkit below to resize, compress, crop, convert or enhance your images in just a few clicks.</p>
"""

_TEXT_CONTENT = """
<p>Writers, students and developers all need reliable text tools, and ToolSimpli brings the most useful ones together in one place. Use the word counter to track word and sentence counts for essays and assignments, or the character counter to stay within strict limits for titles, tweets, and meta descriptions.</p>
<p>Formatting text correctly saves time. Our case converter instantly switches text between uppercase, lowercase, title case and sentence case, while the text reverser flips characters or word order for creative projects and quick checks. If you're cleaning up lists or data, the duplicate line remover and text sorter organize and de-duplicate content in seconds, no spreadsheet needed.</p>
<p>Developers and designers often need placeholder or sample content, so our lorem ipsum generator and random text generator create ready-to-use filler text for mockups and layout testing. For working with links and query strings safely, use the URL encoder to convert special characters, or the URL decoder to reverse the process, so URLs display and function correctly across browsers and applications.</p>
<p>Every text tool on ToolSimpli runs directly in your browser with no sign-up and no software installation. Paste your text, get instant results, and copy the output with one click. Whether you're proofreading an assignment, cleaning a dataset, or preparing content for the web, these free text tools are built to save time and reduce manual work. Explore the full collection below to find the right tool for your task.</p>
"""

_DEV_CONTENT = """
<p>ToolSimpli's developer tools are built to speed up everyday coding tasks without switching between multiple apps or installing extensions. Use the JSON formatter to instantly beautify messy JSON, or the JSON validator to catch syntax errors before they break your application, and the JSON minifier when you need to shrink JSON payloads for production.</p>
<p>Encoding and decoding data is a routine part of development. Our Base64 encoder converts text and files to Base64 in one click, the Base64 decoder reverses the process, and the dedicated Base64 to image converter and image to Base64 converter make it easy to embed images directly in code or extract images from encoded strings.</p>
<p>Shipping faster, lighter code matters for performance. The CSS minifier and JS minifier strip out unnecessary whitespace and comments to shrink file sizes and improve page load times, while the HTML formatter cleans up and indents markup for easier reading and debugging. For generating unique identifiers in databases and APIs, the UUID generator produces valid, random UUIDs instantly.</p>
<p>All developer tools on ToolSimpli run client-side friendly workflows in the browser, require no account, and support copy-paste or file upload where relevant. Whether you're debugging an API response, preparing assets for production, or generating test data, this toolkit is designed to be fast, accurate and free to use as often as you need. Browse the full list below to find the right developer tool for your workflow.</p>
"""


_CALC_CONTENT = """
<p>ToolSimpli's free calculators handle the everyday sums that are easy to get wrong on paper. Work out a loan or mortgage payment before you commit, check what a discount really saves you, split a bill fairly, or see how long it takes to reach a savings goal — each one runs instantly in your browser with no sign-up.</p>
<p>Money questions are the ones people ask most. The loan calculator, mortgage calculator, car loan calculator and EMI calculator all show the monthly payment alongside the total interest you'll pay, so you can compare offers on what they actually cost rather than on the headline rate. The compound interest calculator and savings goal calculator work the other way round, showing what regular saving turns into over time.</p>
<p>For day-to-day maths there's a percentage calculator, percentage change calculator, discount calculator, tip calculator and VAT calculator — quick answers for shopping, invoicing and splitting costs. On the health side, the BMI calculator and BMR calculator give you a reading plus the daily calorie figure that goes with your activity level.</p>
<p>Every calculator is free, needs no account, and keeps whatever you type on your own screen. Nothing you enter is stored. Pick a calculator below and get your answer in a couple of seconds.</p>
"""

CATEGORIES: list[Category] = [
    Category(
        "calculators", "Calculators", "Loan, savings, percentage, health and date calculators.", "calculator",
        meta_title="Free Online Calculators – Loan, EMI, Percentage, BMI & More | ToolSimpli",
        meta_description="Free online calculators for loans, mortgages, EMI, compound interest, percentages, discounts, tips, VAT, BMI and dates. Instant results, no signup required.",
        content=_CALC_CONTENT.strip(),
    ),
    Category(
        "pdf-tools", "PDF Tools", "Merge, split, convert and manage PDF files.", "file-text",
        meta_title="Free Online PDF Tools – Merge, Compress, Convert & Edit PDF | ToolSimpli",
        meta_description="Use ToolSimpli's free online PDF tools to merge, split, compress, convert, watermark and protect PDF files instantly. No installation needed, 100% secure and free.",
        content=_PDF_CONTENT.strip(),
    ),
    Category(
        "image-tools", "Image Tools", "Compress, convert, resize and edit images.", "image",
        meta_title="Free Online Image Tools – Resize, Compress, Crop & Convert Images | ToolSimpli",
        meta_description="ToolSimpli's free image tools let you resize, compress, crop, rotate, convert and watermark images online in seconds. Fast, secure and easy to use, no software required.",
        content=_IMAGE_CONTENT.strip(),
    ),
    Category(
        "text-tools", "Text Tools", "Count, convert, sort and transform text.", "type",
        meta_title="Free Online Text Tools – Word Counter, Case Converter & More | ToolSimpli",
        meta_description="ToolSimpli's free text tools help you count words, convert text case, sort lines, generate lorem ipsum and encode or decode URLs instantly online. No download required.",
        content=_TEXT_CONTENT.strip(),
    ),
    Category(
        "developer-tools", "Developer Tools", "Format, minify, encode and generate.", "code",
        meta_title="Free Online Developer Tools – JSON, Base64, Minifiers & More | ToolSimpli",
        meta_description="ToolSimpli's free developer tools let you format and validate JSON, encode or decode Base64, minify CSS and JS, generate UUIDs and more, all online with no setup.",
        content=_DEV_CONTENT.strip(),
    ),
    Category(
        "pro-tools", "Pro Tools", "Advanced, all-in-one tools that run entirely in your browser.", "sparkles",
        meta_title="Pro Tools – Advanced Free Online Tools | ToolSimpli",
        meta_description="ToolSimpli Pro Tools: powerful, all-in-one online apps like the PDF Studio, Invoice Generator and Resume Builder. Fast, private, and free.",
    ),
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

    # Pro tools — rich, fully client-side apps shown in a highlighted "Pro Tools"
    # container. `custom_ui` = rendered by a bespoke frontend component (not the
    # generic tool UI); `coming_soon` = announced but not built yet.
    pro: bool = False
    custom_ui: bool = False
    coming_soon: bool = False

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
        _opt("text", "Watermark text", OptionType.text, default="© Toolsimpli"),
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


# ---- PRO TOOLS (rich, fully client-side; rendered by bespoke frontend components) ----
define(ToolConfig(
    name="PDF Studio", slug="pdf-studio", category="pro-tools",
    description="All-in-one PDF editor: edit pages, add text and images, apply filters, and export — right in your browser.",
    seo_keywords=["PDF editor online", "edit PDF free", "PDF studio", "online PDF editor"],
    how_to_use=[
        "Open a PDF by clicking Open PDF or dragging a file onto the page.",
        "Edit any page: add text, insert or replace images, add links, or apply filters.",
        "Reorder, duplicate, rotate or delete pages as needed.",
        "Click Export to download your edited PDF.",
    ],
    input_kind=InputKind.file, client_side=True, pro=True, custom_ui=True,
    accepted_extensions=["pdf"],
))
define(ToolConfig(
    name="Invoice Generator", slug="invoice-generator", category="pro-tools",
    description="Create professional invoices with line items, tax and totals, then download a clean PDF.",
    seo_keywords=["invoice generator", "free invoice maker", "create invoice online", "invoice PDF"],
    how_to_use=[
        "Add your logo and fill in your business (From) and client (Bill To) details.",
        "Add line items with a description, quantity and rate — amounts calculate automatically.",
        "Set tax, discount, shipping, amount paid and your currency.",
        "Click Download PDF to save a clean, professional invoice.",
    ],
    input_kind=InputKind.options, client_side=True, pro=True, custom_ui=True,
))
define(ToolConfig(
    name="Resume Builder", slug="resume-builder", category="pro-tools",
    description="Build a polished, modern resume from a simple form and export it as a print-ready PDF.",
    seo_keywords=["resume builder", "free resume maker", "CV builder online", "resume PDF"],
    how_to_use=[
        "Fill in your personal details and a short professional summary.",
        "Add your work experience and education, one entry at a time.",
        "List your skills and optionally upload a passport or profile photo.",
        "Click Download PDF to get a clean, print-ready resume.",
    ],
    input_kind=InputKind.options, client_side=True, pro=True, custom_ui=True,
))


# ---- CALCULATORS ----
define(ToolConfig(
    name="Loan Calculator", slug="loan-calculator", category="calculators",
    description="Work out the monthly payment and total interest on any loan.",
    seo_keywords=['Loan Calculator', 'Monthly Payment Calculator', 'Loan Interest Calculator'],
    how_to_use=['Enter the loan amount', 'Set the interest rate and term', 'Read the monthly payment'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("amount", "Loan amount", OptionType.number, default=10000, min=1),
        _opt("rate", "Annual interest rate (%)", OptionType.number, default=8, min=0),
        _opt("years", "Term (years)", OptionType.number, default=5, min=1),
    ],
))
define(ToolConfig(
    name="Mortgage Calculator", slug="mortgage-calculator", category="calculators",
    description="Estimate a home loan payment from price, deposit, rate and term.",
    seo_keywords=['Mortgage Calculator', 'Home Loan Calculator', 'Mortgage Payment Calculator'],
    how_to_use=['Enter the property price', 'Enter your deposit', 'Set rate and term'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("price", "Property price", OptionType.number, default=250000, min=1),
        _opt("down_payment", "Deposit", OptionType.number, default=50000, min=0),
        _opt("rate", "Annual interest rate (%)", OptionType.number, default=6, min=0),
        _opt("years", "Term (years)", OptionType.number, default=25, min=1),
    ],
))
define(ToolConfig(
    name="Car Loan Calculator", slug="car-loan-calculator", category="calculators",
    description="See the monthly cost and total interest on a car loan.",
    seo_keywords=['Car Loan Calculator', 'Auto Loan Calculator', 'Vehicle Finance Calculator'],
    how_to_use=['Enter the amount borrowed', 'Set rate and term', 'Read the monthly payment'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("amount", "Loan amount", OptionType.number, default=20000, min=1),
        _opt("rate", "Annual interest rate (%)", OptionType.number, default=7, min=0),
        _opt("years", "Term (years)", OptionType.number, default=5, min=1),
    ],
))
define(ToolConfig(
    name="EMI Calculator", slug="emi-calculator", category="calculators",
    description="Calculate an equated monthly instalment for any loan term in months.",
    seo_keywords=['EMI Calculator', 'Equated Monthly Instalment', 'Loan EMI Calculator'],
    how_to_use=['Enter the loan amount', 'Set the rate', 'Enter the term in months'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("amount", "Loan amount", OptionType.number, default=100000, min=1),
        _opt("rate", "Annual interest rate (%)", OptionType.number, default=10, min=0),
        _opt("months", "Term (months)", OptionType.number, default=24, min=1),
    ],
))
define(ToolConfig(
    name="Compound Interest Calculator", slug="compound-interest-calculator", category="calculators",
    description="See what savings grow to with compound interest.",
    seo_keywords=['Compound Interest Calculator', 'Investment Growth Calculator', 'Savings Interest Calculator'],
    how_to_use=['Enter your starting amount', 'Set the rate and years', 'Read the final balance'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("principal", "Starting amount", OptionType.number, default=1000, min=0),
        _opt("rate", "Annual interest rate (%)", OptionType.number, default=7, min=0),
        _opt("years", "Years", OptionType.number, default=10, min=1),
        _opt("compounds_per_year", "Compounds per year", OptionType.number, default=12, min=1, max=365),
    ],
))
define(ToolConfig(
    name="Simple Interest Calculator", slug="simple-interest-calculator", category="calculators",
    description="Calculate simple interest and the total repayable.",
    seo_keywords=['Simple Interest Calculator', 'Interest Calculator', 'Flat Interest Calculator'],
    how_to_use=['Enter the principal', 'Set the rate and years', 'Read the interest'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("principal", "Principal", OptionType.number, default=1000, min=0),
        _opt("rate", "Annual rate (%)", OptionType.number, default=5, min=0),
        _opt("years", "Years", OptionType.number, default=3, min=0),
    ],
))
define(ToolConfig(
    name="Savings Goal Calculator", slug="savings-goal-calculator", category="calculators",
    description="Find out how long it takes to reach a savings target.",
    seo_keywords=['Savings Goal Calculator', 'Save For Goal Calculator', 'Savings Time Calculator'],
    how_to_use=['Enter your target', 'Enter what you save monthly', 'Read the time needed'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("goal", "Savings goal", OptionType.number, default=10000, min=1),
        _opt("monthly", "Monthly contribution", OptionType.number, default=250, min=1),
        _opt("rate", "Annual interest rate (%)", OptionType.number, default=4, min=0),
    ],
))
define(ToolConfig(
    name="Percentage Calculator", slug="percentage-calculator", category="calculators",
    description="Find a percentage of a number, plus the value with it added or removed.",
    seo_keywords=['Percentage Calculator', 'Percent Of Number', 'Calculate Percentage'],
    how_to_use=['Enter the number', 'Enter the percentage', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=200),
        _opt("percent", "Percentage (%)", OptionType.number, default=15),
    ],
))
define(ToolConfig(
    name="Percentage Change Calculator", slug="percentage-change-calculator", category="calculators",
    description="Work out the percentage increase or decrease between two numbers.",
    seo_keywords=['Percentage Change Calculator', 'Percent Increase Calculator', 'Percent Decrease Calculator'],
    how_to_use=['Enter the original value', 'Enter the new value', 'Read the change'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("old_value", "Original value", OptionType.number, default=100),
        _opt("new_value", "New value", OptionType.number, default=125),
    ],
))
define(ToolConfig(
    name="Discount Calculator", slug="discount-calculator", category="calculators",
    description="See the sale price and how much a discount saves you.",
    seo_keywords=['Discount Calculator', 'Sale Price Calculator', 'Percent Off Calculator'],
    how_to_use=['Enter the original price', 'Enter the discount', 'Read the final price'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("price", "Original price", OptionType.number, default=100, min=0),
        _opt("discount", "Discount (%)", OptionType.number, default=20, min=0, max=100),
    ],
))
define(ToolConfig(
    name="Tip Calculator", slug="tip-calculator", category="calculators",
    description="Work out a tip and split the bill between people.",
    seo_keywords=['Tip Calculator', 'Bill Split Calculator', 'Gratuity Calculator'],
    how_to_use=['Enter the bill', 'Choose a tip percentage', 'Set how many people'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("bill", "Bill amount", OptionType.number, default=50, min=0),
        _opt("tip_percent", "Tip (%)", OptionType.number, default=15, min=0),
        _opt("people", "Split between", OptionType.number, default=1, min=1),
    ],
))
define(ToolConfig(
    name="VAT Calculator", slug="vat-calculator", category="calculators",
    description="Add VAT to a price or work backwards to the net amount.",
    seo_keywords=['VAT Calculator', 'Sales Tax Calculator', 'Add Or Remove VAT'],
    how_to_use=['Enter the amount', 'Set the VAT rate', 'Choose add or remove'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("amount", "Amount", OptionType.number, default=100, min=0),
        _opt("rate", "VAT rate (%)", OptionType.number, default=20, min=0),
        _opt("mode", "Mode", OptionType.select, default="add", choices=["add", "remove"]),
    ],
))
define(ToolConfig(
    name="BMI Calculator", slug="bmi-calculator", category="calculators",
    description="Calculate body mass index and see which range it falls in.",
    seo_keywords=['BMI Calculator', 'Body Mass Index Calculator', 'BMI Checker'],
    how_to_use=['Enter your weight in kg', 'Enter your height in cm', 'Read your BMI'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("weight_kg", "Weight (kg)", OptionType.number, default=70, min=1),
        _opt("height_cm", "Height (cm)", OptionType.number, default=175, min=1),
    ],
))
define(ToolConfig(
    name="BMR Calculator", slug="bmr-calculator", category="calculators",
    description="Estimate your basal metabolic rate and daily calorie needs.",
    seo_keywords=['BMR Calculator', 'Basal Metabolic Rate', 'Daily Calorie Calculator'],
    how_to_use=['Enter weight, height and age', 'Choose sex and activity level', 'Read your daily calories'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("weight_kg", "Weight (kg)", OptionType.number, default=70, min=1),
        _opt("height_cm", "Height (cm)", OptionType.number, default=175, min=1),
        _opt("age", "Age", OptionType.number, default=30, min=1, max=120),
        _opt("sex", "Sex", OptionType.select, default="male", choices=["male", "female"]),
        _opt("activity", "Activity level", OptionType.select, default="sedentary", choices=["sedentary", "light", "moderate", "active", "very active"]),
    ],
))
define(ToolConfig(
    name="Age Calculator", slug="age-calculator", category="calculators",
    description="Work out an exact age in years, months and days.",
    seo_keywords=['Age Calculator', 'Date Of Birth Calculator', 'How Old Am I'],
    how_to_use=['Enter the date of birth', 'Read the exact age'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("birth_date", "Date of birth (YYYY-MM-DD)", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Date Difference Calculator", slug="date-difference-calculator", category="calculators",
    description="Count the days, weeks and months between two dates.",
    seo_keywords=['Date Difference Calculator', 'Days Between Dates', 'Date Duration Calculator'],
    how_to_use=['Enter the start date', 'Enter the end date', 'Read the difference'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("start_date", "Start date (YYYY-MM-DD)", OptionType.text, default=""),
        _opt("end_date", "End date (YYYY-MM-DD)", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Length Converter", slug="length-converter", category="calculators",
    description="Convert between mm, cm, m, km, inches, feet, yards and miles.",
    seo_keywords=['Length Converter', 'Unit Converter', 'cm to inches'],
    how_to_use=['Enter the value', 'Pick the units', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=1),
        _opt("from", "From", OptionType.select, default="cm", choices=['mm', 'cm', 'm', 'km', 'in', 'ft', 'yd', 'mi']),
        _opt("to", "To", OptionType.select, default="in", choices=['mm', 'cm', 'm', 'km', 'in', 'ft', 'yd', 'mi']),
    ],
))
define(ToolConfig(
    name="Weight Converter", slug="weight-converter", category="calculators",
    description="Convert between grams, kilograms, ounces, pounds and stone.",
    seo_keywords=['Weight Converter', 'kg to lbs', 'Mass Converter'],
    how_to_use=['Enter the value', 'Pick the units', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=1),
        _opt("from", "From", OptionType.select, default="kg", choices=['mg', 'g', 'kg', 't', 'oz', 'lb', 'st']),
        _opt("to", "To", OptionType.select, default="lb", choices=['mg', 'g', 'kg', 't', 'oz', 'lb', 'st']),
    ],
))
define(ToolConfig(
    name="Volume Converter", slug="volume-converter", category="calculators",
    description="Convert litres, millilitres, cups, pints, quarts and gallons.",
    seo_keywords=['Volume Converter', 'ml to cups', 'Liquid Converter'],
    how_to_use=['Enter the value', 'Pick the units', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=1),
        _opt("from", "From", OptionType.select, default="l", choices=['ml', 'l', 'm3', 'tsp', 'tbsp', 'cup', 'pt', 'qt', 'gal', 'fl oz']),
        _opt("to", "To", OptionType.select, default="gal", choices=['ml', 'l', 'm3', 'tsp', 'tbsp', 'cup', 'pt', 'qt', 'gal', 'fl oz']),
    ],
))
define(ToolConfig(
    name="Area Converter", slug="area-converter", category="calculators",
    description="Convert square metres, feet, acres, hectares and miles.",
    seo_keywords=['Area Converter', 'sq ft to sq m', 'Acre Converter'],
    how_to_use=['Enter the value', 'Pick the units', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=1),
        _opt("from", "From", OptionType.select, default="m2", choices=['mm2', 'cm2', 'm2', 'ha', 'km2', 'in2', 'ft2', 'yd2', 'acre', 'mi2']),
        _opt("to", "To", OptionType.select, default="ft2", choices=['mm2', 'cm2', 'm2', 'ha', 'km2', 'in2', 'ft2', 'yd2', 'acre', 'mi2']),
    ],
))
define(ToolConfig(
    name="Speed Converter", slug="speed-converter", category="calculators",
    description="Convert km/h, mph, m/s, knots and feet per second.",
    seo_keywords=['Speed Converter', 'kmh to mph', 'Velocity Converter'],
    how_to_use=['Enter the value', 'Pick the units', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=1),
        _opt("from", "From", OptionType.select, default="km/h", choices=['m/s', 'km/h', 'mph', 'knot', 'ft/s']),
        _opt("to", "To", OptionType.select, default="mph", choices=['m/s', 'km/h', 'mph', 'knot', 'ft/s']),
    ],
))
define(ToolConfig(
    name="Data Storage Converter", slug="data-storage-converter", category="calculators",
    description="Convert bytes, KB, MB, GB, TB and bits.",
    seo_keywords=['Data Storage Converter', 'MB to GB', 'File Size Converter'],
    how_to_use=['Enter the value', 'Pick the units', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=1),
        _opt("from", "From", OptionType.select, default="MB", choices=['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'bit', 'Kbit', 'Mbit']),
        _opt("to", "To", OptionType.select, default="GB", choices=['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'bit', 'Kbit', 'Mbit']),
    ],
))
define(ToolConfig(
    name="Temperature Converter", slug="temperature-converter", category="calculators",
    description="Convert between Celsius, Fahrenheit and Kelvin.",
    seo_keywords=['Temperature Converter', 'Celsius to Fahrenheit', 'C to F'],
    how_to_use=['Enter the temperature', 'Pick the scales', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Temperature", OptionType.number, default=25),
        _opt("from", "From", OptionType.select, default="C", choices=["C", "F", "K"]),
        _opt("to", "To", OptionType.select, default="F", choices=["C", "F", "K"]),
    ],
))
define(ToolConfig(
    name="Average Calculator", slug="average-calculator", category="calculators",
    description="Find the mean, median, minimum and maximum of a list of numbers.",
    seo_keywords=['Average Calculator', 'Mean Calculator', 'Median Calculator'],
    how_to_use=['Paste or type your numbers', 'Separate them with commas', 'Read the results'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("numbers", "Numbers (comma separated)", OptionType.text, default="4, 8, 15, 16, 23, 42"),
    ],
))
define(ToolConfig(
    name="Standard Deviation Calculator", slug="standard-deviation-calculator", category="calculators",
    description="Calculate standard deviation, variance and mean for a data set.",
    seo_keywords=['Standard Deviation Calculator', 'Variance Calculator', 'Statistics Calculator'],
    how_to_use=['Paste your numbers', 'Separate them with commas', 'Read the statistics'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("numbers", "Numbers (comma separated)", OptionType.text, default="2, 4, 4, 4, 5, 5, 7, 9"),
    ],
))
define(ToolConfig(
    name="Percentage Of Total Calculator", slug="percentage-of-total-calculator", category="calculators",
    description="Work out what percentage one number is of another.",
    seo_keywords=['Percentage Of Total', 'What Percent Is', 'Percent Of Calculator'],
    how_to_use=['Enter the part', 'Enter the total', 'Read the percentage'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("part", "Part", OptionType.number, default=25),
        _opt("total", "Total", OptionType.number, default=200),
    ],
))
define(ToolConfig(
    name="Fraction Calculator", slug="fraction-calculator", category="calculators",
    description="Add, subtract, multiply or divide two fractions.",
    seo_keywords=['Fraction Calculator', 'Add Fractions', 'Fraction Math'],
    how_to_use=['Enter both fractions like 3/4', 'Choose the operation', 'Read the simplified result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("a", "First fraction", OptionType.text, default="1/2"),
        _opt("operation", "Operation", OptionType.select, default="+", choices=["+", "-", "*", "/"]),
        _opt("b", "Second fraction", OptionType.text, default="1/3"),
    ],
))
define(ToolConfig(
    name="Ratio Calculator", slug="ratio-calculator", category="calculators",
    description="Simplify a ratio and see it as a decimal and a percentage.",
    seo_keywords=['Ratio Calculator', 'Simplify Ratio', 'Proportion Calculator'],
    how_to_use=['Enter both numbers', 'Read the simplified ratio'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("a", "First number", OptionType.number, default=16),
        _opt("b", "Second number", OptionType.number, default=9),
    ],
))
define(ToolConfig(
    name="Rounding Calculator", slug="rounding-calculator", category="calculators",
    description="Round a number to any number of decimal places, up or down.",
    seo_keywords=['Rounding Calculator', 'Round Numbers', 'Decimal Rounding'],
    how_to_use=['Enter the number', 'Choose decimal places', 'Read the rounded values'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Number", OptionType.number, default=3.14159),
        _opt("decimals", "Decimal places", OptionType.number, default=2, min=0, max=10),
    ],
))
define(ToolConfig(
    name="Exponent Calculator", slug="exponent-calculator", category="calculators",
    description="Raise any number to any power.",
    seo_keywords=['Exponent Calculator', 'Power Calculator', 'Base To The Power'],
    how_to_use=['Enter the base', 'Enter the power', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("base", "Base", OptionType.number, default=2),
        _opt("power", "Power", OptionType.number, default=10),
    ],
))
define(ToolConfig(
    name="Root Calculator", slug="root-calculator", category="calculators",
    description="Find the square root, cube root or any nth root of a number.",
    seo_keywords=['Root Calculator', 'Square Root Calculator', 'Cube Root'],
    how_to_use=['Enter the number', 'Choose which root', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Number", OptionType.number, default=144),
        _opt("root", "Root (2 = square)", OptionType.number, default=2),
    ],
))
define(ToolConfig(
    name="Logarithm Calculator", slug="logarithm-calculator", category="calculators",
    description="Calculate a logarithm in any base, plus ln and log10.",
    seo_keywords=['Logarithm Calculator', 'Log Calculator', 'Natural Log'],
    how_to_use=['Enter the number', 'Choose the base', 'Read the logarithm'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Number", OptionType.number, default=100),
        _opt("base", "Base", OptionType.number, default=10),
    ],
))
define(ToolConfig(
    name="GCF and LCM Calculator", slug="gcf-lcm-calculator", category="calculators",
    description="Find the greatest common factor and lowest common multiple.",
    seo_keywords=['GCF Calculator', 'LCM Calculator', 'Highest Common Factor'],
    how_to_use=['Enter two or more whole numbers', 'Read the GCF and LCM'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("numbers", "Numbers (comma separated)", OptionType.text, default="12, 18, 24"),
    ],
))
define(ToolConfig(
    name="Quadratic Equation Solver", slug="quadratic-solver", category="calculators",
    description="Solve ax² + bx + c = 0, including complex roots.",
    seo_keywords=['Quadratic Equation Solver', 'Quadratic Formula', 'Solve Quadratic'],
    how_to_use=['Enter a, b and c', 'Read both roots'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("a", "a", OptionType.number, default=1),
        _opt("b", "b", OptionType.number, default=-3),
        _opt("c", "c", OptionType.number, default=2),
    ],
))
define(ToolConfig(
    name="Permutation and Combination Calculator", slug="permutation-combination-calculator", category="calculators",
    description="Calculate nPr and nCr for any n and r.",
    seo_keywords=['Permutation Calculator', 'Combination Calculator', 'nCr Calculator'],
    how_to_use=['Enter n and r', 'Read permutations and combinations'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("n", "n (total items)", OptionType.number, default=10, min=0),
        _opt("r", "r (chosen)", OptionType.number, default=3, min=0),
    ],
))
define(ToolConfig(
    name="Area Calculator", slug="area-calculator", category="calculators",
    description="Find the area of a rectangle, triangle, circle or trapezoid.",
    seo_keywords=['Area Calculator', 'Rectangle Area', 'Circle Area'],
    how_to_use=['Choose the shape', 'Enter the measurements', 'Read the area'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("shape", "Shape", OptionType.select, default="rectangle", choices=["rectangle", "triangle", "circle", "trapezoid"]),
        _opt("a", "Length / base / radius", OptionType.number, default=10),
        _opt("b", "Width / height / second side", OptionType.number, default=5),
        _opt("height", "Height (trapezoid)", OptionType.number, default=4),
    ],
))
define(ToolConfig(
    name="Volume Calculator", slug="volume-calculator", category="calculators",
    description="Find the volume of a box, cylinder, sphere or cone.",
    seo_keywords=['Volume Calculator', 'Cylinder Volume', 'Sphere Volume'],
    how_to_use=['Choose the shape', 'Enter the measurements', 'Read the volume'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("shape", "Shape", OptionType.select, default="box", choices=["box", "cylinder", "sphere", "cone"]),
        _opt("a", "Length / radius", OptionType.number, default=10),
        _opt("b", "Width / height", OptionType.number, default=5),
        _opt("c", "Depth (box only)", OptionType.number, default=3),
    ],
))
define(ToolConfig(
    name="Body Fat Calculator", slug="body-fat-calculator", category="calculators",
    description="Estimate body fat percentage from tape measurements.",
    seo_keywords=['Body Fat Calculator', 'Body Fat Percentage', 'Navy Body Fat'],
    how_to_use=['Enter your measurements', 'Choose your sex', 'Read the estimate'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("sex", "Sex", OptionType.select, default="male", choices=["male", "female"]),
        _opt("height_cm", "Height (cm)", OptionType.number, default=175, min=1),
        _opt("neck_cm", "Neck (cm)", OptionType.number, default=38, min=1),
        _opt("waist_cm", "Waist (cm)", OptionType.number, default=85, min=1),
        _opt("hip_cm", "Hip (cm, women)", OptionType.number, default=95, min=0),
    ],
))
define(ToolConfig(
    name="Ideal Weight Calculator", slug="ideal-weight-calculator", category="calculators",
    description="See an ideal weight for your height plus the healthy BMI range.",
    seo_keywords=['Ideal Weight Calculator', 'Healthy Weight Range', 'Ideal Body Weight'],
    how_to_use=['Enter your height', 'Choose your sex', 'Read the range'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("height_cm", "Height (cm)", OptionType.number, default=175, min=1),
        _opt("sex", "Sex", OptionType.select, default="male", choices=["male", "female"]),
    ],
))
define(ToolConfig(
    name="Water Intake Calculator", slug="water-intake-calculator", category="calculators",
    description="Work out how much water to drink a day for your weight.",
    seo_keywords=['Water Intake Calculator', 'Daily Water Intake', 'How Much Water'],
    how_to_use=['Enter your weight', 'Add your exercise minutes', 'Read the daily amount'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("weight_kg", "Weight (kg)", OptionType.number, default=70, min=1),
        _opt("exercise_minutes", "Exercise (minutes/day)", OptionType.number, default=30, min=0),
    ],
))
define(ToolConfig(
    name="One Rep Max Calculator", slug="one-rep-max-calculator", category="calculators",
    description="Estimate your one-rep max and training percentages.",
    seo_keywords=['One Rep Max Calculator', '1RM Calculator', 'Max Lift Calculator'],
    how_to_use=['Enter the weight lifted', 'Enter the reps', 'Read your 1RM'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("weight", "Weight lifted", OptionType.number, default=80, min=1),
        _opt("reps", "Reps completed", OptionType.number, default=5, min=1, max=20),
    ],
))
define(ToolConfig(
    name="Pace Calculator", slug="pace-calculator", category="calculators",
    description="Work out running pace per kilometre and per mile.",
    seo_keywords=['Pace Calculator', 'Running Pace', 'Min Per KM'],
    how_to_use=['Enter the distance', 'Enter your time', 'Read your pace'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("distance_km", "Distance (km)", OptionType.number, default=10, min=0),
        _opt("time_minutes", "Time (minutes)", OptionType.number, default=55, min=0),
    ],
))
define(ToolConfig(
    name="GPA Calculator", slug="gpa-calculator", category="calculators",
    description="Calculate a weighted grade point average from grades and credits.",
    seo_keywords=['GPA Calculator', 'Grade Point Average', 'College GPA'],
    how_to_use=['Enter your grades', 'Enter matching credits', 'Read your GPA'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("grades", "Grades (comma separated)", OptionType.text, default="A, B+, B, C"),
        _opt("credits", "Credits (comma separated)", OptionType.text, default="3, 3, 4, 3"),
    ],
))
define(ToolConfig(
    name="Fuel Cost Calculator", slug="fuel-cost-calculator", category="calculators",
    description="Work out the fuel needed and the cost of a journey.",
    seo_keywords=['Fuel Cost Calculator', 'Gas Cost Calculator', 'Trip Fuel Cost'],
    how_to_use=['Enter the distance', 'Enter your fuel economy', 'Enter the fuel price'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("distance", "Distance (km)", OptionType.number, default=500, min=0),
        _opt("efficiency_km_per_l", "Economy (km per litre)", OptionType.number, default=12, min=0),
        _opt("price_per_litre", "Price per litre", OptionType.number, default=1.5, min=0),
    ],
))
define(ToolConfig(
    name="Unit Price Calculator", slug="unit-price-calculator", category="calculators",
    description="Compare two pack sizes and see which is better value.",
    seo_keywords=['Unit Price Calculator', 'Cost Per Unit', 'Price Comparison'],
    how_to_use=['Enter price and size for A', 'Enter price and size for B', 'See which wins'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("price_a", "Price A", OptionType.number, default=3.5, min=0),
        _opt("quantity_a", "Quantity A", OptionType.number, default=500, min=0),
        _opt("price_b", "Price B", OptionType.number, default=6, min=0),
        _opt("quantity_b", "Quantity B", OptionType.number, default=1000, min=0),
    ],
))
define(ToolConfig(
    name="Electricity Cost Calculator", slug="electricity-cost-calculator", category="calculators",
    description="See what an appliance costs to run per day, month and year.",
    seo_keywords=['Electricity Cost Calculator', 'Energy Cost', 'Appliance Running Cost'],
    how_to_use=['Enter the wattage', 'Enter hours used per day', 'Enter your rate'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("watts", "Power (watts)", OptionType.number, default=100, min=0),
        _opt("hours_per_day", "Hours per day", OptionType.number, default=5, min=0, max=24),
        _opt("rate_per_kwh", "Rate per kWh", OptionType.number, default=0.25, min=0),
    ],
))
define(ToolConfig(
    name="Paint Calculator", slug="paint-calculator", category="calculators",
    description="Work out how much paint a room needs.",
    seo_keywords=['Paint Calculator', 'How Much Paint', 'Wall Paint Estimator'],
    how_to_use=['Enter the room size', 'Choose the number of coats', 'Read the litres needed'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("length_m", "Room length (m)", OptionType.number, default=5, min=0),
        _opt("width_m", "Room width (m)", OptionType.number, default=4, min=0),
        _opt("height_m", "Wall height (m)", OptionType.number, default=2.7, min=0),
        _opt("coats", "Coats", OptionType.number, default=2, min=1, max=5),
        _opt("coverage_m2_per_litre", "Coverage (m² per litre)", OptionType.number, default=10, min=1),
    ],
))
define(ToolConfig(
    name="Add or Subtract Date Calculator", slug="add-subtract-date-calculator", category="calculators",
    description="Add or subtract days from any date.",
    seo_keywords=['Date Calculator', 'Add Days To Date', 'Subtract Days'],
    how_to_use=['Enter the start date', 'Choose add or subtract', 'Enter the days'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("start_date", "Start date (YYYY-MM-DD)", OptionType.text, default=""),
        _opt("operation", "Operation", OptionType.select, default="add", choices=["add", "subtract"]),
        _opt("days", "Days", OptionType.number, default=30),
    ],
))
define(ToolConfig(
    name="Countdown Calculator", slug="countdown-calculator", category="calculators",
    description="Count the days until (or since) any date.",
    seo_keywords=['Countdown Calculator', 'Days Until', 'Days Since'],
    how_to_use=['Enter the target date', 'Read the countdown'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("target_date", "Target date (YYYY-MM-DD)", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Work Hours Calculator", slug="work-hours-calculator", category="calculators",
    description="Work out hours worked in a shift, and pay if you add a rate.",
    seo_keywords=['Work Hours Calculator', 'Timesheet Calculator', 'Hours Worked'],
    how_to_use=['Enter start and end time', 'Enter your break', 'Read the hours'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("start_time", "Start time (HH:MM)", OptionType.text, default="09:00"),
        _opt("end_time", "End time (HH:MM)", OptionType.text, default="17:30"),
        _opt("break_minutes", "Break (minutes)", OptionType.number, default=30, min=0),
        _opt("hourly_rate", "Hourly rate (optional)", OptionType.number, default=0, min=0),
    ],
))
define(ToolConfig(
    name="Amortization Calculator", slug="amortization-calculator", category="calculators",
    description="See a year-by-year breakdown of interest and principal on a loan.",
    seo_keywords=['Amortization Calculator', 'Loan Schedule', 'Amortization Table'],
    how_to_use=['Enter the loan', 'Set rate and term', 'Read the schedule'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("amount", "Loan amount", OptionType.number, default=200000, min=1),
        _opt("rate", "Annual rate (%)", OptionType.number, default=6, min=0),
        _opt("years", "Term (years)", OptionType.number, default=20, min=1, max=50),
    ],
))
define(ToolConfig(
    name="Refinance Calculator", slug="refinance-calculator", category="calculators",
    description="Compare your current loan with a new one and find the break-even point.",
    seo_keywords=['Refinance Calculator', 'Mortgage Refinance', 'Refinance Break Even'],
    how_to_use=['Enter your balance', 'Enter both rates', 'Add closing costs'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("balance", "Current balance", OptionType.number, default=180000, min=1),
        _opt("current_rate", "Current rate (%)", OptionType.number, default=7, min=0),
        _opt("years_left", "Years left", OptionType.number, default=20, min=1),
        _opt("new_rate", "New rate (%)", OptionType.number, default=5, min=0),
        _opt("new_years", "New term (years)", OptionType.number, default=20, min=1),
        _opt("closing_costs", "Closing costs", OptionType.number, default=3000, min=0),
    ],
))
define(ToolConfig(
    name="Debt Payoff Calculator", slug="debt-payoff-calculator", category="calculators",
    description="See how long a fixed monthly payment takes to clear a debt.",
    seo_keywords=['Debt Payoff Calculator', 'Debt Snowball', 'Payoff Time'],
    how_to_use=['Enter the balance', 'Enter the rate', 'Enter your monthly payment'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("balance", "Balance", OptionType.number, default=5000, min=1),
        _opt("rate", "Annual rate (%)", OptionType.number, default=18, min=0),
        _opt("monthly_payment", "Monthly payment", OptionType.number, default=250, min=1),
    ],
))
define(ToolConfig(
    name="Credit Card Payoff Calculator", slug="credit-card-payoff-calculator", category="calculators",
    description="Find out how long a card balance takes to clear, and the interest cost.",
    seo_keywords=['Credit Card Payoff Calculator', 'Card Interest', 'Payoff Time'],
    how_to_use=['Enter the balance', 'Enter the APR', 'Enter your payment'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("balance", "Balance", OptionType.number, default=3000, min=1),
        _opt("apr", "APR (%)", OptionType.number, default=22, min=0),
        _opt("monthly_payment", "Monthly payment", OptionType.number, default=150, min=1),
    ],
))
define(ToolConfig(
    name="APR Calculator", slug="apr-calculator", category="calculators",
    description="Find the true APR once fees are included in the cost of a loan.",
    seo_keywords=['APR Calculator', 'Effective APR', 'True Interest Rate'],
    how_to_use=['Enter the loan and fees', 'Set rate and term', 'Read the effective APR'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("amount", "Loan amount", OptionType.number, default=10000, min=1),
        _opt("fees", "Fees", OptionType.number, default=300, min=0),
        _opt("rate", "Nominal rate (%)", OptionType.number, default=8, min=0),
        _opt("years", "Term (years)", OptionType.number, default=5, min=1),
    ],
))
define(ToolConfig(
    name="Down Payment Calculator", slug="down-payment-calculator", category="calculators",
    description="Work out a deposit and the loan amount left over.",
    seo_keywords=['Down Payment Calculator', 'Deposit Calculator', 'Loan To Value'],
    how_to_use=['Enter the price', 'Choose a deposit percentage'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("price", "Purchase price", OptionType.number, default=300000, min=1),
        _opt("percent", "Deposit (%)", OptionType.number, default=20, min=0, max=100),
    ],
))
define(ToolConfig(
    name="Investment ROI Calculator", slug="investment-roi-calculator", category="calculators",
    description="Calculate return on investment and the annualised rate.",
    seo_keywords=['ROI Calculator', 'Return On Investment', 'Investment Return'],
    how_to_use=['Enter what you invested', 'Enter what it returned', 'Add the years'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("invested", "Amount invested", OptionType.number, default=10000, min=1),
        _opt("returned", "Value now", OptionType.number, default=15000, min=0),
        _opt("years", "Years held", OptionType.number, default=3, min=0),
    ],
))
define(ToolConfig(
    name="SIP Calculator", slug="sip-calculator", category="calculators",
    description="See what a monthly investment grows to over time.",
    seo_keywords=['SIP Calculator', 'Monthly Investment', 'Systematic Investment Plan'],
    how_to_use=['Enter your monthly amount', 'Set the return rate', 'Choose the years'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("monthly", "Monthly investment", OptionType.number, default=5000, min=1),
        _opt("rate", "Expected return (%)", OptionType.number, default=12, min=0),
        _opt("years", "Years", OptionType.number, default=10, min=1),
    ],
))
define(ToolConfig(
    name="Lumpsum Investment Calculator", slug="lumpsum-calculator", category="calculators",
    description="See what a one-off investment grows to.",
    seo_keywords=['Lumpsum Calculator', 'One Time Investment', 'Investment Growth'],
    how_to_use=['Enter the amount', 'Set the return rate', 'Choose the years'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("amount", "Amount", OptionType.number, default=100000, min=1),
        _opt("rate", "Expected return (%)", OptionType.number, default=12, min=0),
        _opt("years", "Years", OptionType.number, default=10, min=1),
    ],
))
define(ToolConfig(
    name="Retirement Calculator", slug="retirement-calculator", category="calculators",
    description="Project your retirement pot and the income it could provide.",
    seo_keywords=['Retirement Calculator', 'Retirement Savings', 'Pension Projection'],
    how_to_use=['Enter your age and savings', 'Add your monthly saving', 'Read the projection'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("current_age", "Current age", OptionType.number, default=30, min=1, max=100),
        _opt("retirement_age", "Retirement age", OptionType.number, default=60, min=2, max=100),
        _opt("current_savings", "Current savings", OptionType.number, default=20000, min=0),
        _opt("monthly_saving", "Monthly saving", OptionType.number, default=500, min=0),
        _opt("rate", "Expected return (%)", OptionType.number, default=7, min=0),
    ],
))
define(ToolConfig(
    name="401k Calculator", slug="401k-calculator", category="calculators",
    description="Project a workplace pension including the employer match.",
    seo_keywords=['401k Calculator', 'Pension Calculator', 'Employer Match'],
    how_to_use=['Enter your salary', 'Set your contribution', 'Add the employer match'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("annual_salary", "Annual salary", OptionType.number, default=60000, min=1),
        _opt("contribution_percent", "Your contribution (%)", OptionType.number, default=6, min=0, max=100),
        _opt("employer_match_percent", "Employer match (%)", OptionType.number, default=3, min=0, max=100),
        _opt("rate", "Expected return (%)", OptionType.number, default=7, min=0),
        _opt("years", "Years", OptionType.number, default=30, min=1),
    ],
))
define(ToolConfig(
    name="Future Value Calculator", slug="future-value-calculator", category="calculators",
    description="Find the future or present value of a sum of money.",
    seo_keywords=['Future Value Calculator', 'Present Value', 'Time Value Of Money'],
    how_to_use=['Enter the amount', 'Choose future or present', 'Set rate and years'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("amount", "Amount", OptionType.number, default=10000, min=0),
        _opt("rate", "Rate (%)", OptionType.number, default=7, min=0),
        _opt("years", "Years", OptionType.number, default=10, min=0),
        _opt("direction", "Calculate", OptionType.select, default="future", choices=["future", "present"]),
    ],
))
define(ToolConfig(
    name="Annuity Calculator", slug="annuity-calculator", category="calculators",
    description="Find the future and present value of a regular payment stream.",
    seo_keywords=['Annuity Calculator', 'Annuity Value', 'Payment Stream'],
    how_to_use=['Enter the payment', 'Set the rate', 'Choose the number of years'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("payment", "Payment per year", OptionType.number, default=1000, min=0),
        _opt("rate", "Rate (%)", OptionType.number, default=5, min=0),
        _opt("years", "Years", OptionType.number, default=20, min=1),
    ],
))
define(ToolConfig(
    name="Dividend Calculator", slug="dividend-calculator", category="calculators",
    description="Work out dividend income and yield from your holding.",
    seo_keywords=['Dividend Calculator', 'Dividend Yield', 'Dividend Income'],
    how_to_use=['Enter your shares', 'Enter the dividend', 'Add the share price'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("shares", "Shares held", OptionType.number, default=500, min=0),
        _opt("dividend_per_share", "Annual dividend per share", OptionType.number, default=2.5, min=0),
        _opt("share_price", "Share price", OptionType.number, default=50, min=0),
    ],
))
define(ToolConfig(
    name="Inflation Calculator", slug="inflation-calculator", category="calculators",
    description="See how inflation changes what your money is worth.",
    seo_keywords=['Inflation Calculator', 'Purchasing Power', 'Money Value Over Time'],
    how_to_use=['Enter the amount', 'Set the inflation rate', 'Choose the years'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("amount", "Amount", OptionType.number, default=1000, min=0),
        _opt("rate", "Inflation rate (%)", OptionType.number, default=3, min=0),
        _opt("years", "Years", OptionType.number, default=10, min=0),
    ],
))
define(ToolConfig(
    name="Net Worth Calculator", slug="net-worth-calculator", category="calculators",
    description="Total up assets and debts to find your net worth.",
    seo_keywords=['Net Worth Calculator', 'Assets Minus Liabilities', 'Personal Net Worth'],
    how_to_use=['Enter your assets', 'Enter your debts', 'Read your net worth'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("assets", "Total assets", OptionType.number, default=250000, min=0),
        _opt("liabilities", "Total liabilities", OptionType.number, default=90000, min=0),
    ],
))
define(ToolConfig(
    name="FD and RD Calculator", slug="fd-rd-calculator", category="calculators",
    description="Work out maturity on a fixed or recurring deposit.",
    seo_keywords=['FD Calculator', 'RD Calculator', 'Deposit Maturity'],
    how_to_use=['Choose fixed or recurring', 'Enter the amount', 'Set rate and years'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("type", "Deposit type", OptionType.select, default="fixed", choices=["fixed", "recurring"]),
        _opt("amount", "Amount (fixed)", OptionType.number, default=100000, min=0),
        _opt("monthly", "Monthly (recurring)", OptionType.number, default=5000, min=0),
        _opt("rate", "Interest rate (%)", OptionType.number, default=7, min=0),
        _opt("years", "Years", OptionType.number, default=5, min=1),
        _opt("compounds_per_year", "Compounds per year", OptionType.number, default=4, min=1, max=365),
    ],
))
define(ToolConfig(
    name="Salary Calculator", slug="salary-calculator", category="calculators",
    description="Convert a salary between hourly, daily, weekly, monthly and yearly.",
    seo_keywords=['Salary Calculator', 'Hourly To Salary', 'Annual Salary'],
    how_to_use=['Enter the amount', 'Choose the period', 'Read every other period'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("amount", "Amount", OptionType.number, default=60000, min=0),
        _opt("period", "Per", OptionType.select, default="year", choices=["hour", "day", "week", "month", "year"]),
        _opt("hours_per_week", "Hours per week", OptionType.number, default=40, min=1, max=100),
    ],
))
define(ToolConfig(
    name="Paycheck Calculator", slug="paycheck-calculator", category="calculators",
    description="Estimate take-home pay from gross salary and your deduction rates.",
    seo_keywords=['Paycheck Calculator', 'Take Home Pay', 'Net Salary'],
    how_to_use=['Enter gross pay', 'Enter your tax rate', 'Add other deductions'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("gross_annual", "Gross annual pay", OptionType.number, default=60000, min=0),
        _opt("tax_percent", "Tax (%)", OptionType.number, default=20, min=0, max=100),
        _opt("other_deductions_percent", "Other deductions (%)", OptionType.number, default=5, min=0, max=100),
    ],
))
define(ToolConfig(
    name="Markup and Margin Calculator", slug="markup-margin-calculator", category="calculators",
    description="Work out profit, markup and margin from cost and price.",
    seo_keywords=['Markup Calculator', 'Margin Calculator', 'Profit Margin'],
    how_to_use=['Enter your cost', 'Enter your price', 'Read markup and margin'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("cost", "Cost", OptionType.number, default=60, min=0),
        _opt("price", "Selling price", OptionType.number, default=100, min=0),
    ],
))
define(ToolConfig(
    name="Break Even Calculator", slug="break-even-calculator", category="calculators",
    description="Find how many units you must sell to cover your costs.",
    seo_keywords=['Break Even Calculator', 'Break Even Point', 'Break Even Analysis'],
    how_to_use=['Enter fixed costs', 'Enter price per unit', 'Enter variable cost'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("fixed_costs", "Fixed costs", OptionType.number, default=10000, min=0),
        _opt("price_per_unit", "Price per unit", OptionType.number, default=25, min=0),
        _opt("variable_cost_per_unit", "Variable cost per unit", OptionType.number, default=15, min=0),
    ],
))
define(ToolConfig(
    name="Overtime Calculator", slug="overtime-calculator", category="calculators",
    description="Calculate overtime pay and total earnings for a week.",
    seo_keywords=['Overtime Calculator', 'Overtime Pay', 'Time And A Half'],
    how_to_use=['Enter your rate', 'Enter normal and overtime hours', 'Read your pay'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("hourly_rate", "Hourly rate", OptionType.number, default=20, min=0),
        _opt("normal_hours", "Normal hours", OptionType.number, default=40, min=0),
        _opt("overtime_hours", "Overtime hours", OptionType.number, default=8, min=0),
        _opt("overtime_multiplier", "Overtime multiplier", OptionType.number, default=1.5, min=1, max=3),
    ],
))
define(ToolConfig(
    name="Commission Calculator", slug="commission-calculator", category="calculators",
    description="Work out sales commission and total earnings.",
    seo_keywords=['Commission Calculator', 'Sales Commission', 'Commission Rate'],
    how_to_use=['Enter your sales', 'Enter the rate', 'Add any base salary'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("sales", "Total sales", OptionType.number, default=50000, min=0),
        _opt("rate", "Commission rate (%)", OptionType.number, default=5, min=0, max=100),
        _opt("base_salary", "Base salary", OptionType.number, default=0, min=0),
    ],
))
define(ToolConfig(
    name="TDEE Calculator", slug="tdee-calculator", category="calculators",
    description="Find your daily calorie needs and targets for losing or gaining weight.",
    seo_keywords=['TDEE Calculator', 'Daily Calorie Needs', 'Maintenance Calories'],
    how_to_use=['Enter your details', 'Choose activity level', 'Read your targets'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("weight_kg", "Weight (kg)", OptionType.number, default=70, min=1),
        _opt("height_cm", "Height (cm)", OptionType.number, default=175, min=1),
        _opt("age", "Age", OptionType.number, default=30, min=1, max=120),
        _opt("sex", "Sex", OptionType.select, default="male", choices=["male", "female"]),
        _opt("activity", "Activity level", OptionType.select, default="moderate", choices=["sedentary", "light", "moderate", "active", "very active"]),
    ],
))
define(ToolConfig(
    name="Macro Calculator", slug="macro-calculator", category="calculators",
    description="Split a calorie target into protein, carbs and fat.",
    seo_keywords=['Macro Calculator', 'Macronutrient Split', 'IIFYM Calculator'],
    how_to_use=['Enter your calories', 'Choose a split', 'Read your macros'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("calories", "Daily calories", OptionType.number, default=2200, min=1),
        _opt("goal", "Split", OptionType.select, default="balanced", choices=["balanced", "low carb", "high protein", "endurance"]),
    ],
))
define(ToolConfig(
    name="Pregnancy Due Date Calculator", slug="pregnancy-due-date-calculator", category="calculators",
    description="Estimate a due date from the last period.",
    seo_keywords=['Due Date Calculator', 'Pregnancy Calculator', 'Estimated Due Date'],
    how_to_use=['Enter the first day of your last period', 'Set your cycle length'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("last_period", "Last period (YYYY-MM-DD)", OptionType.text, default=""),
        _opt("cycle_length", "Cycle length (days)", OptionType.number, default=28, min=20, max=45),
    ],
))
define(ToolConfig(
    name="Ovulation Calculator", slug="ovulation-calculator", category="calculators",
    description="Find your likely ovulation date and fertile window.",
    seo_keywords=['Ovulation Calculator', 'Fertile Window', 'Period Calculator'],
    how_to_use=['Enter your last period', 'Set your cycle length'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("last_period", "Last period (YYYY-MM-DD)", OptionType.text, default=""),
        _opt("cycle_length", "Cycle length (days)", OptionType.number, default=28, min=20, max=45),
    ],
))
define(ToolConfig(
    name="Target Heart Rate Calculator", slug="target-heart-rate-calculator", category="calculators",
    description="Find your training heart rate zones.",
    seo_keywords=['Target Heart Rate', 'Heart Rate Zones', 'Max Heart Rate'],
    how_to_use=['Enter your age', 'Add your resting heart rate', 'Read your zones'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("age", "Age", OptionType.number, default=30, min=1, max=120),
        _opt("resting_hr", "Resting heart rate", OptionType.number, default=65, min=30, max=120),
    ],
))
define(ToolConfig(
    name="Blood Alcohol Calculator", slug="bac-calculator", category="calculators",
    description="Estimate blood alcohol concentration from drinks and time.",
    seo_keywords=['BAC Calculator', 'Blood Alcohol Content', 'Alcohol Calculator'],
    how_to_use=['Enter the drinks', 'Enter your weight', 'Add hours since drinking'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("standard_drinks", "Standard drinks", OptionType.number, default=3, min=0),
        _opt("weight_kg", "Weight (kg)", OptionType.number, default=75, min=1),
        _opt("sex", "Sex", OptionType.select, default="male", choices=["male", "female"]),
        _opt("hours_since", "Hours since first drink", OptionType.number, default=2, min=0),
    ],
))
define(ToolConfig(
    name="Sleep Calculator", slug="sleep-calculator", category="calculators",
    description="Find the best times to wake up based on sleep cycles.",
    seo_keywords=['Sleep Calculator', 'Sleep Cycle Calculator', 'Best Wake Time'],
    how_to_use=['Enter your bedtime', 'Read the best wake times'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("bedtime", "Bedtime (HH:MM)", OptionType.text, default="23:00"),
    ],
))
define(ToolConfig(
    name="Scientific Calculator", slug="scientific-calculator", category="calculators",
    description="Evaluate any arithmetic expression, with roots, logs and trig.",
    seo_keywords=['Scientific Calculator', 'Online Calculator', 'Expression Calculator'],
    how_to_use=['Type an expression', 'Use sqrt, sin, log and pi', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("expression", "Expression", OptionType.text, default="2 * (3 + 4) ** 2"),
    ],
))
define(ToolConfig(
    name="Probability Calculator", slug="probability-calculator", category="calculators",
    description="Work out probability, odds and the chance over repeated trials.",
    seo_keywords=['Probability Calculator', 'Odds Calculator', 'Chance Calculator'],
    how_to_use=['Enter favourable outcomes', 'Enter total outcomes', 'Add trials'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("favourable", "Favourable outcomes", OptionType.number, default=1, min=0),
        _opt("total", "Total outcomes", OptionType.number, default=6, min=1),
        _opt("trials", "Trials", OptionType.number, default=1, min=1, max=10000),
    ],
))
define(ToolConfig(
    name="Prime and Factor Calculator", slug="prime-factor-calculator", category="calculators",
    description="Find prime factors and all divisors of a number.",
    seo_keywords=['Prime Factorization', 'Factor Calculator', 'Is It Prime'],
    how_to_use=['Enter a whole number', 'Read its factors'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("number", "Number", OptionType.number, default=360, min=2),
    ],
))
define(ToolConfig(
    name="Random Number Generator", slug="random-number-generator", category="calculators",
    description="Generate random numbers in any range, with or without repeats.",
    seo_keywords=['Random Number Generator', 'Random Picker', 'Number Randomiser'],
    how_to_use=['Set the range', 'Choose how many', 'Generate'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("min", "Minimum", OptionType.number, default=1),
        _opt("max", "Maximum", OptionType.number, default=100),
        _opt("count", "How many", OptionType.number, default=5, min=1, max=1000),
        _opt("unique", "No repeats", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Number Base Converter", slug="number-base-converter", category="calculators",
    description="Convert between binary, octal, decimal, hex and any base to 36.",
    seo_keywords=['Number Base Converter', 'Binary To Decimal', 'Hex Converter'],
    how_to_use=['Enter the number', 'Choose the bases', 'Read every conversion'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.text, default="255"),
        _opt("from_base", "From base", OptionType.number, default=10, min=2, max=36),
        _opt("to_base", "To base", OptionType.number, default=2, min=2, max=36),
    ],
))
define(ToolConfig(
    name="Slope Calculator", slug="slope-calculator", category="calculators",
    description="Find slope, distance and midpoint between two points.",
    seo_keywords=['Slope Calculator', 'Distance Formula', 'Midpoint Calculator'],
    how_to_use=['Enter both points', 'Read slope, distance and midpoint'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("x1", "x1", OptionType.number, default=0),
        _opt("y1", "y1", OptionType.number, default=0),
        _opt("x2", "x2", OptionType.number, default=4),
        _opt("y2", "y2", OptionType.number, default=3),
    ],
))
define(ToolConfig(
    name="Perimeter Calculator", slug="perimeter-calculator", category="calculators",
    description="Find the perimeter or circumference of common shapes.",
    seo_keywords=['Perimeter Calculator', 'Circumference Calculator', 'Shape Perimeter'],
    how_to_use=['Choose the shape', 'Enter measurements', 'Read the perimeter'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("shape", "Shape", OptionType.select, default="rectangle", choices=["rectangle", "square", "circle", "triangle"]),
        _opt("a", "Length / side / radius", OptionType.number, default=10, min=0),
        _opt("b", "Width / second side", OptionType.number, default=5, min=0),
        _opt("c", "Third side", OptionType.number, default=7, min=0),
    ],
))
define(ToolConfig(
    name="Triangle Calculator", slug="triangle-calculator", category="calculators",
    description="Find area, perimeter and angles from three sides.",
    seo_keywords=['Triangle Calculator', 'Triangle Area', 'Heron Formula'],
    how_to_use=['Enter the three sides', 'Read area and angles'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("a", "Side a", OptionType.number, default=3, min=0),
        _opt("b", "Side b", OptionType.number, default=4, min=0),
        _opt("c", "Side c", OptionType.number, default=5, min=0),
    ],
))
define(ToolConfig(
    name="Ohms Law Calculator", slug="ohms-law-calculator", category="calculators",
    description="Enter any two of volts, amps and ohms to find the rest.",
    seo_keywords=['Ohms Law Calculator', 'Voltage Calculator', 'Watts Calculator'],
    how_to_use=['Enter any two values', 'Leave the third at zero', 'Read the rest'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("volts", "Volts", OptionType.number, default=12, min=0),
        _opt("amps", "Amps", OptionType.number, default=0, min=0),
        _opt("ohms", "Ohms", OptionType.number, default=4, min=0),
    ],
))
define(ToolConfig(
    name="Resistor Color Code Calculator", slug="resistor-color-code-calculator", category="calculators",
    description="Read a resistor's value from its colour bands.",
    seo_keywords=['Resistor Color Code', 'Resistor Calculator', 'Band Colour Code'],
    how_to_use=['Pick each band colour', 'Read the resistance'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("band1", "Band 1", OptionType.select, default="brown", choices=["black","brown","red","orange","yellow","green","blue","violet","grey","white"]),
        _opt("band2", "Band 2", OptionType.select, default="black", choices=["black","brown","red","orange","yellow","green","blue","violet","grey","white"]),
        _opt("multiplier", "Multiplier", OptionType.select, default="red", choices=["black","brown","red","orange","yellow","green","blue","violet","grey","white","gold","silver"]),
        _opt("tolerance", "Tolerance", OptionType.select, default="gold", choices=["brown","red","green","blue","violet","gold","silver"]),
    ],
))
define(ToolConfig(
    name="Pressure Converter", slug="pressure-converter", category="calculators",
    description="Convert between Pa, kPa, bar, psi, atm and mmHg.",
    seo_keywords=['Pressure Converter', 'psi to bar', 'Pressure Units'],
    how_to_use=['Enter the value', 'Pick the units', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=1),
        _opt("from", "From", OptionType.select, default="bar", choices=['Pa', 'kPa', 'bar', 'psi', 'atm', 'mmHg']),
        _opt("to", "To", OptionType.select, default="psi", choices=['Pa', 'kPa', 'bar', 'psi', 'atm', 'mmHg']),
    ],
))
define(ToolConfig(
    name="Energy Converter", slug="energy-converter", category="calculators",
    description="Convert joules, calories, watt-hours and BTU.",
    seo_keywords=['Energy Converter', 'Joules To Calories', 'kWh Converter'],
    how_to_use=['Enter the value', 'Pick the units', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=1),
        _opt("from", "From", OptionType.select, default="kWh", choices=['J', 'kJ', 'cal', 'kcal', 'Wh', 'kWh', 'BTU']),
        _opt("to", "To", OptionType.select, default="kJ", choices=['J', 'kJ', 'cal', 'kcal', 'Wh', 'kWh', 'BTU']),
    ],
))
define(ToolConfig(
    name="Power Converter", slug="power-converter", category="calculators",
    description="Convert watts, kilowatts, megawatts and horsepower.",
    seo_keywords=['Power Converter', 'Watts To Horsepower', 'kW to hp'],
    how_to_use=['Enter the value', 'Pick the units', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=1),
        _opt("from", "From", OptionType.select, default="kW", choices=['W', 'kW', 'MW', 'hp']),
        _opt("to", "To", OptionType.select, default="hp", choices=['W', 'kW', 'MW', 'hp']),
    ],
))
define(ToolConfig(
    name="Fuel Economy Converter", slug="fuel-economy-converter", category="calculators",
    description="Convert between mpg, km/l and L/100km.",
    seo_keywords=['Fuel Economy Converter', 'MPG To L100km', 'Fuel Consumption'],
    how_to_use=['Enter the figure', 'Choose its unit', 'Read every other unit'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=30, min=0),
        _opt("from", "Unit", OptionType.select, default="mpg (US)", choices=["mpg (US)", "mpg (UK)", "km/l", "L/100km"]),
    ],
))
define(ToolConfig(
    name="Cooking Converter", slug="cooking-converter", category="calculators",
    description="Convert cups, tablespoons, teaspoons, millilitres and more.",
    seo_keywords=['Cooking Converter', 'Cups To ML', 'Recipe Converter'],
    how_to_use=['Enter the value', 'Pick the units', 'Read the result'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=1),
        _opt("from", "From", OptionType.select, default="cup", choices=['ml', 'l', 'tsp', 'tbsp', 'cup', 'pt', 'qt', 'gal', 'fl oz']),
        _opt("to", "To", OptionType.select, default="ml", choices=['ml', 'l', 'tsp', 'tbsp', 'cup', 'pt', 'qt', 'gal', 'fl oz']),
    ],
))
define(ToolConfig(
    name="Shoe Size Converter", slug="shoe-size-converter", category="calculators",
    description="Convert shoe sizes between US, UK and EU.",
    seo_keywords=['Shoe Size Converter', 'US To EU Shoe Size', 'Shoe Size Chart'],
    how_to_use=['Enter the size', 'Choose the region', 'Read every other size'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("size", "Size", OptionType.number, default=9, min=0),
        _opt("from", "Region", OptionType.select, default="US men", choices=["US men", "US women", "UK", "EU"]),
    ],
))
define(ToolConfig(
    name="Grade Calculator", slug="grade-calculator", category="calculators",
    description="Work out a weighted grade and what you still need to score.",
    seo_keywords=['Grade Calculator', 'Weighted Grade', 'Final Grade Calculator'],
    how_to_use=['Enter your scores', 'Enter matching weights', 'Add a target if you like'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("scores", "Scores (comma separated)", OptionType.text, default="85, 90, 78"),
        _opt("weights", "Weights (comma separated)", OptionType.text, default="30, 30, 40"),
        _opt("target_grade", "Target grade (optional)", OptionType.number, default=0, min=0, max=100),
        _opt("remaining_weight", "Remaining weight (optional)", OptionType.number, default=0, min=0, max=100),
    ],
))
define(ToolConfig(
    name="Split Bill Calculator", slug="split-bill-calculator", category="calculators",
    description="Split a bill with tip and tax between any number of people.",
    seo_keywords=['Split Bill Calculator', 'Bill Splitter', 'Share The Bill'],
    how_to_use=['Enter the bill', 'Add tip and tax', 'Choose how many people'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("bill", "Bill amount", OptionType.number, default=120, min=0),
        _opt("people", "People", OptionType.number, default=4, min=1, max=100),
        _opt("tip_percent", "Tip (%)", OptionType.number, default=10, min=0),
        _opt("tax_percent", "Tax (%)", OptionType.number, default=0, min=0),
    ],
))
define(ToolConfig(
    name="Mileage Calculator", slug="mileage-calculator", category="calculators",
    description="Work out mileage reimbursement for a journey.",
    seo_keywords=['Mileage Calculator', 'Mileage Reimbursement', 'Travel Expenses'],
    how_to_use=['Enter the distance', 'Enter the rate', 'Read the total'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("distance", "Distance (km)", OptionType.number, default=1200, min=0),
        _opt("rate_per_km", "Rate per km", OptionType.number, default=0.45, min=0),
    ],
))
define(ToolConfig(
    name="Concrete Calculator", slug="concrete-calculator", category="calculators",
    description="Work out how much concrete a slab needs.",
    seo_keywords=['Concrete Calculator', 'Concrete Volume', 'Cement Calculator'],
    how_to_use=['Enter the slab size', 'Set the depth', 'Read the volume and bags'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("length_m", "Length (m)", OptionType.number, default=5, min=0),
        _opt("width_m", "Width (m)", OptionType.number, default=3, min=0),
        _opt("depth_cm", "Depth (cm)", OptionType.number, default=10, min=0),
        _opt("waste_percent", "Waste allowance (%)", OptionType.number, default=10, min=0, max=50),
    ],
))
define(ToolConfig(
    name="Tile Calculator", slug="tile-calculator", category="calculators",
    description="Work out how many tiles a floor or wall needs.",
    seo_keywords=['Tile Calculator', 'Flooring Calculator', 'How Many Tiles'],
    how_to_use=['Enter the area', 'Enter your tile size', 'Read the count'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("area_m2", "Area (m²)", OptionType.number, default=20, min=0),
        _opt("tile_width_cm", "Tile width (cm)", OptionType.number, default=30, min=1),
        _opt("tile_height_cm", "Tile height (cm)", OptionType.number, default=30, min=1),
        _opt("waste_percent", "Waste allowance (%)", OptionType.number, default=10, min=0, max=50),
    ],
))
define(ToolConfig(
    name="Carbon Footprint Calculator", slug="carbon-footprint-calculator", category="calculators",
    description="Estimate your yearly CO2 from driving, electricity and flights.",
    seo_keywords=['Carbon Footprint Calculator', 'CO2 Calculator', 'Emissions Calculator'],
    how_to_use=['Enter your driving', 'Add your electricity use', 'Add flight hours'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("car_km_per_year", "Car km per year", OptionType.number, default=12000, min=0),
        _opt("electricity_kwh_per_month", "Electricity (kWh/month)", OptionType.number, default=300, min=0),
        _opt("flight_hours_per_year", "Flight hours per year", OptionType.number, default=10, min=0),
    ],
))
define(ToolConfig(
    name="Dice Roller", slug="dice-roller", category="calculators",
    description="Roll any number of dice with any number of sides.",
    seo_keywords=['Dice Roller', 'Roll Dice Online', 'Random Dice'],
    how_to_use=['Choose the sides', 'Choose how many', 'Roll'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("sides", "Sides per die", OptionType.number, default=6, min=2, max=1000),
        _opt("count", "How many dice", OptionType.number, default=2, min=1, max=100),
    ],
))
define(ToolConfig(
    name="Time Duration Calculator", slug="time-duration-calculator", category="calculators",
    description="Find the time between two clock times.",
    seo_keywords=['Time Duration Calculator', 'Hours Between Times', 'Time Difference'],
    how_to_use=['Enter both times', 'Read the duration'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("start_time", "Start (HH:MM)", OptionType.text, default="09:00"),
        _opt("end_time", "End (HH:MM)", OptionType.text, default="17:30"),
    ],
))
define(ToolConfig(
    name="Time Calculator", slug="time-calculator", category="calculators",
    description="Add or subtract hours and minutes from a time.",
    seo_keywords=['Time Calculator', 'Add Hours To Time', 'Time Math'],
    how_to_use=['Enter the time', 'Choose add or subtract', 'Enter hours and minutes'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("time", "Time (HH:MM)", OptionType.text, default="14:30"),
        _opt("operation", "Operation", OptionType.select, default="add", choices=["add", "subtract"]),
        _opt("hours", "Hours", OptionType.number, default=2),
        _opt("minutes", "Minutes", OptionType.number, default=45),
    ],
))
define(ToolConfig(
    name="Time Zone Converter", slug="timezone-converter", category="calculators",
    description="Convert a time between any two world time zones.",
    seo_keywords=['Time Zone Converter', 'World Clock', 'UTC Converter'],
    how_to_use=['Enter the time', 'Choose both zones', 'Read the converted time'],
    input_kind=InputKind.options, supports_single_upload=False, supports_download=False,
    options=[
        _opt("datetime", "Date and time (YYYY-MM-DD HH:MM, blank = now)", OptionType.text, default=""),
        _opt("from_zone", "From zone", OptionType.text, default="UTC"),
        _opt("to_zone", "To zone", OptionType.text, default="Asia/Karachi"),
    ],
))
