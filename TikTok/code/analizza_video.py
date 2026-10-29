"""Analisi dei video di esempio: trascrizione, fotogrammi e ritmo dei tagli.

Serve a estrarre dagli esempi la forma della comunicazione (gancio, ritmo, tono, grafiche),
che poi descriviamo nel canon. Gira tutto in locale: faster-whisper per l'audio, PyAV per
i fotogrammi, yt-dlp per scaricare da link. Installazione una tantum:
  python3 -m pip install --user faster-whisper av yt-dlp pillow

Per ogni video crea sources/esempi-video/_analisi/<nome>/ con:
  analisi-<slug>.md  nota del cervello (frontmatter, scheda, trascrizione con i tempi, collegamenti)
  scheda.json        durata, formato, tagli rilevati, parole al secondo, segmenti della trascrizione
  frames/            un fotogramma ogni --passo secondi, più uno a ogni taglio (temporanei)

I fotogrammi si cancellano a fine analisi per non sprecare spazio: restano il video originale,
la nota e la scheda. Il video originale non viene mai toccato. Con --tieni-frame
restano su disco per guardarli, poi --pulisci li elimina tutti.
La nota è derivata dalla scheda: --note la riscrive per tutti i video senza rifare l'analisi.

Uso, dalla cartella TikTok:
  python3 code/analizza_video.py                     analizza i video nuovi della cartella esempi
  python3 code/analizza_video.py --url https://...   scarica il video nella cartella e lo analizza
  python3 code/analizza_video.py --tieni-frame       come sopra, ma lascia i fotogrammi su disco
  python3 code/analizza_video.py --pulisci           cancella i fotogrammi rimasti, nient'altro
  python3 code/analizza_video.py --note              riscrive le note di analisi dalle schede
  python3 code/analizza_video.py --modello medium --lingua it --passo 1 --rifai
Exit code 0 se tutto riesce, 1 se almeno un video fallisce, 2 se mancano le librerie.
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys
import unicodedata

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARTELLA = os.path.join(VAULT, "sources", "esempi-video")
ANALISI = os.path.join(CARTELLA, "_analisi")
ESTENSIONI = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
SOGLIA_TAGLIO = 30.0  # differenza media tra fotogrammi (0-255) oltre cui conta come taglio
LATO_FRAME = 720      # lato lungo dei fotogrammi salvati, in pixel
COLLEGAMENTI = ["area-produzione", "area-satira", "canon"]  # il primo è il reparto di riferimento


def tempo(s):
    m, s = divmod(s, 60)
    return f"{int(m):02d}:{s:05.2f}"


def scarica(url):
    """Scarica un video con yt-dlp nella cartella esempi e restituisce il percorso."""
    import yt_dlp
    opzioni = {"outtmpl": os.path.join(CARTELLA, "%(uploader)s-%(id)s.%(ext)s"),
               "format": "mp4/best", "quiet": True}
    with yt_dlp.YoutubeDL(opzioni) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


def fotogrammi(percorso, cartella_frames, passo):
    """Salva un frame ogni `passo` secondi e uno a ogni taglio. Restituisce scheda video e tagli."""
    import av
    import numpy as np
    os.makedirs(cartella_frames, exist_ok=True)
    tagli, precedente, prossimo = [], None, 0.0
    with av.open(percorso) as contenitore:
        flusso = contenitore.streams.video[0]
        scheda = {"larghezza": flusso.codec_context.width, "altezza": flusso.codec_context.height,
                  "fps": float(flusso.average_rate or 0)}
        for frame in contenitore.decode(flusso):
            t = float(frame.time or 0)
            piccolo = np.asarray(frame.to_image().convert("L").resize((64, 114)), dtype=np.float32)
            taglio = precedente is not None and np.abs(piccolo - precedente).mean() > SOGLIA_TAGLIO
            precedente = piccolo
            if taglio:
                tagli.append(round(t, 2))
            if t >= prossimo or taglio:
                img = frame.to_image()
                img.thumbnail((LATO_FRAME, LATO_FRAME))
                nome = f"{'taglio' if taglio else 'frame'}-{t:07.2f}s.jpg"
                img.save(os.path.join(cartella_frames, nome), quality=80)
                if t >= prossimo:
                    prossimo += passo
        scheda["durata_s"] = round(t, 2)
    return scheda, tagli


def audio(percorso):
    """Audio mono a 16 kHz in float32, decodificato con PyAV (evita il decoder interno di
    faster-whisper, che non è compatibile con PyAV 19). None se il video è muto."""
    import av
    import numpy as np
    with av.open(percorso) as contenitore:
        if not contenitore.streams.audio:
            return None
        ricampiona = av.AudioResampler(format="flt", layout="mono", rate=16000)
        pezzi = [r.to_ndarray().reshape(-1) for frame in contenitore.decode(audio=0)
                 for r in ricampiona.resample(frame)]
        pezzi += [r.to_ndarray().reshape(-1) for r in ricampiona.resample(None)]
    return np.concatenate(pezzi) if pezzi else None


def trascrivi(percorso, modello, lingua):
    """Trascrizione con faster-whisper. Restituisce (lingua, segmenti)."""
    from faster_whisper import WhisperModel
    campioni = audio(percorso)
    if campioni is None or not len(campioni):
        return None, []
    whisper = WhisperModel(modello, device="cpu", compute_type="int8")
    segmenti, info = whisper.transcribe(campioni, language=lingua, vad_filter=True)
    return info.language, [{"inizio": round(s.start, 2), "fine": round(s.end, 2), "testo": s.text.strip()}
                           for s in segmenti]


def pulisci_frames(uscita):
    """Cancella i fotogrammi di un'analisi. Tocca solo i .jpg di <_analisi>/<nome>/frames/,
    mai il video originale. Restituisce quanti file ha cancellato."""
    cartella = os.path.realpath(os.path.join(uscita, "frames"))
    analisi = os.path.realpath(ANALISI)
    if os.path.dirname(os.path.dirname(cartella)) != analisi or not os.path.isdir(cartella):
        return 0
    cancellati = 0
    for f in os.listdir(cartella):
        if f.lower().endswith(".jpg") and f.startswith(("frame-", "taglio-")):
            os.remove(os.path.join(cartella, f))
            cancellati += 1
    if not os.listdir(cartella):
        os.rmdir(cartella)
    return cancellati


def analizza(percorso, args):
    nome = os.path.splitext(os.path.basename(percorso))[0]
    uscita = os.path.join(ANALISI, nome)
    if os.path.isfile(os.path.join(uscita, "scheda.json")) and not args.rifai:
        print(f"  già analizzato: {nome} (usa --rifai per ripetere)")
        return
    try:
        scrivi_analisi(percorso, nome, uscita, args)
    finally:
        if not args.tieni_frame:
            n = pulisci_frames(uscita)
            print(f"  {nome}: cancellati {n} fotogrammi (il video originale resta)")


def scrivi_analisi(percorso, nome, uscita, args):
    print(f"  {nome}: fotogrammi...")
    scheda, tagli = fotogrammi(percorso, os.path.join(uscita, "frames"), args.passo)
    print(f"  {nome}: trascrizione...")
    lingua, segmenti = trascrivi(percorso, args.modello, args.lingua)
    parole = sum(len(s["testo"].split()) for s in segmenti)
    scheda.update({"file": os.path.basename(percorso), "lingua": lingua, "tagli_s": tagli,
                   "numero_tagli": len(tagli), "parole": parole,
                   "secondi_per_taglio": round(scheda["durata_s"] / (len(tagli) + 1), 2),
                   "parole_al_secondo": round(parole / scheda["durata_s"], 2) if scheda["durata_s"] else 0})
    with open(os.path.join(uscita, "scheda.json"), "w", encoding="utf-8") as f:
        json.dump(scheda, f, ensure_ascii=False, indent=2)
    scheda["analizzato"] = datetime.date.today().isoformat()
    scheda["segmenti"] = segmenti
    with open(os.path.join(uscita, "scheda.json"), "w", encoding="utf-8") as f:
        json.dump(scheda, f, ensure_ascii=False, indent=2)
    scrivi_nota(nome, uscita, scheda)
    print(f"  {nome}: fatto → {os.path.relpath(uscita, VAULT)}")


def slug(nome):
    """Nome del video in kebab-case senza accenti: ssstik.io_123 → ssstik-io-123."""
    testo = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", testo).strip("-")


def scrivi_nota(nome, uscita, scheda):
    """Nota del cervello con scheda e trascrizione: frontmatter e collegamenti come chiede il gate."""
    oggi = datetime.date.today().isoformat()
    sintesi = (f"{scheda['durata_s']} s, {scheda['numero_tagli']} tagli, "
               f"{scheda['parole_al_secondo']} parole al secondo")
    righe = ["---", f'title: "Analisi esempio {slug(nome)}"',
             f'summary: "Trascrizione e ritmo del video di esempio {scheda["file"]}: {sintesi}."',
             "tags: [sources, analisi, esempio-video]", "status: derivato",
             f"created: {scheda.get('analizzato', oggi)}", f"updated: {oggi}",
             "related: [" + ", ".join(f'"[[{c}]]"' for c in COLLEGAMENTI) + "]",
             f'video: "esempi-video/{scheda["file"]}"', "---", "",
             f"# Analisi esempio {slug(nome)}", "",
             f"Torna a [[{COLLEGAMENTI[0]}]]. Nota derivata da `code/analizza_video.py`: "
             "rigenerala con `--note`, non modificarla a mano.", "",
             "## Scheda",
             f"- **Video:** `sources/esempi-video/{scheda['file']}`",
             f"- **Formato:** {scheda['larghezza']}x{scheda['altezza']}, {scheda['fps']:g} fps, lingua {scheda['lingua']}",
             f"- **Ritmo:** {sintesi}, un taglio ogni {scheda['secondi_per_taglio']} s",
             "", "## Trascrizione"]
    righe += [f"- `{tempo(s['inizio'])}` {s['testo']}" for s in scheda.get("segmenti", [])] or ["- (nessun parlato)"]
    righe += ["", "## Collegamenti"] + [f"- [[{c}]]" for c in COLLEGAMENTI]
    with open(os.path.join(uscita, f"analisi-{slug(nome)}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(righe) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Analizza i video di esempio.")
    parser.add_argument("video", nargs="*", help="file da analizzare (default: tutta la cartella esempi)")
    parser.add_argument("--url", action="append", default=[], help="link da scaricare e analizzare")
    parser.add_argument("--modello", default="small", help="modello Whisper: tiny, base, small, medium, large-v3")
    parser.add_argument("--lingua", default=None, help="codice lingua, es. it (default: rilevata)")
    parser.add_argument("--passo", type=float, default=2.0, help="secondi tra un fotogramma e l'altro")
    parser.add_argument("--rifai", action="store_true", help="ripete anche i video già analizzati")
    parser.add_argument("--tieni-frame", action="store_true", help="non cancella i fotogrammi a fine analisi")
    parser.add_argument("--pulisci", action="store_true", help="cancella i fotogrammi rimasti ed esce")
    parser.add_argument("--note", action="store_true", help="riscrive le note dalle schede salvate ed esce")
    args = parser.parse_args()
    if args.note:
        schede = sorted(glob.glob(os.path.join(ANALISI, "*", "scheda.json")))
        for p in schede:
            scrivi_nota(os.path.basename(os.path.dirname(p)), os.path.dirname(p),
                        json.load(open(p, encoding="utf-8")))
        print(f"Riscritte {len(schede)} note di analisi.")
        return 0
    if args.pulisci:
        n = sum(pulisci_frames(os.path.join(ANALISI, d)) for d in sorted(os.listdir(ANALISI))) \
            if os.path.isdir(ANALISI) else 0
        print(f"Cancellati {n} fotogrammi. Video originali, note e schede restano.")
        return 0
    try:
        import av, faster_whisper, numpy, PIL  # noqa: F401
    except ImportError as e:
        print(f"Manca una libreria ({e.name}): python3 -m pip install --user faster-whisper av yt-dlp pillow")
        return 2
    os.makedirs(CARTELLA, exist_ok=True)
    video = list(args.video)
    for url in args.url:
        print(f"Scarico {url}")
        video.append(scarica(url))
    if not video:
        video = sorted(os.path.join(CARTELLA, f) for f in os.listdir(CARTELLA)
                       if os.path.splitext(f)[1].lower() in ESTENSIONI)
    if not video:
        print(f"Nessun video in {os.path.relpath(CARTELLA, VAULT)}")
        return 0
    errori = 0
    for percorso in video:
        try:
            analizza(percorso, args)
        except Exception as e:
            errori += 1
            print(f"  ERRORE su {os.path.basename(percorso)}: {e}")
    print(f"Analizzati {len(video) - errori} video su {len(video)}.")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
