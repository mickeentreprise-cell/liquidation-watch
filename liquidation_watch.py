# -*- coding: utf-8 -*-
"""Liquidation Watch — calcule le health factor d'une position sur BNB Chain
et génère une alerte si le seuil est proche.

Principe (sans dépendre du protocole) :
  - l'utilisateur déclare : collatéral (token, montant), dette (token, montant),
    seuil de liquidation (LTV max du protocole, ex. 0,80 pour Venus),
    et les feeds Chainlink correspondants ;
  - le script lit les prix on-chain (Chainlink BSC), calcule le health factor
    et la distance au seuil, puis sort un verdict ALERTE / OK / CRITIQUE.

Usage :
  python liquidation_watch.py --collateral WBNB --montant-collateral 10 --debt USDT --montant-dette 5000
  python liquidation_watch.py --fichier positions.json      # plusieurs positions
"""
import argparse
import json
import sys
import time

from web3 import Web3

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RPC = "https://bsc-dataseed.binance.org"
W = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 30}))

# tokens (BSC) : adresse + décimales
TOKENS = {
    "WBNB": ("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", 18),
    "USDT": ("0x55d398326f99059fF775485246999027B3197955", 18),
    "USDC": ("0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", 18),
    "BUSD": ("0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56", 18),
    "ETH": ("0x2170Ed0880ac9A755fd29B2688956BD959F933F8", 18),
    "BTCB": ("0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c", 18),
    "CAKE": ("0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82", 18),
    "XRP": ("0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE", 18),
    "ADA": ("0x3EE2200Efb3400fAbB9AacF31297cBdD1d435D47", 18),
    "DOGE": ("0xbA2aE424d960c26247Dd6c32edC70B295c744C43", 18),
    "LTC": ("0x4338665CBB7B2485A8855A139b75D5e34AB0DB94", 18),
    "LINK": ("0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD", 18),
    "DOT": ("0x7083609fCE4d1d8Dc0C979AAb8c869Ea2C873402", 18),
    "MATIC": ("0xCC42724C6683B7E57334c4E856f4c9965ED682bD", 18),
}

# feeds Chainlink BSC mainnet (USD, 8 décimales)
FEEDS = {
    "WBNB": "0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE",
    "USDT": None, "USDC": None, "BUSD": None,  # stablecoins = 1 USD
    "ETH": "0x9ef1B8c0E4F7dc8bF5719Ea496883DC6401d5b2e",
    "BTCB": "0x264990fbd0A4796A3E3d8E37C4d5F87a3aCa5Ebf",
    "CAKE": "0xB6064eD41d4f67e353768aA239cA86f4F73665a1",
    "XRP": "0x93A67D414896A280bF8FFB3b389FE3686e014fdd",
    "ADA": "0xa767f745331D267c7751297D982b050c93985627",
    "DOGE": "0xC8A076F7B4B3dC4A6f8d8E84a0eA0Bc2ff2D3F4A",
    "LINK": "0xca236E327F629f9Fc2c30A4E95775EbF0B89fac8",
}

ABI_FEED = [
    {"inputs": [], "name": "latestRoundData",
     "outputs": [{"name": "roundId", "type": "uint80"}, {"name": "answer", "type": "int256"},
                 {"name": "startedAt", "type": "uint256"}, {"name": "updatedAt", "type": "uint256"},
                 {"name": "answeredInRound", "type": "uint80"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}],
     "stateMutability": "view", "type": "function"},
]


def prix_usd(token: str) -> float:
    token = token.upper()
    feed = FEEDS.get(token)
    if feed is None:
        if token in ("USDT", "USDC", "BUSD"):
            return 1.0
        raise ValueError("pas de feed pour " + token)
    c = W.eth.contract(address=Web3.to_checksum_address(feed), abi=ABI_FEED)
    round_id, answer, _, updated_at, _ = c.functions.latestRoundData().call()
    dec = c.functions.decimals().call()
    age = int(time.time()) - int(updated_at)
    if age > 3600 * 6:
        raise ValueError("prix %s périmé (%d s)" % (token, age))
    return float(answer) / (10 ** dec)


def analyser(position: dict) -> dict:
    coll = position["collateral"].upper()
    debt = position["debt"].upper()
    mc = float(position["montant_collateral"])
    md = float(position["montant_dette"])
    ltv_max = float(position.get("ltv_max", 0.80))
    p_coll = prix_usd(coll)
    p_debt = prix_usd(debt)
    valeur_coll = mc * p_coll
    valeur_dette = md * p_debt
    if valeur_dette <= 0:
        return {"verdict": "RIEN À FAIRE", "detail": "aucune dette"}
    hf = (valeur_coll * ltv_max) / valeur_dette
    # prix du collatéral auquel HF = 1 (liquidation)
    prix_liq = (valeur_dette / ltv_max) / mc
    distance = (p_coll - prix_liq) / p_coll * 100.0
    if hf < 1.0:
        verdict = "CRITIQUE — liquidation possible"
    elif hf < 1.15:
        verdict = "ALERTE — sous 15 % du seuil"
    elif hf < 1.30:
        verdict = "SURVEILLER — sous 30 % du seuil"
    else:
        verdict = "OK"
    return {
        "verdict": verdict,
        "collateral": "%s %.4f @ %.2f $" % (coll, mc, p_coll),
        "dette": "%s %.4f @ %.4f $" % (debt, md, p_debt),
        "valeur_collateral_usd": round(valeur_coll, 2),
        "valeur_dette_usd": round(valeur_dette, 2),
        "health_factor": round(hf, 3),
        "prix_liquidation_collateral_usd": round(prix_liq, 4),
        "distance_au_seuil_pct": round(distance, 2),
        "ltv_max": ltv_max,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--collateral", default="WBNB")
    ap.add_argument("--montant-collateral", type=float, default=0.0)
    ap.add_argument("--debt", default="USDT")
    ap.add_argument("--montant-dette", type=float, default=0.0)
    ap.add_argument("--ltv-max", type=float, default=0.80, help="LTV max du protocole (Venus ~0,80)")
    ap.add_argument("--fichier", default=None, help="json: liste de positions")
    ap.add_argument("--seuil", type=float, default=1.15, help="alerter sous ce health factor")
    args = ap.parse_args()

    positions = []
    if args.fichier:
        positions = json.load(open(args.fichier, encoding="utf-8"))
    else:
        positions = [{
            "collateral": args.collateral,
            "montant_collateral": args.montant_collateral,
            "debt": args.debt,
            "montant_dette": args.montant_dette,
            "ltv_max": args.ltv_max,
        }]

    print("=== LIQUIDATION WATCH — %s ===" % time.strftime("%Y-%m-%d %H:%M:%S"))
    alertes = []
    for i, p in enumerate(positions, 1):
        try:
            res = analyser(p)
        except Exception as e:
            res = {"verdict": "ERREUR", "detail": str(e)[:150]}
        print("\nPosition %d" % i)
        for k, v in res.items():
            print("  %-32s %s" % (k, v))
        if res.get("verdict", "").startswith(("ALERTE", "CRITIQUE")):
            alertes.append({"position": i, **res})
    if alertes:
        print("\n>>> %d ALERTE(S) À ENVOYER AU CLIENT <<<" % len(alertes))
        for a in alertes:
            print("- Position %s : %s (HF %.3f, distance %.2f %%)" %
                  (a["position"], a["verdict"], a["health_factor"], a["distance_au_seuil_pct"]))
    else:
        print("\nAucune alerte (toutes les positions sont saines).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
