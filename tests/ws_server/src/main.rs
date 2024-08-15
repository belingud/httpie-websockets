use std::{env};
use warp::Filter;
use warp::ws::{Message, WebSocket};
use futures_util::{StreamExt, SinkExt};
use serde_json;
use log::{info, error};
use serde_json::Value;
use std::net::SocketAddr;
use flexi_logger::{Logger};


async fn handle_ws(ws: WebSocket, addr: Option<SocketAddr>) {
    let client_addr = addr.map_or("unknown address".to_string(), |a| a.to_string());
    info!("New WebSocket connection from {}", client_addr);

    let (mut tx, mut rx) = ws.split();

    while let Some(result) = rx.next().await {
        match result {
            Ok(msg) => {
                info!("Received message from {}: {:?}", client_addr, msg);

                if msg.is_close() {
                    if let Ok(text) = msg.to_str() {
                        if let Ok(close_frame) = serde_json::from_str::<Value>(text) {
                            let close_reason = close_frame.get("reason").and_then(|v| v.as_str()).unwrap_or("");
                            let close_message = serde_json::json!({ "type": "close", "reason": close_reason });
                            let close_message = Message::text(close_message.to_string());

                            if tx.send(close_message).await.is_err() {
                                error!("Failed to send close message");
                            }
                            break;
                        }
                    }
                    info!("WebSocket connection closed by client {}", client_addr);
                }

                if tx.send(msg).await.is_err() {
                    error!("Client {} disconnected, stopping the handler", client_addr);
                    break;
                }
            }
            Err(e) => {
                error!("WebSocket error from client {}: {}", client_addr, e);
                break;
            }
        }
    }
}

#[tokio::main]
async fn main() {
    Logger::try_with_env_or_str("info")
        .unwrap()
        .format(|write, now, record| {
            let timestamp = now.now().format("%Y-%m-%d %H:%M:%S").to_string();
            writeln!(
                write,
                "[{}] [{}] - {}",
                timestamp,
                record.level(),
                record.args()
            )
        })
        .start()
        .unwrap();
    let port: u16 = env::var("PORT")
        .unwrap_or_else(|_| "8765".to_string())
        .parse()
        .expect("PORT must be a number");

    let routes = warp::path("ws")
        .and(warp::ws())
        .and(warp::addr::remote())
        .map(|ws: warp::ws::Ws, addr: Option<SocketAddr>| {
            ws.on_upgrade(move |socket| handle_ws(socket, addr))
        });
    info!("Starting server on port {}", port);
    warp::serve(routes)
        .run(([0, 0, 0, 0], port))
        .await;
}
