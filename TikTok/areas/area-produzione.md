---
title: "Area produzione"
summary: "Mappa del reparto produzione: dagli esempi analizzati allo script pronto per la voce e il montaggio."
tags: [areas, area, produzione, automazione]
status: attivo
created: 2026-10-28
updated: 2026-10-28
related: ["[[cervello]]", "[[canon]]", "[[area-satira]]"]
---

# Area produzione

Torna a [[cervello]].

## In breve
1. **Esempi:** i video di riferimento stanno in `sources/esempi-video/`. `code/analizza_video.py` li trascrive e ne ricava tagli e ritmo. I fotogrammi si cancellano dopo l'analisi, i video originali restano.
2. **Notizia:** è vera e ha la sua fonte con la data. Si verifica con la ricerca web (`code/perplexity.py`).
3. **Script:** per ogni notizia nascono due file in `workspace/script/`:
   - `<data>-<tema>-script.md`: solo il testo della voce;
   - `<data>-<tema>-schema.md`: blocchi con i tempi e lo schema visivo.
4. **Voce:** [bozza] sintetica, quale non è ancora deciso.
5. **Montaggio e pubblicazione:** [da definire].

## Note del reparto
- Le regole di contenuto stanno in [[area-satira]].

### Esempi analizzati
- [[analisi-ssstik-io-1793199952204]]: meteo satirico su mappa 3D, una sola inquadratura in movimento.
- [[analisi-ssstik-io-1793200639152]]: meteo da TG con battute sui politici e congedo fisso.
- [[analisi-ssstik-io-1793200709975]]: ricetta finto disastro, montaggio serrato.

## Collegamenti
- [[cervello]]
- [[canon]]
- [[area-satira]]
