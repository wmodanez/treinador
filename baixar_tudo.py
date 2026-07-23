"""
Baixa todos os dados disponíveis do Garmin Connect para um período e salva em dados/.

O arquivo de saída consolida, por data, todos os tipos de dado em um único JSON:
corridas, sono, HRV, body battery, estresse, FC de repouso e prontidão para treino.

Uso:
    python baixar_tudo.py                           # últimos 30 dias
    python baixar_tudo.py --dias 60                 # últimos 60 dias
    python baixar_tudo.py --inicio 2026-07-01       # a partir de uma data
    python baixar_tudo.py --inicio 2026-07-01 --fim 2026-07-23
    python baixar_tudo.py --forcar                  # re-baixa datas já salvas
"""

import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from garminconnect import Garmin
except ImportError:
    print("Dependência ausente. Execute: pip install -r requirements.txt")
    sys.exit(1)

from auth import conectar as _conectar

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DADOS_DIR  = Path("dados")
DELAY_SEG  = 0.4   # pausa entre chamadas para evitar rate limit

TIPOS_CORRIDA = {
    "running", "treadmill_running", "track_running",
    "trail_running", "virtual_run",
}


# ---------------------------------------------------------------------------
# Extratores — convertem resposta bruta em dict limpo
# ---------------------------------------------------------------------------

def _extrair_sono(raw: dict | None) -> dict | None:
    if not raw:
        return None
    dto = raw.get("dailySleepDTO") or {}
    scores = dto.get("sleepScores") or {}
    return {
        "total_min":    round((dto.get("sleepTimeSeconds") or 0) / 60),
        "profundo_min": round((dto.get("deepSleepSeconds") or 0) / 60),
        "leve_min":     round((dto.get("lightSleepSeconds") or 0) / 60),
        "rem_min":      round((dto.get("remSleepSeconds") or 0) / 60),
        "acordado_min": round((dto.get("awakeSleepSeconds") or 0) / 60),
        "spo2_media":   dto.get("averageSpO2Value"),
        "respiracao":   dto.get("averageRespirationValue"),
        "score":        scores.get("overall", {}).get("value") if isinstance(scores, dict) else None,
    }


def _extrair_hrv(raw: dict | None) -> dict | None:
    if not raw:
        return None
    s = raw.get("hrvSummary") or {}
    b = s.get("baseline") or {}
    return {
        "noite":         s.get("lastNight"),
        "pico_5min":     s.get("lastNight5MinHigh"),
        "media_semanal": s.get("weeklyAvg"),
        "baseline_low":  b.get("balancedLow"),
        "baseline_high": b.get("balancedUpper"),
        "status":        s.get("status"),
    }


def _extrair_body_battery(raw: list | None) -> dict | None:
    if not raw:
        return None
    valores = [r.get("charged") or r.get("value") for r in raw if r]
    valores = [v for v in valores if v is not None]
    if not valores:
        return None
    return {
        "inicio": valores[0] if valores else None,
        "fim":    valores[-1] if valores else None,
        "minimo": min(valores),
        "maximo": max(valores),
    }


def _extrair_estresse(raw: dict | None) -> dict | None:
    if not raw:
        return None
    return {
        "media":  raw.get("avgStressLevel"),
        "maximo": raw.get("maxStressLevel"),
    }


def _extrair_fc_repouso(raw: dict | None) -> int | None:
    if not raw:
        return None
    return (raw.get("value") or {}).get("restingHeartRate") or raw.get("restingHeartRate")


def _extrair_prontidao(raw: dict | None) -> dict | None:
    if not raw:
        return None
    dto = raw if not raw.get("trainingReadinessDTO") else raw["trainingReadinessDTO"]
    return {
        "score": dto.get("score"),
        "nivel": dto.get("level"),
    }


def _extrair_resumo(raw: dict | None) -> dict | None:
    if not raw:
        return None
    return {
        "passos":            raw.get("totalSteps"),
        "calorias_total":    raw.get("totalKilocalories"),
        "calorias_ativas":   raw.get("activeKilocalories"),
        "distancia_m":       raw.get("totalDistanceMeters"),
        "fc_repouso":        raw.get("restingHeartRate"),
        "fc_maxima":         raw.get("maxHeartRate"),
        "intensidade_min":   raw.get("intensityMinutes"),
    }


# ---------------------------------------------------------------------------
# Download por dia
# ---------------------------------------------------------------------------

def _buscar(fn, *args, label: str = "") -> object:
    try:
        resultado = fn(*args)
        time.sleep(DELAY_SEG)
        return resultado
    except Exception as e:
        print(f"      ⚠ {label}: {e}")
        time.sleep(DELAY_SEG)
        return None


def _baixar_dia(client: Garmin, data: date) -> dict:
    ds = str(data)
    print(f"  {ds}", end="  ", flush=True)

    sono_raw       = _buscar(client.get_sleep_data,          ds,   label="sono")
    hrv_raw        = _buscar(client.get_hrv_data,            ds,   label="hrv")
    bb_raw         = _buscar(client.get_body_battery,        ds, ds, label="body_battery")
    stress_raw     = _buscar(client.get_stress_data,         ds,   label="estresse")
    rhr_raw        = _buscar(client.get_rhr_day,             ds,   label="fc_repouso")
    prontidao_raw  = _buscar(client.get_training_readiness,  ds,   label="prontidao")
    resumo_raw     = _buscar(client.get_stats_and_body,      ds,   label="resumo")

    print("✓")
    return {
        "data":         ds,
        "sono":         _extrair_sono(sono_raw),
        "hrv":          _extrair_hrv(hrv_raw),
        "body_battery": _extrair_body_battery(bb_raw),
        "estresse":     _extrair_estresse(stress_raw),
        "fc_repouso":   _extrair_fc_repouso(rhr_raw),
        "prontidao":    _extrair_prontidao(prontidao_raw),
        "resumo":       _extrair_resumo(resumo_raw),
    }


# ---------------------------------------------------------------------------
# Download de corridas
# ---------------------------------------------------------------------------

def _seg_para_pace(vel_ms: float) -> str | None:
    if not vel_ms or vel_ms <= 0:
        return None
    s = 1000 / vel_ms
    return f"{int(s // 60)}:{int(s % 60):02d}"


def _formatar_duracao(seg: float) -> str:
    h, resto = divmod(int(seg), 3600)
    m, s     = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _baixar_corridas(client: Garmin, inicio: date, fim: date) -> list[dict]:
    print("\nBaixando corridas...")
    raw = client.get_activities_by_date(str(inicio), str(fim), activitytype="running")
    corridas = []
    for a in raw:
        tipo = a.get("activityType", {}).get("typeKey", "")
        if tipo not in TIPOS_CORRIDA:
            continue
        vel  = a.get("averageSpeed", 0)
        dist = round((a.get("distance") or 0) / 1000, 2)
        dur  = a.get("duration") or 0
        corridas.append({
            "id":           a.get("activityId"),
            "nome":         a.get("activityName", ""),
            "tipo":         tipo,
            "data":         (a.get("startTimeLocal") or "")[:10],
            "distancia_km": dist,
            "pace_medio":   _seg_para_pace(vel),
            "duracao":      _formatar_duracao(dur),
            "fc_media":     a.get("averageHR"),
            "cadencia":     a.get("averageRunningCadenceInStepsPerMinute"),
            "vo2max":       a.get("vO2MaxValue"),
        })
    print(f"  {len(corridas)} corrida(s) encontrada(s) ✓")
    return corridas


# ---------------------------------------------------------------------------
# Persistência — mescla com dados já existentes
# ---------------------------------------------------------------------------

def _carregar_existente(caminho: Path) -> dict:
    if caminho.exists():
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    return {"diario": {}, "corridas": []}


def _salvar(dados: dict, caminho: Path) -> None:
    DADOS_DIR.mkdir(exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dias",   type=int, default=30, metavar="N",
                   help="Número de dias para trás a partir de hoje (padrão: 30)")
    p.add_argument("--inicio", metavar="YYYY-MM-DD",
                   help="Data de início (substitui --dias)")
    p.add_argument("--fim",    metavar="YYYY-MM-DD",
                   help="Data de fim (padrão: hoje)")
    p.add_argument("--forcar", action="store_true",
                   help="Re-baixa datas que já existem no arquivo de saída")
    return p.parse_args()


def main() -> None:
    args = _args()

    fim   = date.fromisoformat(args.fim)   if args.fim   else date.today()
    inicio = date.fromisoformat(args.inicio) if args.inicio else fim - timedelta(days=args.dias - 1)

    nome_arquivo = f"garmin_{inicio}_{fim}.json"
    caminho      = DADOS_DIR / nome_arquivo

    client  = _conectar()
    existente = _carregar_existente(caminho)

    # ---- dados diários ----
    dias_totais = (fim - inicio).days + 1
    print(f"\nBaixando dados diários: {inicio} → {fim} ({dias_totais} dias)")

    diario = existente.get("diario", {})
    for i in range(dias_totais):
        data = inicio + timedelta(days=i)
        ds   = str(data)
        if ds in diario and not args.forcar:
            print(f"  {ds}  (já baixado, pulando)")
            continue
        diario[ds] = _baixar_dia(client, data)

    # ---- corridas ----
    corridas_existentes = {c["id"] for c in existente.get("corridas", [])}
    novas_corridas      = [c for c in _baixar_corridas(client, inicio, fim)
                           if c["id"] not in corridas_existentes]
    corridas_final      = sorted(
        existente.get("corridas", []) + novas_corridas,
        key=lambda c: c["data"],
    )

    # ---- salvar ----
    dados_final = {
        "periodo": {"inicio": str(inicio), "fim": str(fim)},
        "diario":  dict(sorted(diario.items())),
        "corridas": corridas_final,
    }
    _salvar(dados_final, caminho)

    n_dias     = len([v for v in diario.values() if v])
    n_corridas = len(corridas_final)
    print(f"\nSalvo em: {caminho}")
    print(f"  {n_dias} dias de dados | {n_corridas} corrida(s) no total")
    print("Para gerar relatório: python relatorio.py treinos")


if __name__ == "__main__":
    main()
