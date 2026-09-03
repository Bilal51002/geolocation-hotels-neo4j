# ============================================================
# ÉTAPE 1 : COMPILATION DE L'APPLICATION REACT AVEC VITE
# ============================================================

FROM node:20-alpine AS build

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

# ============================================================
# ÉTAPE 2 : SERVIR LES FICHIERS STATIQUES AVEC NGINX
# ============================================================

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
