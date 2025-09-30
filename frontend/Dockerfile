# Stage 1: Build the React application
FROM node:20-alpine AS build

WORKDIR /app

# Copy package.json and package-lock.json and install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:1.25-alpine

# Copy the custom Nginx configuration template
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Remove the default Nginx index.html to ensure our built index.html is used
RUN rm /usr/share/nginx/html/index.html

# Copy the built static files from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Set default namespace if not provided
ENV NAMESPACE=diocesan-vitality-dev

# Expose port 80
EXPOSE 80

# Start Nginx with environment variable substitution
CMD ["nginx", "-g", "daemon off;"]
