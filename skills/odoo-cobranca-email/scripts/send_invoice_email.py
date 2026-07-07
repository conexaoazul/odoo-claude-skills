#!/usr/bin/env python3
"""
Envia um email de cobrança ad-hoc para uma fatura (account.move) no Odoo 19,
via JSON-RPC. Inclui o PDF da fatura como anexo e usa message_post no chatter
(rastreável) + fallback para mail.mail.send quando necessário.

Requer: requests  (pip install requests)

Uso:
    export ODOO_URL="https://seu-odoo.odoo.com"
    export ODOO_DB="seu_banco"
    export ODOO_UID=2
    export ODOO_PWD="sua_senha"
    python3 send_invoice_email.py --invoice-id 123 \\
        --to "cliente@email.com" \\
        --from "financeiro@suaempresa.com" \\
        --subject "Fatura XXX — vencimento YYYY-MM-DD" \\
        --body "Prezado cliente, segue fatura..."

Sanitizado para repo público: nenhum dado real de cliente, URL interna ou
credencial é incluído. Substitua os placeholders pelo seu ambiente.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

try:
    import requests
except ImportError:
    sys.stderr.write("Instale 'requests': pip install requests\n")
    sys.exit(1)


def odoo_call(url: str, db: str, uid: int, pwd: str,
              model: str, method: str, args: list[Any]) -> Any:
    """Executa execute_kw no Odoo JSON-RPC."""
    payload = {
        "jsonrpc": "2.0", "method": "call", "id": 1,
        "params": {
            "service": "object", "method": "execute_kw",
            "args": [db, uid, pwd, model, method, args],
        },
    }
    resp = requests.post(f"{url}/jsonrpc", json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(f"Odoo error: {data['error']}")
    return data.get("result")


def authenticate(url: str, db: str, user: str, pwd: str) -> int:
    payload = {
        "jsonrpc": "2.0", "method": "call", "id": 1,
        "params": {
            "service": "common", "method": "authenticate",
            "args": [db, user, pwd, {}],
        },
    }
    resp = requests.post(f"{url}/jsonrpc", json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("error") or not data.get("result"):
        raise RuntimeError("Falha de autenticação")
    return int(data["result"])


def get_invoice_pdf_attachment(url: str, db: str, uid: int, pwd: str,
                               invoice_id: int) -> int | None:
    """Busca anexo PDF já existente da fatura; retorna attachment_id ou None."""
    attachments = odoo_call(url, db, uid, pwd, "ir.attachment", "search_read", [
        [["res_model", "=", "account.move"], ["res_id", "=", invoice_id],
         ["name", "ilike", ".pdf"]],
        ["id", "name", "mimetype"],
    ])
    for att in attachments:
        if att.get("mimetype") == "application/pdf":
            return att["id"]
    return None


def send_via_message_post(url, db, uid, pwd, invoice_id, body, partner_ids=None):
    """Posta mensagem no chatter da fatura (rastreável, aparece no histórico)."""
    return odoo_call(url, db, uid, pwd, "account.move", "message_post",
                     [invoice_id, {"body": body, "partner_ids": partner_ids or []}])


def send_via_mail_mail(url, db, uid, pwd, *, subject, body_html, email_from,
                       email_to, model, res_id, attachment_ids=None):
    """Cria e dispara mail.mail explícito (mais flexível, menos rastreável)."""
    mail_id = odoo_call(url, db, uid, pwd, "mail.mail", "create", [{
        "subject": subject,
        "body_html": body_html,
        "email_from": email_from,
        "email_to": email_to,
        "model": model,
        "res_id": res_id,
        "attachment_ids": [(6, 0, attachment_ids)] if attachment_ids else [],
    }])
    odoo_call(url, db, uid, pwd, "mail.mail", "send", [[mail_id]])
    return mail_id


def main() -> int:
    p = argparse.ArgumentParser(description="Enviar email de cobrança via Odoo JSON-RPC")
    p.add_argument("--url", default=os.environ.get("ODOO_URL"))
    p.add_argument("--db", default=os.environ.get("ODOO_DB"))
    p.add_argument("--user", default=os.environ.get("ODOO_USER",
                                                    os.environ.get("ODOO_UID")))
    p.add_argument("--pwd", default=os.environ.get("ODOO_PWD"))
    p.add_argument("--invoice-id", type=int, required=True)
    p.add_argument("--to", required=True, help="Email do destinatário")
    p.add_argument("--from", dest="email_from",
                   default=os.environ.get("ODOO_FINANCEIRO_EMAIL",
                                          "financeiro@suaempresa.com"))
    p.add_argument("--subject", default="Lembrete de fatura")
    p.add_argument("--body", default="Prezado cliente, segue lembrete da sua fatura.")
    p.add_argument("--mode", choices=["chatter", "mail"], default="chatter",
                   help="chatter=message_post (padrão) | mail=mail.mail.send")
    args = p.parse_args()

    if not all([args.url, args.db, args.user, args.pwd]):
        sys.stderr.write("Defina ODOO_URL, ODOO_DB, ODOO_USER (ou ODOO_UID), ODOO_PWD\n")
        return 2

    uid = (int(args.user) if args.user.isdigit()
           else authenticate(args.url, args.db, args.user, args.pwd))
    pwd = args.pwd

    # Tenta anexar PDF já existente da fatura
    att_id = get_invoice_pdf_attachment(args.url, args.db, uid, pwd, args.invoice_id)
    if att_id:
        print(f"Anexo PDF encontrado: id={att_id}")
    else:
        print("Nenhum anexo PDF encontrado na fatura (email sem anexo).")

    if args.mode == "chatter":
        # message_post envia para os seguidores da fatura; para um destinatário
        # arbitrário externo, use o modo "mail".
        body = f"{args.body}<br/><br/><small>Fatura #{args.invoice_id}</small>"
        msg_id = send_via_message_post(args.url, args.db, uid, pwd,
                                       args.invoice_id, body)
        print(f"message_post enviado: id={msg_id}")
    else:
        mail_id = send_via_mail_mail(args.url, args.db, uid, pwd,
                                     subject=args.subject,
                                     body_html=args.body,
                                     email_from=args.email_from,
                                     email_to=args.to,
                                     model="account.move",
                                     res_id=args.invoice_id,
                                     attachment_ids=[att_id] if att_id else None)
        print(f"mail.mail enviado: id={mail_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())