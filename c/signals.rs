use crate::indicators::*;
use crate::params::SignalParams;

pub trait Signal: Send {
    fn update(&mut self, price: f32, high: Option<f32>, low: Option<f32>, close: Option<f32>);
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
            initial_price,
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
                ema: Ema::new(*ema_fast, *ema_medium, *ema_slow, *initial_price),
                rsi: Rsi::new(*rsi_period, *initial_price, *rsi_ob, *rsi_os, *rsi_bull_div),
                macd: Macd::new(*macd_fast, *macd_slow, *macd_signal, *initial_price, 0, 0.0),
            })
        } else {
            None
        }
    }
}

impl Signal for EmaRsiMacdSignal {
    fn update(&mut self, price: f32, _high: Option<f32>, _low: Option<f32>, _close: Option<f32>) {
        self.ema.update(price as f64);
        self.rsi.update(price as f64);
        self.macd.update(price as f64);
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
            initial_close,
            rsi_period,
            initial_price,
            rsi_ob,
            rsi_os,
            rsi_bull_div,
        } = params
        {
            let mut bb = BollingerBands::new(*std_dev, *initial_close);
            let (_middle, _upper, lower) = bb.update(*initial_close);
            Some(Self {
                name: name.clone(),
                bb,
                rsi: Rsi::new(*rsi_period, *initial_price, *rsi_ob, *rsi_os, *rsi_bull_div),
                current_price: *initial_close,
                current_lower: lower,
            })
        } else {
            None
        }
    }
}

impl<const N: usize> Signal for BbRsiOversoldSignal<N> {
    fn update(&mut self, price: f32, _high: Option<f32>, _low: Option<f32>, close: Option<f32>) {
        if let Some(c) = close {
            let (_middle, _upper, lower) = self.bb.update(c);
            self.current_lower = lower;
        }
        self.current_price = price;
        self.rsi.update(price as f64);
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
            initial_price,
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
                rsi: Rsi::new(*rsi_period, *initial_price, *rsi_ob, *rsi_os, *rsi_bull_div),
                current_price: *initial_close,
                current_upper: upper,
            })
        } else {
            None
        }
    }
}

impl<const N: usize> Signal for BbRsiOverboughtSignal<N> {
    fn update(&mut self, price: f32, _high: Option<f32>, _low: Option<f32>, close: Option<f32>) {
        if let Some(c) = close {
            let (_middle, upper, _lower) = self.bb.update(c);
            self.current_upper = upper;
        }
        self.current_price = price;
        self.rsi.update(price as f64);
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
    current_rsi: f64,
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
            initial_price,
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
                    *initial_close,
                ),
                rsi: Rsi::new(*rsi_period, *initial_price, *rsi_ob, *rsi_os, *rsi_bull_div),
                macd: Macd::new(*macd_fast, *macd_slow, *macd_signal, *initial_price, 0, 0.0),
                current_price: *initial_close,
                current_rsi: 50.0,
            })
        } else {
            None
        }
    }
}

impl<const SR: usize, const PAT: usize> Signal for PatternRsiMacdSignal<SR, PAT> {
    fn update(&mut self, price: f32, high: Option<f32>, low: Option<f32>, close: Option<f32>) {
        if let (Some(h), Some(l), Some(c)) = (high, low, close) {
            self.pattern.update(h, l, c);
        }
        self.rsi.update(price as f64);
        self.macd.update(price as f64);
        self.current_price = price;
        self.current_rsi = self.rsi.get_value();
    }
    fn get_signal(&self) -> i8 {
        (self.pattern.resistance_breakout(self.current_price) as i8)
            & ((self.current_rsi < 80.0) as i8)
            & (self.macd.macd_bullish() as i8)
    }
    fn name(&self) -> &str {
        &self.name
    }
}

// strategy 5, ema_triple_bull__uptrend_pattern__macd_bull__ris_neu
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
            initial_price,
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
                ema: Ema::new(*ema_fast, *ema_medium, *ema_slow, *initial_price),
                pattern: PatternSignals::new(
                    *resistance_threshold,
                    *support_threshold,
                    *initial_high,
                    *initial_low,
                    *initial_close,
                ),
                macd: Macd::new(*macd_fast, *macd_slow, *macd_signal, *initial_price, 0, 0.0),
                rsi: Rsi::new(*rsi_period, *initial_price, *rsi_ob, *rsi_os, *rsi_bull_div),
            })
        } else {
            None
        }
    }
}

impl<const SR: usize, const PAT: usize> Signal for TripleEmaPatternMacdRsiSignal<SR, PAT> {
    fn update(&mut self, price: f32, high: Option<f32>, low: Option<f32>, close: Option<f32>) {
        self.ema.update(price as f64);
        if let (Some(h), Some(l), Some(c)) = (high, low, close) {
            self.pattern.update(h, l, c);
        }
        self.macd.update(price as f64);
        self.rsi.update(price as f64);
    }
    fn get_signal(&self) -> i8 {
        self.ema.ema_triple_bull()
            & self.pattern.uptrend_pattern()
            & self.macd.macd_bullish()
            & self.rsi.rsi_neutral()
    }
    fn name(&self) -> &str {
        &self.name
    }
}

// strategy 6, bb_squeeze_breakout__macd_bull
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
            initial_price,
            squeeze_threshold,
        } = params
        {
            let mut bb = BollingerBands::new(*std_dev, *initial_close);
            let (middle, upper, lower) = bb.update(*initial_close);
            Some(Self {
                name: name.clone(),
                bb,
                macd: Macd::new(*macd_fast, *macd_slow, *macd_signal, *initial_price, 0, 0.0),
                current_price: *initial_close,
                current_upper: upper,
                current_lower: lower,
                current_middle: middle,
                current_squeeze_threshold: *squeeze_threshold,
            })
        } else {
            None
        }
    }
}

impl<const N: usize> Signal for BbSqueezeBreakoutSignal<N> {
    fn update(&mut self, price: f32, _high: Option<f32>, _low: Option<f32>, close: Option<f32>) {
        if let Some(c) = close {
            let (middle, upper, lower) = self.bb.update(c);
            self.current_upper = upper;
            self.current_lower = lower;
            self.current_middle = middle;
        }
        self.current_price = price;
        // macd update needs price, call externally
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
            initial_price,
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
                rsi: Rsi::new(*rsi_period, *initial_price, *rsi_ob, *rsi_os, *rsi_bull_div),
                ema: Ema::new(*ema_fast, *ema_medium, *ema_slow, *initial_price),
            })
        } else {
            None
        }
    }
}

impl Signal for RsiOversoldReversalSignal {
    fn update(&mut self, price: f32, _high: Option<f32>, _low: Option<f32>, _close: Option<f32>) {
        self.rsi.update(price as f64);
        self.ema.update(price as f64);
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
            initial_price,
        } = params
        {
            Some(Self {
                name: name.clone(),
                pattern: PatternSignals::new(
                    *resistance_threshold,
                    *support_threshold,
                    *initial_high,
                    *initial_low,
                    *initial_close,
                ),
                macd: Macd::new(*macd_fast, *macd_slow, *macd_signal, *initial_price, 0, 0.0),
                current_price: *initial_close,
            })
        } else {
            None
        }
    }
}

impl<const SR: usize, const PAT: usize> Signal for SupportBounceSignal<SR, PAT> {
    fn update(&mut self, price: f32, high: Option<f32>, low: Option<f32>, close: Option<f32>) {
        if let (Some(h), Some(l), Some(c)) = (high, low, close) {
            self.pattern.update(h, l, c);
        }
        self.macd.update(price as f64);
        self.current_price = price;
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
            initial_price,
            resistance_threshold,
            support_threshold,
            initial_high,
            initial_low,
            initial_close,
            rsi_period,
            rsi_ob,
            rsi_os,
            rsi_bull_div,
        } = params
        {
            Some(Self {
                name: name.clone(),
                ema: Ema::new(*ema_fast, *ema_medium, *ema_slow, *initial_price),
                pattern: PatternSignals::new(
                    *resistance_threshold,
                    *support_threshold,
                    *initial_high,
                    *initial_low,
                    *initial_close,
                ),
                rsi: Rsi::new(*rsi_period, *initial_price, *rsi_ob, *rsi_os, *rsi_bull_div),
            })
        } else {
            None
        }
    }
}

impl<const SR: usize, const PAT: usize> Signal for UptrendPatternSignal<SR, PAT> {
    fn update(&mut self, price: f32, high: Option<f32>, low: Option<f32>, close: Option<f32>) {
        self.ema.update(price as f64);
        if let (Some(h), Some(l), Some(c)) = (high, low, close) {
            self.pattern.update(h, l, c);
        }
        self.rsi.update(price as f64);
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
            initial_price,
            oversold,
        } = params
        {
            Some(Self {
                name: name.clone(),
                stoch: StochasticOscillator::new(*initial_high, *initial_low, *initial_close),
                ema_fast: _Ema::new(*ema_fast_period, *initial_price),
                ema_slow: _Ema::new(*ema_slow_period, *initial_price),
                current_oversold: *oversold,
            })
        } else {
            None
        }
    }
}

impl<const N: usize, const K: usize, const D: usize> Signal for StochOversoldSignal<N, K, D> {
    fn update(&mut self, price: f32, high: Option<f32>, low: Option<f32>, close: Option<f32>) {
        if let (Some(h), Some(l), Some(c)) = (high, low, close) {
            self.stoch.update(h, l, c);
        }
        self.ema_fast._update(price as f64);
        self.ema_slow._update(price as f64);
    }
    fn get_signal(&self) -> i8 {
        (self.stoch.stoch_oversold(self.current_oversold) as i8)
            & ((self.ema_fast.get() > self.ema_slow.get()) as i8)
    }
    fn name(&self) -> &str {
        &self.name
    }
}
