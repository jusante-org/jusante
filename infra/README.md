# Infraestrutura

Sobe o Jusante com Docker Compose: PostgreSQL + PostGIS, MinIO (fotos) e o backend.

## Primeiro uso

```bash
cd infra
cp .env.exemplo .env          # edite as senhas
docker compose up -d --build
docker compose exec backend python manage.py createsuperuser
```

Painel administrativo: http://localhost:8000/admin
Console do MinIO: http://localhost:9001

## Cadastrar o primeiro município

1. No painel administrativo, cadastre o município (nome, UF, código IBGE).
2. Crie os tipos de OS iniciais:

```bash
docker compose exec backend python manage.py criar_tipos_padrao <codigo_ibge>
```

3. Cadastre usuários (marcando os perfis) e equipes.
