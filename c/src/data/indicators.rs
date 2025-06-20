use std::collections::VecDeque;

pub struct _Ema {
    period: usize,
    multiplier: f32,
    value: f32,
    initialized: bool,
}

impl _Ema {
    pub fn new(period: usize, initial_price: f32) -> Self {
        let multiplier = 2.0 / (period as f32 + 1.0);
        Self {
            period,
            multiplier,
            value: initial_price,
            initialized: true,
        }
    }

    pub fn _update(&mut self, new_price: f32) -> f32 {
        if !self.initialized {
            self.value = new_price;
            self.initialized = true;
        } else {
            self.value = (new_price - self.value) * self.multiplier + self.value;
        }
        self.value
    }

    pub fn get(&self) -> f32 {
        self.value
    }
}

pub struct Rsi {
    period: usize,
    prev_price: f32,
    avg_gain: f32,
    avg_loss: f32,
    count: usize,
    value: f32,
    initialized: bool,
    rsi_overbought: f32,
    rsi_oversold: f32,
    rsi_bull_div_threshold: f32,
    prev_rsi: f32,
    last_price: f32,
}

impl Rsi {
    pub fn new(
        period: usize,
        initial_price: f32,
        rsi_overbought: f32,
        rsi_oversold: f32,
        rsi_bull_div_threshold: f32,
    ) -> Self {
        Self {
            period,
            prev_price: initial_price,
            avg_gain: 0.0,
            avg_loss: 0.0,
            count: 0,
            value: 50.0, // neutral start
            initialized: false,
            rsi_overbought,
            rsi_oversold,
            rsi_bull_div_threshold,
            prev_rsi: 50.0,
            last_price: initial_price,
        }
    }

    pub fn update(&mut self, new_price: f32) {
        self.prev_rsi = self.value;
        self.prev_price = self.last_price;
        self.last_price = new_price;
        self._update(new_price);
    }

    pub fn rsi_ob(&self) -> i8 {
        (self.value > self.rsi_overbought) as i8
    }

    pub fn rsi_os(&self) -> i8 {
        (self.value < self.rsi_oversold) as i8
    }

    pub fn rsi_neutral(&self) -> i8 {
        (self.value >= self.rsi_oversold && self.value <= self.rsi_overbought) as i8
    }

    pub fn rsi_bull_div(&self) -> i8 {
        let price_slope = self.last_price - self.prev_price;
        let rsi_slope = self.value - self.prev_rsi;
        (price_slope < 0.0 && rsi_slope > 0.0 && self.value < self.rsi_bull_div_threshold) as i8
    }

    fn _update(&mut self, new_price: f32) -> f32 {
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
            self.value
        } else {
            self.avg_gain =
                (self.avg_gain * (self.period as f32 - 1.0) + gain) / self.period as f32;
            self.avg_loss =
                (self.avg_loss * (self.period as f32 - 1.0) + loss) / self.period as f32;

            let rs = if self.avg_loss == 0.0 {
                100.0
            } else {
                self.avg_gain / self.avg_loss
            };
            self.value = 100.0 - (100.0 / (1.0 + rs));
            self.value
        }
    }

    pub fn get_value(&self) -> f32 {
        self.value
    }
}

pub struct Macd {
    fast_ema: _Ema,
    slow_ema: _Ema,
    signal_ema: _Ema,
    macd_line: f32,
    signal_line: f32,
    hist: f32,
    initialized: bool,
    prev_macd_bull: i8,
    prev_macd_hist: f32,
}

impl Macd {
    pub fn new(
        fast_period: usize,
        slow_period: usize,
        signal_period: usize,
        initial_price: f32,
        prev_macd_bull: i8,
        prev_macd_hist: f32,
    ) -> Self {
        let fast_ema = _Ema::new(fast_period, initial_price);
        let slow_ema = _Ema::new(slow_period, initial_price);
        let macd_line = 0.0;
        let signal_ema = _Ema::new(signal_period, macd_line);
        Self {
            fast_ema,
            slow_ema,
            signal_ema,
            macd_line,
            signal_line: 0.0,
            hist: 0.0,
            initialized: false,
            prev_macd_bull,
            prev_macd_hist,
        }
    }

    pub fn _update(&mut self, new_price: f32) -> (f32, f32, f32) {
        let fast = self.fast_ema._update(new_price);
        let slow = self.slow_ema._update(new_price);
        self.macd_line = fast - slow;
        if !self.initialized {
            self.signal_ema = _Ema::new(self.signal_ema.period, self.macd_line);
            self.initialized = true;
        }
        self.signal_line = self.signal_ema._update(self.macd_line);
        self.hist = self.macd_line - self.signal_line;
        (self.macd_line, self.signal_line, self.hist)
    }

    pub fn update(&mut self, new_price: f32) {
        let (macd_line, signal_line, hist) = self._update(new_price);
        self.prev_macd_bull = (macd_line > signal_line) as i8;
        self.prev_macd_hist = hist;
    }

    pub fn macd_bullish(&self) -> i8 {
        (self.macd_line > self.signal_line) as i8
    }

    pub fn macd_xu(&self) -> i8 {
        let current = self.macd_bullish();
        (self.prev_macd_bull == 0 && current == 1) as i8
    }

    pub fn macd_xd(&self) -> i8 {
        let current = self.macd_bullish();
        (self.prev_macd_bull == 1 && current == 0) as i8
    }

    pub fn macd_hist_inc(&self) -> i8 {
        (self.hist > self.prev_macd_hist) as i8
    }
}

pub struct Atr {
    period: usize,
    prev_atr: f32,
    prev_close: f32,
    count: usize,
    sum_tr: f32,
    initialized: bool,
}

impl Atr {
    pub fn new(period: usize, initial_close: f32) -> Self {
        Self {
            period,
            prev_atr: 0.0,
            prev_close: initial_close,
            count: 0,
            sum_tr: 0.0,
            initialized: false,
        }
    }

    pub fn update(&mut self, high: f32, low: f32, close: f32) -> f32 {
        let tr = (high - low)
            .max((high - self.prev_close).abs())
            .max((low - self.prev_close).abs());
        if !self.initialized {
            self.sum_tr += tr;
            self.count += 1;
            if self.count == self.period {
                self.prev_atr = self.sum_tr / self.period as f32;
                self.initialized = true;
            }
            self.prev_close = close;
            return self.prev_atr;
        }
        self.prev_atr = (self.prev_atr * (self.period as f32 - 1.0) + tr) / self.period as f32;
        self.prev_close = close;
        self.prev_atr
    }

    pub fn get(&self) -> f32 {
        self.prev_atr
    }

    pub fn high_volatility(&self, threshold: f32) -> i8 {
        (self.prev_atr > threshold) as i8
    }
}

pub struct Ema {
    pub ema_fast: _Ema,
    pub ema_medium: _Ema,
    pub ema_slow: _Ema,
    pub last_price: f32,
}

impl Ema {
    pub fn new(
        ema_fast_period: usize,
        ema_medium_period: usize,
        ema_slow_period: usize,
        initial_price: f32,
    ) -> Self {
        Self {
            ema_fast: _Ema::new(ema_fast_period, initial_price),
            ema_medium: _Ema::new(ema_medium_period, initial_price),
            ema_slow: _Ema::new(ema_slow_period, initial_price),
            last_price: initial_price,
        }
    }

    pub fn update(&mut self, new_price: f32) {
        self.ema_fast._update(new_price);
        self.ema_medium._update(new_price);
        self.ema_slow._update(new_price);
        self.last_price = new_price;
    }

    pub fn ema_f_s(&self) -> i8 {
        (self.ema_fast.get() > self.ema_slow.get()) as i8
    }

    pub fn ema_f_m(&self) -> i8 {
        (self.ema_fast.get() > self.ema_medium.get()) as i8
    }

    pub fn ema_price_m(&self) -> i8 {
        (self.last_price > self.ema_medium.get()) as i8
    }

    pub fn ema_triple_bull(&self) -> i8 {
        (self.ema_fast.get() > self.ema_medium.get() && self.ema_medium.get() > self.ema_slow.get())
            as i8
    }
}

pub struct BollingerBands<const N: usize> {
    std_dev: f32,
    closes: [f32; N],
    idx: usize,
    len: usize,
    mean: f32,
    m2: f32,
}

impl<const N: usize> BollingerBands<N> {
    #[inline(always)]
    pub fn new(std_dev: f32, initial_close: f32) -> Self {
        let mut closes = [0.0; N];
        closes[0] = initial_close;
        Self {
            std_dev,
            closes,
            idx: 1,
            len: 1,
            mean: initial_close,
            m2: 0.0,
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
        let upper = self.mean + self.std_dev * std;
        let lower = self.mean - self.std_dev * std;
        (upper, self.mean, lower)
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
        if (upper - lower).abs() < 1e-8 {
            0.5
        } else {
            (price - lower) / (upper - lower)
        }
    }

    #[inline(always)]
    pub fn bb_extreme_high(&self, bb_position: f32) -> i8 {
        (bb_position > 0.9) as i8
    }

    #[inline(always)]
    pub fn bb_extreme_low(&self, bb_position: f32) -> i8 {
        (bb_position < 0.1) as i8
    }
}

pub struct StochasticOscillator<const N: usize, const K: usize, const D: usize> {
    highs: [f32; N],
    lows: [f32; N],
    closes: [f32; N],
    k_values: [f32; K],
    high_idx: usize,
    low_idx: usize,
    close_idx: usize,
    k_idx: usize,
    len: usize,
    k_len: usize,
}

impl<const N: usize, const K: usize, const D: usize> StochasticOscillator<N, K, D> {
    #[inline(always)]
    pub fn new(initial_high: f32, initial_low: f32, initial_close: f32) -> Self {
        let mut highs = [0.0; N];
        let mut lows = [0.0; N];
        let mut closes = [0.0; N];
        let mut k_values = [0.0; K];
        highs[0] = initial_high;
        lows[0] = initial_low;
        closes[0] = initial_close;
        k_values[0] = 0.0;
        Self {
            highs,
            lows,
            closes,
            k_values,
            high_idx: 1,
            low_idx: 1,
            close_idx: 1,
            k_idx: 0,
            len: 1,
            k_len: 0,
        }
    }

    #[inline(always)]
    pub fn update(&mut self, high: f32, low: f32, close: f32) -> (f32, f32) {
        self.highs[self.high_idx % N] = high;
        self.lows[self.low_idx % N] = low;
        self.closes[self.close_idx % N] = close;
        self.high_idx += 1;
        self.low_idx += 1;
        self.close_idx += 1;
        if self.len < N {
            self.len += 1;
        }
        let min_low = self
            .lows
            .iter()
            .take(self.len)
            .cloned()
            .fold(f32::INFINITY, f32::min);
        let max_high = self
            .highs
            .iter()
            .take(self.len)
            .cloned()
            .fold(f32::NEG_INFINITY, f32::max);
        let k = if (max_high - min_low).abs() < 1e-8 {
            0.0
        } else {
            100.0 * (close - min_low) / (max_high - min_low)
        };
        self.k_values[self.k_idx % K] = k;
        self.k_idx += 1;
        if self.k_len < K {
            self.k_len += 1;
        }
        let k_smooth = self.k_values.iter().take(self.k_len).sum::<f32>() / self.k_len as f32;
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
    prev_highs_pat: Option<f32>,
    prev_lows_pat: Option<f32>,
    last_resistance: f32,
    last_support: f32,
    last_high_pat: f32,
    last_low_pat: f32,
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
            sr_idx: 1,
            pat_idx: 1,
            sr_len: 1,
            pat_len: 1,
            prev_highs_pat: None,
            prev_lows_pat: None,
            last_resistance: initial_high,
            last_support: initial_low,
            last_high_pat: initial_high,
            last_low_pat: initial_low,
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
        self.last_resistance = self
            .highs_sr
            .iter()
            .take(self.sr_len)
            .cloned()
            .fold(f32::NEG_INFINITY, f32::max);
        self.last_support = self
            .lows_sr
            .iter()
            .take(self.sr_len)
            .cloned()
            .fold(f32::INFINITY, f32::min);
        if self.pat_len == PAT {
            self.prev_highs_pat = Some(self.last_high_pat);
            self.prev_lows_pat = Some(self.last_low_pat);
        }
        self.highs_pat[self.pat_idx % PAT] = high;
        self.lows_pat[self.pat_idx % PAT] = low;
        self.pat_idx += 1;
        if self.pat_len < PAT {
            self.pat_len += 1;
        }
        self.last_high_pat = self
            .highs_pat
            .iter()
            .take(self.pat_len)
            .cloned()
            .fold(f32::NEG_INFINITY, f32::max);
        self.last_low_pat = self
            .lows_pat
            .iter()
            .take(self.pat_len)
            .cloned()
            .fold(f32::INFINITY, f32::min);
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
        if let (Some(prev_high), Some(prev_low)) = (self.prev_highs_pat, self.prev_lows_pat) {
            (self.last_high_pat > prev_high && self.last_low_pat > prev_low) as i8
        } else {
            0
        }
    }
    #[inline(always)]
    pub fn downtrend_pattern(&self) -> i8 {
        if let (Some(prev_high), Some(prev_low)) = (self.prev_highs_pat, self.prev_lows_pat) {
            (self.last_high_pat < prev_high && self.last_low_pat < prev_low) as i8
        } else {
            0
        }
    }
}

pub struct EmaIndicator {
    _period: usize,
    alpha: f32,
    current_value: Option<f32>,
}

impl EmaIndicator {
    pub fn new(period: usize) -> Self {
        let alpha = 2.0 / (period + 1) as f32;
        Self {
            _period: period,
            alpha,
            current_value: None,
        }
    }

    pub fn update(&mut self, value: f32) -> f32 {
        match self.current_value {
            Some(prev) => {
                let new_value = self.alpha * value + (1.0 - self.alpha) * prev;
                self.current_value = Some(new_value);
                new_value
            }
            None => {
                self.current_value = Some(value);
                value
            }
        }
    }
}

pub struct RsiIndicator {
    period: usize,
    gains: VecDeque<f32>,
    losses: VecDeque<f32>,
    prev_price: Option<f32>,
}

impl RsiIndicator {
    pub fn new(period: usize) -> Self {
        Self {
            period,
            gains: VecDeque::with_capacity(period),
            losses: VecDeque::with_capacity(period),
            prev_price: None,
        }
    }

    pub fn update(&mut self, price: f32) -> Option<f32> {
        if let Some(prev_price) = self.prev_price {
            let change = price - prev_price;
            if change > 0.0 {
                self.gains.push_back(change);
                self.losses.push_back(0.0);
            } else {
                self.gains.push_back(0.0);
                self.losses.push_back(-change);
            }

            if self.gains.len() > self.period {
                self.gains.pop_front();
                self.losses.pop_front();
            }

            if self.gains.len() == self.period {
                let avg_gain: f32 = self.gains.iter().sum::<f32>() / self.period as f32;
                let avg_loss: f32 = self.losses.iter().sum::<f32>() / self.period as f32;

                if avg_loss == 0.0 {
                    Some(100.0)
                } else {
                    let rs = avg_gain / avg_loss;
                    Some(100.0 - (100.0 / (1.0 + rs)))
                }
            } else {
                None
            }
        } else {
            None
        }
    }
}

pub struct MacdIndicator {
    fast_ema: _Ema,
    slow_ema: _Ema,
    signal_ema: _Ema,
    current_macd: Option<f32>,
    current_signal: Option<f32>,
}

impl MacdIndicator {
    pub fn new(
        fast_period: usize,
        slow_period: usize,
        signal_period: usize,
        initial_price: f32,
    ) -> Self {
        Self {
            fast_ema: _Ema::new(fast_period, initial_price),
            slow_ema: _Ema::new(slow_period, initial_price),
            signal_ema: _Ema::new(signal_period, 0.0),
            current_macd: None,
            current_signal: None,
        }
    }

    pub fn update(&mut self, price: f32) -> (Option<f32>, Option<f32>) {
        let fast = self.fast_ema._update(price);
        let slow = self.slow_ema._update(price);
        let macd = fast - slow;
        self.current_macd = Some(macd);

        if let Some(macd) = self.current_macd {
            let signal = self.signal_ema._update(macd);
            self.current_signal = Some(signal);
        }

        (self.current_macd, self.current_signal)
    }

    pub fn get_histogram(&self) -> Option<f32> {
        match (self.current_macd, self.current_signal) {
            (Some(macd), Some(signal)) => Some(macd - signal),
            _ => None,
        }
    }
}
