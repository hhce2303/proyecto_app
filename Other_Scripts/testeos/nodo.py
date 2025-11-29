import tkinter as tk
from tkinter import simpledialog, messagebox

class Nodo:
    def __init__(self, canvas, x, y, texto):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.radio = 40
        self.texto = texto
        self.id_circulo = canvas.create_oval(
            x - self.radio, y - self.radio,
            x + self.radio, y + self.radio,
            fill="lightblue", outline="black", width=2
        )
        self.id_texto = canvas.create_text(x, y, text=texto, font=("Arial", 10, "bold"))
        self.arrastrando = False

    def mover(self, dx, dy):
        self.x += dx
        self.y += dy
        self.canvas.move(self.id_circulo, dx, dy)
        self.canvas.move(self.id_texto, dx, dy)

    def contiene(self, x, y):
        return (self.x - self.radio <= x <= self.x + self.radio) and \
               (self.y - self.radio <= y <= self.y + self.radio)

    def eliminar(self):
        self.canvas.delete(self.id_circulo)
        self.canvas.delete(self.id_texto)

class MapaMentalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mapa Mental con Tkinter")
        self.canvas = tk.Canvas(root, bg="white", width=800, height=600)
        self.canvas.pack(fill="both", expand=True)

        self.nodos = []
        self.lineas = []
        self.nodo_seleccionado = None
        self.nodo_conexion = None
        self.ultimo_x = 0
        self.ultimo_y = 0

        # Eventos
        self.canvas.bind("<Button-1>", self.click_izquierdo)
        self.canvas.bind("<B1-Motion>", self.arrastrar)
        self.canvas.bind("<ButtonRelease-1>", self.soltar)
        self.canvas.bind("<Button-3>", self.click_derecho)
        self.root.bind("<Return>", self.conectar_nodos)

        # Menú
        menu_bar = tk.Menu(root)
        root.config(menu=menu_bar)
        menu_nodo = tk.Menu(menu_bar, tearoff=0)
        menu_nodo.add_command(label="Agregar Nodo", command=self.agregar_nodo)
        menu_bar.add_cascade(label="Opciones", menu=menu_nodo)

    def agregar_nodo(self):
        texto = simpledialog.askstring("Nuevo Nodo", "Ingrese el texto del nodo:")
        if texto:
            nodo = Nodo(self.canvas, 400, 300, texto)
            self.nodos.append(nodo)

    def click_izquierdo(self, event):
        for nodo in self.nodos:
            if nodo.contiene(event.x, event.y):
                self.nodo_seleccionado = nodo
                self.ultimo_x = event.x
                self.ultimo_y = event.y
                return
        self.nodo_seleccionado = None

    def arrastrar(self, event):
        if self.nodo_seleccionado:
            dx = event.x - self.ultimo_x
            dy = event.y - self.ultimo_y
            self.nodo_seleccionado.mover(dx, dy)
            self.ultimo_x = event.x
            self.ultimo_y = event.y
            self.redibujar_lineas()

    def soltar(self, event):
        self.nodo_seleccionado = None

    def click_derecho(self, event):
        for nodo in self.nodos:
            if nodo.contiene(event.x, event.y):
                if messagebox.askyesno("Eliminar Nodo", f"¿Eliminar nodo '{nodo.texto}'?"):
                    self.eliminar_nodo(nodo)
                return

    def eliminar_nodo(self, nodo):
        nodo.eliminar()
        self.nodos.remove(nodo)
        self.lineas = [l for l in self.lineas if nodo not in l]
        self.redibujar_lineas()

    def conectar_nodos(self, nodo1, nodo2):
        if nodo1 != nodo2:
            self.lineas.append((nodo1, nodo2))
            self.redibujar_lineas()

    def redibujar_lineas(self):
        self.canvas.delete("linea")
        for nodo1, nodo2 in self.lineas:
            self.canvas.create_line(
                nodo1.x, nodo1.y, nodo2.x, nodo2.y,
                fill="black", width=2, tags="linea"
            )

if __name__ == "__main__":
    root = tk.Tk()
    app = MapaMentalApp(root)
    root.mainloop()