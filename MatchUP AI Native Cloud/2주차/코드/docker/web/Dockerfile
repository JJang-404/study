# web 계층 — nginx + 정적 페이지 + api 프록시 (AC-17)
# 공식 nginx 이미지는 /etc/nginx/templates/*.template 의 ${VAR}를 기동 시 치환한다.
FROM nginx:1.27-alpine
ENV API_UPSTREAM=http://api:8080
COPY index.html /usr/share/nginx/html/index.html
COPY default.conf.template /etc/nginx/templates/default.conf.template
EXPOSE 80
