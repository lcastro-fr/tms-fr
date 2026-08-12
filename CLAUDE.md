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
   Un ticket se crea cuando el camión llega. Los precios contra los que se costea se cargan
   desde `/tarifarios`, la única pantalla con alta propia: un tarifario se guarda entero
   —vigencia, tarifas de flete y conceptos adicionales— en un solo formulario.
   Las **zonas** contra las que se tarifa ya no se dibujan sólo a mano: en `/zonas` se pueden
   **componer marcando provincias y departamentos** del INDEC, y el resultado queda editable en el
   mapa. Es lo que hace practicable una zona como "toda la provincia de Buenos Aires", que son
   22.658 vértices y 81 polígonos por las islas del Delta.
   **Las zonas se solapan, y eso ya no traba el costeo:** cada una guarda su superficie y cuando
   dos cubren los destinos se tarifa contra la más chica, o sea la más específica. `/zonas` muestra
   esa superficie porque es lo que hace predecible el resultado.
   **Hasta dónde se factura el viaje ya no se deduce de los remitos:** la OS tiene sus propios
   destinos, que el usuario carga en `/ordenes-servicio` y el costeo usa tal cual. Es lo que
   permite facturar hasta un puerto, un aeropuerto o un **expreso** cuando el remito dice otra
   cosa. Sin destinos cargados se siguen derivando de los remitos, que es el caso mayoritario.
   Y como esos destinos SAP no los manda, `/ubicaciones` tiene **alta propia** con
   geolocalización asistida: el usuario completa la dirección, pide la coordenada al geocoder o la
   marca en el mapa, y guarda.
2. **Eventos.** Registrar los eventos de cada ticket y calcular cuánto duró cada uno.
3. **Orden de servicio.** Planificar la OS *antes* de que llegue el camión. Hoy
   `IngestTicketUseCase` crea una OS nueva por ticket; en este paso el ticket tiene que
   poder colgarse de una OS preexistente. La pantalla `/ordenes-servicio` ya deja corregir a
   mano lo que la ingesta no sabe llenar (`fecha_viaje`, `tipo_operacion`, `tipo_camion`, `via`,
   `hombreador`, `facturable`, `destinos`) y disparar el costeo, pero **la OS sigue naciendo del
   ticket**: no hay alta, ni `numero`, ni estado, ni fechas planificadas.
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
backend/          Django. Ver backend/CLAUDE.md
frontend/         SPA React. Ver frontend/CLAUDE.md
nginx/            nginx.conf del proxy. Es lo que hace que todo sea same-origin.
seed/             datos reales para los import_* commands: xlsx de ubicaciones, y los CSV
                  del INDEC 2022 con los polígonos de provincias, departamentos y municipios
scripts/          utilitarios sueltos de datos
run-dev.sh        levanta el stack exportando DOCKER_UID/GID
generar-tipos.sh  regenera frontend/src/api/schema.d.ts desde el openapi.json
.env              en la raíz, porque compose lo necesita acá para interpolar
```

Los dos `.sh` de la raíz van con `docker compose`, o sea que se corren **en el host**, no
adentro de un contenedor. `generar-tipos.sh` está explicado en `frontend/CLAUDE.md`: es un
script y no un one-liner porque el `Host` que acepta Django, el Node que corre
`openapi-typescript` y el filesystem que ve el contenedor no coinciden.

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
- Las de sesión — `CSRF_TRUSTED_ORIGINS`, `SESSION_COOKIE_AGE`, `SESSION_COOKIE_SECURE` —
  **sí** están en la lista de compose. Agregar una variable nueva de auth y olvidarse de
  `docker-compose.yml` la deja en su default adentro del contenedor, en silencio.

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
- **401 y 403 no son lo mismo.** El 401 es sesión ausente o muerta y el frontend desloguea;
  el 403 es un usuario logueado sin permiso, y la UI muestra el error sin cerrar la sesión.
  Confundirlos echa al usuario cada vez que toca un botón que no le corresponde.
- **Nada de fallas silenciosas.** Si una operación descarta datos, eso viaja en el DTO de
  salida y se le muestra al usuario. No alcanza con no romper.
- **La misma dirección única de dependencias en las dos capas:**
  `tracking → logistica → transportista`, y todos → `catalog`. El frontend espeja esa
  dirección entre sus `features/`.

## Pendientes conocidos

Los de cada capa están en su documento. Estos cruzan las dos:

- **No hay API de gestión de usuarios ni roles.** El alta de usuarios, la creación de roles
  y la asignación se hacen 100% desde el admin de Django. La SPA sólo lee sus permisos.
- **Los datos maestros del tarifario también son del admin.** Transportistas y
  `ConceptoAdicional` se leen por API para poblar el formulario de tarifario, pero darlos de
  alta sigue siendo un paso previo manual en el admin.
- **El catálogo de permisos crece con el código.** `shared/permisos.py` es la fuente de
  verdad, así que agregar un permiso es un cambio de código más una migración (los `choices` se
  serializan) más `manage.py sync_permisos`, no una fila cargada a mano. Y después hay que
  **asignarlo a un rol en el admin**: un permiso nuevo no lo tiene nadie, salvo los superusers,
  que reciben el enum completo sin mirar roles.
- **`backend/seed/` reaparece como `root:root`.** Es el punto de montaje de
  `./seed:/app/seed:ro`, un mount anidado dentro del bind mount de `/app`, y Docker crea
  ese directorio como root sin importar el `user:`. Queda siempre tapado por el mount, así
  que es cosmético.
- **El Node del host puede ser demasiado viejo para el frontend.** Vite 8 pide
  `^20.19 || >=22.12`. El contenedor `web` usa `node:24-slim` y cumple, pero si el host
  tiene menos que eso, `pnpm dev/build/test` sólo corren adentro del contenedor.
- **No hay `.env.example`**, aunque el arranque lo asumía (`cp .env.example .env`).
- **La cobertura es parcial y desigual.** El backend tiene auth/RBAC (`users/tests/`), los
  contratos de catalog, incluida la división política (`catalog/tests/`), la resolución de
  destinos, el costeo —incluido el desempate entre zonas solapadas— y la API de OS
  (`logistica/tests/`), la API de tarifarios (`transportista/tests/`) y la geolocalización de la
  ingesta (`tracking/tests/`); el frontend tiene las conversiones geo, el cableado de los dos
  mapas, los helpers de fecha, dinero y superficie (`lib/`), el mapeo de errores de campo (`api/`)
  y la búsqueda global de las tablas (`components/`).
  Sin cobertura: `shared/models.py` —el borrado lógico, el código más delicado del repo—, y
  **no hay MSW**, así que en el frontend no se
  pueden testear estados de carga ni error del camino real de datos.
- **No hay historia de producción.** El `Dockerfile` del frontend es single-stage de dev
  (`CMD pnpm dev`) y el backend no tiene `STATIC_ROOT` ni `collectstatic`. Todo el setup
  actual asume dev.
