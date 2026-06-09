"""SEO content engine for tools.

Produces an "About" explanation, Features, Benefits and a rich FAQ set for every
tool. Popular tools get hand-written depth (RICH); all others get strong,
capability-aware generated content so the entire 50+ catalogue is SEO-ready.

Kept separate from registry.py so content can grow without touching the tool
capability definitions. Resolved at request time by the /api/tools/{slug} route.
"""
from __future__ import annotations

from app.tools.registry import InputKind, ToolConfig

CATEGORY_LABELS = {
    "pdf-tools": "PDF",
    "image-tools": "image",
    "text-tools": "text",
    "developer-tools": "developer",
}


# --- Hand-written content for popular / high-traffic tools -------------------
# Each entry may supply: about (str), faqs (list of (question, answer)).
RICH: dict[str, dict] = {
    "image-compressor": {
        "about": (
            "Image Compressor is a free online tool that reduces the file size of your JPG, PNG and "
            "WebP images without a noticeable drop in quality. Large images slow down websites, eat up "
            "storage and make email attachments bounce — compressing them fixes all three.\n\n"
            "Our compressor uses smart quality optimization to strip unnecessary data while preserving "
            "the visual detail that matters. You control the compression level, so you can trade a "
            "little more quality for a much smaller file, or keep things crisp. You can compress a "
            "single photo or batch-compress dozens at once and download them together as a ZIP.\n\n"
            "Everything runs in your browser session and your images are deleted automatically within "
            "10 minutes — no account, no watermark, and no limits."
        ),
        "faqs": [
            ("How much can Image Compressor reduce my file size?",
             "Most photos shrink by 40–80% depending on the original quality and the compression level you choose. JPGs and PNGs with lots of flat color compress the most."),
            ("Will compressing reduce the quality of my image?",
             "A little — but with the default settings the difference is almost invisible to the eye while the file gets dramatically smaller. Raise the quality slider if you need maximum fidelity."),
            ("Can I compress multiple images at once?",
             "Yes. Upload as many as you like, compress them in one click, and download them all together as a ZIP file."),
        ],
    },
    "pdf-merge": {
        "about": (
            "PDF Merge lets you combine several PDF files into one organized document, completely free "
            "and online. It is perfect for joining scanned pages, bundling invoices, assembling a report "
            "from multiple sources, or merging contract pages into a single file to send.\n\n"
            "Just upload your PDFs, drag them into the order you want, and click Merge. The pages are "
            "stitched together in sequence into a brand-new PDF that you can download instantly.\n\n"
            "No software to install and no sign-up required. Your files are processed securely and "
            "removed from our servers automatically within 10 minutes."
        ),
        "faqs": [
            ("Can I choose the order pages appear in the merged PDF?",
             "Yes. Arrange the uploaded files in any order before merging and the final document follows that exact sequence."),
            ("Is there a limit to how many PDFs I can merge?",
             "You can merge many files at once. Each individual file can be up to 50 MB."),
            ("Will merging change the quality of my PDFs?",
             "No. Pages are copied as-is, so text stays sharp and selectable and images keep their original resolution."),
        ],
    },
    "pdf-split": {
        "about": (
            "PDF Split breaks a single PDF into separate files — either one file per page or a specific "
            "range you choose (for example 1-3,5). It is the fastest way to pull a chapter out of a "
            "large document, separate scanned receipts, or share just the pages someone needs.\n\n"
            "Upload your PDF, tell us which pages to extract, and download the results individually or "
            "as a ZIP. Free, online, and private — files auto-delete within 10 minutes."
        ),
        "faqs": [
            ("How do I select specific pages to split?",
             "Enter a page range like 1-3,5 in the range field. Leave it blank to split every page into its own PDF."),
            ("Does splitting keep the original formatting?",
             "Yes. Each extracted page is identical to the source — text, fonts and images are preserved exactly."),
        ],
    },
    "pdf-compress": {
        "about": (
            "PDF Compress reduces the size of bulky PDF files so they are easier to email, upload and "
            "store. It works by compressing the internal streams and cleaning out unused objects, "
            "shrinking the file while keeping your pages readable.\n\n"
            "It is ideal for large scanned documents, image-heavy presentations and PDFs that exceed an "
            "upload limit. Upload, click compress, and download a lighter file in seconds — free, "
            "private, and with automatic file deletion."
        ),
        "faqs": [
            ("How much smaller will my PDF get?",
             "Savings vary by document. Text-only PDFs may shrink modestly, while scanned or image-heavy PDFs often compress significantly. The result shows the exact size saved."),
            ("Will compression make my PDF blurry?",
             "Text and vector content stay crisp. The tool focuses on removing redundancy and optimizing streams rather than aggressively downsampling content."),
        ],
    },
    "qr-code-generator": {
        "about": (
            "QR Code Generator turns any link, text, or contact detail into a scannable QR code in "
            "seconds. QR codes are everywhere — on menus, posters, packaging and business cards — "
            "because anyone can open them with a phone camera.\n\n"
            "Enter your URL or text, customize the foreground and background colors to match your brand, "
            "pick a size, and download a high-resolution PNG ready to print or share. It is free, "
            "unlimited, and requires no sign-up."
        ),
        "faqs": [
            ("Do the QR codes I generate ever expire?",
             "No. The codes are static, so they keep working forever and never expire as long as the link they point to is live."),
            ("Can I customize the colors of my QR code?",
             "Yes. Choose any foreground and background color. Keep good contrast so cameras can scan it reliably."),
            ("Can I use these QR codes commercially?",
             "Absolutely. The QR codes you generate are yours to use on products, marketing and anything else, free of charge."),
        ],
    },
    "word-counter": {
        "about": (
            "Word Counter instantly counts the words, characters, sentences and paragraphs in your text "
            "and estimates reading time. It is a must-have for writers, students, marketers and SEO "
            "professionals who need to hit a specific length — essays, meta descriptions, tweets, "
            "articles or assignments.\n\n"
            "Just paste your text and the statistics update right away. Nothing is uploaded or stored, "
            "so even sensitive drafts stay completely private on your device."
        ),
        "faqs": [
            ("How is reading time calculated?",
             "Reading time is based on an average adult reading speed of about 200 words per minute."),
            ("Is my text saved or sent anywhere?",
             "No. Counting happens in your browser session and your text is never stored, making it safe for confidential writing."),
        ],
    },
    "json-formatter": {
        "about": (
            "JSON Formatter cleans up and pretty-prints messy or minified JSON so it is easy to read and "
            "debug. It re-indents your data with consistent spacing and validates the structure as it "
            "goes, flagging syntax errors.\n\n"
            "It is built for developers working with APIs, config files and logs. Paste your JSON, choose "
            "an indent size, and copy the beautifully formatted result. Free, instant and private."
        ),
        "faqs": [
            ("Does JSON Formatter validate my JSON?",
             "Yes. If your JSON has a syntax error the tool tells you instead of producing broken output, so it doubles as a quick validator."),
            ("Can it handle large JSON files?",
             "It comfortably formats large payloads. Processing happens locally in your session for speed and privacy."),
        ],
    },
    "background-remover": {
        "about": (
            "Background Remover makes the background of an image transparent so your subject stands out. "
            "It uses color-key removal, which works best on photos and graphics with a solid or "
            "near-solid background — product shots, logos and icons are ideal.\n\n"
            "Upload your image, adjust the tolerance to control how much of the background is removed, "
            "and download a transparent PNG. Free, online, and your images auto-delete within 10 minutes."
        ),
        "faqs": [
            ("What kind of images work best?",
             "Images with a clean, solid-colored background (like a white product photo) give the best results. Busy or gradient backgrounds are harder to key out."),
            ("What format is the result?",
             "A PNG with a transparent background, which you can drop onto any color or design."),
            ("Why is my background not fully removed?",
             "Increase the tolerance setting so more shades near the background color are made transparent."),
        ],
    },
    "image-resize": {
        "about": (
            "Image Resize changes the pixel dimensions of your images to an exact width and height, with "
            "an option to keep the aspect ratio so nothing looks stretched. Resize photos for social "
            "media, thumbnails, profile pictures or website assets in seconds.\n\n"
            "Upload, enter your target size, and download the result. Free, unlimited and private."
        ),
        "faqs": [
            ("Will resizing distort my image?",
             "Not if you keep the aspect ratio enabled — the image scales proportionally. Disable it only when you need an exact, non-proportional size."),
            ("Can I enlarge a small image?",
             "Yes, though enlarging beyond the original resolution can look soft, since there is no extra detail to add."),
        ],
    },
    "jpg-to-pdf": {
        "about": (
            "JPG to PDF converts one or more images into a single PDF document. It is the easiest way to "
            "turn photos, scans or screenshots into a tidy, shareable PDF — great for receipts, ID "
            "documents, portfolios and homework.\n\n"
            "Upload your images, arrange them in order, and download a combined PDF. Free, online, with "
            "automatic file deletion."
        ),
        "faqs": [
            ("Can I combine several images into one PDF?",
             "Yes. Upload multiple images and they are placed onto sequential pages in a single PDF, in the order you arrange them."),
            ("Which image formats can I convert?",
             "JPG, JPEG, PNG and WebP images are all supported."),
        ],
    },
    "password-generator": {
        "about": (
            "Password Generator creates strong, random passwords that are hard to guess and crack. Reusing "
            "weak passwords is one of the biggest security risks online — a unique random password for "
            "every account is the simplest way to protect yourself.\n\n"
            "Choose a length and whether to include digits and symbols, then generate a secure password "
            "instantly. Generation happens locally and nothing is stored or transmitted."
        ),
        "faqs": [
            ("Are the generated passwords stored anywhere?",
             "No. Each password is generated in your browser session and is never saved or sent anywhere, so it stays private."),
            ("What makes a strong password?",
             "Length and randomness. Aim for at least 16 characters mixing upper- and lower-case letters, digits and symbols — all of which this tool can include."),
        ],
    },
    "base64-encoder": {
        "about": (
            "Base64 Encoder converts text into a Base64 string — a safe way to embed data in URLs, JSON, "
            "HTML, email and config files where certain characters would otherwise break things.\n\n"
            "Paste your text, encode it instantly, and copy the result. Free, private and runs entirely "
            "in your session."
        ),
        "faqs": [
            ("What is Base64 used for?",
             "Base64 represents binary or text data using a safe set of characters, so it can be transmitted in places that only allow plain text — like data URIs, JWTs and email attachments."),
            ("Is Base64 the same as encryption?",
             "No. Base64 is encoding, not encryption — it is easily reversible and provides no security. Use it for transport, not to hide secrets."),
        ],
    },
}


# --- Generated fallbacks ----------------------------------------------------


def _is_file_tool(tool: ToolConfig) -> bool:
    return tool.input_kind == InputKind.file


def _privacy_sentence(tool: ToolConfig) -> str:
    if _is_file_tool(tool):
        return ("Your uploaded files are processed during your session and are automatically deleted "
                "within 10 minutes — we never store your files or any personal data.")
    return "Your input is processed securely in your session and is never stored on our servers."


def _formats_phrase(tool: ToolConfig) -> str:
    if not tool.accepted_extensions:
        return ""
    exts = ", ".join(e.upper() for e in tool.accepted_extensions)
    return exts


def gen_about(tool: ToolConfig) -> str:
    label = CATEGORY_LABELS.get(tool.category, "online")
    desc = tool.description.rstrip(".")
    kw = ", ".join(tool.seo_keywords[:3]) if tool.seo_keywords else ""
    formats = _formats_phrase(tool)

    p1 = (f"{tool.name} is a free online {label} tool that lets you {desc[0].lower()}{desc[1:]}. "
          "It runs entirely in your web browser, so there is nothing to download or install and you "
          "never need to create an account.")
    if formats:
        p1 += f" It supports {formats} files."

    p2_bits = ["Simply open the tool, add your content, and get your result in seconds."]
    if tool.supports_multi_upload:
        p2_bits.append("You can process several files in one go to save time.")
    if tool.supports_preview:
        p2_bits.append("A live preview lets you check the result before you download it.")
    p2 = " ".join(p2_bits)

    p3 = (f"{tool.name} is 100% free with no limits, no watermarks and no sign-up. "
          + _privacy_sentence(tool)
          + (f" Popular searches for this tool include {kw}." if kw else ""))

    return "\n\n".join([p1, p2, p3])


def gen_features(tool: ToolConfig) -> list[str]:
    feats = ["100% free with no usage limits", "Works in any browser — nothing to install"]
    if _is_file_tool(tool):
        feats.append("Drag & drop, click, or paste to upload")
    if tool.supports_multi_upload:
        feats.append("Batch process multiple files at once")
    if tool.supports_preview:
        feats.append("Instant live preview of your result")
    if tool.supports_zip_download:
        feats.append("Download all results together as a ZIP")
    formats = _formats_phrase(tool)
    if formats:
        feats.append(f"Supports {formats}")
    if _is_file_tool(tool):
        feats.append("No watermark added to your files")
    feats.append("Mobile, tablet and desktop friendly")
    return feats


def gen_benefits(tool: ToolConfig) -> list[str]:
    return [
        "Save time with fast, one-click processing",
        "No software, no registration and no email required",
        ("Your files stay private and auto-delete within 10 minutes"
         if _is_file_tool(tool) else "Your data stays private — nothing is stored"),
        "Completely free, with no hidden costs or watermarks",
        "Use it anywhere, on any device with a browser",
    ]


def gen_faqs(tool: ToolConfig) -> list[tuple[str, str]]:
    faqs: list[tuple[str, str]] = [
        (f"Is {tool.name} free to use?",
         f"Yes, {tool.name} is completely free with no usage limits, no watermarks and no sign-up required."),
        ("Do I need to install software or create an account?",
         "No. The tool runs entirely in your web browser — there is nothing to download and no account to create."),
    ]
    if _is_file_tool(tool):
        faqs.append((
            "Are my files safe and private?",
            "Yes. Files are processed in your session and automatically deleted within 10 minutes. We never store your files or share them.",
        ))
        faqs.append(("Is there a file size limit?",
                     "You can upload files up to 50 MB each."))
        formats = _formats_phrase(tool)
        if formats:
            faqs.append((f"Which file formats does {tool.name} support?",
                         f"{tool.name} supports {formats} files."))
    else:
        faqs.append(("Is my data stored or shared?",
                     "No. Your input is processed securely in your session and is never stored or shared."))
    if tool.how_to_use:
        steps = "; ".join(s.lower() for s in tool.how_to_use)
        faqs.append((f"How do I use {tool.name}?",
                     f"It takes just a few steps: {steps}."))
    faqs.append((f"Does {tool.name} work on mobile and Mac/Windows?",
                 "Yes. It works in any modern browser on phones, tablets, Windows, macOS and Linux."))
    return faqs


# --- Public resolver --------------------------------------------------------


def enrich(tool: ToolConfig) -> dict:
    """Return the SEO content block for a tool, merging hand-written and generated content."""
    rich = RICH.get(tool.slug, {})
    about = rich.get("about") or gen_about(tool)

    # FAQs: hand-written ones first, then generated, deduped by question.
    seen: set[str] = set()
    faqs: list[dict] = []
    for q, a in list(rich.get("faqs", [])) + gen_faqs(tool):
        key = q.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        faqs.append({"question": q, "answer": a})

    return {
        "about": about,
        "features": rich.get("features") or gen_features(tool),
        "benefits": rich.get("benefits") or gen_benefits(tool),
        "faqs": faqs,
    }
