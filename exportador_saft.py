# ==========================================================
# EXPORTADOR DE UMA SÉRIE - SAF-T PT 1.04_01
# ==========================================================

import os
import re
import xml.etree.ElementTree as ET
from tkinter import filedialog, messagebox

NS_URI = "urn:OECD:StandardAuditFile-Tax:PT_1.04_01"
NS = {"ns": NS_URI}
ET.register_namespace("", NS_URI)


def obter_serie(invoice_no):
    """Obtém a série da estrutura InvoiceNo: TIPO SÉRIE/NÚMERO."""
    valor = (invoice_no or "").strip()
    if not valor:
        return ""

    # Ex.: FT 2026/123 -> FT 2026
    # Ex.: FT A/123 -> FT A
    if "/" in valor:
        return valor.rsplit("/", 1)[0].strip()

    return valor


def listar_series(ficheiro):
    tree = ET.parse(ficheiro)
    root = tree.getroot()

    sales = root.find(".//ns:SourceDocuments/ns:SalesInvoices", NS)
    if sales is None:
        return []

    series = set()
    for invoice in sales.findall("ns:Invoice", NS):
        numero = invoice.findtext("ns:InvoiceNo", default="", namespaces=NS)
        serie = obter_serie(numero)
        if serie:
            series.add(serie)

    return sorted(series, key=str.upper)


def _numero_monetario(valor):
    try:
        return f"{float(valor):.2f}"
    except Exception:
        return "0.00"


def exportar_serie(ficheiro_entrada, serie, ficheiro_saida):
    """
    Cria um SAF-T PT 1.04_01 parcial contendo apenas SalesInvoices
    da série indicada.

    Mantém Header e MasterFiles do original.
    Remove GeneralLedgerEntries e restantes SourceDocuments para evitar
    criar um ficheiro contabilístico incoerente com uma única série.
    """
    tree = ET.parse(ficheiro_entrada)
    root = tree.getroot()

    # Garantir namespace/version 1.04_01
    root.set("xmlns", NS_URI)

    header = root.find("ns:Header", NS)
    if header is not None:
        version = header.find("ns:AuditFileVersion", NS)
        if version is not None:
            version.text = "1.04_01"

    # Remover GeneralLedgerEntries: não exportamos contabilidade parcial.
    gle = root.find("ns:GeneralLedgerEntries", NS)
    if gle is not None:
        root.remove(gle)

    source = root.find("ns:SourceDocuments", NS)
    if source is None:
        raise ValueError("O SAF-T não contém SourceDocuments.")

    sales = source.find("ns:SalesInvoices", NS)
    if sales is None:
        raise ValueError("O SAF-T não contém SalesInvoices.")

    # Guardar apenas SalesInvoices.
    for child in list(source):
        if child is not sales:
            source.remove(child)

    invoices = sales.findall("ns:Invoice", NS)
    selecionadas = []

    for invoice in invoices:
        numero = invoice.findtext("ns:InvoiceNo", default="", namespaces=NS)
        if obter_serie(numero).upper() == serie.upper():
            selecionadas.append(invoice)
        else:
            sales.remove(invoice)

    if not selecionadas:
        raise ValueError(f"Não foram encontrados documentos da série '{serie}'.")

    # Totais SAF-T: contam todos os documentos, mas excluem A/F nos totais.
    total_debito = 0.0
    total_credito = 0.0

    for invoice in selecionadas:
        estado = invoice.findtext(
            "ns:DocumentStatus/ns:InvoiceStatus",
            default="",
            namespaces=NS
        ).strip().upper()

        if estado in ("A", "F"):
            continue

        for line in invoice.findall("ns:Line", NS):
            debito = line.findtext("ns:DebitAmount", default="0", namespaces=NS)
            credito = line.findtext("ns:CreditAmount", default="0", namespaces=NS)
            try:
                total_debito += float(debito or 0)
            except ValueError:
                pass
            try:
                total_credito += float(credito or 0)
            except ValueError:
                pass

    number = sales.find("ns:NumberOfEntries", NS)
    if number is None:
        number = ET.Element(f"{{{NS_URI}}}NumberOfEntries")
        sales.insert(0, number)
    number.text = str(len(selecionadas))

    total_d = sales.find("ns:TotalDebit", NS)
    if total_d is None:
        total_d = ET.Element(f"{{{NS_URI}}}TotalDebit")
        sales.insert(1, total_d)
    total_d.text = _numero_monetario(total_debito)

    total_c = sales.find("ns:TotalCredit", NS)
    if total_c is None:
        total_c = ET.Element(f"{{{NS_URI}}}TotalCredit")
        sales.insert(2, total_c)
    total_c.text = _numero_monetario(total_credito)

    # Reordenar SalesInvoices: cabeçalho obrigatório antes dos Invoice.
    ordered = []
    for tag in ("NumberOfEntries", "TotalDebit", "TotalCredit"):
        el = sales.find(f"ns:{tag}", NS)
        if el is not None:
            ordered.append(el)
    ordered.extend(sales.findall("ns:Invoice", NS))
    sales[:] = ordered

    # Pretty print quando disponível (Python 3.9+).
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass

    tree.write(
        ficheiro_saida,
        encoding="Windows-1252",
        xml_declaration=True
    )

    return {
        "serie": serie,
        "documentos": len(selecionadas),
        "total_debito": total_debito,
        "total_credito": total_credito,
        "ficheiro": ficheiro_saida,
    }
