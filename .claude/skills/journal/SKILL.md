---
name: journal
description: Diario di lavoro del cervello TikTok (memoria dinamica agganciata alle note statiche). Tre comandi. "buongiorno" controlla che la sessione precedente sia stata chiusa e che i punti aperti lo siano ancora, chiede conferma prima di sistemare eventuali buchi, poi dà il briefing. "chiudi sessione" scrive la nota della sessione in workspace/journal/sessions/. "fine giornata" fonde le sessioni del giorno nel daily in workspace/journal/daily/. Usala quando l'utente dice buongiorno, chiudi sessione, fine giornata, o invoca /journal.
---

# Journal: la memoria dinamica del cervello

Il cervello TikTok ha due strati di memoria:
- **Statica:** le note delle entità vere (account, persone, format, progetti, dati, concetti). Vivono in `TikTok/` e cambiano di rado.
- **Dinamica:** il diario di lavoro, in `TikTok/workspace/journal/`. Ogni sessione e ogni giornata lasciano una nota che si **aggancia sempre** alle note statiche con i `[[wikilink]]`. Mai una nota di diario sciolta nel vuoto.

## Dove stanno le cose

Tutti i percorsi partono dalla radice del progetto `Progetto_tiktok/`.

| Cosa | Percorso |
|---|---|
| Indice del cervello | `TikTok/llms.txt` (derivato: va rigenerato, non modificato a mano) |
| Note di sessione | `TikTok/workspace/journal/sessions/sessione-YYYY-MM-DD.md` |
| Note di giornata | `TikTok/workspace/journal/daily/YYYY-MM-DD.md` |
| Template sessione | `TikTok/workspace/journal/_templates/template-sessione.md` |
| Template daily | `TikTok/workspace/journal/_templates/template-daily.md` |

Le entità a cui agganciarsi sono quelle elencate in `llms.txt`, cioè le note delle cartelle `self/`, `areas/`, `projects/`, `concepts/`, `docs/`, `entities/`, `data/`, `code/`, `outputs/`. Finché il cervello ha solo l'hub, aggancia `[[cervello]]` e `[[canon]]`.

## Regole valide per tutti e tre i comandi

1. **Data di oggi:** ricavala con `date +%F`. Le date sono sempre `YYYY-MM-DD`, mai relative ("ieri", "oggi" non vanno nelle note).
2. **Indice aggiornato:** prima di leggere `llms.txt`, rigeneralo con `python3 code/genera_llms.py` lanciato da `TikTok/`.
3. **Niente entità inventate:** ogni `[[wikilink]]` deve puntare a una nota che esiste già. Prima di scrivere, verifica ogni slug con `ls TikTok/*/<slug>.md`.
4. **Agganci:** ogni nota di diario ha almeno 3 wikilink a note esistenti (lo chiede il gate), e almeno uno va a un'entità statica reale (non solo ad altre note di diario). Se non c'è niente da agganciare, **chiedi all'utente** a quale nota collegarla e non scrivere finché non risponde.
5. **Conferma prima di scrivere:** "chiudi sessione" e "fine giornata" mostrano prima un riassunto di 3 righe e scrivono solo dopo l'ok dell'utente. "buongiorno" scrive solo per sistemare buchi che l'utente ha approvato.
6. **Stile:** italiano naturale, frasi brevi, niente trattino lungo (usa due punti, virgole o punti).
7. Le note del journal stanno in `workspace/`, che `gate_qualita` e `genera_indici` controllano come il resto del cervello (esclusi solo i `_templates/`). Dopo aver scritto il diario, da `TikTok/` lancia la sequenza di controllo qualità di CLAUDE.md e correggi gli errori.

## 1) "buongiorno": inizio sessione

Di base è solo lettura: **non scrive niente nel cervello**. Scrive solo se i controlli trovano un buco e l'utente conferma di volerlo sistemare.

### Passo A: leggi
1. Rigenera e leggi `TikTok/llms.txt`.
2. Leggi l'ultima nota in `TikTok/workspace/journal/sessions/`, cioè la più recente per nome (`ls TikTok/workspace/journal/sessions/sessione-*.md | sort | tail -1`). Se c'è un daily più recente di quella sessione, leggi anche quello.
3. Se non ci sono ancora note di sessione, dillo, salta i controlli e basa il briefing sulle sezioni "da definire" di `workspace/canon.md` e delle aree.

### Passo B: due controlli
**Controllo 1: la sessione precedente è stata chiusa?**
- Prendi la data dell'ultima nota di sessione e cerca lavoro fatto dopo, senza diario:
  - commit successivi: `git log --since=<data ultima sessione> --name-only` dalla radice del progetto;
  - modifiche non committate: `git status --short`;
  - note del cervello cambiate dopo la nota di sessione: `find TikTok -name "*.md" -newer <nota ultima sessione> -not -path "*/workspace/journal/*"`.
  Escludi i file derivati (`_index-*.md`, `llms.txt`, `_showcase/`): da soli non contano come lavoro.
- Cerca anche i giorni con almeno una sessione ma senza il daily corrispondente in `daily/`.

**Controllo 2: i punti aperti sono ancora aperti?**
- Per ogni voce di `## Aperto` dell'ultima sessione (o dell'ultimo daily), apri la nota statica a cui si riferisce e verifica se il punto risulta ancora da fare.
- Classifica ogni voce come **ancora aperta**, **risolta** (la nota statica ora contiene l'informazione) o **non verificabile** (nessuna nota statica la conferma o la smentisce).

### Passo C: se c'è un problema, fermati e chiedi
Se almeno un controllo trova qualcosa (lavoro non registrato, daily mancante, voci risolte o non verificabili):
1. **Non dare ancora il briefing.** Mostra prima all'utente un breve resoconto dei problemi:
   - quali file o commit non sono coperti da una sessione, con le date;
   - quali giorni non hanno il daily;
   - quali voci aperte risultano risolte e in quale nota, e quali non sono verificabili.
2. Proponi come sistemare ogni buco e **aspetta la conferma dell'utente**. Non scrivere niente prima del suo ok.
3. Solo dopo l'ok, sistema quello che l'utente ha approvato:
   - **lavoro non registrato:** segui il flusso di "chiudi sessione" usando come data quella del lavoro (dalla data dei commit o dei file), non quella di oggi. Il riassunto di 3 righe di quel flusso vale come conferma;
   - **daily mancante:** segui il flusso di "fine giornata" per quella data;
   - **voci risolte:** non modificare le vecchie note di sessione, perché sono la storia. Toglile dal briefing e annotale come chiuse nella prossima "chiudi sessione";
   - **voci non verificabili:** chiedi all'utente se sono ancora aperte e riportale nel briefing secondo la sua risposta.
4. Se l'utente non conferma, non toccare niente: dai il briefing segnalando che i buchi restano aperti.

Se i controlli non trovano niente, dillo in una riga e passa al briefing.

### Passo D: briefing
Rispondi con un **briefing di 5 righe**:
- dove eravamo rimasti;
- cosa è ancora aperto (solo le voci confermate come aperte nel passo B o C);
- cosa conviene affrontare oggi, in ordine di priorità (2 o 3 righe).
Cita le note con il loro nome, così l'utente sa da dove viene ogni punto.

## 2) "chiudi sessione": fine sessione

1. Ricostruisci cosa è stato fatto in questa sessione da tre fonti:
   - la conversazione corrente;
   - `git status` e `git diff --stat` dalla radice del progetto, per vedere le note toccate;
   - `git log --since=<data di oggi> --name-only` per i commit di oggi.
2. Mostra all'utente **3 righe**: cosa abbiamo fatto, cosa abbiamo deciso, cosa resta aperto. **Aspetta l'ok.** Se l'utente corregge, aggiorna e ripresenta.
3. Dopo l'ok, scrivi la nota partendo da `_templates/template-sessione.md`:
   - **File:** `TikTok/workspace/journal/sessions/sessione-<data>.md`. Se esiste già una sessione con quella data, usa `sessione-<data>-2.md`, poi `-3`, e così via. Non sovrascrivere mai una sessione esistente.
   - **Frontmatter:** `title`; `summary` di **una sola frase**; `tags: [workspace, type/session]` con `workspace` per primo; `status: done`; `created` e `updated` con la data di oggi; `related` su **una riga** con i wikilink tra virgolette a tutte le note toccate.
   - **Corpo**, tre sezioni brevi:
     - `## Fatto`: cosa abbiamo concluso;
     - `## Deciso`: le scelte prese e il perché;
     - `## Aperto`: cosa resta in sospeso.
   - Nel corpo, aggancia con i `[[wikilink]]` le entità vere toccate (account, persone, format, progetti, dati).
4. Togli dal file tutti i segnaposto `{{...}}` del template e controlla le regole 3 e 4.
5. Conferma all'utente il percorso del file scritto.

## 3) "fine giornata": riassunto di giornata

1. Leggi **tutte** le note `TikTok/workspace/journal/sessions/sessione-<data di oggi>*.md`. Se non ce n'è nessuna, dillo e proponi di fare prima "chiudi sessione".
2. Mostra all'utente **3 righe** su cosa è successo oggi in totale. **Aspetta l'ok.**
3. Dopo l'ok, scrivi il daily partendo da `_templates/template-daily.md`:
   - **File:** `TikTok/workspace/journal/daily/<data>.md`. Se esiste già, aggiornalo (cambia `updated`, fondi le nuove sessioni) invece di crearne un secondo.
   - **Frontmatter:** come la sessione, ma `tags: [workspace, type/daily]`; `related` su una riga con i wikilink a **tutte** le sessioni del giorno più le entità principali toccate.
   - **Corpo:** una sintesi unica in `## Fatto`, `## Deciso`, `## Aperto`, che fonde le sessioni **senza ripeterle riga per riga**. In `## Aperto` togli le voci aperte in una sessione e chiuse in una successiva.
   - In fondo, `## Sessioni` con un wikilink per ogni nota di sessione del giorno.
4. Togli i segnaposto `{{...}}`, controlla le regole 3 e 4 e conferma il percorso del file.
