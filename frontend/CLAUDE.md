# TMS-FR — Frontend

SPA React para el TMS. Consume la API del backend Django que está en `../backend`.
El alcance por pasos, la topología y las convenciones que cruzan las dos capas viven en
`../CLAUDE.md`; **leer ese primero.** La arquitectura del backend y el detalle de la API
están en `../backend/CLAUDE.md`.

Stack: React 19 + TypeScript 6 + Vite 8. Mantine 9 (core, dates, form, hooks, modals,
notifications). TanStack Router 1 (file-based), Query 5, Table 8. axios 1. dayjs.
Leaflet 1.9 + react-leaflet 5 + geoman para el mapa de zonas.

## Alcance

El frontend va detrás del backend, no delante. **Sólo se construyen pantallas para
endpoints que existen.** Nada de inventar rutas ni mockear respuestas para adelantar UI:
si falta el endpoint, el trabajo es en `../backend`.

Hoy la API tiene veinticuatro operaciones: cuatro de auth, cinco del CRUD de zonas
(`/api/v1/zonas/`), dos de ubicaciones (`/api/v1/ubicaciones/`, lista con filtro y PUT), cinco de
órdenes de servicio (`/api/v1/ordenes-servicio/`: opciones, lista con filtros, detalle, PUT y el
POST del costo), siete de tarifarios (`/api/v1/tarifarios/`: opciones, lista con filtros, detalle,
POST, PUT, cierre de vigencia y DELETE) y una de máquina. Zonas, ubicaciones, órdenes de servicio
y tarifarios son las cuatro pantallas de dominio. Tickets sigue teniendo sólo la ingesta desde SAP,
que es máquina a máquina; le falta API de lectura.

## Arquitectura

```
src/
  app/         providers, theme, router, queryClient. Se arma una vez y no se toca.
  api/         schema.d.ts (generado), http.ts, errors.ts. Único lugar con axios.
  features/    una carpeta por app del backend
    catalog/         zonas, ubicaciones
    transportista/   tarifarios (con sus tarifas de flete y de concepto)
    logistica/       órdenes de servicio, costos
    tracking/        tickets, remitos
  routes/      file-based. Sólo composición.
  components/  UI compartida, sin conocimiento de dominio.
  lib/         date.ts, money.ts, geojson.ts
```

Anatomía de un feature:

```
features/catalog/
  api.ts             queryOptions y mutations. El único lugar que escribe URLs.
  zonas-columns.tsx  column defs de TanStack Table
  use-ubicaciones.ts la capa opcional de puntos: permiso + toggle + query
  components/        formularios y vistas del dominio
  index.ts           la única superficie pública
```

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
  - `DataTable` — lista simple, con selección de filas (`rowSelection`). Lo usan zonas y
    ubicaciones.
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
- Las **column defs viven en el feature**: qué columna, qué label y cómo se formatea un
  precio es conocimiento de dominio.
- El formateo pasa en la `cell`, usando `lib/money.ts` y `lib/date.ts`. Una columna de
  precio recibe el string del `Decimal`, nunca un número.
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
- **Una zona es un solo `Polygon`.** `pm:create` reemplaza la figura anterior, y `cutPolygon`
  está apagado: un corte que parte la zona en dos produce un `MultiPolygon` que
  `Zona.geom` no puede guardar. `drawCircle`/`drawCircleMarker` también están apagados porque
  exportan un `Point`.
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
- El template de tiles es una constante en `MapaBase`. La atribución de OSM es obligatoria por
  su licencia, y su servidor de tiles es una cortesía con política de uso: si el volumen crece,
  se cambia esa constante.

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

Los archivos de test cubren exactamente lo que es silencioso cuando se rompe:

- `src/app/providers.test.tsx` — smoke test del árbol de providers.
- `src/lib/date.test.ts` — el ida y vuelta entre el reloj de pared naive del picker y el ISO con
  offset del backend. Es el que más paga después de `geojson`: un ISO naive es 422 y un offset
  tomado de la zona del browser guarda la fecha corrida sin que nadie se entere.
- `src/lib/money.test.ts` — el formateo del `Decimal`-string, incluido el caso vacío que
  `Number("")` convierte en un `$ 0,00` que parece un precio real.
- `src/api/errors.test.ts` — el mapeo de `loc` a campo de formulario, sobre todo el caso
  anidado: dos filas de una lista tienen que escribir en dos campos distintos, y un error de
  fila entera no puede evaporarse.
- `rangoUltimoMes()` está cubierto en `date.test.ts`: que el extremo derecho sea **hoy** y no
  ayer, porque si no lo del día no se ve al entrar a la pantalla.
- `src/lib/geojson.test.ts` — las conversiones `[lng,lat]`↔`[lat,lng]` y el cierre de anillos.
  Es el que más paga: `lib/geojson.ts` no importa leaflet, y un polígono invertido se dibuja
  en otro continente sin tirar un error.
- `src/features/catalog/components/EditorPolygono.test.tsx` — el cableado de geoman: montar y
  desmontar con los modos activos, y que los eventos de edición lleguen al `onChange`. Monta
  Leaflet de verdad con un `getBoundingClientRect` falso.
- `src/components/SelectorPunto.test.tsx` — el click del mapa emite `[lng, lat]`, y el marcador
  es arrastrable y **no** usa el ícono default (`icon.options.iconUrl` tiene que ser `undefined`).

**El límite de jsdom con el mapa:** nada que use el renderer de canvas se puede testear —
`getContext()` devuelve `null` y muere en `clearRect`. Por eso el error de `classList` de
`preferCanvas` no se reproduce headless aunque su mecanismo esté entendido. Estos tests cubren
el cableado, no el render.

## Pendientes conocidos

- **Hay cuatro pantallas de dominio: `/zonas`, `/ubicaciones`, `/ordenes-servicio` y
  `/tarifarios`.** Zonas tiene
  alta, edición y baja con mapa, más la capa opcional de puntos. Ubicaciones tiene **sólo
  edición** —nacen de la ingesta de SAP— con dos filtros (pendientes de validar, sin coordenada)
  y el punto elegido en el mapa. Órdenes de servicio también es **sólo edición**, por lo mismo:
  búsqueda por número de ticket o remito, rango de fecha de viaje, tres switches, la columna de
  ticket, el detalle con tickets y remitos, y el cálculo del costo. Tarifarios es el CRUD
  completo, y el único con alta propia.
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
- **La tabla de ubicaciones no tiene búsqueda por texto.** Son ~1785 filas en 90 páginas de 20,
  así que encontrar un código puntual es incómodo. Los dos componentes de tabla ya cablean
  `getFilteredRowModel()` pero ninguno expone estado de `globalFilter`; agregarlo es client-side
  y sin costo de backend.
- **Editar una ubicación la marca como validada**, y por eso el botón dice "Guardar y validar".
  La dirección se muestra read-only: es la referencia para saber dónde va el punto, pero
  corregirla sería re-geolocalizar y el upsert de SAP la vuelve a traer.
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
