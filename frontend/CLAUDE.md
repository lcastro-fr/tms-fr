# TMS-FR — Frontend

SPA React para el TMS. Consume la API del backend Django que está en `../backend`.
El alcance por pasos, la topología y las convenciones que cruzan las dos capas viven en
`../CLAUDE.md`; **leer ese primero.** La arquitectura del backend y el detalle de la API
están en `../backend/CLAUDE.md`.

Stack: React 19 + TypeScript 6 + Vite 8. Mantine 9 (core, dates, form, hooks, modals,
notifications). TanStack Router 1 (file-based), Query 5, Table 8. axios 1. dayjs.

## Alcance

El frontend va detrás del backend, no delante. **Sólo se construyen pantallas para
endpoints que existen.** Nada de inventar rutas ni mockear respuestas para adelantar UI:
si falta el endpoint, el trabajo es en `../backend`.

Hoy la API tiene seis operaciones y cuatro son el CRUD de zonas (`/api/v1/zonas/`), así
que zonas es la única pantalla que se puede hacer de punta a punta. Tickets y órdenes de
servicio sólo tienen endpoints de escritura pensados para máquina (la ingesta desde SAP y
el cálculo de costo); les falta API de lectura.

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
  components/        formularios y vistas del dominio
  index.ts           la única superficie pública
```

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

Una sola instancia, con la config de CSRF que Django espera:

```ts
axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  xsrfCookieName: "csrftoken",      // default de axios: XSRF-TOKEN
  xsrfHeaderName: "X-CSRFToken",    // default de axios: X-XSRF-TOKEN
})
```

Esas dos últimas líneas parecen ruido y no lo son: axios ya sabe leer la cookie y mandar
el header, pero **sus defaults no son los de Django**. Sin sobreescribirlos el CSRF falla
sin mensaje. Con ellos no hace falta ningún helper para leer cookies.

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

Un 401 invalida la sesión y redirige a `/login` con el destino en search params.

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

## Auth — contrato, todavía no implementado

**Nada de esto existe aún.** La API hoy sólo acepta `X-API-Key`, que es el secreto
compartido con la integración SAP.

- **El `X-API-Key` no se toca desde el browser.** Autoriza escrituras y ponerlo en el
  bundle lo publica. Es exclusivamente machine-to-machine.
- Backend pendiente: `django_auth` de ninja + `POST /api/v1/auth/login`,
  `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`, y `CSRF_TRUSTED_ORIGINS`.
- Frontend: `features/auth/` con `meQueryOptions`, un `beforeLoad` en la ruta
  `_authenticated`, y `/login` como única ruta pública.

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
explota. Es la única razón por la que existe ese archivo.

El test que hay (`src/app/providers.test.tsx`) es un smoke test del árbol de providers:
verifica que Mantine renderice y que el `queryClient` llegue a los hijos. Es barato y
atrapa justo lo que es silencioso cuando se rompe.

## Pendientes conocidos

- **Falta la capa de API.** No existen `src/api/http.ts`, `errors.ts` ni `schema.d.ts`, así
  que todo lo que este documento dice sobre el cliente HTTP y el data fetching es contrato,
  no código. Es el paso siguiente, y depende de que el backend tenga API de lectura.
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
