# Progetto_tiktok — regole del cervello

Vault Obsidian. Il cervello vive in `TikTok/` (una cartella con `self/` = un cervello; se ne possono aggiungere altri accanto). Struttura e regole ricalcano il Cervello VideoMaker (`alessandroo7678/Cervello`).

## Le 11 cartelle
| Cartella | Cosa contiene | Prefisso nota |
|---|---|---|
| `self/` | hub centrale (`cervello.md`, tag `hub`) | — |
| `areas/` | note-mappa dei reparti | `area-` |
| `projects/` | serie, campagne, esperimenti | `progetto-` |
| `sources/` | materiale grezzo da cui nasce il canon (analisi degli esempi incluse) | libero |
| `concepts/` | concetti e regole ricorrenti | `concetto-` |
| `docs/` | procedure e checklist | `procedura-` |
| `entities/` | persone, account, format, strumenti, prodotti | `persona-`, `strumento-`, `prodotto-`, … |
| `data/` | tabelle e numeri | `dati-` |
| `code/` | script del cervello | — |
| `outputs/` | deliverable e formati | `output-` |
| `workspace/` | canon, script, journal | — |

Derivati, **mai a mano**: `_index-*.md`, `llms.txt`, `_showcase/showcase.md`.

## Nota atomica
- Un solo argomento per nota; nome file = slug kebab-case con prefisso di tipo, senza accenti.
- Corpo breve (max 300 righe), `# Titolo`, sezioni corte, poi `## Collegamenti` con i wikilink.
- I fatti nascono nel `workspace/canon.md` con etichette **[confermato] / [da definire] / [bozza]**, poi si dividono in note.
- Le aree sono mappe: "Torna a [[cervello]]", "In breve", "Note del reparto", "Collegamenti".

## Frontmatter YAML (obbligatorio)
```yaml
---
title: "Titolo leggibile"
summary: "Una sola frase: di cosa parla la nota."
tags: [<cartella>, <tipo>, <tema>, ...]
status: attivo | confermato | bozza | da-definire | completato | done | derivato
created: YYYY-MM-DD
updated: YYYY-MM-DD
related: ["[[slug-1]]", "[[slug-2]]", "[[slug-3]]"]
---
```
- **tags:** primo = nome cartella; secondo = tipo al singolare (`hub`, `progetto`, `concetto`, `procedura`, `persona`, `strumento`, `output`, `dati`…); poi i temi. Tag gerarchici tra virgolette (`"channel/partner"`); journal: `type/session`, `type/daily`.
- **related:** una riga, wikilink tra virgolette, gli stessi della sezione Collegamenti.
- Date sempre assolute.

## Controllo qualità
Dalla cartella `TikTok/`, dopo ogni modifica:
```
python3 code/genera_indici.py && python3 code/genera_llms.py && python3 code/genera_showcase.py && python3 code/gate_qualita.py --dettagli
```
Il gate controlla tutte le note, sottocartelle comprese (esclusi solo `_showcase/` e le cartelle `_templates/`), e richiede: 1) frontmatter completo · 2) max 300 righe di corpo · 3) almeno 3 wikilink in uscita verso note esistenti (indici esclusi) · 4) zero link rotti · 5) zero orfani · 6) grafo in una sola componente. Esenzioni temporanee alla regola 3: indici di cartelle vuote e hub finché il cervello è vuoto.

Quando nasce la prima `area-*`, aggiungila agli hub di `INFO` in `code/genera_indici.py` e alla sezione Reparti di `cervello.md`.

## Ricerca web: Perplexity
- Script: `TikTok/code/perplexity.py` (API Sonar, solo libreria standard). Chiave in `env/.env` come `PERPLEXITY_API_KEY=pplx-...`.
- Uso: `python3 code/perplexity.py "domanda" --recency day` (anche `--modello sonar-pro`, `--dominio sito.it`, `--json`); da Python `from perplexity import cerca`.
- Serve a trovare notizie per il daily report. Ogni fatto preso dal web va riportato con la sua fonte (URL) e la data; quello che non ha fonte non entra nel cervello.

## Regole per l'AI
- Distinguere confermato da idea; non inventare numeri, risultati, date, account.
- Ogni wikilink punta a una nota esistente (verifica con `ls TikTok/*/<slug>.md`).
- Stile: italiano naturale, frasi brevi, niente trattino lungo.
- Segreti solo in `env/.env` (ignorato da git), mai nelle note.
- Diario: skill `journal` (buongiorno, chiudi sessione, fine giornata).
