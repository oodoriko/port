#[repr(align(64))]
#[derive(Clone, Copy, Debug)]
pub struct Ema {
    period: i8,
    multiplier: f32,
    value: f32,
    #[allow(dead_code)]
    initialized: bool,

    ema_fast: f32,
    ema_medium: f32,
    ema_slow: f32,
    fast_mult: f32,
    medium_mult: f32,
    slow_mult: f32,
    last_price: f32,

    _padding: [u8; 8],
}

impl Ema {
    #[inline(always)]
    pub fn new(period: usize, initial_price: f32) -> Self {
        let multiplier = 2.0 / (period as f32 + 1.0);
        Self {
            period: period as i8,
            multiplier,
            value: initial_price,
            initialized: true,
            ema_fast: initial_price,
            ema_medium: initial_price,
            ema_slow: initial_price,
            fast_mult: multiplier,
            medium_mult: multiplier,
            slow_mult: multiplier,
            last_price: initial_price,
            _padding: [0u8; 8],
        }
    }

    #[inline(always)]
    pub fn new_uninitialized(period: usize) -> Self {
        let multiplier = 2.0 / (period as f32 + 1.0);
        Self {
            period: period as i8,
            multiplier,
            value: 0.0,
            initialized: false,
            ema_fast: 0.0,
            ema_medium: 0.0,
            ema_slow: 0.0,
            fast_mult: multiplier,
            medium_mult: multiplier,
            slow_mult: multiplier,
            last_price: 0.0,
            _padding: [0u8; 8],
        }
    }

    #[inline(always)]
    pub fn new_triple(
        fast_period: usize,
        medium_period: usize,
        slow_period: usize,
        initial_price: f32,
    ) -> Self {
        Self {
            period: fast_period as i8,
            multiplier: 2.0 / (fast_period as f32 + 1.0),
            value: initial_price,
            initialized: true,
            ema_fast: initial_price,
            ema_medium: initial_price,
            ema_slow: initial_price,
            fast_mult: 2.0 / (fast_period as f32 + 1.0),
            medium_mult: 2.0 / (medium_period as f32 + 1.0),
            slow_mult: 2.0 / (slow_period as f32 + 1.0),
            last_price: initial_price,
            _padding: [0u8; 8],
        }
    }

    #[inline(always)]
    pub fn new_triple_uninitialized(
        fast_period: usize,
        medium_period: usize,
        slow_period: usize,
    ) -> Self {
        Self {
            period: fast_period as i8,
            multiplier: 2.0 / (fast_period as f32 + 1.0),
            value: 0.0,
            initialized: false,
            ema_fast: 0.0,
            ema_medium: 0.0,
            ema_slow: 0.0,
            fast_mult: 2.0 / (fast_period as f32 + 1.0),
            medium_mult: 2.0 / (medium_period as f32 + 1.0),
            slow_mult: 2.0 / (slow_period as f32 + 1.0),
            last_price: 0.0,
            _padding: [0u8; 8],
        }
    }

    #[inline(always)]
    pub fn update(&mut self, new_price: f32) -> f32 {
        if !self.initialized {
            self.value = new_price;
            self.ema_fast = new_price;
            self.ema_medium = new_price;
            self.ema_slow = new_price;
            self.last_price = new_price;
            self.initialized = true;
            return self.value;
        }

        self.value = (new_price - self.value) * self.multiplier + self.value;

        self.ema_fast = (new_price - self.ema_fast) * self.fast_mult + self.ema_fast;
        self.ema_medium = (new_price - self.ema_medium) * self.medium_mult + self.ema_medium;
        self.ema_slow = (new_price - self.ema_slow) * self.slow_mult + self.ema_slow;
        self.last_price = new_price;

        self.value
    }

    #[inline(always)]
    pub fn get(&self) -> f32 {
        self.value
    }

    #[inline(always)]
    pub fn ema_f_s(&self) -> i8 {
        (self.ema_fast > self.ema_slow) as i8
    }

    #[inline(always)]
    pub fn ema_f_m(&self) -> i8 {
        (self.ema_fast > self.ema_medium) as i8
    }

    #[inline(always)]
    pub fn ema_price_m(&self) -> i8 {
        (self.last_price > self.ema_medium) as i8
    }

    #[inline(always)]
    pub fn ema_triple_bull(&self) -> i8 {
        (self.ema_fast > self.ema_medium && self.ema_medium > self.ema_slow) as i8
    }
}

#[repr(align(64))]
#[derive(Clone, Debug)]
pub struct Rsi {
    period: i8,
    prev_price: f32,
    avg_gain: f32,
    avg_loss: f32,
    count: i8,
    value: f32,
    initialized: bool,
    rsi_overbought: f32,
    rsi_oversold: f32,
    rsi_bull_div_threshold: f32,
    prev_rsi: f32,
    last_price: f32,
    _padding: [u8; 8],
}

impl Rsi {
    #[inline(always)]
    pub fn new(
        period: usize,
        initial_price: f32,
        rsi_overbought: f32,
        rsi_oversold: f32,
        rsi_bull_div_threshold: f32,
    ) -> Self {
        Self {
            period: period as i8,
            prev_price: initial_price,
            avg_gain: 0.0,
            avg_loss: 0.0,
            count: 0,
            value: 50.0,
            initialized: false,
            rsi_overbought,
            rsi_oversold,
            rsi_bull_div_threshold,
            prev_rsi: 50.0,
            last_price: initial_price,
            _padding: [0u8; 8],
        }
    }

    #[inline(always)]
    pub fn new_uninitialized(
        period: usize,
        rsi_overbought: f32,
        rsi_oversold: f32,
        rsi_bull_div_threshold: f32,
    ) -> Self {
        Self {
            period: period as i8,
            prev_price: 0.0,
            avg_gain: 0.0,
            avg_loss: 0.0,
            count: 0,
            value: 50.0,
            initialized: false,
            rsi_overbought,
            rsi_oversold,
            rsi_bull_div_threshold,
            prev_rsi: 50.0,
            last_price: 0.0,
            _padding: [0u8; 8],
        }
    }

    #[inline(always)]
    pub fn update(&mut self, new_price: f32) {
        // Handle first value for uninitialized RSI
        if self.prev_price == 0.0 {
            self.prev_price = new_price;
            self.last_price = new_price;
            return; // Don't calculate change on first value
        }

        self.prev_rsi = self.value;
        let change = new_price - self.prev_price;
        let gain = if change > 0.0 { change } else { 0.0 };
        let loss = if change < 0.0 { -change } else { 0.0 };

        if !self.initialized {
            self.avg_gain += gain;
            self.avg_loss += loss;
            self.count += 1;
            if self.count == self.period {
                self.avg_gain /= self.period as f32;
                self.avg_loss /= self.period as f32;
                self.initialized = true;
            }
        } else {
            let period_f = self.period as f32;
            self.avg_gain = (self.avg_gain * (period_f - 1.0) + gain) / period_f;
            self.avg_loss = (self.avg_loss * (period_f - 1.0) + loss) / period_f;

            let rs = if self.avg_loss == 0.0 {
                100.0
            } else {
                self.avg_gain / self.avg_loss
            };
            self.value = 100.0 - (100.0 / (1.0 + rs));
        }

        self.prev_price = new_price;
        self.last_price = new_price;
    }

    #[inline(always)]
    pub fn rsi_ob(&self) -> i8 {
        (self.value > self.rsi_overbought) as i8
    }

    #[inline(always)]
    pub fn rsi_os(&self) -> i8 {
        (self.value < self.rsi_oversold) as i8
    }

    #[inline(always)]
    pub fn rsi_neutral(&self) -> i8 {
        (self.value >= self.rsi_oversold && self.value <= self.rsi_overbought) as i8
    }

    #[inline(always)]
    pub fn rsi_bull_div(&self) -> i8 {
        let price_slope = self.last_price - self.prev_price;
        let rsi_slope = self.value - self.prev_rsi;
        (price_slope < 0.0 && rsi_slope > 0.0 && self.value < self.rsi_bull_div_threshold) as i8
    }

    #[inline(always)]
    pub fn get_value(&self) -> f32 {
        self.value
    }
}

#[repr(align(64))]
#[derive(Clone, Debug)]
pub struct Macd {
    fast_ema: Ema,
    slow_ema: Ema,
    signal_ema: Ema,
    macd_line: f32,
    signal_line: f32,
    histogram: f32,
    initialized: bool,
    prev_macd_bull: i8,
    prev_macd_hist: f32,
    _padding: [u8; 16],
}

impl Macd {
    #[inline(always)]
    pub fn new(
        fast_period: usize,
        slow_period: usize,
        signal_period: usize,
        initial_price: f32,
        prev_macd_bull: i8,
        prev_macd_hist: f32,
    ) -> Self {
        Self {
            fast_ema: Ema::new(fast_period, initial_price),
            slow_ema: Ema::new(slow_period, initial_price),
            signal_ema: Ema::new(signal_period, 0.0),
            macd_line: 0.0,
            signal_line: 0.0,
            histogram: 0.0,
            initialized: false,
            prev_macd_bull,
            prev_macd_hist,
            _padding: [0u8; 16],
        }
    }

    #[inline(always)]
    pub fn new_uninitialized(
        fast_period: usize,
        slow_period: usize,
        signal_period: usize,
        prev_macd_bull: i8,
        prev_macd_hist: f32,
    ) -> Self {
        Self {
            fast_ema: Ema::new_uninitialized(fast_period),
            slow_ema: Ema::new_uninitialized(slow_period),
            signal_ema: Ema::new_uninitialized(signal_period),
            macd_line: 0.0,
            signal_line: 0.0,
            histogram: 0.0,
            initialized: false,
            prev_macd_bull,
            prev_macd_hist,
            _padding: [0u8; 16],
        }
    }

    #[inline(always)]
    pub fn update(&mut self, new_price: f32) {
        let fast = self.fast_ema.update(new_price);
        let slow = self.slow_ema.update(new_price);
        self.macd_line = fast - slow;

        if !self.initialized {
            self.signal_ema = Ema::new(self.signal_ema.period as usize, self.macd_line);
            self.initialized = true;
        }

        self.signal_line = self.signal_ema.update(self.macd_line);
        self.histogram = self.macd_line - self.signal_line;

        self.prev_macd_bull = (self.macd_line > self.signal_line) as i8;
        self.prev_macd_hist = self.histogram;
    }

    #[inline(always)]
    pub fn macd_bullish(&self) -> i8 {
        (self.macd_line > self.signal_line) as i8
    }

    #[inline(always)]
    pub fn macd_xu(&self) -> i8 {
        let current = self.macd_bullish();
        (self.prev_macd_bull == 0 && current == 1) as i8
    }

    #[inline(always)]
    pub fn macd_xd(&self) -> i8 {
        let current = self.macd_bullish();
        (self.prev_macd_bull == 1 && current == 0) as i8
    }

    #[inline(always)]
    pub fn macd_hist_inc(&self) -> i8 {
        (self.histogram > self.prev_macd_hist) as i8
    }

    #[inline(always)]
    pub fn get_values(&self) -> (f32, f32, f32) {
        (self.macd_line, self.signal_line, self.histogram)
    }
}

#[repr(align(64))]
#[derive(Clone, Debug)]
pub struct Atr {
    period: i8,
    prev_atr: f32,
    prev_close: f32,
    count: i8,
    sum_tr: f32,
    initialized: bool,
    multiplier: f32,
    _padding: [u8; 20],
}

impl Atr {
    #[inline(always)]
    pub fn new(period: usize, initial_close: f32) -> Self {
        Self {
            period: period as i8,
            prev_atr: 0.0,
            prev_close: initial_close,
            count: 0,
            sum_tr: 0.0,
            initialized: false,
            multiplier: 1.0 / period as f32,
            _padding: [0u8; 20],
        }
    }

    #[inline(always)]
    pub fn update(&mut self, high: f32, low: f32, close: f32) -> f32 {
        let hl = high - low;
        let hc = (high - self.prev_close).abs();
        let lc = (low - self.prev_close).abs();
        let tr = hl.max(hc).max(lc);

        if !self.initialized {
            self.sum_tr += tr;
            self.count += 1;
            if self.count == self.period {
                self.prev_atr = self.sum_tr * self.multiplier;
                self.initialized = true;
            }
        } else {
            self.prev_atr = ((self.period as f32 - 1.0) * self.prev_atr + tr) * self.multiplier;
        }

        self.prev_close = close;
        self.prev_atr
    }

    #[inline(always)]
    pub fn get(&self) -> f32 {
        self.prev_atr
    }

    #[inline(always)]
    pub fn high_volatility(&self, threshold: f32) -> i8 {
        (self.prev_atr > threshold) as i8
    }
}

#[repr(align(64))]
pub struct BollingerBands<const N: usize> {
    std_dev: f32,
    closes: [f32; N],
    idx: usize,
    len: usize,
    mean: f32,
    m2: f32,
    _padding: [u8; 32],
}

impl<const N: usize> BollingerBands<N> {
    #[inline(always)]
    pub fn new(std_dev: f32, initial_close: f32) -> Self {
        let mut closes = [0.0; N];
        closes[0] = initial_close;
        Self {
            std_dev,
            closes,
            idx: 0,
            len: 1,
            mean: initial_close,
            m2: 0.0,
            _padding: [0u8; 32],
        }
    }

    #[inline(always)]
    pub fn new_uninitialized(std_dev: f32) -> Self {
        Self {
            std_dev,
            closes: [0.0; N],
            idx: 0,
            len: 0,
            mean: 0.0,
            m2: 0.0,
            _padding: [0u8; 32],
        }
    }

    #[inline(always)]
    pub fn update(&mut self, new_close: f32) -> (f32, f32, f32) {
        let old = self.closes[self.idx % N];
        self.closes[self.idx % N] = new_close;
        self.idx += 1;

        if self.len < N {
            self.len += 1;
            let delta = new_close - self.mean;
            self.mean += delta / self.len as f32;
            self.m2 += delta * (new_close - self.mean);
        } else {
            let delta_old = old - self.mean;
            self.mean -= delta_old / self.len as f32;
            self.m2 -= delta_old * (old - self.mean);
            let delta_new = new_close - self.mean;
            self.mean += delta_new / self.len as f32;
            self.m2 += delta_new * (new_close - self.mean);
        }

        let variance = if self.len > 1 {
            self.m2 / (self.len as f32 - 1.0)
        } else {
            0.0
        };
        let std = variance.sqrt();
        let band_width = self.std_dev * std;

        (self.mean + band_width, self.mean, self.mean - band_width)
    }

    #[inline(always)]
    pub fn bb_above_upper(&self, price: f32, upper: f32) -> i8 {
        (price > upper) as i8
    }

    #[inline(always)]
    pub fn bb_below_lower(&self, price: f32, lower: f32) -> i8 {
        (price < lower) as i8
    }

    #[inline(always)]
    pub fn bb_squeeze(&self, upper: f32, lower: f32, middle: f32, squeeze_threshold: f32) -> i8 {
        if middle.abs() < 1e-8 {
            0
        } else {
            ((upper - lower) / middle < squeeze_threshold) as i8
        }
    }

    #[inline(always)]
    pub fn bb_position(&self, price: f32, upper: f32, lower: f32) -> f32 {
        let range = upper - lower;
        if range.abs() < 1e-8 {
            0.5
        } else {
            (price - lower) / range
        }
    }
}

#[repr(align(64))]
pub struct StochasticOscillator<const N: usize, const K: usize, const D: usize> {
    highs: [f32; N],
    lows: [f32; N],
    k_values: [f32; K],
    idx: usize,
    k_idx: usize,
    len: usize,
    k_len: usize,
    min_low: f32,
    max_high: f32,
    _padding: [u8; 16],
}

impl<const N: usize, const K: usize, const D: usize> StochasticOscillator<N, K, D> {
    #[inline(always)]
    pub fn new(initial_high: f32, initial_low: f32, _initial_close: f32) -> Self {
        let mut highs = [0.0; N];
        let mut lows = [0.0; N];
        let mut k_values = [0.0; K];
        highs[0] = initial_high;
        lows[0] = initial_low;
        k_values[0] = 50.0;

        Self {
            highs,
            lows,
            k_values,
            idx: 1,
            k_idx: 1,
            len: 1,
            k_len: 1,
            min_low: initial_low,
            max_high: initial_high,
            _padding: [0u8; 16],
        }
    }

    #[inline(always)]
    pub fn update(&mut self, high: f32, low: f32, close: f32) -> (f32, f32) {
        self.highs[self.idx % N] = high;
        self.lows[self.idx % N] = low;
        self.idx += 1;
        if self.len < N {
            self.len += 1;
        }

        self.max_high = self.highs[..self.len]
            .iter()
            .fold(f32::NEG_INFINITY, |a, &b| a.max(b));
        self.min_low = self.lows[..self.len]
            .iter()
            .fold(f32::INFINITY, |a, &b| a.min(b));

        let range = self.max_high - self.min_low;
        let k = if range.abs() < 1e-8 {
            50.0
        } else {
            100.0 * (close - self.min_low) / range
        };

        self.k_values[self.k_idx % K] = k;
        self.k_idx += 1;
        if self.k_len < K {
            self.k_len += 1;
        }

        let k_smooth = self.k_values[..self.k_len].iter().sum::<f32>() / self.k_len as f32;
        (k_smooth, k_smooth)
    }

    #[inline(always)]
    pub fn stoch_oversold(&self, oversold: f32) -> i8 {
        let k = self.k_values[(self.k_idx.wrapping_sub(1)) % K];
        (k < oversold) as i8
    }

    #[inline(always)]
    pub fn stoch_overbought(&self, overbought: f32) -> i8 {
        let k = self.k_values[(self.k_idx.wrapping_sub(1)) % K];
        (k > overbought) as i8
    }
}

#[repr(align(64))]
pub struct PatternSignals<const SR: usize, const PAT: usize> {
    resistance_threshold: f32,
    support_threshold: f32,
    highs_sr: [f32; SR],
    lows_sr: [f32; SR],
    highs_pat: [f32; PAT],
    lows_pat: [f32; PAT],
    sr_idx: usize,
    pat_idx: usize,
    sr_len: usize,
    pat_len: usize,
    last_resistance: f32,
    last_support: f32,
    last_high_pat: f32,
    last_low_pat: f32,
    prev_high_pat: f32,
    prev_low_pat: f32,
    _padding: [u8; 8],
}

impl<const SR: usize, const PAT: usize> PatternSignals<SR, PAT> {
    #[inline(always)]
    pub fn new(
        resistance_threshold: f32,
        support_threshold: f32,
        initial_high: f32,
        initial_low: f32,
    ) -> Self {
        let mut highs_sr = [0.0; SR];
        let mut lows_sr = [0.0; SR];
        let mut highs_pat = [0.0; PAT];
        let mut lows_pat = [0.0; PAT];

        highs_sr[0] = initial_high;
        lows_sr[0] = initial_low;
        highs_pat[0] = initial_high;
        lows_pat[0] = initial_low;

        Self {
            resistance_threshold,
            support_threshold,
            highs_sr,
            lows_sr,
            highs_pat,
            lows_pat,
            sr_idx: 0,
            pat_idx: 0,
            sr_len: 1,
            pat_len: 1,
            last_resistance: initial_high,
            last_support: initial_low,
            last_high_pat: initial_high,
            last_low_pat: initial_low,
            prev_high_pat: initial_high,
            prev_low_pat: initial_low,
            _padding: [0u8; 8],
        }
    }

    #[inline(always)]
    pub fn new_uninitialized(resistance_threshold: f32, support_threshold: f32) -> Self {
        Self {
            resistance_threshold,
            support_threshold,
            highs_sr: [0.0; SR],
            lows_sr: [0.0; SR],
            highs_pat: [0.0; PAT],
            lows_pat: [0.0; PAT],
            sr_idx: 0,
            pat_idx: 0,
            sr_len: 0,
            pat_len: 0,
            last_resistance: 0.0,
            last_support: 0.0,
            last_high_pat: 0.0,
            last_low_pat: 0.0,
            prev_high_pat: 0.0,
            prev_low_pat: 0.0,
            _padding: [0u8; 8],
        }
    }

    #[inline(always)]
    pub fn update(&mut self, high: f32, low: f32) {
        self.highs_sr[self.sr_idx % SR] = high;
        self.lows_sr[self.sr_idx % SR] = low;
        self.sr_idx += 1;
        if self.sr_len < SR {
            self.sr_len += 1;
        }

        self.last_resistance = self.highs_sr[..self.sr_len]
            .iter()
            .fold(f32::NEG_INFINITY, |a, &b| a.max(b));
        self.last_support = self.lows_sr[..self.sr_len]
            .iter()
            .fold(f32::INFINITY, |a, &b| a.min(b));

        if self.pat_len == PAT {
            self.prev_high_pat = self.last_high_pat;
            self.prev_low_pat = self.last_low_pat;
        }

        self.highs_pat[self.pat_idx % PAT] = high;
        self.lows_pat[self.pat_idx % PAT] = low;
        self.pat_idx += 1;
        if self.pat_len < PAT {
            self.pat_len += 1;
        }

        self.last_high_pat = self.highs_pat[..self.pat_len]
            .iter()
            .fold(f32::NEG_INFINITY, |a, &b| a.max(b));
        self.last_low_pat = self.lows_pat[..self.pat_len]
            .iter()
            .fold(f32::INFINITY, |a, &b| a.min(b));
    }

    #[inline(always)]
    pub fn resistance_level(&self) -> f32 {
        self.last_resistance
    }

    #[inline(always)]
    pub fn support_level(&self) -> f32 {
        self.last_support
    }

    #[inline(always)]
    pub fn near_resistance(&self, price: f32) -> i8 {
        (price > self.resistance_threshold * self.last_resistance) as i8
    }

    #[inline(always)]
    pub fn near_support(&self, price: f32) -> i8 {
        (price < self.support_threshold * self.last_support) as i8
    }

    #[inline(always)]
    pub fn resistance_breakout(&self, price: f32) -> i8 {
        (price > self.last_resistance) as i8
    }

    #[inline(always)]
    pub fn support_breakout(&self, price: f32) -> i8 {
        (price < self.last_support) as i8
    }

    #[inline(always)]
    pub fn uptrend_pattern(&self) -> i8 {
        (self.last_high_pat > self.prev_high_pat && self.last_low_pat > self.prev_low_pat) as i8
    }

    #[inline(always)]
    pub fn downtrend_pattern(&self) -> i8 {
        (self.last_high_pat < self.prev_high_pat && self.last_low_pat < self.prev_low_pat) as i8
    }
}

#[derive(Clone, Debug)]
pub struct EmaIndicator {
    alpha: f32,
    current_value: f32,
    initialized: bool,
}

impl EmaIndicator {
    #[inline(always)]
    pub fn new(period: usize) -> Self {
        Self {
            alpha: 2.0 / (period + 1) as f32,
            current_value: 0.0,
            initialized: false,
        }
    }

    #[inline(always)]
    pub fn update(&mut self, value: f32) -> f32 {
        if !self.initialized {
            self.current_value = value;
            self.initialized = true;
        } else {
            self.current_value = self.alpha * value + (1.0 - self.alpha) * self.current_value;
        }
        self.current_value
    }
}
