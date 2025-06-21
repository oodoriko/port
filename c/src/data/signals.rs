use crate::core::params::SignalParams;
use crate::data::indicators::*;
use arrayvec::ArrayVec;
use smallvec::SmallVec;

const MAX_SIGNALS_PER_ASSET: usize = 16;
const MAX_ASSETS: usize = 64;

#[derive(Debug, Clone, Copy)]
pub struct OhlcData {
    pub open: f32,
    pub high: f32,
    pub low: f32,
    pub close: f32,
}

pub trait SingleAssetSignal: Send {
    fn update(&mut self, _open: f32, _high: f32, _low: f32, close: f32);
    fn get_signal(&self) -> i8;
    fn name(&self) -> &'static str;
}

#[repr(align(32))]
pub struct EmaRsiMacdSignal {
    name: &'static str,
    ema: Ema,
    rsi: Rsi,
    macd: Macd,
}

impl EmaRsiMacdSignal {
    #[inline(always)]
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::EmaRsiMacd {
            ema_fast,
            ema_medium,
            ema_slow,
            rsi_period,
            macd_fast,
            macd_slow,
            macd_signal,
            rsi_ob,
            rsi_os,
            rsi_bull_div,
            ..
        } = params
        {
            Some(Self {
                name: "ema_rsi_macd",
                ema: Ema::new_triple_uninitialized(*ema_fast, *ema_medium, *ema_slow),
                rsi: Rsi::new_uninitialized(*rsi_period, *rsi_ob, *rsi_os, *rsi_bull_div),
                macd: Macd::new_uninitialized(*macd_fast, *macd_slow, *macd_signal, 0, 0.0),
            })
        } else {
            None
        }
    }
}

impl SingleAssetSignal for EmaRsiMacdSignal {
    #[inline(always)]
    fn update(&mut self, _open: f32, _high: f32, _low: f32, close: f32) {
        self.ema.update(close);
        self.rsi.update(close);
        self.macd.update(close);
    }

    #[inline(always)]
    fn get_signal(&self) -> i8 {
        self.ema.ema_f_m() & self.rsi.rsi_neutral() & self.macd.macd_bullish()
    }

    #[inline(always)]
    fn name(&self) -> &'static str {
        self.name
    }
}

#[repr(align(32))]
pub struct BbRsiOversoldSignal<const N: usize> {
    name: &'static str,
    bb: BollingerBands<N>,
    rsi: Rsi,
    current_price: f32,
    current_lower: f32,
}

impl<const N: usize> BbRsiOversoldSignal<N> {
    #[inline(always)]
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::BbRsiOversold {
            std_dev,
            rsi_period,
            rsi_os,
            rsi_bull_div,
            ..
        } = params
        {
            Some(Self {
                name: "bb_rsi_oversold",
                bb: BollingerBands::new_uninitialized(*std_dev),
                rsi: Rsi::new_uninitialized(*rsi_period, 70.0, *rsi_os, *rsi_bull_div),
                current_price: 0.0,
                current_lower: 0.0,
            })
        } else {
            None
        }
    }
}

impl<const N: usize> SingleAssetSignal for BbRsiOversoldSignal<N> {
    #[inline(always)]
    fn update(&mut self, _open: f32, _high: f32, _low: f32, close: f32) {
        let (_upper, _middle, lower) = self.bb.update(close);
        self.current_lower = lower;
        self.current_price = close;
        self.rsi.update(close);
    }

    #[inline(always)]
    fn get_signal(&self) -> i8 {
        self.bb
            .bb_below_lower(self.current_price, self.current_lower)
            & self.rsi.rsi_os()
    }

    #[inline(always)]
    fn name(&self) -> &'static str {
        self.name
    }
}

#[repr(align(32))]
pub struct BbRsiOverboughtSignal<const N: usize> {
    name: &'static str,
    bb: BollingerBands<N>,
    rsi: Rsi,
    current_price: f32,
    current_upper: f32,
}

impl<const N: usize> BbRsiOverboughtSignal<N> {
    #[inline(always)]
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::BbRsiOverbought {
            std_dev,
            rsi_period,
            rsi_ob,
            rsi_bull_div,
            ..
        } = params
        {
            Some(Self {
                name: "bb_rsi_overbought",
                bb: BollingerBands::new_uninitialized(*std_dev),
                rsi: Rsi::new_uninitialized(*rsi_period, *rsi_ob, 30.0, *rsi_bull_div),
                current_price: 0.0,
                current_upper: 0.0,
            })
        } else {
            None
        }
    }
}

impl<const N: usize> SingleAssetSignal for BbRsiOverboughtSignal<N> {
    #[inline(always)]
    fn update(&mut self, _open: f32, _high: f32, _low: f32, close: f32) {
        let (upper, _middle, _lower) = self.bb.update(close);
        self.current_upper = upper;
        self.current_price = close;
        self.rsi.update(close);
    }

    #[inline(always)]
    fn get_signal(&self) -> i8 {
        if self
            .bb
            .bb_above_upper(self.current_price, self.current_upper)
            & self.rsi.rsi_ob()
            == 1
        {
            -1 // Sell signal when overbought conditions are met
        } else {
            0 // Neutral
        }
    }

    #[inline(always)]
    fn name(&self) -> &'static str {
        self.name
    }
}

#[repr(align(32))]
pub struct PatternRsiMacdSignal<const SR: usize, const PAT: usize> {
    name: &'static str,
    pattern: PatternSignals<SR, PAT>,
    rsi: Rsi,
    macd: Macd,
    current_price: f32,
    current_rsi: f32,
}

impl<const SR: usize, const PAT: usize> PatternRsiMacdSignal<SR, PAT> {
    #[inline(always)]
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::PatternRsiMacd {
            resistance_threshold,
            support_threshold,
            rsi_period,
            rsi_os,
            rsi_bull_div,
            macd_fast,
            macd_slow,
            macd_signal,
            ..
        } = params
        {
            Some(Self {
                name: "pattern_rsi_macd",
                pattern: PatternSignals::new_uninitialized(
                    *resistance_threshold,
                    *support_threshold,
                ),
                rsi: Rsi::new_uninitialized(*rsi_period, 70.0, *rsi_os, *rsi_bull_div),
                macd: Macd::new_uninitialized(*macd_fast, *macd_slow, *macd_signal, 0, 0.0),
                current_price: 0.0,
                current_rsi: 0.0,
            })
        } else {
            None
        }
    }
}

impl<const SR: usize, const PAT: usize> SingleAssetSignal for PatternRsiMacdSignal<SR, PAT> {
    #[inline(always)]
    fn update(&mut self, _open: f32, high: f32, low: f32, close: f32) {
        self.pattern.update(high, low);
        self.rsi.update(close);
        self.macd.update(close);
        self.current_price = close;
        self.current_rsi = self.rsi.get_value();
    }

    #[inline(always)]
    fn get_signal(&self) -> i8 {
        self.pattern.resistance_breakout(self.current_price)
            & ((self.current_rsi < 80.0) as i8)
            & self.macd.macd_bullish()
    }

    #[inline(always)]
    fn name(&self) -> &'static str {
        self.name
    }
}

#[repr(align(32))]
pub struct TripleEmaPatternMacdRsiSignal<const SR: usize, const PAT: usize> {
    name: &'static str,
    ema: Ema,
    pattern: PatternSignals<SR, PAT>,
    macd: Macd,
    rsi: Rsi,
}

impl<const SR: usize, const PAT: usize> TripleEmaPatternMacdRsiSignal<SR, PAT> {
    #[inline(always)]
    pub fn from_params(params: &SignalParams) -> Option<Self> {
        if let SignalParams::TripleEmaPatternMacdRsi {
            ema_fast,
            ema_medium,
            ema_slow,
            resistance_threshold,
            support_threshold,
            macd_fast,
            macd_slow,
            macd_signal,
            rsi_period,
            rsi_ob,
            rsi_os,
            rsi_bull_div,
            ..
        } = params
        {
            Some(Self {
                name: "triple_ema_pattern_macd_rsi",
                ema: Ema::new_triple_uninitialized(*ema_fast, *ema_medium, *ema_slow),
                pattern: PatternSignals::new_uninitialized(
                    *resistance_threshold,
                    *support_threshold,
                ),
                macd: Macd::new_uninitialized(*macd_fast, *macd_slow, *macd_signal, 0, 0.0),
                rsi: Rsi::new_uninitialized(*rsi_period, *rsi_ob, *rsi_os, *rsi_bull_div),
            })
        } else {
            None
        }
    }
}

impl<const SR: usize, const PAT: usize> SingleAssetSignal
    for TripleEmaPatternMacdRsiSignal<SR, PAT>
{
    #[inline(always)]
    fn update(&mut self, _open: f32, high: f32, low: f32, close: f32) {
        self.ema.update(close);
        self.pattern.update(high, low);
        self.macd.update(close);
        self.rsi.update(close);
    }

    #[inline(always)]
    fn get_signal(&self) -> i8 {
        self.ema.ema_triple_bull()
            & self.pattern.uptrend_pattern()
            & self.macd.macd_bullish()
            & self.rsi.rsi_neutral()
    }

    #[inline(always)]
    fn name(&self) -> &'static str {
        self.name
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum SignalType {
    EmaRsiMacd = 0,
    BbRsiOversold = 1,
    BbRsiOverbought = 2,
    PatternRsiMacd = 3,
    TripleEmaPatternMacdRsi = 4,
    BbSqueezeBreakout = 5,
    RsiOversoldReversal = 6,
    SupportBounce = 7,
    UptrendPattern = 8,
    StochOversold = 9,
}

impl SignalType {
    #[inline(always)]
    pub fn from_name(name: &str) -> Option<Self> {
        match name {
            "ema_rsi_macd" => Some(Self::EmaRsiMacd),
            "bb_rsi_oversold" => Some(Self::BbRsiOversold),
            "bb_rsi_overbought" => Some(Self::BbRsiOverbought),
            "pattern_rsi_macd" => Some(Self::PatternRsiMacd),
            "triple_ema_pattern_macd_rsi" => Some(Self::TripleEmaPatternMacdRsi),
            "bb_squeeze_breakout" => Some(Self::BbSqueezeBreakout),
            "rsi_oversold_reversal" => Some(Self::RsiOversoldReversal),
            "support_bounce" => Some(Self::SupportBounce),
            "uptrend_pattern" => Some(Self::UptrendPattern),
            "stoch_oversold" => Some(Self::StochOversold),
            _ => None,
        }
    }
}

#[repr(align(64))]
pub struct SignalGenerator {
    pub signals:
        ArrayVec<SmallVec<[Box<dyn SingleAssetSignal>; MAX_SIGNALS_PER_ASSET]>, MAX_ASSETS>,
    n_assets: usize,
    #[allow(dead_code)]
    signal_buffer: [i8; MAX_ASSETS],
    #[allow(dead_code)]
    vote_buffer: [i8; MAX_SIGNALS_PER_ASSET],
}

impl SignalGenerator {
    #[inline(always)]
    pub fn new(n_assets: usize) -> Self {
        let mut signals = ArrayVec::new();
        for _ in 0..n_assets {
            signals.push(SmallVec::with_capacity(MAX_SIGNALS_PER_ASSET));
        }

        Self {
            signals,
            n_assets,
            signal_buffer: [0; MAX_ASSETS],
            vote_buffer: [0; MAX_SIGNALS_PER_ASSET],
        }
    }

    #[inline(always)]
    pub fn add_signal(&mut self, asset_idx: usize, signal: Box<dyn SingleAssetSignal>) {
        if asset_idx < self.n_assets && self.signals[asset_idx].len() < MAX_SIGNALS_PER_ASSET {
            self.signals[asset_idx].push(signal);
        }
    }

    #[inline(always)]
    pub fn update(&mut self, data: Vec<Vec<f32>>) {
        for (asset_idx, asset_data) in data.iter().enumerate().take(self.n_assets) {
            if asset_data.len() >= 4 {
                let (open, high, low, close) = unsafe {
                    (
                        *asset_data.get_unchecked(0),
                        *asset_data.get_unchecked(1),
                        *asset_data.get_unchecked(2),
                        *asset_data.get_unchecked(3),
                    )
                };

                for signal in &mut self.signals[asset_idx] {
                    signal.update(open, high, low, close);
                }
            }
        }
    }

    #[inline(always)]
    pub fn generate_signals(&self) -> Vec<i8> {
        let mut results = Vec::with_capacity(self.n_assets);

        for asset_idx in 0..self.n_assets {
            let asset_signals = &self.signals[asset_idx];

            if asset_signals.is_empty() {
                results.push(0);
                continue;
            }

            if asset_signals.len() == 1 {
                results.push(asset_signals[0].get_signal());
                continue;
            }

            let signal = self.fast_plurality_vote(asset_signals);
            results.push(signal);
        }

        results
    }

    #[inline(always)]
    fn fast_plurality_vote(&self, signals: &[Box<dyn SingleAssetSignal>]) -> i8 {
        let mut buy_count = 0u8;
        let mut sell_count = 0u8;

        for signal in signals {
            match signal.get_signal() {
                1 => buy_count += 1,
                -1 => sell_count += 1,
                _ => {} // neutral, no action
            }
        }

        if buy_count > sell_count {
            1
        } else if sell_count > buy_count {
            -1
        } else {
            0
        }
    }
}

#[inline(always)]
pub fn create_signal_from_params(params: &SignalParams) -> Option<Box<dyn SingleAssetSignal>> {
    match params {
        SignalParams::EmaRsiMacd { .. } => {
            EmaRsiMacdSignal::from_params(params).map(|s| Box::new(s) as Box<dyn SingleAssetSignal>)
        }
        SignalParams::BbRsiOversold { .. } => BbRsiOversoldSignal::<20>::from_params(params)
            .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>),
        SignalParams::BbRsiOverbought { .. } => BbRsiOverboughtSignal::<20>::from_params(params)
            .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>),
        SignalParams::PatternRsiMacd { .. } => PatternRsiMacdSignal::<10, 5>::from_params(params)
            .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>),
        SignalParams::TripleEmaPatternMacdRsi { .. } => {
            TripleEmaPatternMacdRsiSignal::<10, 5>::from_params(params)
                .map(|s| Box::new(s) as Box<dyn SingleAssetSignal>)
        }
        _ => None,
    }
}
