# api 계층 — node 표준 모듈만 사용 (AC-18)
FROM node:20-alpine
WORKDIR /srv
COPY server.js .
USER node
EXPOSE 8080
CMD ["node", "/srv/server.js"]
