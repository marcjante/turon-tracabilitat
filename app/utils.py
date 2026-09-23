"""Utilidades pequeñas compartidas entre schemas."""

from datetime import datetime, timezone


def to_utc(value: datetime | None) -> datetime | None:
    """SQLModel exige datetimes con timezone (un naive falla al insertar).
    Si el cliente manda uno sin zona horaria, se asume UTC en vez de
    rechazar la petición — más tolerante para un formulario rápido."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
