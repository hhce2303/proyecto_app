
# ==================== tickets TABLE PRINTING ====================

def show_tickets_on_table(tickets):
    """
    Llena y retorna los datos para un tksheet (no imprime en consola).
    Retorna headers y data para ser usados en un tksheet.
    """
    headers = ["ID", "Asunto", "sitio", "Solicitante", "Estado", "Creado", "Asignado"]
    data = []
    if not tickets:
        return headers, []
    for t in tickets:
        ticket_id = t.get('id', '')
        subject = t.get('subject', '') + ('..' if len(t.get('subject', '')) > 48 else '')
        site = (t.get('site') or {}).get('name', '')
        requester = t.get('requester', {}).get('name', '')
        status = t.get('status', {}).get('name', '')
        creado = t.get('created_time', {}).get('display_value', '')
        tech = t.get('technician')
        asignado = tech.get('name', '') if isinstance(tech, dict) else ''
        data.append([ticket_id, subject, site, requester, status, creado, asignado])
    return headers, data


