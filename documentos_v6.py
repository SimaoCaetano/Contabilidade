import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

from tabela_documentos import TabelaDocumentos
from exportador_saft import listar_series, exportar_serie


class DocumentosV6:

    def __init__(self, gui):
        self.gui = gui
        self.app = gui.app
        self.tabela = None

    def mostrar(self):
        self.gui.limpar_conteudo()

        topo = ctk.CTkFrame(self.gui.painel, fg_color="transparent")
        topo.pack(fill="x", padx=15, pady=(10, 5))

        titulo = ctk.CTkLabel(
            topo,
            text="Documentos",
            font=("Segoe UI", 22, "bold")
        )
        titulo.pack(side="left")

        btn_exportar = ctk.CTkButton(
            topo,
            text="Exportar Série SAF-T 1.04",
            width=210,
            height=38,
            command=self.exportar_serie
        )
        btn_exportar.pack(side="right")

        self.tabela = TabelaDocumentos(self.gui.painel)
        self.tabela.gui = self.gui
        self.tabela.pack(fill="both", expand=True)
        self.tabela.mostrar(self.app.df_documentos)

    def exportar_serie(self):
        ficheiro = self.app.ficheiro

        if not ficheiro or not os.path.isfile(ficheiro):
            messagebox.showwarning(
                "SAF-T",
                "Abra primeiro um ficheiro SAF-T."
            )
            return

        try:
            series = listar_series(ficheiro)
        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Não foi possível ler as séries.\n\n{e}"
            )
            return

        if not series:
            messagebox.showwarning(
                "SAF-T",
                "Não foram encontradas séries em SalesInvoices."
            )
            return

        janela = ctk.CTkToplevel(self.gui.janela)
        janela.title("Exportar série SAF-T 1.04")
        janela.geometry("500x260")
        janela.transient(self.gui.janela)
        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="Exportar uma série",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=(25, 8))

        ctk.CTkLabel(
            janela,
            text="Selecione a série que pretende exportar:",
            font=("Segoe UI", 13)
        ).pack(pady=(0, 10))

        combo = ctk.CTkComboBox(
            janela,
            values=series,
            width=360,
            height=38
        )
        combo.set(series[0])
        combo.pack(pady=5)

        def executar_exportacao():
            serie = combo.get().strip()
            if not serie:
                return

            nome_base = os.path.splitext(os.path.basename(ficheiro))[0]
            nome_seguro = serie.replace("/", "-").replace("\\", "-")
            destino = filedialog.asksaveasfilename(
                title="Guardar SAF-T da série",
                initialfile=f"{nome_base}_{nome_seguro}_SAFT104.xml",
                defaultextension=".xml",
                filetypes=[("SAF-T XML", "*.xml")]
            )

            if not destino:
                return

            try:
                resultado = exportar_serie(
                    ficheiro,
                    serie,
                    destino
                )
            except Exception as e:
                messagebox.showerror(
                    "Erro na exportação",
                    f"Não foi possível exportar a série.\n\n{e}",
                    parent=janela
                )
                return

            janela.destroy()

            messagebox.showinfo(
                "Exportação concluída",
                "SAF-T 1.04_01 criado com sucesso.\n\n"
                f"Série: {resultado['serie']}\n"
                f"Documentos: {resultado['documentos']:,}\n"
                f"Débito: {resultado['total_debito']:,.2f}\n"
                f"Crédito: {resultado['total_credito']:,.2f}\n\n"
                f"Ficheiro:\n{resultado['ficheiro']}"
            )

        ctk.CTkButton(
            janela,
            text="Exportar",
            width=150,
            height=40,
            command=executar_exportacao
        ).pack(side="left", padx=(80, 10), pady=30)

        ctk.CTkButton(
            janela,
            text="Cancelar",
            width=150,
            height=40,
            fg_color="#64748B",
            hover_color="#475569",
            command=janela.destroy
        ).pack(side="left", padx=10, pady=30)
