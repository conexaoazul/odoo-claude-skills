# Planos — Emissor NFS-e Asaas + Skills Claude Code

A Conexão Azul Digital distribui o **módulo Emissor NFS-e Asaas para Odoo 19** e um
pacote de **Skills Claude Code** (este repositório) para operá-lo com IA. O modelo é
**open-core**: as skills são livres e abertas; o que é pago é o suporte, a operação
gerenciada e a customização em volta delas.

> Funciona em **Odoo.sh, VPS ou on-premise** via JSON-RPC — **sem acesso SSH necessário**.

---

## Por que a Conexão Azul (e não um freelancer ou módulo OCA)

Você pode comprar uma skill avulsa, um módulo da OCA, ou contratar um dev. O que só
**nós** entregamos:

1. **Somos os autores da pilha.** Quem escreveu `blue_payment_asaas_nfse`,
   `conexaoazul_cobranca_email` e `bitconn_ixc_sync` somos nós. Bug? A gente conserta no
   módulo — não contorna. O suporte vem do código-fonte.
2. **Stack integrada 360.** Odoo + Asaas + Chatwoot + Evolution + Postgres funcionando
   junto em produção **na nossa própria empresa**. Cada cliente novo é mais uma prova
   da pilha (dogfooding vivo).
3. **Operação sem SSH.** Tudo via JSON-RPC. Você não entrega a chave do seu server —
   segurança e LGPD. Freelancer pede SSH; nós não precisamos.
4. **Know-how fiscal brasileiro embutido.** NFS-e municipal por cidade, LGPD de
   negativação, antecipação Asaas, conciliação NFS-e × cobrança. Não é "dev que entrega
   código" — é quem já errou esses erros e os corrigiu.
5. **Arsenal de 1.077 skills = capacidade adjacente infinita.** Comprou Setup NFS-e e
   amanhã quer CRM? Já temos skill + módulo. A relação não acaba no ticket — escala
   dentro do mesmo parceiro (LTV).
6. **Prova social concreta.** Casos validados em produção (Portal Nacional Serra-ES,
   distribuidor a 850 NF-e/mês).

---

## O valor que você recebe (ancoragem)

Antes de olhar o preço, veja o que está incluído na pilha de cada plano:

| Componente | Valor de mercado |
|---|---|
| Módulo Emissor NFS-e Asaas (Odoo 19) | R$ 2.500 |
| 4 Skills Claude Code (operação + cobrança + CRM) | R$ 1.200 |
| Setup 1h (call + .env + 1ª NFS-e real) | R$ 600 |
| Audit de infra Odoo/Asaas (1h, PDF) | R$ 450 |
| Canal privado de clientes (peer support) | R$ 290/mês |
| **Valor total da pilha** | **~R$ 5.040** |

Seu plano entrega uma fatia disso por uma fração do valor — porque nosso custo marginal
de criar uma skill ou emitir um audit é quase zero (o arsenal já está pago).

---

## Portal de Workflows (assinatura volume — novo)

Além da escada NFS-e, oferecemos um **portal de automação** com **2.590 workflows n8n + 1.158 skills Claude Code + 50 módulos Odoo** organizados por vertical. Modelo **freemium → assinatura recorrente em volume**, focado no **Autonomista** (auto-serviço, sem call).

> **Benchmark de mercado:** n8nHub (concorrente, só workflows n8n) cobra $19/$49/$99. Nós entregamos workflows **+ skills + módulos Odoo + integração Asaas/Chatwoot + operação** — pilha integrada, não peça solta.

| Tier | Preço | Para quem | Entrega |
|---|---|---|---|
| **Portal Free** | R$ 0 | Quem quer testar | 50 workflows básicos + **demo trial no nosso n8n** (3 execuções) + import 1-click |
| **Portal Pro** | **R$ 147/mês** (ou R$1.470/ano) | Autonomista que quer escalar | Catálogo completo 2.590 + 1.158 skills + updates da comunidade syncados + comunidade + import 1-click |
| **Portal Business** | **R$ 397/mês** | Time que quer premium | Pro + workflows premium curados + suporte prioritário + 5 Setup Express/ano + API access |

**Trial:** 14 dias Portal Pro grátis, **sem cartão**. Demo trial de workflow roda no nosso n8n — você vê funcionando antes de pagar.

**ROI do Portal Pro:** 1 dev custa R$8k/mês. Portal Pro custa R$147/mês e entrega 3 automações/mês prontas. **Paga em 1 semana de trabalho economizado.**

**Cross-sell natural:** Portal Pro → quando travar na config, Setup Express R$600 → quando quiser solução completa, Bundle vertical → quando crescer e não quiser ter trabalho, Operação Gerenciada R$890/mês.

---

## Escada de planos (good-better-best)

| Plano | Preço | Para quem | Entrega |
|-------|-------|-----------|---------|
| **Grátis** | R$ 0 | Quem comprou o módulo e quer se virar | Módulo + 4 skills + README + onboarding por e-mail |
| **Setup Express** | **R$ 600** (one-shot) | Quem quer começar rápido e sem erro | Call 1h + `.env` + 1ª NFS-e emitida junto + validador + audit amostra PDF + treino (2 pessoas) |
| **Suporte NFS-e** | **R$ 290/mês** (ou R$ 2.700/ano) | Quem emite NFS-e todo mês e quer segurança | Canal prioritário SLA 48h + updates antecipados + 1 health-check/mês + fix de bugs + canal privado |
| **Operação Gerenciada** | **R$ 890/mês** | Quem não quer ter trabalho com fiscal | Tudo do Suporte + monitoramento pró-ativo + reconciliação NFS-e×cobrança + KPI mensal + até 500 NFS-e/mês |
| **Custom Skill** | **R$ 600–1.800** / skill | Quem quer automação dedicada | Skill Claude Code para um fluxo específico (cobrança recorrente, relatório, CRM) |

> Plano do meio (**Suporte**) é o âncora: entre R$290 e R$890, a maioria escolhe o meio.

### Bônus de fechamento (custo zero, valor percebido alto — incluídos sem pedir)

- **Skill extra `odoo-cobranca-email`** (LGPL, já pronta) em qualquer plano pago
- **1 audit de infra no primeiro mês** (rodamos `ca-odoo-ha`, 1h) — no Setup e Suporte
- **Acesso ao canal privado de clientes** (Telegram/Chatwoot, peer support)
- **Plano anual = 10 meses** (R$ 2.700/ano vs R$ 3.480) — fidelidade sem parecer desconto

---

## O que cada plano entrega em detalhe

### Grátis (já incluído na compra do módulo)
- Módulo Emissor NFS-e Asaas para Odoo 19
- 4 Skills Claude Code (`asaas-nfse-quicktest`, `odoo-asaas-nfse-ops`,
  `odoo-cobranca-email`, `odoo-sales-crm`)
- README com instalação e exemplos de uso
- Onboarding por e-mail com casos de uso prontos

### Setup Express — R$ 600 (one-shot)
- Call de 1h com nosso time
- Configuração do `.env` (Odoo + Asaas)
- Emissão da **primeira NFS-e real** junto com você
- Validador JSON-RPC rodado (saúde do módulo)
- **Audit amostra PDF** (infra + conexões + módulos órfãos)
- Treino básico da equipe (até 2 pessoas) no Claude Code + skills
- Entrega: em até 2 dias úteis após o pagamento
- **Garantia reversível**: se não emitir a 1ª NFS-e real, devolvemos 50%

### Suporte NFS-e — R$ 290/mês (ou R$ 2.700/ano)
- Canal prioritário (WhatsApp/e-mail) com **SLA 48h**
- **Atualizações das skills antes de todo mundo** (versionadas)
- 1 **health-check mensal** com relatório (validador + KPIs de emissão)
- Fix de bugs do módulo
- Acesso ao canal privado de clientes do módulo (peer support)
- Cancelamento a qualquer momento

### Operação Gerenciada — R$ 890/mês
- Tudo do Suporte NFS-e
- **Monitoramento pró-ativo** da emissão (detectamos problemas antes de você)
- **Reconciliação NFS-e × cobrança** mensal (nenhuma nota fica órfã)
- **Relatório KPI mensal**: NFS-e emitidas, taxa de erro, tempo médio, cobranças recuperadas
- Até 500 NFS-e/mês incluídas (excedente: R$ 2/nota)

### Custom Skill — R$ 600–1.800 / skill
- Skill Claude Code dedicada a um fluxo seu
- Exemplos: régua de cobrança recorrente com NFS-e, relatório de atendimento,
  dashboard de vendas, integração com seu sistema atual
- Entrega: 5–10 dias úteis
- Inclui instalação + treino

---

## O ROI dos planos (por que se paga sozinho)

| Plano | Como se paga |
|---|---|
| **Setup Express R$600** | vs "fazer sozinho": 8h config + 4h debug/mês = R$1.600 do seu tempo. Setup paga em 1 semana. |
| **Suporte R$290/mês** | 1 inadimplente recuperado/mês pelo módulo de cobrança = R$290+ (paga o plano) |
| **Operação R$890/mês** | 1 multa fiscal evitada (nota órfã, erro de código municipal) > R$890. Reconciliação evita prejuízo. |
| **Custom Skill R$600+** | 1 automação que economiza 5h/mês do seu time = R$1.000+/mês. Paga em 30 dias. |

---

## Por que assinar o Suporte/Managed?

As skills deste repo são **livres** — você pode usá-las sem pagar nada. O que você
compra no Suporte/Managed é:

1. **Tranquilidade**: canal prioritário + SLA, sem ficar bloqueado em bug fiscal.
2. **Atualizações primeiro**: recebemos mudanças na API Asaas / Reforma Tributária
   antes de todo mundo — você não fica com skill desatualizada.
3. **Visibilidade**: health-check e relatório KPI mensais mostram o que está
   acontecendo na sua emissão.
4. **Operação delegada**: no Managed, a gente cuida da emissão por você — sua equipe
   foca no negócio.

---

## Como contratar

1. Escolha o plano acima.
2. Escreva para **financeiro@conexaoazul.com.br** (ou responda ao e-mail de onboarding
   que você recebeu).
3. Para Setup Express: agendamos a call em até 2 dias úteis.

> Vagas Setup Express limitadas em julho (capacidade de call 1h) — confirmar na semana.

---

## FAQ rápido

**As skills param de funcionar se eu não assinar?**
Não. As skills são livres e ficam neste repo público. O que você perde sem o Suporte
é: atualizações antecipadas, canal prioritário, health-check e relatório.

**Posso começar pelo Grátis e migrar depois?**
Sim. O Setup Express e o Suporte podem ser contratados a qualquer momento.

**O Suporte tem fidelidade?**
Não. Cancelamento a qualquer momento. Plano anual (= 10 meses) é opcional e voluntário.

**Vocês emitem NFS-e por mim?**
Apenas no plano **Operação Gerenciada**. Nos demais, a emissão é sua (com nossas
skills/playbooks).

**Vocês precisam de acesso SSH ao meu servidor?**
Não. Tudo via JSON-RPC. Você não compartilha credenciais de server — só cria um
usuário Odoo com permissões de API.

**E se eu já uso Claude Code?**
Melhor. As skills são feitas pra ele. Você instala e usa; nosso papel vira o suporte
especializado e a operação gerenciada quando você não quer ter trabalho.

---

*Planos mantidos por [Conexão Azul Digital](https://conexaoazul.com).*
*Inventário completo de skills e módulos: `github.com/conexaoazul/dhy` (SKILLS.md, ODOO-MODULES.md).*