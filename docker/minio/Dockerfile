# Plano B: compila o MinIO a partir do código-fonte oficial (GitHub), na mesma
# versão usada pelo projeto, para quando a imagem pronta não puder ser baixada.
FROM golang:1.24-alpine AS build

ARG MINIO_TAG=RELEASE.2025-02-03T21-03-04Z
RUN apk add --no-cache git
RUN git clone --depth 1 --branch ${MINIO_TAG} https://github.com/minio/minio.git /src
WORKDIR /src
RUN CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o /out/minio .

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=build /out/minio /usr/bin/minio
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
