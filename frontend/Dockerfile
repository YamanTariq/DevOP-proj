FROM nginx:alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/index.html frontend/login.html frontend/signup.html frontend/profile.html /usr/share/nginx/html/
COPY frontend/styles.css frontend/app.js /usr/share/nginx/html/

EXPOSE 80
