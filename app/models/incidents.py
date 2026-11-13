"""12/11/2026 - Krista Colon: entidad Incident (examen final, ficha 07).

Un incidente masivo agrupa los tickets que reportan la misma falla (por ejemplo,
"Caida de wifi en el Edificio B"). Cada ticket pertenece como maximo a un
incidente: la relacion vive en tickets.incident_id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.clock import now


class IncidentStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


@dataclass
class Incident:
    # None hasta que el repositorio guarda el objeto: la base asigna la llave.
    id: int | None = field(default=None, kw_only=True)
    title: str
    created_by_id: int
    description: str = ""
    status: IncidentStatus = IncidentStatus.OPEN
    created_at: datetime = field(default_factory=now)

    @property
    def is_open(self) -> bool:
        return IncidentStatus(self.status) is IncidentStatus.OPEN
