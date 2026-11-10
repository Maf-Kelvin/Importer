001_initial_migration.py.txt is the ORIGINAL migration. It created only 6 tables and had no tenant_id
columns or organizations table, so it did not match the models (and used FLOAT for money).
It was replaced by alembic/versions/001_baseline.py. Kept only for reference; safe to delete.
