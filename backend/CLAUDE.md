# TMS-FR — Backend

API interna del TMS. El alcance por pasos, la topología y las convenciones que cruzan las
dos capas viven en `../CLAUDE.md`; **leer ese primero.**

Django 6.0.7 + django-ninja 1.6.2 + pydantic 2.13.4 sobre Postgres 17 / PostGIS 3.5
(`django.contrib.gis`, backend `postgis`). Python 3.13, dependencias con `uv`.

## Arquitectura

```
models/      Definición de datos. Sin lógica de negocio.
services/    Único lugar con acceso al ORM. Clases con @staticmethod.
use_cases/   Orquestan services. Dueños de la transacción. Reciben DTO, devuelven DTO.
dtos/        pydantic BaseModel. El contrato con el mundo exterior.
api.py       Adaptadores HTTP de 3 líneas. Lo único que importa ninja.
enums.py     StrEnum + su lista *_CHOICES derivada.
```

Dependencias en una sola dirección: `api → use_cases → services → models`.
Entre apps: `tracking → logistica → transportista`, y todos → `catalog`. Nunca al revés.

### Las apps

| App | Modelos | API | Notas |
|---|---|---|---|
| `catalog` | `Ubicacion`, `Zona` | zonas (CRUD) | Datos maestros y geo. Todos dependen de acá. |
| `transportista` | `Transportista`, `Tarifario`, `TarifaFlete`, `ConceptoAdicional`, `TarifaConceptoAdicional` | — | Tarifarios con vigencia. Sin `use_cases/`. |
| `logistica` | `OrdenServicio`, `CostoOrdenServicio` | — | Sin `use_cases/`: el de costo vive en `tracking`. |
| `tracking` | `Ticket`, `Remito`, `RemitoDestino` | ingesta, costo de OS | La punta de entrada. |
| `users` | `User` (login por email, `username = None`), `Permiso`, `Rol`, `UsuarioRol`, `RolPermiso` | auth (login/logout/me/csrf) | `AUTH_USER_MODEL` y el RBAC. La gestión de roles es sólo por admin. |

`shared/` **no es una app**: es un paquete de soporte (`BaseModel` abstracto,
`exceptions.py`, `dtos.py`, `xlsx.py`). `routing/` es un directorio vacío reservado para el
paso 4 y no está en `INSTALLED_APPS`.

`CalcularCostoOrdenServicioUseCase` está en `tracking/use_cases/` y devuelve un DTO de
`logistica`. Es legal — la dirección `tracking → logistica` lo permite — pero conviene
saberlo antes de buscarlo en `logistica/`.

### Reglas duras

- **El ORM vive solo en `services/`.** Ni use cases ni views hacen queries. La única
  excepción tolerada es leer un `.id` ya cargado.
- **Todas las vistas son sincrónicas.** Nada de `async def`. `transaction.Atomic` sólo
  implementa `__enter__`/`__exit__`: puesto sobre un `async def`, **commitea antes de
  que corra el cuerpo**, sin error ni warning. El ORM async de Django es un shim
  `sync_to_async` y las transacciones no funcionan en modo async. Corremos WSGI a
  propósito; `core/asgi.py` queda como hedge para SSE/websockets.
- **`import ninja` sólo en `core/api*.py`, `core/auth.py` y `<app>/api.py`.** En ningún
  otro lugar. Los DTOs son `pydantic.BaseModel`, nunca `ninja.Schema`. Services y use
  cases nunca levantan `ninja.errors.HttpError`. Esto es lo que hace que salir de ninja
  sea reescribir una capa fina y no el proyecto.
- **Las transacciones son de los use cases.** Los services no abren `atomic()`, salvo
  para envolver su propia escritura en un savepoint.
- **Sólo se puede `catch`-and-`continue` dentro de un `@transaction.atomic` si la
  operación que falla estaba envuelta en su propio `atomic()` anidado.** Si no, el
  bloque queda envenenado y toda query posterior tira `TransactionManagementError`.
- **Los use cases devuelven un DTO**, nunca un modelo ni un primitivo. El use case elige
  el DTO; el `from_model` del DTO hace el mapeo.
- **Nada de fallas silenciosas.** Si una ingesta descarta datos, eso va en el DTO de
  salida (`TicketIngestOut.remitos_omitidos`), no en un `logger.warning` y listo.

## La API hoy

Montada en `api/v1/` (`core/urls.py`), armada en `core/api.py`. Son **diez operaciones**:

| Método | Path | Auth | Entrada | Salida |
|---|---|---|---|---|
| GET | `/api/v1/auth/csrf` | — | — | 200 `CsrfOut` |
| POST | `/api/v1/auth/login` | — | `LoginIn` | 200 `SesionOut` |
| POST | `/api/v1/auth/logout` | sesión | — | 204 |
| GET | `/api/v1/auth/me` | sesión | — | 200 `SesionOut` |
| POST | `/api/v1/tickets/ingest` | `X-API-Key` | `TicketIngestIn` | 201 `TicketIngestOut` |
| POST | `/api/v1/ordenes-servicio/{id}/costo` | `X-API-Key` | — | 200 `CostoOrdenServicioOut` |
| GET | `/api/v1/zonas/` | `zonas.ver` | — | 200 `list[ZonaOut]` |
| POST | `/api/v1/zonas/` | `zonas.crear` | `ZonaIn` | 201 `ZonaOut` |
| GET | `/api/v1/zonas/{id}` | `zonas.ver` | — | 200 `ZonaOut` |
| PUT | `/api/v1/zonas/{id}` | `zonas.editar` | `ZonaIn` | 200 `ZonaOut` |

Todas declaran `**ERRORS` (400/401/403/404/409/422/500 → `ErrorOut`). **Zonas ya no acepta
`X-API-Key`**: es browser-only. La `X-API-Key` quedó exclusivamente para la ingesta y el
costo de OS, que son máquina-a-máquina. No hay DELETE, no hay `/health`, no hay paginación
y **no hay ningún DTO `...Filters` todavía**: `GET /zonas/` devuelve el array completo sin
envelope.

La barra final de `/zonas/` es obligatoria: con `APPEND_SLASH` un GET sin barra redirige
301 y un POST sin barra falla.

Docs en `/api/v1/docs`; el schema en `/api/v1/openapi.json` se importa directo en Postman
y es la fuente de los tipos del frontend.

### Formato de salida

ninja hace `model_dump()` en modo python y serializa con `NinjaJSONEncoder`
(`DjangoJSONEncoder`). Dos consecuencias que el frontend ya asume:

- **`Decimal` sale como string JSON** (`"185000.00"`), no como número.
- Los datetimes salen en ISO 8601 con `+00:00` reescrito a `Z`.

Y un DTO tiene una trampa: **`TicketIngestOut.completo` no viaja en el JSON.** Es un
`@property` de Python, no un `@computed_field` de pydantic.

### Auth

`core/auth.py` tiene dos clases:

- `IngestApiKeyAuth(APIKeyHeader)`, `param_name = "X-API-Key"`, comparada con
  `settings.INGEST_API_KEY` vía `hmac.compare_digest`. Sin la variable seteada devuelve
  401. Es machine-to-machine y hoy sólo la usan la ingesta y el costo de OS.
- `SessionAuth(ninja.security.SessionAuth)`, que además recibe los permisos que la
  operación exige: `auth=SessionAuth(PermisoCodigo.ZONAS_CREAR)`.

**La autorización vive en la clase de auth, no en un decorador sobre la view.** Se intentó
con decorador y no funciona: `functools.wraps` no puede copiar el `__globals__`, y ninja
resuelve las anotaciones (`payload: ZonaIn`, que con `from __future__ import annotations`
es un string) contra los globals de la función que recibe. Rompe toda operación con body.

La regla que hace que esto sea correcto: **devolver `None` da 401, levantar `ForbiddenError`
da 403.** `Operation._run_authentication` envuelve el callback en `try/except` y lo rutea
por `api.on_exception`, así que la excepción llega a nuestros handlers. La diferencia
importa: el frontend trata el 401 como sesión muerta y desloguea, así que un usuario
logueado sin permiso **tiene que ver 403**.

### Sesión y CSRF

`CSRF_USE_SESSIONS = True`: el secreto de CSRF vive dentro de la sesión y **no existe la
cookie `csrftoken`**. El browser guarda una sola cookie, `sessionid`, con `HttpOnly`. El
token viaja en el body (`SesionOut.csrf_token`) y la SPA lo manda en `X-CSRFToken`.

ninja marca cada vista generada como `csrf_exempt` a nivel del middleware de Django, y el
chequeo real vive **dentro de la clase de auth** — `APIKeyCookie.__init__(csrf=True)`, del
que `SessionAuth` hereda. No es un flag de `NinjaAPI` (ese kwarg no existe en 1.6.2). Los
métodos seguros lo saltean, así que un `GET /auth/me` no pide el header.

`POST /auth/login` va con `auth=None`, o sea que **ninja no chequea nada**: el chequeo se
agrega a mano con `check_csrf` de `ninja.utils`. Sin esa línea el login queda expuesto a
login-CSRF. Por eso existe `GET /auth/csrf`: entrega el token del usuario anónimo, que es
el único que no puede sacarlo de `SesionOut`.

`login()` de Django llama a `rotate_token()`, así que el token del bootstrap muere en ese
mismo request. Por eso `/auth/login` devuelve el nuevo en su respuesta.

### RBAC

`shared/permisos.py` define `PermisoCodigo(StrEnum)`, que es **la fuente de verdad** del
catálogo. Vive en `shared/` y no en `users/` porque ponerlo allá obligaría a `catalog` a
importar `users`. `sync_permisos` materializa una fila por miembro y da de baja lógica las
que ya no están en el enum.

Las tablas de relación son **propias, no las automáticas de Django**: `UsuarioRol` y
`RolPermiso` heredan de `BaseModel`. La intermedia que genera Django no tiene columna
`active`, así que `_apply_soft_delete` la saltea y dar de baja un `Rol` dejaría vivas sus
asignaciones. Con `through=` se conservan igual los accesores (`rol.permisos.all()`), y
como efecto el admin pierde `filter_horizontal` y usa inlines.

`PermisoService.codigos_de_usuario` resuelve los permisos de un usuario en una query. Lleva
un `active=True` explícito **por cada salto del join**: el manager por default sólo filtra
el modelo raíz, no los que atraviesa. Y filtra el resultado contra el enum, porque una fila
con un código retirado haría fallar la validación de `SesionOut` con un 500.

`AutenticacionService` es el único service que recibe el `HttpRequest`. Es a propósito:
`login()`/`logout()` de Django lo exigen y son escrituras de sesión, o sea ORM, que por la
regla dura va en `services/`.

### Excepciones

`shared/exceptions.py` define `DomainError` y sus cuatro subtipos semánticos:
`ForbiddenError` (403), `NotFoundError` (404), `ConflictError` (409),
`BusinessRuleError` (422). Las excepciones
anidadas de los services heredan de esos, así un solo `exception_handler` resuelve toda
la jerarquía por MRO. Ninguna subclase sobreescribe `code`: lo que cambia es el mensaje.

`core/api_errors.py` los mapea todos al mismo envelope:

```json
{"error": {"code": "conflict", "message": "...", "detail": {}}}
```

Los `code` posibles son nueve: `not_found`, `conflict`, `business_rule`, `domain_error`,
`forbidden`, `payload_invalid` (pydantic, el único que trae `detail.errors`),
`unauthorized`, `http_error`, `internal_error`.

Hay un handler para `ninja.errors.HttpError` y **no es opcional**: ninja registra el suyo
por default, y como `HttpError` es más específico que `Exception` gana por MRO. Sin el
nuestro, un CSRF fallido responde `{"detail": "CSRF check Failed"}` y rompe el envelope.

**El 422 es ambiguo en el cable** — `business_rule` y `payload_invalid` comparten status.
Quien consuma la API ramifica por `code`.

Con `DEBUG=True` el handler de 500 re-lanza, así que en dev un error no manejado devuelve
el HTML de Django y no el envelope.

No existe `ValidationError` propio: pydantic y Django ya exportan ese nombre.

`DomainError` es para reglas de negocio. **Un bug no es un `DomainError`** — tiene que
terminar en 500 con traceback, no disfrazado de 4xx.

Convención: `get_*` devuelve `| None`, `get_*_or_raise` levanta.

## Borrado lógico

`shared.BaseModel` (`created_at`, `updated_at`, `active`) trae un framework de soft
delete propio: `SoftDeleteCollector` reutiliza el collector de Django y hace
`UPDATE active=False` en lugar de `DELETE`.

- `objects` filtra `active=True`. `all_objects` no filtra.
- `base_manager_name = "all_objects"` es **obligatorio**: las internals de Django (FK
  hacia adelante, `refresh_from_db`, el collector) lo necesitan sin filtrar. Como efecto,
  `ticket.orden_servicio` puede devolver una fila inactiva.
- Todo `UniqueConstraint` es parcial sobre `condition=Q(active=True)`, para que una fila
  dada de baja no bloquee recrearla.
- **FKs: `PROTECT` cruzando agregados o hacia datos maestros (`catalog`,
  `transportista`), `CASCADE` sólo hacia abajo dentro del mismo agregado.** Con `CASCADE`
  hacia `catalog`, dar de baja un cliente daría de baja toda su historia.

## Fechas

`AwareDatetime` de punta a punta. Nunca `date` contra un `DateTimeField`: se guarda como
medianoche UTC con sólo un `RuntimeWarning`, y el paso 2 mide duraciones. Se exige tz
explícita en vez de adivinar — leer un naive de Buenos Aires como UTC corre todo 3 horas.
Almacenamiento en UTC (`TIME_ZONE = "UTC"`, `USE_TZ = True`); la conversión a
`TZ_OPERACION` va en el borde de presentación.

`pytest` corre con `filterwarnings = ["error::RuntimeWarning"]` para que esto no vuelva.

## Geo

PostGIS de verdad, no dos floats. `Ubicacion.coordinates` es un `PointField(srid=4326)`
con `@property latitud`/`longitud` (`.y`/`.x`), y `Zona.geom` un `PolygonField(srid=4326)`.

El DTO `GeoJSONPolygon` usa orden GeoJSON, o sea **`[lng, lat]`**, no al revés. Un SRID
distinto de 4326 se rechaza con `BusinessRuleError`.

## Convenciones de código

Las que cruzan las dos capas (comentarios, vocabulario, sufijos de DTO) están en
`../CLAUDE.md`. Propias del backend:

- Un modelo por archivo `*_models.py`, re-exportado en `models/__init__.py` con
  `__all__`. Igual para `dtos/`, `services/`, `use_cases/`.
- `db_table` explícito en snake_case. Constraints con prefijo `uq_` / `ck_` / `idx_`.
- Los enums son `StrEnum` con su `*_CHOICES` derivada al lado, no `TextChoices`.
- Tests contra Postgres, nunca sqlite: en sqlite `select_for_update()` es un no-op
  silencioso, y los pasos 2 y 3 son problemas de row locking.
- ruff con `line-length = 100` e `ignore = ["E501"]`; `ban-relative-imports = "parents"`.
  mypy con el plugin de django-stubs y `check_untyped_defs`.

## Dev loop

**Correr Django en el host necesita las librerías nativas de GDAL/GEOS.** Desde que
`django.contrib.gis` está en `INSTALLED_APPS`, sin ellas cualquier comando —hasta
`manage.py check`— muere con `ImproperlyConfigured: Could not find the GDAL library`. El
`Dockerfile` las instala; el host no las tiene por default:

```bash
sudo apt install binutils gdal-bin libgdal-dev libproj-dev
```

```bash
docker compose up -d db         # desde la raíz del repo
uv sync --group dev
uv run manage.py migrate
uv run manage.py runserver
uv run pytest
uv run ruff check --fix && uv run mypy .
```

Antes de commitear: `uv run manage.py makemigrations --check --dry-run`.

Corriendo así, en el host, decouple sí lee el `.env` de la raíz completo (adentro del
contenedor no; ver `../CLAUDE.md`).

La alternativa, sin instalar nada, es trabajar adentro del contenedor, que corre con el
uid del host (ver `../CLAUDE.md`) así que no deja archivos root-owned:

```bash
docker compose exec api python manage.py migrate
docker compose exec api pytest
docker compose exec api ruff check --fix
docker compose exec api mypy .
```

El venv de la imagen está en `/opt/venv` y su `bin/` va primero en el `PATH`, así que los
comandos se llaman directo. `uv run` también funciona, con `UV_NO_SYNC=1` puesto en la
imagen: las dependencias son del build, y agregar una pide `docker compose build api`.

### Probar la ingesta a mano

```bash
uv run manage.py seed_demo          # crea PL01 (planta) + CL100/CL200 (destinos)
uv run manage.py sync_permisos      # materializa PermisoCodigo en la tabla permiso
uv run manage.py createsuperuser    # para el admin, y pasa todo el RBAC
```

`sync_permisos` es idempotente y hay que correrlo **después de cada migrate** que agregue
códigos al enum. Los roles y su asignación se cargan desde el admin.

También hay `import_ubicaciones`, que levanta los xlsx de `seed/` (compose los monta en
`/app/seed:ro`) usando `shared/xlsx.py`.

Con el stack completo arriba, la ingesta se dispara contra el proxy:

```bash
curl -X POST http://localhost/api/v1/tickets/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $(grep '^INGEST_API_KEY=' ../.env | cut -d= -f2)" \
  -d '{ ... }'
```

`TicketIngestIn` pide `numero`, `planta_codigo`, `fecha_ingreso` (**con offset explícito**,
un naive es 422), `transportista: {cuit, razon_social}` y `remitos[]` con
`{numero, fecha, destinos[]}`. La forma exacta está en `/api/v1/docs`.

## Pendientes conocidos

- **Los únicos tests son los de auth/RBAC** (`conftest.py` + `users/tests/`): resolver,
  cascada del borrado lógico, endpoints, CSRF y 403-vs-401. `shared/models.py` sigue siendo
  el código más delicado del repo y sigue sin cobertura propia. Los tests van en un
  directorio `tests/`, no en un `test_*.py` suelto: el per-file-ignore de `S101` es
  `*/tests/*`.
- **El management command de la ingesta programada no existe.**
  `tracking/management/commands/` tiene sólo `__init__.py`, así que hoy la única forma de
  disparar la ingesta es el POST. Es el paso 1 sin terminar.
- `Remito.numero` tiene unique **global**, pero el formato argentino `0001-00000001` se
  numera por punto de venta. Si dos plantas pueden emitir el mismo número, esto va a
  rechazar remitos válidos. Confirmar el alcance real con SAP.
- `OrdenServicio` sólo tiene dos FKs y algunos flags: sin número, sin estado, sin fechas
  planificadas. El paso 3 necesita al menos estado y fechas.
- **No hay API de lectura** de tickets, órdenes de servicio, remitos, ubicaciones ni
  transportistas — sólo el admin. Sin eso el frontend no puede mostrar nada más que zonas.
- **Sin paginación ni filtros.** `GET /zonas/` devuelve todas las zonas activas con su
  polígono completo en una respuesta. Cuando haya volumen, hace falta paginar y los DTOs
  `...Filters` que la convención ya nombra.
- **`ALLOWED_HOSTS` tiene default vacío.** Con `DEBUG=False` y la variable sin setear,
  Django rechaza todo.
- **No hay `STATIC_ROOT` ni `collectstatic`.** Los estáticos del admin se sirven sólo con
  `runserver` en DEBUG.
- `routing/` está vacío (ni `__init__.py`) esperando el paso 4. Las credenciales de ORS
  (`ORS_API_KEY`, `ORS_SNAP_RADIUS_M`) ya están en settings y en compose.
