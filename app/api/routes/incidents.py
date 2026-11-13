"""12/11/2026 - Krista Colon: rutas de incidentes masivos (examen final, ficha 07).

Cada ruta recibe, llama al servicio y responde. Los permisos (supervisor o
administrador para crear y vincular; personal para consultar) y la regla de
vinculacion viven en IncidentService; los errores de dominio los traduce
app/api/errors.py (403, 404, 409, 422) con el formato comun de la API.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentUser, DbSession
from app.models.incidents import Incident
from app.repositories.sqlalchemy import SqlAlchemyIncidentRepository, SqlAlchemyTicketRepository
from app.schemas.incidents import (
    IncidentCreate,
    IncidentDetailOut,
    IncidentOut,
    IncidentTicketOut,
    LinkTicketRequest,
)
from app.services.incidents import IncidentDetail, IncidentService

router = APIRouter(prefix="/incidents", tags=["incidents"])


def get_incident_service(db: DbSession) -> IncidentService:
    """12/11/2026 - Krista Colon: el servicio usa la MISMA sesion de la peticion, asi la
    unidad de trabajo confirma o revierte todo junto al terminar la ruta."""
    return IncidentService(SqlAlchemyIncidentRepository(db), SqlAlchemyTicketRepository(db))


IncidentServiceDep = Annotated[IncidentService, Depends(get_incident_service)]


def _incident_out(incident: Incident, ticket_count: int) -> IncidentOut:
    return IncidentOut(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        status=str(incident.status),
        created_by_id=incident.created_by_id,
        created_at=incident.created_at,
        ticket_count=ticket_count,
    )


def _detail_out(detail: IncidentDetail) -> IncidentDetailOut:
    base = _incident_out(detail.incident, len(detail.tickets))
    return IncidentDetailOut(
        **base.model_dump(),
        tickets=[
            IncidentTicketOut(
                id=ticket.id,
                title=ticket.title,
                status=str(ticket.status),
                priority=ticket.priority,
                requester_id=ticket.requester_id,
            )
            for ticket in detail.tickets
        ],
    )


@router.post("", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def create_incident(body: IncidentCreate, service: IncidentServiceDep, user: CurrentUser):
    """12/11/2026 - Krista Colon: POST /api/incidents (supervisor o administrador)."""
    incident = service.create(user, body.title, body.description)
    return _incident_out(incident, 0)


@router.get("", response_model=list[IncidentOut])
def list_incidents(service: IncidentServiceDep, user: CurrentUser):
    """12/11/2026 - Krista Colon: GET /api/incidents (personal de soporte)."""
    return [_incident_out(incident, count) for incident, count in service.list(user)]


@router.get("/{incident_id}", response_model=IncidentDetailOut)
def get_incident(incident_id: int, service: IncidentServiceDep, user: CurrentUser):
    """12/11/2026 - Krista Colon: GET /api/incidents/{id} con sus tickets (personal de soporte)."""
    return _detail_out(service.detail(user, incident_id))


@router.post("/{incident_id}/tickets", response_model=IncidentDetailOut)
def link_ticket(
    incident_id: int,
    body: LinkTicketRequest,
    service: IncidentServiceDep,
    user: CurrentUser,
):
    """12/11/2026 - Krista Colon: POST /api/incidents/{id}/tickets (supervisor o administrador).

    Regla de la ficha 07: el ticket debe estar abierto, el incidente tambien, y el
    ticket no puede pertenecer ya a otro incidente.
    """
    return _detail_out(service.link_ticket(user, incident_id, body.ticket_id))
