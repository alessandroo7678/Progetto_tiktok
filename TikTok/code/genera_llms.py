"""Genera un llms.txt per ogni cervello del vault (TikTok/llms.txt, ...).

llms.txt è l'indice-porta per le AI ed è DERIVATO: questo script lo riscrive da capo ogni volta,
non va modificato a mano. Title e summary vengono solo dal frontmatter delle note; gli _index
(anch'essi derivati) non sono elencati; sources/ e workspace/ sono esclusi.

Un cervello è una cartella nella radice del vault che contiene self/. L'intestazione viene
dall'hub del cervello: la nota in self/ con tag "hub". Se l'hub non c'è ancora, l'intestazione
è solo il nome della cartella.

Uso, dalla cartella TikTok:
  python3 code/genera_llms.py              rigenera tutti i cervelli del vault
  python3 code/genera_llms.py ../<altro-cervello>  rigenera solo quel cervello
Exit code 1 se qualche nota (hub compreso) non ha title o summary nel frontmatter.
"""
import json
import os
import re
import sys

VAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FOLDERS = ["self", "areas", "projects", "concepts", "docs", "entities", "data", "code", "outputs"]


def frontmatter(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else ""


def field(fm, key):
    """Valore scalare di una chiave del frontmatter, senza virgolette YAML."""
    m = re.search(rf"^{key}:[ \t]*(.*?)[ \t]*$", fm, re.M)
    if not m or not m.group(1):
        return None
    value = m.group(1)
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)  # stesse sequenze di escape (\" e \\) del double-quoted YAML
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def tags(fm):
    raw = field(fm, "tags") or ""
    return [t.strip().strip('"') for t in raw.strip("[]").split(",")]


def notes_in(brain, folder):
    path = os.path.join(brain, folder)
    if not os.path.isdir(path):
        return []
    return sorted(n for n in os.listdir(path) if n.endswith(".md") and not n.startswith("_index"))


def generate(brain):
    name = os.path.basename(brain)
    missing = []

    hub = next((n for n in notes_in(brain, "self") if "hub" in tags(frontmatter(os.path.join(brain, "self", n)))), None)
    if hub:
        hub_fm = frontmatter(os.path.join(brain, "self", hub))
        title, summary = field(hub_fm, "title"), field(hub_fm, "summary")
        if not title or not summary:
            missing.append(f"self/{hub}")
        lines = [f"# {title or name}", "", f"> {summary or ''}".rstrip(), ""]
    else:
        lines = [f"# {name}", ""]

    lines += [f"<!-- File derivato: generato da TikTok/code/genera_llms.py. Non modificarlo a mano, rigeneralo. -->", ""]

    count = 0
    for folder in FOLDERS:
        lines += [f"## {folder}", ""]
        names = notes_in(brain, folder)
        for n in names:
            s = field(frontmatter(os.path.join(brain, folder, n)), "summary")
            if s is None:
                missing.append(f"{folder}/{n}")
            lines.append(f"- [[{n[:-3]}]] -- {s or ''}".rstrip())
        count += len(names)
        if names:
            lines.append("")

    with open(os.path.join(brain, "llms.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")

    note = "" if hub else " (nessun hub in self/: intestazione = nome cartella)"
    print(f"{name}/llms.txt: {count} note in {len(FOLDERS)} cartelle{note}")
    if missing:
        print(f"  frontmatter senza title/summary (riga lasciata vuota, niente inventato): {', '.join(missing)}")
    return not missing


if len(sys.argv) > 1:
    brains = [os.path.abspath(a) for a in sys.argv[1:]]
else:
    brains = sorted(os.path.join(VAULT, d) for d in os.listdir(VAULT)
                    if not d.startswith(".") and os.path.isdir(os.path.join(VAULT, d, "self")))

results = [generate(b) for b in brains]
sys.exit(0 if all(results) else 1)
