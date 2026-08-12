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

Dependencias en una sola dirección: `api → use_cases → services → models`. **Esa sí es una
regla dura.**

Entre apps el default es `tracking → logistica → transportista`, y todos → `catalog`. Eso es
una **guía, no una restricción**: existe para que el acoplamiento no crezca solo, no para
forzar diseños peores. Cuando respetarla sale más caro que cruzarla —partir una entidad en dos
apps, duplicar DTOs, mudar un endpoint de lugar— se cruza y se anota acá.

Hoy hay **una** excepción: `logistica.use_cases` importa `tracking.services` para que la OS
exponga sus tickets y sus remitos. La alternativa era mudar `GET /ordenes-servicio/{id}` a
`tracking` y dejar el CRUD de la OS repartido en dos archivos. Lo único que sí hay que
verificar al cruzar es que no se arme un ciclo de imports; acá no lo hay, porque
`tracking.services` sólo importa `logistica.models`, que no importa nada de `logistica`
hacia arriba.

### Las apps

| App | Modelos | API | Notas |
|---|---|---|---|
| `catalog` | `Pais`, `Ubicacion`, `Zona`, `Provincia`, `Departamento` | zonas (CRUD), división política (lectura) | Datos maestros y geo. Todos dependen de acá. |
| `transportista` | `Transportista`, `Tarifario`, `TarifaFlete`, `ConceptoAdicional`, `TarifaConceptoAdicional` | tarifarios (CRUD) | Tarifarios con vigencia. El alta de transportistas y de conceptos sigue siendo sólo por admin. |
| `logistica` | `OrdenServicio`, `OrdenServicioDestino`, `CostoOrdenServicio` | órdenes de servicio (lectura y edición) | El use case del costo vive en `tracking`, no acá. |
| `tracking` | `Ticket`, `Remito`, `RemitoDestino` | ingesta, costo de OS | La punta de entrada. |
| `users` | `User` (login por email, `username = None`), `Permiso`, `Rol`, `UsuarioRol`, `RolPermiso` | auth (login/logout/me/csrf) | `AUTH_USER_MODEL` y el RBAC. La gestión de roles es sólo por admin. |

`shared/` **no es una app**: es un paquete de soporte (`BaseModel` abstracto,
`exceptions.py`, `dtos.py`, `xlsx.py`). `routing/` **tampoco es una app** y no está en
`INSTALLED_APPS`: no tiene modelos. Hoy sólo aporta la geolocalización de la ingesta, con la
forma puerto/adaptador que el paso 4 va a reusar para el ruteo:

```
routing/domain/     ports.py (Protocol Geocoder), values.py (Coordinate, GeocodeQuery), exceptions.py
routing/adapters/   OpenRouteServiceAdapter
routing/factory.py  build_geocoder(): elige el adapter según ORS_API_KEY
```

`build_geocoder()` devuelve un `GeocoderNoConfigurado` cuando falta `ORS_API_KEY`, que levanta
`RoutingError` en `geocode()`. **Eso es a propósito**: la ingesta ya captura `RoutingError` y
sigue creando la ubicación sin coordenadas, así que sin ORS el sistema no se cae, sólo deja más
filas pendientes de validar. Construir el adapter siempre tiraría `RoutingError` en el
`__init__`, y como **`RoutingError` no hereda de `DomainError`** eso sería un 500 crudo por un
problema de configuración.

`Coordinate.lat/lng` son `Decimal` y `Point()` de Django **no acepta `Decimal`**: el borde lo
cruza `Coordinate.to_lnglat()`, que devuelve floats. Pasar `coordinate.lat` directo a
`_build_coordinates` es un `TypeError`.

**Qué países soporta el geocoder lo decide el adapter, no `GeocodeQuery`.** El DTO sólo limpia
el string. Si validara ahí, un país no soportado sería un `ValidationError` **de pydantic** —que
no es `ninja.errors.ValidationError`, así que ningún handler de `core/api_errors.py` lo agarra— y
terminaría en el handler de `Exception`: 500 y rollback del `@transaction.atomic` de la ingesta
entera. En el adapter es un `RoutingError`, que el use case ya captura. `normalizar_pais()`
acepta el ISO y el nombre porque SAP manda uno y `Ubicacion.pais` tiene el otro por default.

**Un destino que no se pudo geolocalizar viaja en `TicketIngestOut.destinos_sin_geolocalizar`**,
no sólo en un `logger.warning`: es la regla de "nada de fallas silenciosas", y quien dispara la
ingesta necesita saber qué quedó pendiente de revisar. Igual que `remitos_omitidos`, y `completo`
mira las dos listas.

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

Montada en `api/v1/` (`core/urls.py`), armada en `core/api.py`. Son **treinta operaciones**:

| Método | Path | Auth | Entrada | Salida |
|---|---|---|---|---|
| GET | `/api/v1/auth/csrf` | — | — | 200 `CsrfOut` |
| POST | `/api/v1/auth/login` | — | `LoginIn` | 200 `SesionOut` |
| POST | `/api/v1/auth/logout` | sesión | — | 204 |
| GET | `/api/v1/auth/me` | sesión | — | 200 `SesionOut` |
| POST | `/api/v1/tickets/ingest` | `X-API-Key` | `TicketIngestIn` | 201 `TicketIngestOut` |
| POST | `/api/v1/ordenes-servicio/{id}/costo` | `ordenes_servicio.calcular_costo` | — | 200 `CostoOrdenServicioOut` |
| GET | `/api/v1/ordenes-servicio/opciones` | `ordenes_servicio.ver` | — | 200 `OrdenServicioOpcionesOut` |
| GET | `/api/v1/ordenes-servicio/` | `ordenes_servicio.ver` | `Query[OrdenesServicioFilters]` | 200 `list[OrdenServicioOut]` |
| GET | `/api/v1/ordenes-servicio/{id}` | `ordenes_servicio.ver` | — | 200 `OrdenServicioDetalleOut` |
| PUT | `/api/v1/ordenes-servicio/{id}` | `ordenes_servicio.editar` | `OrdenServicioIn` | 200 `OrdenServicioOut` |
| GET | `/api/v1/zonas/` | `zonas.ver` | — | 200 `list[ZonaOut]` |
| POST | `/api/v1/zonas/` | `zonas.crear` | `ZonaIn` | 201 `ZonaOut` |
| GET | `/api/v1/zonas/{id}` | `zonas.ver` | — | 200 `ZonaOut` |
| PUT | `/api/v1/zonas/{id}` | `zonas.editar` | `ZonaIn` | 200 `ZonaOut` |
| DELETE | `/api/v1/zonas/{id}` | `zonas.eliminar` | — | 204 |
| GET | `/api/v1/ubicaciones/` | `ubicaciones.ver` | `Query[UbicacionesFilters]` | 200 `list[UbicacionOut]` |
| GET | `/api/v1/ubicaciones/opciones` | `ubicaciones.ver` | — | 200 `UbicacionOpcionesOut` |
| POST | `/api/v1/ubicaciones/` | `ubicaciones.crear` | `UbicacionCrearIn` | 201 `UbicacionOut` |
| POST | `/api/v1/ubicaciones/geocodificar` | `ubicaciones.crear` **o** `.editar` | `GeocodificarUbicacionIn` | 200 `UbicacionGeocodificadaOut` |
| PUT | `/api/v1/ubicaciones/{id}` | `ubicaciones.editar` | `UbicacionIn` | 200 `UbicacionOut` |
| GET | `/api/v1/divisiones/provincias` | `zonas.ver` | — | 200 `list[ProvinciaOut]` |
| GET | `/api/v1/divisiones/provincias/{codigo}/departamentos` | `zonas.ver` | — | 200 `list[DivisionOut]` |
| POST | `/api/v1/divisiones/union` | `zonas.crear` **o** `.editar` | `UnionDivisionesIn` | 200 `UnionDivisionesOut` |
| GET | `/api/v1/tarifarios/opciones` | `tarifarios.ver` | — | 200 `TarifarioOpcionesOut` |
| GET | `/api/v1/tarifarios/` | `tarifarios.ver` | `Query[TarifariosFilters]` | 200 `list[TarifarioOut]` |
| POST | `/api/v1/tarifarios/` | `tarifarios.crear` | `TarifarioIn` | 201 `TarifarioDetalleOut` |
| GET | `/api/v1/tarifarios/{id}` | `tarifarios.ver` | — | 200 `TarifarioDetalleOut` |
| PUT | `/api/v1/tarifarios/{id}` | `tarifarios.editar` | `TarifarioIn` | 200 `TarifarioDetalleOut` |
| POST | `/api/v1/tarifarios/{id}/cerrar` | `tarifarios.editar` | `CerrarTarifarioIn` | 200 `TarifarioOut` |
| DELETE | `/api/v1/tarifarios/{id}` | `tarifarios.eliminar` | — | 204 |

Todas declaran `**ERRORS` (400/401/403/404/409/422/500 → `ErrorOut`). **Todo lo de dominio es
browser-only**: la `X-API-Key` quedó **exclusivamente para la ingesta**. El costo de OS la
aceptaba y dejó de hacerlo cuando la pantalla de órdenes de servicio necesitó el botón de
calcular — costear es una acción de usuario, no máquina a máquina, y la key no se puede poner
en el bundle sin publicarla. No hay `/health` y no hay paginación: los GET de lista devuelven
el array completo sin envelope.

**`/ordenes-servicio/` lo sirven dos routers montados sobre el mismo prefijo**, y no es un
descuido: el CRUD vive en `logistica/api.py` y el POST del costo en `tracking/api.py`, porque
`CalcularCostoOrdenServicioUseCase` importa `RemitoService` y `TicketService` y **`logistica` no
puede importar `tracking`**. `add_router` admite repetir prefijo mientras no sea el mismo router
(ahí haría falta `url_name_prefix`), y los paths no chocan porque el converter `int:` hace que
`/opciones` no matchee la ruta de id.

**La OS no tiene alta ni baja por API**, igual que ubicaciones: nace de la ingesta de SAP. El
PUT toca sólo lo que la ingesta no sabe llenar — `fecha_viaje`, `tipo_operacion`, `tipo_camion`,
`via`, `hombreador`, `facturable` y **`destinos`** — y **no recalcula el costo**: el
`CostoOrdenServicioOut` que devuelve puede haber quedado viejo respecto de lo que se acaba de
guardar. Recalcular es el POST, explícito, y la SPA bloquea el botón mientras el formulario esté
sucio.

**`OrdenServicioIn.destinos` es tri-estado y los tres estados importan.** `None` —el campo
omitido— es "no tocar los destinos"; `[]` es "borralos, y que vuelvan a decidir los remitos"; una
lista con filas los reemplaza enteros. Un `= []` pelado como default haría que cualquier PUT que
no mande el campo borre los destinos **en silencio**, y ningún test lo notaría porque las OS de
los fixtures no tienen ninguno.

`OrdenServicioService.replace_destinos` copia a `TarifarioService.replace_hijos` —baja lógica más
`bulk_create`, seguro por la unique parcial sobre `active=True`— y también **sus chequeos**: un
`ubicacion_id` repetido o inexistente es 422 y no el `IntegrityError` de la unique o de la FK, que
sería 500. Lo que agrega es un **early return cuando los ids que llegan ya son los vigentes**: el
PUT es de objeto entero, así que cambiar `hombreador` reenvía los destinos, y sin eso cada
guardado dejaría una generación muerta de filas. Los tarifarios se editan poco y no tienen ese
problema; una OS se corrige todo el tiempo.

**`costo_desactualizado` es un detector, no un certificado.** El PUT no recalcula, así que
`CostoOrdenServicioService.esta_desactualizado` compara lo congelado en el costo contra lo vivo de
la OS. `dias` queda afuera a propósito —leerlo pide `get_dias_permanencia`, que levanta si un
ticket no tiene egreso, y no poder costear no puede impedir mostrar la OS— y la **cantidad de
destinos sólo se compara cuando son explícitos**: con destinos derivados, `resolve_destinos`
colapsa los extranjeros en un punto de salida y el crudo no dice cuántos se van a tarifar, así que
compararlos daría falsos positivos. En la lista se compara sólo lo escalar, que sale gratis con
los costos ya batcheados; contar destinos por fila pediría un aggregate más.

`GET /ordenes-servicio/opciones` existe porque `tipo_operacion`, `tipo_camion` y `via` **son
`StrEnum`, no tablas**. Sale de los `*_CHOICES` ya derivados al lado de cada enum, así que
agregar un valor al enum lo publica solo. Es una sola operación con las tres listas y no tres
endpoints: el formulario las necesita juntas. Desde que la OS tiene destinos propios lleva además
las **ubicaciones**, por lo mismo que `/tarifarios/opciones`: un request, y un usuario con
`ordenes_servicio.editar` no necesita encima `ubicaciones.ver`. Van con `tipo` y
`tiene_coordenadas` —anotado, para no traer la geometría de las ~1793 filas— porque elegir una
ubicación sin punto hace fallar la tarifa por zona recién al apretar Calcular, y la pantalla lo
avisa antes. Son ~181 KB en una query.

`OrdenServicioOut` desnormaliza `origen_codigo`/`origen_nombre` y `transportista_razon_social`
porque **no hay API de transportistas**: sin eso la tabla mostraría ids pelados. El costo vigente
viaja embebido en `costo` (`null` si nunca se calculó) para que abrir la pantalla no pida un
request por fila. En la lista lo resuelve `CostoOrdenServicioService.get_costos_vigentes`, una
query para todas; el `from_model` **lo recibe por parámetro** en vez de leer `orden.costos`,
porque el ORM vive sólo en `services/`. Lo mismo vale para `tickets`.

**`TicketOut.dias_estadia` sale del mismo lugar que el costo.** `TicketService.dias_estadia`
es la única implementación de la regla —diferencia de **fechas** en `TZ_OPERACION`, porque la
estadía empieza cuando cambia el día— y `get_dias_permanencia` la suma en vez de repetirla.
Es el número que multiplica `precio_dia`, así que si la pantalla lo calculara por su cuenta
podría mostrar algo distinto de lo que se factura. Hay filas reales que lo prueban: un ticket que
entra 23:57 y sale 01:00 es **1 día**, y uno que entra 14:42 y sale 19:09 del mismo día es **0**.

La diferencia entre los dos métodos es qué hacen sin egreso: `dias_estadia` devuelve `None` y
`get_dias_permanencia` levanta `TicketSinEgresoError`. **Es a propósito**: no poder costear una
OS no puede impedir mostrarla, así que el DTO viaja con `null` y la pantalla lo marca.

**La lista y el detalle son dos formas distintas a propósito.** `OrdenServicioOut` lleva
`tickets` —el número de ticket es el código con el que la empresa identifica el trabajo, y es
uno por OS: no pesa—, y `OrdenServicioDetalleOut` hereda de ella y **suma `remitos` con sus
destinos**, que son N por OS con M destinos cada uno. Heredar en vez de duplicar campos es lo
que evita que las dos se desincronicen; `from_model` devuelve `Self` y acepta `**extra` para
que la subclase reuse el mapeo.

`RemitoService.list_by_orden_servicio` resuelve remitos y destinos en dos queries con un
`Prefetch`. Dos cosas que no son opcionales: el `active=True` **explícito** en la queryset del
prefetch (la damos nosotros, así que el manager por default no la filtra), y el `order_by`
explícito en los dos niveles — `Remito.Meta` **no tiene `ordering`** y `RemitoDestino` **no
tiene campo de secuencia**, así que sin eso el orden en pantalla cambia entre requests.

### Los filtros de la lista

`OrdenesServicioFilters` tiene seis. Los tres que se agregaron con la búsqueda:

- **`numero`** matchea con `icontains` contra el número de **ticket o de remito**, por travesía
  inversa (`tickets__numero`, `remitos__numero`). El `.distinct()` **no es opcional**: son dos
  joins multivaluados y una OS con dos tickets que matchean sale repetida — con los datos del
  seed, sin él una OS aparece tres veces. Y va `active=True` explícito en cada salto.
- **`fecha_viaje_desde` / `fecha_viaje_hasta`** son `date`, no `AwareDatetime`, y **no
  contradice** la regla de fechas aware: lo que viaja es un día del calendario y el backend lo
  resuelve a instantes en `TZ_OPERACION`. `hasta` suma un día y compara con `__lt`, así que
  incluye el día entero. El borde importa de verdad: una OS a las `02:57Z` del 3 de febrero es
  el **2 de febrero** en Buenos Aires, y con un `__date` ingenuo se corre un día entero sin que
  nadie lo note.
- **`incluir_sin_fecha`** sólo tiene efecto con un rango puesto: sin rango las OS sin
  `fecha_viaje` ya entran igual. Existe porque un rango las excluye por definición, y son justo
  las que hay que completar; sin este flag se vuelven invisibles desde que la pantalla arrancó
  con un rango por default.

**`numero` está indexado con trigramas.** `icontains` es `ILIKE '%…%'`, que ningún B-tree puede
servir, así que `ticket` y `remito` tienen un `GinIndex` con `gin_trgm_ops` sobre `numero`
(`idx_ticket_numero_trgm`, `idx_remito_numero_trgm`) y `django.contrib.postgres` está en
`INSTALLED_APPS`. La extensión la crea la migración `tracking.0002` con `TrigramExtension()`,
que **va antes de los `AddIndex`** porque sin ella `gin_trgm_ops` no existe. `CREATE EXTENSION`
pide superuser: donde el usuario de la app no lo sea, la extensión la crea un DBA antes de
migrar. Con menos de 3 caracteres el índice no aplica —un trigrama son tres— y Postgres vuelve
al seq scan; no es un problema, pero explica por qué un `EXPLAIN` de prueba necesita un patrón
de 3 o más.

**`UbicacionesFilters` fue el primer DTO `...Filters`; `OrdenesServicioFilters` lo copia.** `Query[UbicacionesFilters]` con
un `pydantic.BaseModel` pelado funciona —no hace falta `ninja.Schema`— y ninja lo aplana en un
`parameters` por campo **además** de emitir `components.schemas.UbicacionesFilters`, así que el
frontend lo aliasea por nombre como cualquier otro DTO. Ese component queda **huérfano** (nada
lo referencia; sobrevive porque el aplanado deja su entrada en `$defs`), así que si algún día
openapi-typescript poda los no referenciados, el alias del frontend rompe el `tsc`. Falla
ruidosa, no silenciosa.

Tiene **dos filtros y no son el mismo conjunto**, que es la distinción que importa:

- `validada=False` es la cola que llena la ingesta: coordenadas adivinadas por el geocoder.
- `con_coordenadas=False` es el atraso que ya existe: `import_ubicaciones` crea filas
  **validadas y sin punto** cuando el xlsx no trae `lat`/`long`. Son las que hacen fallar
  `TarifarioService._resolve_por_zona` con `motivo="sin_coordenadas"`, y el filtro de
  `validada` **no las encuentra**.

Un `?validada=` vacío o con basura da 422 `payload_invalid`; desde la SPA no se llega porque el
`validateSearch` de la ruta lo neutraliza antes.

**Ubicaciones tiene alta pero no baja.** La mayoría nacen de la ingesta de SAP, pero hay
ubicaciones que SAP no manda nunca —un **expreso** al que se le factura, un puerto— y sin alta
propia la única forma de cargarlas era el admin. El PUT sigue siendo sólo corrección: toca
`nombre`, `tipo` y `coordinates`, y **marca `validada=True`** — editar es revisar. `codigo` no es
editable porque es la clave con la que `upsert_by_codigo` las reconoce, y la dirección tampoco: es
la entrada de la geolocalización y el upsert la vuelve a traer de SAP.

**El alta usa `UbicacionCrearIn` y no `UbicacionIn`, a propósito.** Compartir el DTO obligaba a
elegir entre romper esa regla o **declarar en el OpenAPI campos que el PUT acepta y descarta en
silencio**. Y no hereda: los dos contratos están hechos para *no* coincidir, y heredar volvería
creable cualquier campo que el PUT gane después. Que hoy el PUT ignore `calle` y `codigo` lo
sostenía sólo el `extra="ignore"` de pydantic; ahora hay un test que lo fija.

Lo que el alta exige y por qué:

- **La coordenada es obligatoria y la fila nace `validada=True`.** Los dos caminos —marcar el
  punto o aceptar el del geocoder— terminan en un punto que el humano vio. Permitir el alta sin
  coordenada crearía el estado que este documento llama el peor posible: `validada=True` y sin
  punto, afuera de la bandeja de pendientes **y** sin geolocalizar.
- **`pais_codigo` es obligatorio**, y un código que no está en la tabla es **422, no el 404** de
  `get_pais_or_raise`: un 404 en `POST /ubicaciones/` se lee como "no existe la ubicación". Mismo
  criterio que `replace_destinos` con un `ubicacion_id` inexistente.
- **`codigo` es opcional y si repite es 409.** Vacío queda `NULL`, que la unique parcial permite
  repetido. `create_ubicacion` **re-lanza el `IntegrityError` cuando `codigo is None`**, porque
  `uq_ubicacion_codigo` es parcial sobre `codigo IS NOT NULL`: ahí el error es otra cosa y
  reportarlo como choque de código taparía el bug real.
- **`calle`/`localidad`/`provincia` llevan `max_length` en el DTO.** Son columnas NOT NULL, y sin
  el límite un campo largo es un `DataError` de Postgres → 500 donde tiene que ser 422. Es el
  mismo pendiente que sigue abierto en `RemitoUbicacionIn`.
- **Una `planta` sin `codigo` se rechaza con 422.** La ingesta busca la planta por
  `get_ubicacion_by_codigo_or_raise(planta_codigo)`, así que una planta sin código no puede ser
  origen de nada: es un callejón sin salida garantizado y silencioso.
- **`destino_default` no se puede setear.** Es un singleton por clave detrás de una unique
  parcial, el PUT tampoco lo edita, y cambiarlo re-tarifa todas las exportaciones. Sigue siendo
  del admin.

La barra final de `/zonas/` y `/ubicaciones/` es obligatoria: con `APPEND_SLASH` un GET sin
barra redirige 301 y un POST sin barra falla. Los paths con id **no la llevan**, y tampoco los
literales `/ubicaciones/opciones` y `/ubicaciones/geocodificar`, que no chocan con
`PUT /{int:ubicacion_id}` por el converter `int:` — el mismo mecanismo de
`/ordenes-servicio/opciones`.

### Geolocalizar es un preview, no parte del alta

`POST /ubicaciones/geocodificar` no escribe nada: devuelve la coordenada y **`consulta`**, que es
el `GeocodeQuery.as_text()` de lo que se buscó de verdad. Existe separado del POST porque el
pedido era que el usuario **vea el pin antes de que se cree algo**, y geolocalizar adentro del alta
no deja corregirlo.

`GeocodificarUbicacionUseCase` recibe el geocoder **por constructor**, igual que
`IngestTicketUseCase` — que es instance-based justamente para que los tests inyecten uno falso y
no toquen la red. No lleva `@transaction.atomic`: no escribe, y envolver una llamada de red en un
`atomic()` retiene la conexión al ritmo del proveedor.

**`catalog` importa `routing` y eso no cruza ninguna regla:** `routing/` no es una app (no está en
`INSTALLED_APPS`, no tiene modelos) y no importa nada de ninguna app, así que es la misma categoría
que `catalog → shared` y no puede formar ciclo. Lo que sí cambió es que `routing/` pasó de un
consumidor a dos.

**`RoutingError` no se convirtió en `DomainError`, se mapea en el use case.** Cubre cosas que son
bugs o errores de operación —"Respuesta inesperada de open route service", "No hay ORS_API_KEY"— y
mapearlas solas a 422 le diría al usuario que rompió una regla cuando el que falló es el sistema,
además de dejar de avisar a nadie. Y qué *significa* una falla de geocoding es decisión del caller:
la ingesta degrada y reporta, este endpoint se niega y explica.

Para poder distinguirlas se agregó `GeocoderNoConfiguradoError(RoutingError)`, que levanta
`GeocoderNoConfigurado`. La ingesta atrapa la base, así que no cambió. El use case mapea:

| se atrapa | se levanta | `detail.motivo` |
|---|---|---|
| `GeocoderNoConfiguradoError` | `GeolocalizacionNoDisponibleError` (422) | `no_configurado` — el mensaje **no nombra `ORS_API_KEY`** |
| `RoutingError` | `GeolocalizacionFallidaError` (422) | `geocoder`, con `str(exc)` como `message` |

**El proveedor casi nunca dice "no encontré", y esto es lo más importante de toda la feature.**
Medido contra el ORS real:

```
Avenida Pellegrini 1500, Rosario, Santa Fe  -> [-60.646318, -32.956212]   correcto
Calle Que No Existe 99999, Nowhereville     -> [-64.0, -34.0]             200 (!)
Santa Fe (sólo provincia)                   -> [-60.814713, -30.326928]   centroide de la provincia
```

Una dirección inventada devuelve **200 con coordenadas redondas**, o sea un fallback a nivel país.
El adapter descarta el `confidence` y el `layer` que Pelias sí manda, así que ni el endpoint ni la
UI pueden distinguir una coincidencia de portal de un centroide. **Lo único que hoy lo evita es
que el usuario ve el pin antes de guardar**, que es precisamente la razón por la que el preview
está separado del alta. `GeocodificarUbicacionIn` rechaza con 422 el caso de las tres partes
vacías —ahí el centroide era la respuesta garantizada— pero no puede hacer nada con una dirección
basura.

`SUPPORTED_COUNTRIES` es `{"AR": "Argentina"}`: cualquier otro país es 422 "no soportado"
**antes de pegarle a la red**, y el camino que queda es marcar el punto a mano.

`DELETE /zonas/{id}` es borrado lógico. **`TarifaFlete.zona` es `PROTECT`**, así que una zona
con tarifas activas responde 409 `conflict` con `detail.tarifas_flete`: sin ese catch del
`ProtectedError` en `ZonaService.delete_zona` la operación termina en 500, porque un
`ProtectedError` no es un `DomainError`.

### El tarifario se guarda entero, en un solo request

`TarifarioIn` trae la vigencia **y** sus dos colecciones de hijos, y el POST y el PUT las
escriben en una transacción. No hay endpoints por tarifa: una tarifa suelta no significa
nada sin su tarifario, y editar el tarifario fila por fila obligaría al formulario a
orquestar N requests y a decidir qué hacer si el tercero falla.

`replace_hijos` **da de baja las filas vigentes y crea las nuevas** en vez de diffear por
id. Es seguro porque las tres uniques (`uq_tarifa_flete_zona`, `uq_tarifa_flete_ubicacion`,
`uq_tarifa_concepto`) son parciales sobre `active=True`, así que recrear una clave recién
dada de baja no choca — el mismo mecanismo del que depende `replace_costo`.

**Un tarifario usado para costear no se edita ni se da de baja: 409.**
`CostoOrdenServicio` referencia `TarifaFlete` y `TarifaConceptoAdicional` con `PROTECT` y
además **congela los precios**, así que pisar una tarifa dejaría el costo apuntando a una
fila que ya no dice lo que se facturó. La salida es `POST /{id}/cerrar` —que **sí** se
permite estando en uso, es justamente el escape— y cargar un tarifario nuevo.

**El chequeo de "en uso" no importa `logistica`.** `TarifarioService.tarifarios_en_uso`
consulta `costos__active=True`, el accesor inverso que `CostoOrdenServicio.tarifa_flete`
registra con `related_name`. La relación la declara `logistica`, pero se navega desde
`transportista` sin un import, que es lo que la deja del lado correcto de la dirección de
dependencias. Dos queries para toda la lista, no una por fila.

**Las validaciones están repartidas y no es casualidad.** El XOR zona/ubicación va en un
`model_validator` de `TarifaFleteIn` para que sea 422 `payload_invalid` con el `loc` de la
fila, en vez de morir en `ck_tarifa_flete_zona_xor_ubicacion` como un `IntegrityError`
(500). Los duplicados dentro del payload y las FKs inexistentes los chequea el service en
Python **antes** de escribir, por lo mismo: un id inventado tiene que ser 422 y no el error
de la FK.

`GET /tarifarios/opciones` trae modalidades, tipos de camión, transportistas, conceptos,
zonas y ubicaciones en un solo request. Zonas y ubicaciones viajan **acá** y no desde sus
propios endpoints por dos razones: el formulario las necesita juntas (igual que
`/ordenes-servicio/opciones`), y así editar un tarifario no exige además `zonas.ver` y
`ubicaciones.ver`. Van finas —`.only()`, sin geometría ni dirección— así que las ~1785
ubicaciones pesan ~120 KB contra los ~350 KB de `GET /ubicaciones/`.

**`TarifariosFilters.vencidos` filtra por vencimiento, no por vigencia.** Un tarifario
cargado con fecha futura todavía no rige, pero tampoco es historia: con un filtro de
"vigentes ahora", darlo de alta lo haría desaparecer de la pantalla en el mismo momento de
guardarlo. Es tri-estado de verdad — `false` es "sólo los que siguen en pie", no "sin
filtro".

`TarifarioService.get_hijos` lleva un `order_by` explícito y no alcanza con
`TarifaFlete.Meta.ordering`: dos filas pueden compartir modalidad y tipo de camión, y sin
desempate el formulario reordena sus filas entre requests. Es el mismo cuidado que
`RemitoService.list_by_orden_servicio`.

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

**`SessionAuth(*codigos)` es OR, no AND.** El chequeo es
`self.requeridos & get_user_permissions(...)`, o sea que alcanza con **uno** de los códigos.
Durante mucho tiempo ninguna operación pasó más de uno, así que la semántica nunca se ejercitó;
la primera es `POST /ubicaciones/geocodificar`, que acepta `ubicaciones.crear` **o**
`ubicaciones.editar` porque el preview no escribe nada y las dos pantallas lo usan. Tres tests la
fijan. Ojo con el envelope: `detail.requiere` lista los códigos **aceptados**, y se lee como si
fueran todos exigidos — no se renombró porque otros tests asertan sobre esa clave.

**`is_superuser` cortocircuita todo:** `PermisoService.codigos_de_usuario` devuelve el enum
completo sin mirar roles, así que un permiso nuevo lo tiene el superuser desde el momento en que
entra al enum. Para el resto sigue haciendo falta `sync_permisos` **y** asignarlo a un rol.

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

**Agregar un código al enum pide migración además de `sync_permisos`.** `Permiso.codigo` es un
`CharField(choices=PERMISO_CHOICES)` y Django serializa los `choices` en el estado de la
migración, así que `makemigrations --check` falla sin un `AlterField`. La migración no crea
ninguna fila: eso lo sigue haciendo `sync_permisos`.

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
con `@property latitud`/`longitud` (`.y`/`.x`), y `Zona.geom` un `MultiPolygonField(srid=4326)`.

Los DTOs `GeoJSONMultiPolygon` y `GeoJSONPoint` usan orden GeoJSON, o sea **`[lng, lat]`**, no al
revés. Un SRID distinto de 4326 se rechaza con `BusinessRuleError`.

### El upsert de ubicaciones y `validada`

`UbicacionService.upsert_by_codigo` es idempotente **por `codigo` y nada más**. `validada` va en
`create_defaults` y no en `defaults`, por dos razones distintas:

- Como **lookup** rompía la idempotencia: un desajuste contra la fila guardada daba
  `DoesNotExist` → INSERT → `IntegrityError` sobre `uq_ubicacion_codigo`, y Django lo re-lanza
  porque su reintento reusa el mismo lookup malo. Eso abortaba una corrida entera de
  `import_ubicaciones`, cuyo `except DomainError` no atrapa un `IntegrityError`.
- En **`defaults`** des-validaría una ubicación que el usuario ya corrigió a mano.

La ingesta crea con `validada=False` **siempre**, también cuando el geocoder respondió: una
coordenada adivinada es adivinada igual. Es la bandeja de pendientes que consume la pantalla de
ubicaciones, y el único lugar del sistema que la vacía.

`coordinates` entra en `defaults` **sólo cuando la fuente trae una**. Un xlsx sin `lat`/`long`
no puede pisar con `NULL` la coordenada que alguien corrigió a mano: dejaría la fila
`validada=True` y sin punto, o sea fuera de la bandeja de pendientes **y** sin geolocalizar —
el peor estado posible, y el que hace fallar el costeo por zona. `nombre` y `tipo` sí se
refrescan desde la planilla, así que una recarga revierte esas dos ediciones.

### El país es una FK, no un texto

`Ubicacion.pais` es FK a `Pais`, cuya **PK es el código ISO 3166-1 alpha-2** — el mismo que
manda SAP. Eso hace que "¿está en Argentina?" sea `ubicacion.pais_id == PAIS_LOCAL`, sin join
y sin comparar strings libres. `PaisService.resolve` busca por código y cae al nombre, porque
`Ubicacion.pais` traía el nombre y SAP manda el código.

**La FK es nullable a propósito.** Un código que SAP mande y que no esté en la tabla deja la
ubicación sin país, y eso viaja en `TicketIngestOut.destinos_sin_pais` en vez de caerse o de
asumir Argentina. Un país inventado no es lo mismo que Argentina: `resolve_destinos` revienta
con 422 `motivo="sin_pais"` recién cuando alguien intenta costear esa OS, en vez de mandarla
al puerto por accidente.

`catalog/paises.py` es la fuente de la tabla y **está incompleto a propósito**: la data
migration siembra lo que haya y `manage.py sync_paises` lo vuelve a materializar, así que
completar la lista no pide migración.

### Los destinos de la OS: explícitos, o derivados de los remitos

**`RemitoDestino` y `OrdenServicioDestino` no son lo mismo, y ahí está toda la idea.** El primero
es dato de SAP: a dónde va la carga según el remito. El segundo lo carga el usuario y dice **hasta
dónde se factura el viaje**. Los dos coinciden casi siempre, pero no siempre: una exportación se
factura hasta el puerto o el aeropuerto, y un viaje terrestre puede descargar en un **expreso**, un
intermediario que no figura en ningún remito. Antes de que existiera la tabla, el destino a tarifar
se *adivinaba* desde los remitos y eso no se podía expresar.

`CalcularCostoOrdenServicioUseCase` resuelve así, y el orden importa:

```python
destinos = OrdenServicioService.list_destinos_ubicaciones(orden.id)
if not destinos:
    crudos = RemitoService.get_distinct_destinos(orden.id)
    destinos = OrdenServicioService.resolve_destinos(orden, crudos)
```

Los explícitos ganan y se usan **tal cual**: sin chequeo de país y sin inyectar el punto de salida
de la vía. Si el usuario pone una ubicación extranjera, se tarifa contra ella y el humano se hace
cargo — rechazarla recrearía el agujero que `Via.TERRESTRE` deja abierto a propósito, porque esta
tabla **es** el mecanismo per-OS para decidir por dónde sale una exportación terrestre. Por eso el
DTO manda `pais` por destino: la pantalla lo muestra.

**La derivación es el default, no un legado.** Se conservó en vez de reemplazarla porque una OS
nace en `IngestTicketUseCase` cuando llega el camión, sin que nadie la haya mirado: con reemplazo
total, toda OS ingestada quedaría sin poder costearse hasta que alguien tipee destinos, y el camino
que ya funciona —100% nacional, el remito dice la verdad— se volvería carga manual por ticket. Y el
backfill no tenía solución correcta: una data migration sólo puede copiar los destinos crudos, la
resolución depende de `via`, y `via` arranca en `terrestre`; para las OS históricas con destino
extranjero había que elegir entre escribir el destino crudo —que por el camino "verbatim" daría un
**precio equivocado en silencio**— o hacer fallar la migración.

**El detalle no resuelve, y no es un descuido.** `ObtenerOrdenServicioUseCase` expone
`destinos_sugeridos` con los destinos **crudos** de los remitos, nunca el resultado de
`resolve_destinos`. Si resolviera, una OS terrestre con destino extranjero —o con un destino sin
país— haría que `GET /ordenes-servicio/{id}` respondiera 422: la OS se volvería imposible de abrir
y por lo tanto de arreglar cargándole los destinos, que es justo lo que hay que hacerle. Es el mismo
reparto que `dias_estadia` (devuelve `None`) contra `get_dias_permanencia` (levanta). Los sugeridos
salen de deduplicar el resultado de `RemitoService.list_by_orden_servicio` que el use case ya trae
—los modelos de Django hashean por pk— así que no cuestan ni una query extra ni un N+1 sobre `pais`.

`origen_destinos` (`OrigenDestinos`: `explicitos` / `remitos` / `no_aplica`) viaja en el detalle
para que nunca haya que adivinar con cuál de los dos conjuntos se va a costear. `no_aplica` es
cámara, que ignora los destinos por completo: sin eso, alguien que cargue tres destinos en una OS
de cámara los vería descartados sin explicación.

**Nada ramifica sobre `tipo == expreso`.** Es data, igual que `destino_default`. Y la fila de
destino no lleva un `rol` (`salida_pais` / `intermediario` / `final`): nada lo consumiría —la tarifa
se resuelve por modalidad, tipo de camión, hombreador y zona/ubicación, nunca por un rol— y sería el
tercer lugar codificando la misma idea. Tampoco lleva FK al remito que sirve: `tracking.models`
importa `logistica.models`, así que eso sería un **ciclo de imports real**, no una objeción de
estilo; si algún día hace falta imputación por remito, la tabla va en `tracking`.

`secuencia` la asigna el service con `enumerate()` sobre el payload y **no la manda el cliente**,
lo que elimina gratis toda una categoría de validación (huecos, duplicados, negativos). Con
replace-all hoy es redundante —`order_by("id")` reproduce el orden— pero hace explícito un contrato
de orden que si no queda apoyado en la monotonía del `BigAutoField`, y sobrevive al paso 4.

### El destino por defecto de una vía

Esto es lo que corre **sólo cuando la OS no tiene destinos explícitos**. Un destino fuera de
Argentina no se factura hasta la puerta sino hasta el punto de salida del
país, que sale de `OrdenServicio.via`. Qué ubicación es ese punto **no está en el código**:
`Ubicacion.destino_default` la marca, con una unique parcial (`uq_ubicacion_destino_default`)
que garantiza una sola activa por clave. Cambiar el puerto es editar una fila del admin, no
deployar.

`logistica/enums.py` mapea `Via → DestinoDefault`, y vive en `logistica` y no en `shared/`
porque necesita importar `transportista` y `catalog` a la vez — lo mismo que hace a
`PermisoCodigo` legal en `shared/` lo hace ilegal acá. **`Via.TERRESTRE` no está en el mapeo a
propósito**: todavía no se definió a dónde sale un destino extranjero por tierra, y su
ausencia es la rama de error (422 `motivo="via_sin_destino_default"`).

`OrdenServicioService.resolve_destinos(orden, destinos)` recibe los destinos crudos en vez de
buscarlos: `Remito` vive en `tracking` y la dirección es `tracking → logistica`, nunca al
revés. El use case compone `RemitoService.get_distinct_destinos` con él. Se calcula **en
caliente, sin cache**: cambiar la vía cambia el destino en el siguiente cálculo. Y deduplica,
así que tres destinos extranjeros colapsan en un solo punto de salida — eso mueve la modalidad
de multiparada a directo, y `cantidad_destinos` cuenta los resueltos, que es lo que se tarifó.

Cargar destinos explícitos **no lo pisa ni lo apaga**: la función queda igual y sigue siendo el
camino por default. Es la razón de que los once tests de `test_resolve_destinos.py` no se hayan
tocado al agregar la tabla.

### Una zona es un MultiPolygon, y los datos lo forzaron

`Zona.geom` **era** `PolygonField` con el argumento de que una zona es exactamente un polígono.
Componer zonas desde la división política del INDEC lo rompió: la provincia de Buenos Aires es un
MultiPolygon de **81 anillos** por las islas del Delta y las de Bahía Blanca, y 14 de los 527
departamentos también lo son. Con `PolygonField` la feature no podía expresar su caso más común, y
tampoco podía expresar "Chubut más Misiones", que es una zona legítima.

Un anillo abierto sigue sin cerrarse solo — muere en GEOS como 422 `business_rule`, así que el
cliente manda el primer punto repetido al final (`cerrarAnillos()` del frontend lo garantiza).
`ZonaService._build_multipolygon` rechaza con 422 cualquier cosa que no sea un MultiPolygon, así
que un `Polygon` pelado es `payload_invalid` del DTO, no un 500 de la columna.

La migración `catalog.0008` es **a mano y no puede no serlo**: el `AlterField` que genera Django
emite el `ALTER COLUMN ... TYPE geometry(MultiPolygon,4326)` **sin `USING`**, y Postgres rechaza el
cast implícito de `geometry(Polygon)` en cuanto hay una fila. Va con `SeparateDatabaseAndState`
más un `RunSQL` con `ST_Multi(geom)`; la vuelta es `ST_GeometryN(geom, 1)`, con pérdida.

### Zonas compuestas por división política

`Provincia` (24) y `Departamento` (527) son datos maestros de sólo lectura, cargados con
`import_divisiones` desde los CSV del INDEC 2022 de `seed/`. Heredan de un abstracto
`DivisionPolitica` y su **PK es el código del INDEC**, como `Pais`: 2 dígitos una provincia, 5 un
departamento. `codigo` se declara en cada concreto y no en el abstracto porque Django no deja
sobreescribir un campo heredado y los largos difieren.

**Cada uno guarda dos geometrías, y confundirlas es el bug fácil de esta feature:**

- `geom` es la resolución completa y es **la única fuente de la unión**.
- `geom_display` está simplificada a `TOLERANCIA_DISPLAY` (0,005° ≈ 550 m) y es lo único que viaja
  por la API, para el selector. Los 527 departamentos son 1,1 M de vértices completos y 34 k
  simplificados.

`POST /divisiones/union` es un **preview que no escribe nada**, igual que
`/ubicaciones/geocodificar`, y por eso no lleva `@transaction.atomic`. Une con el agregado
`Union("geom")` —un aggregate por tabla, compuestos con `GEOSGeometry.union()`— y simplifica el
resultado a `TOLERANCIA_ZONA` (0,001° ≈ 110 m). Medido: la provincia de Buenos Aires baja de
22.658 vértices y 527 KB de GeoJSON a **2.718 vértices y 58 KB**, en 84 ms; el país entero son
691 ms. Se simplifica **al escribir y no al leer** porque `GET /zonas/` no pagina y devuelve la
geometría completa de todas las zonas: visualizar cinco zonas grandes serían 2,6 MB.
`poligonos`, `vertices` y `superficie_km2` viajan en el DTO porque simplificar es una pérdida y
tiene que verse; misma regla que `destinos_sin_geolocalizar`.

Dos cosas que la simplificación obliga a manejar: `.simplify()` puede **colapsar un MultiPolygon a
Polygon** (hay que reenvolverlo, o la columna lo rechaza), y `SimplifyPreserveTopology` conserva la
topología de cada componente pero **puede cruzar dos componentes entre sí** — ahí el
`ZonaService._check_geom` reusado lo convierte en un 422 ruidoso.

**La zona no guarda qué divisiones se marcaron, y es a propósito.** No hay tabla de procedencia: el
resultado se siembra en el editor del mapa y se puede retocar a mano, así que una selección guardada
dejaría de describir la geometría en la primera edición. Guardarla sería una mentira silenciosa.

`DivisionService.list_provincias` lleva un **`order_by("nombre")` explícito y no es opcional**:
Django ignora `Meta.ordering` en cuanto la query agrupa, y `cantidad_departamentos` es un `Count`.
Sin esa línea el `<Select>` lista las 24 provincias en orden arbitrario. Un código que no existe es
**422 `business_rule` con `detail.codigos`, no 404**, por el mismo criterio que `replace_destinos`
con un `ubicacion_id` inventado: un 404 en esta operación se leería como "no existe la zona".

### Entre dos zonas que cubren los destinos gana la más chica

`ZonaService.get_zones_covering_all` puede devolver N zonas y eso **no es un error**: las zonas se
solapan de verdad. Con los datos reales, un destino en Bariloche cae en `Bariloche` (5.438 km²) y en
`Neuquen / Bariloche` (99.708 km²) a la vez. Antes, si el tarifario tenía tarifa en las dos,
`_resolve_por_zona` respondía 409 y la OS no se podía costear; ahora ordena las tarifas por
`zona__superficie_km2` y **gana la zona más específica**. `TarifaAmbiguaError` quedó sólo para el
**empate exacto de superficie**, que es ambigüedad real: elegir a dedo entre dos zonas
indistinguibles sería la falla silenciosa. El `[:2]` sigue siendo la sonda de "¿hay más de una?", y
el desempate final por `zona_id` hace determinista cuál de dos empatadas se nombra en el mensaje.

**`Zona.superficie_km2` es una columna generada de Postgres, no un cache que escriba el service.**
Es un `GeneratedField` con `db_persist=True` sobre `SuperficieKm2("geom")`
(`catalog/db_functions.py`), o sea `ST_Area(geom::geography) / 1000000`. Tres razones para que la
calcule la base y no `ZonaService`:

- **El admin edita `geom` sin pasar por el service** (`ZonaAdmin` es un `GISModelAdmin`), así que un
  cache escrito en `create_zona`/`update_zona` quedaría viejo y el costeo elegiría mal en silencio.
- No hace falta data migration: `ADD COLUMN ... GENERATED ALWAYS AS (...) STORED` computa las filas
  existentes en el mismo DDL. Postgres lo acepta porque `ST_Area(geography)` y el cast
  `geometry → geography` son los dos `IMMUTABLE`.
- Es un número, no una decisión: no hay caso en que se quiera guardar otro.

**No sirve `Area("geom")` de Django.** En 4326 emite `ST_Area(geometry)`, que devuelve **grados
cuadrados**, y `PostGISOperations.get_area_att_for_field` los etiqueta `sq_m` igual: `.sq_km` daría
un número inventado sin un solo error. El cast a `geography` es lo que da metros geodésicos. Y
`SuperficieKm2` hereda de `GeoFunc` porque un `Func` pelado envuelve el string `"geom"` en un
`Value` y emite `ST_Area('geom'::geography)`. Vive en `catalog/db_functions.py` y no en
`models/zonas_models.py` porque **la migración lo importa por path**: moverlo rompe una migración
histórica.

La única cosa que el `GeneratedField` obliga a recordar: **el `INSERT` lo trae de vuelta y el
`UPDATE` no.** `db_returning = True` deja el valor en la instancia recién creada, pero un `UPDATE`
no tiene `RETURNING`, así que `update_zona` hace `refresh_from_db(fields=["superficie_km2"])` o el
PUT responde con la superficie de la geometría anterior.

Esta superficie **no es la misma** que `superficie_km2` de `Provincia`/`Departamento`: aquélla es la
declarada por el INDEC y viaja en el preview de `/divisiones/union`; ésta se calcula sobre la
geometría **ya simplificada** que se guardó. Neuquén: el INDEC declara 94.269,67 km² y la zona
guardada mide 94.270,62.

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
`/app/seed:ro`) usando `shared/xlsx.py`, y `import_divisiones`, que carga las 24 provincias y los
527 departamentos del INDEC desde los **CSV** de `seed/` (ahí `shared/xlsx.py` no aplica: va
`csv.DictReader`). Los dos son idempotentes por código y tienen `--dry-run`.

Tres cosas de `import_divisiones` que no son opcionales:

- **`csv.field_size_limit(10**9)`.** El default de Python son 131.072 bytes por campo y hay filas
  con 500 KB de GeoJSON: sin eso el import muere en la primera provincia grande.
- **La FK sale de `codigo[:2]`, no de la columna `Código de provincia`**, porque esa columna tiene
  errores: `30105 Victoria` viene como Santa Fe cuando su propio código dice Entre Ríos. El command
  reporta la discrepancia y sigue.
- **`geom_display` se calcula al insertar**, en Python con `.simplify(TOLERANCIA_DISPLAY, True)`.
  Toda la corrida son ~7 s y ~20 MB de geometría.

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

- **`catalog/paises.py` tiene una sola entrada.** La tabla `Pais` arranca con Argentina y nada
  más; hasta que se complete la lista, cualquier destino extranjero de SAP cae en
  `destinos_sin_pais` y su OS no se puede costear.
- **Los tests son los de auth/RBAC (`conftest.py` + `users/tests/`), los de catalog —incluida la
  API de división política y `DivisionService`: la unión de dos vecinos da un polígono, la de dos
  disjuntos da dos, la superficie no cuenta dos veces un departamento de una provincia ya marcada,
  y el orden de las provincias, que sin `order_by` explícito es arbitrario—, los de
  `logistica/tests/` (resolución de destinos por vía, destinos explícitos de la OS, costeo
  —incluida la resolución **por zona**: que entre dos que cubren los destinos gane la más chica y
  que el empate exacto de superficie siga siendo 409— y la API de órdenes de servicio),
  los de `transportista/tests/` (la API de tarifarios: alta con hijos, XOR, duplicados,
  solapamiento, el bloqueo por "en uso" y el filtro de vencidos) y los de la geolocalización de
  la ingesta** (`tracking/tests/`, con un `Geocoder` falso inyectado
  para no tocar la red — es para eso que el use case recibe el geocoder por constructor).
  `shared/models.py` sigue siendo el código más delicado del repo y sigue sin cobertura propia.
  Los tests van en un directorio `tests/`, no en un `test_*.py` suelto: el per-file-ignore de
  `S101` es `*/tests/*`.
- **El management command de la ingesta programada no existe.**
  `tracking/management/commands/` tiene sólo `__init__.py`, así que hoy la única forma de
  disparar la ingesta es el POST. Es el paso 1 sin terminar.
- `Remito.numero` tiene unique **global**, pero el formato argentino `0001-00000001` se
  numera por punto de venta. Si dos plantas pueden emitir el mismo número, esto va a
  rechazar remitos válidos. Confirmar el alcance real con SAP.
- `OrdenServicio` sólo tiene dos FKs y algunos flags: sin número, sin estado, sin fechas
  planificadas. El paso 3 necesita al menos estado y fechas.
- **No hay API de lectura propia** de tickets ni de remitos — sólo el admin. Se leen
  **colgados de su OS** (`OrdenServicioDetalleOut`), que alcanza para
  la pantalla pero no para buscarlos por sí solos. Ubicaciones y órdenes de servicio tienen
  lista y PUT, pero no alta ni baja (a propósito: nacen de SAP).
- **Transportistas y conceptos adicionales son de sólo lectura por API.** Salen embebidos en
  `GET /tarifarios/opciones` para poblar el formulario, pero su alta, edición y baja siguen
  siendo del admin. Cargar un transportista nuevo es, hoy, un paso previo manual al tarifario.
- **El geocoder no distingue una dirección de un centroide.** Pelias devuelve `confidence` y
  `layer` y el adapter los descarta, así que una dirección inventada vuelve como 200 con las
  coordenadas del país (`[-64.0, -34.0]`, medido) y se ve igual que un acierto de portal. Hoy lo
  tapa que el usuario revisa el pin antes de guardar; exponer el `layer` en
  `UbicacionGeocodificadaOut` y avisar en la UI cuando no es nivel dirección es el próximo paso
  obvio, y toca el adapter, que la ingesta también usa.
- **No se puede crear una ubicación en un país que no esté en `catalog/paises.py`**, porque
  `pais_codigo` es obligatorio en el alta. La tabla arranca con AR (y BR si se sembró), y
  completarla es `sync_paises`, sin migración.
- **Dar de baja una ubicación sigue siendo del admin.** Hay alta y edición por API, no borrado; con
  `PROTECT` desde `RemitoDestino`, `OrdenServicioDestino` y `TarifaFlete`, un DELETE tendría que
  mapear el `ProtectedError` a 409 como hace `ZonaService.delete_zona`.
- **El costo no congela *qué* destinos se tarifaron, sólo cuántos.** `CostoOrdenServicio` guarda
  `cantidad_destinos` y no la lista, así que un swap de destino con el mismo count no lo detecta
  `esta_desactualizado` —incluido un cambio de `via` que mueve puerto↔aeropuerto, porque `via`
  tampoco está congelada—. La versión exacta es un snapshot de las ubicaciones costeadas, y tiene
  que ser **texto desnormalizado, nunca FKs con `PROTECT`**: eso le pondría a los destinos de la OS
  el mismo candado que tiene un tarifario en uso, y `replace_destinos` empezaría a tirar
  `ProtectedError` en cualquier OS ya costeada. Se difiere hasta que alguien discuta una factura.
- **La búsqueda por `numero` no dice cuál de los dos matcheó.** Si el texto coincide con un
  remito y no con el ticket, la fila igual aparece y en la columna Ticket se ve otro número.
  Devolver el motivo del match pediría cambiar el DTO de la lista.
- **`facturable` se infiere una sola vez, en la ingesta**, mirando si hay tarifario vigente para
  el transportista. Cargar un tarifario después **no** da vuelta las OS ya creadas: hay que
  marcarlas a mano desde la pantalla. Un recálculo masivo, o inferirlo en el momento de costear,
  es la salida prolija.
- **El filtro `con_costo` no se puede combinar con paginación tal como está.** Es un
  `filter`/`exclude` sobre `Q(costos__active=True)`; el `filter` haría join y duplicaría filas si
  alguna vez hubiera más de un costo activo por OS. Hoy la unique parcial
  `uq_costo_orden_servicio_active` lo garantiza, así que no duplica — pero la garantía es esa
  constraint, no el queryset.
- **Sin paginación.** `GET /zonas/` devuelve todas las zonas activas con su polígono completo, y
  `GET /ubicaciones/` **las ~1785 filas del seed** en una sola respuesta (~350 KB). Es el primer
  candidato real a paginar, y desde que una zona puede ser una provincia entera pesa más: ~58 KB
  por zona grande, que es justamente por qué la unión se guarda simplificada. `UbicacionesFilters` sólo filtra por `validada`; un `con_coordenadas`
  sería el próximo filtro obvio, porque el mapa sólo dibuja las geolocalizadas.
- **`UbicacionOut` expone un subconjunto** de la fila (lo que el mapa necesita más la
  dirección). Agregar campos es aditivo y no rompe al frontend.
- **`import_ubicaciones` revierte `nombre` y `tipo` editados a mano** (no la coordenada, que
  está protegida). El xlsx es master para esos dos campos; si molesta, hay que decidir cuál
  gana y el command tendría que reportar lo que pisó.
- **`Ubicacion.tipo` es editable y nada revalida los tickets existentes.** Pasar una `planta` a
  `cliente` hace que la próxima ingesta con ese `planta_codigo` sea rechazada por
  `TicketService._check_valid_ubicacion` con un 422, sin conexión visible con la edición.
  Guardarlo en el service obligaría a `catalog` a importar `tracking`, que la dirección de
  dependencias prohíbe, así que por ahora sólo se avisa en la UI.
- **`RemitoUbicacionIn` no tiene límites de longitud** (`codigo: str` contra una columna de 20,
  etc.). Un campo largo de SAP es un `DataError` de Postgres → 500 con rollback, donde debería
  ser un 422 `payload_invalid`. `CodigoUbicacion` ya existe para esto y se usa en
  `planta_codigo`, pero no acá.
- **Los municipios del INDEC están en `seed/` y quedaron fuera de alcance a propósito.** Son
  **ejidos municipales, no una teselación**: cubren el 51,3 % del país. Buenos Aires, Chaco,
  Mendoza y Salta están al 100 %, pero Santa Fe 20 %, Entre Ríos 22 %, Río Negro 21 %, Córdoba
  5,6 %, Santiago del Estero 0,2 %, Santa Cruz 0,1 %, y CABA no tiene ninguno. Una zona armada con
  municipios de Santa Fe son islas urbanas con agujeros, y un destino en el hueco no cae en ninguna
  zona: `_resolve_por_zona` falla con `sin_zona_comun`. Los departamentos cubren el **99,9 %** y en
  Buenos Aires **son** los partidos (los 135 códigos y nombres coinciden con los de municipios). No
  cargar `seed/Municipios (2022).csv` sin resolver antes ese agujero.
- **`Provincia` y `Departamento` no tienen centroide.** El CSV lo trae y no se guardó: el mapa
  encuadra con `boundsDe()` sobre la geometría que ya bajó. Lo pide el paso 4, no este.
- **`ALLOWED_HOSTS` tiene default vacío.** Con `DEBUG=False` y la variable sin setear,
  Django rechaza todo.
- **No hay `STATIC_ROOT` ni `collectstatic`.** Los estáticos del admin se sirven sólo con
  `runserver` en DEBUG.
- `routing/` **sólo tiene geocoding**: `Geocoder` + el adapter de ORS. El paso 4 le suma el
  ruteo, y ahí entra `ORS_SNAP_RADIUS_M`, que hoy está en settings y en compose **pero no lo
  lee nadie** (snappear es cosa del ruteo, no del geocoding). `routing/` no tiene tests.
