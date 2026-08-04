# TMS-FR

TMS (Transport Management System) para una operación de fletes en Argentina.
Backend Django 6.0 + Postgres 17. Frontend React en `frontend/`, con su propia
arquitectura en `frontend/CLAUDE.md`.

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

SAP se **consulta por schedule**, no nos hace push. La ingesta programada es un management
command. Además hay un `POST /api/v1/tickets/ingest` que llama al mismo use case, para
poder probar la ingesta a mano (Postman). Va con header `X-API-Key`
(`INGEST_API_KEY`), y sin la variable seteada rechaza todo.

## Arquitectura

```
models/      Definición de datos. Sin lógica de negocio.
services/    Único lugar con acceso al ORM. Clases con @staticmethod.
use_cases/   Orquestan services. Dueños de la transacción. Reciben DTO, devuelven DTO.
dtos/        pydantic BaseModel. El contrato con el mundo exterior.
api/         Adaptadores HTTP de 3 líneas. Lo único que importa ninja.
```

Dependencias en una sola dirección: `api → use_cases → services → models`.
`tracking → logistica → transportista`, y todos → `catalog`. Nunca al revés.

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

### Excepciones

`shared/exceptions.py` define `DomainError` y sus tres subtipos semánticos:
`NotFoundError` (404), `ConflictError` (409), `BusinessRuleError` (422). Las excepciones
anidadas de los services heredan de esos, así un solo `exception_handler` resuelve toda
la jerarquía por MRO.

No existe `ValidationError` propio: pydantic y Django ya exportan ese nombre.

`DomainError` es para reglas de negocio. **Un bug no es un `DomainError`** — tiene que
terminar en 500 con traceback, no disfrazado de 4xx.

Convención: `get_*` devuelve `| None`, `get_*_or_raise` levanta.

### Borrado lógico

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

### Fechas

`AwareDatetime` de punta a punta. Nunca `date` contra un `DateTimeField`: se guarda como
medianoche UTC con sólo un `RuntimeWarning`, y el paso 2 mide duraciones. Se exige tz
explícita en vez de adivinar — leer un naive de Buenos Aires como UTC corre todo 3 horas.
Almacenamiento en UTC; la conversión a `America/Argentina/Buenos_Aires` va en el borde de
presentación.

`pytest` corre con `filterwarnings = ["error::RuntimeWarning"]` para que esto no vuelva.

## Convenciones de código

- **Nada de comentarios explicativos largos.** Código autoexplicativo y nombres claros.
  Un comentario de una línea sólo si hay una restricción no obvia que avisar. El
  razonamiento va acá, en el plan o en el commit.
- Vocabulario de dominio en español (`Ubicacion`, `Remito`, `OrdenServicio`, `numero`,
  `fecha_ingreso`), vocabulario técnico en inglés (`BaseModel`, `create_*`, `*Service`,
  `*Error`, `active`).
- DTOs con sufijo de dirección: `...In` (entrada), `...Out` (salida), `...Filters`
  (query params).
- Un modelo por archivo `*_models.py`, re-exportado en `models/__init__.py` con
  `__all__`. Igual para `dtos/`, `services/`, `use_cases/`.
- `db_table` explícito en snake_case. Constraints con prefijo `uq_` / `ck_` / `idx_`.
- Tests contra Postgres, nunca sqlite: en sqlite `select_for_update()` es un no-op
  silencioso, y los pasos 2 y 3 son problemas de row locking.

## Dev loop

El `.env` vive en la raíz del repo (compose lo necesita ahí para interpolar). Los valores
`APP_DB_HOST`/`APP_DB_PORT` del `.env` son los **host-side**; compose los sobreescribe
con `db:5432` para el contenedor.

```bash
cp .env.example .env            # y completar
docker compose up -d db
cd backend
uv sync --group dev
uv run manage.py migrate
uv run manage.py runserver
uv run pytest
uv run ruff check --fix && uv run mypy .
```

El contenedor `web` corre con el uid/gid del host (`DOCKER_UID`/`DOCKER_GID`) porque el
bind mount `./backend:/app` hacía que escribiera archivos root-owned. El venv del
contenedor vive en `/opt/venv`, fuera del mount.

Antes de commitear: `uv run manage.py makemigrations --check --dry-run`.

### Probar la ingesta a mano

```bash
uv run manage.py seed_demo          # crea PL01 (planta) + CL100/CL200 (destinos)
uv run manage.py createsuperuser    # para el admin

curl -X POST http://localhost:8000/api/v1/tickets/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $(grep '^INGEST_API_KEY=' ../.env | cut -d= -f2)" \
  -d @ingest_ticket.example.json
```

Docs OpenAPI en `/api/v1/docs`. El JSON de `/api/v1/openapi.json` se puede importar
directo en Postman como colección.

## Pendientes conocidos

- `Remito.numero` tiene unique **global**, pero el formato argentino `0001-00000001` se
  numera por punto de venta. Si dos plantas pueden emitir el mismo número, esto va a
  rechazar remitos válidos. Confirmar el alcance real con SAP.
- `OrdenServicio` sólo tiene dos FKs: sin número, sin estado, sin fechas planificadas.
  El paso 3 necesita al menos estado y fechas.
- `shared/models.py` no tiene tests y es el código más delicado del repo.
