# Odoo Claude Skills — Conexão Azul Digital

Skills para operar **Odoo 19 com IA** usando [Claude Code](https://claude.ai/code).  
Integração JSON-RPC — funciona em Odoo.sh, VPS ou on-premise. Sem acesso SSH necessário.

## 3 Skills incluídas

| Skill | Função |
|-------|--------|
| [`odoo-asaas-nfse-ops`](skills/odoo-asaas-nfse-ops/) | Diagnosticar e corrigir emissão de NFSe via Asaas |
| [`odoo-cobranca-email`](skills/odoo-cobranca-email/) | Automatizar lembretes de fatura nativos no Odoo |
| [`odoo-sales-crm`](skills/odoo-sales-crm/) | Consultar pipeline, criar propostas, monitorar vendas |

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
# Edite o .env com suas credenciais Odoo
```

## Configuração mínima (.env)

```bash
# Odoo
ODOO_URL=https://seu-odoo.odoo.com      # ou https://meusite.odoo.sh
ODOO_DB=seu_banco
ODOO_UID=2
ODOO_PWD=sua_senha_aqui

# Asaas (para skill NFSe)
ASAAS_ACCESS_TOKEN=aact_prod_...
```

## Como usar com Claude Code

Após instalar, no Claude Code diga:

```
Leia skills/odoo-asaas-nfse-ops/SKILL.md e me ajude a diagnosticar
por que minha NFSe não está sendo emitida.
```

```
Leia skills/odoo-sales-crm/SKILL.md e liste as oportunidades abertas
do meu CRM em ordem de valor.
```

```
Leia skills/odoo-cobranca-email/SKILL.md e crie uma automação para
enviar lembretes de fatura 3 dias antes do vencimento.
```

## QuickTest — Validar NFSe em 60 segundos

```bash
pip3 install requests
export ASAAS_ACCESS_TOKEN="aact_prod_..."
python3 skills/odoo-asaas-nfse-ops/scripts/quicktest.py \
  --customer cus_XXXXXXXXXXXXXXX \
  --service-description "Suporte tecnico em informatica" \
  --service-list-item "01.07" \
  --municipal-service-id "292180" \
  --value 5.00
```

## Validador Odoo + NFSe

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
