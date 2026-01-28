# Build stage
FROM node:18-alpine as build

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx template
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template

# Nginx will replace $PORT in the template at runtime
ENV PORT=8080
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
