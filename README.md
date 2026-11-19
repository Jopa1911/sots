# AI agent za vežbanje zahtevnih razgovora

**Projekat 6 — AI konverzacioni agent za simulaciju razgovora u obrazovnom okruženju**

**Trenutna faza:** 🟡 Faza 2 — prototip · **Istraživački dnevnik:** [DNEVNIK.md](DNEVNIK.md) · **Dijagram:** [DIJAGRAM.drawio.svg](DIJAGRAM.drawio.svg) · **Rad:** [PDF](docs/rad/projekat6_rad.pdf)

Prototip ima dve uloge: **simulator ljutog roditelja**, koji odgovara onoliko grubo koliko je trenutno ljut, i **evaluator**, koji posle razgovora ocenjuje kako je nastavnik reagovao. Razgovor se vodi na engleskom, kao i skup ESConv na kome se zasniva. Bez jezičkog modela sve radi i bez interneta (šabloni i pravila).

## Pokretanje

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash); Linux i macOS: source .venv/bin/activate
pip install -r requirements.txt

streamlit run app.py               # web aplikacija: razgovor, izveštaj, kartice, alternative
python -m src.cli                  # razgovor u terminalu (--debug prikazuje vanila rečenicu i nivo)
python -m src.simulate             # simulirani nastavnici: empatičan, odbrambeni, brzoplet, van teme
python -m src.alternatives         # isti potez roditelja na nivoima ljutnje 1–5
python -m pytest                   # testovi
```

Jezički model je opcion: kopirati `.env.example` u `.env` i upisati provajdera, model i ključ. Podaci i modeli prave se skriptama iz `data/`:

```bash
python data/download_esconv.py && python data/build_esconv_resources.py && python data/train_strategy_classifier.py
python data/download_rewrite_datasets.py && python data/build_rewrite_pairs.py
python data/train_rewriter.py --dry-run   # model za grube rečenice (za obuku: GPU i requirements-optional.txt)
```

## Struktura repozitorijuma

```
├── README.md
├── DNEVNIK.md            istraživački dnevnik projekta
├── DIJAGRAM.drawio.svg   dijagram simulatora (draw.io): od vanila rečenice do ljute
├── app.py                web aplikacija (Streamlit)
├── src/                  kod agenta: tok, ljutnja, generisanje, merenje, fokus, evaluator
├── content/              scenariji, obrazac razgovora, kartice, parovi vanila → grubo, rečnik ljutnje
├── data/                 skripte za preuzimanje i pripremu podataka i obuku modela
├── evaluation/           upitnici i analiza pilot-studije
├── tests/                automatski testovi
└── docs/
    ├── rad/              glavni dokument: motivacija, srodna istraživanja, rešenje, rezultati
    └── dijagrami/        slike za dnevnik i rad (i skripte koje ih prave)
```
