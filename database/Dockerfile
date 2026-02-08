FROM postgres:16-alpine

ENV POSTGRES_DB=myapp \
    POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=postgres

COPY init.sql /docker-entrypoint-initdb.d/

EXPOSE 5432
