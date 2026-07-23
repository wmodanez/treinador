"""
Funções de cálculo para corrida: pace, volume, progressão.
Pace sempre em min/km (string "MM:SS" ou float em segundos por km).
"""

from datetime import timedelta


def pace_str_para_segundos(pace: str) -> int:
    """'8:10' -> 490"""
    partes = pace.strip().split(":")
    return int(partes[0]) * 60 + int(partes[1])


def segundos_para_pace_str(segundos: int) -> str:
    """490 -> '8:10'"""
    return f"{segundos // 60}:{segundos % 60:02d}"


def pace_para_velocidade_kmh(pace_str: str) -> float:
    """'8:10' -> 7.35 km/h"""
    seg = pace_str_para_segundos(pace_str)
    return round(3600 / seg, 2)


def tempo_estimado(distancia_km: float, pace_str: str) -> str:
    """Retorna o tempo estimado para uma distância a um dado pace. '8:10' a 21km -> '2:51:30'"""
    total_seg = int(pace_str_para_segundos(pace_str) * distancia_km)
    return str(timedelta(seconds=total_seg))


def pace_alvo(pace_atual_str: str, melhoria_pct: float) -> str:
    """
    Calcula pace alvo dado uma melhoria percentual.
    pace_atual='8:10', melhoria_pct=5.0 -> pace ~5% mais rápido.
    """
    seg_atual = pace_str_para_segundos(pace_atual_str)
    seg_alvo = int(seg_atual * (1 - melhoria_pct / 100))
    return segundos_para_pace_str(seg_alvo)


def volume_semanal_sugerido(volume_atual_km: float, semana: int) -> float:
    """
    Progressão de volume: +10% por semana, semana de recuperação a cada 4ª semana (reduz 20%).
    """
    if semana % 4 == 0:
        return round(volume_atual_km * 0.8, 1)
    return round(volume_atual_km * 1.10, 1)
