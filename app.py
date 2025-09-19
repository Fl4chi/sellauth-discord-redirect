
import os
import hmac
import hashlib
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, abort

DISCORD_INVITE = os.getenv("DISCORD_INVITE", "https://discord.gg/pb3dRZdCz6")
DISCORD_CHANNEL_URL = os.getenv("DISCORD_CHANNEL_URL", "https://discord.com/channels/1297953096273625098/1297958674882363432")
SELLAUTH_WEBHOOK_SECRET = os.getenv("SELLAUTH_WEBHOOK_SECRET", "")  # HMAC SHA256 shared secret (optional but recommended)

DATABASE = os.getenv("DATABASE_PATH", "data.db")

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

@app.before_first_request
def _setup():
    init_db()

@app.get("/health")
def health():
    return jsonify({"ok": True, "time": datetime.utcnow().isoformat()+"Z"})

@app.post("/webhook/sellauth")
def sellauth_webhook():
    """
    Generic webhook endpoint.
    Expecting JSON body with at least: {"invoice_id": "...", "status": "paid"}
    If SELLAUTH_WEBHOOK_SECRET is set, verify X-Sellauth-Signature: hex(HMAC_SHA256(body, secret))
    """
    raw = request.get_data()
    # Optional signature verification
    if SELLAUTH_WEBHOOK_SECRET:
        sig = request.headers.get("X-Sellauth-Signature", "")
        computed = hmac.new(SELLAUTH_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, computed):
            abort(401, "invalid signature")

    data = request.get_json(silent=True) or {}
    invoice_id = data.get("invoice_id") or data.get("invoice") or data.get("id")
    status = (data.get("status") or "").lower()

    if not invoice_id:
        return jsonify({"error": "missing invoice_id"}), 400

    if status not in {"paid", "completed", "success"}:
        # We still record status transitions but do not mark as paid
        status = status or "received"

    conn = get_db()
    conn.execute(
        "INSERT INTO invoices(invoice_id, status, updated_at) VALUES(?,?,?) "
        "ON CONFLICT(invoice_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at",
        (invoice_id, status, datetime.utcnow().isoformat()+"Z")
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True})

@app.get("/pay")
def pay_page():
    """
    Landing page after checkout.
    Use like: /pay?invoice=TEST-123
    If webhook already marked it paid -> show success screen and auto-redirect to Discord in 10s.
    Otherwise we still show the screen and keep the redirect (most gateways call the webhook before returning user).
    """
    invoice_id = request.args.get("invoice", "").strip()
    # Try to read status from db (if present)
    status = None
    if invoice_id:
        conn = get_db()
        cur = conn.execute("SELECT status FROM invoices WHERE invoice_id = ?", (invoice_id,))
        row = cur.fetchone()
        status = row["status"] if row else None
        conn.close()

    is_paid = (status in {"paid", "completed", "success"}) or (status is None)  # optimistic if unknown
    return render_template(
        "success.html",
        invoice_id=invoice_id or "N/D",
        discord_invite=DISCORD_INVITE,
        discord_channel=DISCORD_CHANNEL_URL,
        auto_redirect_seconds=10,
        is_paid=is_paid,
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
