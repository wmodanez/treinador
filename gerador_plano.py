"""
Gerador de planos de treino semanais por pace.
"""

import json
from datetime import date, timedelta
from pathlib import Path

from calculadora import (
    pace_str_para_segundos,
    segundos_para_pace_str,
    tempo_estimado,
    volume_semanal_sugerido,
)


TIPOS_TREINO = {
    "leve":  {"fator_pace": 1.15, "descricao": "Corrida leve / recuperação"},
    "base":  {"fator_pace": 1.05, "descricao": "Corrida de base (aeróbio fácil)"},
    "alvo":  {"fator_pace": 1.00, "descricao": "Pace alvo da prova"},
    "tempo": {"fator_pace": 0.95, "descricao": "Corrida de limiar (tempo run)"},
    "longo": {"fator_pace": 1.10, "descricao": "Corrida longa"},
}

FASE_CORES = {
    "BASE":            "#4a6fa5",
    "DESENVOLVIMENTO": "#d4882a",
    "PICO":            "#c0392b",
    "POLIMENTO":       "#2d7d52",
}


def pace_para_tipo(pace_base_str: str, tipo: str) -> str:
    seg_base = pace_str_para_segundos(pace_base_str)
    fator = TIPOS_TREINO[tipo]["fator_pace"]
    return segundos_para_pace_str(int(seg_base * fator))


def semana_padrao(volume_km: float, pace_base_str: str) -> list[dict]:
    """Distribui o volume semanal em 4 treinos: Ter base 25%, Qui tempo 20%, Sab leve 20%, Dom longo 35%."""
    proporcoes = [
        ("Terça",   "base",  0.25),
        ("Quinta",  "tempo", 0.20),
        ("Sábado",  "leve",  0.20),
        ("Domingo", "longo", 0.35),
    ]
    treinos = []
    for dia, tipo, prop in proporcoes:
        dist = round(volume_km * prop, 1)
        pace = pace_para_tipo(pace_base_str, tipo)
        treinos.append({
            "dia":          dia,
            "tipo":         tipo,
            "descricao":    TIPOS_TREINO[tipo]["descricao"],
            "distancia_km": dist,
            "pace":         pace,
            "tempo_estimado": tempo_estimado(dist, pace),
        })
    return treinos


def _fase(semana: int, total: int) -> str:
    pct = semana / total
    if pct <= 0.30: return "BASE"
    if pct <= 0.60: return "DESENVOLVIMENTO"
    if pct <= 0.82: return "PICO"
    return "POLIMENTO"


def _foco(semana: int, fase: str, long_km: float, is_rec: bool) -> str:
    if is_rec:
        return "Semana de alívio · volume reduzido" if fase == "PICO" else "Recuperação ativa · semana leve"
    if fase == "BASE":
        if long_km >= 10:
            return f"Primeira dezena! Long run {long_km:.0f} km"
        opts = [
            "Adaptação ao volume · só corridas fáceis",
            "Construção de base · ritmo confortável",
            "Exercícios de cadência · 2× na semana",
        ]
        return opts[(semana - 1) % len(opts)]
    if fase == "DESENVOLVIMENTO":
        if long_km >= 15:
            return f"Long run {long_km:.0f} km · milestone de resistência"
        return f"Long run {long_km:.0f} km · simular ritmo de prova"
    if fase == "PICO":
        return f"Long run {long_km:.0f} km · ritmo de competição"
    return "Taper · qualidade > quantidade · descanso final"


def gerar_plano(
    semanas: int,
    volume_inicial_km: float,
    pace_base_str: str,
    prova_nome: str = "Prova",
    prova_distancia_km: float = 21.0,
    data_inicio: date | None = None,
) -> list[dict]:
    plano  = []
    volume = volume_inicial_km

    for s in range(1, semanas + 1):
        treinos = semana_padrao(volume, pace_base_str)
        is_rec  = (s % 4 == 0)
        fase    = _fase(s, semanas)
        long_km = next((t["distancia_km"] for t in treinos if t["tipo"] == "longo"), 0.0)

        entry: dict = {
            "semana":          s,
            "fase":            fase,
            "is_recovery":     is_rec,
            "volume_total_km": round(volume, 1),
            "long_run_km":     long_km,
            "num_sessoes":     len(treinos),
            "foco":            _foco(s, fase, long_km, is_rec),
            "treinos":         treinos,
        }

        if data_inicio:
            ini = data_inicio + timedelta(weeks=s - 1)
            fim = ini + timedelta(days=6)
            entry["periodo"] = {"inicio": str(ini), "fim": str(fim)}

        plano.append(entry)
        volume = volume_semanal_sugerido(volume, s)

    return plano


def salvar_plano(plano: list[dict], nome_arquivo: str, metadata: dict | None = None) -> Path:
    destino = Path("planos") / nome_arquivo
    destino.parent.mkdir(exist_ok=True)
    doc = {"metadata": metadata or {}, "semanas": plano}
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    return destino


def imprimir_resumo(plano: list[dict]) -> None:
    for semana in plano:
        tag = " [REC]" if semana.get("is_recovery") else ""
        print(f"\n=== Semana {semana['semana']} — {semana['volume_total_km']} km [{semana.get('fase','')}]{tag} ===")
        for t in semana["treinos"]:
            print(f"  {t['dia']:10s} | {t['tipo']:6s} | {t['distancia_km']:4.1f} km | pace {t['pace']} | {t['tempo_estimado']}")
