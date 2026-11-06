# yt-lokus

**English** · [Français](README.fr.md)

A Claude Code plugin that turns a YouTube video into a Markdown note for
[Lokus](https://github.com/lokus-ai/lokus). Give Claude a link: it fetches the
subtitles and files a note, ready to read, in your notes folder.

## What a note contains

- Video metadata: thumbnail, channel, language, word count
- A summary in French, whatever the language of the video, with clickable timestamps
- A critical review: what holds up, what is debatable, what it changes for you
- A transcript split into timestamped paragraphs, with chapters and speaker changes
- Topic tags that link the note to the others in the Lokus graph

Before handing over the note, a check confirms that every cited timestamp exists in the transcript.

## Requirements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp): `brew install yt-dlp` or `pipx install yt-dlp`
- Python 3.9 or later, nothing else to install
- No API key: subtitles come straight from YouTube

## Installation

```bash
claude plugin marketplace add bendevcat/yt-lokus
claude plugin install yt-lokus@yt-lokus-marketplace
```

Then set the root of your notes with the `YT_LOKUS_NOTES` variable in `~/.claude/settings.json`:

```json
{
  "env": {
    "YT_LOKUS_NOTES": "/path/to/your/notes"
  }
}
```

Without this variable, Claude asks you for the path. Notes land in the `yt-transcribe` subfolder.

## Usage

Just ask, for example "transcribe this video into Lokus: <url>", or
type `/yt-lokus:yt-lokus <url>`.

A video that was already transcribed is flagged before a new note is made, and an existing note is never overwritten.

## Limitations

- A video with no subtitles at all, not even automatic ones, cannot be transcribed: the plugin does no speech recognition
- Automatic subtitles garble proper nouns: Claude lists the obvious corrections in a callout
- Notes are written for Lokus, without frontmatter, and the generated text (summary, review, section titles) is in French

## License

[MIT](LICENSE)
