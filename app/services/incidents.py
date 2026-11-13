"""12/11/2026 - Krista Colon: casos de uso de incidentes masivos (examen final, ficha 07).

Regla principal de la ficha: solo un supervisor o un administrador vincula un
ticket ABIERTO a un incidente TODAVIA ABIERTO, y un ticket pertenece como maximo
a un incidente. Los permisos y las reglas viven aqui, en el servicio; la ruta solo
recibe, llama y responde.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.errors import (
    IncidentNotFoundError,
    IncidentNotOpenError,
    PermissionDeniedError,
    TicketAlreadyLinkedError,
    TicketNotEligibleError,
    TicketNotFoundError,
    ValidationError,
)
from app.models.entities import Ticket, User
from app.models.enums import Role, TicketStatus
from app.models.incidents import Incident
from app.repositories.base import IncidentRepository, TicketRepository

# 12/11/2026 - Krista Colon: quienes gestionan incidentes y que tickets se pueden vincular.
MANAGERS = frozenset({Role.SUPERVISOR, Role.ADMINISTRATOR})
LINKABLE_STATUSES = frozenset({TicketStatus.OPEN, TicketStatus.IN_PROGRESS})


@dataclass
class IncidentDetail:
    """12/11/2026 - Krista Colon: un incidente con sus tickets vinculados."""

    incident: Incident
    tickets: list[Ticket] = field(default_factory=list)


class IncidentService:
    def __init__(self, incidents: IncidentRepository, tickets: TicketRepository) -> None:
        self._incidents = incidents
        self._tickets = tickets

    # --- permisos ---------------------------------------------------------

    @staticmethod
    def _require_manager(actor: User, action: str) -> None:
        if Role(actor.role) not in MANAGERS:
            raise PermissionDeniedError(
                f"only a supervisor or administrator can {action}",
                action=action,
            )

    @staticmethod
    def _require_staff(actor: User) -> None:
        # Los incidentes agrupan tickets de muchas personas: un solicitante no los ve.
        if not actor.is_staff:
            raise PermissionDeniedError("only support staff can view incidents", action="view_incidents")

    def _require_incident(self, incident_id: int) -> Incident:
        incident = self._incidents.by_id(incident_id)
        if incident is None:
            raise IncidentNotFoundError(incident_id)
        return incident

    # --- casos de uso -----------------------------------------------------

    def create(self, actor: User, title: str, description: str = "") -> Incident:
        """12/11/2026 - Krista Colon: declarar un incidente (supervisor o administrador)."""
        self._require_manager(actor, "create_incident")
        title = title.strip()
        if not title:
            raise ValidationError("title cannot be empty", field="title")
        incident = Incident(title=title, description=description.strip(), created_by_id=actor.id)
        return self._incidents.add(incident)

    def list(self, actor: User) -> list[tuple[Incident, int]]:
        """12/11/2026 - Krista Colon: incidentes con su cantidad de tickets (solo personal)."""
        self._require_staff(actor)
        counts = self._incidents.ticket_counts()
        return [(incident, counts.get(incident.id, 0)) for incident in self._incidents.all()]

    def detail(self, actor: User, incident_id: int) -> IncidentDetail:
        """12/11/2026 - Krista Colon: un incidente y sus tickets vinculados (solo personal)."""
        self._require_staff(actor)
        incident = self._require_incident(incident_id)
        return IncidentDetail(incident=incident, tickets=self._incidents.tickets_of(incident_id))

    def link_ticket(self, actor: User, incident_id: int, ticket_id: int) -> IncidentDetail:
        """12/11/2026 - Krista Colon: regla principal de la ficha 07.

        El orden importa: todas las validaciones ocurren ANTES de escribir, de modo
        que un intento rechazado no cambia nada en la base.
        """
        self._require_manager(actor, "link_ticket")
        incident = self._require_incident(incident_id)
        if not incident.is_open:
            raise IncidentNotOpenError(incident_id)

        ticket = self._tickets.by_id(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(ticket_id)
        if TicketStatus(ticket.status) not in LINKABLE_STATUSES:
            raise TicketNotEligibleError(ticket_id, ticket.status)

        current = self._incidents.incident_of_ticket(ticket_id)
        if current is not None:
            raise TicketAlreadyLinkedError(ticket_id, current)

        # Segunda barrera, en la base: si otra peticion lo vinculo entre la lectura y
        # esta escritura, el UPDATE condicionado no afecta ninguna fila.
        if not self._incidents.link_ticket(incident_id, ticket_id):
            raise TicketAlreadyLinkedError(ticket_id, self._incidents.incident_of_ticket(ticket_id))

        return IncidentDetail(incident=incident, tickets=self._incidents.tickets_of(incident_id))
