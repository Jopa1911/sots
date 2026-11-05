# 📓 Dnevnik rada — Projekat 6

**AI konverzacioni agent za simulaciju razgovora u obrazovnom okruženju**

**Trenutna faza:** 🟡 Faza 1 — istraživanje i planiranje

Detaljan opis rešenja, slike i literatura nalaze se u glavnom dokumentu rada: [docs/rad/projekat6_rad.pdf](docs/rad/projekat6_rad.pdf).

## Ključne odluke

| Oblast | Odluka |
|---|---|
| Scenario | Agent igra ljutitog roditelja koji telefonom zove nastavnika zbog jedinice na kontrolnom. |
| Izvor podataka | ESConv kao glavni dataset (8 označenih strategija, intenzitet emocije pre i posle razgovora); EmpatheticDialogues, WASSA-2017 i Conversations Gone Awry kao pomoćni. |
| Obrazovni sadržaj | Po jedna kartica za učenje za svaku strategiju iz ESConv-a, po ciklusu: objašnjenje → primer → pitanje → vežba → povratna informacija. |
| Kontrola ljutnje | Ljutnja je promenljiva 0–10 van jezičkog modela; menja se po pravilima za strategije korisnika, najviše ±2 po potezu. |
| Memorija agenta | Tri sloja: stalna (scenario, persona, pravila), radna (menja se svakog poteza) i trajni zapis (posle razgovora). |
| Evaluacija | Pilot-studija pre–posle: samopouzdanje, realističnost razgovora, upotrebljivost (SUS). |

## Tehnologije

| Komponenta | Izbor |
|---|---|
| Programski jezik | Python |
| Jezički model | LLM preko API-ja |
| Prepoznavanje govora | Whisper |
| Sinteza govora | TTS servis sa srpskim glasom |
| Govorni razgovor u realnom vremenu | Pipecat |
| Interfejs prototipa | Streamlit |
| Rad sa datasetima | Hugging Face `datasets`, ConvoKit |
| Analiza pilot-studije | pandas, SciPy, matplotlib |
| Kartice i logovi | YAML, JSON |

## Dataseti

| Dataset | Uloga | Izvor |
|---|---|---|
| ESConv | strategije, primeri i kontraprimeri | https://github.com/thu-coai/Emotional-Support-Conversation |
| EmpatheticDialogues | izrazi ljutnje za personu roditelja | https://github.com/facebookresearch/EmpatheticDialogues |
| WASSA-2017 Emotion Intensity | kalibracija jačine ljutnje | http://saifmohammad.com/WebPages/EmotionIntensity-SharedTask.html |
| Conversations Gone Awry | obrasci eskalacije | https://convokit.cornell.edu/documentation/awry.html |

Sirovi podaci se ne čuvaju u repozitorijumu, već se preuzimaju skriptama iz foldera `data/`.

## Plan rada

| Faza | Sadržaj | Status |
|---|---|---|
| 1 | Istraživanje i planiranje: dataset, model ljutnje, memorija agenta | 🟡 u toku |
| 2 | Obrazovni sadržaj: kartice za 8 strategija iz ESConv-a i kartica anti-strategija | ⬜ |
| 3 | Prototip (tekst): persona, model ljutnje, klasifikator strategija | ⬜ |
| 4 | Prototip (govor): prepoznavanje i sinteza govora, detekcija kraja govora | ⬜ |
| 5 | Kalibracija: podešavanje Δ vrednosti probnim razgovorima | ⬜ |
| 6 | Pilot-studija: sesije sa učesnicima, upitnici, logovi | ⬜ |
| 7 | Analiza rezultata i pisanje rada | ⬜ |
