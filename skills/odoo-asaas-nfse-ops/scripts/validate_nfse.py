#!/usr/bin/env python3
"""Validador NFSe Asaas para Odoo 19 — JSON-RPC standalone."""
import requests, os, json
try:
    import urllib3; urllib3.disable_warnings()
except ImportError: pass

ODOO_URL = os.getenv("ODOO_URL", "https://seu-odoo.odoo.com")
DB       = os.getenv("ODOO_DB", "seu_banco")
UID      = int(os.getenv("ODOO_UID", 2))
PWD      = os.getenv("ODOO_PWD", "")

def odoo(model, method, args=None, kwargs=None):
    r = requests.post(f"{ODOO_URL}/jsonrpc", json={
        "jsonrpc": "2.0", "method": "call", "id": 1,
        "params": {"service": "object", "method": "execute_kw",
                   "args": [DB, UID, PWD, model, method, args or [], kwargs or {}]}
    }, timeout=30, verify=False)
    data = r.json()
    if "error" in data:
        print(f"ERRO: {json.dumps(data['error'])[:400]}")
        return None
    return data.get("result")

print(f"\n{'='*55}")
print(f"Validando NFSe em: {ODOO_URL}")
print(f"{'='*55}")

# 1. Conectividade
try:
    r = requests.get(f"{ODOO_URL}/web/login", timeout=10, verify=False)
    ok = r.status_code in (200, 303)
    print(f"\n[1/4] Conectividade Odoo: {'✅ OK' if ok else f'❌ HTTP {r.status_code}'}")
except Exception as e:
    print(f"\n[1/4] Conectividade: ❌ {e}")

# 2. Provider Asaas
providers = odoo("payment.provider", "search_read",
    [[["code", "=", "asaas"]]],
    {"fields": ["id", "name", "state", "active", "asaas_api_key",
                "auto_create_nfse", "service_list_item", "municipal_service_id"],
     "context": {"active_test": False}})
print(f"\n[2/4] Provider Asaas:")
if providers:
    p = providers[0]
    print(f"  ID: {p['id']} | Nome: {p['name']}")
    print(f"  Ativo:            {'✅' if p.get('active') else '❌'}")
    print(f"  API Key:          {'✅ preenchida' if p.get('asaas_api_key') else '❌ vazia'}")
    print(f"  Auto NFSe:        {'✅' if p.get('auto_create_nfse') else '⚠️  desativado'}")
    print(f"  service_list_item:{p.get('service_list_item') or '  ❌ vazio'}")
    print(f"  municipal_svc_id: {p.get('municipal_service_id') or '  ❌ vazio'}")
else:
    print("  ❌ Não encontrado — módulo não instalado ou sem provider configurado")

# 3. Empresa
companies = odoo("res.company", "search_read", [[[]]],
    {"fields": ["name", "vat", "l10n_br_tax_regime", "l10n_br_activity_code"]})
print(f"\n[3/4] Empresa:")
if companies:
    c = companies[0]
    print(f"  Nome:    {c['name']}")
    print(f"  CNPJ:    {c.get('vat') or '❌ não preenchido'}")
    print(f"  Regime:  {c.get('l10n_br_tax_regime') or '❌ não definido'}")
    print(f"  CNAE:    {c.get('l10n_br_activity_code') or '⚠️  não preenchido'}")

# 4. Módulos instalados
mods = odoo("ir.module.module", "search_read",
    [[["name", "in", ["blue_payment_asaas", "blue_payment_asaas_nfse",
                      "l10n_br_fiscal", "l10n_br_account"]]]],
    {"fields": ["name", "state"]})
print(f"\n[4/4] Módulos:")
installed = {m["name"]: m["state"] for m in (mods or [])}
for mod in ["blue_payment_asaas", "blue_payment_asaas_nfse", "l10n_br_fiscal", "l10n_br_account"]:
    st = installed.get(mod, "não encontrado")
    print(f"  {'✅' if st == 'installed' else '❌'} {mod}: {st}")

print(f"\n{'='*55}\n")
