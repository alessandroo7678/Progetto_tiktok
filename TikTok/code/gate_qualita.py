"""Gate di qualità del cervello.

Controlla ogni nota delle cartelle del cervello, sottocartelle comprese (salta solo
_showcase/ e i _templates/, che sono modelli pieni di segnaposto) contro sei regole
e stampa il referto raggruppato per regola.
Uso, dalla cartella TikTok:  python3 code/gate_qualita.py [cartella-radice] [--dettagli]
Exit code 0 se tutto è in regola, 1 se ci sono errori.
Regola 3: l'_index di una cartella senza note è esentato finché la cartella resta vuota,
e le note di self/ (l'hub) lo sono finché il resto del cervello non ha note di contenuto;
--dettagli mostra quali indici sono in attesa anche quando l'esito è OK.
"""
import os
import re
import sys
from collections import defaultdict

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
ROOT = ARGS[0] if ARGS else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"_showcase"}             # fotografia derivata del cervello
SKIP_DIRS = {"_templates"}       # modelli da copiare, non note: in qualunque cartella
REQUIRED = ["title", "summary", "tags", "status", "created", "updated"]
MAX_BODY_LINES = 300
MIN_LINKS = 3

RULES = {
    1: "Frontmatter completo (title, summary, tags, status, created, updated)",
    2: f"Massimo {MAX_BODY_LINES} righe di corpo",
    3: f"Almeno {MIN_LINKS} wikilink in uscita verso note esistenti (bersagli unici, _index esclusi)",
    4: "Zero link rotti",
    5: "Zero orfani (almeno 1 link in entrata; _index esentati)",
    6: "Una sola componente connessa",
}

LINK_RE = re.compile(r"!?\[\[([^\]]+)\]\]")
FENCE_RE = re.compile(r"```.*?```", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def is_index(slug):
    return slug.startswith("_index")


def split_frontmatter(text):
    """Restituisce (righe del frontmatter, corpo) oppure (None, testo) se manca."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return None, text


def frontmatter_keys(fm_lines):
    """Chiavi di primo livello con un valore non vuoto (inline o come lista su righe seguenti)."""
    keys = {}
    current = None
    for line in fm_lines:
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            current = m.group(1)
            keys[current] = m.group(2).strip() not in ("", '""', "''", "[]")
        elif current and line.strip().startswith("- "):
            keys[current] = True
    return {k for k, filled in keys.items() if filled}


def link_targets(text):
    """Bersagli unici dei wikilink, normalizzati: niente alias, heading o percorso."""
    text = INLINE_CODE_RE.sub("", FENCE_RE.sub("", text))
    targets = set()
    for raw in LINK_RE.findall(text):
        target = raw.split("|")[0].split("#")[0].strip()
        if target:
            targets.add(os.path.basename(target).removesuffix(".md"))
    return targets


# ---------- raccolta ----------
all_slugs = {}   # tutte le note del vault, per sapere se un bersaglio esiste davvero
notes = {}       # solo le note da controllare: slug -> percorso relativo
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if not d.startswith(".")]
    for name in filenames:
        if not name.endswith(".md"):
            continue
        path = os.path.join(dirpath, name)
        rel = os.path.relpath(path, ROOT)
        slug = name[:-3]
        all_slugs[slug] = rel
        parts = rel.split(os.sep)
        if parts[0] not in SKIP and os.sep in rel and not SKIP_DIRS & set(parts[:-1]):
            notes[slug] = rel

errors = defaultdict(list)   # regola -> [(nota, dettaglio)]
outgoing = {}
waiting = []                 # _index di cartelle vuote, esentati dalla regola 3
content_count = defaultdict(int)
for slug, rel in notes.items():
    if not is_index(slug):
        content_count[rel.split(os.sep)[0]] += 1

for slug, rel in sorted(notes.items()):
    text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    fm, body = split_frontmatter(text)

    # Regola 1
    if fm is None:
        errors[1].append((rel, "frontmatter assente"))
    else:
        missing = [k for k in REQUIRED if k not in frontmatter_keys(fm)]
        if missing:
            errors[1].append((rel, "mancano o vuoti: " + ", ".join(missing)))

    # Regola 2
    body_lines = len(body.strip("\n").split("\n")) if body.strip() else 0
    if body_lines > MAX_BODY_LINES:
        errors[2].append((rel, f"{body_lines} righe di corpo"))

    targets = link_targets(text) - {slug}
    outgoing[slug] = targets

    # Regola 4
    broken = sorted(t for t in targets if t not in all_slugs)
    for t in broken:
        errors[4].append((rel, f"[[{t}]] non esiste"))

    # Regola 3. Due esenzioni, entrambe finiscono da sole:
    # l'_index di una cartella che non ha ancora note, finché la cartella resta vuota;
    # l'hub in self/, finché fuori da self/ non c'è nessuna nota di contenuto da collegare.
    folder = rel.split(os.sep)[0]
    brain_empty = all(c == 0 for f, c in content_count.items() if f != "self")
    if (is_index(slug) and content_count[folder] == 0) or (folder == "self" and brain_empty):
        waiting.append(rel)
    else:
        valid = {t for t in targets if t in all_slugs and not is_index(t)}
        if len(valid) < MIN_LINKS:
            errors[3].append((rel, f"{len(valid)} bersagli validi su {MIN_LINKS} richiesti"))

# Regola 5
inbound = defaultdict(set)
for src, targets in outgoing.items():
    for t in targets:
        if t in notes:
            inbound[t].add(src)
for slug, rel in sorted(notes.items()):
    if not is_index(slug) and not inbound[slug]:
        errors[5].append((rel, "nessun link in entrata"))

# Regola 6: componenti connesse sul grafo non orientato delle note controllate
adj = defaultdict(set)
for src, targets in outgoing.items():
    for t in targets:
        if t in notes:
            adj[src].add(t)
            adj[t].add(src)
seen, components = set(), []
for start in sorted(notes):
    if start in seen:
        continue
    comp, stack = [], [start]
    seen.add(start)
    while stack:
        n = stack.pop()
        comp.append(n)
        for m in adj[n] - seen:
            seen.add(m)
            stack.append(m)
    components.append(sorted(comp))
if len(components) > 1:
    components.sort(key=len, reverse=True)
    for i, comp in enumerate(components[1:], start=2):
        errors[6].append((f"isola {i} ({len(comp)} note)", ", ".join(comp)))
    errors[6].insert(0, (f"grappolo principale ({len(components[0])} note)", f"{len(components)} componenti in totale"))

# ---------- referto ----------
# la prima riga della regola 6 descrive il grappolo principale, non è un errore
total = sum(len(v) for v in errors.values()) - (1 if errors.get(6) else 0)

def print_waiting():
    if waiting:
        print(f"In attesa di contenuto (regola 3 sospesa finché la cartella è vuota): {', '.join(sorted(waiting))}")

if total == 0:
    print("OK, 0 errori")
    if "--dettagli" in sys.argv:
        print_waiting()
    sys.exit(0)

print(f"Gate di qualità: {total} errori su {len(notes)} note controllate (saltate: {', '.join(sorted(SKIP | SKIP_DIRS))})\n")
for rule, title in RULES.items():
    items = errors.get(rule, [])
    count = len(items) - (1 if rule == 6 and items else 0)
    print(f"## Regola {rule}: {title}: {'OK' if not items else f'{count} errori'}")
    for note, detail in items:
        print(f"  - {note}: {detail}")
    print()
print_waiting()
sys.exit(1)
