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
   **Mientras el cálculo se valida contra la realidad, el costo teórico convive con uno real.**
   La OS tiene `costo_real` y `observaciones`, que carga logística a mano cuando lo facturado no
   coincide con lo calculado; la tabla de `/ordenes-servicio` muestra las dos cifras en columnas
   separadas, porque lo que hay que poder ver es el desvío. Van en la OS y no en el costo
   calculado justamente para que un recálculo no se los lleve puestos.
2. **Eventos.** Registrar los eventos de cada ticket y calcular cuánto duró cada uno.
3. **Orden de servicio.** Planificar la OS *antes* de que llegue el camión. Hoy
   `IngestTicketUseCase` crea una OS nueva por ticket; en este paso el ticket tiene que
   poder colgarse de una OS preexistente. La pantalla `/ordenes-servicio` ya deja corregir a
   mano lo que la ingesta no sabe llenar (`fecha_viaje`, `tipo_operacion`, `tipo_camion`, `via`,
   `hombreador`, `facturable`, `destinos`) y disparar el costeo, pero **la OS sigue naciendo del
   ticket**: no hay alta, ni `numero`, ni estado, ni fechas planificadas.
   Lo que sí hay es **baja**: una OS que la ingesta creó mal se da de baja con todo lo que le
   cuelga —tickets, remitos y costo— y eso libera el número de ticket para volver a ingestarlo.
   Los tarifarios no se tocan: son dato maestro de todo el transportista.
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
nginx/            nginx.conf (dev) y nginx.prod.conf. Es lo que hace que todo sea same-origin.
seed/             datos reales para los import_* commands: xlsx de ubicaciones, y los CSV
                  del INDEC 2022 con los polígonos de provincias, departamentos y municipios
scripts/          utilitarios sueltos de datos
run-dev.sh        levanta el stack exportando DOCKER_UID/GID
run-prod.sh       levanta el stack de producción (docker-compose.prod.yml + .env.prod)
generar-tipos.sh  regenera frontend/src/api/schema.d.ts desde el openapi.json
.env              en la raíz, porque compose lo necesita acá para interpolar
.env.example      el molde de los dos: se copia a .env o a .env.prod
```

Los `.sh` de la raíz van con `docker compose`, o sea que se corren **en el host**, no
adentro de un contenedor. `generar-tipos.sh` está explicado en `frontend/CLAUDE.md`: es un
script y no un one-liner porque el `Host` que acepta Django, el Node que corre
`openapi-typescript` y el filesystem que ve el contenedor no coinciden.

## Topología

**Son dos topologías, una por compose**, y comparten la decisión que las define: un solo
puerto expuesto, el 80, con la SPA y la API en el mismo origen.

### Dev — `docker-compose.yml`

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

### Prod — `docker-compose.prod.yml`

**Tres servicios, no cuatro: `web` desaparece.** Una SPA compilada no tiene proceso, son
archivos, así que `frontend/Dockerfile.prod` es multi-stage y **termina en nginx**: esa imagen
*es* el proxy. Se levanta con `./run-prod.sh`.

| Servicio | Imagen / build | Publica | Rol |
|---|---|---|---|
| `db` | `postgis/postgis:17-3.5` | — | Igual que dev, pero **sin publicar el puerto** |
| `api` | build `./backend` con `Dockerfile.prod` | — | gunicorn `core.wsgi:application` |
| `proxy` | build `./frontend` con `Dockerfile.prod` | `80:80` | nginx: sirve el `dist` y los dos juegos de estáticos |

```
/api/static/  → alias al volumen static_data     los estáticos del admin, sin tocar Django
/assets/      → el dist de Vite, immutable 1 año
/api/         → api:8000/api/
/admin/       → api:8000/admin/
/             → try_files $uri /index.html        el fallback de la SPA
```

Cuatro cosas que sostienen esto:

- **`name: tms-fr-prod`** en el compose. Con el mismo `name` que dev, `db_data_gis` sería el
  mismo volumen y prod pisaría la base de desarrollo.
- **`STATIC_ROOT` es `/app/staticfiles`, montado como el volumen `static_data`**, que el proxy
  monta `:ro`. El entrypoint del `api` corre `collectstatic` en cada arranque y el proxy espera
  por el healthcheck del `api`, así que nunca sirve un volumen vacío. La razón de que
  `STATIC_URL` no tenga barra inicial es justamente ésta: Django emite `/api/static/…`, que es
  el `location` que nginx resuelve desde el volumen.
- **El volumen nombrado hereda el ownership del mountpoint de la imagen al crearse**, así que el
  `chown app:app /app/staticfiles` del `Dockerfile.prod` es lo único que hace que
  `collectstatic` pueda escribir. Es el mismo mecanismo que el `a+rwX` de `node_modules`.
- **Ni `user:` ni bind mount del código.** El uid del host existía para los bind mounts; en prod
  no hay ninguno y los contenedores corren el usuario `app` de su propia imagen.

El deploy no lleva TLS: nginx escucha en el 80 y la terminación va delante o se agrega después.
Mientras sea HTTP puro, `SESSION_COOKIE_SECURE` **tiene que quedar en `False`** — en `True` el
browser nunca guarda la `sessionid` y el login falla sin un solo error. `check --deploy` avisa
de HSTS, SSL redirect y esa cookie: son los tres esperados sin TLS.

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
- **`.env.example` es el molde de los dos entornos y no está validado por nada.** Agregar una
  variable a `settings.py` y no documentarla ahí no rompe nada: se descubre cuando algo se
  queda en su default en el servidor.
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
- **El deploy de producción es a mano y no hay CI.** `./run-prod.sh` hace
  `up -d --build` contra el host donde se corre: no hay registry, ni tags de imagen, ni
  pipeline que buildee y testee antes. Un rollback es volver el checkout y rebuildear.
- **No hay TLS.** nginx escucha en el 80 y listo. Agregarlo es cert + `listen 443 ssl` +
  redirect, y del lado de Django `SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE=True` y los
  `SECURE_*` que hoy `check --deploy` reclama. El proxy ya reenvía `X-Forwarded-Proto $scheme`
  para que ese día no haya que tocar nada más.
- **El entrypoint del `api` migra en cada arranque.** Es cómodo con un contenedor y es una
  carrera con dos: `migrate` y `sync_permisos` no están hechos para correr en paralelo. Escalar
  el `api` pide sacarlos del entrypoint y hacerlos un paso de deploy aparte.
- **`seed/` está gitignoreado**, así que los xlsx de ubicaciones y los CSV del INDEC hay que
  copiarlos al servidor a mano antes de correr los `import_*`.
