"""Detect mixed-script and confusable characters in UTM keys and values.

Copy-paste from Word, slides, translated briefs, or lookalike fonts often
introduces a single Cyrillic or Greek letter into an otherwise Latin campaign
name. GA4 treats ``cmp-lаunch`` (Cyrillic ``а``) as a different campaign from
``cmp-launch``, so attribution silently splits.

Detection is conservative:

- flag strings that mix Latin with Cyrillic or Greek letters
- flag fullwidth / halfwidth forms that NFKC-normalize to different code points
- flag a small set of format / soft-hyphen characters that are not covered by
  whitespace rules

ASCII-only values and single-script non-Latin values are left alone so
intentional localized campaign names are not rejected.
"""

from __future__ import annotations

import unicodedata

# Scripts that commonly collide with Latin in marketing copy.
_LATIN = "LATIN"
_CYRILLIC = "CYRILLIC"
_GREEK = "GREEK"

_COLLIDING_SCRIPTS = frozenset({_LATIN, _CYRILLIC, _GREEK})

# Soft hyphen and related format marks that survive strip() and look identical
# to a regular hyphen or to nothing at all in most UIs.
_FORMAT_MARKS = frozenset(
    {
        "\u00ad",  # soft hyphen
        "\u034f",  # combining grapheme joiner
        "\u061c",  # Arabic letter mark
        "\u180e",  # Mongolian vowel separator
        "\u2060",  # word joiner
        "\u2061",  # function application
        "\u2062",  # invisible times
        "\u2063",  # invisible separator
        "\u2064",  # invisible plus
        "\u2066",  # LRI
        "\u2067",  # RLI
        "\u2068",  # FSI
        "\u2069",  # PDI
    }
)


def _letter_script(char: str) -> str | None:
    if not char.isalpha():
        return None
    name = unicodedata.name(char, "")
    if name.startswith("LATIN "):
        return _LATIN
    if name.startswith("CYRILLIC "):
        return _CYRILLIC
    if name.startswith("GREEK "):
        return _GREEK
    return None


def mixed_script_label(value: str) -> str | None:
    """Return a short label if *value* mixes colliding scripts or confusables.

    Returns ``None`` when the string is clean.
    """

    if not value:
        return None

    scripts = {script for char in value if (script := _letter_script(char))}
    colliding = scripts & _COLLIDING_SCRIPTS
    if _LATIN in colliding and len(colliding) > 1:
        others = ", ".join(sorted(s.title() for s in colliding if s != _LATIN))
        return f"mixes Latin with {others} letters"

    for char in value:
        if char in _FORMAT_MARKS:
            name = unicodedata.name(char, f"U+{ord(char):04X}")
            return f"contains format character {name}"

    # Fullwidth Latin, compatibility ideographs, and similar forms that
    # look like ASCII after NFKC but are distinct query values.
    nfkc = unicodedata.normalize("NFKC", value)
    if nfkc != value:
        return "contains compatibility / fullwidth characters that NFKC-normalize"

    return None
