"""Explicit migrations only; credentials are never stored in Alembic config."""

import os

from alembic import context
from issuedigest_storage import (
    auth_schema,  # noqa: F401
    create_storage_engine,
    policy_collection_schema,  # noqa: F401
    policy_intake_schema,  # noqa: F401
    public_briefing_schema,  # noqa: F401
    research_schema,  # noqa: F401
    search_schema,  # noqa: F401
)
from issuedigest_storage.schema import metadata

url = context.config.attributes.get("database_url") or os.environ.get("ISSUEDIGEST_DATABASE_URL")
if not url:
    raise ValueError("Set ISSUEDIGEST_DATABASE_URL explicitly for migrations")
if context.is_offline_mode():
    raise ValueError("Storage migrations require a verified PostgreSQL connection")
engine = create_storage_engine(url)
try:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()
finally:
    engine.dispose()
