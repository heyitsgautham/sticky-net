# Stage 1: build the React app with the locked dependencies
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --non-interactive

COPY . .

# CRA bakes REACT_APP_* values into the bundle at build time.
ARG REACT_APP_API_URL=http://localhost:8080
ARG REACT_APP_API_KEY=test-api-key
ENV REACT_APP_API_URL=$REACT_APP_API_URL \
    REACT_APP_API_KEY=$REACT_APP_API_KEY
RUN yarn build

# Stage 2: serve the static bundle with nginx
FROM nginx:alpine

COPY --from=build /app/build/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
