      
import time
import xml.etree.ElementTree as ET
import pandas as pd
import threading
import os
import customtkinter as ctk

from movimentos_v6 import MovimentosV6


import tkinter as tk
from tkinter import ttk, filedialog, messagebox

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class SaftAnalyzer:

    def __init__(self):

        self.root = None

        # Interface
        self.ficheiro = ""
        self.callback_log = None
        self.callback_progress = None

        self.ns = {}

        self.header = {}

        self.clientes = {}

        self.artigos = {}

        self.dados = []

        self.df_original = None

        self.df_visivel = None

        self.df_movimentos = None        

        self.df_documentos = None
        
        self.df_clientes = None

        self.df_artigos = None

        self.df_iva = None
        

        self.inicio = time.time()

    #-------------------------------------------------

    def log(self, texto):

        if self.callback_log:
            self.callback_log(texto)
        else:
            print(texto)


    # --------------------------------------------------

    def progresso(self, valor):

        if self.callback_progress:
            self.callback_progress(valor)


    # --------------------------------------------------

    def definir_ficheiro(self, ficheiro):

        self.ficheiro = ficheiro 

        
    # --------------------------------------------------

    def escolher_ficheiro(self):

        root = tk.Tk()

        root.withdraw()

        ficheiro = filedialog.askopenfilename(
            title="Selecionar ficheiro SAF-T",
            filetypes=[("SAF-T XML", "*.xml")]
        )

        root.destroy()

        return ficheiro


    # --------------------------------------------------

    def abrir_xml(self):

        if self.ficheiro:
            ficheiro = self.ficheiro
        else:
            ficheiro = self.escolher_ficheiro()

        if not ficheiro:
            raise Exception("Nenhum ficheiro selecionado.")

        
        self.log("Abrir XML...")
        self.progresso(10)

        tree = ET.parse(ficheiro)

        self.root = tree.getroot()

        self.ns = {

            "ns":"urn:OECD:StandardAuditFile-Tax:PT_1.04_01"

        }

    # --------------------------------------------------

    def ler_header(self):

        self.log("")
        self.log("Ler Header...")
        self.progresso(20)

        empresa = self.root.findtext(
            ".//ns:Header/ns:CompanyName",
            default="",
            namespaces=self.ns
        )

        nif = self.root.findtext(
            ".//ns:Header/ns:TaxRegistrationNumber",
            default="",
            namespaces=self.ns
        )

        inicio = self.root.findtext(
            ".//ns:Header/ns:StartDate",
            default="",
            namespaces=self.ns
        )

        fim = self.root.findtext(
            ".//ns:Header/ns:EndDate",
            default="",
            namespaces=self.ns
        )

        self.header={

            "empresa":empresa,

            "nif":nif,

            "inicio":inicio,

            "fim":fim

        }

        self.log(f"Empresa: {empresa}")
        self.log(f"NIF: {nif}")



       # --------------------------------------------------

    def ler_clientes(self):

        self.log("")
        self.log("Ler Clientes...")
        self.progresso(30)

        for c in self.root.findall(

            ".//ns:MasterFiles/ns:Customer",

            self.ns

        ):

            codigo = c.findtext(

                "ns:CustomerID",

                default="",

                namespaces=self.ns

            )

            nome = c.findtext(

                "ns:CompanyName",

                default="",

                namespaces=self.ns

            )

            if not nome:

                nome = c.findtext(

                    "ns:CustomerName",

                    default="",

                    namespaces=self.ns

                )

            nif = c.findtext(

                "ns:CustomerTaxID",

                default="",

                namespaces=self.ns

            )

            pais = c.findtext(

                "ns:BillingAddress/ns:Country",

                default="PT",

                namespaces=self.ns

            )

            self.clientes[codigo] = {

                "nome": nome,

                "nif": nif,

                "pais": pais

            }

        self.log(f"{len(self.clientes):,} clientes carregados")

    # --------------------------------------------------

    def ler_artigos(self):

        self.log("")
        self.log("Ler Artigos...")
        self.progresso(40)

        for p in self.root.findall(

            ".//ns:MasterFiles/ns:Product",

            self.ns

        ):

            codigo = p.findtext(

                "ns:ProductCode",

                default="",

                namespaces=self.ns

            )

            descricao = p.findtext(

                "ns:ProductDescription",

                default="",

                namespaces=self.ns

            )

            grupo = p.findtext(

                "ns:ProductGroup",

                default="",

                namespaces=self.ns

            )

            self.artigos[codigo] = {

                "descricao": descricao,

                "grupo": grupo

            }

        self.log(f"{len(self.artigos):,} artigos carregados")


    # --------------------------------------------------

    def ler_faturas(self):

        self.log("")
        self.log("Ler Documentos...")
        self.progresso(50)

        documentos = 0
        linhas = 0

        self.dados = []

        for invoice in self.root.findall(
            ".//ns:SalesInvoices/ns:Invoice",
            self.ns
        ):

            documentos += 1

            documento = invoice.findtext(
                "ns:InvoiceNo",
                default="",
                namespaces=self.ns
            )

            data = invoice.findtext(
                "ns:InvoiceDate",
                default="",
                namespaces=self.ns
            )

            tipo = invoice.findtext(
                "ns:InvoiceType",
                default="",
                namespaces=self.ns
            )

            estado = invoice.findtext(
                "ns:DocumentStatus/ns:InvoiceStatus",
                default="",
                namespaces=self.ns
            )

            cliente_id = invoice.findtext(
                "ns:CustomerID",
                default="",
                namespaces=self.ns
            )

            cliente = self.clientes.get(
                cliente_id,
                {
                    "nome": "Consumidor Final",
                    "nif": "",
                    "pais": "PT"
                }
            )

            nome_cliente = cliente["nome"]

            nif_cliente = cliente["nif"]

            pais_cliente = cliente["pais"]

            # --------------------------------------------------

            for line in invoice.findall(
                "ns:Line",
                self.ns
            ):

                linhas += 1

                artigo = line.findtext(
                    "ns:ProductCode",
                    default="",
                    namespaces=self.ns
                )

                descricao = self.artigos.get(
                    artigo,
                    {}
                ).get(
                    "descricao",
                    ""
                )

                # Se não existir nos MasterFiles,
                # utilizar a descrição da linha da fatura

                if not descricao:

                    descricao = line.findtext(
                        "ns:ProductDescription",
                        default="",
                        namespaces=self.ns
                    )

                quantidade = float(
                    line.findtext(
                        "ns:Quantity",
                        default="0",
                        namespaces=self.ns
                    )
                )

                preco = float(
                    line.findtext(
                        "ns:UnitPrice",
                        default="0",
                        namespaces=self.ns
                    )
                )

                debito = float(
                    line.findtext(
                        "ns:DebitAmount",
                        default="0",
                        namespaces=self.ns
                    )
                )

                credito = float(
                    line.findtext(
                        "ns:CreditAmount",
                        default="0",
                        namespaces=self.ns
                    )
                )

                taxa = float(
                    line.findtext(
                        ".//ns:TaxPercentage",
                        default="0",
                        namespaces=self.ns
                    )
                )
                codigo_iva = line.findtext(
                    ".//ns:TaxCode",
                    default="",
                    namespaces=self.ns
                )

                codigo_isencao = line.findtext(
                    ".//ns:TaxExemptionCode",
                    default="",
                    namespaces=self.ns
                )

                motivo_isencao = line.findtext(
                    ".//ns:TaxExemptionReason",
                    default="",
                    namespaces=self.ns
                )

                iva_debito = round(
                    debito * taxa / 100,
                    2
                )

                iva_credito = round(
                    credito * taxa / 100,
                    2
                )

                # ------------------------------------------
                # NOTAS DE CRÉDITO
                # ------------------------------------------

                if tipo == "NC":

                    quantidade *= -1
                    debito *= -1
                    credito *= -1
                    iva_debito *= -1
                    iva_credito *= -1

                total = (
                    debito +
                    iva_debito +
                    credito +
                    iva_credito
                )

                self.dados.append({

                    "Documento": documento,
                    "Data": data,
                    "Tipo": tipo,
                    "Estado": estado,

                    "ClienteID": cliente_id,
                    "NIF": nif_cliente,
                    "Cliente": nome_cliente,
                    "País": pais_cliente,

                    "Artigo": artigo,
                    "Descrição": descricao,

                    "Quantidade": quantidade,
                    "Preço": preco,

                    "IVA %": taxa,
                    "Código IVA": codigo_iva,
                    "Código Isenção": codigo_isencao,
                    "Motivo Isenção": motivo_isencao,

                    "Débito": debito,
                    "IVA Débito": iva_debito,

                    "Crédito": credito,
                    "IVA Crédito": iva_credito,

                    "Total": total

                })

            if documentos % 1000 == 0:

                self.log(f"{documentos:,} documentos processados...")

        self.log(f"Documentos : {documentos:,}")
        self.log(f"Linhas     : {linhas:,}")
        self.log(f"Registos   : {len(self.dados):,}")


    # --------------------------------------------------

    def preparar_dataframe(self):

        self.log("")
        self.log("Preparar DataFrame...")
        self.progresso(60)

        self.df_original = pd.DataFrame(self.dados)

        self.df = self.df_original.copy()

        # ---------------------------------------
        # Datas
        # ---------------------------------------

        self.df["Data"] = pd.to_datetime(
            self.df["Data"],
            errors="coerce"
        )

        # ---------------------------------------
        # Numéricos
        # ---------------------------------------

        colunas = [

            "Quantidade",
            "Preço",
            "Débito",
            "IVA Débito",
            "Crédito",
            "IVA Crédito",
            "Total"

        ]

        for coluna in colunas:

            self.df[coluna] = pd.to_numeric(
                self.df[coluna],
                errors="coerce"
            ).fillna(0)

        # ---------------------------------------
        # Contagem de documentos
        # ---------------------------------------

        self.total_documentos = self.df["Documento"].nunique()

        documentos_anulados = self.df[
            self.df["Estado"].isin(
                [
                    "A",
                    "ANN",
                    "Anulado"
                ]
            )
        ]

        self.total_anulados = documentos_anulados["Documento"].nunique()

        # ---------------------------------------
        # Remover documentos anulados
        # ---------------------------------------

        self.df = self.df[
            ~self.df["Estado"].isin(
                [
                    "A",
                    "ANN",
                    "Anulado"
                ]
            )
        ]

        self.total_nao_anulados = self.df["Documento"].nunique()

        # ---------------------------------------
        # Ordenar
        # ---------------------------------------

        self.df = self.df.sort_values(
            [
                "Data",
                "Documento"
            ]
        )

        self.df.reset_index(
            drop=True,
            inplace=True
        )

        # ---------------------------------------
        # Totais
        # ---------------------------------------

        self.total_clientes = self.df["Cliente"].nunique()

        self.total_artigos = self.df["Artigo"].nunique()

        self.total_debito = self.df["Débito"].sum()

        self.total_iva_debito = self.df["IVA Débito"].sum()

        self.total_credito = self.df["Crédito"].sum()

        self.total_iva_credito = self.df["IVA Crédito"].sum()

        self.total_geral = self.df["Total"].sum()

        # ---------------------------------------
        # Log
        # ---------------------------------------

        self.log("")
        self.log("Resumo")
        self.log("--------------------------------")

        self.log(f"Documentos ............: {self.total_documentos:,}")

        self.log(f"Não anulados .........: {self.total_nao_anulados:,}")

        self.log(f"Anulados .............: {self.total_anulados:,}")

        self.log(f"Clientes .............: {self.total_clientes:,}")

        self.log(f"Artigos ..............: {self.total_artigos:,}")

        self.log("")

        self.log(f"Débito ...............: {self.total_debito:,.2f}")

        self.log(f"IVA Débito ...........: {self.total_iva_debito:,.2f}")

        self.log(f"Crédito ..............: {self.total_credito:,.2f}")

        self.log(f"IVA Crédito ..........: {self.total_iva_credito:,.2f}")

        self.log(f"Total ................: {self.total_geral:,.2f}")

        self.progresso(70)

        # ---------------------------------------
        # DataFrame visível
        # ---------------------------------------

        self.df_visivel = self.df.copy()

        self.df_movimentos = self.df.copy()

    
    # =====================================================
    # PREPARAR DATAFRAME DOS DOCUMENTOS
    # =====================================================

    def preparar_documentos(self):

        self.log("")
        self.log("Preparar Documentos...")

        self.df_documentos = (

            self.df

            .groupby(
                [
                    "Documento",
                    "Data",
                    "Tipo",
                    "Estado",
                    "Cliente",
                    "NIF",
                    "País"
                ],
                dropna=False
            )
            .agg(

                Base_Debito=("Débito", "sum"),

                IVA_Debito=("IVA Débito", "sum"),

                Base_Credito=("Crédito", "sum"),

                IVA_Credito=("IVA Crédito", "sum"),

                Total=("Total", "sum")

            )

            .reset_index()

        )

        # -----------------------------
        # Base Tributável
        # -----------------------------

        self.df_documentos["Base"] = (

            self.df_documentos["Base_Debito"]

            +

            self.df_documentos["Base_Credito"]

        )

        # -----------------------------
        # IVA
        # -----------------------------

        self.df_documentos["IVA"] = (

            self.df_documentos["IVA_Debito"]

            +

            self.df_documentos["IVA_Credito"]

        )

        # -----------------------------
        # Mercado
        # -----------------------------

        paises_ue = {

            "AT", "BE", "BG", "CY", "CZ", "DE",
            "DK", "EE", "ES", "FI", "FR", "GR",
            "HR", "HU", "IE", "IT", "LT", "LU",
            "LV", "MT", "NL", "PL", "RO", "SE",
            "SI", "SK"

        }

        self.df_documentos["Mercado"] = self.df_documentos["País"].apply(

            lambda p:

                "Nacional"

                if p == "PT"

                else (

                    "Intracomunitário"

                    if p in paises_ue

                    else "Extracomunitário"

                )

        )

        # -----------------------------
        # Estado
        # -----------------------------

        self.df_documentos["Estado"] = (
            self.df_documentos["Estado"]
            .replace({
                "A": "❌ Anulado",
                "ANN": "❌ Anulado"
            })
        )

        self.df_documentos["Estado"] = (
            self.df_documentos["Estado"]
            .replace("", "✅ Ativo")
        )


        # -----------------------------
        # Ordenação
        # -----------------------------

        self.df_documentos = (

            self.df_documentos

            .sort_values(
                [
                    "Data",
                    "Documento"
                ]
            )

            .reset_index(drop=True)

        )

        self.log(
            f"Documentos preparados: {len(self.df_documentos):,}"
        )




    # =====================================================
    # PREPARAR DATAFRAME DOS CLIENTES
    # =====================================================
    #
    # Cria um resumo por cliente que será utilizado
    # na aba Clientes.
    #
    # Este DataFrame é independente dos Movimentos.
    #
    # =====================================================

    def preparar_clientes(self):

        self.log("")
        self.log("Preparar Clientes...")

        self.df_clientes = (

            self.df

            .groupby(
                ["Cliente", "NIF"],
                dropna=False
            )

            .agg(

                Documentos=("Documento", "nunique"),

                Quantidade=("Quantidade", "sum"),

                Base_Debito=("Débito", "sum"),

                IVA_Debito=("IVA Débito", "sum"),

                Base_Credito=("Crédito", "sum"),

                IVA_Credito=("IVA Crédito", "sum"),

                Total=("Total", "sum")

            )

            .reset_index()

        )

        # -----------------------------
        # Base tributável
        # -----------------------------

        self.df_clientes["Base"] = (

            self.df_clientes["Base_Debito"]

            +

            self.df_clientes["Base_Credito"]

        )

        # -----------------------------
        # IVA
        # -----------------------------

        self.df_clientes["IVA"] = (

            self.df_clientes["IVA_Debito"]

            +

            self.df_clientes["IVA_Credito"]

        )

        # -----------------------------
        # Ordenação
        # -----------------------------

        self.df_clientes = (

            self.df_clientes

            .sort_values("Cliente")

            .reset_index(drop=True)

        )

        self.log(f"Clientes preparados: {len(self.df_clientes):,}")
        


    # =====================================================
    # PREPARAR DATAFRAME DOS ARTIGOS
    # =====================================================

    def preparar_artigos(self):

        self.log("")
        self.log("Preparar Artigos...")

        self.df_artigos = (

            self.df

            .groupby(
                ["Artigo", "Descrição", "Código IVA", "IVA %"],
                dropna=False
            )

            .agg(

                Documentos=("Documento", "nunique"),

                Quantidade=("Quantidade", "sum"),

                Base_Debito=("Débito", "sum"),

                IVA_Debito=("IVA Débito", "sum"),

                Base_Credito=("Crédito", "sum"),

                IVA_Credito=("IVA Crédito", "sum"),

                Total=("Total", "sum")

            )

            .reset_index()

        )

        # ----------------------------------------
        # Base
        # ----------------------------------------

        self.df_artigos["Base"] = (

            self.df_artigos["Base_Debito"]

            +

            self.df_artigos["Base_Credito"]

        )

        # ----------------------------------------
        # IVA
        # ----------------------------------------

        self.df_artigos["IVA"] = (

            self.df_artigos["IVA_Debito"]

            +

            self.df_artigos["IVA_Credito"]

        )

        # ----------------------------------------
        # Ordenação
        # ----------------------------------------

        self.df_artigos = (

            self.df_artigos

            .sort_values(
                ["Artigo", "Código IVA", "IVA %"]
            )

            .reset_index(drop=True)

        )

        self.log(
            f"Artigos preparados: {len(self.df_artigos):,}"
        )
    

    # =====================================================
    # PREPARAR DATAFRAME DO IVA
    # =====================================================

    def preparar_iva(self):

        self.log("")
        self.log("Preparar IVA...")

        self.df_iva = (

            self.df

            .groupby(
                ["Código IVA", "IVA %"],
                dropna=False
            )

            .agg(

                Base_Debito=("Débito", "sum"),

                IVA_Debito=("IVA Débito", "sum"),

                Base_Credito=("Crédito", "sum"),

                IVA_Credito=("IVA Crédito", "sum"),

                Total=("Total", "sum")

            )

            .reset_index()

        )

        # ----------------------------------------
        # Base
        # ----------------------------------------

        self.df_iva["Base"] = (

            self.df_iva["Base_Debito"]

            +

            self.df_iva["Base_Credito"]

        )

        # ----------------------------------------
        # IVA
        # ----------------------------------------

        self.df_iva["IVA"] = (

            self.df_iva["IVA_Debito"]

            +

            self.df_iva["IVA_Credito"]

        )

        # ----------------------------------------
        # Ordenação
        # ----------------------------------------

        self.df_iva = (

            self.df_iva

            .sort_values(
                ["IVA %", "Código IVA"]
            )

            .reset_index(drop=True)

        )

        self.log(
            f"Taxas IVA preparadas: {len(self.df_iva):,}"
        )

    #-----------------------------------------------------------------
        
    def executar(self):

        self.inicio = time.time()

        self.log("")
        self.log("===================================")
        self.log("      SAFT ANALYZER PT")
        self.log("===================================")
        self.log("")

        self.abrir_xml()

        self.ler_header()

        self.ler_clientes()

        self.ler_artigos()

        self.ler_faturas()

        self.preparar_dataframe()

        self.preparar_documentos()

        self.preparar_clientes()

        self.preparar_artigos()

        self.preparar_iva()

        segundos = round(time.time() - self.inicio, 2)

        self.log("")
        self.log(f"Processamento concluído em {segundos} segundos.")

 
#------------------------------------------------------------------------        

class AppGUI:

    def __init__(self):

        self.app = SaftAnalyzer()

        self.janela = ctk.CTk()

        self.janela.title("SAFT Analyzer PT")

        self.janela.minsize(1200, 700)

        self.janela.after(
            100,
            lambda: self.janela.state("zoomed")
        )

        self.janela.configure(fg_color="#ECEFF4")

        self.criar_interface()

        self.app.callback_log = self.escrever_log

        self.app.callback_progress = self.atualizar_progresso

        self.ordem_colunas = {}

        self.colunas = {
            "Documento":  {"width": 140, "anchor": "center"},
            "Data":       {"width": 100, "anchor": "center"},
            "Cliente":    {"width": 250, "anchor": "w"},
            "Artigo":     {"width": 250, "anchor": "w"},
            "Base":    {"width": 110, "anchor": "e"},
            "IVA":        {"width": 90, "anchor": "e"},
            "Quantidade": {"width": 110, "anchor": "e"},
            "Total":      {"width": 110, "anchor": "e"},
        }

        self.janela.mainloop()
        
        

        


    def criar_interface(self):

        # MENU
        self.menu = ctk.CTkFrame(
            self.janela,
            width=220,
            fg_color="#1E293B",
            corner_radius=0
        )

        self.menu.pack(side="left", fill="y")
        self.menu.pack_propagate(False)

        ctk.CTkLabel(
            self.menu,
            text="SAFT\nAnalyzer",
            font=("Segoe UI",26,"bold"),
            text_color="white"
        ).pack(pady=(30,10))

        ctk.CTkLabel(
            self.menu,
            text="Versão 6",
            text_color="#CBD5E1",
            font=("Segoe UI",12)
        ).pack(pady=(0,25))

        #-----BOTOES -----

        self.btn_dashboard = ctk.CTkButton(
            self.menu,
            text="Dashboard",
            height=42,
            fg_color="transparent",
            hover_color="#334155",
            anchor="w",
            font=("Segoe UI",15),
            command=self.mostrar_dashboard
        )
        self.btn_dashboard.pack(fill="x", padx=15, pady=4)


        # =====================================================
        # Botão Documentos
        # =====================================================

        self.btn_documentos = ctk.CTkButton(
            self.menu,
            text="Documentos",
            height=42,
            fg_color="transparent",
            hover_color="#334155",
            anchor="w",
            font=("Segoe UI", 15),
            command=self.mostrar_documentos_v6
        )

        self.btn_documentos.pack(fill="x", padx=15, pady=4 )
        

        # =====================================================
        # Botão Movimentos
        # =====================================================

        self.btn_movimentos = ctk.CTkButton(
            self.menu,
            text="Movimentos",
            height=42,
            fg_color="transparent",
            hover_color="#334155",
            anchor="w",
            font=("Segoe UI",15),
            command=self.mostrar_movimentos_v6
        )

        self.btn_movimentos.pack(fill="x", padx=15, pady=4)

        self.btn_clientes = ctk.CTkButton(
            self.menu,
            text="Clientes",
            height=42,
            fg_color="transparent",
            hover_color="#334155",
            anchor="w",
            font=("Segoe UI",15),
            command=self.mostrar_clientes
        )
        self.btn_clientes.pack(fill="x", padx=15, pady=4)

        self.btn_artigos = ctk.CTkButton(
            self.menu,
            text="Artigos",
            height=42,
            fg_color="transparent",
            hover_color="#334155",
            anchor="w",
            font=("Segoe UI",15),
            command=self.mostrar_artigos_v6
        )
        self.btn_artigos.pack(fill="x", padx=15, pady=4)

        self.btn_iva = ctk.CTkButton(
            self.menu,
            text="IVA",
            height=42,
            fg_color="transparent",
            hover_color="#334155",
            anchor="w",
            font=("Segoe UI",15),
            command=self.mostrar_iva_v6
        )
        self.btn_iva.pack(fill="x", padx=15, pady=4)

        self.area = ctk.CTkFrame(
            self.janela,
            fg_color="#ECEFF4"
        )


        # =====================================================
        # BOTÃO FECHAR
        # Fecha a aplicação
        # =====================================================

        self.btn_fechar = ctk.CTkButton(
            self.menu,
            text="Fechar",
            height=42,
            fg_color="#B91C1C",
            hover_color="#991B1B",
            command=self.janela.destroy
        )

        self.btn_fechar.pack(
            side="bottom",
            fill="x",
            padx=15,
            pady=20
        )

        self.area.pack(fill="both", expand=True)

        # ==========================
        # TOPO
        # ==========================

        self.topo = ctk.CTkFrame(
            self.area,
            height=80,
            fg_color="white"
        )
        self.topo.pack(fill="x", padx=20, pady=20)
        self.topo.pack_propagate(False)

        self.lbl_ficheiro = ctk.CTkLabel(
            self.topo,
            text="Nenhum ficheiro selecionado",
            font=("Segoe UI",15)
        )
        self.lbl_ficheiro.pack(side="left", padx=20)

        self.btn_abrir = ctk.CTkButton(
            self.topo,
            text="Abrir SAF-T",
            width=140,
            command=self.abrir_ficheiro
        )

        self.btn_abrir.pack(side="right", padx=10, pady=15)


        self.btn_analisar = ctk.CTkButton(
            self.topo,
            text="Analisar",
            width=140,
            command=self.executar
        )

        self.btn_analisar.pack(side="right", padx=10, pady=15)


        

        # -----------------------------
        # Área de conteúdo
        # -----------------------------

        self.conteudo = ctk.CTkFrame(
            self.area,
            fg_color="transparent"
        )

        self.conteudo.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0,20)
        )

        # Barra de progresso

        self.progress = ctk.CTkProgressBar(self.conteudo)
        self.progress.pack(fill="x", pady=(0,10))
        self.progress.set(0)

        # ------------------------------------
        # Painel dinâmico
        # ------------------------------------

        self.painel = ctk.CTkFrame(
            self.conteudo,
            fg_color="transparent"
        )

        self.painel.pack(
            fill="both",
            expand=True
        )

        # ------------------------------------
        # LOG (fixo)
        # ------------------------------------

        self.frame_log = ctk.CTkFrame(
            self.conteudo,
            height=170
        )

        self.frame_log.pack(
            fill="x",
            pady=(10, 0)
        )

        self.frame_log.pack_propagate(False)

        self.log = ctk.CTkTextbox(
            self.frame_log,
            font=("Consolas", 12)
        )

        self.log.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )

        self.log.insert("end", "SAFT Analyzer pronto.\n")
     

        

    def abrir_ficheiro(self):

        ficheiro = filedialog.askopenfilename(
            title="Selecionar SAF-T",
            filetypes=[("XML", "*.xml")]
        )

        if ficheiro:

            self.app.definir_ficheiro(ficheiro)

            self.lbl_ficheiro.configure(
                text=os.path.basename(ficheiro)
            )


    # =====================================================
    # BLOQUEAR INTERFACE
    # =====================================================
    #
    # Desativa todos os botões enquanto decorre o
    # processamento do SAF-T.
    #
    # O botão Fechar permanece ativo.
    # =====================================================

    def bloquear_interface(self):

        botoes = [

            self.btn_dashboard,
            self.btn_documentos,
            self.btn_movimentos,
            self.btn_clientes,
            self.btn_artigos,
            self.btn_iva,
            

            self.btn_abrir,
            self.btn_analisar

        ]

        for botao in botoes:
            botao.configure(state="disabled")


    # =====================================================
    # DESBLOQUEAR INTERFACE
    # =====================================================
    #
    # Reativa todos os botões quando termina
    # o processamento.
    # =====================================================

    def desbloquear_interface(self):

        botoes = [

            self.btn_dashboard,
            self.btn_documentos,
            self.btn_movimentos,
            self.btn_clientes,
            self.btn_artigos,
            self.btn_iva,
            
            self.btn_abrir,
            self.btn_analisar

        ]

        for botao in botoes:
            botao.configure(state="normal")


    def executar(self):

        if self.log.winfo_exists():
            self.log.delete("1.0", "end")
        self.progress.set(0)

        self.bloquear_interface()


        threading.Thread(
            target=self.processar,
            daemon=True
        ).start()



    def processar(self):

        try:

            self.app.executar()

            self.janela.after(
                0,
                self.finalizar_processamento
            )
            
        except Exception as erro:

            msg = str(erro)

            self.janela.after(
                0,
                lambda: (
                    self.desbloquear_interface(),
                    messagebox.showerror("Erro", msg)
                )
                            )


    def escrever_log(self, texto):

        def atualizar():

            if not self.log.winfo_exists():
                return

            self.log.insert("end", texto + "\n")
            self.log.see("end")

        self.janela.after(0, atualizar)


    def atualizar_progresso(self, valor):

            self.janela.after(
                0,
                lambda: self.progress.set(valor / 100)
            )


    def finalizar_processamento(self):

        self.desbloquear_interface()

        resumo = (
            f"Documentos : {self.app.total_documentos:,}\n"
            f"Clientes   : {self.app.total_clientes:,}\n"
            f"Artigos    : {self.app.total_artigos:,}\n\n"
            f"Total      : {self.app.total_geral:,.2f} €"
        )

        messagebox.showinfo(
            "Processamento concluído",
            resumo
        )
  
        self.mostrar_dashboard()


    def limpar_conteudo(self):

        for widget in self.painel.winfo_children():
            widget.destroy()


    def mostrar_dashboard(self):

        self.limpar_conteudo()

        ctk.CTkLabel(
            self.painel,
            text="Dashboard",
            font=("Segoe UI", 24, "bold")
        ).pack(pady=(15, 20))

        # =====================================================
        # DADOS
        # =====================================================

        dados = [

            ("Empresa", self.app.header.get("empresa", "")),

            ("NIF", self.app.header.get("nif", "")),

            ("Período",
             f"{self.app.header.get('inicio','')}  até  {self.app.header.get('fim','')}")

        ]

        # =====================================================
        # CABEÇALHO
        # =====================================================

        for titulo, valor in dados:

            linha = ctk.CTkFrame(
                self.painel,
                fg_color="transparent"
            )

            linha.pack(fill="x", padx=40, pady=4)

            ctk.CTkLabel(
                linha,
                text=titulo,
                width=150,
                anchor="w",
                font=("Segoe UI",14,"bold")
            ).pack(side="left")

            ctk.CTkLabel(
                linha,
                text=str(valor),
                anchor="w",
                font=("Segoe UI",14)
            ).pack(side="left")

        # =====================================================
        # SEPARADOR
        # =====================================================

        ctk.CTkFrame(
            self.painel,
            height=2,
            fg_color="#CFCFCF"
        ).pack(fill="x", padx=40, pady=12)

        # =====================================================
        # RESUMO
        # =====================================================

        # Documentos

        linha = ctk.CTkFrame(
            self.painel,
            fg_color="transparent"
        )

        linha.pack(fill="x", padx=40, pady=4)

        ctk.CTkLabel(
            linha,
            text="Documentos",
            width=150,
            anchor="w",
            font=("Segoe UI",14,"bold")
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text=f"{self.app.total_documentos:,}",
            font=("Segoe UI",14)
        ).pack(side="left")


        # Não anulados / Anulados

        linha = ctk.CTkFrame(
            self.painel,
            fg_color="transparent"
        )

        linha.pack(fill="x", padx=40, pady=4)

        ctk.CTkLabel(
            linha,
            text="Não anulados",
            width=150,
            anchor="w",
            font=("Segoe UI",14,"bold")
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text=f"{self.app.total_nao_anulados:,}",
            width=80,
            anchor="w",
            font=("Segoe UI",14)
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text="Anulados",
            width=100,
            anchor="w",
            font=("Segoe UI",14,"bold")
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text=f"{self.app.total_anulados:,}",
            font=("Segoe UI",14)
        ).pack(side="left")


        # Clientes

        linha = ctk.CTkFrame(
            self.painel,
            fg_color="transparent"
        )

        linha.pack(fill="x", padx=40, pady=4)

        ctk.CTkLabel(
            linha,
            text="Clientes",
            width=150,
            anchor="w",
            font=("Segoe UI",14,"bold")
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text=f"{self.app.total_clientes:,}",
            font=("Segoe UI",14)
        ).pack(side="left")


        # Artigos

        linha = ctk.CTkFrame(
            self.painel,
            fg_color="transparent"
        )

        linha.pack(fill="x", padx=40, pady=4)

        ctk.CTkLabel(
            linha,
            text="Artigos",
            width=150,
            anchor="w",
            font=("Segoe UI",14,"bold")
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text=f"{self.app.total_artigos:,}",
            font=("Segoe UI",14)
        ).pack(side="left")

        # =====================================================
        # SEPARADOR
        # =====================================================

        ctk.CTkFrame(
            self.painel,
            height=2,
            fg_color="#CFCFCF"
        ).pack(fill="x", padx=40, pady=12)

        # =====================================================
        # TOTAL
        # =====================================================

        linha = ctk.CTkFrame(
            self.painel,
            fg_color="transparent"
        )

        linha.pack(fill="x", padx=40, pady=4)

        ctk.CTkLabel(
            linha,
            text="Total",
            width=150,
            anchor="w",
            font=("Segoe UI",16,"bold")
        ).pack(side="left")

        ctk.CTkLabel(
            linha,
            text=f"{self.app.total_geral:,.2f} €",
            font=("Segoe UI",16,"bold")
        ).pack(side="left")

        
    # =====================================================
    # MOVIMENTOS
    # =====================================================

    def mostrar_movimentos(self):

        self.mostrar_movimentos_v6()


    # =====================================================
    # DOCUMENTOS V6
    # =====================================================

    def mostrar_documentos_v6(self):

        if not hasattr(self, "_documentos_v6"):

            from documentos_v6 import DocumentosV6

            self._documentos_v6 = DocumentosV6(self)

        self._documentos_v6.mostrar()    

      
    # =====================================================
    # TESTE MOVIMENTOS V6
    # =====================================================

    def mostrar_movimentos_v6(self, df=None):

        if df is None:
            self.app.df_movimentos = self.app.df.copy()
        else:
            self.app.df_movimentos = df.copy()

        if not hasattr(self, "_movimentos_v6"):

            from movimentos_v6 import MovimentosV6

            self._movimentos_v6 = MovimentosV6(self)

        self._movimentos_v6.mostrar()


    
    # =====================================================
    # CLIENTES
    # =====================================================
    #
    # Interface idêntica à dos Movimentos.
    #
    # =====================================================

    def mostrar_clientes(self):

        if not hasattr(self, "_clientes_v6"):

            from clientes_v6 import ClientesV6

            self._clientes_v6 = ClientesV6(self)

        self._clientes_v6.mostrar()


    # =====================================================
    # ARTIGOS V6
    # =====================================================

    def mostrar_artigos_v6(self):

        
        if not hasattr(self, "_artigos_v6"):

            
            from artigos_v6 import ArtigosV6

            self._artigos_v6 = ArtigosV6(self)

        
        self._artigos_v6.mostrar()


    # =====================================================
    # IVA V6
    # =====================================================

    def mostrar_iva_v6(self):

        if not hasattr(self, "_iva_v6"):

            from iva_v6 import IVAV6

            self._iva_v6 = IVAV6(self)

        self._iva_v6.mostrar()
    
    # =====================================================
    # CARREGAR CLIENTES NA TABELA
    # =====================================================
    #
    # Esta função:
    #   - Limpa a Treeview
    #   - Carrega os clientes
    #   - Formata os valores
    #
    # Será utilizada por:
    #   - mostrar_clientes()
    #   - filtros
    #   - ordenação
    #
    # =====================================================

    def carregar_clientes(self, df):

        # Limpar Treeview
        self.tree_clientes.delete(
            *self.tree_clientes.get_children()
        )

        # Inserir linhas
        for indice, (_, linha) in enumerate(df.iterrows()):

            documentos = f"{int(linha['Documentos'])}"

            quantidade = (
                f"{linha['Quantidade']:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

            base = (
                f"{linha['Base']:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
                + " €"
            )

            iva = (
                f"{linha['IVA']:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
                + " €"
            )

            total = (
                f"{linha['Total']:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
                + " €"
            )

            tags = []

            if indice % 2 == 0:
                tags.append("par")
            else:
                tags.append("impar")

            if linha["Total"] < 0:
                tags.append("credito")

            self.tree_clientes.insert(
                "",
                "end",
                values=(
                    linha["Cliente"],
                    linha["NIF"],
                    documentos,
                    quantidade,
                    base,
                    iva,
                    total
                ),
                tags=tuple(tags)
            )
    

    # =====================================================
    # ATUALIZAR TOTAIS DOS CLIENTES
    # =====================================================

    def atualizar_totais_clientes(self, df=None):

        if df is None:
            df = self.df_clientes_visivel

        if df.empty:

            self.lbl_totais_clientes.configure(
                text="Registos: 0"
            )

            return

        registos = len(df)

        documentos = df["Documentos"].sum()

        quantidade = df["Quantidade"].sum()

        base = df["Base"].sum()

        iva = df["IVA"].sum()

        total = df["Total"].sum()

        def fmt(valor):

            return (
                f"{valor:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        texto = (
            f"Clientes: {registos:,}      "
            f"Documentos: {documentos:,}      "
            f"Quantidade: {fmt(quantidade)}      "
            f"Base: {fmt(base)} €      "
            f"IVA: {fmt(iva)} €      "
            f"Total: {fmt(total)} €"
        )

        texto = (
            texto.replace(",", "X")
                 .replace(".", ",")
                 .replace("X", ".")
        )

        self.lbl_totais_clientes.configure(
            text=texto
        )
    

    def atualizar_totais(self, df=None):

        if df is None:
            df = self.app.df_visivel

        if df is None or df.empty:
            self.lbl_totais.configure(text="Registos: 0")
            return

        registos = len(df)

        quantidade = df["Quantidade"].sum()

        base = (
            df["Débito"].sum() +
            df["Crédito"].sum()
        )

        iva = (
            df["IVA Débito"].sum() +
            df["IVA Crédito"].sum()
        )

        total = df["Total"].sum()

        def euro(valor):
            return (
                f"{valor:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        texto = (
            f"Registos: {registos:,}      "
            f"Quantidade: {euro(quantidade)}      "
            f"Base: {euro(base)} €      "
            f"IVA: {euro(iva)} €      "
            f"Total: {euro(total)} €"
        )

        texto = (
            texto.replace(",", "X")
                 .replace(".", ",")
                 .replace("X", ".")
        )

        self.lbl_totais.configure(text=texto)

    
    
    # =====================================================
    # CARREGAR MOVIMENTOS NA TABELA
    # =====================================================
    #
    # Esta função:
    #   - Limpa a Treeview
    #   - Carrega todos os registos do DataFrame
    #
    # No futuro será reutilizada pelos filtros,
    # pesquisa e ordenação.
    # =====================================================

    def carregar_movimentos(self, df):

        # ---------------------------------------------
        # Limpar tabela
        # ---------------------------------------------
        self.tree.delete(*self.tree.get_children())

        # ---------------------------------------------
        # Inserir linhas
        # ---------------------------------------------
        for indice, (_, linha) in enumerate(df.iterrows()):

            # Data
            if hasattr(linha["Data"], "strftime"):
                data = linha["Data"].strftime("%d-%m-%Y")
            else:
                data = str(linha["Data"])

            # Quantidade
            quantidade = (
                f"{linha['Quantidade']:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

            # Base
            base = linha["Débito"] + linha["Crédito"]

            base_txt = (
                f"{base:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
                + " €"
            )

            # IVA
            iva = linha["IVA Débito"] + linha["IVA Crédito"]

            iva_txt = (
                f"{iva:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
                + " €"
            )


            # Total
            total = (
                f"{linha['Total']:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
                + " €"
            )

            # Zebra
            tags = []

            if indice % 2 == 0:
                tags.append("par")
            else:
                tags.append("impar")

            # Notas de crédito (Total negativo)
            if linha["Total"] < 0:
                tags.append("credito")

            self.tree.insert(
                "",
                "end",
                values=(
                    linha["Documento"],
                    data,
                    linha["Cliente"],
                    linha["Artigo"],
                    base_txt,
                    iva_txt,
                    quantidade,
                    total
                ),
                tags=tuple(tags)
            )
                   

        self.atualizar_totais(df)

        
    def atualizar_resultados(self):

        total = len(self.app.df_original)

        visivel = len(self.app.df_visivel)

        if total == visivel:

            texto = f"{total:,} movimentos"

        else:

            texto = (
                f"{total:,} movimentos   |   "
                f"{visivel:,} encontrados"
            )

        self.lbl_resultados.configure(text=texto)
    

    def aplicar_filtros(self, event=None):

        df = self.app.df_original.copy()

        for coluna, entry in self.filtros.items():

            texto = entry.get().strip()

            if texto == "":
                continue

            filtro = (
                df[coluna]
                .astype(str)
                .str.lower()
                .str.contains(texto.lower(), na=False)
            )

            df = df[filtro]

        self.app.df_visivel = df

        self.carregar_movimentos(df)

        self.atualizar_resultados()




    def ordenar_movimentos(self, coluna):

        if self.app.df_visivel is None:
            return

        crescente = self.ordem_colunas.get(coluna, True)

        df = self.app.df_visivel.copy()

        # -----------------------------
        # Colunas calculadas
        # -----------------------------

        if coluna == "Base":

            df["__Base__"] = (
                df["Débito"] +
                df["Crédito"]
            )

            df = df.sort_values(
                "__Base__",
                ascending=crescente,
                kind="mergesort"
            )

            df.drop(columns="__Base__", inplace=True)

        elif coluna == "IVA":

            df["__IVA__"] = (
                df["IVA Débito"] +
                df["IVA Crédito"]
            )

            df = df.sort_values(
                "__IVA__",
                ascending=crescente,
                kind="mergesort"
            )

            df.drop(columns="__IVA__", inplace=True)

        # -----------------------------
        # Restantes colunas
        # -----------------------------

        else:

            df = df.sort_values(
                by=coluna,
                ascending=crescente,
                kind="mergesort"
            )

        self.app.df_visivel = df

        self.carregar_movimentos(df)

        self.ordem_colunas[coluna] = not crescente
        

if __name__ == "__main__":
    AppGUI()
