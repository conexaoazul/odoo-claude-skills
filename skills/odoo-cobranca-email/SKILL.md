---
name: odoo-cobranca-email-automation
description: Automatizar cobranças e follow-ups de faturas no Odoo 19 via mail.templates, server actions e automated actions. Inclui desconto de fidelidade, anexos PDF, retenção anti-churn e troubleshooting multi-company.
---

# Odoo Cobrança por Email — Automação Nativa

Skill para criar e operar automação de cobrança diretamente no Odoo 19, sem dependência externa (n8n, scripts).

## Quando usar

- Cliente tem fatura em aberto e precisa de lembrete por email
- Quer aplicar desconto de fidelidade (ex: 10% antecipado) automaticamente
- Precisa de follow-up escalonado (3 dias antes + 1 dia depois do vencimento)
- PDF da fatura deve ir como anexo automaticamente
- Foco em retenção: evitar churn com tom humano e ancoragem no projeto

## NÃO usar quando

- Odoo não tem módulo `account` instalado
- Não há contas contábeis configuradas por empresa ( blocker `_check_company` )
- API externa (SMTP, Asaas) está indisponível

---

## Pré-requisitos

1. **Módulos instalados:** `account`, `mail`, `base_automation`
2. **Cron ativo:** `Automation Rules: check and execute` (ir.cron)
3. **Conta SMTP configurada** no Odoo (Configurações → Geral → Servidor de Email)
4. **Contas contábeis por empresa** (`asset_receivable`, `income`) — ver § Troubleshooting

---

## Arquitetura da Automação

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

| Componente | Modelo Odoo | Função |
|------------|-------------|--------|
| Mail Template | `mail.template` | HTML estilizado + variáveis Jinja2 + anexo PDF |
| Server Action | `ir.actions.server` | `state='mail_post'` dispara o email |
| Automated Action | `base.automation` | Trigger `on_time` relativo ao `invoice_date_due` |
| Cron | `ir.cron` | Processa triggers pendentes a cada N minutos |

---

## 1. Criar Mail Template

### Via API (JSON-RPC)

```python
payload = {
    'jsonrpc': '2.0',
    'method': 'call',
    'params': {
        'service': 'object',
        'method': 'execute_kw',
        'args': [DB, UID, PWD, 'mail.template', 'create', [{
            'name': 'Cobrança: Lembrete com Desconto de Fidelidade',
            'model_id': MODEL_ID_ACCOUNT_MOVE,  # ir.model where model='account.move'
            'subject': '🎁 Oferta especial — R$ {{ round(object.amount_residual * 0.9, 2) }} (desconto)',
            'email_from': '{{ user.email_formatted }}',
            'partner_to': '{{ object.partner_id.id }}',
            'body_html': '<div style="...">...HTML completo...</div>',
            'lang': '${object.partner_id.lang}',
            'auto_delete': False,
        }]],
    },
    'id': 1,
}
```

### Variáveis Jinja2 disponíveis

| Variável | Significado | Exemplo de uso |
|----------|-------------|---------------|
| `object.partner_id.name` | Nome do cliente | Saudação personalizada |
| `object.amount_residual` | Valor em aberto | Cálculo de desconto |
| `round(x, 2)` | Arredondar valor | Odoo 19 safe_eval não aceita `\|format` |
| `object.invoice_date_due` | Data de vencimento | Urgência do desconto |
| `object.invoice_line_ids[0].name` | Descrição do serviço | Contextualização |
| `user.name` / `user.email` | Assinatura do vendedor | Tom humano |

> ⚠️ **Odoo 19 safe_eval:** NÃO usar `"%.2f"\|format(...)`. Usar `round(..., 2)`.

### Anexar PDF da fatura

Após criar o template, vincular o relatório:

```python
# Buscar report_id de account.report_invoice_with_payments
# Atualizar template
write_vals = {'report_template_ids': [(4, REPORT_ID, 0)]}
```

---

## 2. Criar Server Action

```python
server_action_vals = {
    'name': 'Enviar Cobrança com Desconto',
    'model_id': MODEL_ID_ACCOUNT_MOVE,
    'state': 'mail_post',  # ⚠️ Odoo 19 usa 'mail_post', não 'email'
    'type': 'ir.actions.server',
    'template_id': TEMPLATE_ID,
    'usage': 'ir_actions_server',
}
```

Valores válidos de `ir.actions.server.state` no Odoo 19:
- `mail_post` → Enviar email (usar este!)
- `object_write` → Atualizar registro
- `code` → Executar código Python
- `webhook` → Enviar webhook

---

## 3. Criar Automated Actions

### 3.1 Trigger: 3 dias ANTES do vencimento

```python
automation_vals = {
    'name': 'Cobrança Auto: 3 dias antes do vencimento',
    'model_id': MODEL_ID_ACCOUNT_MOVE,
    'trigger': 'on_time',
    'trg_date_id': FIELD_ID_INVOICE_DATE_DUE,  # ir.model.fields
    'trg_date_range': 3,        # POSITIVO
    'trg_date_range_type': 'day',
    'trg_date_range_mode': 'before',   # "antes"
    'filter_domain': "[('move_type', '=', 'out_invoice'), ('payment_state', '!=', 'paid'), ('state', '=', 'posted')]",
    'action_server_ids': [(0, 0, {
        'name': 'Enviar Cobrança',
        'model_id': MODEL_ID_ACCOUNT_MOVE,
        'state': 'mail_post',
        'template_id': TEMPLATE_ID,
    })],
}
```

### 3.2 Trigger: 1 dia DEPOIS do vencimento

```python
automation_vals = {
    'name': 'Follow-up Auto: 1 dia após vencimento',
    'model_id': MODEL_ID_ACCOUNT_MOVE,
    'trigger': 'on_time',
    'trg_date_id': FIELD_ID_INVOICE_DATE_DUE,
    'trg_date_range': 1,
    'trg_date_range_type': 'day',
    'trg_date_range_mode': 'after',    # "depois"
    'filter_domain': "[('move_type', '=', 'out_invoice'), ('payment_state', '!=', 'paid'), ('state', '=', 'posted')]",
    'action_server_ids': [(0, 0, {
        'name': 'Enviar Follow-up',
        'model_id': MODEL_ID_ACCOUNT_MOVE,
        'state': 'mail_post',
        'template_id': TEMPLATE_ID,
    })],
}
```

> ⚠️ **Regra de delay no Odoo 19:**
> - `trg_date_range` deve ser **sempre positivo**
> - Use `trg_date_range_mode='before'` para dias antes
> - Use `trg_date_range_mode='after'` para dias depois

---

## 4. Verificar e ativar o Cron

```python
# Buscar cron
payload = {
    'service': 'object',
    'method': 'execute_kw',
    'args': [DB, UID, PWD, 'ir.cron', 'search_read',
        [[('model_id.model', '=', 'base.automation'), ('active', '=', True)]],
        {'fields': ['name', 'active', 'interval_number', 'interval_type', 'nextcall'], 'limit': 1}],
}
```

Se inativo, ativar via UI: **Configurações → Técnico → Automação → Scheduled Actions**

---

## 5. Teste Rápido

### 5.1 Criar fatura de teste

Via UI Odoo (recomendado — evita erros multi-company):
1. Contabilidade → Clientes → Faturas → Novo
2. Empresa: verifique se o seletor está na empresa correta
3. Parceiro: escolher um com `property_account_receivable_id` da mesma empresa
4. Produto/Serviço: linha com conta de receita da mesma empresa
5. Vencimento: **3 dias a partir de hoje** (para testar Auto 1)
6. Confirmar (postar)

### 5.2 Acelerar o cron (não esperar)

```
Configurações → Técnico → Automação → Scheduled Actions
→ "Automation Rules: check and execute"
→ [Run Manually]
```

### 5.3 Verificar log

```
Configurações → Técnico → Automação → Regras de Automação
→ Abrir a automation → Aba "Logs" ou "Executions"
```

---

## 6. Troubleshooting

### Erro: `_check_company` — "Account belongs to another company"

**Causa:** Conta contábil padrão do parceiro (`property_account_receivable_id`) pertence a empresa diferente da fatura.

**Fix via UI:**
1. Contabilidade → Configuração → Contabilidade → Contas
2. Filtrar por empresa da fatura (ex: BlueConnect)
3. Verificar se existe conta `asset_receivable` para essa empresa
4. Se não existir, criar ou ajustar properties do parceiro

**Fix via SQL (admin only):**
```sql
-- Verificar accounts a receber
SELECT id, code_store, name, account_type 
FROM account_account 
WHERE account_type = 'asset_receivable';

-- Parceiro com company crossover = sempre falha via API
-- Criar fatura via Odoo Shell com SUPERUSER e contexto allowed_company_ids
```

**Workaround prático:**
- Criar fatura manualmente no UI (o Odoo resolve automaticamente as contas)
- Ou usar Odoo Shell com `allowed_company_ids=[EMPRESA_ID]` no contexto

### Erro: "Failed to render inline_template — `format` not defined"

**Causa:** Usou `{{ "%.2f"|format(valor) }}` no subject/body.

**Fix:** Usar `{{ round(valor, 2) }}` — Odoo 19 safe_eval não injeta `format`.

### Erro: "Wrong value for ir.actions.server.state: 'email'"

**Causa:** Usou `state='email'` em vez de `state='mail_post'`.

**Fix:** `mail_post` é o valor correto no Odoo 19.

### Erro: "Delay must be positive. Set 'Delay mode' to 'Before'"

**Causa:** `trg_date_range` negativo (ex: -3).

**Fix:** Use `trg_date_range=3` + `trg_date_range_mode='before'`.

---

## 7. Padrões de Retenção (Anti-Churn)

Incluir no template HTML:

| Padrão | Implementação no email |
|--------|------------------------|
| Desconto de fidelidade | `round(amount_residual * 0.9, 2)` |
| Urgência positiva | "Pague até X e ganhe Y% off" |
| Ancoragem no projeto | Mencionar white-label/Kanban/Chatwoot em andamento |
| Social proof | "Clientes que mantêm ritmo evitam churn" |
| Facilitação | 3 CTAs: PIX, cartão, boleto |
| Tom humano | Assinado por pessoa (Diego Santos), não "Equipe" genérica |
| Fallback | "Se já pagou, desconsidera" |

---

## 8. Resumo de IDs (referência)

| Componente | Nome sugerido | Modelo |
|----------|---------------|--------|
| Mail Template | `Cobrança: Lembrete com Desconto de Fidelidade` | `account.move` |
| Server Action | `Enviar Cobrança com Desconto` | `ir.actions.server` |
| Auto Action 1 | `Cobrança Auto: 3 dias antes do vencimento` | `base.automation` |
| Auto Action 2 | `Follow-up Auto: 1 dia após vencimento` | `base.automation` |

---

## Arquivos relacionados

- [[odoo-19-company-dependent-account-fix]] — como resolver `asset_receivable` multi-company
- [[odoo-rpc-api]] — padrões JSON-RPC para Odoo
- [[asaas-email-automation]] — envio de cobrança via API Asaas + SMTP
- `scripts/generate_daily_growth_roi.sh` — cockpit diário de ROI/carteira em modo read-only
- `scripts/validate_daily_growth_roi.sh` — valida artefatos obrigatórios do cockpit diário
- `scripts/validate_human_collection_campaign.sh` — valida campanha humana em dry-run antes de qualquer envio

---

Última revisão: 2026-06-09
Autor: Dhy (Conexão Azul Digital)

## 9. Módulo Odoo Reutilizável (para clientes)

Para distribuir essa automação como **brinde ou upsell** para clientes no Odoo.sh:

### Estrutura do módulo

```
conexaoazul_cobranca_email/
├── __init__.py
├── __manifest__.py          # Depends: ['account', 'mail', 'base_automation']
├── hooks.py                  # post_init_hook cria template + actions por empresa
├── models/
│   ├── __init__.py
│   └── res_company.py        # Campos: desconto%, dias antes/depois, ativo
├── views/
│   └── res_company_views.xml # Aba "Cobrança" no formulário de empresa
└── security/
    └── ir.model.access.csv
```

### O que o hook faz na instalação

1. Cria **mail.template** global (1x)
2. Cria **server actions** globais (2x: antes + depois)
3. Para **cada empresa ativa**, cria 2 `base.automation` com `filter_domain` filtrando por `company_id`
4. Desativa auto actions genéricas antigas (sem filtro de empresa)

### Como instalar no cliente

```bash
# 1. Zipar o módulo
cd workspace/projects/
zip -r conexaoazul_cobranca_email.zip conexaoazul_cobranca_email/

# 2. Enviar ao cliente ou subir no Odoo.sh
# Odoo.sh → Import Module → Upload

# 3. Ativar
# Apps → Atualizar lista de apps → Instalar "Conexão Azul — Cobrança por Email"
```

### Configuração por empresa

Após instalação:
```
Configurações → Empresas → [Sua Empresa] → aba "Cobrança"
  • Desconto de Fidelidade (%): 10
  • Dias de Antecedência: 3
  • Dias de Follow-up: 1
  • Ativar Cobrança Automática: ✅
```

### Vantagens de entregar como módulo

| Aspecto | API/Script | Módulo Odoo |
|---|---|---|
| Instalação | Manual, técnico | 1 clique no Odoo.sh |
| Atualização | Reexecutar scripts | Atualizar módulo |
| Configuração | Hardcoded | UI por empresa |
| Portabilidade | Depende de credenciais | Self-contained |
| Valor percebido | "Script" | "Feature premium" |

---
Última revisão: 2026-06-09
Autor: Dhy (Conexão Azul Digital)
Versão módulo: 1.0.0

---

## 10. Daily Growth ROI + Campanha Humana Segura

Use este workflow quando o objetivo for recuperar caixa, priorizar clientes, preparar mensagens humanas ou validar a campanha diária sem disparar comunicação. Ele complementa a automação Odoo: antes de qualquer cobrança automática, gere a carteira, aplique exceções e valide os gates humanos.

### Scripts oficiais

Todos ficam em `/docker/openclaw/.openclaw/scripts` (`scripts` é symlink para `workspace/scripts`):

| Script | Função | Modo |
|---|---|---|
| `generate_daily_growth_roi.sh` | Gera cockpit CEO, snapshot Asaas/Odoo, board ROI e chama validação de campanha | read-only/dry-run |
| `validate_daily_growth_roi.sh` | Confere se os relatórios diários obrigatórios existem e têm conteúdo mínimo | read-only |
| `validate_human_collection_campaign.sh` | Garante que campanha está em dry-run, com exceções e gates antes de envio | read-only |

### Ordem recomendada

```bash
cd /docker/openclaw/.openclaw

# 1. Gerar cockpit/board do dia em modo read-only.
# Observação: o script aceita a data como primeiro argumento direto.
bash scripts/generate_daily_growth_roi.sh "$(date +%Y-%m-%d)"

# 2. Validar pacote completo de Growth ROI.
bash scripts/validate_daily_growth_roi.sh "$(date +%Y-%m-%d)"

# 3. Validar guardrails de campanha humana.
bash scripts/validate_human_collection_campaign.sh
```

### Interpretação de status

- `APROVADO`: artefatos prontos para revisão executiva. Ainda não autoriza envio.
- `APROVADO COM RESSALVAS`: Diego/Claude devem revisar avisos antes de qualquer contato externo.
- `BLOQUEADO`: não enviar, não automatizar e não instalar cron; corrigir fila/relatórios primeiro.

### Gates obrigatórios antes de contato externo

- `APROVO ENVIO`: obrigatório para qualquer email/WhatsApp/mensagem.
- Aprovação explícita por email de Diego: obrigatória para iniciar janela de 48h de campanha.
- `APROVO FINANCEIRO`: obrigatório para cancelar, arquivar, criar ou alterar cobrança no Asaas/Odoo.
- `APROVO APPLY`: obrigatório para qualquer alteração técnica em Odoo, Cloudflare, cron ou produção.

### Exceções que a validação deve proteger

- Carlos/teste: excluir de indicadores e não contatar.
- IMTECH / Im Tecnologia: `VIP_CONCILIACAO_NFSE`, nunca cobrança comum antes de conciliação.
- MORIA: retenção, cobrar no máximo uma mensalidade e com tom humano.
- CB TEC: delivery/validation, não faturar antes de aceite.
- C4 Associados: nicho/cross-sell, não cobrança automática.
- Thiago Santos: em dia/report de valor, não cobrar.

### Arquivos esperados no relatório diário

O validador procura em `reports/`:

- `daily-ceo-cockpit-YYYY-MM-DD.md`
- `customer-persona-engine-YYYY-MM-DD.csv`
- `action-queue-daily-YYYY-MM-DD.csv`
- `action-queue-money-now-refined-YYYY-MM-DD.csv`
- `projection-3-scenarios-YYYY-MM-DD.md`
- `messages-daily-growth-YYYY-MM-DD.md`
- `messages-client-specific-refined-YYYY-MM-DD.md`
- `client-exception-rules-YYYY-MM-DD.md`
- planos específicos de IMTECH, MORIA, CB TEC e campanha de nicho.

### O que estes scripts NÃO fazem

- Não enviam mensagens.
- Não alteram Asaas.
- Não alteram Odoo.
- Não instalam cron.
- Não autorizam cobrança automática.
- Não substituem revisão humana quando houver VIP, churn, aceite pendente ou dados divergentes.

### Bugs/atenções validados em 2026-06-14

- `validate_daily_growth_roi.sh` pode gerar falso bloqueio: em uma execução marcou `daily-ceo-cockpit-YYYY-MM-DD.md` como existente e faltante no mesmo run. Antes de bloquear ação executiva, verificar o arquivo manualmente e corrigir a lista/loop do validador.
- `generate_daily_growth_roi.sh` deve escapar valores monetários com `$` dentro de heredoc. String como `R$1.400` pode virar `R<arg>.400` quando o script recebe uma data como `$1`. Usar `R\$1.400` ou heredoc protegido quando necessário.
- A linha `print('snapshot_errors:', len(errs))` observada na sessão estava em comando ad-hoc de shell/Cloudflare API, não em script local reutilizável. Se for usada novamente, mover para script seguro e versionado sem token inline.
