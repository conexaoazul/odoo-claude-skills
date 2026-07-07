---
name: odoo-sales-crm
description: "Operar CRM e vendas no Odoo 19 via JSON-RPC: pipeline de oportunidades, cotações, propostas, pricelists, atividades e chatter. Inclui best-practices de configuração e dashboard comercial."
version: 2.0.0
author: Conexão Azul Digital
tags: [odoo, crm, sales, pipeline, proposals, pricelists, json-rpc]
---

# Odoo Sales & CRM — Operação via IA (JSON-RPC)

Skill para consultar, criar e atualizar registros de CRM e vendas no Odoo 19.
Funciona em Odoo.sh, VPS ou on-premise. Não requer acesso SSH.

## Configuração (.env)

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
    "name": "Lead XXX — Implantação Odoo ERP",
    "partner_id": 42,          # ID do cliente (res.partner)
    "expected_revenue": 5000,
    "probability": 30,
    "description": "Cliente interessado em automação comercial.",
    "user_id": UID,
}])
print(f"Oportunidade criada: ID {lead_id}")
print(f"  Ver: {ODOO_URL}/odoo/crm/{lead_id}")
```

### Avançar etapa de oportunidade

```python
# Listar etapas disponíveis
stages = odoo("crm.stage", "search_read", [[[]]],
    {"fields": ["id", "name", "sequence", "is_won"], "order": "sequence"})
for s in stages:
    print(f"  [{s['id']}] {s['name']} (won={s['is_won']})")

# Mover oportunidade para próxima etapa (exemplo ID 3)
odoo("crm.lead", "write", [[lead_id], {"stage_id": 3}])
```

### Marcar como ganha / perdida

```python
# Ganha
odoo("crm.lead", "action_set_won", [[lead_id]])
# Perdida com motivo
odoo("crm.lead", "action_set_lost", [[lead_id]],
    {"message_log": "Preço acima do budget", "active_test": False})
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
    status = "Rascunho" if o["state"] == "draft" else "Enviado"
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
        "name": "Pacote de serviços — Proposta R$ valor",
    })],
    "note": "<p>Proposta sujeita a aprovação prévia. Validade: 15 dias.</p>",
    "validity_date": "2026-07-22",
}])
print(f"Cotação criada: ID {order_id}")
```

### Enviar cotação por email

```python
odoo("sale.order", "action_quotation_send", [[order_id]])
```

### Confirmar pedido

```python
odoo("sale.order", "action_confirm", [[order_id]])
```

---

## 3. Atividades e Chatter

### Agendar atividade (ligação/demo)

```python
activity_id = odoo("mail.activity", "create", [{
    "res_model": "crm.lead",
    "res_id": lead_id,
    "activity_type_id": 2,        # ajuste ao ID de "Call"/"Meeting" do seu banco
    "summary": "Ligação de follow-up",
    "date_deadline": "2026-07-15",
    "user_id": UID,
}])
```

### Postar mensagem no chatter

```python
odoo("mail.message", "create", [{
    "model": "crm.lead",
    "res_id": lead_id,
    "body": "<p>Atualização comercial: proposta enviada ao cliente.</p>",
    "message_type": "comment",
    "subtype_xmlid": "mail.mt_comment",
}])
```

---

## 4. Dashboard de Vendas (resumo rápido)

```python
from datetime import datetime
inicio_mes = datetime.now().replace(day=1).strftime("%Y-%m-%d")

orders_mes = odoo("sale.order", "search_read",
    [[["state", "in", ["sale", "done"]],
      ["date_order", ">=", f"{inicio_mes} 00:00:00"]]],
    {"fields": ["amount_total"]})
total_mes = sum(o["amount_total"] for o in (orders_mes or []))

cotacoes = odoo("sale.order", "search_count",
    [[["state", "in", ["draft", "sent"]]]])

opps = odoo("crm.lead", "search_read",
    [[["type", "=", "opportunity"], ["stage_id.is_won", "=", False]]],
    {"fields": ["expected_revenue", "probability"]})
pipeline = sum(o["expected_revenue"] * o["probability"] / 100 for o in (opps or []))

print(f"Vendas no mês:      R$ {total_mes:,.2f}")
print(f"Cotações abertas:   {cotacoes}")
print(f"Pipeline ponderado: R$ {pipeline:,.2f}")
```

---

## 5. Best Practices — Configuração CRM/Vendas

### Pipeline B2B recomendado (CRM → Configuration → Stages)

| Etapa | Probabilidade | Observação |
|-------|---------------|------------|
| New Lead | 10% | Entrada do lead |
| Qualified | 25% | BANT confirmado |
| Proposal Sent | 50% | Cotação enviada |
| Negotiation | 75% | Em revisão pelo cliente |
| Won | `is_won=True` | Marca oportunidade como ganha |
| Lost | — | Botão "Mark as Lost" |

- Ative **Rotting Days** em CRM Settings para sinalizar deals parados em vermelho.
- Use **Predictive Lead Scoring** (v16+) para probabilidade automática baseada em histórico; desative se preferir probabilidade manual por etapa.
- Cadastre **Lost Reasons** (CRM → Configuration → Lost Reasons) para gerar dataset de coaching de vendas.

### Quotation Templates (Sales → Configuration → Quotation Templates)

Requer módulo **Sales Management** ativado. Estrutura típica:

- Linha obrigatória: produto principal (ex.: assinatura anual).
- Linhas opcionais: onboarding, suporte premium, usuários extras.
- Marcar **Online Signature** e/ou **Online Payment** (deposit %) para acelerar fechamento.
- Definir validade (ex.: 30 dias) e notas contratuais no campo Notes.

### Pricelists por tier de cliente

1. Sales → Configuration → Settings → ativar **Pricelists**.
2. Criar pricelist com `Compute Price = Discount` (ex.: VIP 15% Off).
3. Atribuir no cadastro do cliente (Sales & Purchase tab → Pricelist).

### Sales Teams com metas

- Configure times em CRM → Configuration → Sales Teams.
- Defina **Expected Revenue** e **Closing Date** em cada oportunidade — alimenta o forecast dashboard por time.

---

## 6. Armadilhas Conhecidas

| Sintoma | Causa | Ação |
|---------|-------|------|
| `stage_id.is_won` não filtra | Campo é computed no `crm.stage` | Confirme que a etapa tem `is_won=True` setado no config |
| Cotação não envia email | Sem template ou servidor SMTP | Configure `mail.template` + servidor de saída em Settings |
| `action_set_won` sem efeito | Oportunidade já ganha ou arquivada | Verifique `active=False` e `stage_id.is_won` |
| Pricelist não aplica desconto | Ordem sem pricelist do cliente | Reabrir cotação e setar `pricelist_id` manualmente |
| Predictive Lead Scoring sobrescreve prob | Recurso v16+ ativo | Desativar em CRM Settings se preferir manual |
| Comissões não nativas | Odoo CRM não tem commission rules | Precisa módulo custom ou de terceiros |

---

## 7. Limitações

- **Comissões** não são nativas do Odoo CRM — exigem módulo custom ou terceiros.
- **Territory-based lead assignment** (roteamento geográfico) requer regras custom ou Enterprise Leads.
- **Cadência de emails** (drip campaigns) não é nativa do CRM — usar **Email Marketing** ou **Marketing Automation**.
- **Quotation Template** com produtos opcionais exige módulo **Sale Management** (não está no `sale` base).

---

## 8. Referências

- [Docs Odoo Sales](https://www.odoo.com/documentation/19.0/applications/sales.html)
- [Docs Odoo CRM](https://www.odoo.com/documentation/19.0/applications/crm.html)
- Skill NFSe: `../odoo-asaas-nfse-ops/`