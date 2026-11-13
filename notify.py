# -*- coding: utf-8 -*-
"""notify.py — exécute Liquidation Watch et envoie l'alerte sur Telegram.

Utilisé par GitHub Actions (toutes les heures) ou en local.
Variables d'environnement :
  TELEGRAM_BOT_TOKEN  (créé via @BotFather)
  TELEGRAM_CHAT_ID    (ton chat id, obtenu via getUpdates)
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import requests

ICI = Path(__file__).resolve().parent


def envoyer_telegram(texte: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        print("Telegram non configuré (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID absents).")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": texte, "disable_web_page_preview": True},
            timeout=30,
        )
        print("Telegram:", r.status_code)
        return r.status_code == 200
    except Exception as e:
        print("Telegram erreur:", str(e)[:200])
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fichier", default=str(ICI / "config.json"))
    ap.add_argument("--seuil", type=float, default=1.15)
    ap.add_argument("--toujours", action="store_true", help="envoyer même sans alerte (test)")
    args = ap.parse_args()

    script = str(ICI / "liquidation_watch.py")
    res = subprocess.run(
        [sys.executable, script, "--fichier", args.fichier],
        capture_output=True, text=True, timeout=180,
    )
    sortie = (res.stdout or "") + (res.stderr or "")
    print(sortie)

    alertes = [l for l in sortie.splitlines() if l.startswith("- Position")]
    doit_envoyer = bool(alertes) or args.toujours

    if doit_envoyer:
        titre = "🚨 LIQUIDATION WATCH — alerte"
        corps = titre + "\n\n" + ("\n".join(alertes) if alertes else "Test : le watcher tourne.")
        return 0 if envoyer_telegram(corps[:4000]) else 1
    print("Aucune alerte : rien à envoyer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
