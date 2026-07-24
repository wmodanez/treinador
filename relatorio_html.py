"""
Gerador de relatórios HTML/PDF — análise de treinos e plano de preparação.

Uso:
    python relatorio_html.py plano   [caminho/plano.json]
    python relatorio_html.py treinos [caminho/atividades.json]
    python relatorio_html.py plano   --html-only   # só HTML, sem PDF

Por padrão gera HTML e converte para PDF via playwright.
Sem argumento de arquivo, usa o JSON mais recente da pasta correspondente.

Instalação do playwright (uma vez):
    pip install playwright
    playwright install chromium
"""

import json
import math
import sys
from datetime import date, datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Paleta e constantes
# ---------------------------------------------------------------------------

FASE_COR = {
    "BASE":            "#4a6fa5",
    "DESENVOLVIMENTO": "#d4882a",
    "PICO":            "#c0392b",
    "POLIMENTO":       "#2d7d52",
}
FASE_COR_BG = {
    "BASE":            "#e8f0f8",
    "DESENVOLVIMENTO": "#fdf0e0",
    "PICO":            "#fde8e8",
    "POLIMENTO":       "#e5f2eb",
}
ZONE_CORES = ["#c8d8e8", "#4a7fcb", "#e8a030", "#e05020", "#8b1a1a"]
ZONE_NOMES = ["Z1 Recuperação", "Z2 Aeróbico", "Z3 Tempo", "Z4 Limiar", "Z5 VO₂Max"]

CSS_BASE = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Georgia', serif;
  background: #f2ede4;
  color: #1a1a2e;
  line-height: 1.5;
  font-size: 14px;
}
.page { max-width: 900px; margin: 0 auto; padding: 32px 24px 64px; }
.breadcrumb {
  font-family: system-ui, sans-serif;
  font-size: 11px;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: #888;
  margin-bottom: 10px;
}
h1 { font-size: 2rem; font-weight: 700; margin-bottom: 8px; line-height: 1.15; }
h2 {
  font-size: 1rem;
  font-weight: 700;
  font-family: system-ui, sans-serif;
  letter-spacing: .04em;
  margin: 32px 0 14px;
  color: #1a1a2e;
}
.subtitle {
  font-family: system-ui, sans-serif;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}
hr { border: none; border-top: 1px solid #d8d0c4; margin: 18px 0; }

/* KPI row */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; }
.kpi {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,.07);
}
.kpi-value { font-size: 1.9rem; font-weight: 700; line-height: 1.1; }
.kpi-label {
  font-family: system-ui, sans-serif;
  font-size: 10px;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: #888;
  margin-top: 4px;
}
.kpi-sub { font-size: 11px; color: #aaa; margin-top: 3px; }

/* Insight cards */
.insight-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 24px; }
.insight-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  border-top: 3px solid #ccc;
  box-shadow: 0 1px 3px rgba(0,0,0,.07);
}
.insight-tag {
  font-family: system-ui, sans-serif;
  font-size: 10px;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: #888;
  margin-bottom: 8px;
}
.insight-title { font-size: 1.05rem; font-weight: 700; margin-bottom: 8px; }
.insight-body { font-size: 12px; color: #555; line-height: 1.6; }

/* Chart containers */
.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 12px; }
.chart-box {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,.07);
}
.chart-label {
  font-family: system-ui, sans-serif;
  font-size: 10px;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: #aaa;
  margin-bottom: 10px;
}
.chart-full { background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.07); margin-bottom: 12px; }

/* Phase bar */
.phase-bar { display: flex; border-radius: 8px; overflow: hidden; margin-bottom: 8px; }
.phase-block {
  padding: 14px 16px;
  color: #fff;
  font-family: system-ui, sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .06em;
}
.phase-block .pb-title { font-size: 12px; margin-bottom: 4px; }
.phase-block .pb-sub { font-weight: 400; opacity: .85; font-size: 11px; }
.phase-block .pb-detail { font-weight: 400; opacity: .75; font-size: 10px; margin-top: 2px; }

/* Race badge */
.race-badge {
  display: inline-block;
  border: 2px solid #c0392b;
  border-radius: 6px;
  padding: 8px 16px;
  margin: 12px 0;
}
.race-badge .rb-label {
  font-family: system-ui, sans-serif;
  font-size: 9px;
  letter-spacing: .15em;
  text-transform: uppercase;
  color: #c0392b;
  margin-bottom: 4px;
}
.race-badge .rb-value { font-size: 1.1rem; font-weight: 700; }
.countdown {
  font-family: system-ui, sans-serif;
  font-size: 12px;
  color: #c0392b;
  margin: 8px 0 20px;
  font-weight: 600;
}
.countdown .c-neutral { color: #555; font-weight: 400; }

/* Week table */
table { width: 100%; border-collapse: collapse; font-family: system-ui, sans-serif; font-size: 12px; }
thead th {
  font-size: 10px;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: #aaa;
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid #e0d8ce;
}
tbody tr { border-bottom: 1px solid #ede8e0; }
tbody tr:hover { background: #faf8f5; }
tbody tr.rec-row { background: #fdfaf5; }
tbody td { padding: 11px 10px; vertical-align: middle; }
.sem-num { color: #aaa; }
.vol-val { font-weight: 700; font-size: 14px; }
.lr-val  { color: #4a6fa5; font-weight: 600; }
.badge {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .05em;
  color: #fff;
  margin-right: 4px;
}
.badge-rec { background: #888; }

/* Pace cards */
.pace-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }
.pace-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  border-left: 4px solid #ccc;
  box-shadow: 0 1px 3px rgba(0,0,0,.07);
}
.pace-card-label {
  font-family: system-ui, sans-serif;
  font-size: 10px;
  letter-spacing: .12em;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.pace-card-value { font-size: 1.6rem; font-weight: 700; line-height: 1.1; margin-bottom: 6px; }
.pace-card-desc { font-size: 11px; color: #666; line-height: 1.5; }

/* Golden rules */
.rules { list-style: none; }
.rules li {
  display: flex;
  gap: 16px;
  padding: 14px 16px;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,.07);
  font-size: 13px;
  align-items: flex-start;
}
.rules li .rule-num {
  font-family: system-ui, sans-serif;
  font-size: 13px;
  font-weight: 700;
  color: #ccc;
  min-width: 18px;
}
.rules li .rule-body { color: #333; line-height: 1.5; }
.rules li .rule-body strong { color: #1a1a2e; }
.rules li .rule-body .accent { color: #4a6fa5; }

/* Footer */
footer {
  font-family: system-ui, sans-serif;
  font-size: 10px;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: #aaa;
  margin-top: 48px;
  padding-top: 16px;
  border-top: 1px solid #d8d0c4;
  display: flex;
  justify-content: space-between;
}

/* Print */
@media print {
  body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .kpi, .chart-box, .chart-full, .insight-card, .pace-card, .rules li { break-inside: avoid; }
  .kpi-row, .insight-row, .pace-grid { break-inside: avoid; }
}

/* Zone legend */
.zone-legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 10px;
  font-family: system-ui, sans-serif;
  font-size: 11px;
  color: #555;
}
.zone-dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; margin-right: 4px; vertical-align: middle; }
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_date(ds: str, fmt: str = "%d/%m") -> str:
    try:
        return datetime.fromisoformat(ds).strftime(fmt)
    except Exception:
        return ds


def _fmt_date_long(ds: str) -> str:
    MESES = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
    try:
        d = date.fromisoformat(ds)
        return f"{d.day} de {MESES[d.month-1]} de {d.year}"
    except Exception:
        return ds


def _pace_seg(pace_str: str) -> int | None:
    try:
        p, s = pace_str.split(":")
        return int(p) * 60 + int(s)
    except Exception:
        return None


def _seg_pace(seg: int) -> str:
    return f"{seg // 60}:{seg % 60:02d}"


def _tempo_hm(total_seg: int) -> str:
    h, m = divmod(total_seg // 60, 60)
    return f"{h}h{m:02d}min" if h else f"{m}min"


def _zona_fc(fc: int | None, fc_max: int = 190) -> int:
    if not fc:
        return 2
    pct = fc / fc_max
    if pct < 0.55: return 0
    if pct < 0.65: return 1
    if pct < 0.75: return 2
    if pct < 0.85: return 3
    return 4


def _estimar_zonas(fc_media: int | None, fc_max: int = 190) -> list[float]:
    """Estima % do tempo por zona a partir da FC média (distribuição gaussiana simplificada)."""
    if not fc_media:
        return [5, 70, 20, 5, 0]
    zona = _zona_fc(fc_media, fc_max)
    dist = [0.0] * 5
    weights = {0: [.6, .25, .1, .05, .0],
               1: [.1, .6, .2, .08, .02],
               2: [.05, .2, .5, .2, .05],
               3: [.02, .08, .2, .55, .15],
               4: [.0, .05, .1, .25, .6]}
    return [w * 100 for w in weights[zona]]


# ---------------------------------------------------------------------------
# HTML do plano de treino
# ---------------------------------------------------------------------------

def _pace_referencias(pace_base: str) -> list[dict]:
    seg = _pace_seg(pace_base)
    if not seg:
        return []
    return [
        {
            "label":  "CORRIDA FÁCIL · Z1–Z2",
            "value":  f"{_seg_pace(int(seg*1.15))}–{_seg_pace(int(seg*1.25))}/km",
            "desc":   "Consegue falar frases completas. Maioria dos treinos: 80% do tempo. FC < 145 bpm.",
            "cor":    "#2d7d52",
        },
        {
            "label":  "MODERADO / LONG RUN · Z2",
            "value":  f"{_seg_pace(int(seg*1.05))}–{_seg_pace(int(seg*1.15))}/km",
            "desc":   "Confortável mas presente. Usado nas corridas longas. Ritmo atual de treino fácil.",
            "cor":    "#4a6fa5",
        },
        {
            "label":  "TEMPO / LIMIAR · Z3–Z4",
            "value":  f"{_seg_pace(int(seg*0.85))}–{_seg_pace(int(seg*0.92))}/km",
            "desc":   "Difícil mas sustentável por 20–30 min. Introduzido na semana 6. 1× por semana.",
            "cor":    "#d4882a",
        },
        {
            "label":  "PACE ALVO DA PROVA",
            "value":  f"{_seg_pace(int(seg*0.95))}–{_seg_pace(int(seg*1.00))}/km",
            "desc":   "Meta: chegada dentro do tempo alvo. Altitude de Brasília (1.170 m) pode exigir +5–10 seg/km.",
            "cor":    "#c0392b",
        },
    ]


REGRAS_DE_OURO = [
    ("Semana de recuperação a cada 3–4 semanas.",
     "Volume cai ~30%. Parece retrocesso, é onde a adaptação acontece."),
    ("Não pule o treino longo.",
     "É a sessão mais importante do plano. Se tiver que cortar algo na semana, corte uma corrida fácil."),
    ("80% do tempo deve ser fácil.",
     "Correr devagar nos dias fáceis é o que permite correr forte nas sessões de qualidade."),
    ("Trabalhe a cadência.",
     "Use músicas em <span class='accent'>160–170 BPM</span> como referência. Passadas menores e mais rápidas reduzem impacto e lesões."),
    ("Não aumente volume mais de 10% por semana.",
     "A regra dos 10% é a principal proteção contra lesões por sobrecarga."),
    ("Taper é parte do treinamento.",
     "As 3 semanas finais de redução chegam na prova com as pernas descansadas — resistência ao impulso de treinar mais."),
]


def _html_plano(meta: dict, semanas: list[dict]) -> str:
    prova_nome  = meta.get("prova_nome", "Minha Prova")
    distancia   = meta.get("prova_distancia_km", 21.0)
    n_semanas   = len(semanas)
    pace_base   = meta.get("pace_base", "")
    data_inicio = meta.get("data_inicio", "")
    data_prova  = meta.get("data_prova", "")

    # KPIs
    max_lr   = max(semanas, key=lambda s: s["long_run_km"])
    max_vol  = max(semanas, key=lambda s: s["volume_total_km"])
    pace_alvo_str = _seg_pace(int(_pace_seg(pace_base) * 0.95)) if _pace_seg(pace_base) else "—"

    dias_ate  = ""
    t_estimado = ""
    if data_prova:
        try:
            delta = (date.fromisoformat(data_prova) - date.today()).days
            dias_ate = str(delta)
        except Exception:
            pass
    if _pace_seg(pace_base):
        seg_base = _pace_seg(pace_base)
        t_low = _tempo_hm(int(seg_base * 0.95 * distancia))
        t_hi  = _tempo_hm(int(seg_base * distancia))
        t_estimado = f"{t_low}–{t_hi}"

    # Phase blocks
    fases_vistas: list[str] = []
    fases_info: dict[str, dict] = {}
    for s in semanas:
        f = s["fase"]
        if f not in fases_info:
            fases_info[f] = {"inicio": s["semana"], "fim": s["semana"],
                             "ini_data": s.get("periodo", {}).get("inicio", ""),
                             "fim_data":  s.get("periodo", {}).get("fim", "")}
            fases_vistas.append(f)
        fases_info[f]["fim"]      = s["semana"]
        fases_info[f]["fim_data"] = s.get("periodo", {}).get("fim", "")

    total_fases_sem = n_semanas

    # Chart data: long run per week + phase
    long_runs_data = [s["long_run_km"] for s in semanas]
    long_runs_fases = [s["fase"] for s in semanas]
    long_runs_labels = [f"S{s['semana']}" for s in semanas]
    long_runs_cores  = [FASE_COR[f] for f in long_runs_fases]

    labels_js   = json.dumps(long_runs_labels)
    data_js     = json.dumps(long_runs_data)
    colors_js   = json.dumps(long_runs_cores)

    # Week table rows
    rows_html = ""
    for s in semanas:
        f     = s["fase"]
        periodo = s.get("periodo", {})
        ini_s = _fmt_date(periodo.get("inicio", ""), "%d/%m")
        fim_s = _fmt_date(periodo.get("fim", ""), "%d/%m")
        per_str = f"{ini_s}–{fim_s}" if ini_s and fim_s else "—"

        badge = f'<span class="badge" style="background:{FASE_COR[f]}">{f[:6]}</span>'
        if s.get("is_recovery"):
            badge += '<span class="badge badge-rec">RECUP.</span>'

        rec_cls = " rec-row" if s.get("is_recovery") else ""
        rows_html += f"""
        <tr class="{rec_cls}">
          <td><span class="sem-num">S{s['semana']}</span></td>
          <td style="color:#555">{per_str}</td>
          <td><span class="vol-val">{s['volume_total_km']:.0f} km</span></td>
          <td><span class="lr-val">{s['long_run_km']:.0f} km</span></td>
          <td style="color:#888">{s['num_sessoes']}×</td>
          <td>{badge} <span style="color:#444;font-size:11px">{s['foco']}</span></td>
        </tr>"""

    # Phase bar HTML
    phase_bar_html = ""
    for f in fases_vistas:
        info = fases_info[f]
        n = info["fim"] - info["inicio"] + 1
        pct = n / total_fases_sem * 100
        ini_s = _fmt_date(info["ini_data"], "%b") if info["ini_data"] else ""
        fim_s = _fmt_date(info["fim_data"], "%b") if info["fim_data"] else ""
        range_str = f"Sem {info['inicio']}–{info['fim']}"
        if ini_s and fim_s and ini_s != fim_s:
            range_str += f" · {ini_s.capitalize()}–{fim_s.capitalize()}"
        elif ini_s:
            range_str += f" · {ini_s.capitalize()}"
        phase_bar_html += f"""
        <div class="phase-block" style="background:{FASE_COR[f]};flex:{pct}">
          <div class="pb-title">{f}</div>
          <div class="pb-sub">{range_str}</div>
        </div>"""

    # Pace reference cards
    pace_cards_html = ""
    refs = _pace_referencias(pace_base)
    for ref in refs:
        pace_cards_html += f"""
        <div class="pace-card" style="border-left-color:{ref['cor']}">
          <div class="pace-card-label" style="color:{ref['cor']}">{ref['label']}</div>
          <div class="pace-card-value">{ref['value']}</div>
          <div class="pace-card-desc">{ref['desc']}</div>
        </div>"""

    # Golden rules
    rules_html = ""
    for i, (titulo, desc) in enumerate(REGRAS_DE_OURO, 1):
        rules_html += f"""
        <li>
          <span class="rule-num">{i}</span>
          <span class="rule-body"><strong>{titulo}</strong> {desc}</span>
        </li>"""

    # Countdown / KPI bars
    ini_kpi = f"início {_fmt_date(data_inicio, '%d/%m')}" if data_inicio else ""
    lr_kpi_sem = max_lr.get("periodo", {}).get("inicio", "")
    lr_kpi_str = f"semana {max_lr['semana']} ({_fmt_date(lr_kpi_sem, '%d/%m')})" if lr_kpi_sem else f"semana {max_lr['semana']}"
    vol_kpi_sem = max_vol.get("periodo", {}).get("inicio", "")
    vol_kpi_str = f"semana {max_vol['semana']} ({_fmt_date(vol_kpi_sem, '%d/%m')})" if vol_kpi_sem else f"semana {max_vol['semana']}"

    countdown_html = ""
    if dias_ate or t_estimado:
        parts = []
        if dias_ate:
            parts.append(f"<strong>{dias_ate} dias</strong> até a largada")
        parts.append(f'<span class="c-neutral">semanas de treino: <strong>{n_semanas}</strong></span>')
        if t_estimado:
            parts.append(f'tempo estimado na chegada: <strong>{t_estimado}</strong>')
        countdown_html = f'<div class="countdown">{" · ".join(parts)}</div>'

    footer_left  = prova_nome.upper()
    footer_right = f"{n_semanas} SEMANAS"
    if data_prova:
        footer_left += f" · {_fmt_date(data_prova, '%d/%m/%Y')}"

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Plano — {prova_nome}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>{CSS_BASE}
canvas {{ max-width: 100%; }}
</style>
</head>
<body>
<div class="page">

  <div class="breadcrumb">PLANO DE PREPARAÇÃO · {n_semanas} SEMANAS</div>
  <h1>{prova_nome}</h1>

  <div class="race-badge">
    <div class="rb-label">PROVA</div>
    <div class="rb-value">{distancia:.0f} km{"" if data_prova == "" else " — " + _fmt_date_long(data_prova)}</div>
  </div>

  {countdown_html}

  <div class="kpi-row">
    <div class="kpi">
      <div class="kpi-value">{n_semanas}</div>
      <div class="kpi-label">Semanas de treino</div>
      <div class="kpi-sub">{ini_kpi}</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">{max_lr['long_run_km']:.0f} km</div>
      <div class="kpi-label">Corrida mais longa</div>
      <div class="kpi-sub">{lr_kpi_str}</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">~{max_vol['volume_total_km']:.0f} km</div>
      <div class="kpi-label">Pico semanal</div>
      <div class="kpi-sub">{vol_kpi_str}</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">{pace_alvo_str}</div>
      <div class="kpi-label">Pace alvo/km</div>
      <div class="kpi-sub">no dia da prova</div>
    </div>
  </div>

  <h2>Fases do plano</h2>
  <div class="phase-bar">{phase_bar_html}</div>

  <h2>Progressão da corrida longa</h2>
  <div class="chart-full">
    <div class="chart-label">DISTÂNCIA DO TREINO LONGO POR SEMANA (KM)</div>
    <canvas id="longChart" height="120"></canvas>
  </div>

  <h2>Semana a semana</h2>
  <table>
    <thead>
      <tr>
        <th>SEM</th><th>PERÍODO</th><th>VOLUME</th>
        <th>LONG RUN</th><th>SESSÕES</th><th>FOCO</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>

  <h2>Referência de ritmos</h2>
  <div class="pace-grid">{pace_cards_html}</div>

  <h2>Regras de ouro</h2>
  <ol class="rules">{rules_html}</ol>

  <footer>
    <span>{footer_left}</span>
    <span>{footer_right}</span>
  </footer>

</div>

<script>
const labels  = {labels_js};
const data    = {data_js};
const colors  = {colors_js};

new Chart(document.getElementById('longChart'), {{
  type: 'line',
  data: {{
    labels,
    datasets: [{{
      data,
      borderColor: '#4a6fa5',
      backgroundColor: 'rgba(74,111,165,.08)',
      pointBackgroundColor: colors,
      pointBorderColor: colors,
      pointRadius: 5,
      pointHoverRadius: 7,
      borderWidth: 2,
      tension: 0.3,
      fill: true,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          label: ctx => ctx.parsed.y + ' km'
        }}
      }}
    }},
    scales: {{
      x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 10 }} }} }},
      y: {{ grid: {{ color: '#f0ece4' }}, ticks: {{ callback: v => v + ' km', font: {{ size: 10 }} }} }}
    }}
  }}
}});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# HTML da análise de treinos
# ---------------------------------------------------------------------------

def _insights_treinos(corridas: list[dict]) -> list[dict]:
    insights = []

    # FC trend
    com_fc = [c for c in corridas if c.get("fc_media")]
    if len(com_fc) >= 2:
        fc_ini = com_fc[0]["fc_media"]
        fc_fim = com_fc[-1]["fc_media"]
        delta  = fc_ini - fc_fim
        if delta >= 5:
            insights.append({
                "tag":   "EVOLUÇÃO POSITIVA",
                "title": f"FC caiu {delta} bpm em {len(com_fc)} sessões",
                "body":  f"FC média de {fc_ini} bpm ({_fmt_date(com_fc[0]['data'])}) para "
                         f"{fc_fim} bpm ({_fmt_date(com_fc[-1]['data'])}) em ritmo similar — "
                         "sinal claro de adaptação cardiovascular. O coração trabalha com mais eficiência.",
                "cor":   "#2d7d52",
            })
        elif delta <= -5:
            insights.append({
                "tag":   "PONTO DE ATENÇÃO",
                "title": f"FC subiu {-delta} bpm",
                "body":  "Aumento da FC média pode indicar fadiga acumulada ou intensidade crescente. "
                         "Verifique sono e recuperação.",
                "cor":   "#d4882a",
            })

    # Cadência
    cads = [c["cadencia"] for c in corridas if c.get("cadencia")]
    if cads:
        media_cad = sum(cads) / len(cads)
        if media_cad < 160:
            insights.append({
                "tag":   "PONTO DE ATENÇÃO",
                "title": f"Cadência abaixo do ideal",
                "body":  f"Média de {media_cad:.0f} spm nos treinos recentes. O alvo é 160–180 spm. "
                         "Cadência mais alta aumenta o impacto articular e reduz a economia de corrida.",
                "cor":   "#d4882a",
            })
        else:
            insights.append({
                "tag":   "BOA TÉCNICA",
                "title": f"Cadência em {media_cad:.0f} spm",
                "body":  "Dentro da faixa ideal (160–180 spm). Passadas eficientes reduzem impacto "
                         "e melhoram a economia de corrida.",
                "cor":   "#4a6fa5",
            })

    # Zone distribution
    all_zones = [_estimar_zonas(c.get("fc_media")) for c in corridas]
    if all_zones:
        z1z2_pct = sum(z[0] + z[1] for z in all_zones) / len(all_zones)
        label = "BASE AERÓBICA" if z1z2_pct >= 70 else "INTENSIDADE ALTA"
        cor   = "#4a6fa5" if z1z2_pct >= 70 else "#c0392b"
        insights.append({
            "tag":   label,
            "title": f"{z1z2_pct:.0f}% do tempo em Z1–Z2",
            "body":  ("Os dois últimos treinos mantiveram o esforço nas zonas aeróbicas — "
                      "ritmo correto para construir base antes de adicionar volume ou intensidade."
                      if z1z2_pct >= 70 else
                      "Alta proporção de tempo em zonas intensas. Considere mais treinos leves para equilibrar a carga."),
            "cor":   cor,
        })

    return insights[:3]


def _html_treinos(corridas: list[dict], periodo: dict | None = None) -> str:
    if not corridas:
        return "<p>Nenhuma corrida encontrada.</p>"

    total_km   = sum(c["distancia_km"] for c in corridas)
    n          = len(corridas)
    fc_atual   = next((c["fc_media"] for c in reversed(corridas) if c.get("fc_media")), None)
    fc_ant     = next((c["fc_media"] for c in corridas if c.get("fc_media")), None)
    vo2        = next((c["vo2max"] for c in reversed(corridas) if c.get("vo2max")), None)
    kcal_total = sum(c.get("kcal", 0) or 0 for c in corridas)

    data_ini = corridas[0]["data"]
    data_fim = corridas[-1]["data"]

    MESES = {"01":"jan","02":"fev","03":"mar","04":"abr","05":"mai","06":"jun",
              "07":"jul","08":"ago","09":"set","10":"out","11":"nov","12":"dez"}
    mes_ini = MESES.get(data_ini[5:7], "")
    mes_fim = MESES.get(data_fim[5:7], "")
    periodo_str = (f"08 a {data_fim[8:10]} de {mes_fim}"
                   if mes_ini == mes_fim
                   else f"{data_ini[8:10]} {mes_ini} a {data_fim[8:10]} {mes_fim}")

    tipo_labels = {"running": "Rua", "treadmill_running": "Esteira",
                   "track_running": "Pista", "trail_running": "Trail"}

    # Legend for rua/esteira
    tipos_usados = sorted({c.get("tipo", "running") for c in corridas})
    legend_html  = " ".join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;font-size:11px;color:#555">'
        f'<span style="display:inline-block;width:12px;height:12px;background:{"#4a6fa5" if t=="running" else "#888"};border-radius:2px"></span>'
        f'{tipo_labels.get(t,t)}</span>'
        for t in tipos_usados
    )

    # Chart data
    datas_js    = json.dumps([c["data"][5:] for c in corridas])
    dists_js    = json.dumps([c["distancia_km"] for c in corridas])
    cores_dist  = ["#4a6fa5" if c.get("tipo","running") == "running" else "#888" for c in corridas]
    cores_js    = json.dumps(cores_dist)
    nomes_js    = json.dumps([c.get("nome","") for c in corridas])

    fc_list   = [c.get("fc_media") for c in corridas]
    fc_js     = json.dumps(fc_list)
    fc_labels = json.dumps([c["data"][5:] for c in corridas if c.get("fc_media")])
    fc_vals   = json.dumps([c["fc_media"] for c in corridas if c.get("fc_media")])

    # Zone data per session (stacked bar)
    zone_data: list[list[float]] = [_estimar_zonas(c.get("fc_media")) for c in corridas]
    zone_js = json.dumps([[z[i] for z in zone_data] for i in range(5)])
    zone_names_js = json.dumps(ZONE_NOMES)
    zone_cores_js = json.dumps(ZONE_CORES)
    sess_labels_js = json.dumps([c.get("nome", c["data"][5:])[:22] for c in corridas])

    # Insight cards
    insights = _insights_treinos(corridas)
    insights_html = ""
    for ins in insights:
        insights_html += f"""
        <div class="insight-card" style="border-top-color:{ins['cor']}">
          <div class="insight-tag" style="color:{ins['cor']}">{ins['tag']}</div>
          <div class="insight-title">{ins['title']}</div>
          <div class="insight-body">{ins['body']}</div>
        </div>"""

    # FC delta subtitle
    fc_delta_html = ""
    if fc_atual and fc_ant and abs(fc_atual - fc_ant) >= 1:
        delta_fc     = int(fc_ant) - int(fc_atual)
        fc_delta_html = (f'<div class="kpi-sub">era {int(fc_ant)} em {_fmt_date(data_ini)} '
                         f'({delta_fc:+d})</div>')

    # Zone legend
    zone_legend = " ".join(
        f'<span><span class="zone-dot" style="background:{ZONE_CORES[i]}"></span>{ZONE_NOMES[i]}</span>'
        for i in range(5)
    )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Análise de Treinos</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>{CSS_BASE}
canvas {{ max-width: 100%; }}
</style>
</head>
<body>
<div class="page">

  <div class="breadcrumb">GARMIN CONNECT</div>
  <h1>Análise de Treinos — {MESES.get(data_fim[5:7],'').capitalize()} {data_fim[:4]}</h1>
  <div class="subtitle">{n} {"atividade" if n==1 else "atividades"} de corrida · {periodo_str} · {legend_html}</div>
  <hr>

  <div class="kpi-row">
    <div class="kpi">
      <div class="kpi-value">{total_km:.1f}</div>
      <div class="kpi-label">KM totais</div>
      <div class="kpi-sub">{n} {"sessão" if n==1 else "sessões"} · {(date.fromisoformat(data_fim)-date.fromisoformat(data_ini)).days} dias</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">{"—" if not kcal_total else f"{int(kcal_total):,}".replace(",",".")}</div>
      <div class="kpi-label">Kcal gastas</div>
      <div class="kpi-sub">{"~" + str(int(kcal_total/n)) + " por treino" if kcal_total and n else "sem dado"}</div>
    </div>
    <div class="kpi">
      <div class="kpi-value" style="color:#c0392b">{int(fc_atual) if fc_atual else "—"} bpm</div>
      <div class="kpi-label">FC média atual</div>
      {fc_delta_html}
    </div>
    <div class="kpi">
      <div class="kpi-value">{f"{vo2:.0f}" if vo2 else "—"}</div>
      <div class="kpi-label">VO₂Max estimado</div>
      <div class="kpi-sub">ml·kg⁻¹·min⁻¹</div>
    </div>
  </div>

  <div class="chart-grid">
    <div class="chart-box">
      <div class="chart-label">DISTÂNCIA POR TREINO</div>
      <canvas id="distChart" height="160"></canvas>
    </div>
    <div class="chart-box">
      <div class="chart-label">FC MÉDIA POR TREINO (BPM)</div>
      <canvas id="fcChart" height="160"></canvas>
    </div>
  </div>

  <div class="chart-full">
    <div class="chart-label">TEMPO EM ZONAS DE FREQUÊNCIA CARDÍACA</div>
    <canvas id="zoneChart" height="100"></canvas>
    <div class="zone-legend">{zone_legend}</div>
  </div>

  <div class="insight-row">{insights_html}</div>

  <footer>
    <span>ANÁLISE GERADA EM {datetime.now().strftime("%d/%m/%Y")}</span>
    <span>{n} SESSÕES · {total_km:.1f} KM</span>
  </footer>

</div>

<script>
// Distância
new Chart(document.getElementById('distChart'), {{
  type: 'bar',
  data: {{
    labels: {datas_js},
    datasets: [{{
      data: {dists_js},
      backgroundColor: {cores_js},
      borderRadius: 4,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          title: (items) => {nomes_js}[items[0].dataIndex],
          label: ctx => ctx.parsed.y.toFixed(2) + ' km'
        }}
      }}
    }},
    scales: {{
      x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 10 }} }} }},
      y: {{ grid: {{ color: '#f0ece4' }}, ticks: {{ callback: v => v + ' km', font: {{ size: 10 }} }} }}
    }}
  }}
}});

// FC
new Chart(document.getElementById('fcChart'), {{
  type: 'line',
  data: {{
    labels: {fc_labels},
    datasets: [{{
      data: {fc_vals},
      borderColor: '#c0392b',
      backgroundColor: 'rgba(192,57,43,.08)',
      pointBackgroundColor: '#c0392b',
      pointRadius: 5,
      borderWidth: 2,
      tension: 0.3,
      fill: true,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: ctx => ctx.parsed.y + ' bpm' }} }}
    }},
    scales: {{
      x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 10 }} }} }},
      y: {{ grid: {{ color: '#f0ece4' }}, ticks: {{ font: {{ size: 10 }} }} }}
    }}
  }}
}});

// Zones
const zoneData = {zone_js};
const zoneNames = {zone_names_js};
const zoneCores = {zone_cores_js};
new Chart(document.getElementById('zoneChart'), {{
  type: 'bar',
  data: {{
    labels: {sess_labels_js},
    datasets: zoneNames.map((name, i) => ({{
      label: name,
      data: zoneData[i],
      backgroundColor: zoneCores[i],
      stack: 'z',
      borderRadius: i === 0 ? {{ topLeft:0,topRight:0,bottomLeft:4,bottomRight:4 }} : 0,
    }}))
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(0) + '%' }} }}
    }},
    scales: {{
      x: {{ stacked: true, grid: {{ display: false }}, ticks: {{ font: {{ size: 10 }} }} }},
      y: {{ stacked: true, display: false, max: 100 }}
    }}
  }}
}});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Funções públicas
# ---------------------------------------------------------------------------

def relatorio_plano_html(src: Path, dst: Path) -> None:
    with open(src, encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict) and "semanas" in raw:
        meta    = raw.get("metadata", {})
        semanas = raw["semanas"]
    else:
        meta    = {}
        semanas = raw

    html = _html_plano(meta, semanas)
    dst.parent.mkdir(exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Relatório salvo em: {dst}")


def relatorio_treinos_html(src: Path, dst: Path) -> None:
    with open(src, encoding="utf-8") as f:
        raw = json.load(f)

    corridas = raw.get("corridas", raw) if isinstance(raw, dict) else raw
    periodo  = raw.get("periodo") if isinstance(raw, dict) else None

    if not corridas:
        print("Nenhuma corrida encontrada no arquivo.")
        sys.exit(1)

    html = _html_treinos(corridas, periodo)
    dst.parent.mkdir(exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Relatório salvo em: {dst}")


# ---------------------------------------------------------------------------
# PDF via playwright
# ---------------------------------------------------------------------------

def html_para_pdf(html_path: Path, pdf_path: Path) -> bool:
    """Converte HTML para PDF via playwright/Chromium. Retorna True se bem-sucedido."""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("  playwright não instalado. Execute:")
        print("    pip install playwright && playwright install chromium")
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page    = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(html_path.resolve().as_uri())
            try:
                page.wait_for_load_state("networkidle", timeout=12_000)
            except PWTimeout:
                pass  # Chart.js pode não ter carregado — continua mesmo assim
            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                margin={"top": "12mm", "right": "10mm", "bottom": "12mm", "left": "10mm"},
            )
            browser.close()
        print(f"PDF salvo em:      {pdf_path}")
        return True
    except Exception as exc:
        print(f"  Erro ao converter para PDF: {exc}")
        return False


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
    import argparse

    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("tipo", choices=["plano", "treinos"],
                   help="Tipo de relatório a gerar")
    p.add_argument("arquivo", nargs="?", metavar="caminho",
                   help="JSON de entrada (padrão: mais recente na pasta)")
    p.add_argument("--html-only", action="store_true",
                   help="Gera apenas o HTML, sem converter para PDF")
    args = p.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M")

    if args.tipo == "plano":
        src      = Path(args.arquivo) if args.arquivo else _ultimo_json(Path("planos"))
        html_dst = Path("planos") / f"relatorio_plano_{ts}.html"
        relatorio_plano_html(src, html_dst)
        if not args.html_only:
            html_para_pdf(html_dst, html_dst.with_suffix(".pdf"))

    else:
        src      = Path(args.arquivo) if args.arquivo else _ultimo_json(Path("dados"))
        html_dst = Path("planos") / f"relatorio_treinos_{ts}.html"
        relatorio_treinos_html(src, html_dst)
        if not args.html_only:
            html_para_pdf(html_dst, html_dst.with_suffix(".pdf"))


if __name__ == "__main__":
    main()
