# Odoo Claude Skills — Conexão Azul Digital

Skills para operar **Odoo 19 com IA** usando [Claude Code](https://claude.ai/code).
Integração JSON-RPC — funciona em Odoo.sh, VPS ou on-premise. Sem acesso SSH necessário.

## 4 Skills incluídas

| Skill | Versão | Função |
|-------|--------|--------|
| [`asaas-nfse-quicktest`](skills/asaas-nfse-quicktest/) | 1.0.0 | **Debug rápido de emissão de NFS-e via API Asaas** — catálogo de erros, payload-modelo, pré-requisitos (endereço do cliente, ISS por município), fluxo emit→authorize→monitor |
| [`odoo-asaas-nfse-ops`](skills/odoo-asaas-nfse-ops/) | 2.0.0 | Diagnosticar e corrigir emissão de NFS-e no **lado Odoo** (módulo Asaas, webhook, bugs conhecidos, validador JSON-RPC) |
| [`odoo-cobranca-email`](skills/odoo-cobranca-email/) | 2.0.0 | Automatizar lembretes de fatura nativos no Odoo (régua, templates, `mail.mail`/`message_post`) — com política cobrança sempre com NFS-e |
| [`odoo-sales-crm`](skills/odoo-sales-crm/) | 2.0.0 | Consultar pipeline, criar propostas, monitorar vendas (CRM, `sale.order`, pricelists, atividades) |

> **NFSe + Cobrança:** use `asaas-nfse-quicktest` (lado API Asaas) + `odoo-asaas-nfse-ops`
> (lado módulo Odoo) juntos. A cobrança a cliente faturável deve seguir sempre com a NFS-e
> emitida e linkada (`--payment` vincula a nota à cobrança Asaas).

---

## Instalação rápida (Claude Code Desktop ou VS Code)

```bash
# 1. Clone o repositório
git clone https://github.com/conexaoazul/odoo-claude-skills.git
cd odoo-claude-skills

# 2. Copie as skills para o seu projeto Claude Code
cp -r skills/ /caminho/do/seu/projeto/.claude/skills/

# 3. Configure o .env (copie o exemplo e preencha)
cp .env.example .env
# Edite o .env com suas credenciais Odoo + Asaas
```

## Configuração mínima (.env)

```bash
# Odoo
ODOO_URL=https://seu-odoo.odoo.com      # ou https://meusite.odoo.sh
ODOO_DB=seu_banco
ODOO_UID=2
ODOO_PWD=sua_senha_aqui

# Asaas (para skills de NFSe — painel.asaas.com > Integrações > API)
ASAAS_ACCESS_TOKEN=aact_prod_...
```

> **Token Asaas começa com `$aact_...`.** Em shell, use **aspas simples** ou salve em
> arquivo e leia com `KEY=$(cat arquivo)` — aspas duplas expandem `$aact` para vazio e
> causam HTTP 401.

## Como usar com Claude Code

Após instalar, no Claude Code diga:

```
Leia skills/asaas-nfse-quicktest/SKILL.md e me ajude a emitir uma NFS-e
via API Asaas vinculada a uma cobrança existente.
```

```
Leia skills/odoo-asaas-nfse-ops/SKILL.md e me ajude a diagnosticar
por que minha NFS-e não está sendo emitida no Odoo.
```

```
Leia skills/odoo-sales-crm/SKILL.md e liste as oportunidades abertas
do meu CRM em ordem de valor.
```

```
Leia skills/odoo-cobranca-email/SKILL.md e crie uma automação para
enviar lembretes de fatura 3 dias antes do vencimento, com link da NFS-e.
```

## QuickTest — Emitir NFS-e em ~2 minutos (API Asaas direta)

```bash
pip3 install requests
export ASAAS_ACCESS_TOKEN='aact_prod_...'
python3 skills/asaas-nfse-quicktest/scripts/quicktest.py \
  --customer cus_XXXXXXXXXXXXXXX \
  --service-description "Nota fiscal da Fatura XXX. Descricao dos Servicos: 1.06 - Assessoria e consultoria em informatica." \
  --municipal-service-id "XXXXX" \
  --municipal-service-name "1.06 - Assessoria e consultoria em informatica." \
  --nbs-code "X.XXXX.XX.XX" \
  --iss 2.0 \
  --value 400.00 \
  --payment pay_XXXXXXXXXXXXXXX \
  --monitor 300
```

**Antes de emitir, garanta:** (1) cliente com endereço completo no Asaas
(`PUT /customers` com `city{ibgeCode}` — sem CEP a API retorna 400); (2) `effectiveDate`
é hoje (data passada = 400); (3) `iss`, `municipalServiceId` e `nbsCode` **variam por
município** — consulte a alíquota/códigos da sua prefeitura; (4) cheque
`GET /invoices?customer=...` antes de emitir para não duplicar nota.

## Validador Odoo + NFSe (lado módulo)

```bash
export ODOO_URL="https://seu-odoo.odoo.com"
export ODOO_DB="seu_banco"
export ODOO_UID=2
export ODOO_PWD="sua_senha"
pip3 install requests
python3 skills/odoo-asaas-nfse-ops/scripts/validate_nfse.py
```

## Suporte

Skills mantidas por [Conexão Azul Digital](https://conexaoazul.com).
Para suporte técnico assistido com Claude Code, entre em contato.