// Core modules
pub mod core {
    pub mod r#const;
    pub mod params;
}

// Data processing modules
pub mod data {
    pub mod data;
    pub mod indicators;
    pub mod signals;
}

// Trading engine modules
pub mod trading {
    pub mod constraints;
    pub mod portfolio;
    pub mod position;
    pub mod strategy;
    pub mod trade;
}

// Analysis modules
pub mod analysis {
    pub mod backtest;
}

// Utility modules
pub mod utils {
    pub mod utils;
}

// API modules
pub mod api;

// Re-export commonly used items at the crate root
pub use analysis::*;
pub use core::*;
pub use data::*;
pub use trading::*;
