from models.news_model import crear_news, deactivate_news_card_model, cargar_news_activas, delete_news_card_model
import tkinter as tk
from tkinter import messagebox
class NewsController:
    def __init__(self, username):
        self.username = username
    
    def cargar_news_activas(self):
        """Obtiene datos y devuelve para que la vista los renderice"""
        return cargar_news_activas()  # Solo retorna datos
    
    def crear_news_controller(self, tipo, nombre, urgencia, fecha_out, callback):
        """Crea news y ejecuta callback"""
        try:
            crear_news(tipo, nombre, urgencia, self.username, fecha_out)
            messagebox.showinfo("Éxito", "News creada")
            if callback:
                callback()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def delete_news_card_controller(self, id_info, callback):
        """Elimina news con confirmación"""
        if messagebox.askyesno("Confirmar", "¿Eliminar?"):
            delete_news_card_model(id_info)
            if callback:
                callback()
    
    def deactivate_news_card_controller(self, id_info, callback):
        """Desactiva news con confirmación"""
        if messagebox.askyesno("Confirmar", "¿Desactivar?"):
            deactivate_news_card_model(id_info)
            if callback:
                callback()
    
    def limpiar_news_form(self, tipo_var, nombre_var, urgencia_var, fecha_out_var):
        """Limpia formulario"""
        tipo_var.set("")
        nombre_var.set("")
        urgencia_var.set("")
        fecha_out_var.set("")