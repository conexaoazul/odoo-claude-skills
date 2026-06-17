---
name: odoo-asaas-nfse-ops
description: "Diagnosticar, configurar e operar emissão de NFSe via Asaas no Odoo 19. Cobre bugs conhecidos, checklist de configuração, validador JSON-RPC e catálogo de erros."
version: 1.0.0
author: Conexão Azul Digital
tags: [odoo, asaas, nfse, fiscal, brasil, json-rpc]
---

# Odoo × Asaas NFSe — Diagnóstico e Operação

Skill para configurar, diagnosticar e corrigir emissão de NFSe integrada com Asaas no Odoo 19.
Funciona em qualquer Odoo 19 — Odoo.sh, VPS, on-premise.

## Configuração (.env)

```bash
export ODOO_URL="https://seu-odoo.odoo.com"
export ODOO_DB="seu_banco"
export ODOO_UID=2
export ODOO_PWD="sua_senha"
export ASAAS_ACCESS_TOKEN="aact_prod_..."
```

## 1. Arquitetura do Pipeline NFSe

```
Cliente Odoo ──► Webhook Asaas ──► Odoo Controller ──► GINFES/Prefeitura
                                          │
                              [payment.provider asaas]  ← Falha #1: filtro active
                              [res.company asaas_info]  ← Falha #2: campo ausente
```

## 2. Bug #1 — Provider lookup retorna vazio

**Sintoma:** `"Provider não encontrado"` no webhook.

**Causa:** filtro `('active', '=', True)` bloqueia provider arquivado.

**Fix no código** (`blue_payment_asaas_nfse/controllers/webhook.py` ~linha 578):
```python
# REMOVER a linha com active=True:
provider = request.env['payment.provider'].sudo().search([
    ('code', '=', 'asaas'),
    # ('active', '=', True),  ← remover
], limit=1)
```

**Verificar via JSON-RPC:**
```python
providers = odoo("payment.provider", "search_read",
    [[["code", "=", "asaas"]]],
    {"fields": ["id", "name", "state", "active"],
     "context": {"active_test": False}})
print(providers)
```

## 3. Bug #2 — Campo `asaas_account_info` ausente

**Sintoma:** `column "asaas_account_info" does not exist`

**Fix via XML migration** (adicionar ao módulo + atualizar):
```xml
<odoo>
  <record model="ir.model.fields" id="field_res_company_asaas_account_info">
    <field name="name">asaas_account_info</field>
    <field name="model_id" ref="base.model_res_company"/>
    <field name="field_description">Asaas Account Info</field>
    <field name="ttype">char</field>
  </record>
</odoo>
```

## 4. Checklist de Configuração NFSe

```
[ ] Provider Asaas: ativo, api_key preenchida, auto_create_nfse=True
[ ] service_list_item preenchido (ex: "01.07")
[ ] municipal_service_id preenchido (código da prefeitura)
[ ] Empresa: CNPJ, regime tributário (simples_nacional), CNAE
[ ] Certificado A1 válido no painel Asaas
[ ] URL webhook configurada: https://seu-odoo.odoo.com/payment/asaas/webhook
```

## 5. Catálogo de Erros

| Erro | Causa | Ação |
|------|-------|------|
| `GW234` | Certificado A1 inválido | Renovar em Asaas > Certificado |
| `"Dados obrigatórios"` | Config fiscal incompleta | Completar CNPJ + regime |
| `400 municipalServiceName` | Campo ausente | Preencher no provider |
| `SYNCHRONIZED → ERROR` | Prefeitura rejeitou | Verificar cert + portal prefeitura |
| `"Provider não encontrado"` | Bug #1 | Aplicar fix §2 |
| `column does not exist` | Bug #2 | Aplicar fix §3 |

## 6. Validador JSON-RPC completo

Ver script: `scripts/validate_nfse.py`

```bash
pip3 install requests
python3 scripts/validate_nfse.py
```

## 7. Referências

- [Docs Asaas NFSe](https://docs.asaas.com/reference/create-invoice)
- [Módulos BlueApps](https://github.com/conexaoazul/blueapps)
- Skill QuickTest: `../asaas-nfse-quicktest/`
