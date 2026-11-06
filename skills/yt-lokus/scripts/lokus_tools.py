#!/usr/bin/env python3
"""Tools for Lokus notes.

    lokus_tools.py find <video_id> <root>   notes that already mention this video
    lokus_tools.py tags <root>              tags in use, most frequent first
    lokus_tools.py check <note.md>          checks a finished note (exit 1 on error)

French and English notes are both understood.
"""
import collections
import os
import re
import sys
from pathlib import Path

TRANSCRIPT_HEADING = re.compile(r"^## (?:Transcription|Transcript)$", re.MULTILINE)
REVIEW_WITH_VERDICT = re.compile(
    r"^## (?:Avis critique|Critical review)\n+\*\*Verdict ?:\*\* \S", re.MULTILINE
)
TIMESTAMP = re.compile(r"\[((?:\d+:)?\d\d:\d\d)\]\(https://youtu\.be/[\w-]+\?t=(\d+)\)")
TAG = re.compile(r"(?:^|(?<=\s))#([^\W\d][\w-]*)", re.MULTILINE)
TAG_LINE = re.compile(r"#[a-z0-9-]+(?: #[a-z0-9-]+)*")


def notes(root: str, skip: tuple[str, ...] = ()):
    for folder, subdirs, files in os.walk(root):
        subdirs[:] = [d for d in subdirs if not d.startswith(".") and d not in skip]
        for name in sorted(files):
            if name.endswith(".md"):
                path = Path(folder) / name
                yield path, path.read_text(encoding="utf-8", errors="replace")


def find(video_id: str, root: str) -> None:
    for path, text in notes(root):
        if video_id in text:
            print(path)


def tags(root: str) -> None:
    counts = collections.Counter()
    for _, text in notes(root, skip=("templates",)):
        # une transcription n'est pas une liste de tags
        counts.update(TAG.findall(TRANSCRIPT_HEADING.split(text, maxsplit=1)[0]))
    for tag, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(count, tag)


def seconds(stamp: str) -> int:
    total = 0
    for part in stamp.split(":"):
        total = total * 60 + int(part)
    return total


def check(note: str) -> None:
    text = Path(note).read_text(encoding="utf-8")
    errors = []
    for marker in ("<!-- RESUME -->", "<!-- AVIS -->"):
        if marker in text:
            errors.append(f"marker {marker} is still there")
    parts = TRANSCRIPT_HEADING.split(text, maxsplit=1)
    if len(parts) != 2:
        sys.exit("ERROR: no transcript section")
    head, transcript = parts
    if not REVIEW_WITH_VERDICT.search(head):
        errors.append("critical review section missing or without a verdict")
    cited = TIMESTAMP.findall(head)
    known = set(TIMESTAMP.findall(transcript))
    if not cited:
        errors.append("no timestamp cited in the summary")
    for stamp, offset in cited:
        if (stamp, offset) not in known:
            errors.append(f"timestamp not in the transcript: {stamp} (t={offset})")
        if seconds(stamp) != int(offset):
            errors.append(f"inconsistent timestamp: {stamp} ≠ t={offset}")
    lines = text.split("\n")
    tag_line = lines[2] if len(lines) > 2 else ""
    if not TAG_LINE.fullmatch(tag_line):
        errors.append(f"malformed tag line: {tag_line!r}")
    elif len(tag_line.split()) < 4:
        errors.append("fewer than 2 topic tags")
    for error in errors:
        print("ERROR:", error)
    if errors:
        sys.exit(1)
    print(f"OK: {len(cited)} timestamps cited, all present")


def main() -> None:
    args = sys.argv[1:]
    if len(args) == 3 and args[0] == "find":
        find(args[1], args[2])
    elif len(args) == 2 and args[0] == "tags":
        tags(args[1])
    elif len(args) == 2 and args[0] == "check":
        check(args[1])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
