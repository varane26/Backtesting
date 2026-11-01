"""The seven strategies from strategies/strategy_0N.pl, ported to the engine.

All logic runs on 1-minute bars in CT (data1). `tf` is the signal-bar size in
minutes, standing in for the strategy's own signal timeframe (data2 or the
in-code bars). Size is one contract; dollar results scale linearly with size.
Each function runs bars[i0:i1] and returns the engine.
"""
from engine import Engine, TFBars, hhmm, MKT, STOP, LIMIT, BUY, SHORT, XLONG, XSHORT


def s01_orb_ema_gap(b, tf, i0, i1, p):
    """Opening range 08:30-08:45 CT, long on a signal-bar close above the range high and
    EMA200 on a gap-up day; stop at the range low, target 1.5R; flat 15:40, re-enter 17:00."""
    O, H, L, C, V, T, D, CA = b.o, b.h, b.l, b.c, b.v, b.hhmm, b.day, b.cabs
    eng = Engine(CA, p["tick"])
    tfb = TFBars(tf)
    alpha = 2.0 / 201
    ema = None
    rng_hi = rng_lo = 0.0
    rng_date = None
    rth_date = None
    rth_open = last_rth_c = prev_rth_c = 0.0
    gap = 0.0
    c2 = 0.0
    ent_wait = re_wait = False
    sd_entry = stop_px = tgt_px = 0.0
    re_dir = 0
    re_stop = re_tgt = 0.0
    for i in range(i0, i1):
        o, h, l, c = O[i], H[i], L[i], C[i]
        if eng.orders:
            eng.fill(i, o, h, l)
        t = T[i]
        d = D[i]
        if 830 < t <= 1500:
            if d != rth_date:
                prev_rth_c = last_rth_c
                rth_open = o
                rth_date = d
            last_rth_c = c
        gap_ok = rth_date == d and prev_rth_c > 0
        if gap_ok:
            gap = rth_open - prev_rth_c
        # opening range from the 1-minute bars 08:30-08:45 (same range for every tf)
        if 830 < t <= 845:
            if d != rng_date:
                rng_hi, rng_lo, rng_date = h, l, d
            else:
                if h > rng_hi:
                    rng_hi = h
                if l < rng_lo:
                    rng_lo = l
        sig = False
        closed = tfb.update(CA[i], o, h, l, c, V[i])
        if closed:
            for end, bo, bh, bl, bc, bv in closed:
                ema = bc if ema is None else ema + alpha * (bc - ema)
                c2 = bc
                t2 = hhmm(end)
                sig = (end // 1440 == rng_date and t2 > 845 and t2 <= 1535
                       and bc > rng_hi and bc > ema and gap_ok and gap >= p["gap_min"])
        lucid = 1540 <= t < 1700
        pos = eng.pos
        if ent_wait:
            if pos != 0:
                stop_px = eng.entry_px - sd_entry
                tgt_px = eng.entry_px + 1.5 * sd_entry
            ent_wait = False
        if re_wait:
            if pos != 0:
                stop_px, tgt_px = re_stop, re_tgt
            re_wait = False
        if pos != 0:
            if lucid:
                re_dir, re_stop, re_tgt = pos, stop_px, tgt_px
                eng.order(MKT, XLONG, None, "Flat")
            else:
                eng.order(STOP, XLONG, stop_px, "SL")
                eng.order(LIMIT, XLONG, tgt_px, "TP")
        if re_dir != 0 and pos == 0 and (t == 1600 or 1701 <= t < 1800):
            eng.order(MKT, BUY, None, "LR")
            eng.order(STOP, XLONG, re_stop, "LR_SL")
            eng.order(LIMIT, XLONG, re_tgt, "LR_TP")
            re_dir = 0
            re_wait = True
        if pos == 0 and re_dir == 0 and not re_wait and not lucid and sig:
            sd = c2 - rng_lo
            if sd > 0:
                sd_entry = sd
                stop_px = c2 - sd
                tgt_px = c2 + 1.5 * sd
                eng.order(MKT, BUY, None, "L")
                eng.order(STOP, XLONG, stop_px, "SL0")
                eng.order(LIMIT, XLONG, tgt_px, "TP0")
                ent_wait = True
    return eng


def s02_sma_ema_pullback(b, tf, i0, i1, p):
    """Two-leg long pullback system on signal bars (SMA414/EMA16 and SMA882/EMA1293/EMA6);
    flat 15:40, unconditional re-open at 17:00 (LucidMode 1)."""
    O, H, L, C, V, T, CA = b.o, b.h, b.l, b.c, b.v, b.hhmm, b.cabs
    eng = Engine(CA, p["tick"])
    tfb = TFBars(tf)
    n1, n2 = 414, 882
    a1, a2f, a3 = 2.0 / 17, 2.0 / 7, 2.0 / 1294
    warm = 1293
    closes = []
    sum1 = sum2 = 0.0
    nb = 0
    e1 = e2f = m3 = 0.0
    prev_low = 0.0
    leg = 0
    re_dir = 0
    for i in range(i0, i1):
        o, h, l, c = O[i], H[i], L[i], C[i]
        if eng.orders:
            eng.fill(i, o, h, l)
        t = T[i]
        ent_ev = exit_ev = False
        closed = tfb.update(CA[i], o, h, l, c, V[i])
        if closed:
            for end, bo, bh, bl, bc, bv in closed:
                nb += 1
                closes.append(bc)
                sum1 += bc
                sum2 += bc
                if nb > n1:
                    sum1 -= closes[nb - 1 - n1]
                if nb > n2:
                    sum2 -= closes[nb - 1 - n2]
                if nb == 1:
                    e1 = e2f = m3 = bc
                else:
                    e1 += a1 * (bc - e1)
                    e2f += a2f * (bc - e2f)
                    m3 += a3 * (bc - m3)
                lower_c = nb > 1 and bc < prev_low
                b1 = nb >= n1 and bc > sum1 / n1 and bc < e1 and nb > warm
                x1 = bc > e1 and lower_c
                b2 = nb >= n2 and bc < sum2 / n2 and bc > m3 and bc < e2f and nb > warm
                x2 = bc > e2f and lower_c
                prev_leg = leg
                if leg == 1 and x1:
                    leg = 0
                elif leg == 2 and x2:
                    leg = 0
                elif leg == 0:
                    leg = 1 if b1 else (2 if b2 else 0)
                ent_ev = leg > 0 and prev_leg == 0
                exit_ev = leg == 0 and prev_leg > 0
                prev_low = bl
        pos = eng.pos
        if pos != 0 and (t < 1540 or t >= 1700):
            re_dir = 0
        if pos == 1 and closed and exit_ev:
            eng.order(MKT, XLONG, None, "LX")
        if pos == 0 and re_dir == 0 and closed and not (1540 <= t < 1600) and ent_ev:
            eng.order(MKT, BUY, None, "L")
        if pos == 1 and 1540 <= t < 1700:
            re_dir = 1
            eng.order(MKT, XLONG, None, "Flat")
        if re_dir == 1 and pos == 0 and 1600 <= t < 1759:
            eng.order(MKT, BUY, None, "Re")
    return eng


def _daily_rth_strategy(b, i0, i1, rule, stop_mult, tick):
    """Shared shell of strategies 03 and 07: RTH daily bars (08:30-15:00 CT) built on
    data1, rules evaluated on the 15:00 bar, exit at C > H[1], optional fixed stop,
    flat 15:40 and re-open at 17:00 with the same stop. `rule(state)` returns
    True for a long entry on the day just completed."""
    O, H, L, C, T, D, DW = b.o, b.h, b.l, b.c, b.hhmm, b.day, b.dow
    eng = Engine(b.cabs, tick)
    day_open = False
    rdate = rdow = None
    rh = rl = rc = 0.0
    st = {"h": [], "l": [], "c": [], "dow": [], "atr": 0.0, "n": 0}
    stop_dist = stop_px = 0.0
    re_dir = 0
    re_stop = 0.0
    re_sent = False
    prev_mp = 0
    for i in range(i0, i1):
        o, h, l, c = O[i], H[i], L[i], C[i]
        if eng.orders:
            eng.fill(i, o, h, l)
        t = T[i]
        d = D[i]
        just_re = False
        if re_sent:
            just_re = True
            re_sent = False
            re_dir = 0
        mp = eng.pos
        if mp != 0 and prev_mp == 0:
            if just_re:
                stop_px = re_stop
            elif stop_dist > 0:
                stop_px = eng.entry_px - mp * stop_dist
            else:
                stop_px = 0.0
        is_rth = 830 < t <= 1500
        fin = None
        if day_open and (not is_rth or d != rdate):
            fin = (rdow, rh, rl, rc)
            day_open = False
        if is_rth:
            if not day_open:
                day_open = True
                rdate, rdow, rh, rl = d, DW[i], h, l
            else:
                if h > rh:
                    rh = h
                if l < rl:
                    rl = l
            rc = c
            if t == 1500 and fin is None:
                fin = (rdow, rh, rl, rc)
                day_open = False
        if fin is not None:
            fdow, fh, fl, fc = fin
            st["h"].append(fh)
            st["l"].append(fl)
            st["c"].append(fc)
            st["dow"].append(fdow)
            st["n"] += 1
            n = st["n"]
            if n == 1:
                st["atr"] = fh - fl
            else:
                pc = st["c"][-2]
                tr = max(fh - fl, abs(fh - pc), abs(fl - pc))
                st["atr"] += (tr - st["atr"]) / 14
            ent_l = rule(st)
            ex_l = n >= 2 and fc > st["h"][-2]
            stop_dist = stop_mult * st["atr"] if stop_mult > 0 else 0.0
            no_entry = 1540 <= t < 1700
            mp = eng.pos
            if mp == 1:
                if ex_l:
                    eng.order(MKT, XLONG, None, "LX")
            elif mp == 0 and re_dir == 0 and not re_sent and not no_entry and ent_l:
                eng.order(MKT, BUY, None, "L")
                if stop_dist > 0:
                    eng.order(STOP, XLONG, fc - stop_dist, "SL1")
        mp = eng.pos
        if mp == 1 and stop_px > 0:
            eng.order(STOP, XLONG, stop_px, "SL")
        if mp != 0 and 1540 <= t < 1700:
            if re_dir == 0:
                re_dir = mp
                re_stop = stop_px
            eng.order(MKT, XLONG, None, "Flat")
        if re_dir != 0 and mp == 0 and not re_sent and (t == 1600 or 1700 < t < 1800):
            eng.order(MKT, BUY, None, "Re")
            if re_stop > 0:
                eng.order(STOP, XLONG, re_stop, "ReSL")
            re_sent = True
        prev_mp = eng.pos
    return eng


def s03_monday_down(b, tf, i0, i1, p):
    """Long at Monday's RTH close after a down Monday; exit C > H[1]; stop 4 x ATR14."""
    def rule(st):
        c = st["c"]
        return st["n"] >= 2 and c[-1] < c[-2] and st["dow"][-1] == 1
    return _daily_rth_strategy(b, i0, i1, rule, 4.0, p["tick"])


def s07_macd_ibs(b, tf, i0, i1, p):
    """Long at the RTH close when (MACD hist fell 3 days and < 0 and IBS < 0.2) or IBS < 0.1;
    exit C > H[1]; no stop."""
    m = {"e12": 0.0, "e26": 0.0, "sig": 0.0, "hist": []}

    def rule(st):
        n = st["n"]
        fc, fh, fl = st["c"][-1], st["h"][-1], st["l"][-1]
        if n == 1:
            m["e12"] = m["e26"] = fc
            macd = 0.0
            m["sig"] = macd
        else:
            m["e12"] += (2.0 / 13) * (fc - m["e12"])
            m["e26"] += (2.0 / 27) * (fc - m["e26"])
            macd = m["e12"] - m["e26"]
            m["sig"] += (2.0 / 10) * (macd - m["sig"])
        hist = m["hist"]
        hist.append(macd - m["sig"])
        ibs = (fc - fl) / (fh - fl) if fh - fl > 0 else 0.5
        mo = n >= 4 and hist[-1] < 0 and hist[-4] > hist[-3] > hist[-2] > hist[-1]
        return (mo and ibs < 0.2) or ibs < 0.1
    return _daily_rth_strategy(b, i0, i1, rule, 0.0, p["tick"])


def s04_vwap_continuation(b, tf, i0, i1, p):
    """VWAP-trend pullback entries 09:30-14:30 CT on signal bars, fixed point stop/target,
    flat 14:55 CT, max 4 trades and 2 losers a day. Works in NY minutes like the original."""
    O, H, L, C, V, CA = b.o, b.h, b.l, b.c, b.v, b.cabs
    eng = Engine(CA, p["tick"])
    tfb = TFBars(tf)
    slope_bars = max(1, round(15 / tf))
    mom_bars = max(1, round(60 / tf))
    need = max(slope_bars, mom_bars)
    mom_min = p["mom_pct"] / 100.0
    l_sl, l_tp, s_sl, s_tp = p["long_stop"], p["long_tgt"], p["short_stop"], p["short_tgt"]
    cl_r = []
    vw_r = []
    n5 = 0
    cur_day = None
    cum_pv = cum_v = 0.0
    wait = 0
    trades_today = losses_today = 0
    prev_tt = 0
    sl = tp = 0.0
    for i in range(i0, i1):
        o, h, l, c = O[i], H[i], L[i], C[i]
        if eng.orders:
            eng.fill(i, o, h, l)
        ca = CA[i]
        if len(eng.trades) != prev_tt:
            tr = eng.trades[-1]
            trades_today += 1
            if tr[2] * (tr[4] - tr[3]) < 0:
                losses_today += 1
            prev_tt = len(eng.trades)
        ny = (ca + 60) % 1440
        day_ny = (ca + 60) // 1440
        if eng.pos == 1 and 955 <= ny < 1080:
            eng.order(MKT, XLONG, None, "EOD")
        elif eng.pos == -1 and 955 <= ny < 1080:
            eng.order(MKT, XSHORT, None, "EOD")
        go = 0
        closed = tfb.update(ca, o, h, l, c, V[i])
        if closed:
            for end, bo, bh, bl, bc, bv in closed:
                c5 = (end + 60) % 1440
                if day_ny != cur_day:
                    cur_day = day_ny
                    cum_pv = cum_v = 0.0
                    trades_today = losses_today = 0
                    wait = 0
                if 570 <= c5 <= 960:
                    cum_pv += (bh + bl + bc) / 3.0 * bv
                    cum_v += bv
                vw = cum_pv / cum_v if cum_v > 0 else bc
                cl_r.append(bc)
                vw_r.append(vw)
                lb = sb = False
                if n5 >= need:
                    vb = vw_r[n5 - slope_bars]
                    cb = cl_r[n5 - mom_bars]
                    if cb > 0:
                        mom = bc / cb - 1
                        lb = bc > vw and vw > vb and mom >= mom_min
                        sb = bc < vw and vw < vb and mom <= -mom_min
                if (630 <= c5 < 930 and eng.pos == 0 and trades_today < 4
                        and losses_today < 2):
                    if wait == 0:
                        if lb:
                            wait = 1
                        elif sb:
                            wait = -1
                    elif wait == 1:
                        if not lb:
                            wait = -1 if sb else 0
                        elif bc < bo:
                            go = 1
                    else:
                        if not sb:
                            wait = 1 if lb else 0
                        elif bc > bo:
                            go = -1
                n5 += 1
        if go == 1:
            wait = 0
            sl, tp = l_sl, l_tp
            eng.order(MKT, BUY, None, "L", attach=(sl, tp))
        elif go == -1:
            wait = 0
            sl, tp = s_sl, s_tp
            eng.order(MKT, SHORT, None, "S", attach=(sl, tp))
        if eng.pos == 1:
            eng.order(STOP, XLONG, eng.entry_px - sl, "SL")
            eng.order(LIMIT, XLONG, eng.entry_px + tp, "TP")
        elif eng.pos == -1:
            eng.order(STOP, XSHORT, eng.entry_px + sl, "SL")
            eng.order(LIMIT, XSHORT, eng.entry_px - tp, "TP")
    return eng


def s05_overnight_long(b, tf, i0, i1, p):
    """Mon-Wed: if the signal bar closing 16:00 CT closes below EMA200 of signal bars,
    buy the 17:00 reopen and sell the 08:30 CT open."""
    O, H, L, C, V, T, DW, CA = b.o, b.h, b.l, b.c, b.v, b.hhmm, b.dow, b.cabs
    eng = Engine(CA, p["tick"])
    tfb = TFBars(tf)
    alpha = 2.0 / 201
    ema = None
    nb2 = 0
    t2 = -1
    c5 = 0.0
    for i in range(i0, i1):
        o, h, l, c = O[i], H[i], L[i], C[i]
        if eng.orders:
            eng.fill(i, o, h, l)
        t = T[i]
        closed = tfb.update(CA[i], o, h, l, c, V[i])
        if closed:
            for end, bo, bh, bl, bc, bv in closed:
                nb2 += 1
                ema = bc if ema is None else ema + alpha * (bc - ema)
                t2 = hhmm(end)
                c5 = bc
        pos = eng.pos
        if pos == 0 and t == 1600 and t2 == 1600 and nb2 > 300 and 1 <= DW[i] <= 3 and c5 < ema:
            eng.order(MKT, BUY, None, "L")
        if pos == 1 and 830 <= t < 1700:
            eng.order(MKT, XLONG, None, "LX" if t < 1540 else "Flat")
    return eng


def s06_channel_breakout(b, tf, i0, i1, p):
    """Long when a 1-minute high clears the 5-bar channel high of signal bars + 1 tick;
    exit on a channel-low break or a 2 x ATR14 trailing stop; flat 15:40, no re-entry."""
    O, H, L, C, V, T, CA = b.o, b.h, b.l, b.c, b.v, b.hhmm, b.cabs
    eng = Engine(CA, p["tick"])
    tfb = TFBars(tf)
    tick = p["tick"]
    ha = []
    la = []
    n2 = 0
    atr2 = pc2 = 0.0
    up = dn = atr_lvl = 0.0
    lvl_ok = False
    best_h = stop_px = trail = e_stop = 0.0
    prev_mp = 0
    for i in range(i0, i1):
        o, h, l, c = O[i], H[i], L[i], C[i]
        if eng.orders:
            eng.fill(i, o, h, l)
        t = T[i]
        mp = eng.pos
        if mp != 0 and prev_mp == 0:
            stop_px = eng.entry_px - e_stop
            trail = e_stop
            best_h = eng.entry_px
        if mp == 1:
            if 1540 <= t < 1700:
                eng.order(MKT, XLONG, None, "Flat")
            else:
                if h > best_h:
                    best_h = h
                if best_h - trail > stop_px:
                    stop_px = best_h - trail
                if lvl_ok and l <= dn - tick:
                    eng.order(MKT, XLONG, None, "Ch")
                else:
                    eng.order(STOP, XLONG, stop_px, "SL")
        if (mp == 0 and lvl_ok and h >= up + tick and (t <= 1500 or t >= 1701)
                and atr_lvl > 0):
            e_stop = 2.0 * atr_lvl
            eng.order(MKT, BUY, None, "L")
            eng.order(STOP, XLONG, c - e_stop, "SL")
        closed = tfb.update(CA[i], o, h, l, c, V[i])
        if closed:
            for end, bo, bh, bl, bc, bv in closed:
                n2 += 1
                if n2 == 1:
                    atr2 = bh - bl
                else:
                    tr = max(bh - bl, abs(bh - pc2), abs(bl - pc2))
                    atr2 += (tr - atr2) / 14
                pc2 = bc
                ha.append(bh)
                la.append(bl)
                if len(ha) > 5:
                    del ha[0]
                    del la[0]
                if n2 >= 5:
                    up = max(ha)
                    dn = min(la)
                    lvl_ok = True
                atr_lvl = atr2
        prev_mp = mp
    return eng


def s08_forecast_to_fill(b, tf, i0, i1, p):
    """Forecast-to-Fill trend (arXiv:2511.08571 port): long while EMA(50) of signal bars rises
    (Pbull = sigmoid(2 x slope / StDev14) > 0.5), stop = max(entry - 2 ATR14, highest high since
    entry - 1.5 ATR14), exit on a regime flip or after 30 bars. tf = 0 uses session daily bars
    (17:00-16:00 CT). VolScalar is computed in the original but never sizes the trade, so it is
    left out. p["lucid_flat"]: flat at 15:40 CT and re-open at 17:00 with the same stop state.
    Improvement options (defaults = the original): p["entry_thr"] / p["exit_thr"] enter above /
    exit at or below these Pbull levels (e.g. 0.6 / 0.4); p["slope_norm"] = "atr" divides the EMA
    change by ATR(14) instead of StDev(Close, 14); p["rth_only"] allows entries only on signal bars
    closing 08:31-15:00 CT."""
    import math
    O, H, L, C, V, T, D, CA = b.o, b.h, b.l, b.c, b.v, b.hhmm, b.day, b.cabs
    eng = Engine(CA, p["tick"])
    lucid = p.get("lucid_flat", False)
    thr_in, thr_out = p.get("entry_thr", 0.5), p.get("exit_thr", 0.5)
    norm_atr = p.get("slope_norm", "stdev") == "atr"
    rth_only = p.get("rth_only", False)
    tfb = TFBars(tf) if tf else None
    sk = None
    so = sh = sl_ = sc = 0.0
    live = False
    a_ema = 2.0 / 51
    ema = ema_prev = None
    closes = []
    trs = []
    prev_c = None
    nbar = 0
    in_trade = False
    entry_bar = 0
    entry_px = 0.0
    hh = 0.0
    standing = None
    re_dir = 0
    prev_mp = 0

    def on_bar(bh, bl, bc):
        nonlocal ema, ema_prev, prev_c, nbar, in_trade, entry_bar, entry_px, hh, standing, re_dir
        nbar += 1
        ema_prev = ema
        ema = bc if ema is None else ema + a_ema * (bc - ema)
        closes.append(bc)
        if len(closes) > 14:
            del closes[0]
        trs.append(bh - bl if prev_c is None else max(bh - bl, abs(bh - prev_c), abs(bl - prev_c)))
        if len(trs) > 14:
            del trs[0]
        prev_c = bc
        if ema_prev is None or len(closes) < 14:
            return
        m = sum(closes) / 14
        sd = math.sqrt(sum((x - m) ** 2 for x in closes) / 14)
        atr = sum(trs) / len(trs)
        den = atr if norm_atr else sd
        slope = (ema - ema_prev) / den if den != 0 else 0.0
        pbull = 1.0 / (1.0 + math.exp(-slope * 2.0))
        mp = 1 if (eng.pos == 1 or re_dir == 1) else 0
        entry_ok = not rth_only or 830 < T[i] <= 1500
        if pbull > thr_in and mp == 0 and entry_ok and not (lucid and 1540 <= T[i] < 1600):
            eng.order(MKT, BUY, None, "F2F_LE")
        standing = None
        if mp == 1:
            if not in_trade:
                in_trade = True
                entry_bar = nbar
                entry_px = eng.entry_px
                hh = bh
            hh = max(hh, bh)
            bars_in = nbar - entry_bar
            standing = max(entry_px - 2.0 * atr, hh - 1.5 * atr)
            if pbull <= thr_out or bars_in >= 30:
                eng.order(MKT, XLONG, None, "RegimeExit" if pbull <= thr_out else "TimeOut")
                if eng.pos == 0:            # flat for the Lucid close: drop the 17:00 re-entry
                    re_dir = 0
                    in_trade = False
                    standing = None
        else:
            in_trade = False

    for i in range(i0, i1):
        o, h, l, c = O[i], H[i], L[i], C[i]
        if eng.orders:
            eng.fill(i, o, h, l)
        t = T[i]
        if eng.pos == 0 and prev_mp == 1 and re_dir == 0:
            in_trade = False
            standing = None
        if tfb is not None:
            closed = tfb.update(CA[i], o, h, l, c, V[i])
            if closed:
                for end, bo, bh, bl, bc, bv in closed:
                    on_bar(bh, bl, bc)
        else:
            k = D[i] + (1 if t > 1600 else 0)
            if k != sk:
                if live:
                    on_bar(sh, sl_, sc)
                sk, so, sh, sl_, sc, live = k, o, h, l, c, True
            else:
                sh, sl_, sc = max(sh, h), min(sl_, l), c
            if t == 1600:
                on_bar(sh, sl_, sc)
                live = False
        if lucid:
            if eng.pos == 1 and 1540 <= t < 1700:
                re_dir = 1
                eng.order(MKT, XLONG, None, "Flat")
            elif re_dir == 1 and eng.pos == 0 and (t == 1600 or 1701 <= t < 1800):
                eng.order(MKT, BUY, None, "Re")
            elif eng.pos == 1 and t >= 1701:
                re_dir = 0
        if eng.pos == 1 and standing is not None:
            eng.order(STOP, XLONG, standing, "ATRExit")
        prev_mp = eng.pos
    return eng


STRATEGIES = {
    "S01": ("ORB + EMA200 + gap filter", s01_orb_ema_gap, True),
    "S02": ("SMA/EMA pullback, 2 legs", s02_sma_ema_pullback, True),
    "S03": ("Monday down-day long", s03_monday_down, False),
    "S04": ("VWAP continuation", s04_vwap_continuation, True),
    "S05": ("Overnight long below EMA200", s05_overnight_long, True),
    "S06": ("Channel breakout + ATR trail", s06_channel_breakout, True),
    "S07": ("MACD / IBS daily mean reversion", s07_macd_ibs, False),
    "S08": ("Forecast-to-Fill trend", s08_forecast_to_fill, True),
}
