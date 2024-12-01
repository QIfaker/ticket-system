from flask import current_app, g
from .ticket_system import TicketSystem

def get_db():
    if 'ticket_system' not in g:
        g.ticket_system = TicketSystem(current_app.config['DATABASE'])
        g.ticket_system.create_tables()
    return g.ticket_system 