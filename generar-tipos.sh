#!/bin/bash
# Regenera frontend/src/api/schema.d.ts desde el openapi.json del backend.
set -euo pipefail

cd "$(dirname "$0")"

URL="${OPENAPI_URL:-http://localhost/api/v1/openapi.json}"
DESTINO="frontend/src/api/schema.d.ts"
CRUDO="frontend/.openapi.json"
NUEVO="frontend/.schema.d.ts.nuevo"

limpiar() { rm -f "$CRUDO" "$NUEVO"; }
trap limpiar EXIT

corriendo=$(docker compose ps --services --filter status=running)
for servicio in api web; do
    if ! grep -qFx "$servicio" <<<"$corriendo"; then
        echo "El servicio '$servicio' no está corriendo. Levantá el stack: docker compose up -d" >&2
        exit 1
    fi
done

echo "Bajando $URL"
if ! curl -fsS "$URL" -o "$CRUDO"; then
    echo "No se pudo bajar el schema. ¿El proxy está publicando el puerto 80?" >&2
    exit 1
fi

# Un 200 con HTML (por ejemplo el traceback de Django con DEBUG=True) no es un schema.
if [ "$(head -c 1 "$CRUDO")" != "{" ]; then
    echo "Lo que devolvió $URL no es JSON:" >&2
    head -c 200 "$CRUDO" >&2
    echo >&2
    exit 1
fi

echo "Generando los tipos"
docker compose exec -T web node_modules/.bin/openapi-typescript .openapi.json -o .schema.d.ts.nuevo

if [ ! -s "$NUEVO" ]; then
    echo "La generación no produjo nada; $DESTINO queda como estaba." >&2
    exit 1
fi

if cmp -s "$NUEVO" "$DESTINO"; then
    echo "$DESTINO ya estaba al día."
    exit 0
fi

# Se mueve recién ahora para que una generación a medias no deje el schema roto.
mv "$NUEVO" "$DESTINO"
echo "$DESTINO actualizado."
echo "Verificá que siga compilando: docker compose exec web node_modules/.bin/tsc -b"
