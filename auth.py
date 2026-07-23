"""
Autenticação compartilhada com o Garmin Connect.
Importado por baixar_tudo.py e baixar_treinos.py.
"""

import getpass
import os
import sys
from pathlib import Path

try:
    from garminconnect import Garmin
except ImportError:
    print("Dependência ausente. Execute: pip install -r requirements.txt")
    sys.exit(1)

TOKEN_DIR = Path.home() / ".garminconnect"


def _dump_token(client: Garmin) -> None:
    TOKEN_DIR.mkdir(exist_ok=True)
    # garminconnect >= 0.2 expõe client.garth (requer garth instalado)
    if hasattr(client, "garth"):
        client.garth.dump(str(TOKEN_DIR))
    elif hasattr(client, "client"):
        client.client.dump(str(TOKEN_DIR))


def _load_token(client: Garmin) -> None:
    if hasattr(client, "garth"):
        client.garth.load(str(TOKEN_DIR))
    elif hasattr(client, "client"):
        client.client.load(str(TOKEN_DIR))


def _load_profile(client: Garmin) -> None:
    """
    Replica o que login() faz internamente ao chamar _load_profile_and_settings().
    Necessário quando a sessão é restaurada por token — login() não é chamado,
    então display_name (usado como parâmetro de URL em vários endpoints) fica None.
    """
    client._load_profile_and_settings()


def conectar() -> Garmin:
    """
    Retorna um cliente Garmin autenticado.
    - Tenta restaurar sessão salva em ~/.garminconnect
    - Se expirada ou inexistente, faz login interativo
    - Aceita GARMIN_EMAIL / GARMIN_PASSWORD via variáveis de ambiente
    """
    if TOKEN_DIR.exists():
        try:
            client = Garmin()
            _load_token(client)
            _load_profile(client)
            print(f"Sessão restaurada ({client.display_name})")
            return client
        except Exception:
            print("Token expirado ou inválido. Refazendo login...")

    email    = os.environ.get("GARMIN_EMAIL")    or input("E-mail Garmin: ").strip()
    password = os.environ.get("GARMIN_PASSWORD") or getpass.getpass("Senha Garmin: ")

    def mfa() -> str:
        return input("Código MFA (e-mail/app autenticador): ").strip()

    try:
        client = Garmin(email=email, password=password, prompt_mfa=mfa)
        client.login()
    except Exception as e:
        msg = str(e)
        if "429" in msg:
            print("\nErro 429 — Garmin bloqueou tentativas de login por excesso de requests.")
            print("Aguarde 30–60 minutos e tente novamente.")
            print("Dica: defina GARMIN_EMAIL e GARMIN_PASSWORD como variáveis de ambiente")
            print("      para evitar múltiplas tentativas de login.")
        else:
            print(f"\nFalha no login: {e}")
        sys.exit(1)

    _dump_token(client)
    print(f"Autenticado. Token salvo em {TOKEN_DIR}")
    return client
