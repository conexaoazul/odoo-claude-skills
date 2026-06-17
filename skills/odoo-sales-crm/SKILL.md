---
name: odoo-sales-crm
description: "Operar CRM e propostas comerciais (sale.order) no Odoo 19 via JSON-RPC. Consultar pipeline, criar cotações, atualizar oportunidades, monitorar negócios."
version: 1.0.0
author: Conexão Azul Digital
tags: [odoo, crm, sales, pipeline, proposals, json-rpc]
---

# Odoo Sales & CRM — Operação via IA (JSON-RPC)

Skill para consultar, criar e atualizar registros de CRM e vendas no Odoo 19.
Funciona em Odoo.sh, VPS ou on-premise. Não requer acesso SSH.

## Configuração

```bash
export ODOO_URL="https://seu-odoo.odoo.com"
export ODOO_DB="seu_banco"
export ODOO_UID=2
export ODOO_PWD="sua_senha"
```

## Conexão base (reutilizar em todos os scripts)

```python
import requests, os, json
try:
    import urllib3; urllib3.disable_warnings()
except: pass

ODOO_URL = os.getenv("ODOO_URL")
DB = os.getenv("ODOO_DB")
UID = int(os.getenv("ODOO_UID", 2))
PWD = os.getenv("ODOO_PWD")

def odoo(model, method, args=None, kwargs=None):
    r = requests.post(f"{ODOO_URL}/jsonrpc", json={
        "jsonrpc": "2.0", "method": "call", "id": 1,
        "params": {"service": "object", "method": "execute_kw",
                   "args": [DB, UID, PWD, model, method, args or [], kwargs or {}]}
    }, timeout=60, verify=False)
    data = r.json()
    if "error" in data:
        print(f"ERRO: {json.dumps(data['error'])[:400]}")
        return None
    return data.get("result")
```

## 1. CRM — Pipeline de Oportunidades

### Listar oportunidades abertas

```python
leads = odoo("crm.lead", "search_read",
    [[["type", "=", "opportunity"], ["stage_id.is_won", "=", False]]],
    {"fields": ["id", "name", "partner_id", "expected_revenue",
                "stage_id", "probability", "date_deadline", "user_id"],
     "order": "expected_revenue desc",
     "limit": 20})

for l in leads:
    print(f"[{l['id']}] {l['name']} | {l['partner_id'][1] if l['partner_id'] else '-'}")
    print(f"      Valor: R$ {l['expected_revenue']:.0f} | Etapa: {l['stage_id'][1]}")
    print(f"      Prob: {l['probability']}% | Resp: {l['user_id'][1] if l['user_id'] else '-'}")
```

### Criar nova oportunidade

```python
lead_id = odoo("crm.lead", "create", [{
    "type": "opportunity",
    "name": "Oportunidade: Implantação Odoo ERP",
    "partner_id": 42,          # ID do cliente (res.partner)
    "expected_revenue": 5000,
    "probability": 30,
    "description": "Cliente interessado em automação de emissão de NFS-e.",
    "user_id": UID,
}])
print(f"✅ Oportunidade criada: ID {lead_id}")
print(f"   Ver: {ODOO_URL}/odoo/crm/{lead_id}")
```

### Avançar etapa de oportunidade

```python
# Listar etapas disponíveis
stages = odoo("crm.stage", "search_read", [[[]]],
    {"fields": ["id", "name", "sequence"], "order": "sequence"})
for s in stages:
    print(f"  [{s['id']}] {s['name']}")

# Mover oportunidade para etapa "Proposta enviada" (exemplo ID 3)
odoo("crm.lead", "write", [[lead_id], {"stage_id": 3}])
print(f"✅ Oportunidade {lead_id} avançada")
```

---

## 2. Vendas — Propostas e Cotações (sale.order)

### Listar propostas em aberto

```python
orders = odoo("sale.order", "search_read",
    [[["state", "in", ["draft", "sent"]]]],
    {"fields": ["id", "name", "partner_id", "amount_total",
                "state", "date_order", "validity_date"],
     "order": "date_order desc",
     "limit": 20})

for o in orders:
    status = "📋 Rascunho" if o["state"] == "draft" else "📧 Enviado"
    print(f"{status} [{o['name']}] {o['partner_id'][1]} | R$ {o['amount_total']:.2f}")
```

### Criar nova cotação

```python
# 1. Buscar cliente
partners = odoo("res.partner", "search_read",
    [[["name", "ilike", "Nome do Cliente"]]],
    {"fields": ["id", "name", "email"], "limit": 5})
partner_id = partners[0]["id"] if partners else None

# 2. Buscar produto/serviço
products = odoo("product.product", "search_read",
    [[["name", "ilike", "Nome do Serviço"], ["sale_ok", "=", True]]],
    {"fields": ["id", "name", "list_price"], "limit": 5})
product_id = products[0]["id"] if products else None

# 3. Criar cotação
order_id = odoo("sale.order", "create", [{
    "partner_id": partner_id,
    "order_line": [(0, 0, {
        "product_id": product_id,
        "product_uom_qty": 1,
        "price_unit": 1500.00,
        "name": "Implantação NFSe Asaas — Odoo 19",
    })],
    "note": "<p>Proposta sujeita a aprovação prévia. Validade: 15 dias.</p>",
    "validity_date": "2026-07-17",
}])
print(f"✅ Cotação criada: ID {order_id}")
print(f"   Ver: {ODOO_URL}/odoo/sales/{order_id}")
```

### Enviar cotação por email (send_email)

```python
odoo("sale.order", "action_quotation_send", [[order_id]])
print(f"✅ Email de cotação enviado para o cliente")
```

### Confirmar pedido (sale → order)

```python
odoo("sale.order", "action_confirm", [[order_id]])
print(f"✅ Pedido {order_id} confirmado")
```

---

## 3. Dashboard de Vendas (resumo rápido)

```python
from datetime import datetime, timedelta

hoje = datetime.now().strftime("%Y-%m-%d")
inicio_mes = datetime.now().replace(day=1).strftime("%Y-%m-%d")

# Pedidos confirmados no mês
orders_mes = odoo("sale.order", "search_read",
    [[["state", "in", ["sale", "done"]],
      ["date_order", ">=", f"{inicio_mes} 00:00:00"]]],
    {"fields": ["amount_total"]})
total_mes = sum(o["amount_total"] for o in (orders_mes or []))

# Cotações em aberto
cotacoes = odoo("sale.order", "search_count",
    [[["state", "in", ["draft", "sent"]]]])

# Oportunidades
opps = odoo("crm.lead", "search_read",
    [[["type", "=", "opportunity"], ["stage_id.is_won", "=", False]]],
    {"fields": ["expected_revenue", "probability"]})
pipeline = sum(o["expected_revenue"] * o["probability"] / 100 for o in (opps or []))

print(f"\n📊 RESUMO COMERCIAL — {hoje}")
print(f"  Vendas no mês:     R$ {total_mes:,.2f}")
print(f"  Cotações abertas:  {cotacoes}")
print(f"  Pipeline ponderado:R$ {pipeline:,.2f}")
```

---

## 4. Referências

- [Docs Odoo Sales](https://www.odoo.com/documentation/19.0/applications/sales.html)
- [Docs Odoo CRM](https://www.odoo.com/documentation/19.0/applications/crm.html)
- Skill NFSe: `../odoo-asaas-nfse-ops/`
- Skill Cobrança: `../odoo-cobranca-email/`
