# Backend

API e regras de negócio do Jusante, em Python com Django (GeoDjango) sobre PostgreSQL + PostGIS.

## Organização

| App | Conteúdo |
| --- | --- |
| `nucleo` | Município, usuário (com perfis: atendente, encarregado, equipe de campo, gestor) e equipe |
| `servicos` | Ordens de Serviço: tipos, solicitante, OS, histórico (eventos), fotos, peças e observações de rede |

**Regra central:** o status de uma OS só muda pelas funções de `servicos/fluxo.py`, que validam a
transição, conferem o perfil de quem age e registram um evento imutável no histórico. Veja o
ciclo de vida em [`docs/mvp-ordens-de-servico.md`](../docs/mvp-ordens-de-servico.md).

## Rodando localmente

Requisitos: Python 3.12+, PostgreSQL com PostGIS e GDAL instalados.
O jeito mais simples é usar o Docker Compose em [`infra/`](../infra/).

Sem Docker:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install "django>=5.2,<5.3" "psycopg[binary]>=3.2"
export JUSANTE_DEBUG=1 POSTGRES_USER=... POSTGRES_PASSWORD=... POSTGRES_HOST=localhost
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Testes

```bash
python manage.py test
```
