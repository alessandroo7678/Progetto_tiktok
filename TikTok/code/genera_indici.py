import os, re, sys, glob, datetime
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = datetime.date.today().isoformat()
ORDER = ["self","areas","projects","sources","concepts","docs","entities","data","code","outputs","workspace"]
# Reparti a cui la cartella appartiene davvero: nessun link di riempimento.
# Quando nasce una nuova nota area-*, aggiungila alle cartelle che le appartengono.
# Un indice raggiunge i 3 link validi grazie alle note che elenca; finché la cartella
# è vuota, il gate lo esenta dalla regola 3 (vedi gate_qualita.py).
INFO = {
 "self":      ("Identità, obiettivi e hub centrale del cervello.", ["area-satira", "area-produzione"]),
 "areas":     ("Note-mappa dei reparti: da qui si scende alle note di dettaglio.", []),
 "projects":  ("Progetti dell'account: serie, campagne, esperimenti.", []),
 "sources":   ("Materiale originale e grezzo da cui nasce il canon.", ["canon", "area-produzione"]),
 "concepts":  ("Concetti e regole ricorrenti dell'account.", []),
 "docs":      ("Procedure e checklist operative.", []),
 "entities":  ("Account, persone, format, strumenti e piattaforme.", ["area-satira"]),
 "data":      ("Dati strutturati: metriche, calendari, numeri.", []),
 "code":      ("Script del cervello. Dalla cartella TikTok: `python3 code/genera_indici.py` rigenera gli indici, `python3 code/gate_qualita.py` controlla il cervello, `python3 code/genera_llms.py` rigenera il llms.txt di ogni cervello, `python3 code/genera_showcase.py` rigenera `_showcase/showcase.md`, `python3 code/perplexity.py \"domanda\" --recency day` cerca notizie sul web con Perplexity (chiave in `env/.env`). `python3 code/analizza_video.py` trascrive e scompone in fotogrammi i video di `sources/esempi-video/`.", ["area-produzione"]),
 "outputs":   ("Deliverable: video, script, caption pronti da pubblicare.", ["area-produzione"]),
 "workspace": ("File di lavoro e bozze non ancora divise in note.", []),
}
GROUP = {"cliente":"Clienti","persona":"Persone","prodotto":"Prodotti","strumento":"Strumenti",
         "area":"Reparti","concetto":"Concetti","procedura":"Procedure","progetto":"Progetti","output":"Deliverable"}

def fm_field(text, key):
    m = re.search(rf'^{key}: "?(.*?)"?$', text, re.M)
    return m.group(1) if m else ""

for i, folder in enumerate(ORDER):
    prev_i, next_i = f"_index-{ORDER[i-1]}", f"_index-{ORDER[(i+1) % len(ORDER)]}"
    desc, hubs = INFO[folder]
    # Anche le sottocartelle (script, analisi, journal): ogni nota deve stare in un indice.
    # Le note in una sottocartella si raggruppano sotto il suo percorso.
    notes, sub = [], {}
    for p in sorted(glob.glob(os.path.join(ROOT, folder, "**", "*.md"), recursive=True)):
        slug = os.path.basename(p)[:-3]
        if slug.startswith("_index"): continue
        t = open(p).read()
        notes.append((slug, fm_field(t, "title"), fm_field(t, "summary")))
        d = os.path.relpath(os.path.dirname(p), os.path.join(ROOT, folder))
        if d != ".": sub[slug] = "/".join(d.split(os.sep)[:2])  # al massimo due livelli
    related = ["cervello"] + [h for h in hubs if h != "cervello"] + [prev_i, next_i]
    related = list(dict.fromkeys(related))
    lines = [f"# Indice — {folder}", "", desc, ""]
    if notes:
        lines += [f"## Note ({len(notes)})", ""]
        groups = {}
        for n in notes:
            g = f"`{sub[n[0]]}/`" if n[0] in sub else GROUP.get(n[0].split("-")[0], "Altro")
            groups.setdefault(g, []).append(n)
        for g, items in groups.items():
            if len(groups) > 1: lines += [f"### {g}", ""]
            lines += ["| Nota | Di cosa parla |", "|---|---|"]
            lines += [f"| [[{s}]] | {sm if '{{' not in sm else 'Template: si copia per creare una nota nuova.'} |"
                      for s, _, sm in items]
            lines.append("")
    else:
        lines += ["## Note (0)", "", "Nessuna nota ancora. Quando ne aggiungi una, rilancia `code/genera_indici.py`.", ""]
    lines += ["## Navigazione", f"- Hub centrale → [[cervello]]"]
    lines += [f"- Reparto di riferimento → [[{h}]]" for h in hubs if h != "canon"]
    if "canon" in hubs: lines.append("- Canon di lavoro → [[canon]]")
    lines += [f"- ← [[{prev_i}]] · [[{next_i}]] →", ""]
    rel = ", ".join(f'"[[{r}]]"' for r in related)
    fm = (f'---\ntitle: "Indice — {folder}"\nsummary: "Indice della cartella {folder}: elenca ogni nota per evitare note orfane."\n'
          f'tags: [{folder}, index]\nstatus: attivo\ncreated: 2026-10-28\nupdated: {TODAY}\nrelated: [{rel}]\n---\n\n')
    open(os.path.join(ROOT, folder, f"_index-{folder}.md"), "w").write(fm + "\n".join(lines))
    print(f"_index-{folder}: {len(notes)} note")
