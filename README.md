# Liquidation Watch

Surveille une position de prêt sur **BNB Chain** et t'envoie une **alerte Telegram** avant la
liquidation : health factor calculé sur les prix **Chainlink** on-chain, prix de liquidation,
distance au seuil.

## 1. Ce que ça fait

- lit les feeds Chainlink BSC (WBNB, ETH, BTCB, CAKE…) ;
- calcule le health factor de la position que tu déclares (collatéral + dette) ;
- envoie un message Telegram dès que le seuil est franchi ;
- ne détient **aucune clé privée**, ne signe **aucune transaction**, ne trade **pas**.

## 2. Test local (5 minutes)

```bash
pip install web3 requests
# édite config.json avec tes positions
python liquidation_watch.py --fichier config.json
```

Sortie :

```
verdict              ALERTE — sous 15 % du seuil
health_factor        1.049
prix_liquidation     625.00 $
distance_au_seuil    4.66 %
```

## 3. Déploiement gratuit sur GitHub Actions (24/7, sans serveur)

1. **Fork** ce dépôt (ou importe-le).
2. Édite `config.json` avec tes positions.
3. Crée un bot Telegram : `@BotFather` → `/newbot` → copie le token.
4. Récupère ton chat id : envoie un message à ton bot, puis ouvre
   `https://api.telegram.org/bot<TOKEN>/getUpdates` → `chat.id`.
5. Dans le dépôt : **Settings → Secrets and variables → Actions** →
   ajoute `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`.
6. Onglet **Actions** → active le workflow `liquidation-watch` (il tourne **toutes les heures**).

Pour tester immédiatement : **Actions → liquidation-watch → Run workflow**.

## 4. Configuration de `config.json`

```json
{
  "positions": [
    {
      "collateral": "WBNB",
      "montant_collateral": 10,
      "debt": "USDT",
      "montant_dette": 5000,
      "ltv_max": 0.80
    }
  ],
  "seuil_alerte_health_factor": 1.15
}
```

- `ltv_max` : LTV maximale du protocole utilisé (Venus ≈ 0,80 ; à vérifier pour ton marché) ;
- `seuil_alerte_health_factor` : seuil d'alerte (1,15 = 15 % au-dessus de la zone de liquidation).

## 5. Limites (à lire)

- outil d'information, **pas un conseil financier** ;
- ne remplace pas la surveillance de ton protocole ;
- si un feed Chainlink est en panne/périmé, le script remonte une erreur (il ne devine pas) ;
- les prix des crypto-actifs peuvent varier brutalement ; un health factor peut passer sous 1
  entre deux exécutions (le cron tourne au mieux toutes les heures — GitHub peut retarder).

## 6. Support

Une question, une installation : réponds au message qui t'a amené ici.
