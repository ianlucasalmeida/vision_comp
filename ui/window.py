import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
from core.engine import MediaEngine

class VisionCompWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Vision Comp")
        self.set_default_size(550, 420)
        self.engine = MediaEngine()

        # ToolbarView é o padrão do Libadwaita para envelopar a HeaderBar (botões de fechar)
        toolbar_view = Adw.ToolbarView()
        header_bar = Adw.HeaderBar()
        toolbar_view.add_top_bar(header_bar)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_margin_top(24)
        vbox.set_margin_bottom(24)
        vbox.set_margin_start(32)
        vbox.set_margin_end(32)

        # Classes de Compressão (Dropdown)
        size_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        size_label = Gtk.Label(label="Tamanho Limite:")
        
        self.size_options = ["5 MB", "10 MB", "15 MB", "20 MB", "25 MB (Edital IFPE)", "Personalizado"]
        self.size_model = Gtk.StringList.new(self.size_options)
        self.dropdown = Gtk.DropDown(model=self.size_model)
        self.dropdown.set_selected(4) # Inicia por padrão no "25 MB (Edital IFPE)"
        self.dropdown.connect("notify::selected", self.on_dropdown_changed)

        self.custom_entry = Gtk.Entry(placeholder_text="Ex: 30")
        self.custom_entry.set_visible(False) # Oculto por padrão

        size_box.append(size_label)
        size_box.append(self.dropdown)
        size_box.append(self.custom_entry)

        # Controles de Arquivo
        self.file_label = Gtk.Label(label="Nenhum arquivo selecionado")
        self.file_label.set_wrap(True)
        
        self.btn_select = Gtk.Button(label="Selecionar Arquivo")
        self.btn_select.connect("clicked", self.on_select_file)
        
        self.btn_compress = Gtk.Button(label="Iniciar Compressão")
        self.btn_compress.connect("clicked", self.on_compress)
        self.btn_compress.set_sensitive(False)
        
        # Barra de Progresso
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_fraction(0.0)

        # Montagem do Layout
        vbox.append(size_box)
        vbox.append(Gtk.Separator()) # Linha divisória
        vbox.append(self.btn_select)
        vbox.append(self.file_label)
        vbox.append(self.btn_compress)
        vbox.append(self.progress_bar)

        toolbar_view.set_content(vbox)
        self.set_content(toolbar_view)
        self.selected_file = None

    def on_dropdown_changed(self, dropdown, pspec):
        # Se selecionou "Personalizado" (índice 5), mostra a entry box
        is_custom = dropdown.get_selected() == 5
        self.custom_entry.set_visible(is_custom)

    def get_target_mb(self):
        idx = self.dropdown.get_selected()
        if idx == 5:
            try:
                return float(self.custom_entry.get_text().strip())
            except ValueError:
                return -1.0 # Erro de conversão
        else:
            # Extrai apenas o número da string, ignorando as letras
            return float(self.size_options[idx].split()[0])

    def on_select_file(self, button):
        dialog = Gtk.FileDialog(title="Selecione o vídeo")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        video_filter = Gtk.FileFilter()
        video_filter.set_name("Arquivos de Vídeo")
        video_filter.add_mime_type("video/*")
        filters.append(video_filter)
        dialog.set_filters(filters)

        dialog.open(self, None, self.on_file_selected)

    def on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.selected_file = file.get_path()
                self.file_label.set_text(self.selected_file.split("/")[-1])
                self.btn_compress.set_sensitive(True)
                self.progress_bar.set_fraction(0.0)
        except Exception as e:
            print(f"Seleção cancelada: {e}")

    def on_compress(self, button):
        target_mb = self.get_target_mb()
        if target_mb <= 0:
            self.file_label.set_text("Erro: Valor de tamanho inválido.")
            return

        self.btn_compress.set_sensitive(False)
        self.btn_select.set_sensitive(False)
        self.dropdown.set_sensitive(False)
        
        output_file = self.selected_file.rsplit(".", 1)[0] + f"_IFPE_{int(target_mb)}MB.mp4"
        self.file_label.set_text("Passo 1/2: Analisando quadros...\n(Isso pode demorar, mas garante a qualidade)")
        
        self.engine.compress_video(self.selected_file, output_file, target_mb, self.on_progress)

    def on_progress(self, fraction):
        # Envia a atualização para a thread principal da UI
        GLib.idle_add(self.update_progress_ui, fraction)

    def update_progress_ui(self, fraction):
        if fraction == -1.0:
            self.file_label.set_text("Erro na conversão!")
            self.reset_ui()
            return False
            
        if fraction >= 1.0:
            self.progress_bar.set_fraction(1.0)
            self.file_label.set_text("Sucesso! Arquivo pronto para o edital.")
            self.reset_ui()
            return False

        # Atualiza visual e texto dependendo do passo
        self.progress_bar.set_fraction(fraction)
        if fraction > 0.5:
            self.file_label.set_text("Passo 2/2: Comprimindo e finalizando...")
            
        return False

    def reset_ui(self):
        self.btn_compress.set_sensitive(True)
        self.btn_select.set_sensitive(True)
        self.dropdown.set_sensitive(True)