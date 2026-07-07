---
name: odoo-asaas-nfse-ops
description: "Diagnosticar, configurar e operar emissão de NFS-e via Asaas no Odoo 19. Cobre bugs conhecidos do módulo, checklist de configuração, validador JSON-RPC, catálogo de erros e fluxo de emissão multi-empresa."
version: 2.0.0
author: Conexão Azul Digital
tags: [odoo, asaas, nfse, fiscal, brasil, json-rpc]
---

# Odoo × Asaas NFS-e — Diagnóstico e Operação

Skill para configurar, diagnosticar, corrigir e emitir NFS-e integrada com Asaas no Odoo 19.
Funciona em qualquer Odoo 19 — Odoo.sh, VPS, on-premise. Cobertura de bugs do módulo
`blue_payment_asaas_nfse`, fluxo de emissão via API Asaas v3 e boas práticas de cobrança.

## Configuração (.env)

```bash
export ODOO_URL="https://seu-odoo.odoo.com"
export ODOO_DB="seu_banco"
export ODOO_UID=2
export ODOO_PWD="sua_senha"
export ASAAS_ACCESS_TOKEN='aact_prod_...'   # SEMPRE aspas simples (ver §6)
```

## 1. Arquitetura do Pipeline NFS-e

```
Cliente Odoo ──► Webhook Asaas ──► Odoo Controller ──► GINFES/Prefeitura
                                          │
                              [payment.provider asaas]  ← Falha #1: filtro active
                              [res.company asaas_info]  ← Falha #2: campo ausente
                              [POST /invoices API v3]   ← Falha #3: payload inconsistente
```

Cada `res.company` pode ter seu próprio `payment.provider` Asaas com `asaas_api_key`
próprio (multi-empresa). Para emitir na conta de outra empresa, veja §5.

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
    {"fields": ["id", "name", "state", "active", "company_id", "asaas_api_key"],
     "context": {"active_test": False}})
# Nunca imprimir o valor de asaas_api_key — apenas se está preenchido.
for p in providers:
    print(p["id"], p["name"], p["state"], "company", p.get("company_id"),
          "has_key" if p.get("asaas_api_key") else "no_key")
```

## 3. Bug #2 — Campo `asaas_account_info` ausente

**Sintoma:** `column "asaas_account_info" does not exist` no webhook.

**Fix via XML migration** (adicionar ao módulo + rodar `-u` no banco):
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

Em ambientes controlados, pode-se criar a coluna direto via SQL:
`ALTER TABLE res_company ADD COLUMN IF NOT EXISTS asaas_account_info VARCHAR;`
(preferir via módulo para manter rastreabilidade do ORM).

## 4. Checklist de Configuração NFS-e

```
[ ] Provider Asaas: api_key preenchida, auto_create_nfse=True (ativo ou não)
[ ] service_list_item preenchido (ex: "01.07" — código LC 116/2003)
[ ] municipal_service_id preenchido (código da prefeitura — varia por município!)
[ ] nbsCode correto para o município (varia — consultar contador/prefeitura)
[ ] Empresa: CNPJ, regime tributário (simples_nacional), CNAE, inscrição municipal
[ ] Certificado A1 válido enviado no painel Asaas (certificateSent=true)
[ ] URL webhook configurada: https://seu-odoo.odoo.com/payment/asaas/webhook
[ ] Cliente com endereço completo (CEP, rua, número, bairro, cidade/IBGE) — ver §7
```

## 5. Multi-empresa — pegar a API key da empresa certa

O módulo permite múltiplos providers Asaas, um por `res.company`. Para emitir na conta
de outra empresa, busque a key no Odoo via JSON-RPC:

```python
# Listar todos os providers Asaas com sua company
providers = odoo("payment.provider", "search_read",
    [[["code", "=", "asaas"]]],
    {"fields": ["id", "name", "company_id", "asaas_api_key"],
     "context": {"active_test": False}})

# Filtrar pela company desejada (ex: company_id == 3)
target = next(p for p in providers if (p.get("company_id") or [None])[0] == 3)
api_key = target["asaas_api_key"]   # NÃO imprimir nem persistir — usar direto no header
```

Nunca logar, salvar em arquivo de texto, ou imprimir `asaas_api_key`. Use direto no
header `access_token` da request. Para validação, exiba apenas `"has_key"`/`"no_key"`.

## 6. Emissão via API Asaas v3 — payload-modelo

**Atenção:** ISS, `municipalServiceId`, `municipalServiceName`, `nbsCode` **variam por
município**. Nunca hardcodar — consultar `fiscalInfo` da conta e a prefeitura.

```python
import requests
from datetime import date
H = {"access_token": api_key, "Content-Type": "application/json"}
BASE = "https://api.asaas.com/v3"

payload = {
    "customer": "cus_XXX",                     # customer Asaas do cliente
    "type": "NFS-e",
    "payment": "pay_XXX",                      # opcional: vincula NFS-e à cobrança Asaas
    "serviceDescription": "Descrição do serviço prestado (máx 2000 chars).",
    "municipalServiceId": "<código da prefeitura>",      # varia por município
    "municipalServiceName": "1.06 - Consultoria em TI.", # varia por município
    "municipalServiceCode": "",
    "value": 400.0,
    "effectiveDate": date.today().isoformat(),  # SEMPRE hoje — passado = HTTP 400
    "observations": "Empresa optante pelo Simples Nacional. ...",
    "taxes": {
        "retainIss": False,
        "iss": <alíquota ISS da sua prefeitura>,  # ex: 5.0 (São Paulo), 2.0, 0…
        "pisCofinsRetentionType": "PIS_COFINS_CSLL_NOT_WITHHELD",
        "pisCofinsTaxStatus": "NONE",
        "inss": 0.0, "ir": 0.0,
        "nbsCode": "<NBS da sua cidade>"          # varia por município
    }
}
r = requests.post(f"{BASE}/invoices", headers=H, json=payload, timeout=30)
if r.status_code == 200:
    inv_id = r.json()["id"]                      # ex: inv_000XXXXXXXXXX
    requests.post(f"{BASE}/invoices/{inv_id}/authorize", headers=H, timeout=30)
    # Poll GET /invoices/{inv_id} a cada 10s até AUTHORIZED ou ERROR (~60-180s)
```

**Fluxo de status:**
```
SCHEDULED → SYNCHRONIZED → AUTHORIZED (ou ERROR)
```
`SYNCHRONIZED` por vários minutos é normal em prefeituras com processamento assíncrono.

### Endpoints que NÃO existem na API v3

| Endpoint | HTTP | Significado |
|----------|------|-------------|
| `POST /invoices/{id}/authorize` | 200 | Dispara autorização (use este) |
| `POST /invoices/{id}/retry` | 404 | Não existe |
| `POST /invoices/{id}/sync` | 404 | Não existe |
| `POST /invoices/{id}/resend` | 404 | Não existe |
| `POST /invoices/{id}/send` | 404 | Não existe |
| `PUT /invoices/{id}` | 200 | Read-only; NÃO altera status |

Não há endpoint para forçar reenvio. Apenas aguardar ou abrir ticket Asaas.

## 7. Pré-requisito: endereço completo do cliente

Cliente sem endereço → `POST /invoices` retorna **400**
`"Endereço do cliente incompleto.; CEP do cliente é inválido."`.
Fix **antes** de emitir:

```python
# PUT /customers/{id} com cidade via ibgeCode
body = {
    "postalCode": "XXXXXXXX",
    "address": "Rua Exemplo",
    "addressNumber": "123",
    "province": "Bairro Exemplo",
    "city": {"ibgeCode": "<código IBGE de 7 dígitos da sua cidade>"},
    "state": "ES",
    "country": "Brasil"
}
requests.put(f"{BASE}/customers/{cus_id}", headers=H, json=body, timeout=30)
```

### Lookup de CNPJ/endereço: BrasilAPI (público, sem token)

Quando você só tem o CNPJ do cliente, fallback público para obter endereço:
```
GET https://brasilapi.com.br/api/cnpj/v1/{cnpj}
→ { "cep", "logradouro", "numero", "bairro", "municipio", "uf" }
```
O código IBGE do município vem em tabelas IBGE/CNPJ públicas — consultar e mapear
para `city.ibgeCode` antes do `PUT /customers`.

## 8. Catálogo de Erros

| Erro | Causa | Ação |
|------|-------|------|
| `GW234` / `Nao foi possivel autenticar` | Certificado A1 inválido/expirado | Renovar em Asaas > Certificado |
| `Dados obrigatórios` | Config fiscal incompleta | Completar CNPJ + regime + inscrição municipal |
| `400 municipalServiceName` | Campo ausente no payload | Preencher `municipalServiceName` |
| `400 Código NBS inválido` | `nbsCode` incorreto para o município | Remover ou usar valor válido para sua cidade |
| `400 data de emissão inferior` | `effectiveDate` no passado | Usar `date.today().isoformat()` |
| `400 Endereço/CEP inválido` | Cliente sem endereço completo | `PUT /customers` com `city.ibgeCode` (§7) |
| `401 invalid_environment` / vazio | Token errado ou header errado | Header é `access_token` (não `Authorization: Bearer`) |
| `401` com key começando `$aact_...` | Shell expandiu `$aact` para vazio | Usar aspas simples ou `KEY=$(cat file)` (§6.1) |
| `SYNCHRONIZED → ERROR` após 60s | Prefeitura rejeitou | Verificar certificado + portal da prefeitura |
| `ERROR` imediato "cadastro geral" | Conta Asaas não aprovada | Aguardar aprovação no painel Asaas |
| `"Provider não encontrado"` | Bug #1 (filtro active) | Aplicar fix §2 |
| `column asaas_account_info does not exist` | Bug #2 | Aplicar fix §3 |
| `HTTP 403` em endpoints financeiros | Permissões da conta Asaas | Sinalizar como dado incompleto, NÃO zerar |

### 6.1. Gotcha de shell — `$aact_...` vira variável vazia

A key Asaas começa com `$aact_prod_...`. Em aspas duplas, `$aact` é interpretado
como variável vazia → **HTTP 401** silencioso.

```bash
# ❌ ERRADO — $aact expande para vazio
export ASAAS_ACCESS_TOKEN="$aact_prod_..."
# ✅ CERTO — aspas simples impede expansão
export ASAAS_ACCESS_TOKEN='$aact_prod_...'
# ✅ OU salvar em arquivo e ler
echo 'aact_prod_...' > /tmp/asaas_key
KEY=$(cat /tmp/asaas_key)   # $(...) não expande o $aact dentro do arquivo
# Tamanho esperado da key: ~166 chars
```

## 9. Política: cobrança faturável sempre com NFS-e

**Regra:** cobrança a cliente faturável vai **sempre** com NFS-e emitida junto (link PDF
no e-mail). Sem nota autorizada → **emitir antes de cobrar**.

**Checklist antes de emitir (evita duplicar nota):**
1. `GET /invoices?customer={cus}` — já existe NFS-e `AUTHORIZED` para este payment?
   Se sim, **não emitir outra** — apenas reenviar o link da nota existente.
2. Cliente tem endereço completo? (§7) — senão completar antes.
3. `effectiveDate` = hoje.
4. Pegar `invoiceNumber` + `invoiceUrl` do payment para montar `serviceDescription`.
5. Após `AUTHORIZED`: capturar `pdfUrl`/`xmlUrl` e enviar cobrança com
   **link de pagamento + link da NFS-e**.

Tom de cobrança: lembrete **amigável** para cliente em dia que atrasou 1-2 dias;
agressivo só para >30d. Nunca dar baixa como "recebido" sem o dinheiro entrar
(evita duplicar receita).

## 10. Validador JSON-RPC completo

Ver script: `scripts/validate_nfse.py`

```bash
pip3 install requests
python3 scripts/validate_nfse.py
```

Valida: conectividade Odoo, provider Asaas (sem expor a key), empresa fiscal
(CNPJ/regime/CNAE) e módulos instalados. Read-only — não escreve no banco.

## 11. QuickTest — emissão de teste via API direta

Para debug rápido sem passar pelo Odoo (valida credenciais + config fiscal Asaas):

```bash
python3 scripts/quicktest.py \
  --customer cus_XXX \
  --service-description "Servico de teste" \
  --service-list-item "01.07" \
  --municipal-service-id "<codigo da sua prefeitura>" \
  --value 1.00
```

O script emite, autoriza e monitora até `AUTHORIZED`/`ERROR`, classificando o erro
contra o catálogo §8.

## 12. Boas práticas

1. **Nunca logar `asaas_api_key`** — exiba apenas `has_key`/`no_key`.
2. **Aspas simples** para a key no shell (§6.1).
3. **`effectiveDate` sempre hoje** — passado = HTTP 400.
4. **ISS/NBS/serviceId variam por município** — consultar `fiscalInfo` + contador.
5. **Cliente com endereço completo** antes de emitir (§7).
6. **Cobrança faturável sempre com NFS-e** (§9) — checar invoices existentes antes.
7. **Multi-empresa:** cada `res.company` tem seu `payment.provider.asaas_api_key`.
8. **Webhook fix §2:** remover filtro `active=True` do lookup do provider.
9. **`SYNCHRONIZED` por minutos é normal** — só alarmar se virar `ERROR`.
10. **Refresh da key:** re-extrair do Odoo antes de emissões longas (token rotaciona).

## 13. Referências

- [Docs Asaas NFS-e](https://docs.asaas.com/reference/create-invoice)
- [BrasilAPI (lookup CNPJ)](https://brasilapi.com.br/api/cnpj/v1/)
- [Módulo base](https://github.com/conexaoazul/blueapps) — `blue_payment_asaas_nfse`