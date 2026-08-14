# TMS-FR — Frontend

SPA React para el TMS. Consume la API del backend Django que está en `../backend`.
El alcance por pasos, la topología y las convenciones que cruzan las dos capas viven en
`../CLAUDE.md`; **leer ese primero.** La arquitectura del backend y el detalle de la API
están en `../backend/CLAUDE.md`.

Stack: React 19 + TypeScript 6 + Vite 8. Mantine 9 (core, dates, form, hooks, modals,
notifications). TanStack Router 1 (file-based), Query 5, Table 8. axios 1. dayjs.
Leaflet 1.9 + react-leaflet 5 + geoman para el mapa de zonas. Phosphor 2 para los iconos.

**Los iconos se importan de a uno, por subpath:** `@phosphor-icons/react/CaretUp`, nunca
`@phosphor-icons/react`. El barrel exporta ~9000 iconos y Vite lo pre-bundlea entero: **6,9 MB**
contra ~110 bytes del subpath. El `exports` del paquete mapea `./*` a `dist/csr/*`, y con
`moduleResolution: "bundler"` los tipos resuelven igual. Antes de esto los iconos eran SVG a mano
—quedó uno, el chevron de `DataTableExpandible`, que ya pasó a `CaretRight`—; no volver a
escribirlos a mano.

## Alcance

El frontend va detrás del backend, no delante. **Sólo se construyen pantallas para
endpoints que existen.** Nada de inventar rutas ni mockear respuestas para adelantar UI:
si falta el endpoint, el trabajo es en `../backend`.

Hoy la API tiene treinta y dos operaciones: cuatro de auth, cinco del CRUD de zonas
(`/api/v1/zonas/`), seis de ubicaciones (`/api/v1/ubicaciones/`: lista con filtros, opciones,
detalle, alta, geocodificar y PUT), tres de división política (`/api/v1/divisiones/`: provincias,
departamentos de una provincia y el POST de la unión), seis de
órdenes de servicio (`/api/v1/ordenes-servicio/`: opciones, lista con filtros, detalle, PUT,
DELETE y el POST del costo), siete de tarifarios (`/api/v1/tarifarios/`: opciones, lista con filtros, detalle,
POST, PUT, cierre de vigencia y DELETE) y una de máquina. Zonas, ubicaciones, órdenes de servicio
y tarifarios son las cuatro pantallas de dominio; división política no tiene pantalla propia, la
consume el formulario de zona. Tickets sigue teniendo sólo la ingesta desde SAP,
que es máquina a máquina; le falta API de lectura.

## Arquitectura

```
src/
  app/         providers, theme, router, queryClient, navegacion. Configuración del shell.
  api/         schema.d.ts (generado), http.ts, errors.ts. Único lugar con axios.
  features/    una carpeta por app del backend
    catalog/         zonas, ubicaciones
    transportista/   tarifarios (con sus tarifas de flete y de concepto)
    logistica/       órdenes de servicio, costos
    tracking/        tickets, remitos
  routes/      file-based. Sólo composición.
  components/  UI compartida, sin conocimiento de dominio.
  lib/         date.ts, money.ts, numero.ts, geojson.ts, texto.ts
```

Anatomía de un feature:

```
features/catalog/
  api.ts             queryOptions y mutations. El único lugar que escribe URLs.
  zonas-columns.tsx  column defs de TanStack Table
  use-ubicaciones.ts la capa opcional de puntos: permiso + toggle + query
  use-divisiones.ts  provincia elegida + qué está marcado + las dos queries
  components/        formularios y vistas del dominio
  index.ts           la única superficie pública
```

**`use-divisiones.ts` copia el molde de `use-ubicaciones.ts` y por la misma razón:** el estado lo
consumen dos componentes que están en lados opuestos del árbol —`SelectorDivisiones`, afuera del
mapa, y `CapaDivisiones`, adentro—, así que el modal llama al hook una vez y le pasa piezas a cada
uno. Es el mismo reparto que `ControlUbicaciones` / `CapaUbicaciones`.

Lo que sí tiene de más es que es dueño de **tres estados que no son lo mismo** y conviene no
confundir: `provinciasElegidas` es el alcance (qué se lista y se dibuja), `provinciasMarcadas` son
las provincias que entran **enteras** a la zona, y `departamentosMarcados` los departamentos
sueltos. El invariante que mantiene es que las marcas son siempre un subconjunto del alcance.

`features/catalog` importa `features/auth` por su `index.ts`, para `usePermisos()` y `<Can>`.
Es legal: la dirección única de dependencias ordena la cadena de dominio
(`tracking → logistica → transportista → catalog`), y `auth` no está en esa cadena — es
infraestructura transversal.

`features/` espeja las apps del backend que exponen dominio, y hereda **la misma
dirección única de dependencias**: `tracking → logistica → transportista`, y todos →
`catalog`.
Nunca al revés. Transversalmente: `routes → features → api → schema.d.ts`.

Un feature importa de otro **sólo por su `index.ts`**, nunca alcanzando un archivo
interno. `components/` y `lib/` no importan de `features/`.

### Reglas duras

- **axios vive sólo en `src/api/http.ts`.** Es el espejo de "el ORM vive sólo en
  `services/`": cambiar de cliente HTTP tiene que ser reescribir un archivo, no el
  proyecto. En un feature se importa la **instancia configurada**; un
  `import axios from "axios"` fuera de `api/` se saltea `baseURL`, CSRF e interceptors
  sin un solo error.
- **`schema.d.ts` es generado.** No se edita a mano. Si un tipo está mal, se arregla el
  DTO de pydantic y se regenera.
- **No se escriben tipos que dupliquen un DTO.** Se alias-ea el generado conservando el
  nombre del DTO, para que el paralelo con el backend sea obvio:
  `export type ZonaOut = components["schemas"]["ZonaOut"]`.
- **`routes/` sólo compone.** Importa de un feature y arma layout. Ninguna query armada a
  mano, ninguna regla de negocio, ninguna URL.
- **El dinero es string.** El backend serializa `Decimal` como string JSON
  (`"185000.00"`) y así se guarda en el estado. `Number()` sólo dentro de `lib/money.ts`
  y sólo para formatear. Nunca aritmética de pesos en float. Ojo con el caso vacío:
  **`Number("")` es `0`, no `NaN`**, así que sin un guard explícito un precio ausente se
  muestra como `$ 0,00`, que es un precio real. Está cubierto en `money.test.ts`.
- **Toda fecha que sale lleva offset explícito.** El backend exige `AwareDatetime`: un ISO
  naive es 422. La conversión a hora de Buenos Aires pasa sólo en el borde de
  presentación, en `lib/date.ts`.
- **Los pickers de `@mantine/dates` entregan un reloj de pared naive**
  (`"YYYY-MM-DD HH:mm:ss"`, `DateStringValue`), no un `Date` ni un ISO. Mandarlo tal cual es
  un 422 garantizado. `aIsoConOffset()` lo interpreta en **`TZ_OPERACION`, no en la zona del
  browser** — un usuario en otro huso escribiendo "10:00" quiere decir las 10 de Buenos Aires — y
  `aWallClock()` es la vuelta, para alimentar el picker desde el ISO del backend.
- **Se ramifica por `error.code`, no por status.** El 422 es dos cosas distintas.
- **Nada de fallas silenciosas.** Espejo de la regla del backend: si una operación
  descarta datos (`TicketIngestOut.remitos_omitidos`), eso se le muestra al usuario. No
  alcanza con no romper.
- **Estilos: theme centralizado y CSS modules.** Nada de estilos inline ad-hoc ni CSS
  global por componente. Colores y espaciados salen del theme de Mantine.

## Cliente HTTP

Una sola instancia, en `src/api/http.ts`:

```ts
axios.create({ baseURL: "/api/v1", withCredentials: true })
```

**No se usa `xsrfCookieName`/`xsrfHeaderName`.** Ese mecanismo de axios lee
`document.cookie`, y el backend va con `CSRF_USE_SESSIONS`: el secreto vive en la sesión y
**no existe cookie `csrftoken`**. Hay una sola cookie, `sessionid`, y es `HttpOnly`.

El token llega en el body — `SesionOut.csrf_token` de `/auth/login` y `/auth/me`, o
`CsrfOut` de `/auth/csrf` — vive en memoria del módulo, y un interceptor de request lo
pone en `X-CSRFToken` para todo método que no sea seguro. `withCredentials` sigue siendo
necesario para que viaje la `sessionid`.

- **URLs relativas.** No hay `VITE_API_URL`: el mismo origen para SPA y API es la
  topología (nginx sirve las dos cosas en `http://localhost`), no un accidente. Quien
  corra Vite fuera de Docker agrega `server.proxy` en `vite.config.ts`, no una variable
  de entorno.
- **axios no conoce el schema.** Cada feature expone funciones finas que anotan el tipo
  generado — `http.get<ZonaOut[]>("/zonas/")` — y ése es el único lugar donde se escribe
  una URL.
- **La barra final importa.** `/zonas/` la necesita: con `APPEND_SLASH` un GET sin barra
  redirige 301 y un POST sin barra falla.
- **Los tipos generados no siempre dicen toda la verdad.** `TicketIngestOut.completo`, por
  ejemplo, no viaja en el JSON: es un `@property` de Python y no un `@computed_field`, así
  que se deriva acá con `remitos_omitidos.length === 0`.

### Errores

Todo error de la API viene con la misma forma:

```json
{"error": {"code": "not_found", "message": "...", "detail": {}}}
```

Un interceptor de respuesta lo convierte en `ApiError { status, code, message, detail }`.
Hay tres cosas que ese interceptor tiene que tolerar:

- **`error.response` puede ser `undefined`** — error de red, o request cancelada por el
  router.
- **`response.data` puede no ser JSON.** Con `DEBUG=True` el backend re-lanza en el
  handler de 500 y Django devuelve su traceback en HTML.
- **El 422 es ambiguo.** `code: "business_rule"` es una regla de negocio y su `message`
  se le muestra al usuario. `code: "payload_invalid"` es pydantic, y trae
  `detail.errors[]` con `loc` — eso va a los campos del formulario, no a un toast.
  Ramificar por status acá mezcla las dos cosas.

`fieldErrors(err)` traduce los `loc` de pydantic a la forma que espera `form.setErrors()`
de Mantine. **Descarta el prefijo del transporte (`["body","payload"]`) y une el resto con
puntos**, no se queda con el último segmento: dentro de una lista el `loc` es
`["body","payload","tarifas_flete",0,"precio"]`, y quedarse con `"precio"` haría que dos
filas distintas escriban sobre el mismo campo. `"tarifas_flete.0.precio"` es la ruta que
`setErrors()` entiende para los items de una lista. Está cubierto en `errors.test.ts`,
incluido el caso del error de **fila entera** (`loc` sin campo final, que es como llega el
XOR zona/ubicación): ese no cae en ningún input, así que la fila lo renderiza aparte.

Un 401 invalida la sesión y redirige a `/login` con el destino en search params, **salvo en
`/auth/*`**, que maneja los suyos: el del login son credenciales inválidas y redirigir se
comería el mensaje, y el de `/auth/me` lo resuelve el `beforeLoad` de `_authenticated`.
Redirigir ahí loopea.

El redirect se registra con `setOnUnauthorized` desde `main.tsx` y no se importa el router
en `http.ts`: eso cerraría el ciclo `router → routes → features → api → router`.

**El handler tiene que ser idempotente, y hay dos guards que lo hacen.** Un loader que dispara
dos requests —`/ordenes-servicio` pide la lista y las opciones— da **dos 401**, y el handler
corre dos veces. La segunda vez el router ya está en `/login`, así que guardaba
`next=/login?next=…`: entrar bien te devolvía al login. Y como ese `next` anidado queda en la
URL, el intento siguiente desde esa misma URL volvía a fallar.

- `main.tsx` corta si `router.state.location.pathname === "/login"`: no se anida el `next`.
- El `validateSearch` de `/login` descarta un `next` que empiece con `/login`. Este es el que
  **despega a un usuario ya trabado**, porque limpia la URL que quedó guardada.

Está reproducido con Chrome headless entrando a `/login?next=%2Flogin%3Fnext%3D%252F`: sin el
segundo guard, el login exitoso termina en `/login`.

## Data fetching

- Cada feature exporta **factories de `queryOptions`**, no hooks sueltos: es lo que
  permite compartir una única definición entre el componente y el loader de la ruta.
- Query keys colocadas con su feature (`zonasKeys.all`, `zonasKeys.detail(id)`). El
  prefijo es el nombre del recurso, para poder invalidar por prefijo.
- Los loaders usan `queryClient.ensureQueryData(...)`; los componentes
  `useSuspenseQuery` sobre el mismo `queryOptions`.
- `retry` desactivado para 4xx. Reintentar un 409 no lo va a arreglar.
- Después de una mutación, invalidación **explícita por prefijo**. Nunca
  `invalidateQueries()` sin argumentos.
- Errores de mutación → `notifications.show`. Errores de query → error boundary de la
  ruta.

## Tablas

- **TanStack Table es la lógica, Mantine es el markup.** Los componentes de tabla viven en
  `components/`, reciben `columns` + `data` y renderizan con `<Table>` de Mantine. Nada de
  `<table>` a mano en un feature.
- **Son dos componentes y no uno con props opcionales**, y es a propósito:
  - `DataTable` — lista simple, con selección de filas (`rowSelection`). Lo usan zonas,
    ubicaciones y tarifarios.
  - `DataTableExpandible` — lista con un detalle por fila (`getExpandedRowModel`), sin
    selección. Lo usa órdenes de servicio. Agrega él mismo la columna del chevron —es mecánica
    de la tabla, no dominio— y el `colSpan` del panel sale de `getVisibleFlatColumns().length + 1`:
    si no coincide con la cantidad de columnas, la tabla se desalinea sola. El contenido del
    panel **se renderiza sólo con la fila abierta**; montar 20 sub-tablas cerradas por página es
    trabajo tirado.

  Un `DataTable` que hiciera las dos cosas terminaría con props que aplican a la mitad de sus
  usos. La duplicación entre los dos (header, paginación, el `Box` con borde) es el precio, y es
  más barato que la alternativa.
- **No entró `mantine-datatable`.** Es compatible (pide `@mantine/core >=9`, tenemos 9.5) y su
  `rowExpansion` hace exactamente esto, pero `getExpandedRowModel` ya viene en el
  `@tanstack/react-table` instalado. La librería sumaba una dependencia más `clsx`, un
  `docker compose build web`, y un `DataTable` que colisiona de nombre con el nuestro.
- **El `<th>` de las dos tablas es `EncabezadoTabla`**, y ahí vive todo el orden: una columna
  ordenable renderiza un `UnstyledButton` —así se llega por teclado, no sólo por click— con el
  caret de Phosphor al lado, y el `<th>` publica `aria-sort`. Una columna que no se puede ordenar
  no lleva botón ni ícono ni `aria-sort`: el afford aparece sólo donde hay algo que apretar.
  `getCanSort()` ya excluye sola a las de display, porque termina en `!!column.accessorFn`.
- **El caret neutro atenuado es lo que dice que la columna se ordena.** Antes el orden funcionaba
  —el `onClick` estaba en el `<th>` desde el principio— pero no había una sola señal en pantalla
  de que existiera, salvo el `cursor: pointer`. El ciclo es ascendente → descendente → sin orden
  (`enableSortingRemoval` viene en true).
- **Las dos tablas pasan `sortDescFirst: false`, por lo mismo que `getColumnCanGlobalFilter`.** El
  default de TanStack decide la dirección del primer click con `getAutoSortDir()`, que mira el
  **tipo del valor de la primera fila**: string → ascendente, cualquier otra cosa → descendente.
  O sea que una columna nullable como `localidad` arranca descendente sólo porque esa fila viene
  en `null`, y cambia de sentido cuando un filtro server-side cambia cuál es la primera fila.
  Ahora todas arrancan ascendente, incluidas las numéricas. Está cubierto en `DataTable.test.tsx`.
- **El orden y la búsqueda son independientes**: filtrar no lo resetea (sí resetea la página).
- **La barra de búsqueda es opt-in y la prende el prop `buscador`**, que es el placeholder: sin
  el prop no hay barra. La tienen los dos componentes y la usan las cuatro pantallas. Es
  client-side sobre las filas ya cargadas, sin debounce —el de `OrdenesServicioPanel` existe
  porque navega y refetchea; acá es una pasada sincrónica sobre un array en memoria, y con la
  caja vacía `getFilteredRowModel` corta antes de filtrar—. El estado es local del componente y
  no va a los search params: `components/` no conoce el router.
- **Sólo se busca en columnas de texto libre. Una columna de valor tabulado (enum, booleano) o
  formateada distinto de su accessor declara `enableGlobalFilter: false`.** Las tabuladas porque
  su filtro natural es un `<Select>` por columna —el paso siguiente—, y las formateadas porque
  el filtro global compara contra el **accessor**, no contra lo que muestra la celda: buscar
  `11/08` no encuentra un `fecha_viaje` que es ISO, y el `accessorFn` de `costo` devuelve el
  número crudo con `-1` de centinela, así que un `1` traería todas las OS **sin** costo. El
  `filterFn` de la columna no sirve para esto: TanStack usa uno solo para toda la búsqueda
  global, y la única palanca por columna es `enableGlobalFilter`.
- **Las dos tablas pasan `getColumnCanGlobalFilter: () => true`, y no es decorativo.** El default
  de TanStack decide qué columnas se buscan mirando **sólo la primera fila** (`typeof value ===
  "string" || "number"`), así que una columna nullable como `codigo` o `localidad` cuya primera
  fila viene en `null` queda afuera de la búsqueda **para toda la tabla**, y vuelve a entrar
  cuando un filtro server-side cambia cuál es la primera fila. Las de display siguen excluidas
  igual: `getCanGlobalFilter` termina en un `&& !!column.accessorFn`. Está cubierto en
  `DataTable.test.tsx`, que es el único test del archivo que falla si se saca la línea.
- **El filtro es sin acentos y sin distinguir mayúsculas** (`filtroGlobalTexto` +
  `lib/texto.ts`): los datos traen "Córdoba" y nadie los tipea así. La aguja se normaliza una
  vez por tecla y no una por celda, con el hook `resolveFilterValue` que TanStack llama antes
  del loop de filas.
- **Filtrar a cero filas muestra un mensaje propio con el término, distinto de `vacio`.** El
  `vacio` es del caller y habla de los datos; el otro es de la tabla y es genérico, porque
  `components/` no conoce dominio. Antes los dos gateaban con `data.length === 0`, así que
  filtrar todo dejaba un `<tbody>` vacío y mudo. El conteo sale de `getFilteredRowModel()` y
  **no** de `getRowModel()`: `getPaginationRowModel` no clampea el `pageIndex`, así que el
  conteo paginado es 0 por un commit cada vez que la búsqueda achica los resultados estando en
  página > 1, y el mensaje parpadearía tipeando normal.
- **La paginación vuelve sola a la página 1 al buscar** — el memo de `getFilteredRowModel` llama
  a `_autoResetPageIndex()` en su `onChange` y ninguna tabla es `manualPagination`. Cae en un
  microtask, que importa sólo para los tests (`findByText`, no `getByText`).
- **En zonas, una fila seleccionada que el filtro esconde sigue contando** en "Visualizar (n)":
  `seleccionadas` se computa sobre `zonas`, no sobre el row model. Es a propósito —buscar es una
  forma de armar una selección entre páginas—, así que no se "arregla" limpiando la selección.
- Las **column defs viven en el feature**: qué columna, qué label y cómo se formatea un
  precio es conocimiento de dominio.
- El formateo pasa en la `cell`, usando `lib/money.ts` y `lib/date.ts`. Una columna de
  precio recibe el string del `Decimal`, nunca un número.
- **Las dos tablas van con `font-variant-numeric: tabular-nums`** (`tabla.module.css`, el único
  módulo compartido por `DataTable`, `DataTableExpandible` y `EncabezadoTabla`). Sin cifras
  tabulares los dígitos tienen anchos distintos y las comas de una columna de pesos no comparten
  vertical, que es justo lo que hay que poder barrer de un vistazo.
- **Alinear a la derecha se declara con `meta: { numerico: true }` en la column def**, y las
  tablas lo leen para poner la clase en el `<th>` y en el `<td>`. Va por `meta` y no por una
  lista de ids en `components/`: qué columna es un número es conocimiento de dominio, y
  `components/` no lo tiene. El `<th>` ordenable además pasa su `Group` a `justify="flex-end"`,
  porque el botón es `display: block; width: 100%`.
- **Sin el alineado a la derecha las cifras tabulares no se notan.** Es el par lo que hace que
  `$ 1.185.000,00` y `$ 94.500,50` compartan la coma; una sola de las dos mitades no alcanza.
- **Hoy todo es client-side** (`getSortedRowModel`, `getFilteredRowModel`,
  `getPaginationRowModel`). Es correcto: la API no tiene paginación ni filtros y
  `list[ZonaOut]` es el array completo.
- **Ubicaciones ya hizo esa migración a medias, y es el molde** (órdenes de servicio lo copia
  entero: `validateSearch`, `loaderDeps`, `useRouterState` para el estado visual). Sus dos filtros son
  server-side (`UbicacionesFilters`), y el estado vive en los **search params de la ruta**:
  `validateSearch` los tipa, `loaderDeps` hace que el loader se rehaga al cambiarlos, y el mismo
  objeto es la entrada de `ubicacionesQueryOptions(filters)`. Así el filtro es linkeable y
  sobrevive un refresh. El sorting y la paginación siguen client-side porque el backend todavía
  no los tiene.
- **`loaderDeps` enumera los campos, no devuelve `search` entero.** Con `search` completo,
  cualquier param futuro se vuelve dep del loader y mintea un match nuevo aunque el backend no
  filtre por él.
- **El tipo del search es más angosto que el DTO** (`UbicacionesSeleccion`, sin `null`). El DTO
  viene de un `bool | None` de pydantic, y un `null` daría una entrada de cache duplicada
  (`hashChei` no lo colapsa como al `undefined`) más un `?validada=null` que vuelve como el
  **string** `"null"`.
- El booleano en la URL **no necesita serializador custom**: el `parseSearch` por default de
  TanStack es `parseSearchWith(JSON.parse)`, y su `qss.toValue` ya mapea `"false"`/`"true"`.
- **La tabla no se vacía al togglear el filtro, y no es por `placeholderData`.** `stores.matches`
  se cambia por las pending recién dentro de `onReady`, o sea después de que resolvió el loader,
  así que la tabla vieja sigue montada; y como ninguna ruta define `remountDeps`, el `key` del
  componente no cambia y React preserva la instancia (el sorting de `DataTable` sobrevive).
  `placeholderData: keepPreviousData` **no serviría**: `useSuspenseQuery` lo pisa con `undefined`.
- **`Route.useSearch()` va por detrás durante la navegación.** Lee la match ya commiteada, que
  se commitea recién con el loader resuelto, así que un control atado a él no se mueve por
  300-400 ms y parece muerto. El estado visual del `Switch` sale de
  `useRouterState({ select: s => s.location.search })`, y el `isLoading` del mismo hook prende un
  `Loader` al lado.
- Cuando el backend gane paginación, se pasa a `manualPagination` / `manualSorting` /
  `manualFiltering` con el mismo mecanismo.

## Mapa

Leaflet + react-leaflet + geoman, con tiles de OpenStreetMap. El reparto es por **lo que cada
componente sabe**, no por lo que dibuja: `components/` no conoce dominio, así que
`MapaBase` (contenedor + tiles) y `EncuadrarEn` (`fitBounds`) viven ahí, y todo lo que toca un
`ZonaOut` o un `UbicacionOut` vive en `features/catalog/components/`. Un `GeoJSONPolygon` no es
vocabulario de dominio sino un formato de intercambio, y `components/ → api/` va en el
sentido de la flecha, así que importar el tipo generado desde `components/` o `lib/` es legal.

**La regla que hace que cambiar de librería de mapas sea acotado:** la API imperativa de
Leaflet — la instancia del mapa, `map.pm.*`, `invalidateSize`, `fitBounds`, `L.*` — queda
confinada a `components/` y a `EditorPolygono`. Los componentes declarativos (`Polygon`,
`CircleMarker`, `Tooltip`) se usan desde cualquier feature, igual que los de Mantine.

- **`[lng, lat]` de GeoJSON vs `[lat, lng]` de Leaflet.** Toda la conversión está en
  `lib/geojson.ts`, que **no importa leaflet** y por eso es lo único del mapa con tests. Es el
  error más caro del feature porque es silencioso: un polígono invertido se dibuja sin un solo
  error, en otro continente.
- **Para guardar se usa `layer.toGeoJSON()`, nunca `getLatLngs()`.** `toGeoJSON()` emite
  `[lng, lat]` y cierra el anillo; `getLatLngs()` devuelve objetos `{lat, lng}` y **sin** el
  punto de cierre. `cerrarAnillos()` lo garantiza igual, porque el backend rechaza un anillo
  abierto con 422.
- **Al dibujar una zona existente para editarla se descarta el vértice de cierre.** Leaflet
  cierra los anillos solo; dejarlo apila dos handles de vértice sobre el primer punto, y
  arrastrar uno corrompe el anillo sin avisar.
- **Una zona es un `MultiPolygon` y vive en una sola capa de Leaflet.** `pm:create` reemplaza la
  figura anterior. `cutPolygon` **está prendido** desde que `Zona.geom` es MultiPolygon: partir la
  zona en dos ahora es legal, y con eso desapareció el prop `onMultiPolygon` que existía sólo para
  avisar que no se podía guardar. `drawCircle`/`drawCircleMarker` siguen apagados porque exportan
  un `Point`.
- **`toGeoJSON()` devuelve `Polygon` cuando la capa tiene un solo polígono**, no `MultiPolygon`, así
  que `EditorPolygono` normaliza envolviendo las coordenadas en un nivel más. Sin eso el POST manda
  un `Polygon` y el backend lo rechaza con 422 — ruidoso, pero por una razón que no se ve desde la
  UI. `aLatLngs()` devuelve `LatLng[][][]`, que es exactamente lo que `L.polygon()` y
  `<Polygon positions>` aceptan para un multipolígono: no hubo que cambiar cómo se dibuja.
- **El editor se puede *sembrar* desde afuera, y el prop es `semilla: { geom, version }`.** Es como
  llega al mapa la geometría que compuso el selector de divisiones. Va gateado por `version` y no
  por identidad de `geom`, porque `EditorPolygono` lee `valor` **una sola vez** a propósito (para no
  realimentarse con lo que él mismo emite): depender de la semilla entera re-sembraría en cada
  render del padre y **pisaría lo que el usuario acabó de retocar a mano**. El mismo gateo aplica al
  `bounds` que reencuadra. Está cubierto en `EditorPolygono.test.tsx`, en los dos sentidos: una
  versión nueva reemplaza, la misma versión no toca nada.
- **Los eventos de edición se escuchan en la capa, no en el mapa.** `_fireUpdate` y
  `_fireDragEnd` de geoman hacen `layer.fire(type, data, false)`: sin propagación. Sólo
  `pm:create` y `pm:remove` llegan al mapa. Escuchar `pm:update` en el mapa hace que editar una
  zona no llegue nunca al formulario y que el `PUT` guarde la geometría vieja, **sin un solo
  error** — está cubierto por `EditorPolygono.test.tsx`.
- **Nunca el ícono default de un `Marker`.** Leaflet resuelve su URL en runtime y bajo un
  bundler da 404: marcadores invisibles, sin un solo error. Hay dos salidas según el caso, y las
  dos están en uso: `CapaUbicaciones` usa **`CircleMarker`** (un `<circle>`, sin imágenes) para
  sus ~1800 puntos, y `SelectorPunto` usa un **`L.divIcon`** con una clase de CSS module porque
  necesita que el marcador sea arrastrable, cosa que un `CircleMarker` no puede. `divIcon` es lo
  que usa geoman para sus propios handles de vértice.
- **En la clase de un `divIcon` no va `transform`.** Leaflet escribe `translate3d()` **inline**
  sobre ese mismo elemento (`DomUtil.setPosition` desde `Marker._setPos`) y un estilo inline le
  gana a cualquier clase sin `!important`. Un pin con `rotate(-45deg)` se ve como un cuadrado, en
  silencio y sólo en el browser (en jsdom `Browser.any3d` es `false` y posiciona con `left`/`top`,
  así que el test no lo ve). Por eso el marcador es un círculo, que además deja el `iconAnchor`
  sin ambigüedad. El tamaño también lo escribe Leaflet inline desde `iconSize`: declararlo en el
  CSS es código muerto.
- **`preferCanvas` en el mapa está prohibido, y no es una preferencia.** Geoman resuelve el
  elemento DOM de la capa con `layer._path ? layer._path : layer._renderer._container`, y con
  el renderer de canvas un `Polygon` **no tiene `_path`**. Combinado con un teardown después
  de `map.remove()` —que hace `delete renderer._container`— eso da
  `Cannot read properties of undefined (reading 'classList')` al cerrar el modal de una zona
  editada. El mapa va en SVG y `CapaUbicaciones` se trae **su propio** `L.canvas()` para sus
  ~1800 puntos: cada uno tiene el renderer que le corresponde.
- **El cleanup del editor no puede asumir que el mapa está vivo.** React corre el cleanup del
  padre antes que el del hijo, así que `MapContainer` ya hizo `map.remove()` cuando corre el
  de `EditorPolygono`. Un flag sobre el evento `unload` del mapa decide si se puede llamar a
  `map.pm.removeControls()`; llamarlo sobre un mapa muerto es la otra mitad del error de
  `classList`.
- **`MapContainer` sin altura explícita mide 0 px** y el mapa "no aparece". La altura sale de
  un CSS module. Adentro de un `Modal` hace falta además `invalidateSize()`, porque el mapa se
  monta antes de que el contenedor tenga tamaño: `MapaBase` lo resuelve con un
  `requestAnimationFrame` más un `ResizeObserver` — el mismo mock de `test/setup.ts` que estaba
  ahí sólo para Mantine.
- **`app/router.tsx` define un `defaultPendingComponent`, y no es cosmético.** Sin él no hay
  **un solo** Suspense boundary en el árbol: `MatchView` resuelve a `SafeFragment` salvo que la
  ruta declare `pendingComponent`, `wrapInSuspense` o `errorComponent`. Hoy nada suspende porque
  cada loader hace `ensureQueryData` de la misma key que el componente pide con
  `useSuspenseQuery`, pero el primer desajuste entre las dos sería pantalla en blanco con un
  "component suspended but no fallback" en consola, no un spinner.
- **Los modales con mapa van `React.lazy` y se montan sólo abiertos.** Leaflet + geoman + su
  CSS no tienen por qué pesar en la pantalla de la tabla, y montar el mapa recién al abrir es
  también parte del arreglo del contenedor en 0 px.
- **`closeOnEscape={false}` en el modal del formulario.** Leaflet y geoman usan Escape para
  cancelar un vértice; con el default, la primera vez que alguien lo aprieta se cierra el modal
  y se lleva el polígono entero.
- El CSS de Leaflet lo importa `MapaBase` y el de geoman `EditorPolygono`, no `main.tsx`: así
  viaja en el chunk del mapa. Es CSS de librería, la única excepción a "nada de CSS global por
  componente".
- **El basemap es CARTO Voyager, y `MapaBase` tiene los tres estilos en un `ESTILOS` para que
  cambiarlo sea una palabra.** El estándar de OSM quedó afuera porque su relleno de landcover
  —verde de bosques, beige de estepa y roca— se lee como relieve en la cordillera y la Patagonia y
  **compite con lo único que importa en estas pantallas**: los polígonos de zonas y los ~1793
  puntos dibujados encima. Positron fue el primer intento y se pasó para el otro lado: es tan
  desaturado que el mapa no se lee. Voyager es el punto medio; `oscuro` (`dark_all`) queda como la
  opción de máximo contraste. Ojo que **Voyager vive en otro path** (`rastertiles/voyager`, no
  `light_all`). La atribución de **CARTO es obligatoria además de la de OSM**, por sus términos de
  uso. `{s}` y `{r}` los resuelve Leaflet solo y no hace falta API key.
- **Los puntos de `CapaUbicaciones` llevan halo blanco, y no es cosmético.** En Leaflet `color` es
  el **trazo**: dejando el color del tipo ahí, cada punto era una mancha con borde del mismo color
  que sobre un basemap con tinta desaparece. Ahora el color del tipo va en `fillColor` y el trazo
  es blanco, que es exactamente lo que ya hacía el marcador de `SelectorPunto` con su
  `border: 2px solid white`. Además aguanta un basemap oscuro sin tocar nada.
- Si un polígono de zona tapa los nombres de localidad, la salida es un `*_nolabels` de base más
  un `*_only_labels` en un pane de Leaflet por encima de los overlays.

## Auth y permisos

**El `X-API-Key` no se toca desde el browser.** Autoriza escrituras y ponerlo en el bundle
lo publica. Quedó sólo para la ingesta desde SAP. El costo de OS la usaba y dejó de hacerlo
justamente para que el botón de calcular fuera posible: ahora va con sesión más
`ordenes_servicio.calcular_costo`.

`features/auth/` es dueño de todo esto. `/login` es la única ruta pública; todo lo demás
cuelga de `_authenticated`, un layout pathless cuyo `beforeLoad` hace
`ensureQueryData(meQueryOptions())`, redirige a `/login` con el destino en search params si
falla, y devuelve `{ sesion }` al context del router.

**Los permisos viven en el cache de Query, no en un store aparte.** `meQueryOptions` va con
`staleTime: Infinity`, `gcTime: Infinity` y `refetchOnWindowFocus: false`: sin esos tres
overrides hereda el `staleTime: 30_000` global y la UI se reacomodaría sola a mitad de
sesión. Se busca **una vez por carga de página** y se refresca sólo en login y logout. Si a
alguien le cambian los roles, lo ve recién al recargar — y mientras tanto la acción
revocada devuelve 403, que es la defensa real.

El `beforeLoad` corre **fuera de React**, así que un Context de `providers.tsx` no le
llegaría. Por eso la sesión entra al context del router: `usePermisos()` la lee con
`useRouteContext({ from: "/_authenticated" })`, o sea sincrónicamente y sin Suspense.

- `usePermisos()` → `{ sesion, can, canAlguno }`.
- `<Can permiso="zonas.crear">` para esconder acciones. `permiso` está tipado con la unión
  de literales que sale de `schema.d.ts`, así que un typo es error de compilación.
- `requirePermiso(sesion, permiso)` en el `beforeLoad` de una ruta, para quien escribe la
  URL a mano. **No reemplaza al backend**, que revalida en cada request.
- La navbar de `_authenticated` se filtra por permiso.

`bootstrapCsrf()` corre sólo en el `loader` de `/login`: es el único momento en que la SPA
está anónima y necesita un token para poder postear.

## Convenciones de código

Las que cruzan las dos capas (comentarios, vocabulario, sufijos de DTO) están en
`../CLAUDE.md`. Propias del frontend:

- **Los campos de la API se dejan tal como llegan** (`fecha_ingreso`,
  `orden_servicio_id`). Pasarlos a camelCase obliga a una capa de mapeo que no paga.
- Archivos `kebab-case.ts`, componentes `PascalCase.tsx`, un componente por archivo.
- Los sufijos de dirección del backend se conservan en los tipos: `...Out` (salida),
  `...In` (entrada), `...Filters` (query params).

## Dev loop

```bash
docker compose up -d          # db + api + web + proxy
```

Todo queda en `http://localhost`: la SPA en `/`, la API en `/api/v1/`, el admin en
`/admin/`. **`http://localhost:8000` ya no existe** — compose dejó de publicar ese puerto
y a la API se llega sólo por el proxy.

```bash
pnpm dev            # Vite con --host (es lo que corre el contenedor)
pnpm build          # tsc -b && vite build
pnpm typecheck      # tsc -b
pnpm test           # vitest run
pnpm test:watch
pnpm lint
```

**El toolchain necesita Node `^20.19 || >=22.12`** (lo pide Vite 8; vitest 4 pide `>=20`).
El contenedor corre `node:24-slim` y cumple. Si el Node del host es más viejo, nada de
esto corre afuera y hay que ir por el contenedor, que va con el uid del host (ver
`../CLAUDE.md`) así que no deja archivos root-owned:

```bash
docker compose exec web node_modules/.bin/tsc -b
docker compose exec web node_modules/.bin/vitest run
docker compose exec web node_modules/.bin/eslint .
```

Se llaman los binarios directo y no `pnpm <script>` a propósito: pnpm revalida
dependencias en cada invocación y termina peleando con su store (por eso el `CMD` de la
imagen es `vite --host` y no `pnpm dev`; está explicado en `../CLAUDE.md`). El
`node_modules` es un volumen anónimo armado en el build, así que **agregar una dependencia
pide `docker compose build web`**.

Regenerar los tipos de la API, con el stack levantado, **desde la raíz del repo**:

```bash
./generar-tipos.sh
```

No es un one-liner y por eso es un script. Tres restricciones que cualquier versión a mano
tiene que respetar igual:

- **El JSON se baja por el proxy, no de `api:8000`.** `ALLOWED_HOSTS` es
  `localhost,127.0.0.1`, así que Django responde **400** a cualquier otro `Host`.
- **`openapi-typescript` corre adentro del contenedor `web`.** Ya es devDependency, así que
  se llama el binario de `node_modules/.bin` y no hace falta `pnpm dlx`. El Node del host
  puede ser más viejo que lo que pide Vite.
- **El contenedor no puede bajarlo él mismo** —para él `localhost` es él mismo— así que el
  archivo se baja desde el host y tiene que caer **adentro de `frontend/`**, que es el bind
  mount que el contenedor ve como `/app`. El script lo deja en `frontend/.openapi.json` y lo
  borra con un `trap`.

Escribe sobre `src/api/schema.d.ts` **recién cuando la generación terminó bien**, así una
corrida a medias no deja el schema roto, y avisa si no cambió nada. `OPENAPI_URL` permite
apuntarlo a otro lado. Después conviene el `tsc -b`: si el backend agregó un campo requerido,
ahí es donde se ve.

`src/routeTree.gen.ts` lo genera el plugin de router y **se commitea**. No está
gitignoreado a propósito: `pnpm build` corre `tsc -b` antes que `vite build`, así que en un
clone limpio el typecheck necesita el archivo ya presente. La alternativa era un paso
`tsr generate` con `@tanstack/router-cli`, que además está roto por skew de versiones
(el CLI es CJS y `router-core` ya es ESM).

## Tests

vitest + Testing Library, entorno `jsdom`, configurado en `vite.config.ts`.

`src/test/setup.ts` mockea `matchMedia` y `ResizeObserver`: **jsdom no los implementa y
Mantine los consulta**, así que sin esos mocks cualquier render con `MantineProvider`
explota. El mock de `ResizeObserver` dejó de ser sólo de Mantine: `MapaBase` lo usa para su
`invalidateSize`, así que sacarlo ahora rompe el mapa también.

También hace `afterEach(cleanup)`, y hace falta explícitamente: el auto-cleanup de Testing
Library se registra sólo si `afterEach` es global, y `vite.config.ts` **no prende `globals`**.
Sin esa línea, dos `render()` en un mismo archivo dejan los dos árboles montados y cualquier
query encuentra elementos duplicados.

Los archivos de test cubren exactamente lo que es silencioso cuando se rompe:

- `src/app/providers.test.tsx` — smoke test del árbol de providers.
- `src/lib/date.test.ts` — el ida y vuelta entre el reloj de pared naive del picker y el ISO con
  offset del backend. Es el que más paga después de `geojson`: un ISO naive es 422 y un offset
  tomado de la zona del browser guarda la fecha corrida sin que nadie se entere.
- `src/lib/money.test.ts` — el formateo del `Decimal`-string, incluido el caso vacío que
  `Number("")` convierte en un `$ 0,00` que parece un precio real; y el desvío con signo entre
  dos importes, con el redondeo a centavos que evita mostrar la cola binaria de la resta.
- `src/lib/numero.test.ts` — la superficie de una zona, con la misma trampa del `Number("")` y el
  umbral de los 100 km², abajo del cual redondear a entero mostraría `0`.
- `src/api/errors.test.ts` — el mapeo de `loc` a campo de formulario, sobre todo el caso
  anidado: dos filas de una lista tienen que escribir en dos campos distintos, y un error de
  fila entera no puede evaporarse.
- `rangoUltimoMes()` está cubierto en `date.test.ts`: que el extremo derecho sea **hoy** y no
  ayer, porque si no lo del día no se ve al entrar a la pantalla.
- `src/lib/geojson.test.ts` — las conversiones `[lng,lat]`↔`[lat,lng]` y el cierre de anillos.
  Es el que más paga: `lib/geojson.ts` no importa leaflet, y un polígono invertido se dibuja
  en otro continente sin tirar un error. Desde MultiPolygon cubre además el nivel de anidamiento
  extra: que los polígonos queden **separados** (unirlos dibujaría una zona que no existe), que se
  cierren todos los anillos y no sólo el primero, y que el bounding box los abarque todos.
  Cubre también `parsearParLatLng`, el parser del paste de coordenadas: los tres separadores que
  acepta, el redondeo a 6 decimales, y sobre todo lo que **rechaza** —un número solo, una
  dirección, un par fuera de rango—, porque devolver un par a medias ahí escribiría una coordenada
  que el usuario nunca tipeó.
- `src/features/catalog/components/EditorPolygono.test.tsx` — el cableado de geoman: montar y
  desmontar con los modos activos, y que los eventos de edición lleguen al `onChange`. Monta
  Leaflet de verdad con un `getBoundingClientRect` falso. Suma lo de MultiPolygon: que emita
  `MultiPolygon` aunque la capa tenga un solo polígono (`toGeoJSON()` devuelve `Polygon` ahí), que
  una zona disjunta se dibuje en una sola capa, y el gateo por `version` de la semilla en los dos
  sentidos.
- `src/components/SelectorPunto.test.tsx` — el click del mapa emite `[lng, lat]`, y el marcador
  es arrastrable y **no** usa el ícono default (`icon.options.iconUrl` tiene que ser `undefined`).
- `src/components/DataTable.test.tsx` — el orden y la búsqueda global. Del orden: el ciclo
  asc → desc → sin orden con las filas en el orden visible (el candado sobre `sortDescFirst`, que
  falla si se saca la línea), el `aria-sort`, y que una columna no ordenable no tenga botón. De la
  búsqueda, que casi toda falla en silencio: que
  una columna nullable con la primera fila en `null` se busque igual (el candado sobre
  `getColumnCanGlobalFilter`), que `cordoba` encuentre "Córdoba", que las columnas con
  `enableGlobalFilter: false` y las de display **no** se busquen, que los dos estados vacíos sean
  distintos, y que la paginación vuelva a la página 1. Es el único test del repo que envuelve en
  `MantineProvider` a mano: `TextInput`/`Table`/`CloseButton` llaman a `useMantineTheme()`, que
  tira sin provider —los tests de mapa se salvan porque `MapaBase` es Leaflet puro—.
- `src/lib/texto.test.ts` — `normalizarTexto`, incluido el caso sorpresa: la `ñ` queda en `n`.

**El límite de jsdom con el mapa:** nada que use el renderer de canvas se puede testear —
`getContext()` devuelve `null` y muere en `clearRect`. Por eso el error de `classList` de
`preferCanvas` no se reproduce headless aunque su mecanismo esté entendido. Estos tests cubren
el cableado, no el render.

## El shell y la navegación

- **`/` no es una pantalla: es un despachador.** Su `beforeLoad` redirige a la primera pantalla
  que la sesión puede ver, en el orden de `NAV`. Sólo **renderiza** —un `<Alert>` de "no tenés
  acceso a ninguna pantalla"— cuando el usuario no tiene ningún `*.ver`.
- **Y ese caso es el que corta un loop, no un adorno.** `requirePermiso` hace
  `redirect({ to: "/" })` y `login.tsx` navega a `next ?? "/"`: si `/` redirigiera siempre, un
  usuario sin permisos rebotaría entre las dos rutas para siempre. Por eso la cascada termina
  cayendo al componente en vez de a un quinto redirect.
- **Los destinos de esa cascada van literales, no derivados de `NAV`.** Así cada
  `redirect({ to })` queda tipado contra su ruta, que con una unión de strings pelea
  (`/ordenes-servicio` tiene `validateSearch`). El precio es que el orden está escrito dos veces:
  si divergen del manifiesto, es un bug.
- **El manifiesto de navegación vive en `app/navegacion.ts`.** Es configuración del shell, como
  `theme.ts` y `router.tsx`, y lo consumen la navbar y (en orden) el despachador. Es un módulo
  hoja —sólo el tipo `PermisoCodigo` y los iconos— así que no cierra ciclo con `app/router.tsx`.
- **Los ítems están agrupados en "Operación" y "Datos maestros", y la división es real.** Órdenes
  de servicio es el trabajo transaccional del día; zonas, ubicaciones y tarifarios son datos de
  referencia que alimentan el costeo. **Un grupo sin ítems visibles no renderiza su label**: con
  sólo `tarifarios.ver` quedaría un encabezado "Operación" vacío.
- **El activo se marca con una barra dorada y no con el relleno tintado de Mantine.** Es
  `box-shadow: inset` sobre el `data-active` del `NavLink`. En una app de tablas el tinte compite
  con las filas rayadas; la barra no.
- **El bloque de usuario va en el header y no al pie de la navbar.** Abajo de `sm` la navbar
  colapsa, y ahí adentro "Cerrar sesión" desaparecería detrás del burger.
- **El skip link es el primer nodo del DOM, antes del `AppShell`.** Adentro de `AppShell.Main`
  sería el último y no serviría para nada, que es exactamente el bug que viene a evitar.
- **El primario efectivo es el shade 8 en claro y el 4 en oscuro, con `autoContrast`.** El shade 6
  (`#a98d60`) da 3,15:1 sobre blanco: no llega a AA para texto, y una etiqueta blanca sobre un
  botón dorado tampoco. El 8 (`#846c44`) da 4,99:1 y el 4 (`#b8a17f`) 6,24:1 sobre el fondo
  oscuro. Como fondo el dorado se ve casi igual; lo que cambia es el texto.
- **Cada ruta de dominio pone su `document.title` con `useDocumentTitle`** de `@mantine/hooks`,
  que ya estaba instalado. Antes las cinco pestañas decían `Fletes` y no se distinguían.
- **`--mantine-color-gold-contrast` no existe.** Mantine emite `-contrast` sólo para los
  *virtual colors*; para un color suelto emite `-filled`, `-light`, `-outline` y compañía. Como
  gold **es** el primario, la variable correcta es `--mantine-primary-color-contrast`. Usar la
  otra no rompe nada visible: el color simplemente se hereda, en silencio.

## Pendientes conocidos

- **Hay cuatro pantallas de dominio: `/zonas`, `/ubicaciones`, `/ordenes-servicio` y
  `/tarifarios`.** Zonas tiene
  alta, edición y baja con mapa, la capa opcional de puntos y el armado por división política. Ubicaciones tiene **alta y
  edición, sin baja**: la mayoría nacen de la ingesta de SAP, pero un expreso o un puerto no los
  manda nadie, así que hay alta propia con geolocalización asistida. Suma dos filtros (pendientes
  de validar, sin coordenada) y el punto elegido en el mapa. Órdenes de servicio tiene **edición y baja,
  sin alta**, por lo mismo que antes:
  búsqueda por número de ticket o remito, rango de fecha de viaje, tres switches, la columna de
  ticket, el detalle con tickets y remitos, los destinos a facturar, el cálculo del costo —desde
  el modal o desde la fila— y el costo real cargado a mano con sus observaciones.
  Tarifarios es el CRUD completo.
- **El confirm de la baja de una OS enumera lo que se lleva puesto, y no es palabrería.** El
  DELETE arrastra los tickets, los remitos y el costo, y desde la tabla eso es invisible: el
  único rastro es la columna de tickets. Por eso el `openConfirmModal` nombra el ticket cuando
  es uno solo, cuenta cuando son varios, y aclara que **los tarifarios no se tocan**. Es la
  regla de no fallar en silencio aplicada a una acción irreversible desde la UI (la fila vuelve
  sólo por el admin).
- **La tabla de zonas muestra la superficie en km², y no es decorativa.** Es el número con el que el
  backend desempata: cuando dos zonas cubren los destinos de una OS, se costea contra **la más
  chica**. Sin verlo, quien carga las zonas no puede predecir contra qué zona se tarifa cuando se
  solapan (con los datos reales, Bariloche 5.438 km² está adentro de Neuquen / Bariloche 99.708).
  Va con `accessorFn` numérico y no `accessorKey`: sobre el string del `Decimal` el orden sería
  lexicográfico. Debajo de 100 km² `formatearKm2` conserva dos decimales, porque una zona chica
  redondeada a entero se leería como `0 km²`.
- **Una zona se puede componer marcando provincias y departamentos, y el resultado sigue siendo
  editable a mano.** El modal tiene dos pestañas —**Dibujar** y **División política**— pero **un
  solo mapa**, montado afuera de los `Tabs`: cambiar de pestaña no lo remonta ni pierde lo dibujado,
  y "componer" no es un modo aparte sino otra forma de sembrar el mismo editor. Por eso tampoco hay
  procedencia guardada: lo que se guarda es geometría, y el backend no sabe de dónde salió.
- **Los controles van al costado del mapa, no arriba.** Con el selector arriba —select, checkbox de
  provincia entera, filtro, la lista scrolleable de departamentos, los badges y los dos botones— el
  mapa quedaba abajo del fold, justo cuando lo que la pantalla viene a resolver es *ver* el polígono
  mientras se marca. La columna izquierda es fija en 340 px y el mapa toma el resto.
- **El selector de provincias es múltiple, porque una zona puede cruzar provincias.** El
  `MultiSelect` es el **alcance** del armado, no un foco: de todas las provincias elegidas se
  listan y se dibujan los departamentos a la vez, y la lista va **agrupada con un encabezado por
  provincia**. Agrupar no es cosmético: hay homónimos entre provincias (dos "San Martín", dos
  "Belgrano"), y una lista plana los volvería indistinguibles.
- **Sacar una provincia del alcance se lleva sus marcas.** Lo hace `elegirProvincias` en el hook,
  filtrando los dos sets por el prefijo de 2 dígitos. Conservarlas dejaría códigos en el payload
  que no están en pantalla y que no hay forma de destildar: selección invisible, que es la falla
  silenciosa de esta pantalla.
- **Los departamentos de las provincias elegidas se dibujan como malla clickeable**
  (`CapaDivisiones`): click en el mapa marca y desmarca, igual que el checkbox de la lista. Con una
  provincia entera marcada sus checkboxes van `disabled` **y el click del mapa también se ignora**
  — el guard vive en `toggleDepartamento` del hook y no en los componentes, porque son dos caminos
  hacia la misma acción y sumar un departamento ya incluido mandaría el mismo polígono dos veces.
  Ojo que eso es **por provincia**: con Chubut entera marcada, los departamentos de Misiones siguen
  vivos.
- **Los departamentos se piden por provincia con `useQueries`, nunca los 527 juntos.** Una query
  por provincia elegida, con `staleTime: Infinity` porque son datos del INDEC 2022 que no cambian:
  agregar y sacar provincias del alcance no vuelve a pegarle a la red. La geometría que baja es la
  **simplificada**; la unión de verdad la calcula el backend sobre la resolución completa.
- **El memo de `grupos` se ancla en una clave derivada y no en el array de `useQueries`**, que es
  nuevo en cada render. La clave son los largos de cada `data`, y es sólida justamente porque los
  departamentos de una provincia son inmutables. De `grupos` cuelgan `departamentos`,
  `codigosDibujadosMarcados` y el efecto que cachea nombres para los badges.
- **El `<Alert>` de "Geometría compuesta" dice polígonos, vértices y km², y eso es la regla de no
  fallar en silencio.** El backend simplifica el contorno para que la zona sea liviana —Buenos Aires
  entera pasa de 22.658 vértices a 2.718— y el número que se muestra es el de después: es una
  pérdida, y tiene que verse antes de guardar. El conteo de polígonos es lo que explica que Buenos
  Aires sean "81 polígonos separados": son las islas del Delta.
- **La OS tiene su propia lista de destinos, y es el segundo formulario con listas dinámicas.**
  `FilasDestinoOrden` copia el molde de `FilasTarifaFlete` (`insertListItem`/`removeListItem`,
  `<Select searchable limit={50}>` para las ~1793 ubicaciones, el error de fila entera renderizado
  aparte). Los destinos viajan en el **mismo PUT** que el resto de la OS, así que no hay estados
  intermedios que reconciliar.
- **Los destinos siempre se mandan, incluso vacíos, y eso es a propósito.** En la API el campo es
  tri-estado: omitirlo es "no tocar", `[]` es "borralos". El formulario tiene la lista completa en
  pantalla, así que siempre manda su estado real; mandar `undefined` desde acá haría que vaciar la
  lista no se guarde nunca.
- **El `<Alert>` de procedencia es lo que evita que el costo sea magia.** Con destinos cargados dice
  que se factura hasta esa lista, tal cual; sin ellos, que sale de los remitos y que un destino en
  el exterior se reemplaza por el punto de salida de la vía. Sale de `origen_destinos` del detalle.
- **En una OS de cámara el fieldset va deshabilitado con su motivo, no gris y mudo.** El costeo
  ignora los destinos por completo (`cantidad_destinos = 0`), así que dejar los inputs vivos
  invitaría a cargar filas que se descartan sin explicación.
- **El botón dice "Reemplazar por los destinos de los remitos", no "agregar".** Sumar un expreso
  *además* de los destinos de cliente da ≥2 destinos → multiparada → resolución sólo por zona → hace
  falta un polígono que cubra todos, y lo más probable es un 422 `sin_zona_comun`. Para un expreso la
  semántica es reemplazo: se factura hasta ahí, un destino, directo.
- **Una ubicación sin coordenadas se marca en la fila con un badge "sin geo".** La tarifa por zona
  falla con `sin_coordenadas` si a *cualquier* destino le falta el punto, y eso hoy se descubre
  recién al apretar Calcular; `tiene_coordenadas` viene en las opciones justamente para avisar antes.
- **Y desde esa misma fila se arregla, sin cerrar la OS.** El lápiz abre `EditorUbicacionModal` de
  `catalog`, que resuelve el id contra el `GET /ubicaciones/{id}` nuevo y monta el mismo
  `UbicacionFormModal` de `/ubicaciones`. Antes el camino era cerrar la OS —perdiendo lo editado sin
  guardar—, ir a la otra pantalla, buscar la fila y volver.
  - **Es el primer par de modales apilados del repo**, y no hizo falta `Modal.Stack`: los dos
    portalean a `body` con el z-index default, así que el que monta último queda encima, y el
    `scopeTab` de Mantine corta solo cuando el foco no está en su nodo. Lo que **sí** hizo falta es
    apagarle `closeOnEscape` y `closeOnClickOutside` a la OS mientras el hijo está abierto: los dos
    escuchan el mismo `keydown` en `document`, y un Escape cerraba la OS **por debajo**, llevándose
    el formulario. El hijo ya los tenía en `false` por Leaflet.
  - **`EditorUbicacionModal` vive en `catalog` y no en `logistica`, y hace `lazy()` adentro.** Es lo
    que deja el barrel liviano: exportar `UbicacionFormModal` directo desde `catalog/index.ts`
    metería Leaflet y geoman en el chunk de cualquier pantalla que importe el feature, que es
    exactamente lo que la regla de "los modales con mapa van `React.lazy`" evita.
  - **Al guardar se invalidan las `opciones` de OS, no `ubicacionesKeys`.** El badge sale de
    `tiene_coordenadas` de `/ordenes-servicio/opciones`, que va con `staleTime: Infinity`: sin esa
    invalidación arreglar la coordenada no apaga el badge y parece que no pasó nada. Lo dispara el
    prop `onGuardada` del formulario —distinto de `onCreada`, que es de `UbicacionesPanel` y sólo
    limpia su filtro—, porque `catalog` no puede importar `logistica` para invalidar solo.
  - **El lápiz pide `ubicaciones.ver` **y** `ubicaciones.editar`**, no sólo editar: el formulario
    consume `/ubicaciones/opciones` y el detalle, que van con `ubicaciones.ver`. Y **no** se ata al
    `disabled` de la fila, que habla de editar los destinos de la OS y es otro permiso.
- **El aviso de costo desactualizado sale de `costo_desactualizado`, no se calcula acá.** El PUT no
  recalcula, así que editar destinos (o vía, o tipo de camión) deja el total guardado viejo. El
  backend compara lo congelado contra lo vivo; el modal lo muestra sobre el total, que sigue siendo
  el que está guardado.
- **El formulario de tarifario es el primero del repo con listas dinámicas.** Un solo
  `useForm` tiene la vigencia más `tarifas_flete[]` y `tarifas_concepto[]`, y las filas se
  agregan y sacan con `form.insertListItem` / `form.removeListItem` de `@mantine/form` — no
  hizo falta ninguna dependencia nueva. Todo se guarda en **un POST/PUT**: el backend recibe
  el tarifario entero, así que no hay estados intermedios que reconciliar si una fila falla.
- **Cada fila de flete elige "alcance" (zona o ubicación) y recién después la referencia.**
  En la API son dos campos excluyentes (`zona_id` XOR `ubicacion_id`); modelarlo como una
  elección hace que el XOR se cumpla **por construcción** y deja al validador de pydantic
  como red, no como primera línea. El `<Select>` de ubicaciones va `searchable` con
  `limit={50}`: son ~1785 opciones.
- **Las opciones del formulario salen de `/tarifarios/opciones`, no de `/zonas/` ni de
  `/ubicaciones/`.** Un request, `staleTime: Infinity`, y —lo que importa— un usuario con
  `tarifarios.editar` no necesita además `zonas.ver` y `ubicaciones.ver`.
- **Un tarifario ya usado para costear abre en sólo lectura**, con un `<Alert>` que explica
  por qué y las dos salidas: **Cerrar vigencia** y **Duplicar**. Dejarlo gris y mudo sería la
  falla silenciosa; y sin Duplicar, "cargá uno nuevo" significaría retipear N filas a mano.
  Duplicar es 100% frontend: copia las filas, tira los ids y la vigencia.
- **El switch de la lista dice "Incluir históricos" y el filtro de la API es `vencidos`, no
  `vigentes`.** No es lo mismo: un tarifario cargado con fecha de inicio futura todavía no
  rige, y con un filtro de "vigentes ahora" **desaparecía de la pantalla apenas se guardaba**.
  Es el mismo problema que las OS sin `fecha_viaje` escondidas por el rango por default.
- **El precio se maneja como string de punta a punta.** `NumberInput` con
  `decimalScale={2}` y separadores es-AR muestra `$ 1.500,55` pero entrega `1500.55`, que es
  lo que viaja al backend: no hay `Number()` en el camino ni aritmética de pesos en float.
- **La pantalla de OS arranca con un rango de fechas puesto: los últimos 30 días.** El default
  lo inyecta `validateSearch` (`rangoUltimoMes()` de `lib/date.ts`), así que **nunca queda sin
  rango**: limpiarlo vuelve al default. Por eso el `DateRangePicker` va **sin `clearable`** —
  una X que no llega a limpiar nada se siente rota— y por eso `DateRangePicker` tiene un preset
  "Últimos 30 días", que es la única forma de volver al default después de cambiarlo.
- **La pantalla también arranca mostrando sólo las facturables.** Un default que filtra necesita
  un control que sepa decir "traeme el resto": con un switch `facturable` a secas, apagarlo
  volvería al default y no habría forma de ver las demás. Por eso el search param es
  **`incluir_no_facturables`, invertido**, y `ordenesServicioQueryOptions` lo traduce a
  `facturable: true | undefined` antes de pegarle a la API. **Es el único lugar donde el search
  y el query param de la API no se llaman igual**, y la traducción vive en `api.ts`, que es
  quien es dueño del contrato.
- **Un rango por default esconde las OS sin `fecha_viaje`**, que son justo las que hay que
  completar. De ahí el switch "Incluir sin fecha de viaje", que las trae además del rango. Sin
  ese control el trabajo pendiente se vuelve invisible, que es la regla de "nada de fallas
  silenciosas" aplicada a un filtro.
- **Los dos switches de "Incluir…" son el idioma de esta pantalla**, y no es casual: cada vez
  que un default filtra, el control se nombra por lo que agrega, no por lo que restringe. Un
  "Sólo X" apagado no puede representar nada cuando el default ya es X.
- **La caja de búsqueda va con `useDebouncedValue` a 300 ms.** El valor visible es estado local
  y el debounced es el que navega: sin eso cada tecla dispara el loader y una navegación, y el
  input se siente trabado.
- **El botón de calcular costo se deshabilita con el formulario sucio**, y no es una
  formalidad: el POST costea lo que hay **guardado en el servidor**, así que con cambios sin
  guardar mostraría un número que no se corresponde con lo que el usuario tiene en pantalla. Es
  la regla de "nada de fallas silenciosas" aplicada a un botón. El aviso dice por qué está
  bloqueado, en vez de dejarlo gris y mudo.
- **Guardar la OS ya no cierra el modal**, y eso es lo que hace usable el botón de arriba. El
  ciclo real es *corregir → costear*, y cerrando al guardar había que reabrir la OS para apretar
  Calcular. Ahora `guardar.onSuccess` hace `setInitialValues` + `resetDirty` con lo que se
  mandó: el formulario queda limpio, `sucio` pasa a `false` y el botón se desbloquea en el
  lugar. El `onClose()` del camino `not_found` **sí** se conserva: ahí la OS ya no existe.
- **Eso obligó a sacar el estado local del costo, y era un bug esperando.** El modal tenía un
  `useState` con el costo y comparaba `costo === detalle.costo` **por identidad de objeto** para
  decidir si mostrar el aviso de "quedó viejo". Eso sólo funcionaba porque el detalle nunca se
  refetcheaba con el modal abierto; al no cerrarlo al guardar, la invalidación por prefijo lo
  refetchea y la identidad cambia sola, así que el aviso no habría vuelto a aparecer nunca. Hoy
  el costo sale de `detalle.costo` y `costoViejo` es directamente `detalle.costo_desactualizado`,
  que es lo que el backend ya calcula.
- **El costo real y sus observaciones van en el fieldset de Costo, no en Generales.** Son la
  contrapartida del número calculado y se leen contra él: el `description` del campo muestra el
  **desvío** (`+$ 5.000,00 contra el calculado`) cuando existen los dos. Sin eso la resta la
  tiene que hacer el usuario a ojo, que es justo lo que el campo viene a evitar.
- **La resta vive en `lib/money.ts` y no en el componente.** `diferenciaPesos` es la única forma
  de hacer aritmética de pesos en el frontend, y está ahí porque `Number()` sólo se permite en
  ese archivo y sólo para mostrar. Redondea a centavos antes de comparar contra cero: la resta
  en float deja colas de `1e-10` que se verían como un desvío inexistente. Está cubierto en
  `money.test.ts`.
- **La tabla tiene dos columnas de costo, no una.** `costo` es el calculado y `costo_real` el
  cargado a mano; el punto de la pantalla es **ver el desvío**, y una sola columna que muestre
  el real cuando existe esconde exactamente lo que hay que mirar. `costo_real` copia el
  `accessorFn` numérico con `-1` de centinela y el `enableGlobalFilter: false` de `costo`, por
  las mismas dos razones.
- **Calcular el costo también se puede desde la fila.** Es el atajo para la OS que ya está bien
  cargada y sólo hay que costear: no hay que abrir el modal. La mutación vive en
  `OrdenesServicioPanel` (el molde de `TarifariosPanel`) y la fila en curso sale de
  `calcular.isPending ? calcular.variables.id : null`, sin un `useState` aparte.
- **Ese error va a una notificación `autoClose: false`, y la excepción está justificada.** La
  regla de esta pantalla es que los `business_rule` del costeo van a un `<Alert>` y no a un
  toast, porque su mensaje es lo único que explica la falla; desde la tabla no hay un `<Alert>`
  donde quedarse, así que la salida es un toast **que no se cierra solo**, con el número de OS
  en el título. Un toast con autoClose sí sería la falla silenciosa que la regla evita.
- **El botón de la fila no se deshabilita por `facturable` ni por falta de `fecha_viaje`.** El
  backend responde 422 con el motivo exacto, y esconder la acción dejaría al usuario sin la
  explicación de por qué esa OS no se puede costear.
- **El costeo es el endpoint más rico en `business_rule` del repo** y sus mensajes son lo único
  que le explica al usuario por qué falló: OS no facturable, sin `fecha_viaje`, sin tarifario
  vigente, tarifa no resuelta (`detail.motivo` ∈ `sin_coordenadas`/`sin_zona_comun`/`sin_tarifa`),
  vía sin punto de salida, ticket sin egreso, concepto de cámara faltante, tarifario ambiguo
  (409). Por eso van a un `<Alert>` dentro del modal y no a un toast que se va solo.
- **Los `<Select>` de la OS salen del endpoint `/opciones`, no de constantes.** `tipo_operacion`,
  `tipo_camion` y `via` son `StrEnum` del backend, y hardcodearlos —como todavía hace
  `UbicacionFormModal` con `TIPOS`— hace que agregar un valor al enum pase desapercibido. **Ya pasó:**
  `expreso` se agregó a `TipoUbicacion` y hubo que tocar a mano `TIPOS` y el `COLOR_POR_TIPO` de
  `CapaUbicaciones`, porque ningún endpoint publica los tipos de ubicación. Las ubicaciones del
  `<Select>` de destinos sí salen de `/ordenes-servicio/opciones`.
- **La fila de una OS se expande y muestra sus tickets** con ingreso, egreso y estadía
  (`TicketsDeOrden`, reusado tal cual en el modal). La columna de tickets concatenados se
  conserva igual: es lo que permite barrer la tabla sin abrir nada. Una OS **sin** tickets no
  tiene chevron, en vez de abrir un panel vacío.
- **La estadía no se calcula en el frontend.** Viene en `TicketOut.dias_estadia` porque es el
  mismo número que multiplica `precio_dia` en el costo: restarlo acá lo haría divergir del costo
  sin que nadie se entere. Un ingreso 23:57 y un egreso 01:00 son **1 día**, no una hora — hay
  filas reales así en la base.
- **Falta el filtro por columna, que es el paso siguiente de la búsqueda.** La barra global ya
  cubre el texto libre (ver "Tablas"), y las columnas de valor tabulado quedaron marcadas con
  `enableGlobalFilter: false` justamente esperándolo: para un enum el control es un `<Select>`
  por columna, no un `includes` de texto. Hoy no hay forma de filtrar por tipo de ubicación,
  estado de tarifario, vía ni tipo de operación sin mirar la columna a ojo.
- **En órdenes de servicio conviven dos cajas de búsqueda, y es a propósito.** La de arriba es
  server-side (`numero` → search param → loader → refetch, con debounce de 300 ms) y **trae**
  filas del backend por número de ticket o remito; la de adentro de la tabla es client-side y
  **achica** las que ya están. Por eso su placeholder empieza con "Filtrar lo cargado": dos
  cajas con el mismo label se leen como un bug.
- **Editar una ubicación la marca como validada**, y por eso el botón dice "Guardar y validar".
  La dirección se muestra read-only: es la referencia para saber dónde va el punto, pero
  corregirla sería re-geolocalizar y el upsert de SAP la vuelve a traer.
- **Ubicaciones ya tiene alta, y el mismo modal hace las dos cosas.** `UbicacionFormModal` toma
  `ubicacion: UbicacionOut | null` y `UbicacionesPanel` usa el tri-estado de `ZonasPanel`
  (`undefined` cerrado, `null` creando). No se partió en dos porque el cableado del mapa es más de
  la mitad del archivo y es idéntico en los dos modos; el precedente de partir (`DataTable` vs
  `DataTableExpandible`) se justifica por props que aplican a la mitad de los usos, y acá todas
  aplican a los dos.
- **Los campos de dirección ahora son campos del form en los dos modos**, con
  `readOnly={!esNuevo}`. Antes leían `ubicacion.calle` directo y no eran campos, y por eso un 422
  sobre `calle` no tenía dónde caer. Van `readOnly` y no `disabled`, con una línea que explica por
  qué no se editan: "gris y mudo" es la falla silenciosa de la UI.
- **`TIPOS` murió: los tipos y los países salen de `/ubicaciones/opciones`** con
  `staleTime: Infinity`, consumido con `useSuspenseQuery` **dentro del modal**, que ya está
  envuelto en un `<Suspense>` por el panel. Así la ruta no prefetchea opciones que sólo sirven para
  editar. **`COLOR_POR_TIPO` de `CapaUbicaciones` sigue hardcodeado y está bien**: los colores son
  presentación, no datos del enum.
- **"Geolocalizar" vive dentro del `Fieldset` de dirección**, no al lado de Guardar: no es una
  alternativa de submit. Se deshabilita si calle, localidad y provincia están las tres vacías
  —espejando el validador del backend, así el caso común no viaja—, en éxito muestra
  **"Se buscó: …"** porque el backend corta la localidad en el guión y el pin saldría de un string
  que el usuario no escribió, y en error muestra un `<Alert>` con el mensaje del proveedor más el
  próximo paso. Aparece **también editando**: la bandeja de pendientes está llena de filas que la
  ingesta no pudo geolocalizar y reintentar es buena parte del valor. Se esconde con
  `canAlguno("ubicaciones.crear", "ubicaciones.editar")`, porque `<Can>` toma un permiso solo.
- **El pin del geocoder puede ser el centroide del país y verse igual que un acierto.** El
  proveedor devuelve 200 para una dirección inventada. Por eso el flujo es geolocalizar → mirar →
  guardar, y no un alta que geolocaliza sola: el ojo del usuario es la única validación que hay.
- **`CentrarEn` existe porque `MapContainer` sólo honra `center`/`zoom` al montar.** Sin él, tras
  geolocalizar el mapa se queda donde estaba y el marcador aparece fuera de pantalla: la feature
  *parece* rota. `EncuadrarEn` no sirve para un punto, `fitBounds` de un bounds degenerado zoomea
  al máximo. Tiene test porque cuando se rompe se rompe en silencio.
- **La coordenada se tipea, se pega o se marca, y los tres caminos escriben lo mismo.** Los campos
  del form son `lat` y `lng` (`number | string`, `""` vacío) y el `GeoJSONPoint` se **deriva** con
  `aPunto()`; modelarlo al revés —`coordinates` como estado— obligaría a cada input a mantener su
  propio string en paralelo, porque un `-34.` a medio tipear no es un punto. Con lat/lng como
  fuente única, click y drag del mapa actualizan los inputs sin un solo `useEffect` de
  sincronización. Ojo con el derivado: `NumberInput` entrega `"-"` mientras se escribe el signo, y
  un `NaN` ahí llega a Leaflet como posición del marcador.
- **El separador decimal de esos dos campos es punto, no coma como en los precios.** Los
  `NumberInput` de `FilasTarifaFlete` van `decimalSeparator=","` porque es plata en es-AR; una
  coordenada se copia de Google Maps o de un GPS, que emiten `-34.603722`. Con coma, el caso de uso
  principal se rechaza. Por lo mismo hay un `onPaste` que parte `-34.603722, -58.381592` en los dos
  campos: pegar el par en un `NumberInput` lo corta en la coma y no deja nada usable.
- **Van sin `min`/`max`, y el rango se valida en el form.** El `clampBehavior` por default de
  Mantine es `"blur"`: un `95` tipeado en latitud se convertiría solo en `90` sin decir nada, que
  es exactamente la falla silenciosa. El validador espeja a `_build_coordinates` del backend, que
  tira `CoordenadasInvalidasError` — un `business_rule`, o sea el `<Alert>` y no el campo.
- **El mapa se centra al salir del campo, no mientras se escribe.** `-3` → `-34` → `-34.6` son
  tres lugares distintos del planeta, así que un debounce haría saltar el mapa tres veces por
  coordenada. El `onBlur` alimenta el mismo `CentrarEn` que usa el geocoder, y **compone** con el
  `onBlur` que ya trae `getInputProps` en vez de pisarlo. El click del mapa no lo toca: ya estás
  mirando ahí.
- **Al crear con "Sólo pendientes de validar" prendido, el filtro se limpia solo.** La ubicación
  nueva nace validada, así que no entraría en ese filtro y el usuario vería que "no pasó nada". El
  modal avisa con `onCreada` y el panel saca el filtro.
- **Las ubicaciones no se paginan**, así que la capa de puntos del mapa de zonas baja las ~1785
  filas y descarta en el cliente las que no tienen coordenadas — mostrando cuántas fueron, que es
  lo que evita que sea un descarte silencioso.
- **`react-hooks/incompatible-library` avisa sobre `useReactTable`** en `DataTable`: el React
  Compiler no puede memoizar lo que devuelve TanStack Table. Es un warning inherente a la
  librería, no algo por arreglar.
- **No hay alias `@/`.** Ni en `tsconfig.app.json` (`paths`) ni en `vite.config.ts`
  (`resolve.alias`), así que los imports entre carpetas son relativos.
- **No hay `ColorSchemeScript`.** `MantineProvider` va con `defaultColorScheme="auto"`, y
  sin ese script puede haber un flash del scheme equivocado al recargar. Es cosmético.
- Skew menor de versiones: `@tanstack/router-plugin` está en 1.168 y
  `@tanstack/react-router` en 1.170. Misma familia, conviene alinearlas.
- **No hay MSW.** El smoke test no toca la red. Cuando haya features de verdad, hace falta
  para testear estados de carga y error.
- Los pendientes que cruzan las dos capas (auth para el browser, uid/gid de los bind
  mounts, build de producción, versión de Node del host) están en `../CLAUDE.md`.
