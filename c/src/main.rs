use port::api::create_router;
use std::net::SocketAddr;
use tokio;

#[tokio::main]
async fn main() {
    // Initialize logging
    env_logger::init();

    // Create the API router
    let app = create_router();

    // Define the address to bind to
    let addr = SocketAddr::from(([127, 0, 0, 1], 8080));
    println!("🚀 Backtest API server starting on http://{}", addr);

    // Start the server
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
