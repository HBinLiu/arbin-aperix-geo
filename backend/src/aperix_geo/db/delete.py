"""ORM soft delete: session.delete() sets deleted=true; reads exclude deleted rows."""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from aperix_geo.db.base import Base

INCLUDE_DELETED = "include_deleted"


class SoftDeleteSession(Session):
    def delete(self, instance: object) -> None:  # noqa: A003
        if isinstance(instance, Base):
            instance.soft_delete()
            return
        super().delete(instance)


def _apply_soft_delete_criteria(execute_state) -> None:
    if not execute_state.is_select:
        return
    opts = execute_state.execution_options
    if opts.get(INCLUDE_DELETED):
        return
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            Base,
            lambda cls: cls.deleted.is_(False),
            include_aliases=True,
        )
    )


event.listens_for(SoftDeleteSession, "do_orm_execute")(_apply_soft_delete_criteria)
