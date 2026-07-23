"""
Baixa atividades de corrida do Garmin Connect e salva em dados/.

Uso:
    python baixar_treinos.py                            # últimas 20 corridas
    python baixar_treinos.py --limite 50                # últimas 50 corridas
    python baixar_treinos.py --dias 30                  # últimos 30 dias
    python baixar_treinos.py --inicio 2026-06-01        # a partir de uma data
    python baixar_treinos.py --inicio 2026-06-01 --fim 2026-07-23

Credenciais:
    Na primeira execução, o script pede e-mail e senha interativamente.
    O token de autenticação fica salvo em ~/.garminconnect para as próximas vezes.
    Você também pode definir as variáveis de ambiente GARMIN_EMAIL e GARMIN_PASSWORD.
"""

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from garminconnect import Garmin
except ImportError:
    print("Dependência ausente. Execute: pip install -r requirements.txt")
    sys.exit(1)

from auth import conectar as _conectar

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

TIPOS_CORRIDA = {
    "running",
    "treadmill_running",
    "track_running",
    "trail_running",
    "virtual_run",
}


# ---------------------------------------------------------------------------
# Conversão de campos
# ---------------------------------------------------------------------------

def _seg_para_pace(velocidade_ms: float) -> str | None:
    """Converte velocidade (m/s) para pace no formato MM:SS/km."""
    if not velocidade_ms or velocidade_ms <= 0:
        return None
    seg_por_km = 1000 / velocidade_ms
    minutos    = int(seg_por_km // 60)
    segundos   = int(seg_por_km % 60)
    return f"{minutos}:{segundos:02d}"


def _formatar_duracao(segundos: float) -> str:
    """Converte segundos totais para H:MM:SS."""
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    return f"{h}:{m:02d}:{s:02d}"


def _converter_atividade(a: dict) -> dict | None:
    """Mapeia campos brutos da API para o formato interno do projeto."""
    tipo = a.get("activityType", {}).get("typeKey", "")
    if tipo not in TIPOS_CORRIDA:
        return None

    velocidade = a.get("averageSpeed", 0)
    distancia  = round((a.get("distance", 0) or 0) / 1000, 2)
    duracao    = a.get("duration", 0) or 0

    data_raw = a.get("startTimeLocal", "")
    data     = data_raw[:10] if data_raw else ""

    return {
        "id":          a.get("activityId"),
        "nome":        a.get("activityName", ""),
        "tipo":        tipo,
        "data":        data,
        "distancia_km": distancia,
        "pace_medio":  _seg_para_pace(velocidade),
        "duracao":     _formatar_duracao(duracao),
        "fc_media":    a.get("averageHR"),
        "cadencia":    a.get("averageRunningCadenceInStepsPerMinute"),
        "vo2max":      a.get("vO2MaxValue"),
    }


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def _baixar_por_limite(client: Garmin, limite: int) -> list[dict]:
    print(f"Buscando últimas {limite} atividades...")
    raw = client.get_activities(0, limite)
    return [c for a in raw if (c := _converter_atividade(a))]


def _baixar_por_dias(client: Garmin, dias: int) -> list[dict]:
    fim    = date.today()
    inicio = fim - timedelta(days=dias)
    return _baixar_por_periodo(client, inicio, fim)


def _baixar_por_periodo(client: Garmin, inicio: date, fim: date) -> list[dict]:
    print(f"Buscando atividades de {inicio} a {fim}...")
    raw = client.get_activities_by_date(
        str(inicio), str(fim), activitytype="running"
    )
    return [c for a in raw if (c := _converter_atividade(a))]


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------

def _salvar(atividades: list[dict], nome: str | None = None) -> Path:
    Path("dados").mkdir(exist_ok=True)
    if not nome:
        ts   = datetime.now().strftime("%Y%m%d_%H%M")
        nome = f"atividades_{ts}.json"
    destino = Path("dados") / nome

    # Atualiza arquivo existente: mescla por ID para evitar duplicatas
    existentes: list[dict] = []
    if destino.exists():
        with open(destino, encoding="utf-8") as f:
            existentes = json.load(f)

    ids_existentes = {a["id"] for a in existentes}
    novas = [a for a in atividades if a["id"] not in ids_existentes]
    combinadas = sorted(existentes + novas, key=lambda a: a["data"])

    with open(destino, "w", encoding="utf-8") as f:
        json.dump(combinadas, f, ensure_ascii=False, indent=2)

    return destino


def _imprimir_resumo(atividades: list[dict]) -> None:
    if not atividades:
        print("Nenhuma atividade de corrida encontrada.")
        return

    print(f"\n{'Data':<12} {'Dist':>7} {'Pace':>8} {'Duração':>10} {'FC':>5}")
    print("-" * 48)
    for a in atividades:
        print(
            f"{a['data']:<12} "
            f"{a['distancia_km']:>6.2f}km "
            f"{a['pace_medio'] or '-':>8} "
            f"{a['duracao']:>10} "
            f"{str(a['fc_media'] or '-'):>5}"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    group = p.add_mutually_exclusive_group()
    group.add_argument("--limite",  type=int, default=20, metavar="N",
                       help="Número de atividades mais recentes (padrão: 20)")
    group.add_argument("--dias",    type=int,             metavar="N",
                       help="Atividades dos últimos N dias")
    group.add_argument("--inicio",  metavar="YYYY-MM-DD",
                       help="Data de início do período")
    p.add_argument("--fim",    metavar="YYYY-MM-DD",
                   help="Data de fim (padrão: hoje; só usado com --inicio)")
    p.add_argument("--saida",  metavar="arquivo.json",
                   help="Nome do arquivo de saída em dados/ (padrão: atividades_TIMESTAMP.json)")
    return p.parse_args()


def main() -> None:
    args = _args()

    client = _conectar()

    if args.inicio:
        inicio = date.fromisoformat(args.inicio)
        fim    = date.fromisoformat(args.fim) if args.fim else date.today()
        atividades = _baixar_por_periodo(client, inicio, fim)
    elif args.dias:
        atividades = _baixar_por_dias(client, args.dias)
    else:
        atividades = _baixar_por_limite(client, args.limite)

    if not atividades:
        print("Nenhuma corrida encontrada com os filtros informados.")
        sys.exit(0)

    _imprimir_resumo(atividades)

    destino = _salvar(atividades, args.saida)
    print(f"\n{len(atividades)} atividade(s) salva(s) em: {destino}")
    print("Para gerar o relatório: python relatorio.py treinos")


if __name__ == "__main__":
    main()
