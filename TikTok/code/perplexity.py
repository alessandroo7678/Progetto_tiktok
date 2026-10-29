"""Collegamento a Perplexity: cerca sul web e restituisce risposta + fonti.

Serve a scovare notizie fresche per il daily report. Usa l'API Sonar di Perplexity
con la sola libreria standard di Python, niente da installare.
La chiave si legge da PERPLEXITY_API_KEY nell'ambiente oppure da env/.env alla radice
del vault (riga PERPLEXITY_API_KEY=pplx-...). Mai scriverla nelle note.

Uso, dalla cartella TikTok:
  python3 code/perplexity.py "notizie TikTok di oggi"
  python3 code/perplexity.py "trend TikTok Italia" --recency day --modello sonar-pro
  python3 code/perplexity.py "..." --json        risposta grezza in JSON
Da Python:  from perplexity import cerca  →  cerca("domanda", recency="day")
Exit code 0 se la ricerca riesce, 1 se l'API risponde con un errore, 2 se manca la chiave.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

VAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE = os.path.join(VAULT, "env", ".env")
API_URL = "https://api.perplexity.ai/chat/completions"
RECENCY = ["hour", "day", "week", "month", "year"]
SYSTEM = ("Rispondi in italiano, in modo conciso e fattuale. "
          "Riporta solo fatti presenti nelle fonti, con date assolute. Non inventare.")


class ChiaveMancante(Exception):
    pass


def api_key():
    """Chiave dall'ambiente, altrimenti da env/.env."""
    key = os.environ.get("PERPLEXITY_API_KEY", "").strip()
    if key:
        return key
    if os.path.isfile(ENV_FILE):
        for line in open(ENV_FILE, encoding="utf-8"):
            name, _, value = line.strip().partition("=")
            if name.strip().removeprefix("export ").strip() == "PERPLEXITY_API_KEY":
                key = value.strip().strip('"').strip("'")
                if key:
                    return key
    raise ChiaveMancante(f"Manca PERPLEXITY_API_KEY: aggiungila in {ENV_FILE}")


def cerca(domanda, recency=None, modello="sonar", domini=None, sistema=SYSTEM, grezzo=False):
    """Una ricerca. Restituisce {"risposta", "fonti": [{"titolo", "url", "data"}], "modello"}."""
    body = {"model": modello,
            "messages": [{"role": "system", "content": sistema},
                         {"role": "user", "content": domanda}]}
    if recency:
        body["search_recency_filter"] = recency
    if domini:
        body["search_domain_filter"] = domini
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {api_key()}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    if grezzo:
        return data

    # search_results ha titolo e data; citations (solo URL) è il ripiego dei modelli più vecchi
    fonti = [{"titolo": s.get("title") or s.get("url"), "url": s.get("url"), "data": s.get("date")}
             for s in data.get("search_results") or []]
    if not fonti:
        fonti = [{"titolo": u, "url": u, "data": None} for u in data.get("citations") or []]
    return {"risposta": data["choices"][0]["message"]["content"].strip(),
            "fonti": fonti,
            "modello": data.get("model", modello)}


def markdown(risultato):
    lines = [risultato["risposta"], "", "## Fonti", ""]
    for i, f in enumerate(risultato["fonti"], start=1):
        data = f" ({f['data']})" if f.get("data") else ""
        lines.append(f"{i}. [{f['titolo']}]({f['url']}){data}")
    if not risultato["fonti"]:
        lines.append("Nessuna fonte restituita.")
    return "\n".join(lines)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Ricerca web con Perplexity.")
    p.add_argument("domanda")
    p.add_argument("--recency", choices=RECENCY, help="solo risultati recenti (hour, day, week, month, year)")
    p.add_argument("--modello", default="sonar", help="sonar (default), sonar-pro, sonar-reasoning-pro…")
    p.add_argument("--dominio", action="append", dest="domini", help="limita a un dominio; ripetibile")
    p.add_argument("--json", action="store_true", help="stampa la risposta grezza dell'API")
    a = p.parse_args()
    try:
        out = cerca(a.domanda, a.recency, a.modello, a.domini, grezzo=a.json)
    except ChiaveMancante as e:
        print(e, file=sys.stderr)
        sys.exit(2)
    except urllib.error.HTTPError as e:
        print(f"Errore API {e.code}: {e.read().decode(errors='replace')}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(out, ensure_ascii=False, indent=2) if a.json else markdown(out))
