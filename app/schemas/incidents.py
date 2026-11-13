"""12/11/2026 - Krista Colon: esquemas (Pydantic) de incidentes (examen final, ficha 07).

El cliente solo envia titulo y descripcion al crear, y el numero de ticket al
vincular. El estado, quien lo creo y las fechas los decide el servidor.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=2000)


class LinkTicketRequest(BaseModel):
    # 12/11/2026 - Krista Colon: el numero de ticket que se quiere vincular.
    ticket_id: int = Field(ge=1)


class IncidentOut(BaseModel):
    id: int
    title: str
    description: str
    status: str
    created_by_id: int
    created_at: datetime
    ticket_count: int = 0


class IncidentTicketOut(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    requester_id: int


class IncidentDetailOut(IncidentOut):
    tickets: list[IncidentTicketOut] = Field(default_factory=list)
