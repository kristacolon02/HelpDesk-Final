class DomainError(Exception):
    """Base class for expected business errors."""

    code = "domain_error"

    def __init__(self, message: str | None = None, **properties: object) -> None:
        self.properties = properties
        super().__init__(message or self.code)


class ValidationError(DomainError):
    """Raised when business input is invalid."""

    code = "validation_error"

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        **properties: object,
    ) -> None:
        if field is not None:
            properties = {"field": field, **properties}
        super().__init__(message, **properties)


class ConflictError(ValidationError):
    """22/10/2026 - Agregue este error de dominio para que la API no muestre el
    IntegrityError de PostgreSQL: se lanza cuando la base rechaza un dato que
    choca con una fila existente (por ejemplo un email repetido)."""

    code = "conflict"


class NotFoundError(DomainError):
    """Raised when a required entity does not exist."""

    code = "not_found"

    def __init__(self, resource: str, identifier: object) -> None:
        super().__init__(
            f"{resource} {identifier} was not found",
            resource=resource,
            identifier=identifier,
        )


class TicketNotFoundError(NotFoundError):
    """Raised when a ticket does not exist."""

    code = "ticket_not_found"

    def __init__(self, ticket_id: int) -> None:
        DomainError.__init__(
            self,
            f"Ticket {ticket_id} was not found",
            ticket_id=ticket_id,
        )


class UserNotFoundError(NotFoundError):
    """Raised when a user does not exist."""

    code = "user_not_found"

    def __init__(self, user_id: int) -> None:
        DomainError.__init__(
            self,
            f"User {user_id} was not found",
            user_id=user_id,
        )


class AuthenticationError(DomainError):
    """Raised when the caller is not identified (or the identity is unknown)."""

    code = "unauthenticated"


class PermissionDeniedError(DomainError):
    """Raised when an actor is not allowed to perform an action."""

    code = "permission_denied"


class InvalidStatusTransitionError(ValidationError):
    """Raised when a status change violates the ticket workflow."""

    code = "invalid_status_transition"

    def __init__(self, from_status: object, to_status: object) -> None:
        from_value = getattr(from_status, "value", from_status)
        to_value = getattr(to_status, "value", to_status)
        super().__init__(
            f"Cannot transition ticket from {from_value} to {to_value}",
            from_status=str(from_value),
            to_status=str(to_value),
        )


# 12/11/2026 - Krista Colon: errores de dominio del modulo de incidentes (examen final, ficha 07).
class IncidentNotFoundError(NotFoundError):
    """Raised when an incident does not exist."""

    code = "incident_not_found"

    def __init__(self, incident_id: int) -> None:
        DomainError.__init__(
            self,
            f"Incident {incident_id} was not found",
            incident_id=incident_id,
        )


class IncidentNotOpenError(ConflictError):
    """12/11/2026 - Krista Colon: no se vinculan tickets a un incidente ya resuelto."""

    code = "incident_not_open"

    def __init__(self, incident_id: int) -> None:
        super().__init__(
            f"Incident {incident_id} is not open",
            incident_id=incident_id,
        )


class TicketNotEligibleError(ConflictError):
    """12/11/2026 - Krista Colon: solo un ticket abierto o en proceso puede vincularse."""

    code = "ticket_not_eligible"

    def __init__(self, ticket_id: int, status: object) -> None:
        status_value = getattr(status, "value", status)
        super().__init__(
            f"Ticket {ticket_id} is {status_value} and cannot be linked",
            ticket_id=ticket_id,
            status=str(status_value),
        )


class TicketAlreadyLinkedError(ConflictError):
    """12/11/2026 - Krista Colon: un ticket pertenece como maximo a un incidente."""

    code = "ticket_already_linked"

    def __init__(self, ticket_id: int, incident_id: int | None) -> None:
        super().__init__(
            f"Ticket {ticket_id} already belongs to incident {incident_id}",
            ticket_id=ticket_id,
            incident_id=incident_id,
        )
