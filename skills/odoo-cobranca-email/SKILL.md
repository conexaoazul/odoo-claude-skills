---
name: odoo-cobranca-email
description: "Automatizar cobrança e follow-up de faturas no Odoo 19 via mail.template, server actions e base.automation. Inclui régua de cobrança, template com desconto de fidelidade, anexo PDF da fatura, envio ad-hoc via JSON-RPC e troubleshooting multi-company."
version: 2.0.0
author: Conexão Azul Digital
tags: [odoo, cobranca, email, faturas, json-rpc, brasil]
---

# Odoo Cobrança por Email — Automação Nativa

Skill para criar e operar automação de cobrança diretamente no Odoo 19, sem
dependência externa (n8n, scripts, gateways proprietários). Funciona em qualquer
Odoo 19 — Odoo.sh, VPS, on-premise.

## Configuração (.env)

```bash
export ODOO_URL="https://seu-odoo.odoo.com"
export ODOO_DB="seu_banco"
export ODOO_UID=2
export ODOO_PWD="sua_senha"
export ODOO_FINANCEIRO_EMAIL="financeiro@suaempresa.com"
```

## Quando usar

- Fatura em aberto precisa de lembrete por email
- Quer aplicar desconto de fidelidade (ex: 10% antecipado) automaticamente
- Follow-up escalonado (3 dias antes + 1 dia depois do vencimento)
- PDF da fatura deve ir como anexo automaticamente
- Foco em retenção: evitar churn com tom humano e ancoragem no projeto

## Não usar quando

- Odoo não tem módulo `account` instalado
- Não há contas contábeis configuradas por empresa (blocker `_check_company`)
- SMTP não configurado no Odoo

## Pré-requisitos

1. Módulos instalados: `account`, `mail`, `base_automation`
2. Cron ativo: `Automation Rules: check and execute` (`ir.cron`)
3. Conta SMTP configurada (Configurações → Geral → Servidor de Email)
4. Contas contábeis por empresa (`asset_receivable`, `income`)

## Arquitetura

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Cron Odoo   │────▶│ Auto Action  │────▶│ Server Action│
│ (ir.cron)    │     │(base.automation)    │ (mail_post)  │
└──────────────┘     └──────────────┘     └──────────────┘
                                                   │
                                                   ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Parceiro    │◀────│  account.move│◀────│ Mail Template│
│  (email)     │     │  (fatura)    │     │ (PDF anexo)  │
└──────────────┘     └──────────────┘     └──────────────┘
```

| Componente       | Modelo Odoo        | Função                                        |
|------------------|--------------------|-----------------------------------------------|
| Mail Template    | `mail.template`    | HTML + variáveis Jinja2 + anexo PDF            |
| Server Action    | `ir.actions.server`| `state='mail_post'` dispara o email            |
| Automated Action | `base.automation`  | Trigger `on_time` relativo ao `invoice_date_due` |
| Cron             | `ir.cron`          | Processa triggers pendentes a cada N minutos   |

## 1. Criar Mail Template (JSON-RPC)

```python
payload = {
    "jsonrpc": "2.0", "method": "call", "id": 1,
    "params": {
        "service": "object", "method": "execute_kw",
        "args": [DB, UID, PWD, "mail.template", "create", [{
            "name": "Cobrança: Lembrete com Desconto de Fidelidade",
            "model_id": MODEL_ID_ACCOUNT_MOVE,  # ir.model where model='account.move'
            "subject": "Oferta especial — R$ {{ round(object.amount_residual * 0.9, 2) }} (desconto)",
            "email_from": "{{ user.email_formatted }}",
            "partner_to": "{{ object.partner_id.id }}",
            "body_html": "<div style=\"...\">...HTML...</div>",
            "lang": "${object.partner_id.lang}",
            "auto_delete": False,
        }]],
    },
}
```

### Variáveis Jinja2 disponíveis

| Variável                       | Significado              | Uso                          |
|--------------------------------|--------------------------|------------------------------|
| `object.partner_id.name`       | Nome do cliente          | Saudação personalizada       |
| `object.amount_residual`       | Valor em aberto          | Cálculo de desconto          |
| `round(x, 2)`                  | Arredondar valor         | Odoo 19 safe_eval não aceita `\|format` |
| `object.invoice_date_due`      | Data de vencimento       | Urgência do desconto         |
| `object.invoice_line_ids[0].name` | Descrição do serviço  | Contextualização             |
| `user.name` / `user.email`     | Assinatura do vendedor   | Tom humano                   |

> Odoo 19 safe_eval: NÃO usar `"%.2f"|format(...)`. Usar `round(..., 2)`.

### Anexar PDF da fatura

```python
# Buscar report_id de account.report_invoice_with_payments
# e vincular ao template
write_vals = {"report_template_ids": [(4, REPORT_ID, 0)]}
```

## 2. Criar Server Action

```python
server_action_vals = {
    "name": "Enviar Cobrança com Desconto",
    "model_id": MODEL_ID_ACCOUNT_MOVE,
    "state": "mail_post",  # Odoo 19 usa 'mail_post', não 'email'
    "type": "ir.actions.server",
    "template_id": TEMPLATE_ID,
    "usage": "ir_actions_server",
}
```

Valores válidos de `ir.actions.server.state` no Odoo 19:
`mail_post` (email), `object_write` (atualizar registro), `code` (Python), `webhook`.

## 3. Criar Automated Actions

### 3.1 Trigger: 3 dias ANTES do vencimento

```python
automation_vals = {
    "name": "Cobrança Auto: 3 dias antes do vencimento",
    "model_id": MODEL_ID_ACCOUNT_MOVE,
    "trigger": "on_time",
    "trg_date_id": FIELD_ID_INVOICE_DATE_DUE,  # ir.model.fields
    "trg_date_range": 3,
    "trg_date_range_type": "day",
    "trg_date_range_mode": "before",
    "filter_domain": "[('move_type', '=', 'out_invoice'), ('payment_state', '!=', 'paid'), ('state', '=', 'posted')]",
    "action_server_ids": [(0, 0, {
        "name": "Enviar Cobrança",
        "model_id": MODEL_ID_ACCOUNT_MOVE,
        "state": "mail_post",
        "template_id": TEMPLATE_ID,
    })],
}
```

### 3.2 Trigger: 1 dia DEPOIS do vencimento

```python
automation_vals = {
    "name": "Follow-up Auto: 1 dia após vencimento",
    "model_id": MODEL_ID_ACCOUNT_MOVE,
    "trigger": "on_time",
    "trg_date_id": FIELD_ID_INVOICE_DATE_DUE,
    "trg_date_range": 1,
    "trg_date_range_type": "day",
    "trg_date_range_mode": "after",
    "filter_domain": "[('move_type', '=', 'out_invoice'), ('payment_state', '!=', 'paid'), ('state', '=', 'posted')]",
    "action_server_ids": [(0, 0, {
        "name": "Enviar Follow-up",
        "model_id": MODEL_ID_ACCOUNT_MOVE,
        "state": "mail_post",
        "template_id": TEMPLATE_ID,
    })],
}
```

> Regra de delay no Odoo 19: `trg_date_range` deve ser **sempre positivo**.
> Use `trg_date_range_mode='before'` para dias antes e `'after'` para dias depois.

## 4. Régua de Cobrança (best-practice genérica)

| Janela              | Tom             | Ação                                     |
|---------------------|-----------------|------------------------------------------|
| 7 dias antes        | Amigável        | Lembrete soft com link de pagamento      |
| 3 dias antes        | Oferta          | Desconto de fidelidade (ex: 10%)         |
| Vencimento          | Confirmação     | Aviso de vencimento + PDF da fatura      |
| 1 dia depois        | Escalonamento   | Follow-up com novo link + contato direto |
| 7 dias depois       | Urgência        | Cobrança formal + suspensão de serviços  |

> Política recomendada: **cobrança sempre com NFS-e emitida junto**.
> Inclua no email o link de pagamento **e** o link da NFS-e (PDF anexo).
> Sem nota autorizada, emita a NFS-e antes de cobrar.

## 5. Enviar email ad-hoc via JSON-RPC

### 5.1 Via `message_post` na fatura (chatter)

```python
odoo("account.move", "message_post",
    [INVOICE_ID],
    {"body": "Lembrete: fatura XXX vence em YYYY-MM-DD.", "partner_ids": []})
```

### 5.2 Via `mail.mail` create + send

```python
mail_id = odoo("mail.mail", "create", [{
    "subject": "Fatura XXX — vencimento YYYY-MM-DD",
    "body_html": "<p>Prezado cliente, ...</p>",
    "email_from": "financeiro@suaempresa.com",
    "email_to": "cliente@email.com",
    "model": "account.move",
    "res_id": INVOICE_ID,
    "attachment_ids": [(6, 0, [PDF_ATTACHMENT_ID])],
}])
odoo("mail.mail", "send", [[mail_id]])
```

Ver script completo: `scripts/send_invoice_email.py`.

## 6. Template HTML sugerido (resumo)

```html
<div style="font-family: Arial, sans-serif; max-width: 640px;">
  <p>Olá {{ object.partner_id.name }},</p>
  <p>Sua fatura <strong>{{ object.name }}</strong> vence em
     <strong>{{ object.invoice_date_due }}</strong>.</p>
  <p>Valor em aberto: <strong>R$ {{ round(object.amount_residual, 2) }}</strong></p>
  <p>Pague até o vencimento e ganhe <strong>10% de desconto</strong>:
     R$ {{ round(object.amount_residual * 0.9, 2) }}</p>
  <p>
    <a href="{{ object.access_url }}" style="...">Pagar fatura</a>
    &nbsp;|&nbsp;
    <a href="{{ object.access_url }}#nfse" style="...">Ver NFS-e</a>
  </p>
  <p>Se já pagou, desconsidere este email.</p>
  <p>— {{ user.name }}<br/>{{ user.email }}</p>
</div>
```

Padrões de retenção a embutir no template:

| Padrão                | Implementação                                   |
|-----------------------|-------------------------------------------------|
| Desconto de fidelidade| `round(amount_residual * 0.9, 2)`               |
| Urgência positiva     | "Pague até X e ganhe Y% off"                    |
| Ancoragem no projeto  | Mencionar serviço/projeto em andamento          |
| Facilitação           | CTAs: PIX, cartão, boleto                       |
| Tom humano            | Assinado por pessoa, não "Equipe" genérica      |
| Fallback              | "Se já pagou, desconsidere"                     |

## 7. Verificar e ativar o Cron

```python
odoo("ir.cron", "search_read",
    [[("model_id.model", "=", "base.automation"), ("active", "=", True)]],
    {"fields": ["name", "active", "interval_number", "interval_type", "nextcall"],
     "limit": 1})
```

Se inativo, ative via UI: **Configurações → Técnico → Automação → Scheduled Actions**.

## 8. Teste Rápido

1. Contabilidade → Clientes → Faturas → Novo
2. Verifique o seletor de empresa correto
3. Parceiro com `property_account_receivable_id` da mesma empresa
4. Linha com conta de receita da mesma empresa
5. Vencimento: 3 dias a partir de hoje (para testar Auto 1)
6. Confirmar (postar)
7. Configurações → Técnico → Automação → Scheduled Actions
   → "Automation Rules: check and execute" → **Run Manually**
8. Inspecione a Aba "Logs"/"Executions" da regra de automação

## 9. Troubleshooting

### `Account belongs to another company` (`_check_company`)

**Causa:** `property_account_receivable_id` do parceiro pertence a outra empresa.

**Fix UI:** Contabilidade → Configuração → Contas, filtre por empresa da fatura,
garanta conta `asset_receivable` para essa empresa.

**Fix SQL (diagnóstico):**
```sql
SELECT id, code, name, account_type, company_id
FROM account_account
WHERE account_type = 'asset_receivable';
```

**Workaround:** criar fatura via UI (Odoo resolve contas automaticamente) ou via
Odoo Shell com `allowed_company_ids=[EMPRESA_ID]` no contexto.

### `Failed to render inline_template — format not defined`

**Causa:** `{{ "%.2f"|format(valor) }}` no template.
**Fix:** `{{ round(valor, 2) }}`.

### `Wrong value for ir.actions.server.state: 'email'`

**Causa:** `state='email'` em vez de `state='mail_post'`.

### `Delay must be positive. Set 'Delay mode' to 'Before'`

**Causa:** `trg_date_range` negativo (ex: -3).
**Fix:** `trg_date_range=3` + `trg_date_range_mode='before'`.

## 10. Módulo Odoo Reutilizável (para clientes)

Para distribuir como brinde/upsell no Odoo.sh:

```
conexaoazul_cobranca_email/
├── __init__.py
├── __manifest__.py          # depends: ['account', 'mail', 'base_automation']
├── hooks.py                 # post_init_hook cria template + actions por empresa
├── models/
│   ├── __init__.py
│   └── res_company.py       # Campos: desconto %, dias antes/depois, ativo
├── views/
│   └── res_company_views.xml  # Aba "Cobrança" no formulário de empresa
└── security/
    └── ir.model.access.csv
```

**O que o hook faz na instalação:**

1. Cria `mail.template` global (1x)
2. Cria `ir.actions.server` globais (2x: antes + depois)
3. Para cada empresa ativa, cria 2 `base.automation` com `filter_domain`
   filtrando por `company_id`
4. Desativa auto actions genéricas antigas (sem filtro de empresa)

**Instalação no Odoo.sh:**

```bash
# Empacotar
zip -r conexaoazul_cobranca_email.zip conexaoazul_cobranca_email/
# Odoo.sh → Import Module → Upload
# Apps → Atualizar lista → Instalar "Conexão Azul — Cobrança por Email"
```

**Configuração por empresa:**

Configurações → Empresas → [Sua Empresa] → aba "Cobrança":

- Desconto de Fidelidade (%): 10
- Dias de Antecedência: 3
- Dias de Follow-up: 1
- Ativar Cobrança Automática: [x]

## 11. Resumo de IDs (referência)

| Componente     | Nome sugerido                              | Modelo              |
|----------------|--------------------------------------------|---------------------|
| Mail Template  | `Cobrança: Lembrete com Desconto`          | `account.move`      |
| Server Action  | `Enviar Cobrança com Desconto`             | `ir.actions.server` |
| Auto Action 1  | `Cobrança Auto: 3 dias antes do vencimento`| `base.automation`   |
| Auto Action 2  | `Follow-up Auto: 1 dia após vencimento`    | `base.automation`   |

## 12. Referências

- [Odoo 19 docs — mail.template](https://www.odoo.com/documentation/19.0/reference/reports.html)
- [Odoo 19 docs — Automated Actions](https://www.odoo.com/documentation/19.0/automations.html)
- Skill companheira: `../odoo-asaas-nfse-ops/` (cobrança sempre com NFS-e)
- Script de envio: `scripts/send_invoice_email.py`