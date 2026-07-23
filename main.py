"""
Ponto de entrada do treinador.

Uso:
    python main.py                          # parâmetros fixos definidos abaixo
    python main.py --auto                   # lê dados reais de dados/garmin_*.json
    python main.py --auto --semanas 16      # idem com número de semanas diferente
    python main.py --auto --arquivo dados/garmin_2026-06-01_2026-07-23.json
    python main.py --prova-nome "5k do Parque" --distancia 5 --semanas 8
"""

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path

from calculadora import pace_str_para_segundos, segundos_para_pace_str
from gerador_plano import gerar_plano, imprimir_resumo, salvar_plano

# ---------------------------------------------------------------------------
# Parâmetros fixos (usados quando não sobrescritos por flags)
# ---------------------------------------------------------------------------

VOLUME_ATUAL_KM = 7.0
PACE_BASE       = "8:10"
SEMANAS         = 18
PROVA_NOME      = "Minha Prova"
PROVA_DISTANCIA = 21.0


# ---------------------------------------------------------------------------
# Inferência automática a partir dos dados do Garmin
# ---------------------------------------------------------------------------

def _ultimo_arquivo_garmin() -> Path | None:
    arquivos = sorted(Path("dados").glob("garmin_*.json"))
    return arquivos[-1] if arquivos else None


def _volume_semanal(corridas: list[dict], janela_dias: int = 28) -> float:
    """Média de km/semana nas últimas `janela_dias` dias."""
    hoje   = date.today()
    cutoff = hoje - timedelta(days=janela_dias)
    recentes = [
        c["distancia_km"]
        for c in corridas
        if c.get("distancia_km") and date.fromisoformat(c["data"]) >= cutoff
    ]
    if not recentes:
        return VOLUME_ATUAL_KM
    semanas = janela_dias / 7
    return round(sum(recentes) / semanas, 1)


def _pace_base(corridas: list[dict], ultimas_n: int = 8) -> str:
    """Média ponderada por distância do pace das últimas N corridas com pace registrado."""
    com_pace = [c for c in corridas if c.get("pace_medio") and c.get("distancia_km")]
    recentes = sorted(com_pace, key=lambda c: c["data"], reverse=True)[:ultimas_n]
    if not recentes:
        return PACE_BASE

    soma_peso   = sum(c["distancia_km"] for c in recentes)
    soma_ponder = sum(
        pace_str_para_segundos(c["pace_medio"]) * c["distancia_km"]
        for c in recentes
    )
    return segundos_para_pace_str(int(soma_ponder / soma_peso))


def inferir_parametros(caminho: Path) -> tuple[float, str]:
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)

    corridas = dados.get("corridas", [])
    if not corridas:
        print("Nenhuma corrida encontrada no arquivo. Usando parâmetros fixos.")
        return VOLUME_ATUAL_KM, PACE_BASE

    volume = _volume_semanal(corridas)
    pace   = _pace_base(corridas)
    return volume, pace


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--auto", action="store_true",
                   help="Infere volume e pace a partir dos dados do Garmin em dados/")
    p.add_argument("--semanas", type=int, default=SEMANAS, metavar="N",
                   help=f"Semanas de preparação (padrão: {SEMANAS})")
    p.add_argument("--arquivo", metavar="caminho",
                   help="Arquivo garmin_*.json a usar com --auto")
    p.add_argument("--prova-nome", default=PROVA_NOME, metavar="NOME",
                   help=f"Nome da prova alvo (padrão: \"{PROVA_NOME}\")")
    p.add_argument("--distancia", type=float, default=PROVA_DISTANCIA, metavar="KM",
                   help=f"Distância da prova em km (padrão: {PROVA_DISTANCIA})")
    return p.parse_args()


def main() -> None:
    args = _args()

    volume = VOLUME_ATUAL_KM
    pace   = PACE_BASE

    if args.auto:
        caminho = Path(args.arquivo) if args.arquivo else _ultimo_arquivo_garmin()
        if not caminho or not caminho.exists():
            print("Nenhum arquivo de dados encontrado em dados/. "
                  "Execute primeiro: python baixar_tudo.py")
            print("Usando parâmetros fixos como fallback.\n")
        else:
            volume, pace = inferir_parametros(caminho)
            print(f"Dados lidos de: {caminho}")

    prova_nome = args.prova_nome
    distancia  = args.distancia

    print(f"Prova:          {prova_nome} ({distancia} km)")
    print(f"Volume semanal: {volume} km/sem")
    print(f"Pace base:      {pace} min/km")
    print(f"Semanas:        {args.semanas}")
    print()

    plano = gerar_plano(
        semanas=args.semanas,
        volume_inicial_km=volume,
        pace_base_str=pace,
        prova_nome=prova_nome,
        prova_distancia_km=distancia,
    )
    imprimir_resumo(plano)

    slug = re.sub(r"[^a-z0-9]+", "_", prova_nome.lower()).strip("_")
    caminho_plano = salvar_plano(
        plano,
        f"{slug}.json",
        metadata={"prova_nome": prova_nome, "prova_distancia_km": distancia, "semanas": args.semanas},
    )
    print(f"\nPlano salvo em: {caminho_plano}")


if __name__ == "__main__":
    main()
