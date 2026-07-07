---
name: asaas-nfse-quicktest
description: "Debug rápido de emissão de NFS-e via API Asaas em menos de 1 minuto. Valida conectividade, diagnostica gaps cadastrais, emite, autoriza e monitora até AUTHORIZED. Catálogo de erros conhecidos e payload-modelo parametrizável."
version: 1.0.0
author: Conexão Azul Digital
tags: [asaas, nfse, fiscal, brasil, api]
---

# Asaas NFS-e QuickTest — Debug Rápido de Emissão

Skill para validar o pipeline de emissão de NFS-e via API Asaas direto da linha de
comando. Útil para subir a primeira nota de um novo município, isolar erro de
cadastro, ou confirmar que certificado/config fiscal estão OK antes de acionar o
Odoo. Funciona em qualquer ambiente (Odoo.sh, VPS, on-premise) — só precisa do
token da API Asaas.

## Configuração (.env)

```bash
# Painel Asaas > Integrações > API
export ASAAS_ACCESS_TOKEN='aact_prod_...'

# Multi-empresa (opcional, via Odoo JSON-RPC) — veja §6
export ODOO_URL="https://seu-odoo.odoo.com"
export ODOO_DB="seu_banco"
export ODOO_UID=2
export ODOO_PWD="sua_senha"
```

> **Atenção ao shell:** o token começa com `$aact_...`. Em aspas duplas, o bash
> expande `$aact` para vazio e a API retorna **401**. Use **aspas simples** ou
> salve o token em arquivo e leia com `KEY=$(cat /tmp/asaas_key.txt)`.
> Tamanho esperado: ~166 chars.

## 1. Uso Rápido

```bash
python3 skills/asaas-nfse-quicktest/scripts/quicktest.py \
  --customer cus_XXX \
  --service-description "Serviços de suporte técnico em TI" \
  --service-list-item "01.07" \
  --municipal-service-id "XXXXXX" \
  --municipal-service-name "1.06 - Assessoria e consultoria em informática." \
  --nbs-code "X.XXXX.XX.XX" \
  --iss 2.0 \
  --value 400.00 \
  --payment pay_XXX \
  --monitor 300
```

Saída esperada (sucesso):

```
✅ Conectado: SUA EMPRESA LTDA | CNPJ: 00.000.000/0001-00
✅ NFS-e criada: inv_XXX | Status: SCHEDULED
✅ Autorização aceita
⏱️  Monitorando inv_XXX (máx 300s)...
  T+10s  | SYNCHRONIZED
  T+120s | AUTHORIZED
RESULTADO: AUTHORIZED
   PDF:  https://...
   XML:  https://...
```

## 2. Catálogo de Erros

| HTTP | Padrão na resposta | Causa provável | Ação |
|------|-------------------|----------------|------|
| 401  | `invalid_environment` / vazio | Token errado ou header incorreto | Usar header `access_token: <token>` (não `Authorization: Bearer`) |
| 401  | `invalid_environment` / vazio | Token começa com `$aact_` e shell expandiu | Aspas simples ou `KEY=$(cat arquivo)` |
| 400  | `dados obrigatorios.*empresa` | Config fiscal incompleta | Completar `simplesNacional`, regime, inscrição municipal, CNAE no painel Asaas |
| 400  | `invalid_action` + `municipalServiceName` | Campo `municipalServiceName` ausente | Incluir `municipalServiceName` no payload |
| 400  | `Código NBS inválido` | `nbsCode` incorreto para o município | Remover `nbsCode` do payload ou usar valor válido da prefeitura |
| 400  | `data de emissão.*inferior` | `effectiveDate` no passado | Usar `datetime.now().strftime("%Y-%m-%d")` |
| 400  | `Endereço do cliente incompleto.*CEP.*inválido` | Cliente sem endereço/CEP | `PUT /customers/{id}` com endereço completo + `city{ibgeCode}` (§5) |
| 200  | `status: ERROR` com `GW234` | Certificado A1 inválido/expirado | Renovar certificado no painel Asaas (validade, senha, CNPJ) |
| 200  | `SYNCHRONIZED` → `ERROR` após 60s | Prefeitura rejeitou | Verificar cadastro no portal da prefeitura + certificado |
| 200  | `ERROR` imediato / `cadastro geral aprovado` | Conta Asaas não aprovada | Aguardar aprovação da conta no painel Asaas |

## 3. Pré-requisitos (config fiscal no painel Asaas)

```
[ ] Certificado A1 enviado e válido
[ ] Simples Nacional = true (se aplicável)
[ ] Regime tributário definido (specialTaxRegime ≠ "0")
[ ] Inscrição municipal preenchida
[ ] CNAE definido
[ ] serviceListItem definido (código LC 116/2003, ex: "01.07")
```

O script faz essa leitura automaticamente via `GET /fiscalInfo` e avisa os gaps
antes de tentar emitir.

## 4. Payload-modelo NFS-e (campos por parâmetro)

```python
payload = {
    "customer": "cus_XXX",            # ID do cliente Asaas
    "type": "NFS-e",
    "payment": "pay_XXX",             # opcional: vincula a NFS-e a uma cobrança Asaas
    "serviceDescription": (
        f"Nota fiscal da Fatura {invoiceNumber}.\n"
        f"Descrição dos Serviços: {svcName}\n"
        f"Para mais informações acesse: {invoiceUrl}."
    ),
    "municipalServiceId": "XXXXXX",   # código do serviço na sua prefeitura
    "municipalServiceName": "1.06 - Assessoria e consultoria em informática.",
    "municipalServiceCode": "",
    "value": 400.0,
    "effectiveDate": "2026-07-07",    # SEMPRE hoje (data no passado = HTTP 400)
    "observations": "Empresa optante pelo Simples Nacional. "
                    "Retenções tributárias, quando aplicáveis, "
                    "serão destacadas na própria NFS-e.",
    "taxes": {
        "retainIss": False,
        "iss": 2.0,                   # alíquota do seu município (varia)
        "pisCofinsRetentionType": "PIS_COFINS_CSLL_NOT_WITHHELD",
        "pisCofinsTaxStatus": "NONE",
        "inss": 0.0, "ir": 0.0,
        "nbsCode": "X.XXXX.XX.XX"     # NBS do seu município (varia)
    }
}
# POST /invoices     → 200 SCHEDULED
# POST /invoices/{id}/authorize → 200
# GET  /invoices/{id} (poll 10s) → SYNCHRONIZED → AUTHORIZED (~120s)
# Em AUTHORIZED: capturar pdfUrl, xmlUrl, number, rpsNumber
```

> **ISS, municipalServiceId e nbsCode variam por município.** Consulte a
> alíquota e os códigos na prefeitura onde sua empresa é inscrita. Os valores
> acima são exemplos — não use cegos.

## 5. Pré-requisito: cliente com endereço completo

Cliente sem endereço → `POST /invoices` retorna **400**
`"Endereço do cliente incompleto.; CEP do cliente é inválido."`.

Correção antes de emitir:

```python
# PUT /customers/{id} — cidade via ibgeCode
body = {
    "postalCode":   "00000000",        # CEP do cliente
    "address":      "Rua Exemplo",
    "addressNumber":"123",
    "province":     "Bairro",
    "city":         {"ibgeCode": "XXXXXXX"},  # código IBGE da cidade do cliente
    "state":        "XX",
    "country":      "Brasil"
}
requests.put(f"https://api.asaas.com/v3/customers/{cus}",
             headers={"access_token": TOKEN, "Content-Type": "application/json"},
             json=body)
```

### Lookup de endereço por CNPJ (fallback público)

A **BrasilAPI** é pública, sem token, e devolve CEP, logradouro, número, bairro,
município e UF a partir do CNPJ:

```bash
curl -s https://brasilapi.com.br/api/cnpj/v1/{cnpj} | jq '{cep, logradouro, numero, bairro, municipio, uf}'
```

O código IBGE da cidade você obtém em tabelas públicas IBGE→CNPJ ou no site do
IBGE (`https://www.ibge.gov.br`) — guarde em tabela auxiliar no seu sistema.

## 6. Multi-empresa: qual token usar?

Em instalações Odoo com mais de uma empresa (cada uma com sua conta Asaas), o
token de cada empresa vive no campo `payment.provider.asaas_api_key`. Para
descobrir via JSON-RPC:

```python
import requests, json
URL = "https://seu-odoo.odoo.com/jsonrpc"
def odoo(model, method, args, kwargs=None):
    r = requests.post(URL, json={
        "jsonrpc": "2.0", "service": "object", "method": "execute_kw",
        "args": [DB, UID, PWD, model, method, args, kwargs or {}]
    })
    return r.json().get("result")

providers = odoo("payment.provider", "search_read",
    [[["code", "=", "asaas"], ["company_id", "=", SUA_COMPANY_ID]]],
    {"fields": ["id", "name", "company_id", "asaas_api_key"],
     "context": {"active_test": False}})
# providers[0]["asaas_api_key"] → token da empresa certa
```

> Use `context: {"active_test": False}` para também achar providers arquivados
> (bug clássico do Odoo — ver skill `odoo-asaas-nfse-ops`).

## 7. Política: cobrança faturável sempre com NFS-e emitida

Best-practice genérica para quem cobra via Asaas e emite NFS-e via Asaas:

- **Cobrança faturável → NFS-e emitida junto** (link da nota junto com o link
  de pagamento). Sem nota autorizada, **emita antes de cobrar**.
- **Antes de emitir**, verifique se já existe NFS-e autorizada para a mesma
  cobrança — evita duplicar nota:

  ```bash
  curl -s -H "access_token: $ASAAS_ACCESS_TOKEN" \
    "https://api.asaas.com/v3/invoices?customer=cus_XXX" | jq '.data[] | {id, status, payment}'
  ```

- **Checklist antes de emitir:**
  1. Já existe NFS-e `AUTHORIZED` para este `payment`? Se sim, só reenvie o link.
  2. Cliente tem endereço completo? (§5)
  3. `effectiveDate` = hoje.
  4. Pegar `invoiceNumber` + `invoiceUrl` do payment para montar `serviceDescription`.
  5. Após `AUTHORIZED`: capturar `pdfUrl`, enviar cobrança com **link de
     pagamento + link da NFS-e** ao cliente.

## 8. Quando o problema NÃO é a API

Se o QuickTest emitir com sucesso e mesmo assim o Odoo não gerar notas, o
defeito está na camada Odoo (provider lookup, webhook, campos do módulo).
Carregue a skill **`odoo-asaas-nfse-ops`** para diagnóstico JSON-RPC do lado
Odoo.

## 9. Referências

- [Docs Asaas — Create Invoice](https://docs.asaas.com/reference/create-invoice)
- [Docs Asaas — Authorize Invoice](https://docs.asaas.com/reference/authorize-invoice)
- [BrasilAPI — consulta CNPJ pública](https://brasilapi.com.br/api/cnpj/v1/{cnpj})
- [Tabela de códigos IBGE](https://www.ibge.gov.br/explica/codigos-dos-municipios.php)
- Skill complementar: `../odoo-asaas-nfse-ops/`

## 10. Pendências conhecidas

- Timeout prolongado (>300s em `SYNCHRONIZED`) — algumas prefeituras são lentas.
- Prefeituras com homologação manual obrigatória.
- Cancelamento não suportado em alguns municípios (verificar `POST /invoices/{id}/cancel`).
- NBS code correto por município — manter tabela local atualizada.