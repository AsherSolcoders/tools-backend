"""Text tool processors.

Every processor has the signature:
    fn(files: list[Path], text: str, options: dict) -> ToolResult
"""
from __future__ import annotations

import re
import urllib.parse
from pathlib import Path

from app.tools.registry import ToolResult, register

_LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, "
    "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. "
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu "
    "fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
    "culpa qui officia deserunt mollit anim id est laborum."
)


@register("word-counter")
def word_counter(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    words = re.findall(r"\b\w+\b", text)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    reading_minutes = round(len(words) / 200, 1)  # ~200 wpm
    return ToolResult(meta={
        "words": len(words),
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "").replace("\n", "")),
        "sentences": len(sentences),
        "paragraphs": len(paragraphs),
        "reading_time_minutes": reading_minutes,
    })


@register("character-counter")
def character_counter(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    return ToolResult(meta={
        "characters": len(text),
        "characters_no_spaces": len(re.sub(r"\s", "", text)),
        "lines": text.count("\n") + 1 if text else 0,
    })


@register("case-converter")
def case_converter(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    mode = options.get("mode", "upper")
    if mode == "upper":
        out = text.upper()
    elif mode == "lower":
        out = text.lower()
    elif mode == "title":
        out = text.title()
    elif mode == "sentence":
        out = re.sub(r"(^\s*\w|[.!?]\s*\w)", lambda m: m.group().upper(), text.lower())
    else:
        out = text
    return ToolResult(text=out)


@register("duplicate-line-remover")
def duplicate_line_remover(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    case_sensitive = bool(options.get("case_sensitive", False))
    seen: set[str] = set()
    out_lines: list[str] = []
    for line in text.splitlines():
        key = line if case_sensitive else line.lower()
        if key not in seen:
            seen.add(key)
            out_lines.append(line)
    return ToolResult(text="\n".join(out_lines),
                      meta={"removed": text.count("\n") + 1 - len(out_lines) if text else 0})


@register("text-sorter")
def text_sorter(files, text: str, options: dict) -> ToolResult:
    lines = [ln for ln in (text or "").split("\n")]
    order = str(options.get("order", "a-z"))
    if _flag(options, "ignore_empty", True):
        lines = [ln for ln in lines if ln.strip()]
    key = (lambda s: s.lower()) if not _flag(options, "case_sensitive") else None
    if order == "length":
        lines.sort(key=len)
    elif order == "numeric":
        def num(s: str) -> float:
            m = re.search(r"-?\d+(?:\.\d+)?", s)
            return float(m.group(0)) if m else float("inf")
        lines.sort(key=num)
    else:
        lines.sort(key=key)
    if order == "z-a":
        lines.reverse()
    return ToolResult(text="\n".join(lines), meta={"lines": len(lines)})


@register("text-reverser")
def text_reverser(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    mode = options.get("mode", "characters")
    if mode == "characters":
        out = text[::-1]
    elif mode == "words":
        out = " ".join(text.split()[::-1])
    else:  # lines
        out = "\n".join(text.splitlines()[::-1])
    return ToolResult(text=out)


@register("url-encoder")
def url_encoder(files, text: str, options: dict) -> ToolResult:
    return ToolResult(text=urllib.parse.quote(text or "", safe=""))


@register("url-decoder")
def url_decoder(files, text: str, options: dict) -> ToolResult:
    return ToolResult(text=urllib.parse.unquote(text or ""))


@register("lorem-ipsum-generator")
def lorem_ipsum_generator(files, text: str, options: dict) -> ToolResult:
    count = int(options.get("paragraphs", 3) or 3)
    count = max(1, min(count, 50))
    return ToolResult(text="\n\n".join([_LOREM] * count))


@register("random-text-generator")
def random_text_generator(files, text: str, options: dict) -> ToolResult:
    import secrets
    import string

    length = max(1, min(int(options.get("length", 32) or 32), 2000))
    alphabet = string.ascii_letters + string.digits
    out = "".join(secrets.choice(alphabet) for _ in range(length))
    return ToolResult(text=out)


# ===========================================================================
# Analysis
# ===========================================================================

def _int(options: dict, key: str, default: int) -> int:
    """An option read as a whole number, tolerating a blank or a bad value.

    Options arrive as JSON from the browser, so a number field can turn up as
    "", "3" or 3 — none of which int() handles the same way.
    """
    try:
        return int(float(str(options.get(key, default)).strip() or default))
    except (TypeError, ValueError):
        return default


def _flag(options: dict, key: str, default: bool = False) -> bool:
    value = options.get(key, default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


_VOWELS = "aeiouy"


def _syllables(word: str) -> int:
    """Rough syllable count — enough for readability scores, not for a dictionary."""
    word = word.lower().strip("'\".,;:!?()[]")
    if not word:
        return 0
    count, prev_vowel = 0, False
    for ch in word:
        is_vowel = ch in _VOWELS
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text or "")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


@register("sentence-paragraph-counter")
def sentence_paragraph_counter(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    sentences = _sentences(text)
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    words = _words(text)
    return ToolResult(meta={
        "sentences": len(sentences),
        "paragraphs": len(paragraphs),
        "words": len(words),
        "words_per_sentence": round(len(words) / len(sentences), 1) if sentences else 0,
        "sentences_per_paragraph": round(len(sentences) / len(paragraphs), 1) if paragraphs else 0,
        "longest_sentence_words": max((len(_words(s)) for s in sentences), default=0),
    })


@register("line-counter")
def line_counter(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    lines = text.split("\n")
    non_empty = [ln for ln in lines if ln.strip()]
    return ToolResult(meta={
        "lines": len(lines) if text else 0,
        "non_empty_lines": len(non_empty),
        "empty_lines": len(lines) - len(non_empty) if text else 0,
        "unique_lines": len({ln.strip() for ln in non_empty}),
        "longest_line_characters": max((len(ln) for ln in lines), default=0),
    })


@register("keyword-density-checker")
def keyword_density_checker(files, text: str, options: dict) -> ToolResult:
    """Which words carry the page, as a percentage of the total."""
    from collections import Counter

    # Stop words are excluded, otherwise "the" tops every result and the tool
    # tells you nothing about the subject.
    stop = {
        "the","a","an","and","or","but","if","of","to","in","on","for","with","at","by",
        "from","as","is","are","was","were","be","been","being","it","its","this","that",
        "these","those","i","you","he","she","we","they","them","his","her","their","our",
        "your","my","me","us","do","does","did","have","has","had","not","no","so","than",
        "then","there","here","what","which","who","when","where","how","all","any","can",
        "will","would","should","could","about","into","over","after","before","up","out",
    }
    min_len = max(1, int(_int(options, "min_length", 3)))
    top = max(1, min(int(_int(options, "top", 20)), 100))
    words = [w.lower() for w in _words(text) if len(w) >= min_len and w.lower() not in stop]
    if not words:
        return ToolResult(meta={"error": "Paste some text to analyse."})
    counts = Counter(words)
    total = len(words)
    return ToolResult(meta={
        "total_counted_words": total,
        "unique_words": len(counts),
        "keywords": [
            {"word": w, "count": n, "density_percent": round(n / total * 100, 2)}
            for w, n in counts.most_common(top)
        ],
    })


@register("readability-checker")
def readability_checker(files, text: str, options: dict) -> ToolResult:
    """Flesch Reading Ease and the grade-level scores that go with it."""
    words = _words(text)
    sentences = _sentences(text)
    if len(words) < 10 or not sentences:
        return ToolResult(meta={"error": "Paste at least a couple of sentences to score."})
    syllables = sum(_syllables(w) for w in words)
    wps = len(words) / len(sentences)
    spw = syllables / len(words)
    flesch = 206.835 - 1.015 * wps - 84.6 * spw
    fk_grade = 0.39 * wps + 11.8 * spw - 15.59
    complex_words = sum(1 for w in words if _syllables(w) >= 3)
    gunning_fog = 0.4 * (wps + 100 * complex_words / len(words))
    if flesch >= 90:
        level = "Very easy — 5th grade"
    elif flesch >= 70:
        level = "Easy — 6th to 7th grade"
    elif flesch >= 60:
        level = "Plain English — 8th to 9th grade"
    elif flesch >= 50:
        level = "Fairly difficult — 10th to 12th grade"
    elif flesch >= 30:
        level = "Difficult — college"
    else:
        level = "Very difficult — university graduate"
    return ToolResult(meta={
        "flesch_reading_ease": round(flesch, 1),
        "reading_level": level,
        "flesch_kincaid_grade": round(fk_grade, 1),
        "gunning_fog_index": round(gunning_fog, 1),
        "words": len(words),
        "sentences": len(sentences),
        "average_words_per_sentence": round(wps, 1),
        "complex_words": complex_words,
    })


@register("text-analyzer")
def text_analyzer(files, text: str, options: dict) -> ToolResult:
    """Everything the individual counters report, in one pass."""
    from collections import Counter

    text = text or ""
    words = _words(text)
    sentences = _sentences(text)
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    letters = sum(1 for c in text if c.isalpha())
    digits = sum(1 for c in text if c.isdigit())
    lower = [w.lower() for w in words]
    return ToolResult(meta={
        "characters": len(text),
        "characters_no_spaces": len(re.sub(r"\s", "", text)),
        "letters": letters,
        "digits": digits,
        "words": len(words),
        "unique_words": len(set(lower)),
        "sentences": len(sentences),
        "paragraphs": len(paragraphs),
        "lines": len(text.split("\n")) if text else 0,
        "average_word_length": round(sum(len(w) for w in words) / len(words), 2) if words else 0,
        "average_words_per_sentence": round(len(words) / len(sentences), 1) if sentences else 0,
        "reading_time_minutes": round(len(words) / 200, 1),
        "speaking_time_minutes": round(len(words) / 130, 1),
        "most_common": [{"word": w, "count": n} for w, n in Counter(lower).most_common(5)],
    })


@register("headline-analyzer")
def headline_analyzer(files, text: str, options: dict) -> ToolResult:
    """Scores a headline on the things that actually move click-through."""
    headline = (text or "").strip().split("\n")[0]
    if not headline:
        return ToolResult(meta={"error": "Type a headline to analyse."})
    words = _words(headline)
    power = {"free","best","proven","easy","fast","simple","ultimate","complete","essential",
             "guide","how","why","new","secret","instant","top","step","tips","without"}
    emotional = {"amazing","surprising","shocking","stunning","incredible","powerful",
                 "effortless","painless","brilliant","remarkable"}
    lower = {w.lower() for w in words}
    score = 50
    if 6 <= len(words) <= 12:
        score += 15
    if 40 <= len(headline) <= 60:
        score += 15
    if any(c.isdigit() for c in headline):
        score += 10
    hits_power = sorted(lower & power)
    hits_emotion = sorted(lower & emotional)
    score += min(10, 5 * len(hits_power)) + min(10, 5 * len(hits_emotion))
    notes = []
    if len(headline) > 60:
        notes.append("Over 60 characters — Google usually truncates the title here.")
    if len(headline) < 30:
        notes.append("Under 30 characters — there is room to say more.")
    if not any(c.isdigit() for c in headline):
        notes.append("No number. Headlines with a number tend to get more clicks.")
    if not hits_power:
        notes.append("No power word (free, proven, easy, guide…).")
    if headline.isupper():
        notes.append("ALL CAPS reads as shouting and hurts trust.")
    return ToolResult(meta={
        "headline": headline,
        "score_out_of_100": min(100, score),
        "characters": len(headline),
        "words": len(words),
        "power_words": hits_power,
        "emotional_words": hits_emotion,
        "suggestions": notes or ["Looks good — nothing obvious to fix."],
    })


@register("text-summarizer")
def text_summarizer(files, text: str, options: dict) -> ToolResult:
    """Extractive summary: keeps the highest-scoring original sentences.

    Deliberately extractive, not generative. Nothing is invented and no model or
    external service is involved — every sentence returned appears verbatim in
    the input, so the summary cannot say something the source did not.
    """
    from collections import Counter

    sentences = _sentences(text)
    if len(sentences) < 3:
        return ToolResult(meta={"error": "Paste at least three sentences to summarise."})
    want = max(1, min(int(_int(options, "sentences", 3)), len(sentences)))
    stop = {"the","a","an","and","or","of","to","in","on","for","with","is","are","was",
            "were","be","it","this","that","as","at","by","from","but","not","have","has"}
    freq = Counter(w.lower() for w in _words(text) if w.lower() not in stop and len(w) > 2)
    if not freq:
        return ToolResult(meta={"error": "Not enough distinct words to summarise."})
    peak = max(freq.values())
    scored = []
    for i, s in enumerate(sentences):
        ws = [w.lower() for w in _words(s)]
        if not ws:
            continue
        # Divided by length so a long sentence doesn't win on word count alone.
        score = sum(freq.get(w, 0) / peak for w in ws) / len(ws)
        scored.append((score, i, s))
    picked = sorted(sorted(scored, reverse=True)[:want], key=lambda t: t[1])
    summary = " ".join(s for _, _, s in picked)
    return ToolResult(text=summary, meta={
        "original_sentences": len(sentences),
        "summary_sentences": len(picked),
        "original_words": len(_words(text)),
        "summary_words": len(_words(summary)),
        "reduction_percent": round(100 - len(_words(summary)) / max(1, len(_words(text))) * 100, 1),
    })


@register("style-checker")
def style_checker(files, text: str, options: dict) -> ToolResult:
    """Rule-based writing checks.

    Not a grammar checker: it flags mechanical problems a rule can be sure of —
    doubled words, spacing around punctuation, sentences that run long — and
    stays quiet about anything that needs a language model to judge.
    """
    text = text or ""
    if not text.strip():
        return ToolResult(meta={"error": "Paste some text to check."})
    issues = []
    for m in re.finditer(r"\b(\w+)\s+\1\b", text, re.IGNORECASE):
        issues.append({"type": "repeated word", "found": m.group(0), "at": m.start()})
    for m in re.finditer(r"  +", text):
        issues.append({"type": "double space", "found": "(spaces)", "at": m.start()})
    for m in re.finditer(r"[,.;:!?](?=[A-Za-z])", text):
        issues.append({"type": "missing space after punctuation", "found": m.group(0), "at": m.start()})
    for m in re.finditer(r"\s+[,.;:!?]", text):
        issues.append({"type": "space before punctuation", "found": m.group(0).strip(), "at": m.start()})
    long_sentences = [s for s in _sentences(text) if len(_words(s)) > 30]
    for s in long_sentences[:20]:
        issues.append({"type": "long sentence", "found": s[:60] + "…", "at": text.find(s)})
    if text.count('"') % 2:
        issues.append({"type": "unbalanced quotes", "found": '"', "at": -1})
    if text.count("(") != text.count(")"):
        issues.append({"type": "unbalanced brackets", "found": "()", "at": -1})
    return ToolResult(meta={
        "issues_found": len(issues),
        "issues": issues[:100],
        "long_sentences": len(long_sentences),
        "note": "Mechanical checks only — spelling and grammar are not judged here.",
    })


@register("palindrome-checker")
def palindrome_checker(files, text: str, options: dict) -> ToolResult:
    raw = (text or "").strip()
    if not raw:
        return ToolResult(meta={"error": "Type a word or phrase to check."})
    cleaned = re.sub(r"[^a-z0-9]", "", raw.lower())
    return ToolResult(meta={
        "input": raw,
        "is_palindrome": bool(cleaned) and cleaned == cleaned[::-1],
        "compared": cleaned,
        "reversed": cleaned[::-1],
        "note": "Spaces, case and punctuation are ignored.",
    })


# ===========================================================================
# Case
# ===========================================================================

@register("uppercase-converter")
def uppercase_converter(files, text: str, options: dict) -> ToolResult:
    return ToolResult(text=(text or "").upper())


@register("lowercase-converter")
def lowercase_converter(files, text: str, options: dict) -> ToolResult:
    return ToolResult(text=(text or "").lower())


@register("capitalize-each-word")
def capitalize_each_word(files, text: str, options: dict) -> ToolResult:
    """Capitalize the first letter of each word, leaving the rest untouched.

    str.title() lowercases everything after the first letter, so "USA" comes back
    as "Usa" and "McDonald" as "Mcdonald". Only the first letter is changed here,
    which keeps acronyms and internal capitals intact.
    """
    out = re.sub(r"\b[a-zA-Z]", lambda m: m.group(0).upper(), text or "")
    return ToolResult(text=out)


# ===========================================================================
# Whitespace and lines
# ===========================================================================

@register("remove-extra-spaces")
def remove_extra_spaces(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    out = "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n"))
    return ToolResult(text=out, meta={"characters_removed": len(text) - len(out)})


@register("trim-whitespace")
def trim_whitespace(files, text: str, options: dict) -> ToolResult:
    where = str(options.get("where", "both"))
    lines = (text or "").split("\n")
    if where == "start":
        out = [ln.lstrip() for ln in lines]
    elif where == "end":
        out = [ln.rstrip() for ln in lines]
    else:
        out = [ln.strip() for ln in lines]
    return ToolResult(text="\n".join(out))


@register("remove-line-breaks")
def remove_line_breaks(files, text: str, options: dict) -> ToolResult:
    text = (text or "").replace("\r\n", "\n")
    joiner = " " if _flag(options, "add_space", True) else ""
    if _flag(options, "keep_paragraphs", True):
        # Blank lines separate paragraphs, so only breaks *inside* a paragraph go.
        paras = [joiner.join(ln.strip() for ln in p.split("\n") if ln.strip())
                 for p in re.split(r"\n\s*\n", text)]
        out = "\n\n".join(p for p in paras if p)
    else:
        out = joiner.join(ln.strip() for ln in text.split("\n") if ln.strip())
    return ToolResult(text=out)


@register("add-line-breaks")
def add_line_breaks(files, text: str, options: dict) -> ToolResult:
    """Wrap text to a width, or break it after a chosen character."""
    text = text or ""
    mode = str(options.get("mode", "width"))
    if mode == "after":
        marker = str(options.get("after", ".")) or "."
        out = text.replace(marker, marker + "\n")
    else:
        import textwrap

        width = max(10, _int(options, "width", 80))
        out = "\n".join(
            "\n".join(textwrap.wrap(p, width)) or ""
            for p in text.split("\n")
        )
    return ToolResult(text=out)


@register("remove-empty-lines")
def remove_empty_lines(files, text: str, options: dict) -> ToolResult:
    lines = (text or "").split("\n")
    kept = [ln for ln in lines if ln.strip()]
    return ToolResult(text="\n".join(kept),
                      meta={"lines_removed": len(lines) - len(kept)})


@register("remove-specific-characters")
def remove_specific_characters(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    chars = str(options.get("characters", ""))
    out = text
    if chars:
        out = out.translate({ord(c): None for c in chars})
    if _flag(options, "remove_punctuation"):
        out = re.sub(r"[^\w\s]", "", out)
    if _flag(options, "remove_digits"):
        out = re.sub(r"\d", "", out)
    if not chars and not _flag(options, "remove_punctuation") and not _flag(options, "remove_digits"):
        return ToolResult(meta={"error": "Enter the characters to remove, or tick one of the boxes."})
    return ToolResult(text=out, meta={"characters_removed": len(text) - len(out)})


@register("text-cleaner")
def text_cleaner(files, text: str, options: dict) -> ToolResult:
    """Every tidy-up in one pass, in the order that avoids undoing itself."""
    text = text or ""
    original = len(text)
    if _flag(options, "fix_smart_quotes", True):
        text = (text.replace("‘", "'").replace("’", "'")
                    .replace("“", '"').replace("”", '"')
                    .replace("–", "-").replace("—", "-")
                    .replace("…", "..."))
    if _flag(options, "strip_html"):
        text = re.sub(r"<[^>]+>", "", text)
    if _flag(options, "remove_urls"):
        text = re.sub(r"https?://\S+|www\.\S+", "", text)
    if _flag(options, "remove_punctuation"):
        text = re.sub(r"[^\w\s]", "", text)
    if _flag(options, "remove_numbers"):
        text = re.sub(r"\d+", "", text)
    if _flag(options, "single_spaces", True):
        text = "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n"))
    if _flag(options, "remove_empty_lines", True):
        text = "\n".join(ln for ln in text.split("\n") if ln.strip())
    return ToolResult(text=text.strip(),
                      meta={"characters_before": original, "characters_after": len(text.strip())})


@register("find-and-replace")
def find_and_replace(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    find = str(options.get("find", ""))
    replace = str(options.get("replace", ""))
    if not find:
        return ToolResult(meta={"error": "Enter the text to find."})
    if _flag(options, "regex"):
        # A visitor-supplied pattern, so it goes through the same guard as the
        # Regex Tester — (a+)+ here would hang the server just as readily.
        from app.core.regex_guard import UnsafePattern, compile_pattern, substitute

        flags = 0 if _flag(options, "case_sensitive", True) else re.IGNORECASE
        try:
            pattern = compile_pattern(find, flags)
            out, count = substitute(pattern, replace, text)
        except UnsafePattern as exc:
            return ToolResult(meta={"error": str(exc)})
    elif _flag(options, "case_sensitive", True):
        count = text.count(find)
        out = text.replace(find, replace)
    else:
        pattern = re.compile(re.escape(find), re.IGNORECASE)
        out, count = pattern.subn(replace, text)
    return ToolResult(text=out, meta={"replacements": count})


@register("shuffle-lines")
def shuffle_lines(files, text: str, options: dict) -> ToolResult:
    import random

    lines = [ln for ln in (text or "").split("\n") if ln.strip()]
    if not lines:
        return ToolResult(meta={"error": "Paste some lines to shuffle."})
    random.shuffle(lines)
    return ToolResult(text="\n".join(lines), meta={"lines": len(lines)})


@register("add-prefix-suffix")
def add_prefix_suffix(files, text: str, options: dict) -> ToolResult:
    prefix = str(options.get("prefix", ""))
    suffix = str(options.get("suffix", ""))
    lines = (text or "").split("\n")
    out = [
        f"{prefix}{ln}{suffix}" if ln.strip() or not _flag(options, "skip_empty", True) else ln
        for ln in lines
    ]
    return ToolResult(text="\n".join(out), meta={"lines": len(lines)})


@register("add-line-numbers")
def add_line_numbers(files, text: str, options: dict) -> ToolResult:
    lines = (text or "").split("\n")
    start = _int(options, "start", 1)
    sep = str(options.get("separator", ". ")) or ". "
    if _flag(options, "pad", True):
        width = len(str(start + len(lines) - 1))
        out = [f"{str(start + i).rjust(width)}{sep}{ln}" for i, ln in enumerate(lines)]
    else:
        out = [f"{start + i}{sep}{ln}" for i, ln in enumerate(lines)]
    return ToolResult(text="\n".join(out), meta={"lines": len(lines)})


@register("text-repeater")
def text_repeater(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    if not text:
        return ToolResult(meta={"error": "Paste the text to repeat."})
    # Capped: the result is held in memory and sent over the wire, so an
    # unbounded count is a way to knock the server over rather than a feature.
    times = max(1, min(_int(options, "times", 5), 10000))
    sep = {"newline": "\n", "space": " ", "comma": ", ", "none": ""}.get(
        str(options.get("separator", "newline")), "\n")
    out = sep.join([text] * times)
    if len(out) > 2_000_000:
        return ToolResult(meta={"error": "That would produce more than 2 MB of text. Lower the count."})
    return ToolResult(text=out, meta={"repetitions": times, "characters": len(out)})


@register("column-extractor")
def column_extractor(files, text: str, options: dict) -> ToolResult:
    """Pull one column out of delimited lines (CSV, TSV, pipe-separated…)."""
    delim = {"comma": ",", "tab": "\t", "pipe": "|", "semicolon": ";", "space": " "}.get(
        str(options.get("delimiter", "comma")), ",")
    index = _int(options, "column", 1)
    lines = [ln for ln in (text or "").split("\n") if ln.strip()]
    if not lines:
        return ToolResult(meta={"error": "Paste some delimited lines."})
    if index < 1:
        return ToolResult(meta={"error": "Columns are numbered from 1."})
    out, missing = [], 0
    for ln in lines:
        parts = ln.split(delim)
        if len(parts) >= index:
            out.append(parts[index - 1].strip())
        else:
            missing += 1
    return ToolResult(text="\n".join(out), meta={
        "rows": len(lines), "extracted": len(out), "rows_without_that_column": missing,
    })


@register("single-line-converter")
def single_line_converter(files, text: str, options: dict) -> ToolResult:
    """Collapse text to one line, or split one line back out."""
    text = text or ""
    mode = str(options.get("mode", "to_single"))
    sep = str(options.get("separator", " ")) or " "
    if mode == "to_single":
        out = sep.join(ln.strip() for ln in text.split("\n") if ln.strip())
    else:
        out = "\n".join(part.strip() for part in text.split(sep) if part.strip())
    return ToolResult(text=out)


@register("text-diff")
def text_diff(files, text: str, options: dict) -> ToolResult:
    """Line-by-line comparison of two texts."""
    import difflib

    other = str(options.get("compare_with", ""))
    if not (text or "").strip() or not other.strip():
        return ToolResult(meta={"error": "Paste text in both boxes to compare them."})
    a = (text or "").splitlines()
    b = other.splitlines()
    if _flag(options, "ignore_case"):
        a, b = [x.lower() for x in a], [x.lower() for x in b]
    if _flag(options, "ignore_whitespace"):
        a, b = [x.strip() for x in a], [x.strip() for x in b]
    diff = list(difflib.unified_diff(a, b, lineterm="", n=_int(options, "context", 2)))
    added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
    ratio = difflib.SequenceMatcher(None, "\n".join(a), "\n".join(b)).ratio()
    return ToolResult(text="\n".join(diff) or "The two texts are identical.", meta={
        "identical": a == b,
        "lines_added": added,
        "lines_removed": removed,
        "similarity_percent": round(ratio * 100, 1),
    })


@register("common-unique-lines")
def common_unique_lines(files, text: str, options: dict) -> ToolResult:
    """Set operations on two lists of lines."""
    other = str(options.get("compare_with", ""))
    if not (text or "").strip() or not other.strip():
        return ToolResult(meta={"error": "Paste a list in both boxes."})
    norm = (lambda s: s.strip().lower()) if not _flag(options, "case_sensitive") else (lambda s: s.strip())
    a = [ln for ln in (text or "").split("\n") if ln.strip()]
    b = [ln for ln in other.split("\n") if ln.strip()]
    sa, sb = {norm(x) for x in a}, {norm(x) for x in b}
    mode = str(options.get("mode", "common"))
    if mode == "common":
        keep = sa & sb
    elif mode == "only_first":
        keep = sa - sb
    elif mode == "only_second":
        keep = sb - sa
    else:
        keep = sa ^ sb
    # Return the original casing rather than the normalized key.
    source = a + b
    seen, out = set(), []
    for line in source:
        k = norm(line)
        if k in keep and k not in seen:
            seen.add(k)
            out.append(line.strip())
    return ToolResult(text="\n".join(out), meta={
        "first_list": len(sa), "second_list": len(sb), "result_lines": len(out),
    })


# ===========================================================================
# Encoding and conversion
# ===========================================================================

@register("base64-text")
def base64_text(files, text: str, options: dict) -> ToolResult:
    import base64
    import binascii

    text = text or ""
    if not text.strip():
        return ToolResult(meta={"error": "Paste some text."})
    if str(options.get("mode", "encode")) == "encode":
        out = base64.b64encode(text.encode("utf-8")).decode("ascii")
        if _flag(options, "url_safe"):
            out = base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")
        return ToolResult(text=out, meta={"mode": "encode"})
    try:
        raw = text.strip().replace("-", "+").replace("_", "/")
        # Base64 needs its length to be a multiple of 4; pasted strings often
        # have the "=" padding stripped, so put it back before decoding.
        raw += "=" * (-len(raw) % 4)
        return ToolResult(text=base64.b64decode(raw).decode("utf-8"), meta={"mode": "decode"})
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return ToolResult(meta={"error": "That isn't valid Base64 text."})


@register("html-entity-converter")
def html_entity_converter(files, text: str, options: dict) -> ToolResult:
    import html

    text = text or ""
    if str(options.get("mode", "encode")) == "encode":
        # quote=True also escapes " and ', so the result is safe inside an
        # attribute as well as in element text.
        return ToolResult(text=html.escape(text, quote=True))
    return ToolResult(text=html.unescape(text))


@register("unicode-converter")
def unicode_converter(files, text: str, options: dict) -> ToolResult:
    """Between readable text and \\uXXXX escapes, or raw UTF-8 bytes."""
    text = text or ""
    if not text:
        return ToolResult(meta={"error": "Paste some text."})
    mode = str(options.get("mode", "to_escapes"))
    try:
        if mode == "to_escapes":
            out = "".join(ch if ch.isascii() and ch.isprintable() else f"\\u{ord(ch):04x}" for ch in text)
        elif mode == "from_escapes":
            out = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
        elif mode == "to_bytes":
            out = " ".join(f"{b:02x}" for b in text.encode("utf-8"))
        else:
            out = bytes(int(p, 16) for p in text.split()).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ToolResult(meta={"error": "That input doesn't match the chosen direction."})
    return ToolResult(text=out, meta={"code_points": len(text)})


def _text_radix(text: str, options: dict, base: int, width: int) -> ToolResult:
    """Shared body for the binary / hex / octal text converters."""
    text = text or ""
    if not text.strip():
        return ToolResult(meta={"error": "Paste some text."})
    if str(options.get("mode", "encode")) == "encode":
        fmt = {2: "b", 8: "o", 16: "x"}[base]
        out = " ".join(format(b, f"0{width}{fmt}") for b in text.encode("utf-8"))
        return ToolResult(text=out)
    try:
        # Accept the values however they were pasted — spaced, comma-separated,
        # or (for fixed-width binary and hex) run together with no separator.
        parts = re.split(r"[\s,]+", text.strip())
        if len(parts) == 1 and base in (2, 16) and len(parts[0]) % width == 0:
            parts = [parts[0][i:i + width] for i in range(0, len(parts[0]), width)]
        return ToolResult(text=bytes(int(p, base) for p in parts if p).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return ToolResult(meta={"error": "That isn't a valid sequence for this base."})


@register("binary-text-converter")
def binary_text_converter(files, text: str, options: dict) -> ToolResult:
    return _text_radix(text, options, 2, 8)


@register("hex-text-converter")
def hex_text_converter(files, text: str, options: dict) -> ToolResult:
    return _text_radix(text, options, 16, 2)


@register("ascii-octal-converter")
def ascii_octal_converter(files, text: str, options: dict) -> ToolResult:
    base = 10 if str(options.get("base", "decimal")) == "decimal" else 8
    text = text or ""
    if not text.strip():
        return ToolResult(meta={"error": "Paste some text."})
    if str(options.get("mode", "encode")) == "encode":
        codes = [format(b, "03o") if base == 8 else str(b) for b in text.encode("utf-8")]
        return ToolResult(text=" ".join(codes))
    try:
        parts = re.split(r"[\s,]+", text.strip())
        return ToolResult(text=bytes(int(p, base) for p in parts if p).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return ToolResult(meta={"error": "That isn't a valid sequence of character codes."})


@register("caesar-cipher")
def caesar_cipher(files, text: str, options: dict) -> ToolResult:
    """ROT13 by default; any shift from 1 to 25.

    A classic cipher with no key management — it obscures text, it does not
    secure it. Never use it for anything that matters.
    """
    shift = _int(options, "shift", 13) % 26
    if str(options.get("mode", "encode")) == "decode":
        shift = -shift
    def rot(m: re.Match) -> str:
        ch = m.group(0)
        base = ord("A") if ch.isupper() else ord("a")
        return chr((ord(ch) - base + shift) % 26 + base)
    return ToolResult(text=re.sub(r"[A-Za-z]", rot, text or ""),
                      meta={"shift": shift % 26, "note": "Obscures text; it is not encryption."})


_MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.",
    "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.",
    "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-", "U": "..-",
    "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....",
    "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.", "!": "-.-.--",
    "/": "-..-.", "(": "-.--.", ")": "-.--.-", "&": ".-...", ":": "---...",
    ";": "-.-.-.", "=": "-...-", "+": ".-.-.", "-": "-....-", "_": "..--.-",
    '"': ".-..-.", "$": "...-..-", "@": ".--.-.",
}
_MORSE_REVERSE = {v: k for k, v in _MORSE.items()}


@register("morse-code-translator")
def morse_code_translator(files, text: str, options: dict) -> ToolResult:
    text = (text or "").strip()
    if not text:
        return ToolResult(meta={"error": "Type something to translate."})
    if str(options.get("mode", "encode")) == "encode":
        out, unknown = [], set()
        for ch in text.upper():
            if ch == " ":
                out.append("/")
            elif ch in _MORSE:
                out.append(_MORSE[ch])
            elif not ch.isspace():
                unknown.add(ch)
        meta = {"unsupported_characters": sorted(unknown)} if unknown else {}
        return ToolResult(text=" ".join(out), meta=meta)
    words = re.split(r"\s*/\s*|\s{3,}", text)
    decoded = " ".join(
        "".join(_MORSE_REVERSE.get(sym, "?") for sym in word.split())
        for word in words
    )
    return ToolResult(text=decoded,
                      meta={"note": "? marks a code with no letter."} if "?" in decoded else {})


_ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
         "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_SCALES = ["", " thousand", " million", " billion", " trillion", " quadrillion"]


def _under_thousand(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("-" + _ONES[n % 10] if n % 10 else "")
    return _ONES[n // 100] + " hundred" + (" and " + _under_thousand(n % 100) if n % 100 else "")


def _spell(n: int) -> str:
    if n == 0:
        return "zero"
    parts, group = [], 0
    while n:
        n, chunk = divmod(n, 1000)
        if chunk:
            parts.append(_under_thousand(chunk) + _SCALES[group])
        group += 1
    return ", ".join(reversed(parts))


@register("number-to-words")
def number_to_words(files, text: str, options: dict) -> ToolResult:
    raw = (text or "").strip().replace(",", "")
    if not raw:
        return ToolResult(meta={"error": "Type a number."})
    try:
        value = float(raw)
    except ValueError:
        return ToolResult(meta={"error": "That isn't a number."})
    if abs(value) >= 10 ** 18:
        return ToolResult(meta={"error": "That number is too large to spell out."})
    sign = "negative " if value < 0 else ""
    whole = int(abs(value))
    words = sign + _spell(whole)
    fraction = round(abs(value) - whole, 6)
    if fraction:
        digits = str(fraction).split(".")[1]
        words += " point " + " ".join(_ONES[int(d)] if d != "0" else "zero" for d in digits)
    return ToolResult(text=words, meta={"number": value, "capitalised": words.capitalize()})


_WORD_VALUES = {w: i for i, w in enumerate(_ONES) if w}
_WORD_VALUES.update({w: i * 10 for i, w in enumerate(_TENS) if w})


@register("words-to-number")
def words_to_number(files, text: str, options: dict) -> ToolResult:
    raw = re.sub(r"[^a-z\s-]", " ", (text or "").lower())
    tokens = [t for t in re.split(r"[\s-]+", raw) if t and t != "and"]
    if not tokens:
        return ToolResult(meta={"error": "Type a number in words, e.g. two hundred and five."})
    negative = tokens[0] in {"negative", "minus"}
    if negative:
        tokens = tokens[1:]
    scales = {"hundred": 100, "thousand": 1000, "million": 10 ** 6,
              "billion": 10 ** 9, "trillion": 10 ** 12}
    total = current = 0
    for token in tokens:
        if token in _WORD_VALUES:
            current += _WORD_VALUES[token]
        elif token == "hundred":
            current = max(1, current) * 100
        elif token in scales:
            total += max(1, current) * scales[token]
            current = 0
        elif token == "zero":
            continue
        else:
            return ToolResult(meta={"error": f"Not a number word: {token!r}"})
    result = total + current
    return ToolResult(text=str(-result if negative else result),
                      meta={"number": -result if negative else result})


_ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


@register("roman-numeral-converter")
def roman_numeral_converter(files, text: str, options: dict) -> ToolResult:
    raw = (text or "").strip()
    if not raw:
        return ToolResult(meta={"error": "Type a number or a Roman numeral."})
    if raw.isdigit():
        n = int(raw)
        if not 1 <= n <= 3999:
            return ToolResult(meta={"error": "Roman numerals cover 1 to 3999."})
        out = ""
        for value, sym in _ROMAN:
            count, n = divmod(n, value)
            out += sym * count
        return ToolResult(text=out, meta={"number": int(raw), "roman": out})
    upper = raw.upper()
    if not re.fullmatch(r"[MDCLXVI]+", upper):
        return ToolResult(meta={"error": "That is neither a number nor a Roman numeral."})
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for i, ch in enumerate(upper):
        # Subtractive pairs: a smaller symbol before a larger one is subtracted.
        if i + 1 < len(upper) and values[ch] < values[upper[i + 1]]:
            total -= values[ch]
        else:
            total += values[ch]
    # Round-trip check catches invalid strings like "IIII" or "VX" that the
    # character test above lets through.
    check, n = "", total
    for value, sym in _ROMAN:
        count, n = divmod(n, value)
        check += sym * count
    if check != upper:
        return ToolResult(meta={"error": f"That isn't a valid numeral. Did you mean {check}?"})
    return ToolResult(text=str(total), meta={"roman": upper, "number": total})


# ===========================================================================
# Extractors
# ===========================================================================

def _dedupe(items: list[str], keep_order: bool = True) -> list[str]:
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out if keep_order else sorted(seen)


@register("email-extractor")
def email_extractor(files, text: str, options: dict) -> ToolResult:
    found = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
    if _flag(options, "lowercase", True):
        found = [e.lower() for e in found]
    unique = _dedupe(found) if _flag(options, "unique", True) else found
    if _flag(options, "sort"):
        unique = sorted(unique)
    sep = "\n" if str(options.get("separator", "newline")) == "newline" else ", "
    return ToolResult(text=sep.join(unique),
                      meta={"found": len(found), "unique": len(set(found))})


@register("url-extractor")
def url_extractor(files, text: str, options: dict) -> ToolResult:
    # Trailing punctuation is stripped, since a URL at the end of a sentence
    # otherwise swallows the full stop.
    raw = re.findall(r"(?:https?://|www\.)[^\s<>\"')\]]+", text or "")
    found = [u.rstrip(".,;:!?") for u in raw]
    if _flag(options, "domains_only"):
        found = [re.sub(r"^https?://", "", u).split("/")[0] for u in found]
    unique = _dedupe(found) if _flag(options, "unique", True) else found
    return ToolResult(text="\n".join(unique),
                      meta={"found": len(found), "unique": len(set(found))})


@register("phone-extractor")
def phone_extractor(files, text: str, options: dict) -> ToolResult:
    """Finds phone-shaped runs of digits.

    Deliberately loose: numbering plans differ by country, so this matches the
    common shapes and leaves it to you to check the results.
    """
    pattern = r"\+?\d[\d\s().-]{6,18}\d"
    found = [re.sub(r"\s{2,}", " ", m.strip()) for m in re.findall(pattern, text or "")]
    if _flag(options, "digits_only"):
        found = [re.sub(r"[^\d+]", "", f) for f in found]
    unique = _dedupe(found) if _flag(options, "unique", True) else found
    return ToolResult(text="\n".join(unique), meta={"found": len(found), "unique": len(set(found))})


@register("number-extractor")
def number_extractor(files, text: str, options: dict) -> ToolResult:
    pattern = r"-?\d+(?:\.\d+)?" if _flag(options, "include_decimals", True) else r"-?\d+"
    found = re.findall(pattern, text or "")
    if _flag(options, "unique"):
        found = _dedupe(found)
    if _flag(options, "sort"):
        found.sort(key=float)
    numbers = [float(n) for n in found]
    sep = "\n" if str(options.get("separator", "newline")) == "newline" else ", "
    return ToolResult(text=sep.join(found), meta={
        "count": len(found),
        "sum": round(sum(numbers), 6) if numbers else 0,
        "smallest": min(numbers) if numbers else None,
        "largest": max(numbers) if numbers else None,
    })


@register("delimiter-extractor")
def delimiter_extractor(files, text: str, options: dict) -> ToolResult:
    """Everything sitting between two markers — quotes, brackets, custom tags."""
    start = str(options.get("start", "["))
    end = str(options.get("end", "]"))
    if not start or not end:
        return ToolResult(meta={"error": "Enter both the opening and closing marker."})
    pattern = re.escape(start) + ("(.*?)" if not _flag(options, "greedy") else "(.*)") + re.escape(end)
    flags = re.DOTALL if _flag(options, "across_lines") else 0
    found = re.findall(pattern, text or "", flags)
    if _flag(options, "include_markers"):
        found = [f"{start}{f}{end}" for f in found]
    if _flag(options, "unique"):
        found = _dedupe(found)
    return ToolResult(text="\n".join(found), meta={"matches": len(found)})


# ===========================================================================
# Generators
# ===========================================================================

@register("random-string-generator")
def random_string_generator(files, text: str, options: dict) -> ToolResult:
    """Random strings with control over which characters can appear.

    Uses `secrets`, not `random`: these are routinely used as passwords and API
    keys, and `random` is predictable from a handful of prior outputs.
    """
    import secrets
    import string

    length = max(1, min(_int(options, "length", 16), 512))
    count = max(1, min(_int(options, "count", 5), 200))
    alphabet = ""
    if _flag(options, "lowercase", True):
        alphabet += string.ascii_lowercase
    if _flag(options, "uppercase", True):
        alphabet += string.ascii_uppercase
    if _flag(options, "digits", True):
        alphabet += string.digits
    if _flag(options, "symbols"):
        alphabet += "!@#$%^&*()-_=+[]{};:,.?"
    if _flag(options, "exclude_ambiguous"):
        # 0/O and 1/l/I are the pairs people mistype when reading a code aloud.
        alphabet = "".join(c for c in alphabet if c not in "0OoIl1")
    if not alphabet:
        return ToolResult(meta={"error": "Turn on at least one character set."})
    out = ["".join(secrets.choice(alphabet) for _ in range(length)) for _ in range(count)]
    return ToolResult(text="\n".join(out),
                      meta={"length": length, "count": count, "alphabet_size": len(alphabet)})


_WORD_BANK = (
    "amber anchor aurora badge bamboo beacon birch bloom breeze bridge bronze brook cactus "
    "canyon cedar chorus cinder cobalt comet copper coral crest cypress dawn delta dusk ember "
    "falcon fern flint forest fossil garnet glacier granite grove harbor haven hazel heron "
    "indigo ivory jade jasper juniper kettle lagoon lantern larch laurel ledge lily lotus "
    "lumen maple marble meadow mesa mist moss nectar nimbus north oak onyx opal orchard otter "
    "pebble pepper pilot pine plume pollen prairie quartz quill raven reef ridge river rowan "
    "saffron sage sandal shale shore silver slate solstice spruce summit thistle thorn tide "
    "timber topaz tundra umber valley velvet vertex willow winter zephyr"
).split()

_NAME_FIRST = (
    "Alex Amara Aria Bennett Cara Dara Devon Elia Emerson Farah Finley Gabriel Harper Idris "
    "Imani Jordan Kai Kiran Lena Logan Maya Micah Nadia Noor Omar Parker Quinn Rania Reese "
    "Rowan Sasha Simone Tariq Tessa Uma Vega Wren Yusuf Zara"
).split()
_NAME_LAST = (
    "Ahmed Baker Carter Diaz Ellis Fischer Gray Hassan Iqbal Jensen Khan Lawson Mensah Novak "
    "Okafor Patel Quinn Reyes Silva Tanaka Ueda Vargas Walsh Yilmaz Zhang"
).split()


@register("random-word-generator")
def random_word_generator(files, text: str, options: dict) -> ToolResult:
    """Words drawn from a small curated bank — no dictionary file to ship."""
    import random

    count = max(1, min(_int(options, "count", 10), 500))
    mode = str(options.get("mode", "words"))
    if mode == "names":
        out = [f"{random.choice(_NAME_FIRST)} {random.choice(_NAME_LAST)}" for _ in range(count)]
    else:
        pool = _WORD_BANK if count <= len(_WORD_BANK) and _flag(options, "unique", True) else None
        out = random.sample(_WORD_BANK, count) if pool else [random.choice(_WORD_BANK) for _ in range(count)]
        if _flag(options, "capitalize"):
            out = [w.capitalize() for w in out]
    sep = "\n" if str(options.get("separator", "newline")) == "newline" else ", "
    return ToolResult(text=sep.join(out), meta={"count": len(out)})


@register("username-generator")
def username_generator(files, text: str, options: dict) -> ToolResult:
    import random

    count = max(1, min(_int(options, "count", 10), 200))
    base = re.sub(r"[^a-z0-9]+", "", (text or "").lower())
    style = str(options.get("style", "word_word"))
    sep = str(options.get("separator", "_"))
    out = []
    for _ in range(count):
        if base and style == "name_number":
            name = base
        elif style == "name_number":
            name = random.choice(_NAME_FIRST).lower()
        else:
            name = random.choice(_WORD_BANK)
        if style == "word_word":
            handle = f"{name}{sep}{random.choice(_WORD_BANK)}"
        elif style == "name_number":
            handle = f"{name}{sep}{random.randint(1, 9999)}"
        else:
            handle = f"{random.choice(_WORD_BANK)}{sep}{random.choice(_WORD_BANK)}{random.randint(1, 99)}"
        out.append(handle[:30])
    return ToolResult(text="\n".join(_dedupe(out)), meta={"generated": len(set(out))})


@register("placeholder-data-generator")
def placeholder_data_generator(files, text: str, options: dict) -> ToolResult:
    """Fake rows for seeding a database or filling out a design mockup.

    Everything here is generated from the word banks above — no real person's
    details are involved, and the emails use example.com, which is reserved by
    the IETF exactly so test data cannot reach a live inbox.
    """
    import json as _json
    import random

    rows = max(1, min(_int(options, "rows", 10), 500))
    fmt = str(options.get("format", "json"))
    records = []
    for i in range(1, rows + 1):
        first = random.choice(_NAME_FIRST)
        last = random.choice(_NAME_LAST)
        records.append({
            "id": i,
            "name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}@example.com",
            "username": f"{first.lower()}{random.randint(10, 999)}",
            "city": random.choice(_WORD_BANK).capitalize(),
            "phone": f"+1-555-{random.randint(1000, 9999)}",
            "signed_up": f"202{random.randint(0, 6)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        })
    if fmt == "csv":
        headers = list(records[0])
        lines = [",".join(headers)]
        lines += [",".join(str(r[h]) for h in headers) for r in records]
        out = "\n".join(lines)
    elif fmt == "sql":
        headers = list(records[0])
        out = "\n".join(
            "INSERT INTO users (" + ", ".join(headers) + ") VALUES ("
            + ", ".join(str(r[h]) if isinstance(r[h], int) else "'" + str(r[h]).replace("'", "''") + "'"
                        for h in headers) + ");"
            for r in records
        )
    else:
        out = _json.dumps(records, indent=2)
    return ToolResult(text=out, meta={"rows": rows, "format": fmt})


# ===========================================================================
# Fancy Unicode text
# ===========================================================================
#
# These map plain letters onto look-alike Unicode code points. The result is
# real text you can paste into a bio or a post — not an image — but it is NOT
# plain ASCII: screen readers announce it character by character, and search
# engines do not treat it as the word it resembles. Fine for a display name,
# wrong for anything that needs to be read or found.

_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_LOWER = "abcdefghijklmnopqrstuvwxyz"
_DIGITS = "0123456789"


def _block(upper_start: int, lower_start: int, digit_start: int | None = None,
           holes: dict[str, str] | None = None) -> dict[str, str]:
    """Build a style map from the contiguous Unicode block it lives in.

    Several of the Mathematical Alphanumeric blocks have gaps, because the
    characters were already encoded elsewhere years earlier. `holes` patches
    those individually — without it, those letters land on unassigned code
    points and render as boxes.
    """
    table = {c: chr(upper_start + i) for i, c in enumerate(_UPPER)}
    table.update({c: chr(lower_start + i) for i, c in enumerate(_LOWER)})
    if digit_start is not None:
        table.update({c: chr(digit_start + i) for i, c in enumerate(_DIGITS)})
    if holes:
        table.update(holes)
    return table


_STYLES: dict[str, dict[str, str]] = {
    "bold": _block(0x1D400, 0x1D41A, 0x1D7CE),
    "italic": _block(0x1D434, 0x1D44E, holes={"h": "ℎ"}),
    "bold italic": _block(0x1D468, 0x1D482),
    "script": _block(0x1D49C, 0x1D4B6, holes={
        "B": "ℬ", "E": "ℰ", "F": "ℱ", "H": "ℋ", "I": "ℐ",
        "L": "ℒ", "M": "ℳ", "R": "ℛ", "e": "ℯ", "g": "ℊ",
        "o": "ℴ",
    }),
    "bold script": _block(0x1D4D0, 0x1D4EA),
    "fraktur": _block(0x1D504, 0x1D51E, holes={
        "C": "ℭ", "H": "ℌ", "I": "ℑ", "R": "ℜ", "Z": "ℨ",
    }),
    "double-struck": _block(0x1D538, 0x1D552, 0x1D7D8, holes={
        "C": "ℂ", "H": "ℍ", "N": "ℕ", "P": "ℙ", "Q": "ℚ",
        "R": "ℝ", "Z": "ℤ",
    }),
    "sans-serif": _block(0x1D5A0, 0x1D5BA, 0x1D7E2),
    "sans bold": _block(0x1D5D4, 0x1D5EE, 0x1D7EC),
    "sans italic": _block(0x1D608, 0x1D622),
    "monospace": _block(0x1D670, 0x1D68A, 0x1D7F6),
    "wide": {c: chr(0xFF21 + i) for i, c in enumerate(_UPPER)}
            | {c: chr(0xFF41 + i) for i, c in enumerate(_LOWER)}
            | {c: chr(0xFF10 + i) for i, c in enumerate(_DIGITS)}
            | {" ": "　"},
    "circled": {c: chr(0x24B6 + i) for i, c in enumerate(_UPPER)}
               | {c: chr(0x24D0 + i) for i, c in enumerate(_LOWER)}
               | {c: chr(0x2460 + i - 1) for i, c in enumerate(_DIGITS) if i}
               | {"0": "⓪"},
    "squared": {c: chr(0x1F130 + i) for i, c in enumerate(_UPPER)}
               | {c.lower(): chr(0x1F130 + i) for i, c in enumerate(_UPPER)},
    "small caps": dict(zip(_LOWER, "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘqʀsᴛᴜᴠᴡxʏᴢ"))
                  | dict(zip(_UPPER, "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘqʀsᴛᴜᴠᴡxʏᴢ")),
    # No superscript "q" exists in Unicode, so it is left out of the map on
    # purpose — the tool reports it rather than silently passing it through.
    "superscript": {c: v for c, v in zip(_LOWER, "ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖ?ʳˢᵗᵘᵛʷˣʸᶻ") if v != "?"}
                   | dict(zip(_DIGITS, "⁰¹²³⁴⁵⁶⁷⁸⁹"))
                   | {"+": "⁺", "-": "⁻", "=": "⁼", "(": "⁽", ")": "⁾"},
    "subscript": dict(zip(_DIGITS, "₀₁₂₃₄₅₆₇₈₉"))
                 | {"a": "ₐ", "e": "ₑ", "h": "ₕ", "i": "ᵢ", "j": "ⱼ", "k": "ₖ", "l": "ₗ",
                    "m": "ₘ", "n": "ₙ", "o": "ₒ", "p": "ₚ", "r": "ᵣ", "s": "ₛ", "t": "ₜ",
                    "u": "ᵤ", "v": "ᵥ", "x": "ₓ", "+": "₊", "-": "₋", "=": "₌"},
}

_UPSIDE_DOWN = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789,.?!'\"()[]{}<>&_;",
    "ɐqɔpǝɟƃɥıɾʞlɯuodbɹsʇnʌʍxʎz∀qƆpƎℲƃHIſʞ˥WNOԀQɹS┴∩ΛMX⅄Z0ƖᄅƐㄣϛ9ㄥ86'˙¿¡,„)(][}{><⅋‾؛",
)


def _apply_style(text: str, style: str) -> str:
    table = _STYLES.get(style)
    if table is None:
        return text
    return "".join(table.get(ch, ch) for ch in text)


@register("fancy-text-generator")
def fancy_text_generator(files, text: str, options: dict) -> ToolResult:
    """Every style at once, so you can pick the one you like."""
    text = (text or "").strip()
    if not text:
        return ToolResult(meta={"error": "Type some text to style."})
    if len(text) > 500:
        return ToolResult(meta={"error": "Keep it under 500 characters."})
    variants = {name: _apply_style(text, name) for name in _STYLES}
    variants["strikethrough"] = "".join(ch + "̶" for ch in text)
    variants["underline"] = "".join(ch + "̲" for ch in text)
    variants["upside down"] = text.lower().translate(_UPSIDE_DOWN)[::-1]
    variants["spaced"] = " ".join(text)
    return ToolResult(
        text="\n".join(f"{name}: {value}" for name, value in variants.items()),
        meta={"styles": variants,
              "note": "Real text, not an image — but screen readers spell it out letter by letter."},
    )


@register("bold-italic-text")
def bold_italic_text(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    if not text.strip():
        return ToolResult(meta={"error": "Type some text to style."})
    style = str(options.get("style", "bold"))
    if style not in _STYLES:
        return ToolResult(meta={"error": "Choose one of the listed styles."})
    return ToolResult(text=_apply_style(text, style), meta={"style": style})


@register("small-superscript-text")
def small_superscript_text(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    if not text.strip():
        return ToolResult(meta={"error": "Type some text to convert."})
    style = str(options.get("style", "small caps"))
    out = _apply_style(text, style)
    missing = sorted({ch for ch in text if ch.isalnum() and _STYLES[style].get(ch) is None})
    meta = {"style": style}
    if missing:
        # Superscript and subscript are incomplete blocks in Unicode; there is no
        # superscript "q", so say so rather than silently leaving it plain.
        meta["no_equivalent_for"] = missing
    return ToolResult(text=out, meta=meta)


@register("strikethrough-text")
def strikethrough_text(files, text: str, options: dict) -> ToolResult:
    """Adds a combining mark after each character, so any font can render it."""
    text = text or ""
    if not text.strip():
        return ToolResult(meta={"error": "Type some text."})
    marks = {"strikethrough": "̶", "underline": "̲", "double underline": "̳",
             "overline": "̅", "slash": "̷"}
    mark = marks.get(str(options.get("style", "strikethrough")), "̶")
    return ToolResult(text="".join(ch + mark for ch in text),
                      meta={"note": "Combining marks — they may sit differently in some fonts."})


@register("bubble-square-text")
def bubble_square_text(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    if not text.strip():
        return ToolResult(meta={"error": "Type some text."})
    style = "circled" if str(options.get("style", "bubble")) == "bubble" else "squared"
    return ToolResult(text=_apply_style(text, style), meta={"style": style})


@register("zalgo-text-generator")
def zalgo_text_generator(files, text: str, options: dict) -> ToolResult:
    """Piles combining diacritics onto each character for the 'glitch' look."""
    import random

    text = text or ""
    if not text.strip():
        return ToolResult(meta={"error": "Type some text."})
    if len(text) > 200:
        return ToolResult(meta={"error": "Keep it under 200 characters — the output grows fast."})
    intensity = max(1, min(_int(options, "intensity", 5), 30))
    above = [chr(c) for c in range(0x0300, 0x0315)]
    below = [chr(c) for c in range(0x0316, 0x0333)]
    middle = [chr(c) for c in range(0x0334, 0x0338)]
    pools = []
    if _flag(options, "above", True):
        pools.append(above)
    if _flag(options, "below", True):
        pools.append(below)
    if _flag(options, "middle"):
        pools.append(middle)
    if not pools:
        return ToolResult(meta={"error": "Turn on at least one direction."})
    out = []
    for ch in text:
        out.append(ch)
        if ch.isspace():
            continue
        for pool in pools:
            out += [random.choice(pool) for _ in range(random.randint(1, intensity))]
    return ToolResult(text="".join(out),
                      meta={"note": "Some apps strip or flatten combining marks."})


@register("upside-down-text")
def upside_down_text(files, text: str, options: dict) -> ToolResult:
    text = text or ""
    if not text.strip():
        return ToolResult(meta={"error": "Type some text to flip."})
    flipped = text.translate(_UPSIDE_DOWN)
    if _flag(options, "reverse", True):
        # Flipping each letter is only half of it — reading upside down also runs
        # right to left, so the string is reversed unless you turn that off.
        flipped = flipped[::-1]
    return ToolResult(text=flipped)


_ASCII_FONT = {
    "A": ["  #  ", " # # ", "#####", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#### ", "#   #", "#### "],
    "C": [" ####", "#    ", "#    ", "#    ", " ####"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#### ", "#    ", "#####"],
    "F": ["#####", "#    ", "#### ", "#    ", "#    "],
    "G": [" ####", "#    ", "#  ##", "#   #", " ####"],
    "H": ["#   #", "#   #", "#####", "#   #", "#   #"],
    "I": ["#####", "  #  ", "  #  ", "  #  ", "#####"],
    "J": ["    #", "    #", "    #", "#   #", " ### "],
    "K": ["#   #", "#  # ", "###  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#### ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "# # #", "#  # ", " ## #"],
    "R": ["#### ", "#   #", "#### ", "#  # ", "#   #"],
    "S": [" ####", "#    ", " ### ", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", " # # ", "  #  "],
    "W": ["#   #", "#   #", "# # #", "## ##", "#   #"],
    "X": ["#   #", " # # ", "  #  ", " # # ", "#   #"],
    "Y": ["#   #", " # # ", "  #  ", "  #  ", "  #  "],
    "Z": ["#####", "   # ", "  #  ", " #   ", "#####"],
    "0": [" ### ", "#  ##", "# # #", "##  #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", "#####"],
    "2": [" ### ", "#   #", "   # ", "  #  ", "#####"],
    "3": ["#### ", "    #", " ### ", "    #", "#### "],
    "4": ["#   #", "#   #", "#####", "    #", "    #"],
    "5": ["#####", "#    ", "#### ", "    #", "#### "],
    "6": [" ### ", "#    ", "#### ", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", "  #  "],
    "8": [" ### ", "#   #", " ### ", "#   #", " ### "],
    "9": [" ### ", "#   #", " ####", "    #", " ### "],
    "!": ["  #  ", "  #  ", "  #  ", "     ", "  #  "],
    "?": [" ### ", "#   #", "   # ", "     ", "  #  "],
    ".": ["     ", "     ", "     ", "     ", "  #  "],
    "-": ["     ", "     ", "#####", "     ", "     "],
    " ": ["     ", "     ", "     ", "     ", "     "],
}


@register("ascii-art-generator")
def ascii_art_generator(files, text: str, options: dict) -> ToolResult:
    """Draws short text in a built-in 5-row block font.

    A single embedded font rather than a font library: the whole point of this
    tool is that it works with nothing installed.
    """
    raw = (text or "").strip().upper()
    if not raw:
        return ToolResult(meta={"error": "Type a word to draw."})
    if len(raw) > 20:
        return ToolResult(meta={"error": "Keep it to 20 characters — longer than that won't fit."})
    unsupported = sorted({c for c in raw if c not in _ASCII_FONT})
    if unsupported:
        return ToolResult(meta={
            "error": f"No shape for: {' '.join(unsupported)}. Letters, digits and . - ! ? only."
        })
    fill = str(options.get("character", "#"))[:1] or "#"
    gap = " " * max(0, min(_int(options, "spacing", 1), 5))
    rows = ["".join(_ASCII_FONT[c][r] + gap for c in raw).rstrip() for r in range(5)]
    art = "\n".join(row.replace("#", fill) for row in rows)
    return ToolResult(text=art, meta={"characters": len(raw), "width": max(len(r) for r in rows)})


# ===========================================================================
# Markdown
# ===========================================================================

def _md_inline(text: str) -> str:
    """Inline Markdown → HTML, with the text escaped first.

    Escaping before any tag is inserted is what stops a pasted `<script>` from
    surviving into the output. Everything after this point only ever adds tags
    this function itself produced.
    """
    import html as _html

    out = _html.escape(text, quote=False)
    out = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img src="\2" alt="\1">', out)
    out = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", out)
    out = re.sub(r"~~(.+?)~~", r"<del>\1</del>", out)
    return out


@register("markdown-to-html")
def markdown_to_html(files, text: str, options: dict) -> ToolResult:
    """A focused Markdown subset: headings, lists, quotes, code, tables, rules.

    Not a full CommonMark implementation — it covers what people actually write
    in a README or a blog draft, and escapes everything it doesn't understand
    rather than passing raw HTML through.
    """
    import html as _html

    src = (text or "").replace("\r\n", "\n")
    if not src.strip():
        return ToolResult(meta={"error": "Paste some Markdown."})

    html_lines: list[str] = []
    list_stack: list[str] = []
    in_code = False
    code_buffer: list[str] = []
    paragraph: list[str] = []

    def close_lists() -> None:
        while list_stack:
            html_lines.append(f"</{list_stack.pop()}>")

    def flush_paragraph() -> None:
        if paragraph:
            html_lines.append("<p>" + _md_inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    for line in src.split("\n"):
        fence = re.match(r"^```(\w*)", line)
        if fence:
            if in_code:
                html_lines.append("<pre><code>" + _html.escape("\n".join(code_buffer)) + "</code></pre>")
                code_buffer.clear()
                in_code = False
            else:
                flush_paragraph()
                close_lists()
                in_code = True
            continue
        if in_code:
            code_buffer.append(line)
            continue

        if not line.strip():
            flush_paragraph()
            close_lists()
            continue
        if re.match(r"^\s*([-*_])\1{2,}\s*$", line):
            flush_paragraph()
            close_lists()
            html_lines.append("<hr>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            flush_paragraph()
            close_lists()
            level = len(heading.group(1))
            html_lines.append(f"<h{level}>{_md_inline(heading.group(2).strip())}</h{level}>")
            continue
        quote = re.match(r"^>\s?(.*)$", line)
        if quote:
            flush_paragraph()
            close_lists()
            html_lines.append(f"<blockquote>{_md_inline(quote.group(1))}</blockquote>")
            continue
        bullet = re.match(r"^\s*[-*+]\s+(.*)$", line)
        number = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if bullet or number:
            flush_paragraph()
            want = "ul" if bullet else "ol"
            if not list_stack or list_stack[-1] != want:
                close_lists()
                list_stack.append(want)
                html_lines.append(f"<{want}>")
            content = (bullet or number).group(1)
            html_lines.append(f"<li>{_md_inline(content)}</li>")
            continue
        close_lists()
        paragraph.append(line.strip())

    if in_code:  # unterminated fence — keep the content rather than losing it
        html_lines.append("<pre><code>" + _html.escape("\n".join(code_buffer)) + "</code></pre>")
    flush_paragraph()
    close_lists()
    return ToolResult(text="\n".join(html_lines), meta={"lines_in": len(src.split("\n"))})


@register("html-to-markdown")
def html_to_markdown(files, text: str, options: dict) -> ToolResult:
    """HTML → Markdown for the tags that have a Markdown equivalent."""
    import html as _html

    src = (text or "").replace("\r\n", "\n")
    if not src.strip():
        return ToolResult(meta={"error": "Paste some HTML."})

    out = re.sub(r"<!--.*?-->", "", src, flags=re.DOTALL)
    # Script and style hold code, not prose — drop them whole rather than
    # letting their contents fall through as body text.
    out = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", out, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"<br\s*/?>", "\n", out, flags=re.IGNORECASE)
    out = re.sub(r"<hr\s*/?>", "\n---\n", out, flags=re.IGNORECASE)
    for level in range(6, 0, -1):
        out = re.sub(rf"<h{level}[^>]*>(.*?)</h{level}>", rf"\n{'#' * level} \1\n",
                     out, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"<(strong|b)\b[^>]*>(.*?)</\1>", r"**\2**", out, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"<(em|i)\b[^>]*>(.*?)</\1>", r"*\2*", out, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"<(del|s|strike)\b[^>]*>(.*?)</\1>", r"~~\2~~", out, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"<pre[^>]*>\s*<code[^>]*>(.*?)</code>\s*</pre>", r"\n```\n\1\n```\n",
                 out, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", out, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r'<img[^>]*alt="([^"]*)"[^>]*src="([^"]*)"[^>]*>', r"![\1](\2)", out, flags=re.IGNORECASE)
    out = re.sub(r'<img[^>]*src="([^"]*)"[^>]*>', r"![](\1)", out, flags=re.IGNORECASE)
    out = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", out, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"<blockquote[^>]*>(.*?)</blockquote>",
                 lambda m: "\n" + "\n".join("> " + ln.strip() for ln in m.group(1).strip().split("\n")) + "\n",
                 out, flags=re.DOTALL | re.IGNORECASE)
    def _list(match: re.Match) -> str:
        """Render a list, numbering it when the parent tag says to.

        The generic <li> rule below can't do this: by the time it runs, an item
        has no idea whether it came from a <ul> or an <ol>, so every ordered
        list came out as bullets.
        """
        ordered = match.group(1).lower() == "ol"
        items = re.findall(r"<li[^>]*>(.*?)</li>", match.group(2), re.DOTALL | re.IGNORECASE)
        rendered = [
            f"{i}. {item.strip()}" if ordered else f"- {item.strip()}"
            for i, item in enumerate(items, start=1)
        ]
        return "\n" + "\n".join(rendered) + "\n"

    out = re.sub(r"<(ul|ol)[^>]*>(.*?)</\1>", _list, out, flags=re.DOTALL | re.IGNORECASE)
    # Anything left is a stray <li> outside a list, or a nesting shape the
    # pattern above didn't match.
    out = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", out, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"</?(ul|ol)[^>]*>", "\n", out, flags=re.IGNORECASE)
    out = re.sub(r"</p>", "\n\n", out, flags=re.IGNORECASE)
    out = re.sub(r"<[^>]+>", "", out)          # anything left has no equivalent
    out = _html.unescape(out)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return ToolResult(text=out.strip())


@register("hashtag-generator")
def hashtag_generator(files, text: str, options: dict) -> ToolResult:
    """Turns a topic or a block of text into usable hashtags."""
    from collections import Counter

    src = (text or "").strip()
    if not src:
        return ToolResult(meta={"error": "Enter a topic, or paste your caption."})
    stop = {"the","a","an","and","or","of","to","in","on","for","with","is","are","was","this",
            "that","it","at","by","from","as","be","you","your","our","we","my","me","i"}
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]+", src)
             if len(w) > 2 and w.lower() not in stop]
    if not words:
        return ToolResult(meta={"error": "No usable words found."})
    limit = max(1, min(_int(options, "count", 20), 60))
    style = str(options.get("style", "lowercase"))
    ranked = [w for w, _ in Counter(words).most_common(limit)]

    def shape(word: str) -> str:
        return f"#{word.capitalize()}" if style == "camel" else f"#{word}"

    tags = [shape(w) for w in ranked]
    # Two-word combinations read as real hashtags (#contentwriting) rather than
    # a list of loose keywords, which is what people actually post.
    if _flag(options, "combine", True) and len(ranked) > 1:
        tags += [shape(ranked[i] + ranked[i + 1]) for i in range(min(5, len(ranked) - 1))]
    tags = _dedupe(tags)[:limit]
    sep = "\n" if str(options.get("separator", "space")) == "newline" else " "
    return ToolResult(text=sep.join(tags), meta={"hashtags": len(tags), "source_words": len(set(words))})
