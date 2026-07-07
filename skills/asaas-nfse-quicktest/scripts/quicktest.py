#!/usr/bin/env python3
"""
Asaas NFS-e QuickTest — Debug rápido de emissão de NFS-e
==========================================================

Valida o pipeline de emissão de NFS-e via API Asaas:
  1. Conectividade (GET /myAccount)
  2. Configuração fiscal (GET /fiscalInfo) + diagnóstico de gaps
  3. Emissão (POST /invoices) com payload parametrizável
  4. Autorização (POST /invoices/{id}/authorize)
  5. Monitoramento até AUTHORIZED / ERROR / CANCELLED
  6. Classificação do erro contra catálogo conhecido

Uso:
    export ASAAS_ACCESS_TOKEN='aact_prod_...'
    python3 quicktest.py \\
        --customer cus_XXX \\
        --service-description "Serviços de consultoria em TI" \\
        --service-list-item "01.07" \\
        --municipal-service-id "292180" \\
        --municipal-service-name "1.06 - Assessoria e consultoria em informática." \\
        --nbs-code "X.XXXX.XX.XX" \\
        --iss 2.0 \\
        --value 400.00 \\
        [--payment pay_XXX] \\
        [--monitor 300]

Autor: Conexão Azul Digital · Licença MIT
"""

import argparse
import os
import sys
import time
from datetime import datetime

import requests

BASE = "https://api.asaas.com/v3"


class AsaasNFSeQuickTest:
    def __init__(self, token: str):
        self.token = token
        self.headers = {"access_token": token, "Content-Type": "application/json"}

    # --- HTTP helpers ----------------------------------------------------
    def call(self, method, endpoint, data=None):
        url = f"{BASE}{endpoint}"
        try:
            if method == "GET":
                return requests.get(url, headers=self.headers, timeout=20)
            if method == "POST":
                return requests.post(url, headers=self.headers, json=data, timeout=30)
            if method == "PUT":
                return requests.put(url, headers=self.headers, json=data, timeout=30)
        except requests.RequestException as exc:
            print(f"[!] Falha de rede ({method} {endpoint}): {exc}")
        return None

    # --- Passo 1: conectividade -----------------------------------------
    def validate_connectivity(self):
        r = self.call("GET", "/myAccount")
        if r is None or r.status_code != 200:
            print(f"[!] Falha de conectividade: HTTP {getattr(r, 'status_code', '?')}")
            if r is not None:
                print(f"    {r.text[:300]}")
            return False
        d = r.json()
        print(f"[OK] Conectado: {d.get('company')} | CNPJ: {d.get('cpfCnpj')}")
        return True

    # --- Passo 2: config fiscal -----------------------------------------
    def check_fiscal_config(self):
        r = self.call("GET", "/fiscalInfo")
        if r is None or r.status_code != 200:
            print("[!] Não foi possível ler a configuração fiscal (/fiscalInfo).")
            return {}
        return r.json()

    # --- Passo 3: diagnóstico -------------------------------------------
    @staticmethod
    def diagnose(cfg):
        issues = []
        if not cfg.get("certificateSent"):
            issues.append("Certificado digital NÃO enviado")
        if not cfg.get("simplesNacional"):
            issues.append("Simples Nacional = false")
        if cfg.get("specialTaxRegime") == "0":
            issues.append("Regime tributário não definido")
        if not cfg.get("municipalInscription"):
            issues.append("Inscrição municipal vazia")
        if not cfg.get("serviceListItem"):
            issues.append("Código de serviço não definido")
        if not cfg.get("cnae"):
            issues.append("CNAE não definido")
        for issue in issues:
            print(f"  [!] {issue}")
        return issues

    # --- Passo 4: emissão ------------------------------------------------
    def emit(self, customer, desc, svc_name, svc_id, value, taxes,
             payment=None, observations=None):
        payload = {
            "customer": customer,
            "type": "NFS-e",
            "serviceDescription": desc,
            "municipalServiceName": svc_name,
            "municipalServiceId": svc_id,
            "municipalServiceCode": "",
            "value": value,
            "effectiveDate": datetime.now().strftime("%Y-%m-%d"),
            "taxes": taxes,
        }
        if payment:
            payload["payment"] = payment
        if observations:
            payload["observations"] = observations
        r = self.call("POST", "/invoices", payload)
        if r is None or r.status_code != 200:
            print(f"[!] Erro ao criar NFS-e: HTTP {getattr(r, 'status_code', '?')}")
            if r is not None:
                print(f"    {r.text[:500]}")
            return None
        d = r.json()
        print(f"[OK] NFS-e criada: {d.get('id')} | Status: {d.get('status')}")
        return d.get("id")

    # --- Passo 5: autorização -------------------------------------------
    def authorize(self, inv_id):
        r = self.call("POST", f"/invoices/{inv_id}/authorize")
        if r is not None and r.status_code == 200:
            print("[OK] Autorização aceita")
            return True
        print(f"[!] Autorização falhou: HTTP {getattr(r, 'status_code', '?')}")
        if r is not None:
            print(f"    {r.text[:300]}")
        return False

    # --- Passo 6: monitoramento -----------------------------------------
    def monitor(self, inv_id, max_seconds=180):
        print(f"\n[*] Monitorando {inv_id} (máx {max_seconds}s)...")
        steps = max(1, max_seconds // 10)
        for i in range(steps):
            time.sleep(10)
            r = self.call("GET", f"/invoices/{inv_id}")
            if r is None or r.status_code != 200:
                print(f"  T+{(i+1)*10}s | Erro HTTP {getattr(r, 'status_code', '?')}")
                continue
            d = r.json()
            st = d.get("status")
            print(f"  T+{(i+1)*10}s | {st}")
            if st in ("AUTHORIZED", "CANCELLED", "ERROR"):
                return d
        return None

    # --- Passo 7: classificação -----------------------------------------
    @staticmethod
    def classify_error(result):
        if not result:
            print("\n[?] Timeout — verifique manualmente mais tarde.")
            return
        st = result.get("status")
        dsc = result.get("statusDescription", "")
        print(f"\n{'='*60}")
        print(f"RESULTADO: {st}")
        if st == "AUTHORIZED":
            print("[OK] SUCESSO!")
            print(f"   PDF:    {result.get('pdfUrl')}")
            print(f"   XML:    {result.get('xmlUrl')}")
            print(f"   Número: {result.get('number')}")
            print(f"   RPS:    {result.get('rpsNumber')}")
            print(f"   Valor:  R$ {result.get('value')}")
        elif st == "CANCELLED":
            print(f"[*] Cancelada: {dsc}")
        elif st == "ERROR":
            print(f"[!] ERRO: {dsc}")
            low = dsc.lower()
            if "GW234" in dsc:
                print("   -> Certificado digital inválido/não autenticado (A1).")
                print("   -> Ação: renovar certificado, conferir senha e CNPJ no painel Asaas.")
            elif "dados obrigatorios" in low:
                print("   -> Configuração fiscal incompleta.")
                print("   -> Ação: completar Simples Nacional, regime e inscrição no painel Asaas.")
            elif "nao foi possivel autenticar" in low:
                print("   -> Prefeitura rejeitou a autenticação do certificado.")
                print("   -> Ação: renovar A1, verificar senha, contatar prefeitura.")
            elif "endereco" in low or "cep" in low:
                print("   -> Endereço do cliente incompleto.")
                print("   -> Ação: PUT /customers/{id} com city{ibgeCode} (ver SKILL.md §5).")
            else:
                print("   -> Erro não catalogado — consultar suporte Asaas.")
        print("=" * 60)


def build_parser():
    p = argparse.ArgumentParser(
        description="Asaas NFS-e QuickTest — Conexão Azul Digital")
    p.add_argument("--token", default=os.getenv("ASAAS_ACCESS_TOKEN"),
                   help="Token de API Asaas (ou env ASAAS_ACCESS_TOKEN)")
    p.add_argument("--customer", required=True, help="Customer ID (ex: cus_XXX)")
    p.add_argument("--service-description", required=True,
                   help="Descrição do serviço prestado")
    p.add_argument("--service-list-item", default="01.07",
                   help="Código LC 116/2003 (ex: 01.07)")
    p.add_argument("--municipal-service-id", required=True,
                   help="ID municipal do serviço (verifique na sua prefeitura)")
    p.add_argument("--municipal-service-name", required=True,
                   help="Nome municipal do serviço (ex: '1.06 - Assessoria ...')")
    p.add_argument("--nbs-code", default=None,
                   help="Código NBS (varia por município; omita se incerto)")
    p.add_argument("--iss", type=float, default=2.0,
                   help="Alíquota de ISS (%) — varia por município")
    p.add_argument("--value", type=float, required=True, help="Valor da nota")
    p.add_argument("--payment", default=None,
                   help="ID de cobrança Asaas (pay_XXX) — vincula NFS-e à cobrança")
    p.add_argument("--observations", default=None,
                   help="Observações livre (texto)")
    p.add_argument("--tax-situation", default="011")
    p.add_argument("--tax-classification", default="011001")
    p.add_argument("--operation-indicator", default="020101")
    p.add_argument("--monitor", type=int, default=180,
                   help="Tempo máximo de monitoramento (segundos)")
    return p


def main():
    args = build_parser().parse_args()

    if not args.token:
        print("[!] Defina ASAAS_ACCESS_TOKEN (env) ou passe --token.")
        print("    DICA: o token começa com '$aact_...'. Use aspas simples "
              "para evitar expansão shell.")
        sys.exit(1)

    qt = AsaasNFSeQuickTest(args.token)

    # Passo 1
    if not qt.validate_connectivity():
        sys.exit(1)

    # Passo 2-3
    cfg = qt.check_fiscal_config()
    qt.diagnose(cfg)

    # Passo 4 — montar taxes
    taxes = {
        "retainIss": False,
        "iss": args.iss,
        "pis": 0.0, "cofins": 0.0, "csll": 0.0, "inss": 0.0, "ir": 0.0,
        "taxSituationCode": args.tax_situation,
        "taxClassificationCode": args.tax_classification,
        "operationIndicatorCode": args.operation_indicator,
        "pisCofinsRetentionType": "PIS_COFINS_CSLL_NOT_WITHHELD",
        "pisCofinsTaxStatus": "NONE",
    }
    if args.nbs_code:
        taxes["nbsCode"] = args.nbs_code

    inv_id = qt.emit(
        customer=args.customer,
        desc=args.service_description,
        svc_name=args.municipal_service_name,
        svc_id=args.municipal_service_id,
        value=args.value,
        taxes=taxes,
        payment=args.payment,
        observations=args.observations,
    )
    if not inv_id:
        sys.exit(1)

    # Passo 5
    qt.authorize(inv_id)

    # Passo 6-7
    result = qt.monitor(inv_id, args.monitor)
    qt.classify_error(result)


if __name__ == "__main__":
    main()