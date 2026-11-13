"""12/11/2026 - Krista Colon: pruebas del modulo de incidentes masivos (examen final, ficha 07).

Corren contra la base de PRUEBAS aislada (`helpdesk_test`, ver tests/conftest.py),
nunca contra la base habitual `helpdesk`. La fixture `committed_db` recarga el seed
antes y despues de cada prueba, asi que cada una parte de los mismos datos:

Usuarios del seed: 1 administrador | 2 supervisor | 3 y 6 tecnicos | 4 y 5 solicitantes
Tickets del seed:  1 open | 2 in_progress | 3 closed | 4 open | 5 resolved | 6 in_progress

Para comprobar que los datos PERSISTEN, las lecturas de verificacion se hacen con
una sesion NUEVA sobre la base de pruebas, distinta de la que uso la API.

    uv run pytest tests/test_final_incidentes.py -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import create_app
from app.repositories.sqlalchemy import (
    IncidentORM,
    SqlAlchemyIncidentRepository,
    SqlAlchemyTicketRepository,
    TicketORM,
)
from app.services.incidents import IncidentService
from tests.helpers import auth_headers

ADMIN = auth_headers(1)
SUPERVISOR = auth_headers(2)
TECHNICIAN = auth_headers(3)
REQUESTER = auth_headers(4)


@pytest.fixture
def client(committed_db):
    # 12/11/2026 - Krista Colon: misma forma que las pruebas de la semana 14.
    with TestClient(create_app()) as test_client:
        yield test_client


def incident_of(pg_engine, ticket_id: int) -> int | None:
    """12/11/2026 - Krista Colon: lee tickets.incident_id desde una sesion NUEVA."""
    with Session(pg_engine) as fresh:
        return fresh.scalar(select(TicketORM.incident_id).where(TicketORM.id == ticket_id))


def create_incident(client, title: str = "Caida de wifi en Edificio B", headers=SUPERVISOR) -> dict:
    response = client.post(
        "/api/incidents",
        json={"title": title, "description": "Sin conexion en aulas 201 a 210"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- camino feliz -------------------------------------------------------------

def test_supervisor_crea_incidente_y_vincula_un_ticket_abierto(client, pg_engine):
    incident = create_incident(client)

    response = client.post(
        f"/api/incidents/{incident['id']}/tickets",
        json={"ticket_id": 1},
        headers=SUPERVISOR,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert [ticket["id"] for ticket in body["tickets"]] == [1]
    assert body["ticket_count"] == 1
    # Efecto observable y persistente: una sesion nueva ve el vinculo en la base.
    assert incident_of(pg_engine, 1) == incident["id"]


def test_el_incidente_creado_se_lee_desde_otra_sesion(client, pg_engine):
    incident = create_incident(client, title="Impresoras del laboratorio 1 sin red")

    with Session(pg_engine) as fresh:
        row = fresh.get(IncidentORM, incident["id"])

    assert row is not None
    assert row.title == "Impresoras del laboratorio 1 sin red"
    assert row.status == "open"
    assert row.created_by_id == 2


def test_el_detalle_refleja_los_tickets_vinculados(client):
    incident = create_incident(client)
    client.post(f"/api/incidents/{incident['id']}/tickets", json={"ticket_id": 1}, headers=SUPERVISOR)
    client.post(f"/api/incidents/{incident['id']}/tickets", json={"ticket_id": 4}, headers=ADMIN)

    response = client.get(f"/api/incidents/{incident['id']}", headers=TECHNICIAN)

    assert response.status_code == 200
    assert [ticket["id"] for ticket in response.json()["tickets"]] == [1, 4]


# --- prueba enfocada de la ficha 07 ---------------------------------------------

def test_ticket_ya_vinculado_no_entra_a_un_segundo_incidente_y_permanece_en_el_primero(client, pg_engine):
    primero = create_incident(client, title="Caida de wifi en Edificio B")
    segundo = create_incident(client, title="Caida de wifi en Edificio C")
    vinculo = client.post(f"/api/incidents/{primero['id']}/tickets", json={"ticket_id": 1}, headers=SUPERVISOR)
    assert vinculo.status_code == 200

    response = client.post(
        f"/api/incidents/{segundo['id']}/tickets",
        json={"ticket_id": 1},
        headers=SUPERVISOR,
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"] == "ticket_already_linked"
    # Sin mutacion: el ticket sigue en el primero y el segundo no gano ningun ticket.
    assert incident_of(pg_engine, 1) == primero["id"]
    detalle = client.get(f"/api/incidents/{segundo['id']}", headers=SUPERVISOR).json()
    assert detalle["tickets"] == []


# --- rechazos sin cambio de estado ------------------------------------------------

def test_un_tecnico_no_puede_vincular_y_el_ticket_no_cambia(client, pg_engine):
    incident = create_incident(client)

    response = client.post(f"/api/incidents/{incident['id']}/tickets", json={"ticket_id": 1}, headers=TECHNICIAN)

    assert response.status_code == 403
    assert response.json()["error"] == "permission_denied"
    assert incident_of(pg_engine, 1) is None


def test_un_ticket_cerrado_no_se_puede_vincular(client, pg_engine):
    incident = create_incident(client)

    response = client.post(f"/api/incidents/{incident['id']}/tickets", json={"ticket_id": 3}, headers=SUPERVISOR)

    assert response.status_code == 409
    assert response.json()["error"] == "ticket_not_eligible"
    assert incident_of(pg_engine, 3) is None


def test_no_se_vincula_a_un_incidente_resuelto(client, pg_engine):
    incident = create_incident(client)
    with Session(pg_engine) as fresh:
        fresh.get(IncidentORM, incident["id"]).status = "resolved"
        fresh.commit()

    response = client.post(f"/api/incidents/{incident['id']}/tickets", json={"ticket_id": 1}, headers=SUPERVISOR)

    assert response.status_code == 409
    assert response.json()["error"] == "incident_not_open"
    assert incident_of(pg_engine, 1) is None


def test_solo_supervisor_o_administrador_crea_incidentes(client, pg_engine):
    response = client.post("/api/incidents", json={"title": "Prueba de tecnico"}, headers=TECHNICIAN)

    assert response.status_code == 403
    with Session(pg_engine) as fresh:
        assert fresh.scalars(select(IncidentORM)).all() == []


def test_un_solicitante_no_ve_los_incidentes(client):
    create_incident(client)

    assert client.get("/api/incidents", headers=REQUESTER).status_code == 403


def test_entrada_invalida_y_recursos_inexistentes(client):
    incident = create_incident(client)

    assert client.post("/api/incidents", json={"title": "ab"}, headers=SUPERVISOR).status_code == 422
    assert client.post(f"/api/incidents/{incident['id']}/tickets", json={"ticket_id": 0}, headers=SUPERVISOR).status_code == 422
    assert client.post(f"/api/incidents/{incident['id']}/tickets", json={"ticket_id": 999}, headers=SUPERVISOR).status_code == 404
    assert client.post("/api/incidents/999/tickets", json={"ticket_id": 1}, headers=SUPERVISOR).status_code == 404
    assert client.get("/api/incidents/999", headers=SUPERVISOR).status_code == 404


def test_sin_token_la_api_responde_401(client):
    assert client.get("/api/incidents").status_code == 401


# --- servicio y repositorio directamente, en la sesion de prueba --------------------

def test_el_servicio_rechaza_el_segundo_vinculo_sin_tocar_la_base(db):
    from app.domain.errors import TicketAlreadyLinkedError
    from app.repositories.sqlalchemy import SqlAlchemyUserRepository

    service = IncidentService(SqlAlchemyIncidentRepository(db), SqlAlchemyTicketRepository(db))
    supervisor = SqlAlchemyUserRepository(db).by_id(2)
    primero = service.create(supervisor, "Incidente A")
    segundo = service.create(supervisor, "Incidente B")
    service.link_ticket(supervisor, primero.id, 4)

    with pytest.raises(TicketAlreadyLinkedError):
        service.link_ticket(supervisor, segundo.id, 4)

    assert service.detail(supervisor, primero.id).tickets[0].id == 4
    assert service.detail(supervisor, segundo.id).tickets == []
