# Frontend: multi-stage build -- compile the Vite app, then serve the
# static output with nginx.
#
# Why nginx over a Node-based static server (e.g. `serve`): the final
# image needs no Node.js or build tooling at all, only the compiled
# dist/ output, on top of a small (~40MB), standard, battle-tested
# static file server. A SPA needs the same one addition either way --
# rewriting every unmatched path to index.html so React Router's
# client-side routes (e.g. /transactions/:id) work on a hard refresh --
# so nginx isn't meaningfully more complex than the alternative; see
# nginx.conf.

FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

# Vite env vars are baked in at BUILD time, not read at container
# runtime -- ARG->ENV is what makes docker-compose.yml's build.args
# actually reach `import.meta.env.VITE_API_BASE_URL` inside the bundle.
# IMPORTANT: this must be a URL the BROWSER can reach (localhost + the
# backend's published port), never a Docker-internal service hostname
# like http://backend:8000 -- the browser runs on the host machine, not
# inside the compose network. See .env.example.
ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
