#!/usr/bin/env python3
"""
Asaas NFSe QuickTest — Debug rápido de emissão de NFSe
========================================================
Autor: Claudia · Conexão Azul Digital
Data: 2026-06-17
Versão: 1.0

Uso:
    export ASAAS_ACCESS_TOKEN="$aact_prod_..."
    python3 quicktest.py \
        --customer cus_XXXXXXXXXXXXXXX \
        --service-description "Suporte tecnico em informatica" \
        --service-list-item "01.07" \
        --municipal-service-id "292180" \
        --value 5.00
"""

import argparse
import json
import os
import requests
import sys
import time
from datetime import datetime

BASE = "https://api.asaas.com/v3"


class AsaasNFSeQuickTest:
    def __init__(self, token: str):
        self.token = token
        self.headers = {"access_token": token, "Content-Type": "application/json"}

    def call(self, method, endpoint, data=None):
        url = f"{BASE}{endpoint}"
        if method == "GET":
            return requests.get(url, headers=self.headers, timeout=20)
        if method == "POST":
            return requests.post(url, headers=self.headers, json=data, timeout=30)
        if method == "PUT":
            return requests.put(url, headers=self.headers, data=data, timeout=30)
        return None

    def validate_connectivity(self):
        """Passo 1: Testar conexão API."""
        r = self.call("GET", "/myAccount")
        if r.status_code == 200:
            d = r.json()
            print(f"✅ Conectado: {d.get('company')} | CNPJ: {d.get('cpfCnpj')}")
            return True
        print(f"❌ Falha de conectividade: HTTP {r.status_code}")
        return False

    def check_fiscal_config(self):
        """Passo 2: Ler configuração fiscal atual."""
        r = self.call("GET", "/fiscalInfo")
        if r.status_code != 200:
            print("⚠️  Não foi possível ler configuração fiscal")
            return {}
        return r.json()

    def diagnose(self, cfg):
        """Passo 3: Detectar gaps conhecidos."""
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
        for i in issues:
            print(f"  ⚠️  {i}")
        return issues

    def emit(self, customer, desc, svc_name, svc_id, value, taxes):
        """Passo 4: Emitir NFSe."""
        payload = {
            "customer": customer,
            "serviceDescription": desc,
            "municipalServiceName": svc_name,
            "value": value,
            "effectiveDate": datetime.now().strftime("%Y-%m-%d"),
            "municipalServiceId": svc_id,
            "taxes": taxes
        }
        r = self.call("POST", "/invoices", payload)
        if r.status_code == 200:
            d = r.json()
            print(f"✅ NFSe criada: {d.get('id')} | Status: {d.get('status')}")
            return d.get("id")
        print(f"❌ Erro ao criar: HTTP {r.status_code}")
        print(r.text)
        return None

    def authorize(self, inv_id):
        """Passo 5: Autorizar NFSe."""
        r = self.call("POST", f"/invoices/{inv_id}/authorize")
        if r.status_code == 200:
            print("✅ Autorização aceita")
            return True
        print(f"❌ Autorização falhou: HTTP {r.status_code}")
        return False

    def monitor(self, inv_id, max_seconds=180):
        """Passo 6: Monitorar até AUTHORIZED/ERROR/CANCELLED."""
        print(f"\n⏱️  Monitorando {inv_id} (máx {max_seconds}s)...")
        for i in range(max_seconds // 10):
            time.sleep(10)
            r = self.call("GET", f"/invoices/{inv_id}")
            if r.status_code != 200:
                print(f"  T+{(i+1)*10}s | Erro HTTP {r.status_code}")
                continue
            d = r.json()
            st, dsc = d.get("status"), d.get("statusDescription")
            print(f"  T+{(i+1)*10}s | {st}")
            if st in ("AUTHORIZED", "CANCELLED", "ERROR"):
                return d
        return None

    def classify_error(self, result):
        """Passo 7: Classificar erro via catálogo aprendido."""
        if not result:
            print("\n⏳ Timeout — verificar manualmente mais tarde")
            return
        st = result.get("status")
        dsc = result.get("statusDescription", "")
        print(f"\n{'='*50}")
        print(f"RESULTADO: {st}")
        if st == "AUTHORIZED":
            print("✅ SUCESSO!")
            print(f"   PDF:  {result.get('pdfUrl')}")
            print(f"   XML:  {result.get('xmlUrl')}")
            print(f"   Número: {result.get('number')}")
            print(f"   RPS:  {result.get('rpsNumber')}")
            print(f"   Valor: R$ {result.get('value')}")
        elif st == "ERROR":
            print(f"❌ ERRO: {dsc}")
            if "GW234" in dsc:
                print("   → Certificado digital inválido ou não autenticado (A1)")
                print("   → AÇÃO: verificar validade, senha e CNPJ do certificado no painel Asaas")
            elif "dados obrigatórios" in dsc.lower():
                print("   → Configuração fiscal incompleta")
                print("   → AÇÃO: completar Simples Nacional, regime e inscrição no painel Asaas")
            elif "Nao foi possivel autenticar" in dsc:
                print("   → Prefeitura rejeitou autenticação do certificado")
                print("   → AÇÃO: renovar certificado A1, verificar senha ou contatar prefeitura")
            else:
                print("   → Erro não catalogado — consultar suporte Asaas: integrations@asaas.com.br")
        print(f"{'='*50}")


def build_parser():
    parser = argparse.ArgumentParser(description="Asaas NFSe QuickTest — Claudia/Conexão Azul")
    parser.add_argument("--token", default=os.getenv("ASAAS_ACCESS_TOKEN"), help="Token de API Asaas (ou env ASAAS_ACCESS_TOKEN)")
    parser.add_argument("--customer", required=True, help="Customer ID (ex: cus_XXXXXXXXXXXXXXX)")
    parser.add_argument("--service-description", required=True, help="Descrição do serviço")
    parser.add_argument("--service-list-item", required=True, help="Código do serviço LC 116/2003 (ex: 01.07)")
    parser.add_argument("--municipal-service-id", required=True, help="ID municipal do serviço (ex: 292180)")
    parser.add_argument("--value", type=float, required=True, help="Valor da nota")
    parser.add_argument("--tax-situation", default="011", help="taxSituationCode")
    parser.add_argument("--tax-classification", default="011001", help="taxClassificationCode")
    parser.add_argument("--operation-indicator", default="020101", help="operationIndicatorCode")
    parser.add_argument("--monitor", type=int, default=180, help="Tempo máximo de monitoramento (segundos)")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.token:
        print("[!] Defina ASAAS_ACCESS_TOKEN ou passe --token")
        sys.exit(1)

    qt = AsaasNFSeQuickTest(args.token)

    # Passo 1
    if not qt.validate_connectivity():
        sys.exit(1)

    # Passo 2-3
    cfg = qt.check_fiscal_config()
    qt.diagnose(cfg)

    # Passo 4
    taxes = {
        "retainIss": False,
        "iss": 0.25,
        "pis": 0.03,
        "cofins": 0.15,
        "csll": 0.0,
        "inss": 0.0,
        "ir": 0.0,
        "taxSituationCode": args.tax_situation,
        "taxClassificationCode": args.tax_classification,
        "operationIndicatorCode": args.operation_indicator,
        "pisCofinsRetentionType": "NOT_WITHHELD",
        "pisCofinsTaxStatus": "STANDARD_TAXABLE_OPERATION"
    }
    inv_id = qt.emit(args.customer, args.service_description,
                     args.service_list_item, args.municipal_service_id,
                     args.value, taxes)
    if not inv_id:
        sys.exit(1)

    # Passo 5
    qt.authorize(inv_id)

    # Passo 6-7
    result = qt.monitor(inv_id, args.monitor)
    qt.classify_error(result)


if __name__ == "__main__":
    main()
