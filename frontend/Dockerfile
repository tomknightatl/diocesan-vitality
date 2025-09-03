# Stage 1: Serve the application with Nginx
FROM nginx:1.25-alpine

# Copy the custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Remove the default Nginx index.html to ensure our built index.html is used
RUN rm /usr/share/nginx/html/index.html

# Copy the simple index.html
COPY index.html /usr/share/nginx/html/index.html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]