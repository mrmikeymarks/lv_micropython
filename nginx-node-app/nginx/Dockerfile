# nginx reverse-proxy image with the site config baked in
FROM nginx:1.27-alpine

# Replace the default server config with our reverse-proxy config
RUN rm /etc/nginx/conf.d/default.conf
COPY default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
