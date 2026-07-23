"""
Gerador de planos de treino semanais por pace.
Produz um plano estruturado por semana com tipos de treino e distâncias.
"""

import json
from pathlib import Path
from calculadora import (
    pace_str_para_segundos,
    segundos_para_pace_str,
    tempo_estimado,
    volume_semanal_sugerido,
)


TIPOS_TREINO = {
    "leve":   {"fator_pace": 1.15, "descricao": "Corrida leve / recuperação"},
    "base":   {"fator_pace": 1.05, "descricao": "Corrida de base (aeróbio fácil)"},
    "alvo":   {"fator_pace": 1.00, "descricao": "Pace alvo da prova"},
    "tempo":  {"fator_pace": 0.95, "descricao": "Corrida de limiar (tempo run)"},
    "longo":  {"fator_pace": 1.10, "descricao": "Corrida longa"},
}


def pace_para_tipo(pace_base_str: str, tipo: str) -> str:
    seg_base = pace_str_para_segundos(pace_base_str)
    fator = TIPOS_TREINO[tipo]["fator_pace"]
    return segundos_para_pace_str(int(seg_base * fator))


def semana_padrao(volume_km: float, pace_base_str: str) -> list[dict]:
    """
    Distribui o volume semanal em 4 treinos:
      Ter: base (25%), Qui: tempo (20%), Sab: leve (20%), Dom: longo (35%)
    """
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
            "dia": dia,
            "tipo": tipo,
            "descricao": TIPOS_TREINO[tipo]["descricao"],
            "distancia_km": dist,
            "pace": pace,
            "tempo_estimado": tempo_estimado(dist, pace),
        })
    return treinos


def gerar_plano(
    semanas: int,
    volume_inicial_km: float,
    pace_base_str: str,
    prova_nome: str = "Prova",
    prova_distancia_km: float = 21.0,
) -> list[dict]:
    plano = []
    volume = volume_inicial_km

    for s in range(1, semanas + 1):
        treinos = semana_padrao(volume, pace_base_str)
        plano.append({
            "semana": s,
            "volume_total_km": round(volume, 1),
            "treinos": treinos,
        })
        volume = volume_semanal_sugerido(volume, s)

    return plano


def salvar_plano(plano: list[dict], nome_arquivo: str) -> Path:
    destino = Path("planos") / nome_arquivo
    destino.parent.mkdir(exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(plano, f, ensure_ascii=False, indent=2)
    return destino


def imprimir_resumo(plano: list[dict]) -> None:
    for semana in plano:
        print(f"\n=== Semana {semana['semana']} — {semana['volume_total_km']} km ===")
        for t in semana["treinos"]:
            print(f"  {t['dia']:10s} | {t['tipo']:6s} | {t['distancia_km']:4.1f} km | pace {t['pace']} | {t['tempo_estimado']}")
