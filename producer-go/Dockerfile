# ---- build stage ----
FROM golang:1.22-alpine AS build
WORKDIR /app

COPY go.mod ./
COPY main.go ./

# No go.sum is committed — `go mod tidy` resolves and pins the one
# dependency (segmentio/kafka-go, pinned in go.mod) at build time.
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -o /producer .

# ---- run stage ----
FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=build /producer /producer

CMD ["/producer"]
