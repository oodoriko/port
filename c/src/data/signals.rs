use crate::indicators::*;
use crate::params::SignalParams;
use crate::r#const::{MAX_ASSETS, MAX_SIGNALS_PER_ASSET};
use arrayvec::ArrayVec;
use smallvec::SmallVec;

#[derive(Debug, Clone)]
pub struct OhlcData {
    pub open: f32,
    pub high: f32,
    pub low: f32,
    pub close: f32,
}

pub trait SingleAssetSignal: Send {
    fn update(&mut self, _open: f32, _high: f32, _low: f32, close: f32);
    fn get_signal(&self) -> i8;
    fn name(&self) -> &str;
}

// strategy 1, ema_fm__ris_neu__macd_bull
pub struct EmaRsiMacdSignal {
    name: String,
    ema: Ema,
    rsi: Rsi,
    macd: Macd,
}

impl EmaRsiMacdSignal {
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::EmaRsiMacd {
            ema_fast,
            ema_medium,
            ema_slow,
            rsi_period,
            initial_close,
            rsi_ob,
            rsi_os,
            rsi_bull_div,
            macd_fast,
            macd_slow,
            macd_signal,
        } = params
        {
            Some(Self {
                name: "ema_fm__ris_neu__macd_bull".to_string(),
                ema: Ema::new(*ema_fast, *ema_medium, *ema_slow, *initial_close),
                rsi: Rsi::new(*rsi_period, *initial_close, *rsi_ob, *rsi_os, *rsi_bull_div),
                macd: Macd::new(*macd_fast, *macd_slow, *macd_signal, *initial_close, 0, 0.0),
            })
        } else {
            None
        }
    }
}

impl SingleAssetSignal for EmaRsiMacdSignal {
    fn update(&mut self, _open: f32, _high: f32, _low: f32, close: f32) {
        self.ema.update(close);
        self.rsi.update(close);
        self.macd.update(close);
    }
    fn get_signal(&self) -> i8 {
        self.ema.ema_f_m() & self.rsi.rsi_neutral() & self.macd.macd_bullish()
    }
    fn name(&self) -> &str {
        &self.name
    }
}

// strategy 2, bb_below_lower__ris_os
pub struct BbRsiOversoldSignal<const N: usize> {
    name: String,
    bb: BollingerBands<N>,
    rsi: Rsi,
    current_price: f32,
    current_lower: f32,
}

impl<const N: usize> BbRsiOversoldSignal<N> {
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::BbRsiOversold {
            name,
            std_dev,
            rsi_period,
            initial_close,
            rsi_ob,
            rsi_os,
            rsi_bull_div,
        } = params
        {
            let mut bb = BollingerBands::new(*std_dev, *initial_close as f32);
            let (_middle, _upper, lower) = bb.update(*initial_close as f32);
            Some(Self {
                name: name.clone(),
                bb,
                rsi: Rsi::new(*rsi_period, *initial_close, *rsi_ob, *rsi_os, *rsi_bull_div),
                current_price: *initial_close,
                current_lower: lower as f32,
            })
        } else {
            None
        }
    }
}

impl<const N: usize> SingleAssetSignal for BbRsiOversoldSignal<N> {
    fn update(&mut self, _open: f32, _high: f32, _low: f32, close: f32) {
        let (_middle, _upper, lower) = self.bb.update(close);
        self.current_lower = lower;
        self.current_price = close;
        self.rsi.update(close);
    }
    fn get_signal(&self) -> i8 {
        (self
            .bb
            .bb_below_lower(self.current_price, self.current_lower) as i8)
            & (self.rsi.rsi_os() as i8)
    }
    fn name(&self) -> &str {
        &self.name
    }
}

// strategy 3, bb_above_upper__ris_ob
pub struct BbRsiOverboughtSignal<const N: usize> {
    name: String,
    bb: BollingerBands<N>,
    rsi: Rsi,
    current_price: f32,
    current_upper: f32,
}

impl<const N: usize> BbRsiOverboughtSignal<N> {
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::BbRsiOverbought {
            name,
            std_dev,
            initial_close,
            rsi_period,
            rsi_ob,
            rsi_os,
            rsi_bull_div,
        } = params
        {
            let mut bb = BollingerBands::new(*std_dev, *initial_close);
            let (_middle, upper, _lower) = bb.update(*initial_close);
            Some(Self {
                name: name.clone(),
                bb,
                rsi: Rsi::new(*rsi_period, *initial_close, *rsi_ob, *rsi_os, *rsi_bull_div),
                current_price: *initial_close,
                current_upper: upper,
            })
        } else {
            None
        }
    }
}

impl<const N: usize> SingleAssetSignal for BbRsiOverboughtSignal<N> {
    fn update(&mut self, _open: f32, _high: f32, _low: f32, close: f32) {
        let (_middle, upper, _lower) = self.bb.update(close);
        self.current_upper = upper;
        self.current_price = close;
        self.rsi.update(close);
    }
    fn get_signal(&self) -> i8 {
        (self
            .bb
            .bb_above_upper(self.current_price, self.current_upper) as i8)
            & (self.rsi.rsi_ob() as i8)
    }
    fn name(&self) -> &str {
        &self.name
    }
}

// strategy 4, res_breakout__ris_lt80__macd_bull
pub struct PatternRsiMacdSignal<const SR: usize, const PAT: usize> {
    name: String,
    pattern: PatternSignals<SR, PAT>,
    rsi: Rsi,
    macd: Macd,
    current_price: f32,
    current_rsi: f32,
}

impl<const SR: usize, const PAT: usize> PatternRsiMacdSignal<SR, PAT> {
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::PatternRsiMacd {
            name,
            resistance_threshold,
            support_threshold,
            initial_high,
            initial_low,
            initial_close,
            rsi_period,
            rsi_ob,
            rsi_os,
            rsi_bull_div,
            macd_fast,
            macd_slow,
            macd_signal,
        } = params
        {
            Some(Self {
                name: name.clone(),
                pattern: PatternSignals::new(
                    *resistance_threshold,
                    *support_threshold,
                    *initial_high,
                    *initial_low,
                ),
                rsi: Rsi::new(*rsi_period, *initial_close, *rsi_ob, *rsi_os, *rsi_bull_div),
                macd: Macd::new(*macd_fast, *macd_slow, *macd_signal, *initial_close, 0, 0.0),
                current_price: *initial_close,
                current_rsi: 50.0,
            })
        } else {
            None
        }
    }
}

impl<const SR: usize, const PAT: usize> SingleAssetSignal for PatternRsiMacdSignal<SR, PAT> {
    fn update(&mut self, _open: f32, high: f32, low: f32, close: f32) {
        self.pattern.update(high, low);
        self.rsi.update(close);
        self.macd.update(close);
        self.current_price = close;
        self.current_rsi = self.rsi.get_value();
    }
    fn get_signal(&self) -> i8 {
        self.pattern.resistance_breakout(self.current_price)
            & (self.current_rsi < 80.0) as i8
            & self.macd.macd_bullish()
    }
    fn name(&self) -> &str {
        &self.name
    }
}

// strategy 5, triple_ema_pattern_macd_rsi
pub struct TripleEmaPatternMacdRsiSignal<const SR: usize, const PAT: usize> {
    name: String,
    ema: Ema,
    pattern: PatternSignals<SR, PAT>,
    macd: Macd,
    rsi: Rsi,
}

impl<const SR: usize, const PAT: usize> TripleEmaPatternMacdRsiSignal<SR, PAT> {
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::TripleEmaPatternMacdRsi {
            name,
            ema_fast,
            ema_medium,
            ema_slow,
            resistance_threshold,
            support_threshold,
            initial_high,
            initial_low,
            initial_close,
            macd_fast,
            macd_slow,
            macd_signal,
            rsi_period,
            rsi_ob,
            rsi_os,
            rsi_bull_div,
        } = params
        {
            Some(Self {
                name: name.clone(),
                ema: Ema::new(*ema_fast, *ema_medium, *ema_slow, *initial_close),
                pattern: PatternSignals::new(
                    *resistance_threshold,
                    *support_threshold,
                    *initial_high,
                    *initial_low,
                ),
                macd: Macd::new(*macd_fast, *macd_slow, *macd_signal, *initial_close, 0, 0.0),
                rsi: Rsi::new(*rsi_period, *initial_close, *rsi_ob, *rsi_os, *rsi_bull_div),
            })
        } else {
            None
        }
    }
}

impl<const SR: usize, const PAT: usize> SingleAssetSignal
    for TripleEmaPatternMacdRsiSignal<SR, PAT>
{
    fn update(&mut self, _open: f32, high: f32, low: f32, close: f32) {
        self.ema.update(close);
        self.pattern.update(high, low);
        self.macd.update(close);
        self.rsi.update(close);
    }
    fn get_signal(&self) -> i8 {
        self.ema.ema_triple_bull()
            & self.pattern.uptrend_pattern()
            & self.macd.macd_bullish()
            & !(self.rsi.rsi_ob())
    }
    fn name(&self) -> &str {
        &self.name
    }
}

// strategy 6, bb_squeeze_breakout
pub struct BbSqueezeBreakoutSignal<const N: usize> {
    name: String,
    bb: BollingerBands<N>,
    macd: Macd,
    current_price: f32,
    current_upper: f32,
    current_lower: f32,
    current_middle: f32,
    current_squeeze_threshold: f32,
}

impl<const N: usize> BbSqueezeBreakoutSignal<N> {
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::BbSqueezeBreakout {
            name,
            std_dev,
            initial_close,
            macd_fast,
            macd_slow,
            macd_signal,
        } = params
        {
            let mut bb = BollingerBands::new(*std_dev, *initial_close);
            let (middle, upper, lower) = bb.update(*initial_close);
            Some(Self {
                name: name.clone(),
                bb,
                macd: Macd::new(*macd_fast, *macd_slow, *macd_signal, *initial_close, 0, 0.0),
                current_price: *initial_close,
                current_upper: upper,
                current_lower: lower,
                current_middle: middle,
                current_squeeze_threshold: 0.02,
            })
        } else {
            None
        }
    }
}

impl<const N: usize> SingleAssetSignal for BbSqueezeBreakoutSignal<N> {
    fn update(&mut self, _open: f32, _high: f32, _low: f32, close: f32) {
        let (middle, upper, lower) = self.bb.update(close);
        self.current_upper = upper;
        self.current_lower = lower;
        self.current_middle = middle;
        self.current_price = close;
        self.macd.update(close);
    }
    fn get_signal(&self) -> i8 {
        (self.bb.bb_squeeze(
            self.current_upper,
            self.current_lower,
            self.current_middle,
            self.current_squeeze_threshold,
        ) as i8)
            & (self
                .bb
                .bb_above_upper(self.current_price, self.current_upper) as i8)
            & (self.macd.macd_bullish() as i8)
    }
    fn name(&self) -> &str {
        &self.name
    }
}

// strategy 7, ris_os__ema_price_m
pub struct RsiOversoldReversalSignal {
    name: String,
    rsi: Rsi,
    ema: Ema,
}

impl RsiOversoldReversalSignal {
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::RsiOversoldReversal {
            name,
            rsi_period,
            initial_close,
            rsi_ob,
            rsi_os,
            rsi_bull_div,
            ema_fast,
            ema_medium,
            ema_slow,
        } = params
        {
            Some(Self {
                name: name.clone(),
                rsi: Rsi::new(*rsi_period, *initial_close, *rsi_ob, *rsi_os, *rsi_bull_div),
                ema: Ema::new(*ema_fast, *ema_medium, *ema_slow, *initial_close),
            })
        } else {
            None
        }
    }
}

impl SingleAssetSignal for RsiOversoldReversalSignal {
    fn update(&mut self, _open: f32, _high: f32, _low: f32, close: f32) {
        self.rsi.update(close);
        self.ema.update(close);
    }
    fn get_signal(&self) -> i8 {
        self.rsi.rsi_os() & self.ema.ema_price_m()
    }
    fn name(&self) -> &str {
        &self.name
    }
}

// strategy 8, sup_bounce__macd_bull
pub struct SupportBounceSignal<const SR: usize, const PAT: usize> {
    name: String,
    pattern: PatternSignals<SR, PAT>,
    macd: Macd,
    current_price: f32,
}

impl<const SR: usize, const PAT: usize> SupportBounceSignal<SR, PAT> {
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::SupportBounce {
            name,
            resistance_threshold,
            support_threshold,
            initial_high,
            initial_low,
            initial_close,
            macd_fast,
            macd_slow,
            macd_signal,
        } = params
        {
            Some(Self {
                name: name.clone(),
                pattern: PatternSignals::new(
                    *resistance_threshold,
                    *support_threshold,
                    *initial_high,
                    *initial_low,
                ),
                macd: Macd::new(*macd_fast, *macd_slow, *macd_signal, *initial_close, 0, 0.0),
                current_price: *initial_close,
            })
        } else {
            None
        }
    }
}

impl<const SR: usize, const PAT: usize> SingleAssetSignal for SupportBounceSignal<SR, PAT> {
    fn update(&mut self, _open: f32, high: f32, low: f32, close: f32) {
        self.pattern.update(high, low);
        self.macd.update(close);
        self.current_price = close;
    }
    fn get_signal(&self) -> i8 {
        (self.pattern.near_support(self.current_price) as i8) & (self.macd.macd_bullish() as i8)
    }
    fn name(&self) -> &str {
        &self.name
    }
}

// strategy 9, upt_pat__ris_lt80
pub struct UptrendPatternSignal<const SR: usize, const PAT: usize> {
    name: String,
    ema: Ema,
    pattern: PatternSignals<SR, PAT>,
    rsi: Rsi,
}

impl<const SR: usize, const PAT: usize> UptrendPatternSignal<SR, PAT> {
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::UptrendPattern {
            name,
            ema_fast,
            ema_medium,
            ema_slow,
            initial_close,
            resistance_threshold,
            support_threshold,
            initial_high,
            initial_low,
            rsi_period,
            rsi_ob,
            rsi_os,
            rsi_bull_div,
        } = params
        {
            Some(Self {
                name: name.clone(),
                ema: Ema::new(*ema_fast, *ema_medium, *ema_slow, *initial_close),
                pattern: PatternSignals::new(
                    *resistance_threshold,
                    *support_threshold,
                    *initial_high,
                    *initial_low,
                ),
                rsi: Rsi::new(*rsi_period, *initial_close, *rsi_ob, *rsi_os, *rsi_bull_div),
            })
        } else {
            None
        }
    }
}

impl<const SR: usize, const PAT: usize> SingleAssetSignal for UptrendPatternSignal<SR, PAT> {
    fn update(&mut self, _open: f32, high: f32, low: f32, close: f32) {
        self.ema.update(close);
        self.pattern.update(high, low);
        self.rsi.update(close);
    }
    fn get_signal(&self) -> i8 {
        self.ema.ema_triple_bull() & self.pattern.uptrend_pattern() & !(self.rsi.rsi_ob())
    }
    fn name(&self) -> &str {
        &self.name
    }
}

// strategy 10, stoch_os__ema_price_m
pub struct StochOversoldSignal<const N: usize, const K: usize, const D: usize> {
    name: String,
    stoch: StochasticOscillator<N, K, D>,
    ema_fast: _Ema,
    ema_slow: _Ema,
    current_oversold: f32,
}

impl<const N: usize, const K: usize, const D: usize> StochOversoldSignal<N, K, D> {
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::StochOversold {
            name,
            initial_high,
            initial_low,
            initial_close,
            ema_fast_period,
            ema_slow_period,
            oversold,
        } = params
        {
            Some(Self {
                name: name.clone(),
                stoch: StochasticOscillator::new(*initial_high, *initial_low, *initial_close),
                ema_fast: _Ema::new(*ema_fast_period, *initial_close),
                ema_slow: _Ema::new(*ema_slow_period, *initial_close),
                current_oversold: *oversold,
            })
        } else {
            None
        }
    }
}

impl<const N: usize, const K: usize, const D: usize> SingleAssetSignal
    for StochOversoldSignal<N, K, D>
{
    fn update(&mut self, _open: f32, high: f32, low: f32, close: f32) {
        self.stoch.update(high, low, close);
        self.ema_fast._update(close);
        self.ema_slow._update(close);
    }
    fn get_signal(&self) -> i8 {
        (self.stoch.stoch_oversold(self.current_oversold) as i8)
            & ((self.ema_fast.get() > self.ema_slow.get()) as i8)
    }
    fn name(&self) -> &str {
        &self.name
    }
}

////////////////////////////////////////////////////////////
// Signal Generator
////////////////////////////////////////////////////////////
pub enum SignalType {
    EmaRsiMacd,
    BbRsiOversold,
    BbRsiOverbought,
    PatternRsiMacd,
    TripleEmaPatternMacdRsi,
    BbSqueezeBreakout,
    RsiOversoldReversal,
    SupportBounce,
    UptrendPattern,
    StochOversold,
}

impl SignalType {
    pub fn from_name(name: &str) -> Option<Self> {
        match name {
            "ema_rsi_macd" => Some(SignalType::EmaRsiMacd),
            "bb_rsi_oversold" => Some(SignalType::BbRsiOversold),
            "bb_rsi_overbought" => Some(SignalType::BbRsiOverbought),
            "pattern_rsi_macd" => Some(SignalType::PatternRsiMacd),
            "triple_ema_pattern_macd_rsi" => Some(SignalType::TripleEmaPatternMacdRsi),
            "bb_squeeze_breakout" => Some(SignalType::BbSqueezeBreakout),
            "rsi_oversold_reversal" => Some(SignalType::RsiOversoldReversal),
            "support_bounce" => Some(SignalType::SupportBounce),
            "uptrend_pattern" => Some(SignalType::UptrendPattern),
            "stoch_oversold" => Some(SignalType::StochOversold),
            _ => None,
        }
    }
}

pub struct SignalGenerator {
    pub signals:
        ArrayVec<SmallVec<[Box<dyn SingleAssetSignal>; MAX_SIGNALS_PER_ASSET]>, MAX_ASSETS>,
    n_assets: usize,
}

impl SignalGenerator {
    pub fn new(n_assets: usize) -> Self {
        assert!(n_assets <= MAX_ASSETS, "Too many assets");
        let mut signals = ArrayVec::new();
        for _ in 0..n_assets {
            signals.push(SmallVec::new());
        }

        Self { signals, n_assets }
    }

    pub fn add_signal(&mut self, asset_idx: usize, signal: Box<dyn SingleAssetSignal>) {
        assert!(asset_idx < self.n_assets, "Asset index out of bounds");
        assert!(
            self.signals[asset_idx].len() < MAX_SIGNALS_PER_ASSET,
            "Too many signals for asset {}",
            asset_idx
        );
        self.signals[asset_idx].push(signal);
    }

    #[inline]
    pub fn update(&mut self, data: Vec<Vec<f32>>) {
        assert!(
            data.len() >= self.n_assets,
            "Not enough OHLC data for all assets"
        );

        for (asset_idx, asset_signals) in self.signals.iter_mut().enumerate() {
            if asset_idx < data.len() {
                let asset_data = &data[asset_idx];
                for signal in asset_signals.iter_mut() {
                    signal.update(asset_data[0], asset_data[1], asset_data[2], asset_data[3]);
                }
            }
        }
    }

    pub fn generate_signals(&self) -> Vec<i8> {
        let mut results = Vec::with_capacity(self.n_assets);

        for asset_signals in self.signals.iter() {
            if asset_signals.is_empty() {
                results.push(0);
                continue;
            }

            let signals: Vec<i8> = asset_signals
                .iter()
                .map(|signal| signal.get_signal())
                .collect();

            let final_signal = self.plurality_vote(&signals);
            results.push(final_signal);
        }

        results
    }

    #[inline]
    fn plurality_vote(&self, signals: &[i8]) -> i8 {
        if signals.is_empty() {
            return 0;
        }

        let mut counts = [0i32; 3]; // [-1, 0, 1] -> [0, 1, 2]
        for &signal in signals {
            counts[(signal + 1) as usize] += 1;
        }

        let mut max_count = counts[0];
        let mut max_idx = 0;
        let mut is_tie = false;

        for i in 1..3 {
            if counts[i] > max_count {
                max_count = counts[i];
                max_idx = i;
                is_tie = false;
            } else if counts[i] == max_count {
                is_tie = true;
            }
        }

        if is_tie {
            0
        } else {
            (max_idx as i8) - 1
        }
    }
}

// Helper function to create signals from params
pub fn create_signal_from_params(params: &SignalParams) -> Option<Box<dyn SingleAssetSignal>> {
    match params {
        SignalParams::EmaRsiMacd { .. } => {
            EmaRsiMacdSignal::from_params(params).map(|s| Box::new(s) as Box<dyn SingleAssetSignal>)
        }
        SignalParams::BbRsiOversold { .. } => BbRsiOversoldSignal::<20>::from_params(params)
            .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>),
        SignalParams::BbRsiOverbought { .. } => BbRsiOverboughtSignal::<20>::from_params(params)
            .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>),
        SignalParams::PatternRsiMacd { .. } => PatternRsiMacdSignal::<20, 10>::from_params(params)
            .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>),
        SignalParams::TripleEmaPatternMacdRsi { .. } => {
            TripleEmaPatternMacdRsiSignal::<20, 10>::from_params(params)
                .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>)
        }
        SignalParams::BbSqueezeBreakout { .. } => {
            BbSqueezeBreakoutSignal::<20>::from_params(params)
                .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>)
        }
        SignalParams::RsiOversoldReversal { .. } => RsiOversoldReversalSignal::from_params(params)
            .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>),
        SignalParams::SupportBounce { .. } => SupportBounceSignal::<20, 10>::from_params(params)
            .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>),
        SignalParams::UptrendPattern { .. } => UptrendPatternSignal::<20, 10>::from_params(params)
            .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>),
        SignalParams::StochOversold { .. } => StochOversoldSignal::<14, 3, 3>::from_params(params)
            .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>),
    }
}
