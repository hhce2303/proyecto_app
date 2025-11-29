import smtplib
from email.mime.text import MIMEText

# -------------------------------
# CONFIGURACIÓN
# -------------------------------
SMTP_SERVER = "smtp.office365.com"  # Cambia por tu servidor SMTP
SMTP_PORT = 587                     # 587 para STARTTLS, 465 para SSL
USERNAME = "hector.cruz@sig.systems"  # Tu usuario/correo
PASSWORD = "Hhce.sig#2303"          # Tu contraseña o contraseña de app
DESTINATARIO = "yonier.angulo@sig.systems"  # A quién enviar el correo

# -------------------------------
# MENSAJE
# -------------------------------
asunto = "Prueba de correo Python"
cuerpo = "✅ Este es un correo de prueba enviado desde Python."

msg = MIMEText(cuerpo)
msg['Subject'] = asunto
msg['From'] = USERNAME
msg['To'] = DESTINATARIO

# -------------------------------
# ENVÍO
# -------------------------------
try:
    # Conexión al servidor SMTP
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()  # Inicia TLS
    server.login(USERNAME, PASSWORD)
    server.sendmail(USERNAME, DESTINATARIO, msg.as_string())
    server.quit()
    print("✅ Correo enviado correctamente")
except Exception as e:
    print("❌ Error al enviar el correo:", e)
