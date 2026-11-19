"""Arhitektura simulatora, slojevi i uloge (Slika 1 u dnevniku): numerisani čvorovi i legenda sa strane."""
import sys

import dijagrami as d
from dijagrami import EDGE, Fig, draw_shape, edge, esc

d.ZONES.update({
    "P": dict(fill="#9a6b3f", tint="#f8f2ea", border="#e3cfb5", text="#7a5230"),
    "1": dict(fill="#0e7ec4", tint="#e9f5fd", border="#b8def6", text="#0b6aa6"),
    "2": dict(fill="#c2410c", tint="#fff1ea", border="#f6c9b1", text="#9a3412"),
    "3": dict(fill="#7c3aed", tint="#f4efff", border="#d9c9fb", text="#6d28d9"),
    "E": dict(fill="#15803d", tint="#eaf8ef", border="#ade3bf", text="#166534"),
})
Z = d.ZONES


def build():
    W, H = 1860, 960
    fig = Fig(W, H)
    raw = {
        # P - podaci i priprema
        1: ("P", "circle", 110, 92), 6: ("P", "square", 230, 92),
        2: ("P", "circle", 610, 64), 3: ("P", "circle", 610, 122), 5: ("P", "square", 730, 92),
        4: ("P", "circle", 990, 92),
        # 1 - tok i sadržaj
        7: ("1", "circle", 110, 262), 8: ("1", "square", 205, 262), 9: ("1", "square", 300, 262),
        10: ("1", "diamond", 400, 262), 11: ("1", "square", 500, 262),
        12: ("1", "circle", 500, 375), 13: ("1", "square", 400, 375), 14: ("1", "circle", 300, 375),
        15: ("1", "circle", 205, 478), 16: ("1", "circle", 300, 478),
        # 2 - emocija chatbota
        17: ("2", "square", 660, 300), 18: ("2", "circle", 770, 300), 19: ("2", "circle", 880, 300),
        21: ("2", "circle", 990, 300), 20: ("2", "square", 660, 440), 22: ("2", "square", 880, 440),
        23: ("2", "diamond", 990, 440), 24: ("2", "circle", 1070, 375), 25: ("2", "square", 1070, 262),
        # 3 - merenje ljutnje nastavnika
        26: ("3", "square", 205, 635), 27: ("3", "circle", 330, 635),
        # E - evaluator
        28: ("E", "circle", 180, 835),
        29: ("E", "diamond", 330, 800), 30: ("E", "diamond", 460, 800), 31: ("E", "diamond", 590, 800),
        32: ("E", "diamond", 330, 875), 33: ("E", "diamond", 460, 875), 34: ("E", "diamond", 590, 875),
        35: ("E", "square", 790, 835), 36: ("E", "circle", 900, 835), 37: ("E", "circle", 1010, 835),
    }
    N = {k: dict(z=z, shape=s, x=x, y=y, r=17 if s != "square" else 16.5) for k, (z, s, x, y) in raw.items()}

    def pt(x, y):
        return dict(shape="point", x=x, y=y)

    d.zone(fig, "P", 60, 30, 1060, 120)
    d.zone(fig, "1", 60, 205, 500, 330)
    d.zone(fig, "2", 600, 205, 520, 330)
    d.zone(fig, "3", 60, 580, 500, 110)
    d.zone(fig, "E", 60, 740, 1060, 190)
    fig.zones.append('<rect x="272" y="768" width="376" height="138" rx="12" fill="#ffffff" fill-opacity="0.55" '
                     'stroke="#ade3bf" stroke-width="1.3" stroke-dasharray="5 4"/>')

    # P: priprema
    edge(fig, "priprema", N[1], N[6])
    edge(fig, "priprema", N[2], N[5])
    edge(fig, "priprema", N[3], N[5])
    edge(fig, "priprema", N[5], N[21])
    edge(fig, "priprema", N[4], N[21])
    edge(fig, "priprema", N[6], N[9])

    # 1: tok i sadržaj
    for a, b in [(7, 8), (8, 9), (9, 10), (10, 11), (13, 14), (14, 16)]:
        edge(fig, "tok", N[a], N[b])
    edge(fig, "upis", N[11], N[12])
    edge(fig, "citanje", N[12], N[13])
    edge(fig, "citanje", N[15], N[16])

    # 3: merenje ljutnje nastavnika
    edge(fig, "tok", N[7], N[26], via=[(110, 635)])
    edge(fig, "tok", N[26], N[27])
    edge(fig, "tok", N[27], N[17], via=[(580, 635), (580, 300)])

    # 2: emocija chatbota
    edge(fig, "tok", N[11], N[17])
    edge(fig, "tok", N[17], N[18])
    edge(fig, "tok", N[18], N[19])
    edge(fig, "upis", N[18], N[12], via=[(770, 375)])
    edge(fig, "tok", N[16], N[20])
    edge(fig, "tok", N[20], N[22])
    edge(fig, "citanje", N[19], N[22])
    edge(fig, "citanje", N[21], N[22])
    edge(fig, "tok", N[22], N[23])
    edge(fig, "tok", N[23], N[24])
    edge(fig, "tok", N[24], N[25])
    edge(fig, "tok", N[25], N[7], via=[(1070, 178), (110, 178)])

    # E: evaluator
    edge(fig, "posle", pt(860, 535), N[28], via=[(860, 715), (180, 715)], width=3.0)
    edge(fig, "posle", N[28], pt(272, 835), width=3.0)
    edge(fig, "posle", pt(648, 835), N[35], width=3.0)
    edge(fig, "posle", N[35], N[36])
    edge(fig, "posle", N[36], N[37])

    for k, n in N.items():
        fig.nodes.append(draw_shape(n["shape"], n["x"], n["y"], n["r"], Z[n["z"]]["fill"], str(k)))

    # ---------------- legenda ----------------
    LX, LY, LW = 1170, 18, 670
    fig.legend.append(f'<rect x="{LX}" y="{LY}" width="{LW}" height="{H - 36}" rx="16" fill="#fbfbfd" '
                      f'stroke="#e5e7eb" stroke-width="1.4"/>')
    fig.legend.append(f'<text x="{LX + 24}" y="{LY + 38}" font-size="19" font-weight="700" fill="#111827">Legenda</text>')
    groups = {
        "P": ("Podaci i priprema", [
            "ESConv (strategije S1–S8)", "ParaDetox (uvredljivo – neutralno)", "APPDIA (uvredljivo – neutralno)",
            "Naši školski parovi vanila → grubo", "Obrtanje parova, filtriranje, nivo",
            "Klasifikator i relacija redosleda"]),
        "1": ("Sloj 1 – tok i sadržaj", [
            "Replika nastavnika (tekst ili glas)", "Govor u tekst (opciono)",
            "Prepoznavanje strategija (S1–S8, A1–A3)", "Provera fokusa (tema, izlazak iz uloge)",
            "Pritužbe: saslušana, rešena, predlog", "Stanje razgovora", "Obrazac razgovora: pravila toka",
            "Sledeći potez roditelja", "Scenario: persona, činjenice, pritužbe", "Grube smernice za potez"]),
        "2": ("Sloj 2 – emocija chatbota (ljutnja)", [
            "Model ljutnje (Δ po strategiji)", "Ljutnja roditelja (0–10)", "Ciljni nivo ljutnje (1–5)",
            "Jezički model: vanila rečenica", "Parovi vanila → grubo (primeri)",
            "Poseban model: gruba rečenica", "Provera: merač, bezbednost, fokus", "Replika roditelja",
            "Tekst u govor (opciono)"]),
        "3": ("Sloj 3 – merenje ljutnje nastavnika", [
            "Merač ljutnje (rečnik i znaci u tekstu)", "Ljutnja nastavnika po replici"]),
        "E": ("Uloga 2 – evaluator", [
            "Zapis razgovora", "Ishod i rešene pritužbe", "Kriva ljutnje roditelja", "Smirenost nastavnika",
            "Redosled strategija (ESConv)", "Fokus na temi", "Provera simulatora (pogođen nivo)", "Ocena 0–100",
            "Povratna informacija po replikama", "Preporučene kartice"]),
    }
    shape_of = {k: n["shape"] for k, n in N.items()}
    ROW, HEAD = 22.5, 36

    def group_block(key, x, y, start_no):
        title, items = groups[key]
        z = Z[key]
        fig.legend.append(
            f'<rect x="{x}" y="{y - 13}" width="24" height="24" rx="6" fill="{z["fill"]}"/>'
            f'<text x="{x + 12}" y="{y - 1}" dy="0.36em" text-anchor="middle" font-size="13" font-weight="700" '
            f'fill="#fff">{key}</text>'
            f'<text x="{x + 33}" y="{y - 1}" dy="0.36em" font-size="14.5" font-weight="700" '
            f'fill="{z["text"]}">{esc(title)}</text>')
        y += HEAD - 6
        no = start_no
        for item in items:
            fig.legend.append(draw_shape(shape_of[no], x + 12, y, 10.5, z["fill"], str(no), fs=10, sw=0))
            fig.legend.append(f'<text x="{x + 33}" y="{y}" dy="0.36em" font-size="14" fill="#1f2937">{esc(item)}</text>')
            y += ROW
            no += 1
        return y + 14, no

    c1x, c2x, y0 = LX + 24, LX + 352, LY + 82
    y, no = y0, 1
    for key in ("P", "1", "2"):
        y, no = group_block(key, c1x, y, no)
    col1 = y
    y = y0
    for key in ("3", "E"):
        y, no = group_block(key, c2x, y, no)

    y += 2
    fig.legend.append(f'<text x="{c2x}" y="{y}" dy="0.36em" font-size="14.5" font-weight="700" fill="#111827">Oblici</text>')
    y += HEAD - 6
    sx = c2x
    for shape, label, wdt in [("circle", "Podatak", 98), ("square", "Obrada", 92), ("diamond", "Provera", 0)]:
        fig.legend.append(draw_shape(shape, sx + 12, y, 10.5, "#6b7280", None, sw=0))
        fig.legend.append(f'<text x="{sx + 31}" y="{y}" dy="0.36em" font-size="14" fill="#1f2937">{label}</text>')
        sx += wdt
    y += ROW + 14
    fig.legend.append(f'<text x="{c2x}" y="{y}" dy="0.36em" font-size="14.5" font-weight="700" fill="#111827">Veze</text>')
    y += HEAD - 6
    for kind, label in [("tok", "Tok obrade jedne replike"), ("upis", "Upis u stanje razgovora"),
                        ("citanje", "Čitanje (pravila, primeri, nivo)"), ("priprema", "Priprema podataka"),
                        ("posle", "Evaluacija posle razgovora")]:
        st = EDGE[kind]
        dash = f' stroke-dasharray="{st["dash"]}" stroke-linecap="round"' if st["dash"] else ""
        fig.legend.append(
            f'<path d="M{c2x},{y} L{c2x + 24},{y}" stroke="{st["color"]}" stroke-width="{st["width"]}"{dash} '
            f'marker-end="url(#{fig.marker(st["color"])})"/>'
            f'<text x="{c2x + 33}" y="{y}" dy="0.36em" font-size="14" fill="#1f2937">{label}</text>')
        y += ROW
    y += 8
    for line in ["Uloga 1 (simulator ljutog roditelja): slojevi 1 i 2.",
                 "Sloj 3 utiče na ljutnju roditelja i na ocenu.",
                 "Deblja strelica polazi od zone ili ulazi u zonu."]:
        fig.legend.append(f'<text x="{c2x}" y="{y}" dy="0.36em" font-size="13" fill="#6b7280">{esc(line)}</text>')
        y += 18
    return fig, col1, y


if __name__ == "__main__":
    out = sys.argv[1]
    fig, a, b = build()
    open(f"{out}/arhitektura_simulatora.svg", "w", encoding="utf-8").write(fig.svg())
    print("legend ends:", round(a), round(b))
