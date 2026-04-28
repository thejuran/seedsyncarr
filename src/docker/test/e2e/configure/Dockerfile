FROM alpine:3.19

RUN apk add --no-cache curl bash jq

WORKDIR /
ADD src/docker/wait-for-it.sh /
ADD src/docker/test/e2e/configure/setup_seedsyncarr.sh /

# Force rebuild 2026-01-21-v3
RUN echo "Cache bust: 2026-01-21-v3"

CMD ["/setup_seedsyncarr.sh"]