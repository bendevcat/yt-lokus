#!/usr/bin/env python3
"""Outils autour des notes Lokus.

    lokus_tools.py find <id_video> <racine>   notes qui mentionnent déjà cette vidéo
    lokus_tools.py tags <racine>              tags utilisés, du plus fréquent au plus rare
    lokus_tools.py check <note.md>            contrôle une note terminée (code 1 si erreur)
"""
import collections
import os
import re
import sys
from pathlib import Path

TRANSCRIPT_HEADING = "## Transcription"
REVIEW_HEADING = "## Avis critique"
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
        counts.update(TAG.findall(text.split(TRANSCRIPT_HEADING)[0]))
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
            errors.append(f"le marqueur {marker} est encore là")
    if TRANSCRIPT_HEADING not in text:
        sys.exit(f"ERREUR : pas de section « {TRANSCRIPT_HEADING} »")
    head, transcript = text.split(TRANSCRIPT_HEADING, 1)
    if not re.search(rf"^{REVIEW_HEADING}\n+\*\*Verdict :\*\* \S", head, re.MULTILINE):
        errors.append(f"section « {REVIEW_HEADING} » absente ou sans verdict")
    cited = TIMESTAMP.findall(head)
    known = set(TIMESTAMP.findall(transcript))
    if not cited:
        errors.append("aucun horodatage cité dans le résumé")
    for stamp, offset in cited:
        if (stamp, offset) not in known:
            errors.append(f"horodatage absent de la transcription : {stamp} (t={offset})")
        if seconds(stamp) != int(offset):
            errors.append(f"horodatage incohérent : {stamp} ≠ t={offset}")
    lines = text.split("\n")
    tag_line = lines[2] if len(lines) > 2 else ""
    if not TAG_LINE.fullmatch(tag_line):
        errors.append(f"ligne de tags mal formée : {tag_line!r}")
    elif len(tag_line.split()) < 4:
        errors.append("moins de 2 tags thématiques")
    for error in errors:
        print("ERREUR :", error)
    if errors:
        sys.exit(1)
    print(f"OK : {len(cited)} horodatages cités, tous présents")


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
