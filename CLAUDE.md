# TMS-FR

TMS (Transport Management System) para una operación de fletes en Argentina.

Este documento es el general del repo: alcance, topología y las convenciones que cruzan
las dos capas. La arquitectura de cada capa vive en su propio documento:

- **`backend/CLAUDE.md`** — Django 6 + PostGIS. Capas, reglas duras, excepciones, borrado
  lógico, la API.
- **`frontend/CLAUDE.md`** — React 19 + Vite + Mantine + TanStack. Features, cliente
  HTTP, data fetching, tablas.

## Alcance

Cuatro pasos, en orden. No adelantarse a los siguientes.

1. **Ingesta y costo.** Traer tickets ya conocidos desde SAP y calcular su costo.
   Un ticket se crea cuando el camión llega.
2. **Eventos.** Registrar los eventos de cada ticket y calcular cuánto duró cada uno.
3. **Orden de servicio.** Planificar la OS *antes* de que llegue el camión. Hoy
   `IngestTicketUseCase` crea una OS nueva por ticket; en este paso el ticket tiene que
   poder colgarse de una OS preexistente.
4. **Ruteo.** Optimización logística con OpenRouteService (`lat`/`lng` ya están en
   `Ubicacion`).

SAP se **consulta por schedule**, no nos hace push. La ingesta programada va a ser un
management command (**todavía no existe**: hoy la única forma de dispararla es
`POST /api/v1/tickets/ingest`, pensado para probar a mano con Postman). Va con header
`X-API-Key` (`INGEST_API_KEY`), y sin la variable seteada rechaza todo.

**El frontend va detrás del backend, no delante.** Sólo se construyen pantallas para
endpoints que existen; si falta el endpoint, el trabajo es en `backend/`.

## Layout

```
backend/     Django. Ver backend/CLAUDE.md
frontend/    SPA React. Ver frontend/CLAUDE.md
nginx/       nginx.conf del proxy. Es lo que hace que todo sea same-origin.
seed/        xlsx de datos reales para los import_* commands
.env         en la raíz, porque compose lo necesita acá para interpolar
```

## Topología

Cuatro servicios en compose, y **un solo puerto expuesto: el 80**.

| Servicio | Imagen / build | Publica | Rol |
|---|---|---|---|
| `db` | `postgis/postgis:17-3.5` | `${APP_DB_PORT}:5432` | Postgres 17 + PostGIS 3.5 |
| `api` | build `./backend` | — | Django. Sólo alcanzable por el proxy. |
| `web` | build `./frontend` | — | Vite dev server en `:5173` |
| `proxy` | `nginx:latest` | `80:80` | Ruteo same-origin |

El proxy resuelve todo en `http://localhost`:

```
/         → web:5173          la SPA
/api/     → api:8000/api/     la API (y /api/static/, ver abajo)
/admin/   → api:8000/admin/   el admin de Django
```

**`http://localhost:8000` ya no existe** — compose dejó de publicar ese puerto. Que la SPA
y la API compartan origen es la decisión que evita CORS: no hay `django-cors-headers` en
el proyecto y no hace falta.

`STATIC_URL` es `api/static/` y no `static/`, a propósito: así los estáticos del admin
caen dentro del `location /api/` del proxy y se sirven sin agregar una regla más.

## Los contenedores corren con el uid del host

`api` y `web` van con `user: "${DOCKER_UID}:${DOCKER_GID}"`. Sin eso, todo lo que el
contenedor escribe en los bind mounts (`__pycache__`, `.ruff_cache`, `.mypy_cache`,
`node_modules`, migraciones nuevas) queda `root:root` en el repo y después hace falta
`sudo` para borrarlo. Las dos variables están en el `.env`, y `run-dev.sh` además las
exporta desde `id -u`/`id -g`.

Que el proceso corra con otro uid obliga a que **nada que el contenedor necesite escribir
viva en una ruta que armó el build como root**. De ahí tres decisiones en los Dockerfile:

- El venv del backend va a `/opt/venv` (`UV_PROJECT_ENVIRONMENT`), fuera de `/app`, y el
  cache de uv del build se borra para que el uid del host recree el suyo. `UV_NO_SYNC=1`
  evita que `uv run` intente mutar un venv que no le pertenece.
- El `node_modules` del frontend es un volumen anónimo, y queda `a+rwX` en la imagen
  porque el volumen hereda esos permisos al crearse.
- El `web` arranca `node_modules/.bin/vite --host` en vez de `pnpm dev`: pnpm revalida
  dependencias en cada arranque, y como exige que su store esté en el **mismo filesystem
  que el proyecto**, con `/app` bind-mounteado cae a `/app/.pnpm-store` e intenta
  reinstalar. Las dependencias las instala el build; agregar una pide
  `docker compose build web`.

Si venís de antes de este cambio, los volúmenes anónimos viejos conservan su ownership
root: hay que recrearlos una vez con
`docker compose up -d --force-recreate --renew-anon-volumes`.

## Variables de entorno

El `.env` vive en la raíz. `AutoConfig` de decouple lo busca desde `REPO_ROOT`.

- `APP_DB_HOST`/`APP_DB_PORT` del `.env` son los valores **host-side**; compose los
  sobreescribe con `db:5432` para el contenedor.
- **Dentro del contenedor decouple no encuentra el `.env`.** `BASE_DIR` es `/app`, así que
  `REPO_ROOT` es `/`, y el archivo no está montado ahí. Decouple cae a `os.environ`, o
  sea que **sólo llegan las variables que compose pasa explícitamente**. `TZ_OPERACION`,
  `CONN_MAX_AGE` y `SQL_LOG_LEVEL` no están en esa lista y se quedan en su default.
  Host-side (`uv run manage.py`) sí se lee el `.env` completo.

## Dev loop

```bash
docker compose up -d        # db + api + web + proxy → http://localhost
docker compose logs -f api
```

Para trabajar sobre una sola capa, cada documento tiene su loop:
`backend/CLAUDE.md` (uv, pytest, ruff, mypy, migraciones) y `frontend/CLAUDE.md`
(pnpm, generación de tipos).

Levantar sólo la base y correr el backend en el host es lo más rápido para iterar en
Django: `docker compose up -d db` y después el loop de `backend/CLAUDE.md`. Ojo que eso
**necesita GDAL/GEOS instaladas en el host** — sin ellas ni `manage.py check` arranca.

## Convenciones que cruzan las dos capas

- **Nada de comentarios explicativos largos.** Código autoexplicativo y nombres claros.
  Un comentario de una línea sólo si hay una restricción no obvia que avisar. El
  razonamiento va en estos documentos, en el plan o en el commit.
- **Vocabulario de dominio en español, técnico en inglés.** `Ubicacion`, `Remito`,
  `OrdenServicio`, `numero`, `fecha_ingreso` de un lado; `BaseModel`, `*Service`,
  `*Error`, `queryOptions`, `active` del otro.
- **Sufijos de dirección en los DTOs y sus tipos espejo:** `...In` (entrada), `...Out`
  (salida), `...Filters` (query params).
- **Fechas aware de punta a punta.** Almacenamiento en UTC; la conversión a
  `America/Argentina/Buenos_Aires` (`TZ_OPERACION`) pasa sólo en el borde de
  presentación. El backend rechaza un ISO naive con 422.
- **`Decimal` viaja como string JSON** (`"185000.00"`). El frontend lo trata como string
  y nunca hace aritmética de pesos en float.
- **Un solo envelope de error:** `{"error": {"code", "message", "detail"}}`. Se ramifica
  por `code`, nunca por status — el 422 es dos cosas distintas (`business_rule` vs
  `payload_invalid`).
- **Nada de fallas silenciosas.** Si una operación descarta datos, eso viaja en el DTO de
  salida y se le muestra al usuario. No alcanza con no romper.
- **La misma dirección única de dependencias en las dos capas:**
  `tracking → logistica → transportista`, y todos → `catalog`. El frontend espeja esa
  dirección entre sus `features/`.

## Pendientes conocidos

Los de cada capa están en su documento. Estos cruzan las dos:

- **No hay auth usable desde el browser.** La API sólo acepta `X-API-Key`, que es el
  secreto compartido con la integración SAP y autoriza escrituras: mandarlo desde la SPA
  lo publica en el bundle. La decisión tomada es sesión Django + CSRF
  (`django_auth` de ninja, más `POST /auth/login`, `/auth/logout`, `GET /auth/me` y
  `CSRF_TRUSTED_ORIGINS`), y no está implementada.
- **`nginx.conf` no manda los headers de upgrade a WebSocket** en `location /`, así que
  el HMR de Vite no funciona a través del puerto 80. Falta `proxy_http_version 1.1` más
  `Upgrade` / `Connection`.
- **`backend/seed/` reaparece como `root:root`.** Es el punto de montaje de
  `./seed:/app/seed:ro`, un mount anidado dentro del bind mount de `/app`, y Docker crea
  ese directorio como root sin importar el `user:`. Queda siempre tapado por el mount, así
  que es cosmético.
- **El Node del host puede ser demasiado viejo para el frontend.** Vite 8 pide
  `^20.19 || >=22.12`. El contenedor `web` usa `node:24-slim` y cumple, pero si el host
  tiene menos que eso, `pnpm dev/build/test` sólo corren adentro del contenedor.
- **No hay `.env.example`**, aunque el arranque lo asumía (`cp .env.example .env`).
- **Cero tests en todo el repo.** Ni backend ni frontend: no hay `conftest.py`, ningún
  `test_*.py` y ningún runner en el frontend.
- **No hay historia de producción.** El `Dockerfile` del frontend es single-stage de dev
  (`CMD pnpm dev`) y el backend no tiene `STATIC_ROOT` ni `collectstatic`. Todo el setup
  actual asume dev.
