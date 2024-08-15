################################################################################
# Build stage
FROM rust:1.80.0-slim as builder

WORKDIR /app

ENV RUSTUP_DIST_SERVER=https://rsproxy.cn
ENV RUSTUP_UPDATE_ROOT=https://rsproxy.cn/rustup
RUN rustup target add x86_64-unknown-linux-musl

COPY . .
RUN cargo build --release --target x86_64-unknown-linux-musl

################################################################################
# Run stage
FROM scratch

COPY --from=builder /app/target/x86_64-unknown-linux-musl/release/ws_server /app/ws_server

ENV PORT 8765
EXPOSE 8765

CMD ["/app/ws_server"]
