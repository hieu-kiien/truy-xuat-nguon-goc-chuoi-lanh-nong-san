FROM node:24-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_ENABLE_DEMO_LOGIN=false
ENV VITE_ENABLE_DEMO_LOGIN=$VITE_ENABLE_DEMO_LOGIN

RUN npm run build

FROM nginx:alpine AS final

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
