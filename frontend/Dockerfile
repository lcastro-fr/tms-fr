FROM node:24-slim

ENV PNPM_HOME="/pnpm"
ENV COREPACK_HOME="/pnpm/corepack"
ENV npm_config_store_dir="/pnpm/store"
ENV PATH="$PNPM_HOME:$PATH"
ENV HOME=/tmp

RUN corepack enable
RUN corepack prepare pnpm@latest --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* .npmrc* ./

RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile

COPY . .

RUN mkdir -p /pnpm/store && chmod -R a+rwX /pnpm /app/node_modules

# vite directo, sin pnpm: `pnpm dev` revalida dependencias en cada arranque y pnpm exige
# que el store esté en el mismo filesystem que el proyecto, así que con /app bind-mounteado
# cae a /app/.pnpm-store e intenta reinstalar. Las dependencias las instala el build;
# agregar una pide `docker compose build web`.
CMD ["node_modules/.bin/vite", "--host"]
