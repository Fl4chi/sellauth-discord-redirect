
# SellAuth → Discord Redirect (Flask)

Un server in Python/Flask che:
- Riceve il webhook di pagamento da SellAuth (`/webhook/sellauth`).
- Mostra una pagina elegante di conferma pagamento e reindirizza automaticamente su Discord dopo 10s (`/pay?invoice=ID`).
- Espone `/health` per UptimeRobot.

## Variabili d'ambiente
- `DISCORD_INVITE` (default: `https://discord.gg/pb3dRZdCz6`)
- `DISCORD_CHANNEL_URL` (non usata per il redirect automatico, ma utile per i testi)
- `SELLAUTH_WEBHOOK_SECRET` (opzionale ma consigliato, per HMAC SHA256)
- `PORT` (Render imposta automaticamente)

## Avvio locale
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
# apri http://127.0.0.1:8000/pay?invoice=TEST-123
```

## Deploy su Render (Free)
1. Carica questo progetto su GitHub.
2. Su Render → *New* → *Web Service* → collega la repo.
3. Runtime: **Python 3.11+**.  
   Build Command: `pip install -r requirements.txt`  
   Start Command: `gunicorn app:app`
4. Imposta le *Environment Variables*:
   - `DISCORD_INVITE=https://discord.gg/pb3dRZdCz6`
   - `DISCORD_CHANNEL_URL=https://discord.com/channels/1297953096273625098/1297958674882363432`
   - `SELLAUTH_WEBHOOK_SECRET=SEGRETO_SCELTO_DA_TE` (facoltativo)
5. Deploy.

## Configurare SellAuth
- Imposta la *Deliverables Type* in **Dynamic** e inserisci il webhook URL:  
  `https://<tuo-servizio>.onrender.com/webhook/sellauth`
- Imposta la *return URL* o *success URL* (dove possibile) a:  
  `https://<tuo-servizio>.onrender.com/pay?invoice={{INVOICE_ID}}`
  > Sostituisci `{{INVOICE_ID}}` con il token/variabile che SellAuth espone nelle impostazioni.
- Il webhook invia JSON con almeno:
  ```json
  {"invoice_id":"ABC-123","status":"paid"}
  ```
  Se SellAuth supporta la firma, invia l'header `X-Sellauth-Signature` con `hex(HMAC_SHA256(body, SELLAUTH_WEBHOOK_SECRET))`.

> Nota: se il webhook arriva in ritardo, la pagina `/pay` è comunque ottimistica e reindirizza dopo 10s.

## UptimeRobot
- Crea un monitor *HTTP(s)* che pinghi:
  `https://<tuo-servizio>.onrender.com/health`
- Imposta l'intervallo (5 minuti sul piano gratuito).

