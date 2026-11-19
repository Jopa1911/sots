# Upitnici za pilot-studiju

Tok jedne sesije (oko 30 minuta): upitnik A → kratko uputstvo → kartice S3, S2 i S6 → dva razgovora sa simulatorom (scenario `bad_grade`, zatim `trip_exclusion`) → upitnici B, C i D. Rezultati simulatora (ukupni poeni, ishod, broj replika) uzimaju se iz izveštaja evaluatora (JSON). Odgovori se unose u `pilot_podaci.csv` (šablon: `pilot_sablon.csv`), a analiza se pokreće sa `python evaluation/analyze_pilot.py evaluation/pilot_podaci.csv`.

Skala za A, B i C: 1 – uopšte se ne slažem, 2 – ne slažem se, 3 – nisam siguran/na, 4 – slažem se, 5 – potpuno se slažem.

## A. Samopouzdanje u razgovoru sa ljutim roditeljem (pre i posle vežbe)

Isti upitnik se popunjava pre prvog i posle drugog razgovora (kolone `pre_se1`–`pre_se6` i `post_se1`–`post_se6`).

1. Mogu da ostanem smiren/a i kada je roditelj ljut.
2. Umem da prepoznam i naglas imenujem emociju roditelja.
3. Umem da ponovim pritužbu roditelja svojim rečima.
4. Znam kada je pravi trenutak da predložim rešenje.
5. Mogu da vratim razgovor na temu kada skrene.
6. Uopšteno, siguran/na sam da mogu uspešno da vodim razgovor sa ljutim roditeljem.

## B. Realističnost simulacije (posle vežbe)

1. Roditelj u simulaciji je zvučao kao pravi ljuti roditelj.
2. Ljutnja roditelja se menjala u skladu sa onim što sam rekao/la.
3. Roditelj je ostao na temi razgovora.
4. Roditelj je bio grub, ali ne uvredljiv preko mere.
5. Povratna informacija evaluatora bila je tačna i korisna.

## C. Upotrebljivost – System Usability Scale (SUS, Brooke, 1996)

Koristi se originalnih deset stavki. Ako učesnici popunjavaju na srpskom, pre studije treba proveriti da li postoji validiran prevod; ispod je radni prevod.

1. I think that I would like to use this system frequently. – Mislim da bih često koristio/la ovaj sistem.
2. I found the system unnecessarily complex. – Sistem mi je bio nepotrebno složen.
3. I thought the system was easy to use. – Sistem je bio lak za korišćenje.
4. I think that I would need the support of a technical person to be able to use this system. – Mislim da bi mi bila potrebna pomoć tehničke osobe da bih koristio/la ovaj sistem.
5. I found the various functions in this system were well integrated. – Funkcije sistema su dobro povezane.
6. I thought there was too much inconsistency in this system. – U sistemu je bilo previše nedoslednosti.
7. I would imagine that most people would learn to use this system very quickly. – Mislim da bi većina ljudi brzo naučila da koristi ovaj sistem.
8. I found the system very cumbersome to use. – Sistem je bio veoma nezgrapan za korišćenje.
9. I felt very confident using the system. – Osećao/la sam se sigurno dok sam koristio/la sistem.
10. I needed to learn a lot of things before I could get going with this system. – Morao/la sam mnogo toga da naučim pre nego što sam mogao/la da koristim sistem.

Bodovanje: neparne stavke (x − 1), parne stavke (5 − x), zbir × 2,5 → 0–100.

## D. Otvorena pitanja

1. Kada je roditelj delovao najmanje uverljivo?
2. Šta vam je u povratnoj informaciji bilo najkorisnije, a šta nejasno?
3. Šta biste promenili pre upotrebe u obuci nastavnika?

## Etika

Učešće je dobrovoljno i anonimno (šifra učesnika umesto imena). Pre početka učesnici se upozoravaju da simulirani roditelj može biti grub i da sesiju mogu prekinuti u svakom trenutku. Transkripti se čuvaju bez ličnih podataka.
