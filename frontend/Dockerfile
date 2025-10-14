# syntax=docker/dockerfile:1

# 1) Build
FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# VITE_API_BASE is injected by compose at runtime; do not bake here
RUN npm run build-only

# 2) Serve static (tiny server)
FROM node:20
WORKDIR /app
RUN npm i -g serve
COPY --from=build /app/dist ./dist
# serve on 5173 to match your compose mapping
CMD ["serve", "-s", "dist", "-l", "5173"]
