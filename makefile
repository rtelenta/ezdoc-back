dev:
	poetry run fastapi dev

db-migrate:
	poetry run alembic revision --autogenerate -m "$(m)"

db-upgrade:
	poetry run alembic upgrade head