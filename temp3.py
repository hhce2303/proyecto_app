import customtkinter
import os
from PIL import Image
import under_super

# --- Simple tester to preview icons from under_super.ICON_PATH ---
def run_icon_tester(max_size=(48, 48)):
    """Abre una ventana simple que carga y muestra los iconos de under_super.ICON_PATH.

    - Muestra cada archivo de imagen soportado en un frame con scroll.
    - Imprime en consola los archivos cargados y los que fallaron.
    - Cierra con el botón 'Cerrar' o con la X.
    """
    customtkinter.set_appearance_mode("dark")
    app = customtkinter.CTk()
    app.title("Icon Tester · ICON_PATH")
    app.geometry("700x520")

    header = customtkinter.CTkFrame(app)
    header.pack(fill="x", padx=10, pady=(10, 0))
    customtkinter.CTkLabel(
        header,
        text=f"ICON_PATH: {under_super.ICON_PATH}",
        anchor="w"
    ).pack(fill="x", padx=10, pady=8)

    body = customtkinter.CTkScrollableFrame(app, width=660, height=400)
    body.pack(fill="both", expand=True, padx=10, pady=10)
    body.grid_columnconfigure(0, weight=1)

    icons_dir = under_super.ICON_PATH
    supported = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".bmp"}
    loaded, failed = [], []

    if icons_dir and os.path.isdir(icons_dir):
        files = sorted([f for f in os.listdir(icons_dir) if os.path.splitext(f)[1].lower() in supported])
        if not files:
            customtkinter.CTkLabel(body, text="No se encontraron imágenes en ICON_PATH.").grid(row=0, column=0, padx=12, pady=8, sticky="w")
        else:
            r = 0
            for fname in files:
                fpath = os.path.join(icons_dir, fname)
                try:
                    img = Image.open(fpath)
                    # Convert to CTkImage to be DPI-friendly
                    cimg = customtkinter.CTkImage(light_image=img, dark_image=img, size=max_size)

                    row_frame = customtkinter.CTkFrame(body, corner_radius=6)
                    row_frame.grid(row=r, column=0, sticky="ew", padx=6, pady=4)
                    row_frame.grid_columnconfigure(1, weight=1)

                    lbl_img = customtkinter.CTkLabel(row_frame, image=cimg, text="")
                    lbl_img.image = cimg  # keep reference
                    lbl_img.grid(row=0, column=0, padx=8, pady=6)

                    customtkinter.CTkLabel(row_frame, text=fname, anchor="w").grid(row=0, column=1, sticky="w", padx=6)

                    loaded.append(fname)
                    r += 1
                except Exception as e:
                    failed.append((fname, str(e)))
    else:
        customtkinter.CTkLabel(body, text="ICON_PATH no existe o no es un directorio.").grid(row=0, column=0, padx=12, pady=8, sticky="w")

    footer = customtkinter.CTkFrame(app)
    footer.pack(fill="x", padx=10, pady=(0, 10))
    summary = f"Cargados: {len(loaded)}  |  Fallidos: {len(failed)}"
    customtkinter.CTkLabel(footer, text=summary, anchor="w").pack(side="left", padx=10, pady=8)
    customtkinter.CTkButton(footer, text="Cerrar", command=app.destroy).pack(side="right", padx=10, pady=8)

    # Console debug
    if loaded:
        print("[IconTester] Cargados:")
        for n in loaded:
            print(" -", n)
    if failed:
        print("[IconTester] Fallidos:")
        for n, err in failed:
            print(f" - {n}: {err}")

    app.mainloop()


class ScrollableCheckBoxFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, master, item_list, command=None, **kwargs):
        super().__init__(master, **kwargs)

        self.command = command
        self.checkbox_list = []
        for i, item in enumerate(item_list):
            self.add_item(item)

    def add_item(self, item):
        checkbox = customtkinter.CTkCheckBox(self, text=item)
        if self.command is not None:
            checkbox.configure(command=self.command)
        checkbox.grid(row=len(self.checkbox_list), column=0, pady=(0, 10))
        self.checkbox_list.append(checkbox)

    def remove_item(self, item):
        for checkbox in self.checkbox_list:
            if item == checkbox.cget("text"):
                checkbox.destroy()
                self.checkbox_list.remove(checkbox)
                return

    def get_checked_items(self):
        return [checkbox.cget("text") for checkbox in self.checkbox_list if checkbox.get() == 1]


class ScrollableRadiobuttonFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, master, item_list, command=None, **kwargs):
        super().__init__(master, **kwargs)

        self.command = command
        self.radiobutton_variable = customtkinter.StringVar()
        self.radiobutton_list = []
        for i, item in enumerate(item_list):
            self.add_item(item)

    def add_item(self, item):
        radiobutton = customtkinter.CTkRadioButton(self, text=item, value=item, variable=self.radiobutton_variable)
        if self.command is not None:
            radiobutton.configure(command=self.command)
        radiobutton.grid(row=len(self.radiobutton_list), column=0, pady=(0, 10))
        self.radiobutton_list.append(radiobutton)

    def remove_item(self, item):
        for radiobutton in self.radiobutton_list:
            if item == radiobutton.cget("text"):
                radiobutton.destroy()
                self.radiobutton_list.remove(radiobutton)
                return

    def get_checked_item(self):
        return self.radiobutton_variable.get()


class ScrollableLabelButtonFrame(customtkinter.CTkScrollableFrame):
    def __init__(self, master, command=None, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.command = command
        self.radiobutton_variable = customtkinter.StringVar()
        self.label_list = []
        self.button_list = []

    def add_item(self, item, image=None):
        label = customtkinter.CTkLabel(self, text=item, image=image, compound="left", padx=5, anchor="w")
        button = customtkinter.CTkButton(self, text="Command", width=100, height=24)
        if self.command is not None:
            button.configure(command=lambda: self.command(item))
        label.grid(row=len(self.label_list), column=0, pady=(0, 10), sticky="w")
        button.grid(row=len(self.button_list), column=1, pady=(0, 10), padx=5)
        self.label_list.append(label)
        self.button_list.append(button)

    def remove_item(self, item):
        for label, button in zip(self.label_list, self.button_list):
            if item == label.cget("text"):
                label.destroy()
                button.destroy()
                self.label_list.remove(label)
                self.button_list.remove(button)
                return


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("CTkScrollableFrame example")
        self.grid_rowconfigure(0, weight=1)
        self.columnconfigure(2, weight=1)

        # create scrollable checkbox frame
        self.scrollable_checkbox_frame = ScrollableCheckBoxFrame(master=self, width=200, command=self.checkbox_frame_event,
                                                                 item_list=[f"item {i}" for i in range(50)])
        self.scrollable_checkbox_frame.grid(row=0, column=0, padx=15, pady=15, sticky="ns")
        self.scrollable_checkbox_frame.add_item("new item")

        # create scrollable radiobutton frame
        self.scrollable_radiobutton_frame = ScrollableRadiobuttonFrame(master=self, width=500, command=self.radiobutton_frame_event,
                                                                       item_list=[f"item {i}" for i in range(100)],
                                                                       label_text="ScrollableRadiobuttonFrame")
        self.scrollable_radiobutton_frame.grid(row=0, column=1, padx=15, pady=15, sticky="ns")
        self.scrollable_radiobutton_frame.configure(width=200)
        self.scrollable_radiobutton_frame.remove_item("item 3")

        # create scrollable label and button frame
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.scrollable_label_button_frame = ScrollableLabelButtonFrame(master=self, width=300, command=self.label_button_frame_event, corner_radius=0)
        self.scrollable_label_button_frame.grid(row=0, column=2, padx=0, pady=0, sticky="nsew")
        for i in range(20):  # add items with images
            self.scrollable_label_button_frame.add_item(f"image and item {i}", image=customtkinter.CTkImage(Image.open(os.path.join(current_dir, "test_images", "chat_light.png"))))

    def checkbox_frame_event(self):
        print(f"checkbox frame modified: {self.scrollable_checkbox_frame.get_checked_items()}")

    def radiobutton_frame_event(self):
        print(f"radiobutton frame modified: {self.scrollable_radiobutton_frame.get_checked_item()}")

    def label_button_frame_event(self, item):
        print(f"label button frame clicked: {item}")


if __name__ == "__main__":
    # Ejecuta el tester de iconos por defecto; 
    # descomenta las 3 líneas siguientes si quieres abrir la demo original de scrollables.
    run_icon_tester()
    # customtkinter.set_appearance_mode("dark")
    # app = App()
    # app.mainloop()