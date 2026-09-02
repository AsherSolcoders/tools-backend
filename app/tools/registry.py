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

_SEO_CONTENT = """
<p>ToolSimpli's free SEO tools cover the checks you actually run before a page goes live. Generate the meta tags, Open Graph tags and canonical link that decide how a page looks when it is shared or listed, preview the result as a SERP snippet, and confirm the title and description fit before Google truncates them.</p>
<p>Structured data is where most sites lose rich results. The schema markup generator writes valid JSON-LD for articles, products, FAQs, breadcrumbs, local businesses and reviews, and the structured data validator checks what you already have — so a missing required field is caught here rather than in Search Console six weeks later.</p>
<p>For on-page work, paste your HTML and get the heading structure, image alt coverage, internal and outbound links, anchor text spread and code-to-text ratio in one pass. Content tools cover keyword density, keyword prominence, keyword combinations and a content brief you can hand to a writer. Technical tools generate robots.txt, XML sitemaps, hreflang tags and .htaccess redirects, and test a robots.txt against a URL before you deploy it.</p>
<p>Every tool runs on what you paste in. Nothing is crawled, nothing is stored, and no account is needed. Pick a tool below and get the answer in a couple of seconds.</p>
"""

CATEGORIES: list[Category] = [
    Category(
        "seo-tools", "SEO Tools", "Meta tags, schema markup, sitemaps and on-page audits.", "trending-up",
        meta_title="Free SEO Tools – Meta Tags, Schema, Sitemap & On-Page Audit | ToolSimpli",
        meta_description="Free online SEO tools to generate meta tags, Open Graph, schema markup, robots.txt and sitemaps, plus on-page checks for headings, alt text and links. No signup.",
        content=_SEO_CONTENT.strip(),
    ),
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
define(ToolConfig(
    name="Sentence and Paragraph Counter", slug="sentence-paragraph-counter", category="text-tools",
    description="Count sentences and paragraphs, with averages for each.",
    seo_keywords=['Sentence Counter', 'Paragraph Counter', 'Sentence Count Tool'],
    how_to_use=['Paste your text', 'Read the counts'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Line Counter", slug="line-counter", category="text-tools",
    description="Count total, empty, unique and longest lines.",
    seo_keywords=['Line Counter', 'Count Lines', 'Line Count Tool'],
    how_to_use=['Paste your text', 'Read the line counts'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Keyword Density Checker", slug="keyword-density-checker", category="text-tools",
    description="See which words dominate your text, and by how much.",
    seo_keywords=['Keyword Density Checker', 'Word Frequency', 'Keyword Density Tool'],
    how_to_use=['Paste your text', 'Set the minimum word length', 'Read the densities'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("min_length", "Minimum word length", OptionType.number, default=3, min=1, max=20),
        _opt("top", "How many keywords", OptionType.number, default=20, min=1, max=100),
    ],
))
define(ToolConfig(
    name="Readability Checker", slug="readability-checker", category="text-tools",
    description="Score your writing with Flesch, Flesch-Kincaid and Gunning Fog.",
    seo_keywords=['Readability Checker', 'Flesch Reading Ease', 'Readability Score'],
    how_to_use=['Paste your text', 'Read the score and grade level'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Text Analyzer", slug="text-analyzer", category="text-tools",
    description="Full statistics for any text in one pass.",
    seo_keywords=['Text Analyzer', 'Text Statistics', 'Text Analysis Tool'],
    how_to_use=['Paste your text', 'Read the statistics'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Headline Analyzer", slug="headline-analyzer", category="text-tools",
    description="Score a headline on length, numbers and power words.",
    seo_keywords=['Headline Analyzer', 'Title Analyzer', 'Headline Score'],
    how_to_use=['Type your headline', 'Read the score and suggestions'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Text Summarizer", slug="text-summarizer", category="text-tools",
    description="Shorten long text by keeping only its most important sentences.",
    seo_keywords=['Text Summarizer', 'Summarize Text', 'Article Summarizer'],
    how_to_use=['Paste your text', 'Choose how many sentences', 'Read the summary'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("sentences", "Sentences to keep", OptionType.number, default=3, min=1, max=20),
    ],
))
define(ToolConfig(
    name="Style Checker", slug="style-checker", category="text-tools",
    description="Catch repeated words, spacing slips and sentences that run too long.",
    seo_keywords=['Style Checker', 'Punctuation Checker', 'Writing Checker'],
    how_to_use=['Paste your text', 'Review the issues found'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Palindrome Checker", slug="palindrome-checker", category="text-tools",
    description="Check whether a word or phrase reads the same backwards.",
    seo_keywords=['Palindrome Checker', 'Is It A Palindrome', 'Palindrome Test'],
    how_to_use=['Type a word or phrase', 'See the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Uppercase Converter", slug="uppercase-converter", category="text-tools",
    description="Turn any text into UPPERCASE.",
    seo_keywords=['Uppercase Converter', 'Text To Uppercase', 'Capital Letters'],
    how_to_use=['Paste your text', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Lowercase Converter", slug="lowercase-converter", category="text-tools",
    description="Turn any text into lowercase.",
    seo_keywords=['Lowercase Converter', 'Text To Lowercase', 'Small Letters'],
    how_to_use=['Paste your text', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Capitalize Each Word", slug="capitalize-each-word", category="text-tools",
    description="Capitalize the first letter of every word, leaving acronyms intact.",
    seo_keywords=['Capitalize Each Word', 'Title Case Converter', 'Capitalize Text'],
    how_to_use=['Paste your text', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Remove Extra Spaces", slug="remove-extra-spaces", category="text-tools",
    description="Collapse repeated spaces and tabs down to one.",
    seo_keywords=['Remove Extra Spaces', 'Remove Double Spaces', 'Space Remover'],
    how_to_use=['Paste your text', 'Copy the cleaned text'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Trim Whitespace", slug="trim-whitespace", category="text-tools",
    description="Strip spaces from the start, the end, or both ends of every line.",
    seo_keywords=['Trim Whitespace', 'Trim Spaces', 'Whitespace Remover'],
    how_to_use=['Paste your text', 'Choose which end', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("where", "Trim", OptionType.select, default="both", choices=["both", "start", "end"]),
    ],
))
define(ToolConfig(
    name="Remove Line Breaks", slug="remove-line-breaks", category="text-tools",
    description="Join wrapped lines back into flowing paragraphs.",
    seo_keywords=['Remove Line Breaks', 'Remove Newlines', 'Join Lines'],
    how_to_use=['Paste your text', 'Choose whether to keep paragraphs', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("keep_paragraphs", "Keep paragraph breaks", OptionType.boolean, default=True),
        _opt("add_space", "Add a space where lines join", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Add Line Breaks", slug="add-line-breaks", category="text-tools",
    description="Wrap text to a set width, or break it after a chosen character.",
    seo_keywords=['Add Line Breaks', 'Insert Line Breaks', 'Wrap Text'],
    how_to_use=['Paste your text', 'Choose wrap width or a marker', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Break", OptionType.select, default="width", choices=["width", "after"]),
        _opt("width", "Wrap width", OptionType.number, default=80, min=10, max=500),
        _opt("after", "Break after this character", OptionType.text, default="."),
    ],
))
define(ToolConfig(
    name="Remove Empty Lines", slug="remove-empty-lines", category="text-tools",
    description="Delete blank lines from a list or a document.",
    seo_keywords=['Remove Empty Lines', 'Delete Blank Lines', 'Remove Blank Rows'],
    how_to_use=['Paste your text', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Remove Specific Characters", slug="remove-specific-characters", category="text-tools",
    description="Strip chosen characters, all punctuation, or all digits.",
    seo_keywords=['Remove Characters', 'Remove Symbols', 'Character Remover'],
    how_to_use=['Paste your text', 'Enter the characters to remove', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("characters", "Characters to remove", OptionType.text, default=""),
        _opt("remove_punctuation", "Remove all punctuation", OptionType.boolean, default=False),
        _opt("remove_digits", "Remove all digits", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Text Cleaner", slug="text-cleaner", category="text-tools",
    description="Every tidy-up in one pass — spacing, blank lines, HTML, smart quotes.",
    seo_keywords=['Text Cleaner', 'Clean Text Online', 'Text Formatter'],
    how_to_use=['Paste your text', 'Tick what to clean', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("fix_smart_quotes", "Straighten curly quotes and dashes", OptionType.boolean, default=True),
        _opt("single_spaces", "Collapse repeated spaces", OptionType.boolean, default=True),
        _opt("remove_empty_lines", "Remove blank lines", OptionType.boolean, default=True),
        _opt("strip_html", "Strip HTML tags", OptionType.boolean, default=False),
        _opt("remove_urls", "Remove URLs", OptionType.boolean, default=False),
        _opt("remove_punctuation", "Remove punctuation", OptionType.boolean, default=False),
        _opt("remove_numbers", "Remove numbers", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Find and Replace", slug="find-and-replace", category="text-tools",
    description="Replace text across a whole document, with optional regex.",
    seo_keywords=['Find And Replace', 'Replace Text Online', 'Search And Replace'],
    how_to_use=['Paste your text', 'Enter what to find and what to replace it with', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("find", "Find", OptionType.text, default=""),
        _opt("replace", "Replace with", OptionType.text, default=""),
        _opt("case_sensitive", "Match case", OptionType.boolean, default=True),
        _opt("regex", "Treat as a regular expression", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Shuffle Lines", slug="shuffle-lines", category="text-tools",
    description="Put a list of lines into random order.",
    seo_keywords=['Shuffle Lines', 'Randomize Lines', 'Random Line Order'],
    how_to_use=['Paste your lines', 'Shuffle', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Add Prefix and Suffix", slug="add-prefix-suffix", category="text-tools",
    description="Wrap every line with text of your choice.",
    seo_keywords=['Add Prefix To Lines', 'Add Suffix', 'Prefix Suffix Tool'],
    how_to_use=['Paste your lines', 'Enter a prefix or suffix', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("prefix", "Prefix", OptionType.text, default=""),
        _opt("suffix", "Suffix", OptionType.text, default=""),
        _opt("skip_empty", "Skip blank lines", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Add Line Numbers", slug="add-line-numbers", category="text-tools",
    description="Number every line, with your own separator.",
    seo_keywords=['Add Line Numbers', 'Number Lines', 'Line Numbering Tool'],
    how_to_use=['Paste your text', 'Set the starting number', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("start", "Start at", OptionType.number, default=1),
        _opt("separator", "Separator", OptionType.text, default=". "),
        _opt("pad", "Line up the numbers", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Text Repeater", slug="text-repeater", category="text-tools",
    description="Repeat text as many times as you need.",
    seo_keywords=['Text Repeater', 'Repeat Text', 'Duplicate Text'],
    how_to_use=['Paste your text', 'Choose how many times', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("times", "Repetitions", OptionType.number, default=5, min=1, max=10000),
        _opt("separator", "Separated by", OptionType.select, default="newline", choices=["newline", "space", "comma", "none"]),
    ],
))
define(ToolConfig(
    name="Column Extractor", slug="column-extractor", category="text-tools",
    description="Pull a single column out of CSV or other delimited text.",
    seo_keywords=['Column Extractor', 'CSV Column Extractor', 'Split Columns'],
    how_to_use=['Paste your rows', 'Pick the delimiter and column', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("delimiter", "Delimiter", OptionType.select, default="comma", choices=["comma", "tab", "pipe", "semicolon", "space"]),
        _opt("column", "Column number", OptionType.number, default=1, min=1, max=200),
    ],
))
define(ToolConfig(
    name="Single Line Converter", slug="single-line-converter", category="text-tools",
    description="Collapse text into one line, or split one line back out.",
    seo_keywords=['Text To One Line', 'Multi Line To Single Line', 'Line Joiner'],
    how_to_use=['Paste your text', 'Choose the direction', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Convert", OptionType.select, default="to_single", choices=["to_single", "to_lines"]),
        _opt("separator", "Separator", OptionType.text, default=" "),
    ],
))
define(ToolConfig(
    name="Text Diff Checker", slug="text-diff", category="text-tools",
    description="Compare two texts and see exactly what changed.",
    seo_keywords=['Text Diff', 'Compare Text', 'Text Comparison Tool'],
    how_to_use=['Paste the original', 'Paste the changed version', 'Read the differences'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("compare_with", "Compare with", OptionType.text, default=""),
        _opt("ignore_case", "Ignore case", OptionType.boolean, default=False),
        _opt("ignore_whitespace", "Ignore leading and trailing spaces", OptionType.boolean, default=False),
        _opt("context", "Context lines", OptionType.number, default=2, min=0, max=10),
    ],
))
define(ToolConfig(
    name="Common and Unique Lines", slug="common-unique-lines", category="text-tools",
    description="Find the lines two lists share, or the ones only one has.",
    seo_keywords=['Compare Lists', 'Common Lines', 'Unique Lines Finder'],
    how_to_use=['Paste both lists', 'Choose what to keep', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("compare_with", "Second list", OptionType.text, default=""),
        _opt("mode", "Keep", OptionType.select, default="common", choices=["common", "only_first", "only_second", "not_shared"]),
        _opt("case_sensitive", "Match case", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Base64 Text Converter", slug="base64-text", category="text-tools",
    description="Encode text to Base64, or decode it back.",
    seo_keywords=['Base64 Encode', 'Base64 Decode', 'Base64 Converter'],
    how_to_use=['Paste your text', 'Choose encode or decode', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Mode", OptionType.select, default="encode", choices=["encode", "decode"]),
        _opt("url_safe", "URL-safe alphabet", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="HTML Entity Converter", slug="html-entity-converter", category="text-tools",
    description="Escape text for HTML, or turn entities back into characters.",
    seo_keywords=['HTML Entity Encode', 'HTML Entity Decode', 'HTML Escape Tool'],
    how_to_use=['Paste your text', 'Choose encode or decode', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Mode", OptionType.select, default="encode", choices=["encode", "decode"]),
    ],
))
define(ToolConfig(
    name="Unicode Converter", slug="unicode-converter", category="text-tools",
    description="Move between readable text, \\uXXXX escapes and UTF-8 bytes.",
    seo_keywords=['Unicode Converter', 'UTF-8 Converter', 'Unicode Escape'],
    how_to_use=['Paste your text', 'Choose the direction', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Convert", OptionType.select, default="to_escapes", choices=["to_escapes", "from_escapes", "to_bytes", "from_bytes"]),
    ],
))
define(ToolConfig(
    name="Binary to Text Converter", slug="binary-text-converter", category="text-tools",
    description="Convert text to binary and binary back to text.",
    seo_keywords=['Binary To Text', 'Text To Binary', 'Binary Translator'],
    how_to_use=['Paste text or binary', 'Choose the direction', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Mode", OptionType.select, default="encode", choices=["encode", "decode"]),
    ],
))
define(ToolConfig(
    name="Hex to Text Converter", slug="hex-text-converter", category="text-tools",
    description="Convert text to hexadecimal and hex back to text.",
    seo_keywords=['Hex To Text', 'Text To Hex', 'Hexadecimal Converter'],
    how_to_use=['Paste text or hex', 'Choose the direction', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Mode", OptionType.select, default="encode", choices=["encode", "decode"]),
    ],
))
define(ToolConfig(
    name="ASCII and Octal Converter", slug="ascii-octal-converter", category="text-tools",
    description="Convert text to character codes in decimal or octal.",
    seo_keywords=['ASCII Converter', 'Octal Converter', 'Character Code Converter'],
    how_to_use=['Paste text or codes', 'Pick decimal or octal', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Mode", OptionType.select, default="encode", choices=["encode", "decode"]),
        _opt("base", "Number base", OptionType.select, default="decimal", choices=["decimal", "octal"]),
    ],
))
define(ToolConfig(
    name="ROT13 and Caesar Cipher", slug="caesar-cipher", category="text-tools",
    description="Shift letters by any amount — ROT13 by default.",
    seo_keywords=['ROT13', 'Caesar Cipher', 'Letter Shift Cipher'],
    how_to_use=['Paste your text', 'Set the shift', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Mode", OptionType.select, default="encode", choices=["encode", "decode"]),
        _opt("shift", "Shift by", OptionType.number, default=13, min=1, max=25),
    ],
))
define(ToolConfig(
    name="Morse Code Translator", slug="morse-code-translator", category="text-tools",
    description="Translate text to Morse code and back.",
    seo_keywords=['Morse Code Translator', 'Text To Morse', 'Morse Decoder'],
    how_to_use=['Paste text or Morse', 'Choose the direction', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Mode", OptionType.select, default="encode", choices=["encode", "decode"]),
    ],
))
define(ToolConfig(
    name="Number to Words Converter", slug="number-to-words", category="text-tools",
    description="Spell any number out in English words.",
    seo_keywords=['Number To Words', 'Number Spelling', 'Numbers In Words'],
    how_to_use=['Type a number', 'Copy the words'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Words to Number Converter", slug="words-to-number", category="text-tools",
    description="Turn a number written in words back into digits.",
    seo_keywords=['Words To Number', 'Text To Number', 'Word Number Converter'],
    how_to_use=['Type the number in words', 'Copy the digits'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Roman Numeral Converter", slug="roman-numeral-converter", category="text-tools",
    description="Convert between numbers and Roman numerals, both ways.",
    seo_keywords=['Roman Numeral Converter', 'Number To Roman', 'Roman To Number'],
    how_to_use=['Type a number or a numeral', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Email Extractor", slug="email-extractor", category="text-tools",
    description="Pull every email address out of a block of text.",
    seo_keywords=['Email Extractor', 'Extract Emails', 'Email Finder'],
    how_to_use=['Paste your text', 'Copy the addresses'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("unique", "Remove duplicates", OptionType.boolean, default=True),
        _opt("lowercase", "Lowercase them", OptionType.boolean, default=True),
        _opt("sort", "Sort alphabetically", OptionType.boolean, default=False),
        _opt("separator", "Separated by", OptionType.select, default="newline", choices=["newline", "comma"]),
    ],
))
define(ToolConfig(
    name="URL Extractor", slug="url-extractor", category="text-tools",
    description="Pull every link out of text or pasted HTML.",
    seo_keywords=['URL Extractor', 'Link Extractor', 'Extract URLs'],
    how_to_use=['Paste your text', 'Copy the links'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("unique", "Remove duplicates", OptionType.boolean, default=True),
        _opt("domains_only", "Domains only", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Phone Number Extractor", slug="phone-extractor", category="text-tools",
    description="Find phone numbers in any block of text.",
    seo_keywords=['Phone Number Extractor', 'Extract Phone Numbers', 'Phone Finder'],
    how_to_use=['Paste your text', 'Copy the numbers'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("unique", "Remove duplicates", OptionType.boolean, default=True),
        _opt("digits_only", "Strip formatting", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Number Extractor", slug="number-extractor", category="text-tools",
    description="Pull every number out of text, with a running total.",
    seo_keywords=['Number Extractor', 'Extract Numbers', 'Digit Extractor'],
    how_to_use=['Paste your text', 'Copy the numbers'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("include_decimals", "Include decimals", OptionType.boolean, default=True),
        _opt("unique", "Remove duplicates", OptionType.boolean, default=False),
        _opt("sort", "Sort smallest first", OptionType.boolean, default=False),
        _opt("separator", "Separated by", OptionType.select, default="newline", choices=["newline", "comma"]),
    ],
))
define(ToolConfig(
    name="Text Between Delimiters", slug="delimiter-extractor", category="text-tools",
    description="Extract everything sitting between two markers.",
    seo_keywords=['Extract Text Between', 'Delimiter Extractor', 'Text Between Characters'],
    how_to_use=['Paste your text', 'Set the opening and closing markers', 'Copy the matches'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("start", "Opening marker", OptionType.text, default="["),
        _opt("end", "Closing marker", OptionType.text, default="]"),
        _opt("include_markers", "Keep the markers", OptionType.boolean, default=False),
        _opt("across_lines", "Match across lines", OptionType.boolean, default=False),
        _opt("unique", "Remove duplicates", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Random String Generator", slug="random-string-generator", category="text-tools",
    description="Generate random strings, passwords and keys.",
    seo_keywords=['Random String Generator', 'Password Generator', 'Random Key Generator'],
    how_to_use=['Set the length', 'Pick the character sets', 'Generate'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("length", "Length", OptionType.number, default=16, min=1, max=512),
        _opt("count", "How many", OptionType.number, default=5, min=1, max=200),
        _opt("lowercase", "Lowercase letters", OptionType.boolean, default=True),
        _opt("uppercase", "Uppercase letters", OptionType.boolean, default=True),
        _opt("digits", "Digits", OptionType.boolean, default=True),
        _opt("symbols", "Symbols", OptionType.boolean, default=False),
        _opt("exclude_ambiguous", "Avoid look-alike characters", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Random Word Generator", slug="random-word-generator", category="text-tools",
    description="Generate random words or names for names, tests and games.",
    seo_keywords=['Random Word Generator', 'Random Name Generator', 'Word Picker'],
    how_to_use=['Choose words or names', 'Set how many', 'Generate'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Generate", OptionType.select, default="words", choices=["words", "names"]),
        _opt("count", "How many", OptionType.number, default=10, min=1, max=500),
        _opt("unique", "No repeats", OptionType.boolean, default=True),
        _opt("capitalize", "Capitalize", OptionType.boolean, default=False),
        _opt("separator", "Separated by", OptionType.select, default="newline", choices=["newline", "comma"]),
    ],
))
define(ToolConfig(
    name="Username Generator", slug="username-generator", category="text-tools",
    description="Generate available-looking usernames and handles.",
    seo_keywords=['Username Generator', 'Handle Generator', 'Nickname Generator'],
    how_to_use=['Optionally type a base word', 'Pick a style', 'Generate'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("style", "Style", OptionType.select, default="word_word", choices=["word_word", "name_number", "word_word_number"]),
        _opt("separator", "Joiner", OptionType.text, default="_"),
        _opt("count", "How many", OptionType.number, default=10, min=1, max=200),
    ],
))
define(ToolConfig(
    name="Placeholder Data Generator", slug="placeholder-data-generator", category="text-tools",
    description="Generate fake rows for testing, as JSON, CSV or SQL.",
    seo_keywords=['Placeholder Data Generator', 'Fake Data Generator', 'Test Data Generator'],
    how_to_use=['Choose the format', 'Set how many rows', 'Generate'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("rows", "Rows", OptionType.number, default=10, min=1, max=500),
        _opt("format", "Format", OptionType.select, default="json", choices=["json", "csv", "sql"]),
    ],
))
define(ToolConfig(
    name="Fancy Text Generator", slug="fancy-text-generator", category="text-tools",
    description="Turn text into every Unicode style at once — bold, script, bubble and more.",
    seo_keywords=['Fancy Text Generator', 'Stylish Text', 'Cool Fonts Copy Paste'],
    how_to_use=['Type your text', 'Pick the style you like', 'Copy it'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Bold and Italic Unicode Text", slug="bold-italic-text", category="text-tools",
    description="Bold, italic, script, fraktur and monospace text you can paste anywhere.",
    seo_keywords=['Bold Text Generator', 'Italic Text Generator', 'Unicode Font Converter'],
    how_to_use=['Type your text', 'Choose a style', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("style", "Style", OptionType.select, default="bold", choices=["bold", "italic", "bold italic", "script", "bold script", "fraktur", "double-struck", "sans-serif", "sans bold", "sans italic", "monospace", "wide"]),
    ],
))
define(ToolConfig(
    name="Small Text and Superscript Generator", slug="small-superscript-text", category="text-tools",
    description="Small caps, superscript and subscript text.",
    seo_keywords=['Small Text Generator', 'Superscript Generator', 'Subscript Text'],
    how_to_use=['Type your text', 'Choose a style', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("style", "Style", OptionType.select, default="small caps", choices=["small caps", "superscript", "subscript"]),
    ],
))
define(ToolConfig(
    name="Strikethrough and Underline Text", slug="strikethrough-text", category="text-tools",
    description="Add a strike, underline or overline that survives copy and paste.",
    seo_keywords=['Strikethrough Text', 'Underline Text Generator', 'Crossed Out Text'],
    how_to_use=['Type your text', 'Choose a style', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("style", "Style", OptionType.select, default="strikethrough", choices=["strikethrough", "underline", "double underline", "overline", "slash"]),
    ],
))
define(ToolConfig(
    name="Bubble and Square Text", slug="bubble-square-text", category="text-tools",
    description="Turn letters into circled or squared characters.",
    seo_keywords=['Bubble Text Generator', 'Circled Text', 'Square Text Generator'],
    how_to_use=['Type your text', 'Choose bubble or square', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("style", "Style", OptionType.select, default="bubble", choices=["bubble", "square"]),
    ],
))
define(ToolConfig(
    name="Zalgo Glitch Text Generator", slug="zalgo-text-generator", category="text-tools",
    description="Create the corrupted, glitchy Zalgo look.",
    seo_keywords=['Zalgo Text Generator', 'Glitch Text', 'Cursed Text Generator'],
    how_to_use=['Type your text', 'Set the intensity', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("intensity", "Intensity", OptionType.number, default=5, min=1, max=30),
        _opt("above", "Marks above", OptionType.boolean, default=True),
        _opt("below", "Marks below", OptionType.boolean, default=True),
        _opt("middle", "Marks through", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Upside Down Text Generator", slug="upside-down-text", category="text-tools",
    description="Flip text upside down for bios and posts.",
    seo_keywords=['Upside Down Text', 'Flip Text', 'Reverse Text Generator'],
    how_to_use=['Type your text', 'Copy the flipped result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("reverse", "Reverse the order too", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="ASCII Art Generator", slug="ascii-art-generator", category="text-tools",
    description="Draw short words as large block letters.",
    seo_keywords=['ASCII Art Generator', 'Text To ASCII Art', 'Block Letter Generator'],
    how_to_use=['Type a short word', 'Pick the fill character', 'Copy the art'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("character", "Fill character", OptionType.text, default="#"),
        _opt("spacing", "Space between letters", OptionType.number, default=1, min=0, max=5),
    ],
))
define(ToolConfig(
    name="Markdown to HTML Converter", slug="markdown-to-html", category="text-tools",
    description="Turn Markdown into clean, safe HTML.",
    seo_keywords=['Markdown To HTML', 'MD To HTML Converter', 'Markdown Converter'],
    how_to_use=['Paste your Markdown', 'Copy the HTML'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="HTML to Markdown Converter", slug="html-to-markdown", category="text-tools",
    description="Turn HTML back into readable Markdown.",
    seo_keywords=['HTML To Markdown', 'HTML To MD Converter', 'Markdown From HTML'],
    how_to_use=['Paste your HTML', 'Copy the Markdown'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Hashtag Generator", slug="hashtag-generator", category="text-tools",
    description="Turn a topic or caption into ready-to-post hashtags.",
    seo_keywords=['Hashtag Generator', 'Social Tag Generator', 'Instagram Hashtags'],
    how_to_use=['Enter a topic or paste a caption', 'Choose how many', 'Copy the hashtags'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("count", "How many", OptionType.number, default=20, min=1, max=60),
        _opt("style", "Style", OptionType.select, default="lowercase", choices=["lowercase", "camel"]),
        _opt("combine", "Include two-word tags", OptionType.boolean, default=True),
        _opt("separator", "Separated by", OptionType.select, default="space", choices=["space", "newline"]),
    ],
))
define(ToolConfig(
    name="JSON Viewer", slug="json-viewer", category="developer-tools",
    description="Flatten JSON into one searchable path per value.",
    seo_keywords=['JSON Viewer', 'JSON Tree Explorer', 'JSON Path Viewer'],
    how_to_use=['Paste your JSON', 'Read the paths'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("limit", "Rows to show", OptionType.number, default=500, min=1, max=5000),
    ],
))
define(ToolConfig(
    name="JSON Diff", slug="json-diff", category="developer-tools",
    description="Compare two JSON documents by value, not by text.",
    seo_keywords=['JSON Diff', 'Compare JSON', 'JSON Comparison Tool'],
    how_to_use=['Paste the first JSON', 'Paste the second', 'Read the differences'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("compare_with", "Second JSON", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="JSONPath Tester", slug="jsonpath-tester", category="developer-tools",
    description="Query JSON with a dotted path and see what it returns.",
    seo_keywords=['JSONPath Tester', 'JSON Query Tool', 'JSON Path Evaluator'],
    how_to_use=['Paste your JSON', 'Enter a path like users[0].email', 'Read the matches'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("query", "Path", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="JSON to YAML Converter", slug="json-yaml-converter", category="developer-tools",
    description="Convert JSON to YAML and YAML back to JSON.",
    seo_keywords=['JSON To YAML', 'YAML To JSON', 'YAML Converter'],
    how_to_use=['Paste JSON or YAML', 'Choose the direction', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("direction", "Convert", OptionType.select, default="json_to_yaml", choices=["json_to_yaml", "yaml_to_json"]),
        _opt("indent", "JSON indent", OptionType.number, default=2, min=0, max=8),
        _opt("sort_keys", "Sort keys", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="JSON to XML Converter", slug="json-xml-converter", category="developer-tools",
    description="Convert JSON to XML and XML back to JSON.",
    seo_keywords=['JSON To XML', 'XML To JSON', 'XML Converter'],
    how_to_use=['Paste JSON or XML', 'Choose the direction', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("direction", "Convert", OptionType.select, default="json_to_xml", choices=["json_to_xml", "xml_to_json"]),
        _opt("root", "Root element name", OptionType.text, default="root"),
        _opt("indent", "Indent", OptionType.number, default=2, min=0, max=8),
    ],
))
define(ToolConfig(
    name="JSON to CSV Converter", slug="json-csv-converter", category="developer-tools",
    description="Convert JSON to CSV or TSV, and CSV back to JSON.",
    seo_keywords=['JSON To CSV', 'CSV To JSON', 'JSON CSV Converter'],
    how_to_use=['Paste JSON or CSV', 'Choose the direction', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("direction", "Convert", OptionType.select, default="json_to_csv", choices=["json_to_csv", "csv_to_json"]),
        _opt("delimiter", "Delimiter", OptionType.select, default="comma", choices=["comma", "tab", "semicolon", "pipe"]),
        _opt("parse_numbers", "Read numbers as numbers", OptionType.boolean, default=True),
        _opt("indent", "JSON indent", OptionType.number, default=2, min=0, max=8),
    ],
))
define(ToolConfig(
    name="TOML and INI Converter", slug="toml-ini-converter", category="developer-tools",
    description="Convert between TOML, INI and JSON.",
    seo_keywords=['TOML To JSON', 'INI To JSON', 'TOML Converter'],
    how_to_use=['Paste your config', 'Choose the direction', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("direction", "Convert", OptionType.select, default="toml_to_json", choices=["toml_to_json", "ini_to_json", "json_to_toml", "json_to_ini"]),
    ],
))
define(ToolConfig(
    name="JSON to TypeScript Types", slug="json-to-types", category="developer-tools",
    description="Turn a JSON sample into TypeScript, Python or Go models.",
    seo_keywords=['JSON To TypeScript', 'JSON To Types', 'JSON To Struct'],
    how_to_use=['Paste a JSON sample', 'Pick the language', 'Copy the types'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("language", "Language", OptionType.select, default="typescript", choices=["typescript", "python", "go"]),
        _opt("name", "Root type name", OptionType.text, default="Root"),
    ],
))
define(ToolConfig(
    name="cURL to Code Converter", slug="curl-to-code", category="developer-tools",
    description="Turn a cURL command into JavaScript, Python, Go or PHP.",
    seo_keywords=['cURL To Code', 'cURL Converter', 'cURL To Python'],
    how_to_use=['Paste your cURL command', 'Pick the language', 'Copy the code'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("language", "Language", OptionType.select, default="javascript", choices=["javascript", "python", "go", "php"]),
    ],
))
define(ToolConfig(
    name="CSS Beautifier", slug="css-beautifier", category="developer-tools",
    description="Re-indent minified CSS into something readable.",
    seo_keywords=['CSS Beautifier', 'CSS Formatter', 'Unminify CSS'],
    how_to_use=['Paste your CSS', 'Copy the formatted result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("indent", "Indent size", OptionType.number, default=2, min=0, max=8),
        _opt("remove_comments", "Remove comments", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="JavaScript Beautifier", slug="js-beautifier", category="developer-tools",
    description="Re-indent minified JavaScript or TypeScript.",
    seo_keywords=['JavaScript Beautifier', 'JS Formatter', 'Unminify JavaScript'],
    how_to_use=['Paste your code', 'Copy the formatted result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("indent", "Indent size", OptionType.number, default=2, min=0, max=8),
        _opt("keep_blank_lines", "Keep blank lines", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="SQL Formatter", slug="sql-formatter", category="developer-tools",
    description="Break a long SQL statement onto readable lines.",
    seo_keywords=['SQL Formatter', 'SQL Beautifier', 'Format SQL Query'],
    how_to_use=['Paste your query', 'Copy the formatted SQL'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("uppercase_keywords", "Uppercase keywords", OptionType.boolean, default=True),
        _opt("commas_on_new_lines", "One column per line", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="SQL Minifier", slug="sql-minifier", category="developer-tools",
    description="Strip comments and whitespace from an SQL statement.",
    seo_keywords=['SQL Minifier', 'Minify SQL', 'Compress SQL Query'],
    how_to_use=['Paste your query', 'Copy the minified SQL'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="XML Formatter", slug="xml-formatter", category="developer-tools",
    description="Pretty-print or minify XML, and catch syntax errors.",
    seo_keywords=['XML Formatter', 'XML Beautifier', 'XML Validator'],
    how_to_use=['Paste your XML', 'Copy the formatted result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("indent", "Indent size", OptionType.number, default=2, min=0, max=8),
        _opt("minify", "Minify instead", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="HTML Minifier", slug="html-minifier", category="developer-tools",
    description="Shrink HTML without breaking pre or textarea content.",
    seo_keywords=['HTML Minifier', 'Minify HTML', 'Compress HTML'],
    how_to_use=['Paste your HTML', 'Copy the minified result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("remove_comments", "Remove comments", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="JavaScript Obfuscator", slug="js-obfuscator", category="developer-tools",
    description="Hide string literals and strip comments from JavaScript.",
    seo_keywords=['JavaScript Obfuscator', 'JS Obfuscator', 'Obfuscate Code'],
    how_to_use=['Paste your JavaScript', 'Copy the obfuscated result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("minify", "Collapse blank lines", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="HTML Validator", slug="html-validator", category="developer-tools",
    description="Find unclosed tags, bad nesting and missing alt text.",
    seo_keywords=['HTML Validator', 'HTML Checker', 'Validate HTML'],
    how_to_use=['Paste your HTML', 'Review the issues'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="CSS Validator", slug="css-validator", category="developer-tools",
    description="Catch unbalanced braces and broken declarations.",
    seo_keywords=['CSS Validator', 'CSS Checker', 'Validate CSS'],
    how_to_use=['Paste your CSS', 'Review the issues'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="JavaScript Syntax Checker", slug="js-validator", category="developer-tools",
    description="Check brackets, quotes and comments before you debug.",
    seo_keywords=['JavaScript Validator', 'JS Syntax Checker', 'JavaScript Linter'],
    how_to_use=['Paste your JavaScript', 'Review the issues'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Hash Generator", slug="hash-generator", category="developer-tools",
    description="MD5, SHA-1, SHA-256, SHA-512 and more, from any text.",
    seo_keywords=['Hash Generator', 'MD5 Generator', 'SHA256 Generator'],
    how_to_use=['Paste your text', 'Pick an algorithm', 'Copy the hash'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("algorithm", "Algorithm", OptionType.select, default="all", choices=["all", "md5", "sha1", "sha224", "sha256", "sha384", "sha512", "sha3_256", "sha3_512", "blake2b"]),
        _opt("uppercase", "Uppercase output", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="File Hash Checker", slug="file-hash-checker", category="developer-tools",
    description="Hash a file and compare it against a published checksum.",
    seo_keywords=['File Hash Checker', 'Checksum Verifier', 'File SHA256'],
    how_to_use=['Upload the file', 'Paste the expected checksum', 'Compare'],
    input_kind=InputKind.file, supports_single_upload=True, supports_download=False,
    accepted_extensions=['*'], max_upload_mb=50,
    options=[
        _opt("algorithm", "Algorithm", OptionType.select, default="sha256", choices=["md5", "sha1", "sha256", "sha512"]),
        _opt("expected", "Expected checksum", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="HMAC Generator", slug="hmac-generator", category="developer-tools",
    description="Sign a message with a secret key using HMAC.",
    seo_keywords=['HMAC Generator', 'HMAC SHA256', 'Message Authentication Code'],
    how_to_use=['Paste your message', 'Enter the secret key', 'Copy the signature'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("key", "Secret key", OptionType.text, default=""),
        _opt("algorithm", "Algorithm", OptionType.select, default="sha256", choices=["md5", "sha1", "sha256", "sha384", "sha512"]),
    ],
))
define(ToolConfig(
    name="CRC32 Checksum Calculator", slug="crc32-checksum", category="developer-tools",
    description="CRC32 and Adler-32 checksums for text or a file.",
    seo_keywords=['CRC32 Calculator', 'Checksum Calculator', 'Adler32'],
    how_to_use=['Paste your text', 'Copy the checksum'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Base32 and Base58 Converter", slug="base32-base58-converter", category="developer-tools",
    description="Encode and decode Base32 and Base58.",
    seo_keywords=['Base32 Encode', 'Base58 Encode', 'Base58 Decoder'],
    how_to_use=['Paste your text', 'Pick the scheme', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("scheme", "Scheme", OptionType.select, default="base32", choices=["base32", "base58"]),
        _opt("mode", "Mode", OptionType.select, default="encode", choices=["encode", "decode"]),
    ],
))
define(ToolConfig(
    name="JWT Decoder", slug="jwt-decoder", category="developer-tools",
    description="Read a JWT's header, payload and expiry.",
    seo_keywords=['JWT Decoder', 'JWT Debugger', 'Decode JSON Web Token'],
    how_to_use=['Paste your token', 'Read the claims'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="JWT Encoder", slug="jwt-encoder", category="developer-tools",
    description="Sign a JSON payload into a JWT with HMAC.",
    seo_keywords=['JWT Encoder', 'JWT Generator', 'Create JSON Web Token'],
    how_to_use=['Paste the payload as JSON', 'Enter a secret', 'Copy the token'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("secret", "Secret", OptionType.text, default=""),
        _opt("algorithm", "Algorithm", OptionType.select, default="HS256", choices=["HS256", "HS384", "HS512"]),
        _opt("expires_minutes", "Expires in (minutes, 0 = never)", OptionType.number, default=0, min=0, max=525600),
    ],
))
define(ToolConfig(
    name="AES Encrypt and Decrypt", slug="aes-encrypt-decrypt", category="developer-tools",
    description="AES-256-GCM encryption with a passphrase.",
    seo_keywords=['AES Encryption', 'Encrypt Text Online', 'AES Decrypt'],
    how_to_use=['Paste your text', 'Enter a passphrase', 'Encrypt or decrypt'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Mode", OptionType.select, default="encrypt", choices=["encrypt", "decrypt"]),
        _opt("password", "Passphrase", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="GZIP Compressor", slug="gzip-compressor", category="developer-tools",
    description="Compress or expand text with GZIP or Deflate.",
    seo_keywords=['GZIP Compressor', 'Deflate Compress', 'Text Compression Tool'],
    how_to_use=['Paste your text', 'Choose compress or expand', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("mode", "Mode", OptionType.select, default="compress", choices=["compress", "decompress"]),
        _opt("algorithm", "Algorithm", OptionType.select, default="gzip", choices=["gzip", "deflate"]),
        _opt("level", "Compression level", OptionType.number, default=9, min=1, max=9),
    ],
))
define(ToolConfig(
    name="Escape and Unescape String", slug="escape-unescape-string", category="developer-tools",
    description="Escape text for JavaScript, JSON, SQL, HTML, shell and more.",
    seo_keywords=['Escape String', 'Unescape String', 'String Escape Tool'],
    how_to_use=['Paste your text', 'Pick the language', 'Copy the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("language", "Language", OptionType.select, default="javascript", choices=["javascript", "python", "json", "html", "sql", "csv", "regex", "shell"]),
        _opt("mode", "Mode", OptionType.select, default="escape", choices=["escape", "unescape"]),
    ],
))
define(ToolConfig(
    name="htpasswd Generator", slug="htpasswd-generator", category="developer-tools",
    description="Generate an Apache or nginx .htpasswd line.",
    seo_keywords=['htpasswd Generator', 'Apache Password Generator', 'Basic Auth Password'],
    how_to_use=['Enter a username and password', 'Pick a scheme', 'Copy the line'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("username", "Username", OptionType.text, default=""),
        _opt("password", "Password", OptionType.text, default=""),
        _opt("scheme", "Scheme", OptionType.select, default="bcrypt", choices=["bcrypt", "md5", "sha1"]),
        _opt("rounds", "bcrypt cost", OptionType.number, default=12, min=4, max=15),
    ],
))
define(ToolConfig(
    name="Credit Card Validator", slug="credit-card-validator", category="developer-tools",
    description="Check a card number's Luhn checksum and identify the issuer.",
    seo_keywords=['Credit Card Validator', 'Luhn Checker', 'Card Number Validator'],
    how_to_use=['Enter the card number', 'Read the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Regex Tester", slug="regex-tester", category="developer-tools",
    description="Test a regular expression and see every match and group.",
    seo_keywords=['Regex Tester', 'Regular Expression Tester', 'Regex Match Tool'],
    how_to_use=['Paste your text', 'Enter the pattern', 'Read the matches'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("pattern", "Pattern", OptionType.text, default=""),
        _opt("replace_with", "Replace with (optional)", OptionType.text, default=""),
        _opt("ignore_case", "Ignore case", OptionType.boolean, default=False),
        _opt("multiline", "Multiline (^ and $ per line)", OptionType.boolean, default=False),
        _opt("dot_all", "Dot matches newlines", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Regex Cheat Sheet", slug="regex-cheat-sheet", category="developer-tools",
    description="Every regex token explained, with ready-made patterns.",
    seo_keywords=['Regex Cheat Sheet', 'Regex Reference', 'Regular Expression Guide'],
    how_to_use=['Search for a token, or leave it blank', 'Read the reference'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Color Converter", slug="color-converter", category="developer-tools",
    description="Convert a colour between HEX, RGB, HSL, HSV and CMYK.",
    seo_keywords=['Color Converter', 'HEX To RGB', 'RGB To HSL'],
    how_to_use=['Enter a colour', 'Read every format'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("color", "Colour", OptionType.color, default="#4f46e5"),
    ],
))
define(ToolConfig(
    name="Contrast Checker", slug="contrast-checker", category="developer-tools",
    description="Check colour contrast against the WCAG thresholds.",
    seo_keywords=['Contrast Checker', 'WCAG Contrast', 'Color Accessibility Checker'],
    how_to_use=['Enter the text colour', 'Enter the background', 'Read the ratio'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("foreground", "Text colour", OptionType.color, default="#111827"),
        _opt("background", "Background", OptionType.color, default="#ffffff"),
    ],
))
define(ToolConfig(
    name="CSS Gradient Generator", slug="css-gradient-generator", category="developer-tools",
    description="Build linear, radial and conic CSS gradients.",
    seo_keywords=['CSS Gradient Generator', 'Gradient Maker', 'Linear Gradient CSS'],
    how_to_use=['Pick your colours', 'Choose the type', 'Copy the CSS'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("color_1", "First colour", OptionType.color, default="#4f46e5"),
        _opt("color_2", "Second colour", OptionType.color, default="#ec4899"),
        _opt("type", "Type", OptionType.select, default="linear", choices=["linear", "radial", "conic"]),
        _opt("angle", "Angle", OptionType.number, default=90, min=0, max=360),
    ],
))
define(ToolConfig(
    name="Box Shadow Generator", slug="box-shadow-generator", category="developer-tools",
    description="Build a CSS box-shadow with live values.",
    seo_keywords=['Box Shadow Generator', 'CSS Shadow Maker', 'Border Radius Generator'],
    how_to_use=['Set the offsets and blur', 'Pick a colour', 'Copy the CSS'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("x", "Horizontal offset", OptionType.number, default=0, min=-100, max=100),
        _opt("y", "Vertical offset", OptionType.number, default=4, min=-100, max=100),
        _opt("blur", "Blur", OptionType.number, default=12, min=0, max=200),
        _opt("spread", "Spread", OptionType.number, default=0, min=-100, max=100),
        _opt("border_radius", "Border radius", OptionType.number, default=12, min=0, max=200),
        _opt("color", "Shadow colour", OptionType.color, default="#000000"),
        _opt("opacity", "Opacity", OptionType.number, default=0.25, min=0, max=1),
        _opt("inset", "Inset", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Flexbox and Grid Generator", slug="flexbox-grid-generator", category="developer-tools",
    description="Generate CSS Flexbox or Grid layout rules.",
    seo_keywords=['Flexbox Generator', 'CSS Grid Generator', 'Flexbox Playground'],
    how_to_use=['Choose flex or grid', 'Set the options', 'Copy the CSS'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("layout", "Layout", OptionType.select, default="flex", choices=["flex", "grid"]),
        _opt("direction", "Flex direction", OptionType.select, default="row", choices=["row", "row-reverse", "column", "column-reverse"]),
        _opt("justify", "Justify content", OptionType.select, default="flex-start", choices=["flex-start", "center", "flex-end", "space-between", "space-around", "space-evenly"]),
        _opt("align", "Align items", OptionType.select, default="stretch", choices=["stretch", "flex-start", "center", "flex-end", "baseline"]),
        _opt("wrap", "Wrap", OptionType.boolean, default=True),
        _opt("columns", "Grid columns", OptionType.number, default=3, min=1, max=12),
        _opt("column_mode", "Grid sizing", OptionType.select, default="equal", choices=["equal", "responsive"]),
        _opt("gap", "Gap (px)", OptionType.number, default=16, min=0, max=200),
    ],
))
define(ToolConfig(
    name="Cubic Bezier Generator", slug="cubic-bezier-generator", category="developer-tools",
    description="Build CSS easing curves, or start from a preset.",
    seo_keywords=['Cubic Bezier Generator', 'CSS Easing Editor', 'Animation Timing Function'],
    how_to_use=['Pick a preset or set the points', 'Copy the CSS'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("preset", "Preset", OptionType.select, default="ease", choices=["custom", "linear", "ease", "ease-in", "ease-out", "ease-in-out", "ease-in-quad", "ease-out-quad", "ease-in-out-quad", "ease-in-cubic", "ease-out-cubic", "ease-in-out-cubic", "ease-out-back", "ease-in-out-back"]),
        _opt("x1", "x1", OptionType.number, default=0.25, min=0, max=1),
        _opt("y1", "y1", OptionType.number, default=0.1, min=-3, max=3),
        _opt("x2", "x2", OptionType.number, default=0.25, min=0, max=1),
        _opt("y2", "y2", OptionType.number, default=1, min=-3, max=3),
        _opt("duration_ms", "Duration (ms)", OptionType.number, default=300, min=0, max=10000),
    ],
))
define(ToolConfig(
    name="CSS Unit Converter", slug="css-unit-converter", category="developer-tools",
    description="Convert between px, rem, em, %, pt and physical units.",
    seo_keywords=['CSS Unit Converter', 'PX To REM', 'REM Converter'],
    how_to_use=['Enter a value', 'Pick the unit', 'Read every other unit'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=16),
        _opt("from", "Unit", OptionType.select, default="px", choices=["px", "rem", "em", "%", "pt", "pc", "in", "cm", "mm"]),
        _opt("root_font_size", "Root font size (px)", OptionType.number, default=16, min=1, max=100),
        _opt("parent_font_size", "Parent font size (px)", OptionType.number, default=16, min=1, max=100),
    ],
))
define(ToolConfig(
    name="Unix Timestamp Converter", slug="unix-timestamp-converter", category="developer-tools",
    description="Convert Unix timestamps to dates and back.",
    seo_keywords=['Unix Timestamp Converter', 'Epoch Converter', 'Timestamp To Date'],
    how_to_use=['Paste a timestamp or a date', 'Pick a time zone', 'Read the result'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("timezone", "Time zone", OptionType.text, default="UTC"),
    ],
))
define(ToolConfig(
    name="Byte Size Converter", slug="byte-size-converter", category="developer-tools",
    description="Convert between KB, MB, GB, TB and their KiB counterparts.",
    seo_keywords=['Byte Converter', 'MB To GB', 'Data Size Converter'],
    how_to_use=['Enter a size', 'Pick the unit', 'Read every other unit'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("value", "Value", OptionType.number, default=1),
        _opt("from", "Unit", OptionType.select, default="MB", choices=["B", "KB", "MB", "GB", "TB", "KiB", "MiB", "GiB", "TiB"]),
    ],
))
define(ToolConfig(
    name="IEEE 754 Float Converter", slug="ieee754-converter", category="developer-tools",
    description="See the exact bits behind a floating-point number.",
    seo_keywords=['IEEE 754 Converter', 'Float To Binary', 'Floating Point Converter'],
    how_to_use=['Enter a number or a hex pattern', 'Read the bit layout'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("precision", "Precision", OptionType.select, default="64", choices=["32", "64"]),
    ],
))
define(ToolConfig(
    name="Cron Expression Tool", slug="cron-expression-tool", category="developer-tools",
    description="Explain a cron expression and list its next runs.",
    seo_keywords=['Cron Expression Generator', 'Crontab Parser', 'Cron Schedule Explainer'],
    how_to_use=['Enter a cron expression', 'Read the explanation and next runs'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Subnet Calculator", slug="subnet-calculator", category="developer-tools",
    description="CIDR maths for IPv4 and IPv6 networks.",
    seo_keywords=['Subnet Calculator', 'CIDR Calculator', 'IP Range Calculator'],
    how_to_use=['Enter a network like 192.168.1.0/24', 'Read the range'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("cidr", "Network", OptionType.text, default="192.168.1.0/24"),
    ],
))
define(ToolConfig(
    name="User Agent Parser", slug="user-agent-parser", category="developer-tools",
    description="Read the browser, OS and device out of a User-Agent string.",
    seo_keywords=['User Agent Parser', 'UA Parser', 'Browser Detection Tool'],
    how_to_use=['Paste a User-Agent string', 'Read the breakdown'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Markdown Table Generator", slug="markdown-table-generator", category="developer-tools",
    description="Turn CSV or TSV rows into an aligned Markdown table.",
    seo_keywords=['Markdown Table Generator', 'CSV To Markdown Table', 'Markdown Table Maker'],
    how_to_use=['Paste your rows', 'Pick the delimiter', 'Copy the table'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("delimiter", "Delimiter", OptionType.select, default="comma", choices=["comma", "tab", "semicolon", "pipe"]),
        _opt("align", "Alignment", OptionType.select, default="left", choices=["left", "center", "right"]),
        _opt("pad", "Line up the columns", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="README Generator", slug="readme-generator", category="developer-tools",
    description="Generate a project README with the usual sections.",
    seo_keywords=['README Generator', 'Readme Template', 'GitHub Readme Maker'],
    how_to_use=['Enter the project name', 'Pick the language', 'Copy the Markdown'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("project", "Project name", OptionType.text, default=""),
        _opt("description", "Description", OptionType.text, default=""),
        _opt("language", "Language", OptionType.select, default="node", choices=["node", "python", "go", "rust", "php"]),
        _opt("license", "Licence", OptionType.select, default="MIT", choices=["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "none"]),
        _opt("include_features", "Include Features section", OptionType.boolean, default=True),
        _opt("include_contributing", "Include Contributing section", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="gitignore Generator", slug="gitignore-generator", category="developer-tools",
    description="Build a .gitignore for the stacks you actually use.",
    seo_keywords=['gitignore Generator', 'Git Ignore Template', 'Create gitignore'],
    how_to_use=['List your stacks', 'Copy the file'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("stacks", "Stacks (comma separated)", OptionType.text, default="node, macos, editors, secrets"),
    ],
))
define(ToolConfig(
    name="Mock SQL Generator", slug="mock-sql-generator", category="developer-tools",
    description="Generate CREATE TABLE and INSERT statements from a JSON sample.",
    seo_keywords=['Mock SQL Generator', 'JSON To SQL', 'SQL Insert Generator'],
    how_to_use=['Paste a JSON array', 'Name the table', 'Copy the SQL'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("table", "Table name", OptionType.text, default="records"),
    ],
))
define(ToolConfig(
    name="Connection String Builder", slug="connection-string-builder", category="developer-tools",
    description="Build a database URL with the password escaped correctly.",
    seo_keywords=['Connection String Builder', 'Database URL Builder', 'Postgres Connection String'],
    how_to_use=['Pick the engine', 'Fill in the details', 'Copy the URL'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("engine", "Engine", OptionType.select, default="postgresql", choices=["postgresql", "mysql", "mongodb", "redis", "mssql", "sqlite"]),
        _opt("host", "Host", OptionType.text, default="localhost"),
        _opt("port", "Port (0 = default)", OptionType.number, default=0, min=0, max=65535),
        _opt("database", "Database", OptionType.text, default="mydb"),
        _opt("username", "Username", OptionType.text, default=""),
        _opt("password", "Password", OptionType.text, default=""),
        _opt("parameters", "Extra parameters", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Responsive srcset Generator", slug="srcset-generator", category="developer-tools",
    description="Build a responsive img tag with srcset and sizes.",
    seo_keywords=['srcset Generator', 'Responsive Image Generator', 'Picture Tag Generator'],
    how_to_use=['Enter the image path', 'Set the widths', 'Copy the HTML'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("path", "Image path", OptionType.text, default="/images/photo.jpg"),
        _opt("widths", "Widths", OptionType.text, default="480, 768, 1024, 1440, 1920"),
        _opt("pattern", "Filename pattern", OptionType.text, default="{stem}-{w}.{ext}"),
        _opt("sizes", "sizes attribute", OptionType.text, default="(max-width: 768px) 100vw, 50vw"),
        _opt("alt", "Alt text", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="SVG Optimizer", slug="svg-optimizer", category="developer-tools",
    description="Strip the editor metadata that bloats an exported SVG.",
    seo_keywords=['SVG Optimizer', 'SVG Minifier', 'Compress SVG'],
    how_to_use=['Paste your SVG', 'Copy the optimized markup'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("remove_ids", "Remove id attributes", OptionType.boolean, default=True),
        _opt("round_numbers", "Round long decimals", OptionType.boolean, default=True),
        _opt("precision", "Decimal places", OptionType.number, default=2, min=0, max=6),
    ],
))
define(ToolConfig(
    name="HTTP Status Code Reference", slug="http-status-reference", category="developer-tools",
    description="Every HTTP status code, with notes on when to use it.",
    seo_keywords=['HTTP Status Codes', 'HTTP Response Codes', 'Status Code Reference'],
    how_to_use=['Search for a code or name', 'Read the reference'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="MIME Type Lookup", slug="mime-type-lookup", category="developer-tools",
    description="Find the MIME type for any file extension.",
    seo_keywords=['MIME Type Lookup', 'Content Type Finder', 'File Extension MIME'],
    how_to_use=['Enter an extension', 'Read the MIME type'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="ASCII and Unicode Table", slug="ascii-unicode-table", category="developer-tools",
    description="The ASCII table, plus details for any character you paste.",
    seo_keywords=['ASCII Table', 'Unicode Table', 'Character Code Lookup'],
    how_to_use=['Paste characters, or leave it blank', 'Read the table'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("start", "From (decimal)", OptionType.number, default=32, min=0, max=127),
        _opt("end", "To (decimal)", OptionType.number, default=126, min=0, max=127),
    ],
))
define(ToolConfig(
    name="HTML Entity Reference", slug="html-entity-reference", category="developer-tools",
    description="Every common HTML entity with its character and code.",
    seo_keywords=['HTML Entity Reference', 'HTML Symbols', 'HTML Character Codes'],
    how_to_use=['Search for a symbol', 'Copy the entity'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Meta Tag Generator", slug="meta-tag-generator", category="seo-tools",
    description="Generate title, description, robots and canonical tags.",
    seo_keywords=['Meta Tag Generator', 'SEO Meta Tags', 'Meta Description Generator'],
    how_to_use=['Enter your title and description', 'Copy the tags into your head'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("title", "Page title", OptionType.text, default=""),
        _opt("description", "Meta description", OptionType.text, default=""),
        _opt("keywords", "Keywords", OptionType.text, default=""),
        _opt("author", "Author", OptionType.text, default=""),
        _opt("canonical", "Canonical URL", OptionType.text, default=""),
        _opt("robots", "Robots", OptionType.select, default="index, follow", choices=["index, follow", "noindex, follow", "index, nofollow", "noindex, nofollow"]),
        _opt("include_viewport", "Include charset and viewport", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Open Graph Generator", slug="open-graph-generator", category="seo-tools",
    description="Generate Open Graph and Twitter tags for link previews.",
    seo_keywords=['Open Graph Generator', 'OG Tags Generator', 'Facebook Meta Tags'],
    how_to_use=['Enter your title, URL and image', 'Copy the tags'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("title", "Title", OptionType.text, default=""),
        _opt("description", "Description", OptionType.text, default=""),
        _opt("url", "Page URL", OptionType.text, default=""),
        _opt("image", "Image URL", OptionType.text, default=""),
        _opt("site_name", "Site name", OptionType.text, default=""),
        _opt("type", "Type", OptionType.select, default="website", choices=["website", "article", "product", "profile", "video.other"]),
        _opt("twitter_handle", "Twitter handle", OptionType.text, default=""),
        _opt("include_twitter", "Include Twitter tags", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Twitter Card Generator", slug="twitter-card-generator", category="seo-tools",
    description="Generate Twitter Card tags for rich link previews.",
    seo_keywords=['Twitter Card Generator', 'X Card Tags', 'Twitter Meta Tags'],
    how_to_use=['Enter your title and image', 'Pick the card type', 'Copy the tags'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("title", "Title", OptionType.text, default=""),
        _opt("description", "Description", OptionType.text, default=""),
        _opt("image", "Image URL", OptionType.text, default=""),
        _opt("image_alt", "Image alt text", OptionType.text, default=""),
        _opt("card", "Card type", OptionType.select, default="summary_large_image", choices=["summary", "summary_large_image", "app", "player"]),
        _opt("site", "Site handle", OptionType.text, default=""),
        _opt("creator", "Creator handle", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Canonical Tag Generator", slug="canonical-tag-generator", category="seo-tools",
    description="Build a clean canonical link and catch the URL mistakes.",
    seo_keywords=['Canonical Tag Generator', 'Canonical URL', 'rel canonical'],
    how_to_use=['Paste the page URL', 'Copy the tag'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("url", "Page URL", OptionType.text, default=""),
        _opt("strip_parameters", "Remove tracking parameters", OptionType.boolean, default=True),
        _opt("lowercase", "Lowercase the host", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Hreflang Generator", slug="hreflang-generator", category="seo-tools",
    description="Generate hreflang tags for a multi-language site.",
    seo_keywords=['Hreflang Generator', 'Hreflang Tags', 'Multilingual SEO Tags'],
    how_to_use=['List each language and URL', 'Copy the tags onto every listed page'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Robots Meta Tag Generator", slug="robots-meta-generator", category="seo-tools",
    description="Control indexing and snippets with a robots meta tag.",
    seo_keywords=['Robots Meta Tag', 'Noindex Tag Generator', 'Meta Robots'],
    how_to_use=['Choose the directives', 'Copy the tag'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("noindex", "noindex", OptionType.boolean, default=False),
        _opt("nofollow", "nofollow", OptionType.boolean, default=False),
        _opt("noarchive", "noarchive", OptionType.boolean, default=False),
        _opt("nosnippet", "nosnippet", OptionType.boolean, default=False),
        _opt("noimageindex", "noimageindex", OptionType.boolean, default=False),
        _opt("notranslate", "notranslate", OptionType.boolean, default=False),
        _opt("max_snippet", "max-snippet (-1 = no limit)", OptionType.number, default=-1, min=-1, max=1000),
        _opt("max_image_preview", "max-image-preview", OptionType.select, default="large", choices=["large", "standard", "none"]),
        _opt("google_only", "Add a googlebot tag too", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="SERP Snippet Preview", slug="serp-preview", category="seo-tools",
    description="See how your title and description will read in Google.",
    seo_keywords=['SERP Preview', 'Google Snippet Preview', 'SERP Simulator'],
    how_to_use=['Enter your title, description and URL', 'Check where it cuts off'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("title", "Title", OptionType.text, default=""),
        _opt("description", "Meta description", OptionType.text, default=""),
        _opt("url", "URL", OptionType.text, default="https://example.com/page"),
        _opt("device", "Device", OptionType.select, default="desktop", choices=["desktop", "mobile"]),
    ],
))
define(ToolConfig(
    name="Schema Markup Generator", slug="schema-generator", category="seo-tools",
    description="Generate JSON-LD for articles, products, events and more.",
    seo_keywords=['Schema Markup Generator', 'JSON-LD Generator', 'Structured Data Generator'],
    how_to_use=['Pick the type', 'Fill in the fields', 'Copy the JSON-LD'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("type", "Schema type", OptionType.select, default="Article", choices=["Article", "BlogPosting", "NewsArticle", "Product", "Organization", "Person", "Event", "Recipe", "VideoObject", "WebSite"]),
        _opt("name", "Name or headline", OptionType.text, default=""),
        _opt("url", "URL", OptionType.text, default=""),
        _opt("description", "Description", OptionType.text, default=""),
        _opt("image", "Image URL", OptionType.text, default=""),
        _opt("author", "Author or job title", OptionType.text, default=""),
        _opt("publisher", "Publisher or venue", OptionType.text, default=""),
        _opt("date", "Date", OptionType.text, default=""),
        _opt("price", "Price", OptionType.text, default=""),
        _opt("currency", "Currency", OptionType.text, default="USD"),
        _opt("rating", "Rating", OptionType.text, default=""),
        _opt("review_count", "Review count", OptionType.text, default=""),
        _opt("same_as", "Social profiles (comma separated)", OptionType.text, default=""),
        _opt("search_box", "Include site search action", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="FAQ Schema Generator", slug="faq-schema-generator", category="seo-tools",
    description="Turn questions and answers into FAQPage JSON-LD.",
    seo_keywords=['FAQ Schema Generator', 'FAQPage JSON-LD', 'FAQ Rich Results'],
    how_to_use=['Enter each question and answer', 'Copy the JSON-LD'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Breadcrumb Schema Generator", slug="breadcrumb-schema-generator", category="seo-tools",
    description="Generate BreadcrumbList JSON-LD for your navigation path.",
    seo_keywords=['Breadcrumb Schema', 'BreadcrumbList JSON-LD', 'Breadcrumb Markup'],
    how_to_use=['List each crumb and URL', 'Copy the JSON-LD'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Local Business Schema Generator", slug="local-business-schema", category="seo-tools",
    description="Generate LocalBusiness JSON-LD with address, hours and location.",
    seo_keywords=['Local Business Schema', 'LocalBusiness JSON-LD', 'Local SEO Schema'],
    how_to_use=['Fill in your business details', 'Copy the JSON-LD'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("name", "Business name", OptionType.text, default=""),
        _opt("business_type", "Type", OptionType.select, default="LocalBusiness", choices=["LocalBusiness", "Restaurant", "Store", "ProfessionalService", "MedicalBusiness", "AutoRepair", "Dentist", "LegalService", "RealEstateAgent", "HealthAndBeautyBusiness"]),
        _opt("street", "Street address", OptionType.text, default=""),
        _opt("city", "City", OptionType.text, default=""),
        _opt("region", "Region or state", OptionType.text, default=""),
        _opt("postal_code", "Postal code", OptionType.text, default=""),
        _opt("country", "Country code", OptionType.text, default="US"),
        _opt("phone", "Phone", OptionType.text, default=""),
        _opt("url", "Website", OptionType.text, default=""),
        _opt("image", "Image URL", OptionType.text, default=""),
        _opt("price_range", "Price range", OptionType.text, default=""),
        _opt("hours", "Opening hours", OptionType.text, default="Mo-Fr 09:00-17:00"),
        _opt("latitude", "Latitude", OptionType.text, default=""),
        _opt("longitude", "Longitude", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Review Schema Generator", slug="review-schema-generator", category="seo-tools",
    description="Generate Review or AggregateRating JSON-LD.",
    seo_keywords=['Review Schema Generator', 'AggregateRating Markup', 'Star Rating Schema'],
    how_to_use=['Enter what is reviewed', 'Set the rating', 'Copy the JSON-LD'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("item_name", "Item reviewed", OptionType.text, default=""),
        _opt("item_type", "Item type", OptionType.select, default="Product", choices=["Product", "Service", "Book", "Movie", "Course", "SoftwareApplication", "LocalBusiness"]),
        _opt("mode", "Markup", OptionType.select, default="aggregate", choices=["aggregate", "single"]),
        _opt("rating", "Rating", OptionType.text, default="4.5"),
        _opt("best_rating", "Best possible", OptionType.text, default="5"),
        _opt("review_count", "Review count", OptionType.text, default="10"),
        _opt("author", "Reviewer name", OptionType.text, default=""),
        _opt("review_body", "Review text", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Structured Data Validator", slug="structured-data-validator", category="seo-tools",
    description="Check JSON-LD for the fields Google actually requires.",
    seo_keywords=['Structured Data Validator', 'JSON-LD Validator', 'Rich Results Checker'],
    how_to_use=['Paste your JSON-LD or page HTML', 'Review what is missing'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Google Review Link Generator", slug="google-review-link", category="seo-tools",
    description="Build a direct link that opens the Google review box.",
    seo_keywords=['Google Review Link', 'Review Link Generator', 'Place ID Review URL'],
    how_to_use=['Paste your Google Place ID', 'Copy and share the link'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("place_id", "Place ID", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Heading Structure Analyzer", slug="heading-analyzer", category="seo-tools",
    description="Check your H1-H6 order and catch skipped levels.",
    seo_keywords=['Heading Analyzer', 'H1 Checker', 'Heading Structure SEO'],
    how_to_use=['Paste your page HTML', 'Review the outline'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Image Alt Text Checker", slug="alt-text-checker", category="seo-tools",
    description="Find images with missing or unhelpful alt text.",
    seo_keywords=['Alt Text Checker', 'Image Alt Checker', 'Missing Alt Text'],
    how_to_use=['Paste your page HTML', 'Review the coverage'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Internal Link Analyzer", slug="internal-link-analyzer", category="seo-tools",
    description="Break down internal, external and broken-anchor links.",
    seo_keywords=['Internal Link Analyzer', 'Link Checker', 'Internal Linking SEO'],
    how_to_use=['Paste your page HTML', 'Set your domain', 'Review the links'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("domain", "Your domain", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Nofollow Link Checker", slug="nofollow-link-checker", category="seo-tools",
    description="See which outbound links pass ranking signal.",
    seo_keywords=['Nofollow Checker', 'Outbound Link Checker', 'rel nofollow Checker'],
    how_to_use=['Paste your page HTML', 'Set your domain', 'Review the links'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("domain", "Your domain", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Anchor Text Analyzer", slug="anchor-text-analyzer", category="seo-tools",
    description="Check your anchor text spread for over-optimisation.",
    seo_keywords=['Anchor Text Analyzer', 'Anchor Text Distribution', 'Anchor Text SEO'],
    how_to_use=['Paste your page HTML', 'Set your brand name', 'Review the spread'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("brand", "Brand name", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Meta Tags Analyzer", slug="meta-tags-analyzer", category="seo-tools",
    description="Pull every SEO tag out of a page and grade it.",
    seo_keywords=['Meta Tags Analyzer', 'Meta Tag Extractor', 'SEO Tag Checker'],
    how_to_use=['Paste your page HTML', 'Review the tags and issues'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Canonical Checker", slug="canonical-checker", category="seo-tools",
    description="Check a page's canonical link for the usual mistakes.",
    seo_keywords=['Canonical Checker', 'Canonical Tag Checker', 'rel canonical Validator'],
    how_to_use=['Paste your page HTML', 'Enter the page URL', 'Review the findings'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("page_url", "Page URL", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Hreflang Checker", slug="hreflang-checker", category="seo-tools",
    description="Validate the hreflang tags on a page.",
    seo_keywords=['Hreflang Checker', 'Hreflang Validator', 'Hreflang Tester'],
    how_to_use=['Paste your page HTML', 'Review the issues'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="AMP Validator", slug="amp-validator", category="seo-tools",
    description="Check the AMP rules that break a page outright.",
    seo_keywords=['AMP Validator', 'AMP Checker', 'Validate AMP HTML'],
    how_to_use=['Paste your AMP HTML', 'Review the issues'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Code to Text Ratio Checker", slug="code-to-text-ratio", category="seo-tools",
    description="Measure how much of a page is content versus markup.",
    seo_keywords=['Code To Text Ratio', 'Text To HTML Ratio', 'Content Ratio Checker'],
    how_to_use=['Paste your page HTML', 'Read the ratio'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="SEO Report Generator", slug="seo-report-generator", category="seo-tools",
    description="Run every on-page check at once and get a score.",
    seo_keywords=['SEO Report Generator', 'On Page SEO Checker', 'SEO Audit Tool'],
    how_to_use=['Paste your page HTML', 'Read the report'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[],
))
define(ToolConfig(
    name="Keyword Combiner", slug="keyword-combiner", category="seo-tools",
    description="Mix keyword lists into every combination.",
    seo_keywords=['Keyword Combiner', 'Keyword Mixer', 'Keyword Permutation Tool'],
    how_to_use=['Paste each list, separated by a blank line', 'Copy the combinations'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("second_list", "Second list", OptionType.text, default=""),
        _opt("joiner", "Join with", OptionType.select, default="space", choices=["space", "hyphen", "plus", "none"]),
        _opt("match_type", "Match type", OptionType.select, default="broad", choices=["broad", "phrase", "exact"]),
        _opt("include_reversed", "Include reversed order", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Keyword Prominence Checker", slug="keyword-prominence", category="seo-tools",
    description="See where your keyword sits, not just how often it appears.",
    seo_keywords=['Keyword Prominence', 'Keyword Placement Checker', 'Keyword Position SEO'],
    how_to_use=['Paste your content or HTML', 'Enter the keyword', 'Read the placement'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("keyword", "Keyword", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="URL Slug Generator", slug="seo-slug-generator", category="seo-tools",
    description="Turn any title into a clean, SEO-friendly slug.",
    seo_keywords=['URL Slug Generator', 'SEO Slug Generator', 'Permalink Generator'],
    how_to_use=['Paste one title per line', 'Copy the slugs'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("remove_stop_words", "Remove stop words", OptionType.boolean, default=False),
        _opt("separator", "Separator", OptionType.text, default="-"),
        _opt("max_length", "Max length (0 = no limit)", OptionType.number, default=60, min=0, max=200),
    ],
))
define(ToolConfig(
    name="Near Me Keyword Tool", slug="near-me-keyword-tool", category="seo-tools",
    description="Build local keyword variations for every location you serve.",
    seo_keywords=['Near Me Keywords', 'Local Keyword Generator', 'Local SEO Keywords'],
    how_to_use=['List your services', 'List your locations', 'Copy the keywords'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("locations", "Locations (comma separated)", OptionType.text, default=""),
        _opt("variations", "Patterns per location", OptionType.number, default=6, min=1, max=10),
        _opt("include_near_me", "Add plain near me terms", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Keyword Value Calculator", slug="keyword-value-calculator", category="seo-tools",
    description="Work out what ranking for a keyword is worth per month.",
    seo_keywords=['Keyword Value Calculator', 'Keyword CPC Calculator', 'Traffic Value Estimator'],
    how_to_use=['Enter the search volume and CPC', 'Set your conversion rate', 'Read the value'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("monthly_searches", "Monthly searches", OptionType.number, default=1000, min=0),
        _opt("cpc", "Cost per click", OptionType.number, default=2, min=0),
        _opt("position", "Target position", OptionType.number, default=1, min=1, max=10),
        _opt("conversion_rate", "Conversion rate (%)", OptionType.number, default=2, min=0, max=100),
        _opt("order_value", "Average order value", OptionType.number, default=100, min=0),
    ],
))
define(ToolConfig(
    name="Content Brief Generator", slug="content-brief-generator", category="seo-tools",
    description="Generate a structured brief and outline for a writer.",
    seo_keywords=['Content Brief Generator', 'SEO Content Outline', 'Article Brief Template'],
    how_to_use=['Enter the target keyword', 'Pick the intent', 'Copy the brief'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("keyword", "Target keyword", OptionType.text, default=""),
        _opt("intent", "Search intent", OptionType.select, default="informational", choices=["informational", "commercial", "transactional", "navigational"]),
        _opt("word_count", "Target word count", OptionType.number, default=1500, min=200, max=10000),
        _opt("audience", "Audience", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Featured Snippet Optimizer", slug="featured-snippet-optimizer", category="seo-tools",
    description="Check whether your content is shaped to win a snippet.",
    seo_keywords=['Featured Snippet Optimizer', 'Position Zero Checker', 'Snippet Optimization'],
    how_to_use=['Paste your content', 'Enter the keyword', 'Read the checks'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("keyword", "Target keyword", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="NAP Consistency Checker", slug="nap-consistency-checker", category="seo-tools",
    description="Compare your name, address and phone across listings.",
    seo_keywords=['NAP Consistency Checker', 'Citation Checker', 'Local Listing Checker'],
    how_to_use=['Paste each listing, separated by a blank line', 'Review the differences'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Disavow File Generator", slug="disavow-file-generator", category="seo-tools",
    description="Format a Google disavow file from a list of bad links.",
    seo_keywords=['Disavow File Generator', 'Google Disavow Tool', 'Backlink Disavow'],
    how_to_use=['Paste the domains or URLs', 'Copy the file'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("domain_level", "Disavow whole domains", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Domain Name Generator", slug="domain-name-generator", category="seo-tools",
    description="Generate domain ideas from your keywords.",
    seo_keywords=['Domain Name Generator', 'Domain Ideas', 'Business Name Generator'],
    how_to_use=['Enter your keywords', 'Copy the shortlist'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("prefixes", "Prefixes", OptionType.text, default="get,try,my,the,go"),
        _opt("suffixes", "Suffixes", OptionType.text, default="hub,ly,app,hq,lab,ify,zone"),
        _opt("tlds", "Extensions", OptionType.text, default="com,io,co,net,app"),
        _opt("limit", "How many names", OptionType.number, default=60, min=1, max=500),
    ],
))
define(ToolConfig(
    name="UTM Campaign URL Builder", slug="utm-builder", category="seo-tools",
    description="Build tagged campaign URLs that track correctly.",
    seo_keywords=['UTM Builder', 'Campaign URL Builder', 'UTM Parameter Generator'],
    how_to_use=['Enter the destination URL', 'Fill in source, medium and campaign', 'Copy the URL'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("url", "Destination URL", OptionType.text, default=""),
        _opt("source", "Campaign source", OptionType.text, default=""),
        _opt("medium", "Campaign medium", OptionType.text, default=""),
        _opt("campaign", "Campaign name", OptionType.text, default=""),
        _opt("term", "Campaign term", OptionType.text, default=""),
        _opt("content", "Campaign content", OptionType.text, default=""),
        _opt("id", "Campaign ID", OptionType.text, default=""),
        _opt("lowercase", "Lowercase the values", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Robots.txt Generator", slug="robots-txt-generator", category="seo-tools",
    description="Build a robots.txt with the right rules and a sitemap line.",
    seo_keywords=['Robots.txt Generator', 'Create Robots File', 'Robots txt Maker'],
    how_to_use=['List the paths to block', 'Add your sitemap', 'Copy the file'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("allow", "Paths to allow", OptionType.text, default=""),
        _opt("sitemap", "Sitemap URL", OptionType.text, default=""),
        _opt("block_ai_crawlers", "Block AI crawlers", OptionType.boolean, default=False),
        _opt("block_everything", "Block the whole site", OptionType.boolean, default=False),
        _opt("crawl_delay", "Crawl delay (0 = none)", OptionType.number, default=0, min=0, max=120),
    ],
))
define(ToolConfig(
    name="Robots.txt Tester", slug="robots-txt-tester", category="seo-tools",
    description="Test whether a URL is blocked before you deploy.",
    seo_keywords=['Robots.txt Tester', 'Robots txt Validator', 'Crawl Rule Tester'],
    how_to_use=['Paste your robots.txt', 'Enter the path to test', 'Read the verdict'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[
        _opt("path", "Path to test", OptionType.text, default="/"),
        _opt("user_agent", "User agent", OptionType.text, default="*"),
    ],
))
define(ToolConfig(
    name="XML Sitemap Generator", slug="xml-sitemap-generator", category="seo-tools",
    description="Turn a list of URLs into a valid XML sitemap.",
    seo_keywords=['XML Sitemap Generator', 'Sitemap Maker', 'Create Sitemap XML'],
    how_to_use=['Paste one URL per line', 'Set the options', 'Copy the sitemap'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("changefreq", "Change frequency", OptionType.select, default="weekly", choices=["always", "hourly", "daily", "weekly", "monthly", "yearly", "never", "none"]),
        _opt("priority", "Priority", OptionType.select, default="0.8", choices=["1.0", "0.9", "0.8", "0.7", "0.6", "0.5", "none"]),
        _opt("lastmod", "Last modified (YYYY-MM-DD)", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Sitemap Validator", slug="sitemap-validator", category="seo-tools",
    description="Check a sitemap for duplicates, bad URLs and size limits.",
    seo_keywords=['Sitemap Validator', 'XML Sitemap Checker', 'Validate Sitemap'],
    how_to_use=['Paste your sitemap XML', 'Review the issues'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=False,
    options=[],
))
define(ToolConfig(
    name="Redirect Generator", slug="htaccess-redirect-generator", category="seo-tools",
    description="Generate .htaccess or nginx redirect rules from a list.",
    seo_keywords=['htaccess Redirect Generator', '301 Redirect Generator', 'Nginx Redirect Rules'],
    how_to_use=['List old and new paths', 'Pick the server', 'Copy the rules'],
    input_kind=InputKind.text, supports_single_upload=False, supports_download=True,
    options=[
        _opt("server", "Server", OptionType.select, default="apache", choices=["apache", "nginx"]),
        _opt("status", "Status code", OptionType.select, default="301", choices=["301", "302", "307", "308"]),
    ],
))
define(ToolConfig(
    name="Circle Crop", slug="circle-crop", category="image-tools",
    description="Crop any photo into a circle with a transparent background.",
    seo_keywords=['Circle Crop', 'Round Image Cropper', 'Crop Photo To Circle'],
    how_to_use=['Upload your image', 'Set the size', 'Download the PNG'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("size", "Output size (0 = keep)", OptionType.number, default=0, min=0, max=4000),
    ],
))
define(ToolConfig(
    name="Round Corners", slug="round-corners", category="image-tools",
    description="Round the corners of an image, with a transparent outside.",
    seo_keywords=['Round Corners Image', 'Rounded Corner Maker', 'Round Image Corners'],
    how_to_use=['Upload your image', 'Set the radius', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("radius_percent", "Corner radius (%)", OptionType.number, default=15, min=0, max=50),
    ],
))
define(ToolConfig(
    name="Shape Crop", slug="shape-crop", category="image-tools",
    description="Crop to a fixed ratio, or to a circle, hexagon, triangle or star.",
    seo_keywords=['Shape Crop', 'Aspect Ratio Cropper', 'Crop Image To Shape'],
    how_to_use=['Upload your image', 'Pick a ratio or shape', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("shape", "Shape", OptionType.select, default="square", choices=["square", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "circle", "hexagon", "triangle", "star"]),
    ],
))
define(ToolConfig(
    name="Bulk Image Resizer", slug="bulk-image-resizer", category="image-tools",
    description="Resize many images at once, by size or percentage.",
    seo_keywords=['Bulk Image Resizer', 'Batch Resize Images', 'Resize Multiple Photos'],
    how_to_use=['Upload your images', 'Choose a size or percentage', 'Download them all'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("mode", "Resize by", OptionType.select, default="fit", choices=["fit", "exact", "percent"]),
        _opt("width", "Width (px)", OptionType.number, default=1200, min=0, max=8000),
        _opt("height", "Height (px, 0 = auto)", OptionType.number, default=0, min=0, max=8000),
        _opt("percent", "Percentage", OptionType.number, default=50, min=1, max=400),
        _opt("format", "Output format", OptionType.select, default="keep", choices=["keep", "jpg", "png", "webp", "avif"]),
        _opt("quality", "Quality", OptionType.number, default=88, min=1, max=100),
    ],
))
define(ToolConfig(
    name="Universal Image Converter", slug="universal-image-converter", category="image-tools",
    description="Convert between PNG, JPG, WebP, AVIF, BMP, TIFF, GIF and ICO.",
    seo_keywords=['Image Converter', 'Convert Image Format', 'PNG To WebP'],
    how_to_use=['Upload your images', 'Pick the output format', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("format", "Convert to", OptionType.select, default="png", choices=["png", "jpg", "webp", "avif", "bmp", "tiff", "gif", "ico"]),
        _opt("quality", "Quality", OptionType.number, default=90, min=1, max=100),
    ],
))
define(ToolConfig(
    name="PNG Compressor", slug="png-compressor", category="image-tools",
    description="Shrink PNG files by reducing the palette, losslessly encoded.",
    seo_keywords=['PNG Compressor', 'Compress PNG', 'Reduce PNG Size'],
    how_to_use=['Upload your PNGs', 'Set the colour count', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['png'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("reduce_colors", "Reduce the palette", OptionType.boolean, default=True),
        _opt("colors", "Maximum colours", OptionType.number, default=256, min=2, max=256),
    ],
))
define(ToolConfig(
    name="WebP and AVIF Compressor", slug="webp-avif-compressor", category="image-tools",
    description="Re-encode images to WebP or AVIF for much smaller files.",
    seo_keywords=['WebP Compressor', 'AVIF Converter', 'Compress Image WebP'],
    how_to_use=['Upload your images', 'Pick WebP or AVIF', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("format", "Format", OptionType.select, default="webp", choices=["webp", "avif"]),
        _opt("quality", "Quality", OptionType.number, default=80, min=1, max=100),
        _opt("lossless", "Lossless (WebP only)", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="SVG to PNG Converter", slug="svg-to-png", category="image-tools",
    description="Rasterise SVG at any scale, or wrap an image as SVG.",
    seo_keywords=['SVG To PNG', 'Convert SVG', 'SVG Rasterizer'],
    how_to_use=['Upload an SVG or paste the markup', 'Set the scale', 'Download the PNG'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['svg', 'png', 'jpg', 'jpeg'], max_upload_mb=25,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("direction", "Convert", OptionType.select, default="svg_to_png", choices=["svg_to_png", "png_to_svg"]),
        _opt("scale", "Scale", OptionType.number, default=2, min=0.1, max=10),
    ],
))
define(ToolConfig(
    name="Image Adjuster", slug="image-adjuster", category="image-tools",
    description="Brightness, contrast, saturation, sharpness and gamma.",
    seo_keywords=['Image Adjuster', 'Brightness Contrast Tool', 'Adjust Photo Online'],
    how_to_use=['Upload your image', 'Move the sliders', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("brightness", "Brightness", OptionType.number, default=100, min=0, max=300),
        _opt("contrast", "Contrast", OptionType.number, default=100, min=0, max=300),
        _opt("saturation", "Saturation", OptionType.number, default=100, min=0, max=300),
        _opt("sharpness", "Sharpness", OptionType.number, default=100, min=0, max=300),
        _opt("gamma", "Gamma", OptionType.number, default=1, min=0.1, max=3),
    ],
))
define(ToolConfig(
    name="Image Filters", slug="image-filters", category="image-tools",
    description="Sepia, vintage, duotone, posterize and more.",
    seo_keywords=['Image Filters', 'Photo Effects Online', 'Sepia Filter'],
    how_to_use=['Upload your image', 'Choose an effect', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("effect", "Effect", OptionType.select, default="grayscale", choices=["grayscale", "sepia", "invert", "posterize", "solarize", "vintage", "cool", "warm", "high contrast", "duotone"]),
        _opt("levels", "Posterize levels", OptionType.number, default=4, min=1, max=8),
        _opt("threshold", "Solarize threshold", OptionType.number, default=128, min=0, max=255),
        _opt("dark", "Duotone dark", OptionType.color, default="#1e1b4b"),
        _opt("light", "Duotone light", OptionType.color, default="#a5b4fc"),
    ],
))
define(ToolConfig(
    name="Black and White Converter", slug="black-and-white-converter", category="image-tools",
    description="Greyscale, dithered, or a hard two-tone threshold.",
    seo_keywords=['Black And White Converter', 'Grayscale Image', 'Convert Photo To BW'],
    how_to_use=['Upload your image', 'Pick a mode', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("mode", "Mode", OptionType.select, default="grayscale", choices=["grayscale", "threshold", "dithered"]),
        _opt("threshold", "Threshold", OptionType.number, default=128, min=1, max=254),
        _opt("auto_contrast", "Auto contrast", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Sharpen Image", slug="sharpen-image", category="image-tools",
    description="Bring back detail with unsharp masking.",
    seo_keywords=['Sharpen Image', 'Unsharp Mask', 'Make Photo Sharper'],
    how_to_use=['Upload your image', 'Set the amount', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("amount", "Amount (%)", OptionType.number, default=150, min=1, max=500),
        _opt("radius", "Radius", OptionType.number, default=2, min=0.1, max=20),
        _opt("threshold", "Threshold", OptionType.number, default=3, min=0, max=100),
    ],
))
define(ToolConfig(
    name="Blur and Pixelate", slug="blur-pixelate", category="image-tools",
    description="Blur or pixelate a whole image, or just one area.",
    seo_keywords=['Blur Image', 'Pixelate Image', 'Blur Face In Photo'],
    how_to_use=['Upload your image', 'Set the area to hide', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("style", "Style", OptionType.select, default="blur", choices=["blur", "pixelate"]),
        _opt("radius", "Blur radius", OptionType.number, default=8, min=0.5, max=60),
        _opt("block_size", "Pixel size", OptionType.number, default=16, min=2, max=100),
        _opt("x", "Area x", OptionType.number, default=0, min=0, max=10000),
        _opt("y", "Area y", OptionType.number, default=0, min=0, max=10000),
        _opt("width", "Area width (0 = all)", OptionType.number, default=0, min=0, max=10000),
        _opt("height", "Area height (0 = all)", OptionType.number, default=0, min=0, max=10000),
    ],
))
define(ToolConfig(
    name="Motion Blur", slug="motion-blur", category="image-tools",
    description="Add a directional streak, like a panning camera.",
    seo_keywords=['Motion Blur', 'Directional Blur', 'Speed Effect Photo'],
    how_to_use=['Upload your image', 'Pick the direction', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("direction", "Direction", OptionType.select, default="horizontal", choices=["horizontal", "vertical", "diagonal", "anti-diagonal"]),
        _opt("length", "Streak length", OptionType.number, default=15, min=3, max=60),
    ],
))
define(ToolConfig(
    name="Pixel Art Converter", slug="pixel-art-converter", category="image-tools",
    description="Turn a photo into blocky, limited-palette pixel art.",
    seo_keywords=['Pixel Art Converter', 'Photo To Pixel Art', '8 Bit Image Maker'],
    how_to_use=['Upload your image', 'Set the pixel width', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("pixel_width", "Pixels across", OptionType.number, default=64, min=8, max=512),
        _opt("colors", "Palette size", OptionType.number, default=16, min=2, max=256),
        _opt("scale_back", "Scale back up", OptionType.boolean, default=True),
        _opt("scale", "Scale factor", OptionType.number, default=8, min=1, max=32),
    ],
))
define(ToolConfig(
    name="Glitch Effect", slug="glitch-effect", category="image-tools",
    description="RGB split and scanline glitch, with an optional deep fry.",
    seo_keywords=['Glitch Effect', 'Deep Fry Image', 'RGB Split Effect'],
    how_to_use=['Upload your image', 'Set the strength', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("strength", "Strength", OptionType.number, default=10, min=1, max=100),
        _opt("rgb_split", "RGB split", OptionType.boolean, default=True),
        _opt("deep_fry", "Deep fry", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Cartoon Effect", slug="cartoon-effect", category="image-tools",
    description="Flat colour plus ink outlines, for a drawn look.",
    seo_keywords=['Cartoon Effect', 'Photo To Cartoon', 'Comic Filter'],
    how_to_use=['Upload your image', 'Tune the outline', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("levels", "Colour levels", OptionType.number, default=4, min=2, max=8),
        _opt("smoothing", "Smoothing", OptionType.number, default=5, min=3, max=9),
        _opt("edge_strength", "Edge sensitivity", OptionType.number, default=40, min=1, max=200),
        _opt("outline", "Draw outlines", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Scan Cleanup", slug="scan-cleanup", category="image-tools",
    description="Straighten and whiten a photographed document.",
    seo_keywords=['Scan Cleanup', 'Deskew Document', 'Whiten Scanned Page'],
    how_to_use=['Upload the photo', 'Leave the defaults on', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("deskew", "Straighten", OptionType.boolean, default=True),
        _opt("whiten", "Whiten the paper", OptionType.boolean, default=True),
        _opt("sharpen", "Sharpen the text", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Image Color Picker", slug="image-color-picker", category="image-tools",
    description="Read the exact colour at any pixel.",
    seo_keywords=['Image Color Picker', 'Eyedropper Tool', 'Get Color From Image'],
    how_to_use=['Upload your image', 'Enter the coordinates', 'Read the colour'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=False, supports_zip_download=False,
    options=[
        _opt("x", "X", OptionType.number, default=0, min=0, max=20000),
        _opt("y", "Y", OptionType.number, default=0, min=0, max=20000),
        _opt("sample_radius", "Average over", OptionType.number, default=2, min=0, max=50),
    ],
))
define(ToolConfig(
    name="Color Palette Extractor", slug="color-palette-extractor", category="image-tools",
    description="Pull a colour palette out of any image, with CSS.",
    seo_keywords=['Color Palette Extractor', 'Image Color Palette', 'Extract Colors From Image'],
    how_to_use=['Upload your image', 'Choose how many colours', 'Copy the palette'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("colors", "How many colours", OptionType.number, default=8, min=2, max=24),
    ],
))
define(ToolConfig(
    name="Dominant Color Finder", slug="dominant-color-finder", category="image-tools",
    description="Find the one colour an image reads as.",
    seo_keywords=['Dominant Color Finder', 'Main Color Of Image', 'Average Image Color'],
    how_to_use=['Upload your image', 'Read the dominant colour'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("ignore_neutrals", "Skip greys and white", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Color Histogram Viewer", slug="color-histogram", category="image-tools",
    description="See the tonal spread and check the exposure.",
    seo_keywords=['Color Histogram', 'Image Histogram Viewer', 'Photo Exposure Check'],
    how_to_use=['Upload your image', 'Read the histogram'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=False,
    options=[],
))
define(ToolConfig(
    name="EXIF Remover", slug="exif-remover", category="image-tools",
    description="Strip metadata, including the GPS location in phone photos.",
    seo_keywords=['EXIF Remover', 'Remove Photo Metadata', 'Strip GPS From Image'],
    how_to_use=['Upload your images', 'Download the cleaned copies'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("quality", "JPEG quality", OptionType.number, default=92, min=1, max=100),
    ],
))
define(ToolConfig(
    name="Image Dimension Checker", slug="image-dimension-checker", category="image-tools",
    description="Size, ratio, megapixels and file weight at a glance.",
    seo_keywords=['Image Size Checker', 'Image Dimensions', 'Check Photo Resolution'],
    how_to_use=['Upload your images', 'Read the details'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=False, supports_zip_download=True,
    options=[],
))
define(ToolConfig(
    name="DPI Checker and Changer", slug="dpi-checker", category="image-tools",
    description="Check the DPI and see the real printed size.",
    seo_keywords=['DPI Checker', 'Change Image DPI', '300 DPI Converter'],
    how_to_use=['Upload your image', 'Set a new DPI if you need one', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("set_dpi", "Set DPI (0 = just check)", OptionType.number, default=0, min=0, max=1200),
    ],
))
define(ToolConfig(
    name="Reverse Image Search Helper", slug="reverse-image-search", category="image-tools",
    description="Build the search links for an image on every major engine.",
    seo_keywords=['Reverse Image Search', 'Find Image Source', 'Search By Image URL'],
    how_to_use=['Paste the image URL', 'Open the search links'],
    input_kind=InputKind.options, supports_single_upload=False,
    supports_download=False, supports_zip_download=False,
    options=[
        _opt("image_url", "Image URL", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Add Text to Image", slug="add-text-to-image", category="image-tools",
    description="Put a caption on a photo, with an outline that stays readable.",
    seo_keywords=['Add Text To Image', 'Write On Photo', 'Text Over Image'],
    how_to_use=['Upload your image', 'Type the text', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("message", "Text", OptionType.text, default=""),
        _opt("position", "Position", OptionType.select, default="bottom", choices=["top", "middle", "bottom"]),
        _opt("font_size", "Font size (0 = auto)", OptionType.number, default=0, min=0, max=400),
        _opt("color", "Text colour", OptionType.color, default="#ffffff"),
        _opt("outline", "Outline the text", OptionType.boolean, default=True),
        _opt("outline_color", "Outline colour", OptionType.color, default="#000000"),
        _opt("opacity", "Opacity (%)", OptionType.number, default=100, min=1, max=100),
    ],
))
define(ToolConfig(
    name="Add Border to Image", slug="add-border", category="image-tools",
    description="Add a solid, double or polaroid frame.",
    seo_keywords=['Add Border To Image', 'Photo Frame Online', 'Image Border Maker'],
    how_to_use=['Upload your image', 'Pick a style', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("style", "Style", OptionType.select, default="solid", choices=["solid", "double", "polaroid"]),
        _opt("width", "Border width", OptionType.number, default=0, min=1, max=400),
        _opt("color", "Border colour", OptionType.color, default="#ffffff"),
        _opt("inner_color", "Inner colour", OptionType.color, default="#111827"),
    ],
))
define(ToolConfig(
    name="Meme Generator", slug="meme-generator", category="image-tools",
    description="Top and bottom captions in the classic meme style.",
    seo_keywords=['Meme Generator', 'Make A Meme', 'Meme Maker Online'],
    how_to_use=['Upload the image', 'Type the captions', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("top", "Top text", OptionType.text, default=""),
        _opt("bottom", "Bottom text", OptionType.text, default=""),
        _opt("font_size", "Font size (0 = auto)", OptionType.number, default=0, min=0, max=400),
        _opt("uppercase", "Uppercase", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Collage Maker", slug="collage-maker", category="image-tools",
    description="Arrange several photos into a clean grid.",
    seo_keywords=['Collage Maker', 'Photo Grid Maker', 'Picture Collage Online'],
    how_to_use=['Upload your photos', 'Set the columns', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("columns", "Columns (0 = auto)", OptionType.number, default=0, min=0, max=10),
        _opt("cell_size", "Cell size (px)", OptionType.number, default=400, min=80, max=1600),
        _opt("gap", "Gap (px)", OptionType.number, default=10, min=0, max=100),
        _opt("background", "Background", OptionType.color, default="#ffffff"),
    ],
))
define(ToolConfig(
    name="Image Splitter", slug="image-splitter", category="image-tools",
    description="Cut an image into a grid for a carousel post.",
    seo_keywords=['Image Splitter', 'Split Image Into Grid', 'Instagram Carousel Cutter'],
    how_to_use=['Upload your image', 'Set the grid', 'Download the pieces'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("columns", "Columns", OptionType.number, default=3, min=1, max=10),
        _opt("rows", "Rows", OptionType.number, default=1, min=1, max=10),
    ],
))
define(ToolConfig(
    name="Favicon Generator", slug="favicon-generator", category="image-tools",
    description="Every favicon size a site needs, plus the HTML.",
    seo_keywords=['Favicon Generator', 'Make A Favicon', 'ICO Generator'],
    how_to_use=['Upload a square logo', 'Download the set', 'Paste the HTML into your head'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("apple_background", "Apple icon background", OptionType.color, default="#ffffff"),
    ],
))
define(ToolConfig(
    name="Placeholder Image Generator", slug="placeholder-image-generator", category="image-tools",
    description="Generate sized placeholder images for mockups.",
    seo_keywords=['Placeholder Image Generator', 'Dummy Image Maker', 'Mockup Placeholder'],
    how_to_use=['Set the size', 'Add a label', 'Download'],
    input_kind=InputKind.options, supports_single_upload=False,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("width", "Width", OptionType.number, default=800, min=16, max=4000),
        _opt("height", "Height", OptionType.number, default=600, min=16, max=4000),
        _opt("label", "Label (blank = the size)", OptionType.text, default=""),
        _opt("background", "Background", OptionType.color, default="#e2e8f0"),
        _opt("color", "Text colour", OptionType.color, default="#475569"),
        _opt("diagonals", "Draw diagonals", OptionType.boolean, default=False),
        _opt("format", "Format", OptionType.select, default="png", choices=["png", "jpg"]),
    ],
))
define(ToolConfig(
    name="Gradient Generator", slug="gradient-generator", category="image-tools",
    description="Make a gradient image and get the matching CSS.",
    seo_keywords=['Gradient Generator', 'CSS Gradient Image', 'Background Gradient Maker'],
    how_to_use=['Pick two colours', 'Choose the style', 'Download'],
    input_kind=InputKind.options, supports_single_upload=False,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("start_color", "Start colour", OptionType.color, default="#4f46e5"),
        _opt("end_color", "End colour", OptionType.color, default="#ec4899"),
        _opt("style", "Style", OptionType.select, default="linear", choices=["linear", "radial"]),
        _opt("angle", "Angle", OptionType.number, default=90, min=0, max=360),
        _opt("width", "Width", OptionType.number, default=1200, min=16, max=4000),
        _opt("height", "Height", OptionType.number, default=600, min=16, max=4000),
    ],
))
define(ToolConfig(
    name="Signature Maker", slug="signature-maker", category="image-tools",
    description="Turn a photo of your signature into a transparent PNG.",
    seo_keywords=['Signature Maker', 'Transparent Signature', 'Signature Background Remover'],
    how_to_use=['Photograph your signature on white paper', 'Upload it', 'Download the PNG'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("threshold", "Ink threshold", OptionType.number, default=160, min=1, max=254),
        _opt("ink_color", "Ink colour", OptionType.color, default="#000000"),
        _opt("trim", "Trim the empty edges", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Passport Photo Maker", slug="passport-photo-maker", category="image-tools",
    description="Crop to an official size and lay out a print sheet.",
    seo_keywords=['Passport Photo Maker', 'ID Photo Tool', 'Visa Photo Size'],
    how_to_use=['Upload your photo', 'Pick the country size', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("size", "Photo size", OptionType.select, default="US passport (2x2 in)", choices=["US passport (2x2 in)", "UK / EU passport (35x45 mm)", "India passport (35x45 mm)", "Schengen visa (35x45 mm)", "China visa (33x48 mm)", "Canada passport (50x70 mm)", "Australia passport (35x45 mm)"]),
        _opt("dpi", "DPI", OptionType.number, default=300, min=150, max=1200),
        _opt("print_sheet", "Also make a 6x4 print sheet", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Image to ASCII Art", slug="image-to-ascii", category="image-tools",
    description="Turn a picture into text art.",
    seo_keywords=['Image To ASCII', 'ASCII Art From Photo', 'Picture To Text Art'],
    how_to_use=['Upload your image', 'Set the width', 'Copy the art'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("width", "Columns", OptionType.number, default=100, min=20, max=400),
        _opt("invert", "Invert", OptionType.boolean, default=False),
        _opt("enhance_contrast", "Boost contrast", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Sprite Sheet Generator", slug="sprite-sheet-generator", category="image-tools",
    description="Pack frames into one sheet, with the CSS positions.",
    seo_keywords=['Sprite Sheet Generator', 'CSS Sprite Maker', 'Combine Images Sprite'],
    how_to_use=['Upload your frames', 'Pick the layout', 'Download the sheet and CSS'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("layout", "Layout", OptionType.select, default="horizontal", choices=["horizontal", "vertical", "grid"]),
        _opt("columns", "Grid columns (0 = auto)", OptionType.number, default=0, min=0, max=20),
    ],
))
define(ToolConfig(
    name="CSS Image Snippet", slug="css-image-snippet", category="image-tools",
    description="Embed an image in CSS as a data URI.",
    seo_keywords=['CSS Background Image', 'Image To Data URI', 'Base64 CSS Background'],
    how_to_use=['Upload a small image', 'Copy the CSS'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("selector", "CSS selector", OptionType.text, default=".hero"),
        _opt("size", "background-size", OptionType.select, default="cover", choices=["cover", "contain", "auto", "100% 100%"]),
        _opt("position", "background-position", OptionType.select, default="center", choices=["center", "top", "bottom", "left", "right"]),
    ],
))
define(ToolConfig(
    name="Social Media Image Resizer", slug="social-media-resizer", category="image-tools",
    description="Export one image at the right size for every platform.",
    seo_keywords=['Social Media Image Resizer', 'Instagram Size Resizer', 'Social Post Dimensions'],
    how_to_use=['Upload your image', 'Tick the placements', 'Download the set'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("platforms", "Placements (comma separated)", OptionType.text, default="Instagram post (square), Facebook post, X / Twitter post, YouTube thumbnail, Open Graph / link preview"),
        _opt("mode", "Fit", OptionType.select, default="crop", choices=["crop", "pad"]),
        _opt("background", "Pad colour", OptionType.color, default="#ffffff"),
    ],
))
define(ToolConfig(
    name="Profile Picture Maker", slug="profile-picture-maker", category="image-tools",
    description="A clean square or circular avatar, ready to upload.",
    seo_keywords=['Profile Picture Maker', 'Avatar Maker', 'Circular Profile Photo'],
    how_to_use=['Upload your photo', 'Pick the size', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("size", "Size (px)", OptionType.number, default=512, min=64, max=2048),
        _opt("circle", "Circular", OptionType.boolean, default=True),
        _opt("border_width", "Ring width", OptionType.number, default=0, min=0, max=200),
        _opt("border_color", "Ring colour", OptionType.color, default="#ffffff"),
    ],
))
define(ToolConfig(
    name="Thumbnail Maker", slug="thumbnail-maker", category="image-tools",
    description="Small, right-sized copies, with an optional caption.",
    seo_keywords=['Thumbnail Maker', 'Create Thumbnails', 'Image Thumbnail Generator'],
    how_to_use=['Upload your images', 'Set the size', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("width", "Width", OptionType.number, default=400, min=32, max=2000),
        _opt("height", "Height", OptionType.number, default=300, min=32, max=2000),
        _opt("crop_to_fit", "Crop to fit", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Background Changer", slug="background-changer", category="image-tools",
    description="Swap a plain background for a colour, a blur or another image.",
    seo_keywords=['Background Changer', 'Replace Photo Background', 'Change Image Background'],
    how_to_use=['Upload the subject', 'Pick a new background', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("background", "New background", OptionType.select, default="color", choices=["color", "blur", "transparent", "image"]),
        _opt("color", "Colour", OptionType.color, default="#ffffff"),
        _opt("blur_radius", "Blur radius", OptionType.number, default=12, min=2, max=60),
        _opt("tolerance", "Removal tolerance", OptionType.number, default=60, min=5, max=200),
    ],
))
define(ToolConfig(
    name="GIF Converter", slug="gif-converter", category="image-tools",
    description="Build an animated GIF from images, or split one into frames.",
    seo_keywords=['GIF Maker', 'Images To GIF', 'GIF To Frames'],
    how_to_use=['Upload your images or a GIF', 'Pick the direction', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'avif'], max_upload_mb=25,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("direction", "Convert", OptionType.select, default="images_to_gif", choices=["images_to_gif", "gif_to_frames"]),
        _opt("fps", "Frames per second", OptionType.number, default=5, min=1, max=50),
        _opt("width", "Width (0 = keep)", OptionType.number, default=0, min=0, max=1200),
        _opt("loop", "Loop forever", OptionType.boolean, default=True),
        _opt("max_frames", "Max frames to extract", OptionType.number, default=60, min=1, max=300),
    ],
))
define(ToolConfig(
    name="Remove PDF Pages", slug="pdf-remove-pages", category="pdf-tools",
    description="Delete pages from a PDF and keep the rest.",
    seo_keywords=['Remove PDF Pages', 'Delete Pages From PDF', 'PDF Page Remover'],
    how_to_use=['Upload your PDF', 'List the pages to remove', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("pages", "Pages to remove", OptionType.text, default=""),
    ],
))
define(ToolConfig(
    name="Insert Pages into PDF", slug="pdf-insert-pages", category="pdf-tools",
    description="Insert one PDF into another at any point.",
    seo_keywords=['Insert Pages Into PDF', 'Add Pages To PDF', 'Merge PDF At Page'],
    how_to_use=['Upload the original, then the PDF to insert', 'Choose where it goes', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("after_page", "Insert after page (0 = start)", OptionType.number, default=0, min=0, max=5000),
    ],
))
define(ToolConfig(
    name="Alternate PDF Pages", slug="pdf-alternate-pages", category="pdf-tools",
    description="Interleave two PDFs — for odd and even scanner passes.",
    seo_keywords=['Alternate PDF Pages', 'Merge Odd And Even Pages', 'Interleave PDF'],
    how_to_use=['Upload the odd pages, then the even', 'Reverse the second if needed', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("reverse_second", "Second file is in reverse order", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Resize PDF Pages", slug="pdf-resize-pages", category="pdf-tools",
    description="Scale every page onto A4, Letter or another size.",
    seo_keywords=['Resize PDF Pages', 'Scale PDF', 'Change PDF Page Size'],
    how_to_use=['Upload your PDF', 'Pick the paper size', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("size", "Paper size", OptionType.select, default="a4", choices=["a4", "letter", "legal", "a3", "a5"]),
        _opt("landscape", "Landscape", OptionType.boolean, default=False),
        _opt("margin", "Margin (pt)", OptionType.number, default=0, min=0, max=100),
    ],
))
define(ToolConfig(
    name="Crop PDF", slug="pdf-crop", category="pdf-tools",
    description="Trim the margins off every page.",
    seo_keywords=['Crop PDF', 'Trim PDF Margins', 'PDF Margin Cutter'],
    how_to_use=['Upload your PDF', 'Set the trim or use auto', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("auto", "Crop to content automatically", OptionType.boolean, default=False),
        _opt("auto_margin", "Auto margin (pt)", OptionType.number, default=6, min=0, max=60),
        _opt("top", "Top (%)", OptionType.number, default=0, min=0, max=45),
        _opt("bottom", "Bottom (%)", OptionType.number, default=0, min=0, max=45),
        _opt("left", "Left (%)", OptionType.number, default=0, min=0, max=45),
        _opt("right", "Right (%)", OptionType.number, default=0, min=0, max=45),
    ],
))
define(ToolConfig(
    name="Grayscale PDF", slug="pdf-grayscale", category="pdf-tools",
    description="Convert a PDF to greyscale for cheaper printing.",
    seo_keywords=['Grayscale PDF', 'Black And White PDF', 'Remove Color From PDF'],
    how_to_use=['Upload your PDF', 'Set the quality', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("dpi", "Render DPI", OptionType.number, default=150, min=72, max=400),
    ],
))
define(ToolConfig(
    name="Flatten PDF", slug="pdf-flatten", category="pdf-tools",
    description="Bake annotations and form fields so nothing stays editable.",
    seo_keywords=['Flatten PDF', 'Make PDF Uneditable', 'Flatten PDF Forms'],
    how_to_use=['Upload your PDF', 'Choose the method', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("rasterize", "Rasterise the pages", OptionType.boolean, default=False),
        _opt("dpi", "Raster DPI", OptionType.number, default=150, min=72, max=400),
    ],
))
define(ToolConfig(
    name="Repair PDF", slug="pdf-repair", category="pdf-tools",
    description="Rebuild a damaged PDF so it opens again.",
    seo_keywords=['Repair PDF', 'Fix Corrupt PDF', 'PDF Recovery Tool'],
    how_to_use=['Upload the damaged PDF', 'Download the rebuilt copy'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[],
))
define(ToolConfig(
    name="Optimize PDF for Web", slug="pdf-optimize-web", category="pdf-tools",
    description="Linearise so page one shows before the rest downloads.",
    seo_keywords=['Optimize PDF For Web', 'Linearize PDF', 'Fast Web View PDF'],
    how_to_use=['Upload your PDF', 'Choose the image quality', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("downsample_images", "Downsample images", OptionType.boolean, default=True),
        _opt("image_dpi", "Image DPI", OptionType.number, default=150, min=72, max=400),
        _opt("quality", "Image quality", OptionType.number, default=80, min=10, max=100),
    ],
))
define(ToolConfig(
    name="Enhance Scanned PDF", slug="pdf-enhance-scan", category="pdf-tools",
    description="Whiten and sharpen a scanned or photographed document.",
    seo_keywords=['Enhance Scanned PDF', 'Clean Up Scan', 'Whiten PDF Scan'],
    how_to_use=['Upload the scan', 'Leave the defaults on', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("dpi", "Render DPI", OptionType.number, default=200, min=100, max=400),
        _opt("whiten", "Whiten the paper", OptionType.boolean, default=True),
        _opt("sharpen", "Sharpen the text", OptionType.boolean, default=True),
        _opt("quality", "JPEG quality", OptionType.number, default=80, min=30, max=100),
    ],
))
define(ToolConfig(
    name="Add Text to PDF", slug="pdf-add-text", category="pdf-tools",
    description="Stamp text onto any page of a PDF.",
    seo_keywords=['Add Text To PDF', 'Write On PDF', 'PDF Text Stamp'],
    how_to_use=['Upload your PDF', 'Type the text', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("message", "Text", OptionType.text, default=""),
        _opt("pages", "Pages (blank = all)", OptionType.text, default=""),
        _opt("position", "Position", OptionType.select, default="top-left", choices=["top-left", "top-center", "top-right", "bottom-left", "bottom-center", "bottom-right"]),
        _opt("font_size", "Font size", OptionType.number, default=14, min=6, max=96),
        _opt("color", "Colour", OptionType.color, default="#000000"),
        _opt("offset_x", "Nudge across", OptionType.number, default=0, min=-500, max=500),
        _opt("offset_y", "Nudge down", OptionType.number, default=0, min=-500, max=500),
    ],
))
define(ToolConfig(
    name="Add Image to PDF", slug="pdf-add-image", category="pdf-tools",
    description="Place a logo or picture on chosen pages.",
    seo_keywords=['Add Image To PDF', 'Add Logo To PDF', 'Insert Picture Into PDF'],
    how_to_use=['Upload the PDF, then the image', 'Pick the position', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['pdf', 'png', 'jpg', 'jpeg', 'webp'], max_upload_mb=50,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("pages", "Pages (blank = all)", OptionType.text, default=""),
        _opt("position", "Position", OptionType.select, default="top-right", choices=["top-left", "top-center", "top-right", "middle-center", "bottom-left", "bottom-center", "bottom-right"]),
        _opt("width_percent", "Width (% of page)", OptionType.number, default=25, min=1, max=100),
        _opt("margin", "Margin (pt)", OptionType.number, default=24, min=0, max=200),
        _opt("behind_text", "Place behind the text", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Add Header and Footer", slug="pdf-header-footer", category="pdf-tools",
    description="Running header and footer with page numbers.",
    seo_keywords=['PDF Header Footer', 'Add Header To PDF', 'PDF Footer Text'],
    how_to_use=['Upload your PDF', 'Write the header and footer', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("header", "Header text", OptionType.text, default=""),
        _opt("footer", "Footer text", OptionType.text, default="Page {page} of {total}"),
        _opt("align", "Alignment", OptionType.select, default="center", choices=["left", "center", "right"]),
        _opt("font_size", "Font size", OptionType.number, default=9, min=6, max=24),
        _opt("margin", "Margin (pt)", OptionType.number, default=28, min=8, max=100),
        _opt("skip_first_page", "Skip the first page", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Redact PDF", slug="pdf-redact", category="pdf-tools",
    description="Permanently remove words from a PDF, not just cover them.",
    seo_keywords=['Redact PDF', 'Black Out Text In PDF', 'PDF Redaction Tool'],
    how_to_use=['Upload your PDF', 'List the words to remove', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("ignore_case", "Ignore case", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Sign PDF", slug="pdf-sign", category="pdf-tools",
    description="Place a signature image on a page and lock it in.",
    seo_keywords=['Sign PDF', 'Add Signature To PDF', 'E Sign PDF Online'],
    how_to_use=['Upload the PDF, then your signature image', 'Choose the page', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['pdf', 'png', 'jpg', 'jpeg'], max_upload_mb=50,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("page", "Page (0 = last)", OptionType.number, default=0, min=0, max=5000),
        _opt("width", "Signature width (pt)", OptionType.number, default=160, min=40, max=600),
        _opt("x", "X (0 = auto)", OptionType.number, default=0, min=0, max=2000),
        _opt("y", "Y (0 = auto)", OptionType.number, default=0, min=0, max=2000),
        _opt("add_date", "Add the date", OptionType.boolean, default=True),
        _opt("lock", "Flatten so it cannot be moved", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Create Blank PDF", slug="pdf-create-blank", category="pdf-tools",
    description="Blank, lined, gridded or dotted pages.",
    seo_keywords=['Create Blank PDF', 'Blank PDF Generator', 'Lined Paper PDF'],
    how_to_use=['Pick a style and size', 'Set the page count', 'Download'],
    input_kind=InputKind.text, supports_single_upload=False,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("pages", "Pages", OptionType.number, default=1, min=1, max=200),
        _opt("size", "Paper size", OptionType.select, default="a4", choices=["a4", "letter", "legal", "a3", "a5"]),
        _opt("landscape", "Landscape", OptionType.boolean, default=False),
        _opt("style", "Style", OptionType.select, default="blank", choices=["blank", "lined", "grid", "dotted"]),
        _opt("spacing", "Line spacing (pt)", OptionType.number, default=24, min=6, max=100),
    ],
))
define(ToolConfig(
    name="Bates Numbering", slug="pdf-bates-numbering", category="pdf-tools",
    description="Sequential legal numbering across a whole production.",
    seo_keywords=['Bates Numbering', 'Bates Stamp PDF', 'Legal Page Numbering'],
    how_to_use=['Upload your PDFs in order', 'Set the prefix and start', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("prefix", "Prefix", OptionType.text, default=""),
        _opt("suffix", "Suffix", OptionType.text, default=""),
        _opt("start", "Start at", OptionType.number, default=1, min=0, max=999999),
        _opt("digits", "Digits", OptionType.number, default=6, min=1, max=12),
        _opt("position", "Position", OptionType.select, default="bottom-right", choices=["bottom-right", "bottom-left", "top-right", "top-left"]),
        _opt("font_size", "Font size", OptionType.number, default=10, min=6, max=24),
    ],
))
define(ToolConfig(
    name="Remove PDF Metadata", slug="pdf-remove-metadata", category="pdf-tools",
    description="Strip author, software and timestamps from a PDF.",
    seo_keywords=['Remove PDF Metadata', 'PDF Metadata Cleaner', 'Strip PDF Author'],
    how_to_use=['Upload your PDFs', 'Download the cleaned copies'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=True,
    options=[],
))
define(ToolConfig(
    name="Compare PDFs", slug="pdf-compare", category="pdf-tools",
    description="See exactly what changed between two PDFs.",
    seo_keywords=['Compare PDFs', 'PDF Diff Tool', 'PDF Comparison'],
    how_to_use=['Upload both PDFs', 'Read the differences'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=False, supports_zip_download=True,
    options=[
        _opt("ignore_whitespace", "Ignore spacing", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="PDF to Base64", slug="pdf-to-base64", category="pdf-tools",
    description="Encode a PDF as Base64 or a data URI.",
    seo_keywords=['PDF To Base64', 'Encode PDF Base64', 'PDF Data URI'],
    how_to_use=['Upload your PDF', 'Copy the string'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("data_uri", "Include the data: prefix", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="Extract Text from PDF", slug="pdf-extract-text", category="pdf-tools",
    description="Pull the text out as TXT, Markdown or JSON.",
    seo_keywords=['Extract Text From PDF', 'PDF To Text', 'PDF Text Extractor'],
    how_to_use=['Upload your PDF', 'Pick the format', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("format", "Format", OptionType.select, default="txt", choices=["txt", "markdown", "json"]),
        _opt("keep_layout", "Keep the column order", OptionType.boolean, default=False),
        _opt("page_breaks", "Mark page breaks", OptionType.boolean, default=True),
    ],
))
define(ToolConfig(
    name="PDF to HTML", slug="pdf-to-html", category="pdf-tools",
    description="Convert a PDF into a readable HTML page.",
    seo_keywords=['PDF To HTML', 'Convert PDF To Web Page', 'PDF HTML Converter'],
    how_to_use=['Upload your PDF', 'Choose the style', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("preserve_layout", "Keep the exact layout", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Extract Images from PDF", slug="pdf-extract-images", category="pdf-tools",
    description="Pull out embedded images at full resolution.",
    seo_keywords=['Extract Images From PDF', 'PDF Image Extractor', 'Get Pictures From PDF'],
    how_to_use=['Upload your PDF', 'Set a minimum size', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=True,
    options=[
        _opt("min_size", "Skip images under (px)", OptionType.number, default=100, min=0, max=2000),
        _opt("max_images", "Maximum to extract", OptionType.number, default=100, min=1, max=500),
    ],
))
define(ToolConfig(
    name="Extract Tables from PDF", slug="pdf-extract-tables", category="pdf-tools",
    description="Find tables and export them as CSV.",
    seo_keywords=['Extract Tables From PDF', 'PDF Table To CSV', 'PDF Table Extractor'],
    how_to_use=['Upload your PDF', 'Download the CSV files'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=True,
    options=[],
))
define(ToolConfig(
    name="Extract PDF Attachments", slug="pdf-extract-attachments", category="pdf-tools",
    description="Pull out files embedded inside a PDF.",
    seo_keywords=['Extract PDF Attachments', 'PDF Embedded Files', 'Get Attachments From PDF'],
    how_to_use=['Upload your PDF', 'Download the attachments'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=True,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=True,
    options=[],
))
define(ToolConfig(
    name="Summarize PDF", slug="pdf-summarize", category="pdf-tools",
    description="Shorten a PDF to its most important sentences.",
    seo_keywords=['Summarize PDF', 'PDF Summary Tool', 'Shorten PDF'],
    how_to_use=['Upload your PDF', 'Choose the length', 'Read the summary'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("sentences", "Sentences to keep", OptionType.number, default=5, min=1, max=30),
    ],
))
define(ToolConfig(
    name="HTML to PDF", slug="html-to-pdf", category="pdf-tools",
    description="Turn pasted HTML into a paginated PDF.",
    seo_keywords=['HTML To PDF', 'Convert HTML To PDF', 'Web Page To PDF'],
    how_to_use=['Paste your HTML', 'Add CSS if you want', 'Download'],
    input_kind=InputKind.text, supports_single_upload=False,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("css", "Extra CSS", OptionType.text, default=""),
        _opt("size", "Paper size", OptionType.select, default="a4", choices=["a4", "letter", "legal", "a3", "a5"]),
        _opt("margin", "Margin (pt)", OptionType.number, default=50, min=0, max=200),
    ],
))
define(ToolConfig(
    name="Text to PDF", slug="text-to-pdf", category="pdf-tools",
    description="Turn plain text or Markdown into a formatted PDF.",
    seo_keywords=['Text To PDF', 'Markdown To PDF', 'TXT To PDF Converter'],
    how_to_use=['Paste your text', 'Pick the font size', 'Download'],
    input_kind=InputKind.text, supports_single_upload=False,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("markdown", "Read it as Markdown", OptionType.boolean, default=True),
        _opt("font", "Font", OptionType.select, default="sans-serif", choices=["sans-serif", "serif", "monospace"]),
        _opt("font_size", "Font size", OptionType.number, default=11, min=8, max=24),
        _opt("size", "Paper size", OptionType.select, default="a4", choices=["a4", "letter", "legal", "a3", "a5"]),
        _opt("margin", "Margin (pt)", OptionType.number, default=56, min=0, max=200),
    ],
))
define(ToolConfig(
    name="EPUB to PDF", slug="epub-to-pdf", category="pdf-tools",
    description="Convert an ebook into a PDF you can print.",
    seo_keywords=['EPUB To PDF', 'Ebook To PDF', 'Convert EPUB'],
    how_to_use=['Upload your .epub', 'Pick the paper size', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['epub'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("size", "Paper size", OptionType.select, default="a5", choices=["a4", "letter", "legal", "a3", "a5"]),
        _opt("margin", "Margin (pt)", OptionType.number, default=40, min=0, max=200),
    ],
))
define(ToolConfig(
    name="PDF to EPUB", slug="pdf-to-epub", category="pdf-tools",
    description="Build a reflowable ebook from a PDF.",
    seo_keywords=['PDF To EPUB', 'Convert PDF To Ebook', 'PDF EPUB Converter'],
    how_to_use=['Upload your PDF', 'Set the title', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("title", "Book title", OptionType.text, default=""),
        _opt("author", "Author", OptionType.text, default=""),
        _opt("pages_per_chapter", "Pages per chapter", OptionType.number, default=10, min=1, max=100),
    ],
))
define(ToolConfig(
    name="Extract PDF Form Data", slug="pdf-extract-form-data", category="pdf-tools",
    description="Read every filled field out of a PDF form.",
    seo_keywords=['Extract PDF Form Data', 'Read PDF Form Fields', 'PDF Form To JSON'],
    how_to_use=['Upload the form', 'Read the values'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[],
))
define(ToolConfig(
    name="Fill PDF Form", slug="pdf-fill-form", category="pdf-tools",
    description="Fill a PDF form from JSON or name=value lines.",
    seo_keywords=['Fill PDF Form', 'PDF Form Filler', 'Complete PDF Form'],
    how_to_use=['Upload the form', 'Enter the values', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("flatten", "Lock the answers in", OptionType.boolean, default=False),
    ],
))
define(ToolConfig(
    name="Create Fillable PDF Form", slug="pdf-create-form", category="pdf-tools",
    description="Add text boxes and checkboxes to a PDF.",
    seo_keywords=['Create Fillable PDF', 'PDF Form Builder', 'Make PDF Form'],
    how_to_use=['Upload your PDF', 'List the fields', 'Download'],
    input_kind=InputKind.file, supports_single_upload=True, supports_multi_upload=False,
    accepted_extensions=['pdf'], max_upload_mb=50,
    supports_download=True, supports_zip_download=False,
    options=[
        _opt("page", "Page", OptionType.number, default=1, min=1, max=5000),
        _opt("start_y", "Start from (pt)", OptionType.number, default=100, min=20, max=700),
        _opt("spacing", "Row spacing (pt)", OptionType.number, default=44, min=28, max=120),
        _opt("label_width", "Label width (pt)", OptionType.number, default=150, min=60, max=300),
        _opt("field_width", "Field width (pt)", OptionType.number, default=240, min=60, max=400),
    ],
))
