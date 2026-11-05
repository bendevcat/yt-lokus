# yt-lokus

Un plugin Claude Code qui transforme une vidéo YouTube en note Markdown pour
[Lokus](https://github.com/lokus-ai/lokus). Donnez un lien à Claude, il récupère les
sous-titres et range une note prête à relire dans votre dossier de notes.

## Ce que contient une note

- Métadonnées de la vidéo : miniature, chaîne, langue, nombre de mots
- Résumé en français, quelle que soit la langue de la vidéo, avec des horodatages cliquables
- Avis critique : ce qui tient, ce qui se discute, ce que ça change pour vous
- Transcription découpée en paragraphes horodatés, avec les chapitres et les changements de voix
- Tags thématiques qui relient la note aux autres dans le graphe de Lokus

Avant de rendre la note, un contrôle vérifie que chaque horodatage cité existe dans la transcription.

## Prérequis

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) : `brew install yt-dlp` ou `pipx install yt-dlp`
- Python 3.9 ou plus récent, sans dépendance à installer
- Aucune clé d'API : les sous-titres viennent directement de YouTube

## Installation

```bash
claude plugin marketplace add bendevcat/yt-lokus
claude plugin install yt-lokus@yt-lokus-marketplace
```

Indiquez ensuite la racine de vos notes dans la variable `YT_LOKUS_NOTES` de `~/.claude/settings.json` :

```json
{
  "env": {
    "YT_LOKUS_NOTES": "/chemin/vers/vos/notes"
  }
}
```

Sans cette variable, Claude vous demande le chemin. Les notes arrivent dans le sous-dossier `yt-transcribe`.

## Utilisation

Demandez-le simplement, par exemple « transcris cette vidéo dans Lokus : <url> », ou
tapez `/yt-lokus:yt-lokus <url>`.

Une vidéo déjà transcrite est signalée avant d'en refaire une, et une note existante n'est jamais écrasée.

## Limites

- Une vidéo sans sous-titres, même automatiques, ne peut pas être transcrite : le plugin ne fait pas de reconnaissance vocale
- Les sous-titres automatiques déforment les noms propres : Claude liste les corrections évidentes dans un encadré
- Les notes sont écrites pour Lokus, sans frontmatter, et le texte généré est en français

## Licence

[MIT](LICENSE)
