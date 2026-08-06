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

Hoy la API tiene doce operaciones: cuatro de auth, cinco del CRUD de zonas
(`/api/v1/zonas/`), la lista de ubicaciones (`/api/v1/ubicaciones/`) y dos de máquina. Zonas es
la única pantalla de dominio que se puede hacer de punta a punta, y ubicaciones alcanza para la
capa de puntos del mapa pero no para una pantalla propia. Tickets y órdenes de servicio sólo
tienen endpoints de escritura pensados para máquina (la ingesta desde SAP y el cálculo de
costo); les falta API de lectura.

## Arquitectura

```
src/
  app/         providers, theme, router, queryClient. Se arma una vez y no se toca.
  api/         schema.d.ts (generado), http.ts, errors.ts. Único lugar con axios.
  features/    una carpeta por app del backend
    catalog/         zonas, ubicaciones
    transportista/   transportistas, tarifarios
    logistica/       órdenes de servicio, costos
    tracking/        tickets, remitos
  routes/      file-based. Sólo composición.
  components/  UI compartida, sin conocimiento de dominio.
  lib/         date.ts, money.ts, format.ts
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
  y sólo para formatear. Nunca aritmética de pesos en float.
- **Toda fecha que sale lleva offset explícito.** El backend exige `AwareDatetime`: un ISO
  naive es 422. La conversión a hora de Buenos Aires pasa sólo en el borde de
  presentación, en `lib/date.ts`.
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
de Mantine.

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

- **TanStack Table es la lógica, Mantine es el markup.** Un `DataTable` genérico en
  `components/` recibe `columns` + `data` y renderiza con `<Table>` de Mantine. Nada de
  `<table>` a mano en un feature.
- Las **column defs viven en el feature**: qué columna, qué label y cómo se formatea un
  precio es conocimiento de dominio.
- El formateo pasa en la `cell`, usando `lib/money.ts` y `lib/date.ts`. Una columna de
  precio recibe el string del `Decimal`, nunca un número.
- **Hoy todo es client-side** (`getSortedRowModel`, `getFilteredRowModel`,
  `getPaginationRowModel`). Es correcto: la API no tiene paginación ni filtros y
  `list[ZonaOut]` es el array completo.
- Cuando el backend gane paginación y sus DTOs `...Filters`, se pasa a `manualPagination`
  / `manualSorting` / `manualFiltering`, y el estado de la tabla sube a los search params
  de la ruta para volverse la entrada del `queryOptions`. Está escrito acá para que sea
  una migración prevista y no un refactor sorpresa.

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
- **`CircleMarker`, no `Marker`.** El ícono default de Leaflet resuelve su URL en runtime y
  bajo un bundler da 404: marcadores invisibles, sin error. `CircleMarker` es un `<circle>` y
  no usa imágenes.
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
lo publica. Quedó sólo para la ingesta desde SAP; `/zonas/` ya no lo acepta.

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

Regenerar los tipos de la API, con el backend levantado:

```bash
pnpm dlx openapi-typescript http://localhost/api/v1/openapi.json -o src/api/schema.d.ts
```

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

Los tres archivos de test cubren exactamente lo que es silencioso cuando se rompe:

- `src/app/providers.test.tsx` — smoke test del árbol de providers.
- `src/lib/geojson.test.ts` — las conversiones `[lng,lat]`↔`[lat,lng]` y el cierre de anillos.
  Es el que más paga: `lib/geojson.ts` no importa leaflet, y un polígono invertido se dibuja
  en otro continente sin tirar un error.
- `src/features/catalog/components/EditorPolygono.test.tsx` — el cableado de geoman: montar y
  desmontar con los modos activos, y que los eventos de edición lleguen al `onChange`. Monta
  Leaflet de verdad con un `getBoundingClientRect` falso.

**El límite de jsdom con el mapa:** nada que use el renderer de canvas se puede testear —
`getContext()` devuelve `null` y muere en `clearRect`. Por eso el error de `classList` de
`preferCanvas` no se reproduce headless aunque su mecanismo esté entendido. Estos tests cubren
el cableado, no el render.

## Pendientes conocidos

- **`/zonas` es la única pantalla de dominio.** Alta, edición y baja con mapa, más la capa
  opcional de ubicaciones. No hay pantalla de ubicaciones: la API es sólo lista.
- **Las ubicaciones no se paginan ni se filtran del lado del servidor**, así que la capa baja
  las 1785 filas del seed y descarta en el cliente las que no tienen coordenadas — mostrando
  cuántas fueron, que es lo que evita que sea un descarte silencioso. Cuando el backend gane
  `UbicacionesFilters`, el filtro se va para allá.
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
