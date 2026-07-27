# Grocery Backend

Modular FastAPI foundation for a grocery commerce and delivery application.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for Swagger UI or call `GET /api/v1/health`.

## PostgreSQL and pgAdmin

```powershell
docker compose up -d postgres pgadmin
alembic upgrade head
uvicorn app.main:app --reload
```

- Database: `grocery`
- PostgreSQL user: `postgres`
- PostgreSQL password: `12345`
- pgAdmin: `http://localhost:5050`
- pgAdmin login: `admin@grocery.local` / `12345`

When registering PostgreSQL inside pgAdmin, use host `postgres` for Docker pgAdmin,
or `localhost` for a desktop pgAdmin installation.

Each folder under `app/modules` owns one business capability. Keep its models, schemas,
repository, service, and router together; only place reusable code under `app/shared`.

## Create an admin user

```powershell
python scripts/create_admin.py --name "Admin" --email "admin@example.com"
```

## Clear application data

```sql
DO $$
DECLARE
    table_list text;
BEGIN
    SELECT string_agg(format('%I.%I', schemaname, tablename), ', ')
    INTO table_list
    FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename <> 'alembic_version';

    IF table_list IS NOT NULL THEN
        EXECUTE 'TRUNCATE TABLE ' || table_list || ' RESTART IDENTITY CASCADE';
    END IF;
END $$;
```
