# ==============================================================================
# Dockerfile cho Frontend (React + Vite + TypeScript)
# Multi-stage build: Node.js để compile -> Nginx để serve static files
# ==============================================================================

# Stage 1: Build source code React
FROM node:20-alpine AS builder

WORKDIR /app

# Tối ưu Cache: Copy package files trước
COPY package*.json ./
RUN npm install

# Copy toàn bộ code và tiến hành build production
COPY . .
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Web Server Nginx (Siêu nhẹ, ~20MB)
FROM nginx:alpine AS final

# Áp dụng cấu hình SPA fallback cho Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build static files
COPY --from=builder /app/dist /usr/share/nginx/html

# Mở cổng 80 trong container
EXPOSE 80

# Chạy Nginx ở chế độ foreground
CMD ["nginx", "-g", "daemon off;"]
