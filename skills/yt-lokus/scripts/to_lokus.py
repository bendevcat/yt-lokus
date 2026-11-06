#!/usr/bin/env python3
"""Turns YouTube subtitles fetched by yt-dlp into a Markdown note for Lokus.

    to_lokus.py <video.info.json> <video.LANG.json3> <output_dir> [note_lang]

Both files come from yt-dlp (--write-info-json --write-subs --write-auto-subs
--sub-format json3). note_lang sets the language of the note's labels: `fr` or
`en` (default), any other value falls back to English.

Writes <output_dir>/<title>.md and prints its path. An existing file is never
overwritten (suffix -2, -3…). The summary and review sections hold the markers
<!-- RESUME --> and <!-- AVIS -->, which Claude then replaces.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

PARAGRAPH_SECONDS = 60  # durée cible d'un paragraphe horodaté
SHORT_TURN_WORDS = 3  # en dessous, une prise de parole est une simple relance
CHAPTER_GRACE_SECONDS = 15  # délai pour finir la phrase avant de couper à un chapitre
SENTENCE_END = re.compile(r"[.?!…]+(?=\s|$)")
SOUND_TAG = re.compile(r"\[[^\]]*\]|♪+")  # [musique], [Applaudissements]…

LABELS = {
    "fr": {
        "colon": " :",
        "thumbnail": "miniature",
        "channel": "Chaîne",
        "language": "Langue",
        "words": "Mots",
        "transcribed": "Transcrit le",
        "summary": "Résumé",
        "review": "Avis critique",
        "transcript": "Transcription",
        "auto": "**Sous-titres automatiques** : noms propres et termes techniques"
                " peuvent être mal transcrits.",
        "voices": " Un « — » marque un changement de voix détecté par YouTube.",
        "translated": "**Sous-titres traduits automatiquement** : la vidéo est en"
                      " « {spoken} », la piste « {track} » est une traduction de YouTube.",
    },
    "en": {
        "colon": ":",
        "thumbnail": "thumbnail",
        "channel": "Channel",
        "language": "Language",
        "words": "Words",
        "transcribed": "Transcribed on",
        "summary": "Summary",
        "review": "Critical review",
        "transcript": "Transcript",
        "auto": "**Automatic subtitles**: proper nouns and technical terms"
                " may be mistranscribed.",
        "voices": " A “—” marks a speaker change detected by YouTube.",
        "translated": "**Auto-translated subtitles**: the video is in “{spoken}”,"
                      " the “{track}” track is a YouTube translation.",
    },
}


def fmt_ts(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def split_turns(segments: list[dict]) -> list[list[dict]]:
    """Découpe en prises de parole aux repères `speaker_change` de YouTube.

    Une prise de parole de SHORT_TURN_WORDS mots ou moins (« Ouais. », « OK. »)
    est une relance : elle reste dans la prise précédente, entre parenthèses.
    """
    turns: list[list[dict]] = []
    for seg in segments:
        if seg.get("speaker_change") or not turns:
            turns.append([])
        turns[-1].append(seg)
    merged: list[list[dict]] = []
    for turn in turns:
        words = sum(len(s["text"].split()) for s in turn)
        if merged and words <= SHORT_TURN_WORDS:
            text = " ".join(" ".join(s["text"] for s in turn).split())
            merged[-1].append({"start": turn[0]["start"], "text": f"*(— {text})*", "aside": True})
        else:
            merged.append(list(turn))
    return merged


def group_segments(segments: list[dict], chapter_starts: list[float]) -> list[tuple[float, str]]:
    """Regroupe les lignes de sous-titres en paragraphes (start, texte).

    Chaque prise de parole ouvre un paragraphe commençant par « — ». Sans
    repères de locuteur, tout est une seule prise.
    """
    has_turns = any(s.get("speaker_change") for s in segments)
    paragraphs: list[tuple[float, str]] = []
    for turn in split_turns(segments):
        first = len(paragraphs)
        paragraphs += group_turn(turn, chapter_starts)
        if has_turns and len(paragraphs) > first:
            t, txt = paragraphs[first]
            paragraphs[first] = (t, f"— {txt}")
    return paragraphs


def group_turn(segments: list[dict], chapter_starts: list[float]) -> list[tuple[float, str]]:
    """Découpe une prise de parole en paragraphes.

    On cherche à couper dès que le paragraphe dépasse PARAGRAPH_SECONDS ou
    franchit un début de chapitre. La coupure se fait à la dernière fin de
    phrase de la ligne courante : dans les sous-titres auto, les lignes coupent
    n'importe où et finissent rarement sur un point. Le texte qui suit ouvre le
    paragraphe suivant, horodaté au début de la ligne (donc un peu en avance).
    Sans fin de phrase (sous-titres sans ponctuation), coupure forcée à 2× la
    durée cible, ou CHAPTER_GRACE_SECONDS après le début du chapitre.
    """
    paragraphs: list[tuple[float, str]] = []
    start, buf = None, []
    for seg in segments:
        text = " ".join(seg.get("text", "").split())
        if not text:
            continue
        if seg.get("aside") and not buf and paragraphs:
            # une relance n'ouvre jamais de paragraphe : elle suit le précédent
            t, txt = paragraphs[-1]
            paragraphs[-1] = (t, f"{txt} {text}")
            continue
        now = float(seg["start"])
        if start is None:
            start = now
        buf.append(text)
        elapsed = now - start
        chapter = next((c for c in chapter_starts if start < c <= now), None)
        if elapsed < PARAGRAPH_SECONDS and chapter is None:
            continue
        ends = list(SENTENCE_END.finditer(text))
        if ends:
            cut = ends[-1].end()
            buf[-1] = text[:cut]
            tail = text[cut:].strip()
            paragraphs.append((start, " ".join(buf)))
            start, buf = (now, [tail]) if tail else (None, [])
        elif elapsed >= 2 * PARAGRAPH_SECONDS or (
            chapter is not None and now - chapter >= CHAPTER_GRACE_SECONDS
        ):
            paragraphs.append((start, " ".join(buf)))
            start, buf = None, []
    if buf:
        paragraphs.append((start, " ".join(buf)))
    return paragraphs


def render_body(vid: str, paragraphs: list[tuple[float, str]], chapters: list[dict]) -> str:
    """Paragraphes horodatés, avec un titre ### avant chaque chapitre."""
    pending = list(chapters)
    blocks = []
    for t, txt in paragraphs:
        while pending and pending[0]["start"] <= t:
            blocks.append(f"### {pending.pop(0)['title']}")
        blocks.append(f"**[{fmt_ts(t)}](https://youtu.be/{vid}?t={int(t)})** {txt}")
    return "\n\n".join(blocks)


def safe_filename(title: str) -> str:
    name = re.sub(r'[\\/:*?"<>|#^\[\]]', "", title).strip().rstrip(".")
    return (name or "transcript")[:120]


def build_note(d: dict, note_lang: str = "en") -> str:
    labels = LABELS.get(note_lang.split("-")[0].lower(), LABELS["en"])
    colon = labels["colon"]
    vid = d["video_id"]
    url = f"https://www.youtube.com/watch?v={vid}"
    lang = d["language_code"]
    caption = d["caption_type"]
    chapters = d["chapters"]
    paragraphs = group_segments(d["segments"], [c["start"] for c in chapters])
    body = render_body(vid, paragraphs, chapters)

    warn = ""
    if caption == "auto":
        voices = labels["voices"] if any(s.get("speaker_change") for s in d["segments"]) else ""
        warn = f"\n> [!note]\n> {labels['auto']}{voices}\n"
    if d.get("translated_from"):
        translated = labels["translated"].format(spoken=d["translated_from"], track=lang)
        warn += f"\n> [!warning]\n> {translated}\n"

    # Pas de frontmatter : Lokus 1.2 ne le gère pas (il devient un titre à la
    # première sauvegarde) et son graphe ne lit que les #tags du texte.
    return f"""# {d.get("title") or vid}

#youtube #transcript

[![{labels["thumbnail"]}]({d.get("thumbnail_url") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"})]({url})

**Source{colon}** [YouTube]({url}) · **{labels["channel"]}{colon}** [{d.get("author_name") or "?"}]({d.get("author_url") or url}) · **{labels["language"]}{colon}** {lang} ({caption}) · **{labels["words"]}{colon}** {d["word_count"]} · **{labels["transcribed"]}{colon}** {date.today().isoformat()}
{warn}
## {labels["summary"]}

<!-- RESUME -->

## {labels["review"]}

<!-- AVIS -->

## {labels["transcript"]}

{body}
"""


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_segments(events: list[dict], clean_sound_tags: bool) -> list[dict]:
    """Extrait les lignes de sous-titres d'un fichier json3.

    YouTube marque souvent à tort un changement de voix sur un repère sonore et
    sur la ligne qui le suit : ces deux repères-là sont ignorés.
    """
    segments = []
    after_tag = False
    for ev in events:
        segs = ev.get("segs") or []
        text = "".join(s.get("utf8", "") for s in segs)
        if ev.get("aAppend") or not text.strip():
            continue  # événements "\n" de défilement des sous-titres auto
        changed = any(s.get("isSpeakerChange") for s in segs)
        has_tag = False
        if clean_sound_tags:
            text, count = SOUND_TAG.subn("", text)
            has_tag = count > 0
        changed = changed and not has_tag and not after_tag
        after_tag = has_tag
        if text.strip():
            segments.append({"start": ev["tStartMs"] / 1000, "text": text, "speaker_change": changed})
    return segments


def from_ytdlp(info_path: str, subs_path: str) -> dict:
    """Rassemble les métadonnées et les sous-titres écrits par yt-dlp."""
    info = load_json(info_path)
    # yt-dlp nomme les sous-titres <id>.<lang>.json3
    lang = Path(subs_path).name.rsplit(".", 2)[-2]
    caption = "manual" if lang in (info.get("subtitles") or {}) else "auto"
    segments = read_segments(load_json(subs_path).get("events", []), caption == "auto")
    spoken = info.get("language") or ""
    translated = caption == "auto" and spoken and spoken.split("-")[0].lower() != lang.split("-")[0].lower()
    return {
        "video_id": info["id"],
        "title": info.get("title"),
        "author_name": info.get("channel") or info.get("uploader"),
        "author_url": info.get("channel_url") or info.get("uploader_url"),
        "thumbnail_url": info.get("thumbnail"),
        "language_code": lang,
        "caption_type": caption,
        "translated_from": spoken if translated else None,
        "word_count": sum(len(s["text"].split()) for s in segments),
        "chapters": [{"start": float(c["start_time"]), "title": c["title"]}
                     for c in info.get("chapters") or []],
        "segments": segments,
    }


def main() -> None:
    args = sys.argv[1:]
    if len(args) not in (3, 4):
        sys.exit(__doc__)
    data = from_ytdlp(args[0], args[1])
    out_dir = Path(args[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    base = safe_filename(data.get("title") or data["video_id"])
    path, n = out_dir / f"{base}.md", 2
    while path.exists():
        path, n = out_dir / f"{base}-{n}.md", n + 1
    path.write_text(build_note(data, *args[3:]), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
