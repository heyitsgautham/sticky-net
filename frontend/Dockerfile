# Frontend Dockerfile - Serve React app with nginx
FROM nginx:alpine

# Copy built React app to nginx
COPY build/ /usr/share/nginx/html/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 8080
EXPOSE 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
