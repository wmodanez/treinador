"""
Gerador de relatórios PDF para planos de treino e análise de atividades.

Uso:
    python relatorio.py plano   [caminho/plano.json]
    python relatorio.py treinos [caminho/atividades.json]

Sem argumento de arquivo, usa o JSON mais recente da pasta correspondente.
"""

import io
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AZUL   = colors.HexColor("#4a90d9")
VERMELHO = colors.HexColor("#e74c3c")
CINZA  = colors.HexColor("#555555")
FUNDO_AZUL = colors.HexColor("#f0f7ff")
FUNDO_VERM = colors.HexColor("#fff0f0")


def _fig_to_image(fig, w_cm: float = 16, h_cm: float = 6) -> Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=w_cm * cm, height=h_cm * cm)


def _estilos() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo":    ParagraphStyle("titulo",    parent=base["Title"],   fontSize=22, spaceAfter=6,  alignment=TA_CENTER),
        "subtitulo": ParagraphStyle("subtitulo", parent=base["Normal"],  fontSize=12, spaceAfter=4,  alignment=TA_CENTER, textColor=CINZA),
        "secao":     ParagraphStyle("secao",     parent=base["Heading2"],fontSize=13, spaceBefore=12,spaceAfter=4),
        "normal":    ParagraphStyle("normal",    parent=base["Normal"],  fontSize=10, spaceAfter=4),
        "rodape":    ParagraphStyle("rodape",    parent=base["Normal"],  fontSize=8,  alignment=TA_CENTER, textColor=colors.grey),
    }


def _tabela_estilo(cor_header, cor_fundo) -> TableStyle:
    return TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  cor_header),
        ("TEXTCOLOR",      (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("ALIGN",          (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [cor_fundo, colors.white]),
        ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
    ])


def _cabecalho(story: list, titulo: str, subtitulo: str, cor_linha, S: dict) -> None:
    story += [
        Paragraph(titulo, S["titulo"]),
        Paragraph(subtitulo, S["subtitulo"]),
        Paragraph(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", S["subtitulo"]),
        Spacer(1, 0.4 * cm),
        HRFlowable(width="100%", thickness=1, color=cor_linha),
        Spacer(1, 0.5 * cm),
    ]


# ---------------------------------------------------------------------------
# Relatório de Plano de Treino
# ---------------------------------------------------------------------------

def _grafico_volume(plano: list) -> Image:
    semanas = [s["semana"] for s in plano]
    volumes = [s["volume_total_km"] for s in plano]
    maximo  = max(volumes)
    cores   = ["#4a90d9" if v >= maximo * 0.9 else "#a8d0f0" for v in volumes]

    fig, ax = plt.subplots(figsize=(13, 4))
    bars = ax.bar(semanas, volumes, color=cores, edgecolor="#cccccc", linewidth=0.5)
    for bar, vol in zip(bars, volumes):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.1,
            f"{vol}",
            ha="center", va="bottom", fontsize=7,
        )
    ax.set_xlabel("Semana", fontsize=10)
    ax.set_ylabel("Volume (km)", fontsize=10)
    ax.set_title("Progressão de Volume Semanal", fontsize=12, fontweight="bold")
    ax.set_xticks(semanas)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.1f"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _fig_to_image(fig)


def relatorio_plano(src: Path, dst: Path) -> None:
    with open(src, encoding="utf-8") as f:
        plano = json.load(f)

    doc = SimpleDocTemplate(str(dst), pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    S = _estilos()
    story: list = []

    _cabecalho(story, "Plano de Treino",
               "Maratona Monumental de Brasília — 22/11/2026", AZUL, S)

    # sumário
    total_km = sum(s["volume_total_km"] for s in plano)
    story += [
        Paragraph("Resumo", S["secao"]),
        Table(
            [
                ["Semanas", "Volume total", "Início", "Pico"],
                [
                    str(len(plano)),
                    f"{total_km:.1f} km",
                    f"{plano[0]['volume_total_km']} km/sem",
                    f"{max(s['volume_total_km'] for s in plano)} km/sem",
                ],
            ],
            colWidths=[4*cm] * 4,
            style=_tabela_estilo(AZUL, FUNDO_AZUL),
        ),
        Spacer(1, 0.5 * cm),
    ]

    # gráfico
    story += [
        Paragraph("Progressão de Volume", S["secao"]),
        _grafico_volume(plano),
        Spacer(1, 0.5 * cm),
    ]

    # tabela semanal completa
    story.append(Paragraph("Treinos por Semana", S["secao"]))
    rows = [["Sem.", "Dia", "Tipo", "Distância", "Pace", "Duração"]]
    for s in plano:
        for i, t in enumerate(s["treinos"]):
            rows.append([
                str(s["semana"]) if i == 0 else "",
                t["dia"],
                t["tipo"].capitalize(),
                f"{t['distancia_km']} km",
                t["pace"],
                t["tempo_estimado"],
            ])

    story += [
        Table(rows, colWidths=[1.4*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm],
              style=_tabela_estilo(AZUL, FUNDO_AZUL)),
        Spacer(1, 0.5 * cm),
        Paragraph("Gerado por Treinador de Corrida", S["rodape"]),
    ]

    doc.build(story)
    print(f"Relatório salvo em: {dst}")


# ---------------------------------------------------------------------------
# Relatório de Treinos Realizados
# ---------------------------------------------------------------------------

def _pace_para_seg(pace_str: str) -> int | None:
    try:
        p, s = pace_str.split(":")
        return int(p) * 60 + int(s)
    except Exception:
        return None


def _seg_para_pace(seg: int) -> str:
    return f"{seg // 60}:{seg % 60:02d}"


def _graficos_treinos(atividades: list) -> Image:
    datas = [a["data"] for a in atividades]
    dists = [a["distancia_km"] for a in atividades]
    paces_seg = [_pace_para_seg(a.get("pace_medio", "")) for a in atividades]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))

    # distância por treino
    ax1.bar(range(len(datas)), dists, color="#e74c3c", edgecolor="#cccccc", linewidth=0.5)
    ax1.set_xticks(range(len(datas)))
    ax1.set_xticklabels([d[5:] for d in datas], rotation=45, ha="right", fontsize=7)
    ax1.set_ylabel("Distância (km)")
    ax1.set_title("Distância por Treino", fontweight="bold")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # evolução do pace
    validos = [(i, p) for i, p in enumerate(paces_seg) if p]
    if validos:
        xs = [v[0] for v in validos]
        ys = [v[1] / 60 for v in validos]
        ax2.plot(xs, ys, marker="o", color="#4a90d9", linewidth=1.5, markersize=5)
        ax2.set_xticks(xs)
        ax2.set_xticklabels([datas[x][5:] for x in xs], rotation=45, ha="right", fontsize=7)
        ax2.yaxis.set_major_formatter(
            ticker.FuncFormatter(lambda v, _: _seg_para_pace(int(v * 60)))
        )
        ax2.set_ylabel("Pace (min/km)")
        ax2.set_title("Evolução do Pace", fontweight="bold")
        ax2.invert_yaxis()
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)
    else:
        ax2.text(0.5, 0.5, "Sem dados de pace", ha="center", va="center",
                 transform=ax2.transAxes, fontsize=11, color="#555555")

    fig.tight_layout()
    return _fig_to_image(fig)


def relatorio_treinos(src: Path, dst: Path) -> None:
    with open(src, encoding="utf-8") as f:
        raw = json.load(f)

    # Suporta dois formatos:
    # - baixar_treinos.py: lista plana de corridas
    # - baixar_tudo.py:    dict com chaves "corridas" e "diario"
    if isinstance(raw, dict):
        atividades = raw.get("corridas", [])
    else:
        atividades = raw

    if not atividades:
        print("Nenhuma corrida encontrada no arquivo.")
        sys.exit(1)

    doc = SimpleDocTemplate(str(dst), pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    S = _estilos()
    story: list = []

    periodo_ini = atividades[0]["data"]
    periodo_fim = atividades[-1]["data"]
    _cabecalho(story, "Análise de Treinos Realizados",
               f"{periodo_ini} a {periodo_fim}", VERMELHO, S)

    total_km = sum(a["distancia_km"] for a in atividades)
    n = len(atividades)
    paces_validos = [_pace_para_seg(a.get("pace_medio", "")) for a in atividades if a.get("pace_medio")]
    pace_medio = _seg_para_pace(sum(paces_validos) // len(paces_validos)) if paces_validos else "-"

    story += [
        Paragraph("Resumo", S["secao"]),
        Table(
            [
                ["Atividades", "Volume total", "Média por treino", "Pace médio"],
                [str(n), f"{total_km:.1f} km", f"{total_km/n:.1f} km", pace_medio],
            ],
            colWidths=[4*cm] * 4,
            style=_tabela_estilo(VERMELHO, FUNDO_VERM),
        ),
        Spacer(1, 0.5 * cm),
        Paragraph("Evolução", S["secao"]),
        _graficos_treinos(atividades),
        Spacer(1, 0.5 * cm),
        Paragraph("Histórico detalhado", S["secao"]),
    ]

    rows = [["Data", "Distância", "Pace médio", "Duração", "FC média"]] + [
        [
            a["data"],
            f"{a['distancia_km']} km",
            a.get("pace_medio", "-"),
            a.get("duracao", "-"),
            str(a.get("fc_media", "-")),
        ]
        for a in atividades
    ]
    story += [
        Table(rows, colWidths=[3.2*cm] * 5,
              style=_tabela_estilo(VERMELHO, FUNDO_VERM)),
        Spacer(1, 0.5 * cm),
        Paragraph("Gerado por Treinador de Corrida", S["rodape"]),
    ]

    doc.build(story)
    print(f"Relatório salvo em: {dst}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _ultimo_json(pasta: Path) -> Path:
    arquivos = sorted(pasta.glob("*.json"))
    if not arquivos:
        print(f"Nenhum arquivo .json encontrado em {pasta}/")
        sys.exit(1)
    return arquivos[-1]


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("plano", "treinos"):
        print(__doc__)
        sys.exit(1)

    tipo = sys.argv[1]
    ts   = datetime.now().strftime("%Y%m%d_%H%M")

    if tipo == "plano":
        src = Path(sys.argv[2]) if len(sys.argv) > 2 else _ultimo_json(Path("planos"))
        dst = Path("planos") / f"relatorio_plano_{ts}.pdf"
        relatorio_plano(src, dst)

    elif tipo == "treinos":
        src = Path(sys.argv[2]) if len(sys.argv) > 2 else _ultimo_json(Path("dados"))
        dst = Path("planos") / f"relatorio_treinos_{ts}.pdf"
        relatorio_treinos(src, dst)


if __name__ == "__main__":
    main()
