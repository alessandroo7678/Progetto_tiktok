"""Genera _showcase/showcase.md per ogni cervello del vault: la fotografia da demo.

showcase.md è DERIVATO: questo script lo riscrive da capo ogni volta, non va modificato a mano.
Conta le note delle cartelle del cervello (salta sources/ e workspace/), i wikilink che le
collegano e le componenti connesse del grafo, con le stesse regole di gate_qualita.py.
Titoli e summary vengono solo dal frontmatter.

Uso, dalla cartella TikTok:
  python3 code/genera_showcase.py              rigenera tutti i cervelli del vault
  python3 code/genera_showcase.py ../<altro-cervello>  rigenera solo quel cervello
"""
import datetime
import json
import os
import re
import sys
from collections import defaultdict

VAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FOLDERS = ["self", "areas", "projects", "concepts", "docs", "entities", "data", "code", "outputs"]
SKIPPED = ["sources", "workspace"]

LINK_RE = re.compile(r"!?\[\[([^\]]+)\]\]")
FENCE_RE = re.compile(r"```.*?```", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def frontmatter(text):
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else ""


def field(fm, key):
    """Valore scalare di una chiave del frontmatter, senza virgolette YAML."""
    m = re.search(rf"^{key}:[ \t]*(.*?)[ \t]*$", fm, re.M)
    if not m or not m.group(1):
        return None
    value = m.group(1)
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def link_targets(text):
    """Bersagli unici dei wikilink, come in gate_qualita.py."""
    text = INLINE_CODE_RE.sub("", FENCE_RE.sub("", text))
    targets = set()
    for raw in LINK_RE.findall(text):
        target = raw.split("|")[0].split("#")[0].strip()
        if target:
            targets.add(os.path.basename(target).removesuffix(".md"))
    return targets


def components(nodes, edges):
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    seen, count = set(), 0
    for start in nodes:
        if start in seen:
            continue
        count += 1
        stack = [start]
        seen.add(start)
        while stack:
            for m in adj[stack.pop()] - seen:
                seen.add(m)
                stack.append(m)
    return count


def generate(brain):
    name = os.path.basename(brain)
    notes = {}  # slug -> (cartella, testo)
    for folder in FOLDERS:
        path = os.path.join(brain, folder)
        if os.path.isdir(path):
            for n in sorted(os.listdir(path)):
                if n.endswith(".md"):
                    notes[n[:-3]] = (folder, open(os.path.join(path, n), encoding="utf-8").read())

    edges = set()
    out_per_folder = defaultdict(int)
    for slug, (folder, text) in notes.items():
        for t in link_targets(text) - {slug}:
            if t in notes:
                edges.add((slug, t))
                out_per_folder[folder] += 1
    n_comp = components(sorted(notes), edges)

    hub = next((s for s, (f, t) in notes.items() if f == "self" and not s.startswith("_index")
                and "hub" in (field(frontmatter(t), "tags") or "")), None)
    title = field(frontmatter(notes[hub][1]), "title") if hub else None
    hub_summary = field(frontmatter(notes[hub][1]), "summary") if hub else None
    title = title or name

    total = len(notes)
    indexes = sum(1 for s in notes if s.startswith("_index"))
    today = datetime.date.today().isoformat()
    status = "tutto collegato" if n_comp == 1 else ("nessuna nota" if n_comp == 0 else "grafo diviso in isole")

    lines = [
        "---",
        f'title: "Showcase — {title}"',
        f'summary: "Fotografia derivata del cervello {name}: note, wikilink e connessione del grafo."',
        "tags: [_showcase, derivato]",
        "status: derivato",
        f"created: {today}",
        f"updated: {today}",
        "---",
        "",
        f"# Showcase — {title}",
        "",
    ]
    if hub_summary:
        lines += [f"> {hub_summary}", ""]
    lines += [
        f"<!-- File derivato: generato da TikTok/code/genera_showcase.py il {today}. Non modificarlo a mano, rigeneralo. -->",
        "",
        "## In numeri",
        "",
        "| | |",
        "|---|---|",
        f"| **Note** | {total} ({total - indexes} di contenuto + {indexes} indici) |",
        f"| **Wikilink** | {len(edges)} collegamenti unici nota → nota |",
        f"| **Componenti connesse** | {n_comp} ({status}) |",
        "",
        f"Cartelle contate: {', '.join(FOLDERS)}. Saltate: {', '.join(SKIPPED)}.",
        "",
        "## Note per cartella",
        "",
        "| Cartella | Note | di cui contenuto | Wikilink in uscita |",
        "|---|---:|---:|---:|",
    ]
    for folder in FOLDERS:
        in_folder = [s for s, (f, _) in notes.items() if f == folder]
        content = sum(1 for s in in_folder if not s.startswith("_index"))
        lines.append(f"| {folder} | {len(in_folder)} | {content} | {out_per_folder[folder]} |")
    lines += [f"| **Totale** | **{total}** | **{total - indexes}** | **{len(edges)}** |", "", "## Hub", ""]

    for folder in FOLDERS:
        idx = f"_index-{folder}"
        if idx in notes:
            lines.append(f"- [[{idx}]] -- {field(frontmatter(notes[idx][1]), 'summary') or ''}".rstrip())
        else:
            lines.append(f"- {folder}: indice non ancora generato")

    out_dir = os.path.join(brain, "_showcase")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "showcase.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{name}/_showcase/showcase.md: {total} note, {len(edges)} wikilink, {n_comp} componenti")


if len(sys.argv) > 1:
    brains = [os.path.abspath(a) for a in sys.argv[1:]]
else:
    brains = sorted(os.path.join(VAULT, d) for d in os.listdir(VAULT)
                    if not d.startswith(".") and os.path.isdir(os.path.join(VAULT, d, "self")))
for b in brains:
    generate(b)
