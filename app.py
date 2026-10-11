"""
AI TRADING ARENA v1.2.0 -- DESKTOP EDITION
Ten AI traders battle across a 4-quarter season: shorts, margin calls,
dividends, herd contagion, rumor events, circuit breakers, volatility
regimes, candlestick charts, trader dossiers, spectator betting with a
persistent bankroll + Hall of Fame, procedural sound.

Run:       python ai_trading_arena_desktop.py
Requires:  pip install pygame          (no other dependencies)
Package:   pyinstaller --onefile --windowed --name "AI-Trading-Arena" ai_trading_arena_desktop.py
"""

import array
import json
import math
import os
import random
import sys
import traceback

import pygame

# ----------------------------------------------------------------- config --
__version__ = "1.2.0"
WFL = getattr(pygame, "WINDOWFOCUSLOST", -1)
MOUSE = (640, 430)
QUIT_HINT = "ESC quit"

WIDTH, HEIGHT = 1280, 860
FPS          = 60
VIS          = 260
CANDLE_PER   = 6
CANDLE_N     = 80
QUARTER      = 300
QUARTERS     = 4
TOTAL        = QUARTER * QUARTERS
SPEEDS       = [(20, "1x"), (40, "2x"), (80, "4x"), (160, "8x")]
IMPACT       = 150000.0
START_CASH   = 10_000.0
SHORT_CAP    = 0.45

BG     = (10, 14, 20)
PANEL  = (22, 28, 38)
PANEL2 = (15, 20, 28)
BORDER = (46, 56, 72)
TEXT   = (226, 232, 240)
DIM    = (128, 140, 158)
GOLD   = (250, 204, 21)
GREEN  = (34, 197, 140)
RED    = (246, 88, 80)
BLUE   = (96, 140, 235)
FVGOLD = (190, 160, 60)

SIDE_COLORS = {"BUY": GREEN, "SELL": RED, "SHORT": (255, 130, 90), "COVER": (86, 214, 255)}

STOCK_DEFS = [
    ("NOVA", "Nova Dynamics",    "AI Semis",     184.0, 0.011, 0.0009),
    ("HELX", "Helix Bio",        "Biotech",       46.0, 0.019, 0.0019),
    ("GRNZ", "GreenZoom Energy", "Solar",         68.0, 0.014, 0.0012),
    ("BRCK", "Brickstone REIT",  "Real Estate",  312.0, 0.005, 0.0005),
    ("QNTM", "Quantic Robotics", "Robotics",      97.0, 0.013, 0.0011),
    ("ORBT", "Orbital Freight",  "Aerospace",    142.0, 0.012, 0.0010),
    ("PZAZ", "Pizzazz Media",    "Streaming",     24.5, 0.017, 0.0016),
    ("DONK", "DonkeyCoin",       "Meme Asset",     3.2, 0.024, 0.0030),
]

ROSTER = [
    ("MOMENTUM MAX",   "momentum", (255, 105, 180), "chases rising charts"),
    ("QUANT QUINN",    "quant",    (86, 214, 255),  "trades SMA crossovers"),
    ("DIANE VALUE",    "value",    (250, 204, 21),  "buys below fair value"),
    ("RITA REVERT",    "meanrev",  (178, 140, 255), "fades extremes"),
    ("HEDGEFUND HANK", "hedge",    (64, 220, 140),  "rotates into strength"),
    ("PANIC PETE",     "panic",    (255, 122, 92),  "FOMO in, panic out"),
    ("CONTRA CLEO",    "contra",   (255, 160, 60),  "shorts the hype"),
    ("CHAOS CARL",     "chaos",    (150, 235, 90),  "trades on pure vibes"),
    ("YOLO YASMIN",    "yolo",     (120, 170, 255), "all-in on one horse"),
    ("INDEX IAN",      "index",    (196, 204, 214), "buys the whole market"),
]

IDLE = ["reading the tape", "waiting for a setup", "sipping coffee",
        "running models", "watching order flow", "doing nothing, smugly"]

NEWS_TEMPLATES = [
    ("{name} lands a massive government contract",   0.08,  0.30),
    ("{name} misses earnings, guidance slashed",    -0.28, -0.10),
    ("Analysts upgrade {name} to STRONG BUY",        0.05,  0.18),
    ("{name} CEO exits abruptly amid scandal",      -0.25, -0.08),
    ("{name} unveils a breakout product",            0.10,  0.28),
    ("Regulators open probe into {name}",           -0.22, -0.06),
    ("Viral hype erupts around {name}",              0.06,  0.35),
    ("Short-seller report alleges fraud at {name}", -0.30, -0.12),
    ("{name} declares a surprise special dividend",  0.04,  0.12),
    ("Supply-chain disruption hits {name}",         -0.15, -0.05),
    ("Insiders load up on {name} shares",            0.04,  0.14),
    ("Fire halts production at {name}",             -0.18, -0.06),
    ("{name} announces a stock split",               0.03,  0.10),
    ("{name} wins industry innovation award",        0.04,  0.12),
]

GLOBAL_NEWS = [
    ("Central bank slashes rates -- markets rally!",   0.04,  0.10),
    ("Central bank hikes rates -- markets wobble",    -0.10, -0.04),
    ("Euphoric risk-on wave sweeps global markets",    0.03,  0.08),
    ("Flight to cash -- investors dump risky assets", -0.09, -0.03),
    ("Crypto winter deepens -- speculators flee",     -0.12, -0.04),
]

if getattr(sys, "frozen", False):
    _DIR = os.path.dirname(sys.executable)
else:
    try:
        _DIR = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        _DIR = os.getcwd()
SAVE_PATH = os.path.join(_DIR, "arena_save.json")   # persists between runs


def load_save():
    d = {"bankroll": 1000.0, "season": 0, "wins": 0, "losses": 0, "hof": {}}
    try:
        with open(SAVE_PATH) as f:
            d.update({k: v for k, v in json.load(f).items() if k in d})
    except Exception:
        pass
    return d


def save_save(d):
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump(d, f)
    except Exception:
        pass

# ---------------------------------------------------------------- helpers --
_FONTS = {}


def F(size, bold=False, mono=False):
    key = (size, bold, mono)
    if key not in _FONTS:
        name = "consolas,menlo,couriernew,dejavusansmono" if mono \
               else "arial,helvetica,dejavusans"
        _FONTS[key] = pygame.font.SysFont(name, size, bold=bold)
    return _FONTS[key]


def txt(surf, s, x, y, size=14, color=TEXT, bold=False, mono=False, align="tl"):
    img = F(size, bold, mono).render(s, True, color)
    r = img.get_rect()
    if align == "tr":   r.topright = (x, y)
    elif align == "tc": r.midtop = (x, y)
    elif align == "mr": r.midright = (x, y)
    elif align == "ml": r.midleft = (x, y)
    elif align == "mc": r.center = (x, y)
    else:               r.topleft = (x, y)
    surf.blit(img, r)
    return r.size


def panel(surf, rect, fill=PANEL):
    pygame.draw.rect(surf, fill, rect, border_radius=10)
    pygame.draw.rect(surf, BORDER, rect, 1, border_radius=10)


def dline(surf, p1, p2, color, dash=5, gap=4, width=1):
    x1, y1 = p1
    x2, y2 = p2
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist <= 0:
        return
    ux, uy = (x2 - x1) / dist, (y2 - y1) / dist
    d = 0.0
    while d < dist:
        e = min(d + dash, dist)
        pygame.draw.line(surf, color, (int(x1 + ux * d), int(y1 + uy * d)),
                         (int(x1 + ux * e), int(y1 + uy * e)), width)
        d = e + gap


def tri(surf, cx, cy, up, color, s=5):
    if up: pts = [(cx, cy - s), (cx - s, cy + s), (cx + s, cy + s)]
    else:  pts = [(cx, cy + s), (cx - s, cy - s), (cx + s, cy - s)]
    pygame.draw.polygon(surf, color, [(int(a), int(b)) for a, b in pts])


def crown(surf, cx, cy, w=14, color=GOLD):
    h = w * 0.62
    pts = [(cx - w / 2, cy + h / 2), (cx - w / 2, cy - h * 0.15), (cx - w * 0.22, cy + h * 0.15),
           (cx, cy - h / 2), (cx + w * 0.22, cy + h * 0.15), (cx + w / 2, cy - h * 0.15),
           (cx + w / 2, cy + h / 2)]
    pygame.draw.polygon(surf, color, [(int(a), int(b)) for a, b in pts])


def chip(surf, rect, label, color, size=11, bold=True, mono=False):
    pygame.draw.rect(surf, tuple(int(c * 0.25) + 12 for c in color), rect,
                     border_radius=rect.h // 2)
    pygame.draw.rect(surf, color, rect, 1, border_radius=rect.h // 2)
    txt(surf, label, rect.centerx, rect.centery, size, color, bold=bold, mono=mono, align="mc")


def button(surf, rect, label, active=False, clicks=None, action=None, size=12,
           accent=GREEN, mono=False):
    pygame.draw.rect(surf, (40, 52, 70) if active else PANEL, rect, border_radius=7)
    pygame.draw.rect(surf, accent if active else BORDER, rect, 1, border_radius=7)
    txt(surf, label, rect.centerx, rect.centery, size, TEXT if active else DIM,
        bold=True, mono=mono, align="mc")
    if clicks is not None and action is not None:
        clicks.append((rect, action))


def spark(surf, r, data, color):
    if len(data) < 2:
        return
    mn, mx = min(data), max(data)
    if mx - mn < 1e-9:
        mx = mn + 1
    if mn <= START_CASH <= mx:
        yy = r.bottom - (START_CASH - mn) / (mx - mn) * r.h
        pygame.draw.line(surf, (60, 72, 90), (r.x, yy), (r.right, yy), 1)
    n = len(data)
    pts = [(int(r.x + i * r.w / (n - 1)),
            int(r.bottom - (v - mn) / (mx - mn) * r.h)) for i, v in enumerate(data)]
    pygame.draw.lines(surf, color, False, pts)


def wrap(text, font, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if font.size(t)[0] <= maxw:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines


def trunc(s, font, maxw):
    if font.size(s)[0] <= maxw:
        return s
    while s and font.size(s + "...")[0] > maxw:
        s = s[:-1]
    return s + "..."


def money(v):
    return f"${v:,.0f}"


def smoney(v):
    return ("+" if v >= 0 else "-") + f"${abs(v):,.0f}"


def fq(q):
    a = abs(q)
    s = f"{a:,.0f}" if a >= 100 else (f"{a:.1f}" if a >= 10 else f"{a:.2f}")
    return ("-" + s) if q < 0 else s


def fmt_k(v):
    if v >= 1e6: return f"{v/1e6:.1f}M"
    if v >= 1e3: return f"{v/1e3:.0f}k"
    return f"{v:.0f}"


def win_probs(mkt):
    nws = [t.net_worth(mkt) for t in mkt.traders]
    mx = max(nws)
    es = [math.exp((v - mx) / 1500.0) for v in nws]
    s = sum(es)
    return [e / s for e in es]


def arena_vix(mkt):
    vals = []
    for s in mkt.stocks:
        h = s.history[-41:]
        if len(h) > 10:
            rs = [h[i + 1] / h[i] - 1 for i in range(len(h) - 1)]
            m = sum(rs) / len(rs)
            var = sum((x - m) ** 2 for x in rs) / len(rs)
            vals.append(math.sqrt(var))
    if not vals:
        return 12.0
    return max(5.0, min(80.0, sum(vals) / len(vals) * 1600))


def make_icon():
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, (16, 22, 32), s.get_rect())
    for x, h, up in ((4, 9, 1), (10, 14, 1), (16, 8, 0), (22, 17, 1)):
        pygame.draw.rect(s, GREEN if up else RED, (x, 26 - h, 5, h))
    pygame.draw.lines(s, GOLD, False, [(3, 24), (11, 17), (17, 20), (28, 6)], 2)
    return s

# ------------------------------------------------------------------ sound --
class SoundKit:
    """Stdlib-only synth (array module). Desktop: built once at startup.
    Plays silence if no audio device is available."""

    def __init__(self):
        self.on = True
        self.ok = False
        self._built = False
        self.sounds = {}
        self.last = {}

    def ensure(self):
        if self._built:
            return
        self._built = True
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            info = pygame.mixer.get_init()
            if info is None:
                return
            sr = info[0]
            ch = info[2] if len(info) > 2 else 1

            def mk(tones, vol=0.5):
                samples = []
                for f, d, shape in tones:
                    n = max(8, int(sr * d))
                    for i in range(n):
                        t = i / sr
                        ph = 2 * math.pi * f * t
                        if shape == 0:
                            w = math.sin(ph)
                        elif shape == 1:
                            w = 0.7 if math.sin(ph) >= 0 else -0.7
                        else:
                            w = 2 / math.pi * math.asin(math.sin(ph))
                        env = (1.0 - i / n) ** 1.4
                        v = max(-1.0, min(1.0, w * env * vol))
                        samples.append(int(v * 32000))
                    samples.extend([0] * int(sr * 0.012))
                a = array.array("h", samples)
                if ch > 1:
                    a = array.array("h", [s for s in a for _ in range(ch)])
                snd = pygame.mixer.Sound(buffer=a.tobytes())
                snd.set_volume(0.55)
                return snd

            self.sounds = {
                "click":   mk([(1150, .03, 0)]),
                "buy":     mk([(620, .055, 0)]),
                "sell":    mk([(300, .06, 0)]),
                "short":   mk([(210, .07, 1)]),
                "cover":   mk([(520, .05, 0)]),
                "news":    mk([(740, .05, 0), (980, .06, 0)], .45),
                "chime":   mk([(523, .09, 0), (659, .09, 0), (784, .13, 0)], .5),
                "cash":    mk([(660, .06, 0), (880, .07, 0), (1320, .1, 0)], .5),
                "fanfare": mk([(523, .11, 0), (659, .11, 0), (784, .11, 0),
                               (1047, .22, 0)], .55),
            }
            self.ok = True
        except Exception:
            self.ok = False

    def play(self, name, min_gap=0.05):
        if not (self.ok and self.on):
            return
        s = self.sounds.get(name)
        if s is None:
            return
        now = pygame.time.get_ticks()
        if now - self.last.get(name, -10 ** 9) < min_gap * 1000:
            return
        self.last[name] = now
        try:
            s.play()
        except Exception:
            self.ok = False

# ------------------------------------------------------------------ model --
class Stock:
    def __init__(self, symbol, name, sector, price, vol, fvol):
        self.symbol, self.name, self.sector = symbol, name, sector
        self.price = price
        self.fundamental = price
        self.vol, self.fvol = vol, fvol
        self.shock = 0.0
        self.history = [price]
        self.vhist = [300.0]
        self.marks = []
        self.halt_until = -1
        self.cb_arm = -1

    def halted_now(self, mkt):
        return mkt.tick < self.halt_until

    def tick(self, mkt):
        mult = mkt.vmult
        adj = 0.0
        if self.sector == mkt.hot_sector:
            adj = 0.0009
        elif self.sector == mkt.cold_sector:
            adj = -0.0007
        self.fundamental *= 1 + 0.0002 + adj + random.gauss(0, self.fvol * mult)
        self.fundamental = max(0.5, self.fundamental)
        if self.halted_now(mkt):
            self.price = max(0.5, self.price *
                             (1 + random.gauss(0, self.vol * mult * 0.15)))
        else:
            pull = (self.fundamental / self.price - 1.0) * 0.012
            self.shock *= 0.93
            self.price = max(0.5, self.price *
                             (1 + pull + random.gauss(0, self.vol * mult) + self.shock))
        self.history.append(self.price)
        self.vhist.append(200 + abs(random.gauss(0, 600)))

    def ret(self, n):
        h = self.history
        if len(h) < 2:
            return 0.0
        n = min(n, len(h) - 1)
        return h[-1] / h[-1 - n] - 1.0

    def sma(self, n):
        h = self.history
        if len(h) < n:
            return None
        return sum(h[-n:]) / n


class Trader:
    KIND_CD = {"index": (20, 42), "value": (10, 20), "hedge": (8, 18),
               "contra": (8, 16), "default": (5, 13)}

    def __init__(self, name, kind, color, blurb):
        self.name, self.kind, self.color, self.blurb = name, kind, color, blurb
        self.cash = START_CASH
        self.holdings = {}
        self.avg_cost = {}
        self.realized = 0.0
        self.nw_hist = [START_CASH]
        self.cooldown = random.randint(4, 18)
        self.status = "warming up"
        self.mem = {}
        self.orders = 0
        self.closed = []
        self.peak = START_CASH
        self.max_dd = 0.0
        self.blowups = 0
        self.flag2x = False
        self.flaghalf = False
        self.last_action = None

    def pos_value(self, mkt):
        return sum(q * mkt.by_sym[s].price for s, q in self.holdings.items())

    def net_worth(self, mkt):
        return self.cash + self.pos_value(mkt)

    def short_value(self, mkt):
        return sum(-q * mkt.by_sym[s].price
                   for s, q in self.holdings.items() if q < 0)

    def unrealized(self, mkt):
        u = 0.0
        for sym, q in self.holdings.items():
            p = mkt.by_sym[sym].price
            if q > 0:
                u += (p - self.avg_cost[sym]) * q
            else:
                u += (self.avg_cost[sym] - p) * (-q)
        return u

    def ret_recent(self):
        h = self.nw_hist
        return h[-1] / h[-60] - 1.0 if len(h) >= 60 else 0.0

    def tradables(self, mkt):
        return [s for s in mkt.stocks if not s.halted_now(mkt)]

    def order(self, mkt, stock, dollars, note=None, force=False):
        """dollars > 0: buy/cover.  dollars < 0: sell/short."""
        sym = stock.symbol
        halted = stock.halted_now(mkt)
        if halted and not force:
            self.status = f"{sym} is halted"
            return False
        px = stock.price
        traded = 0.0
        side = None
        if dollars >= 0:
            spend = min(dollars, self.cash, 9000.0)
            if spend < 20:
                return False
            qty = spend / px
            pos = self.holdings.get(sym, 0.0)
            if pos < 0:
                side = "COVER"
                cover = min(qty, -pos)
                pnl = (self.avg_cost[sym] - px) * cover
                self.realized += pnl
                self.closed.append(pnl)
                pos += cover
                if pos <= 1e-9:
                    self.holdings.pop(sym, None)
                    self.avg_cost.pop(sym, None)
                    rest = qty - cover
                    if rest > 1e-9:
                        self.holdings[sym] = rest
                        self.avg_cost[sym] = px
                else:
                    self.holdings[sym] = pos
            else:
                side = "BUY"
                self.holdings[sym] = pos + qty
                self.avg_cost[sym] = ((self.avg_cost.get(sym, px) * pos + px * qty)
                                      / (pos + qty))
            self.cash -= spend
            traded = spend
        else:
            val = -dollars
            pos = self.holdings.get(sym, 0.0)
            if pos > 0:
                qc = min(val / px, pos)
                pnl = (px - self.avg_cost[sym]) * qc
                self.realized += pnl
                self.closed.append(pnl)
                self.cash += qc * px
                traded += qc * px
                pos -= qc
                if pos <= 1e-9:
                    self.holdings.pop(sym, None)
                    self.avg_cost.pop(sym, None)
                else:
                    self.holdings[sym] = pos
                val -= qc * px
                side = "SELL"
            cur = self.holdings.get(sym, 0.0)
            if val > 1e-6 and cur <= 1e-9:
                allowed = SHORT_CAP * self.net_worth(mkt) - self.short_value(mkt)
                spend = min(val, allowed, 9000.0)
                if spend >= 300:
                    qty = spend / px
                    old = -cur
                    if old > 1e-9:
                        self.avg_cost[sym] = ((self.avg_cost[sym] * old + px * qty)
                                              / (old + qty))
                    else:
                        self.avg_cost[sym] = px
                    self.holdings[sym] = -(old + qty)
                    self.cash += spend
                    traded += spend
                    side = "SHORT"
                elif side is None:
                    self.status = "margin limit reached"
                    return False
        if side is None or traded <= 0:
            return False
        if not halted:
            mkt.impact(stock, traded if dollars >= 0 else -traded)
        mkt.log_trade(self, stock, side, traded / px, px)
        self.last_action = {"sym": sym, "side": side}
        self.status = note or {"BUY": f"bought {sym}", "SELL": f"sold {sym}",
                               "SHORT": f"shorted {sym}", "COVER": f"covered {sym}"}[side]
        return True

    def act(self, mkt):
        lo, hi = Trader.KIND_CD.get(self.kind, Trader.KIND_CD["default"])
        self.cooldown = random.randint(lo, hi)
        getattr(self, "st_" + self.kind)(mkt)

    def st_momentum(self, mkt):
        for sym, qty in list(self.holdings.items()):
            s = mkt.by_sym[sym]
            if qty <= 0 or s.halted_now(mkt):
                continue
            ac = self.avg_cost.get(sym, s.price)
            if s.price < ac * 0.95:
                self.order(mkt, s, -qty * s.price, f"stop-loss on {sym}")
                return
            if s.price > ac * 1.20:
                self.order(mkt, s, -qty * 0.6 * s.price, f"taking profit on {sym}")
                return
        pool = self.tradables(mkt)
        if pool:
            best = max(pool, key=lambda s: s.ret(20))
            if best.ret(20) > 0.035:
                held = self.holdings.get(best.symbol, 0.0) * best.price
                if held < self.net_worth(mkt) * 0.5 and self.cash > 300:
                    if self.order(mkt, best, self.cash * 0.45,
                                  f"riding {best.symbol} momentum"):
                        return
        self.status = random.choice(IDLE)

    def st_quant(self, mkt):
        for s in mkt.stocks:
            a, b = s.sma(10), s.sma(40)
            if a is None or b is None:
                continue
            sign = 1 if a > b else -1
            prev = self.mem.get(s.symbol)
            self.mem[s.symbol] = sign
            if prev is not None and prev != sign and not s.halted_now(mkt):
                if sign > 0:
                    if self.order(mkt, s, self.cash * 0.4,
                                  f"golden cross: buying {s.symbol}"):
                        return
                elif self.holdings.get(s.symbol, 0.0) > 0:
                    if self.order(mkt, s, -self.holdings[s.symbol] * s.price,
                                  f"death cross: exiting {s.symbol}"):
                        return
        self.status = "waiting for a crossover"

    def st_value(self, mkt):
        pool = self.tradables(mkt)
        best, bd = None, 0.0
        for s in pool:
            est = s.fundamental * random.gauss(1.0, 0.05)
            dev = s.price / est - 1.0
            if dev < bd:
                best, bd = s, dev
        if best is not None and bd < -0.12:
            held = self.holdings.get(best.symbol, 0.0) * best.price
            if held < self.net_worth(mkt) * 0.4 and self.cash > 200:
                if self.order(mkt, best, self.cash * 0.35,
                              f"value entry {best.symbol} ({bd*100:.0f}% under)"):
                    return
        for sym, qty in list(self.holdings.items()):
            s = mkt.by_sym[sym]
            if qty <= 0 or s.halted_now(mkt):
                continue
            est = s.fundamental * random.gauss(1.0, 0.05)
            if s.price > est * 1.25:
                self.order(mkt, s, -qty * s.price, f"harvesting overpriced {sym}")
                return
        self.status = random.choice(IDLE)

    def st_meanrev(self, mkt):
        for sym, qty in list(self.holdings.items()):
            s = mkt.by_sym[sym]
            if qty <= 0 or s.halted_now(mkt):
                continue
            sm = s.sma(30)
            if sm and s.price > sm * 1.06:
                self.order(mkt, s, -qty * s.price, f"fading {sym} strength")
                return
        cands = []
        for s in self.tradables(mkt):
            sm = s.sma(30)
            if sm:
                dev = s.price / sm - 1.0
                if dev < -0.025:
                    cands.append((dev, s))
        if cands:
            dev, s = min(cands, key=lambda p: p[0])
            held = self.holdings.get(s.symbol, 0.0) * s.price
            if held < self.net_worth(mkt) * 0.35 and self.cash > 200:
                if self.order(mkt, s, self.cash * 0.3, f"buying the {s.symbol} dip"):
                    return
        self.status = random.choice(IDLE)

    def st_hedge(self, mkt):
        nw = self.net_worth(mkt)
        pool = self.tradables(mkt)
        if not pool:
            self.status = "waiting for open markets"
            return
        ranked = sorted(pool, key=lambda s: s.ret(30), reverse=True)[:3]
        targets = {s.symbol: nw * 0.26 for s in ranked}
        for sym in list(self.holdings.keys()):
            s = mkt.by_sym[sym]
            if sym not in targets and not s.halted_now(mkt):
                self.order(mkt, s, -self.holdings[sym] * s.price,
                           f"rotating out of {sym}")
                return
        for sym, tv in targets.items():
            s = mkt.by_sym[sym]
            if s.halted_now(mkt):
                continue
            cv = self.holdings.get(sym, 0.0) * s.price
            if cv < tv * 0.8 and self.cash > 250:
                if self.order(mkt, s, min(tv - cv, self.cash * 0.8),
                              f"balancing into {sym}"):
                    return
            if cv > tv * 1.25:
                if self.order(mkt, s, -(cv - tv), f"trimming {sym}"):
                    return
        self.status = "rebalancing the book"

    def st_panic(self, mkt):
        for sym, qty in list(self.holdings.items()):
            s = mkt.by_sym[sym]
            if qty <= 0 or s.halted_now(mkt):
                continue
            hi = max(s.history[-50:])
            if s.price < hi * 0.94:
                self.order(mkt, s, -qty * s.price, f"AAAAH dumping {sym}!!")
                return
        pool = self.tradables(mkt)
        if pool:
            hot = max(pool, key=lambda s: s.ret(5))
            if hot.ret(5) > 0.04 and self.cash > 200:
                self.order(mkt, hot, self.cash * 0.6, f"FOMO buying {hot.symbol}!!")
                return
        self.status = "nervously watching the screen"

    def st_contra(self, mkt):
        for sym, q in list(self.holdings.items()):
            s = mkt.by_sym[sym]
            if s.halted_now(mkt):
                continue
            if q < 0:
                ac = self.avg_cost.get(sym, s.price)
                ch = s.price / ac - 1.0
                sm = s.sma(30)
                if ch <= -0.025 or (sm and s.price < sm):
                    pnl = (ac - s.price) * (-q)
                    self.order(mkt, s, (-q) * s.price,
                               f"covered {sym} short ({smoney(pnl)})")
                    return
                if ch >= 0.05:
                    self.order(mkt, s, (-q) * s.price, f"stopped out of {sym} short")
                    return
            else:
                sm = s.sma(30)
                if sm and s.price > sm * 1.05:
                    self.order(mkt, s, -q * s.price, f"flipping out of {sym}")
                    return
        pool = self.tradables(mkt)
        cands = [s for s in pool
                 if s.ret(15) > 0.045 and s.sma(30) and s.price > s.sma(30) * 1.03
                 and self.holdings.get(s.symbol, 0.0) <= 0]
        if cands:
            s = max(cands, key=lambda x: x.ret(15))
            if self.order(mkt, s, -self.net_worth(mkt) * 0.25,
                          f"shorting euphoric {s.symbol}"):
                return
        dips = [s for s in pool if s.ret(15) < -0.05 and s.sma(30)
                and s.price < s.sma(30) * 0.97]
        if dips and random.random() < 0.5 and self.cash > 300:
            s = random.choice(dips)
            self.order(mkt, s, self.cash * 0.15, f"bargain hunting {s.symbol}")
            return
        self.status = "hunting euphoria to short"

    def st_chaos(self, mkt):
        r = random.random()
        if r < 0.30 and self.holdings:
            sym = random.choice(list(self.holdings.keys()))
            s = mkt.by_sym[sym]
            q = self.holdings[sym]
            if q > 0 and not s.halted_now(mkt):
                self.order(mkt, s, -q * random.uniform(0.4, 1.0) * s.price,
                           f"dumped {sym} on a vibe")
                return
        if r < 0.72:
            pool = self.tradables(mkt)
            if pool and self.cash > 150:
                s = random.choice(pool)
                self.order(mkt, s, self.cash * random.uniform(0.2, 0.7),
                           f"aping into {s.symbol}")
                return
        self.status = random.choice(["vibing", "trusting the gut",
                                     "eating snacks", "doing nothing, brilliantly"])

    def st_yolo(self, mkt):
        fav = self.mem.get("fav")
        if fav is None or random.random() < 0.05:
            pool = self.tradables(mkt)
            if pool:
                fav = random.choice(pool)
            self.mem["fav"] = fav
        if fav is None:
            self.status = "picking a horse"
            return
        if fav.halted_now(mkt):
            self.status = f"locked out of {fav.symbol}"
            return
        qty = self.holdings.get(fav.symbol, 0.0)
        if qty > 0:
            ac = self.avg_cost.get(fav.symbol, fav.price)
            ch = fav.price / ac - 1.0
            if ch > 0.15:
                self.order(mkt, fav, -qty * fav.price, f"{fav.symbol} mooned: paper hands")
                return
            if ch < -0.10:
                self.order(mkt, fav, -qty * fav.price, f"{fav.symbol} rekt: rage quit")
                return
            if self.cash > 200:
                self.order(mkt, fav, self.cash * 0.5, f"doubling down on {fav.symbol}")
                return
            self.status = f"married to {fav.symbol}"
        else:
            if self.cash > 200:
                self.order(mkt, fav, self.cash * 0.85, f"ALL-IN on {fav.symbol}")
                return
            self.status = f"waiting to reload {fav.symbol}"

    def st_index(self, mkt):
        nw = self.net_worth(mkt)
        caps = {s.symbol: s.fundamental for s in mkt.stocks}
        tot = sum(caps.values()) or 1.0
        worst = None
        for sym, cap in caps.items():
            s = mkt.by_sym[sym]
            tv = nw * 0.94 * cap / tot
            cv = self.holdings.get(sym, 0.0) * s.price
            dev = cv - tv
            if worst is None or abs(dev) > abs(worst[0]):
                worst = (dev, sym, s)
        if worst and abs(worst[0]) > max(400.0, nw * 0.025):
            dev, sym, s = worst
            if not s.halted_now(mkt):
                note = f"index {'trim' if dev > 0 else 'add'} {sym}"
                if self.order(mkt, s, -dev, note):
                    return
        self.status = "indexing the whole market"


class Market:
    def __init__(self, season=1):
        self.season = season
        self.stocks = [Stock(*d) for d in STOCK_DEFS]
        self.by_sym = {s.symbol: s for s in self.stocks}
        self.traders = [Trader(n, k, c, b) for (n, k, c, b) in ROSTER]
        self.tick = 0
        self.trade_log = []
        self.news = []
        self.toasts = []
        self.pending = []
        self.banner = None
        self.banner_frames = 0
        self.over = False
        self.resolved = False
        self.snd = None
        self.bet = None
        self.bet_result = None
        self._flashcd = {}
        self.regime = "NORMAL"
        self.vmult = 1.0
        secs = sorted({s.sector for s in self.stocks})
        self.hot_sector = random.choice(secs)
        self.cold_sector = random.choice([x for x in secs if x != self.hot_sector])
        self.q_nw0 = {t.name: t.net_worth(self) for t in self.traders}
        self.next_news = random.randint(70, 150)

    def impact(self, stock, value):
        stock.price = max(0.5, stock.price * (1 + value / IMPACT))

    def log_trade(self, ai, stock, side, qty, px):
        self.trade_log.append({"t": self.tick, "ai": ai, "side": side,
                               "sym": stock.symbol, "qty": qty, "px": px})
        if len(self.trade_log) > 90:
            del self.trade_log[:45]
        ai.orders += 1
        stock.vhist[-1] += abs(qty * px) * 0.9
        stock.marks.append((len(stock.history) - 1, px, side, ai.color))
        if len(stock.marks) > 120:
            del stock.marks[:60]
        if self.snd:
            self.snd.play({"BUY": "buy", "SELL": "sell", "SHORT": "short",
                           "COVER": "cover"}.get(side, "click"), 0.05)

    def toast(self, text, color):
        self.toasts.append({"text": text[:70], "color": color, "ttl": 220})
        if len(self.toasts) > 6:
            del self.toasts[:2]

    def add_news(self, text, color):
        self.news.append((self.tick, text, color))
        if len(self.news) > 50:
            del self.news[:25]
        if self.snd:
            self.snd.play("news", 0.2)

    def fire_news(self):
        if random.random() < 0.20:
            tpl, lo, hi = random.choice(GLOBAL_NEWS)
            imp = random.uniform(lo, hi)
            for s in self.stocks:
                s.fundamental *= (1 + imp)
                if not s.halted_now(self):
                    s.shock += imp * 0.02
            self.add_news(tpl, GREEN if imp > 0 else RED)
        elif random.random() < 0.30 and not self.pending:
            s = random.choice(self.stocks)
            tpl, lo, hi = random.choice(NEWS_TEMPLATES)
            drift = 0.006 if (lo + hi) > 0 else -0.006
            if not s.halted_now(self):
                s.shock += drift
            self.add_news(f"RUMOR MILL: whispers circling {s.name}...", (176, 150, 255))
            self.pending.append([self.tick + random.randint(30, 60), s.symbol, tpl, lo, hi])
        else:
            s = random.choice(self.stocks)
            tpl, lo, hi = random.choice(NEWS_TEMPLATES)
            imp = random.uniform(lo, hi)
            s.fundamental *= (1 + imp)
            if not s.halted_now(self):
                s.price *= (1 + imp * 0.35)
                s.shock += imp * 0.02
            self.add_news(tpl.format(name=s.name, sym=s.symbol),
                          GREEN if imp > 0 else RED)

    def mirror(self, t, star, act):
        s = self.by_sym.get(act["sym"])
        if s is None or s.halted_now(self):
            return
        if act["side"] in ("BUY", "COVER") and t.cash > 400:
            if t.order(self, s, t.cash * 0.25, f"copying {star.name} -> {s.symbol}"):
                self._copytoast(t, star)
        elif act["side"] in ("SELL", "SHORT"):
            q = t.holdings.get(s.symbol, 0.0)
            if q > 0 and t.order(self, s, -q * s.price,
                                 f"copying {star.name} -> out of {s.symbol}"):
                self._copytoast(t, star)

    def _copytoast(self, t, star):
        if self.tick - self._flashcd.get("copy" + t.name, -999) > 300:
            self._flashcd["copy" + t.name] = self.tick
            self.toast(f"{t.name} is copying {star.name}!", t.color)

    def pay_dividends(self):
        top, topy = None, 0.0
        for s in self.stocks:
            dy = random.uniform(0.004, 0.011)
            if dy > topy:
                top, topy = s, dy
            dps = s.fundamental * dy
            for t in self.traders:
                q = t.holdings.get(s.symbol, 0.0)
                if q > 0:
                    t.cash += dps * q
                elif q < 0:
                    t.cash -= dps * (-q)
        self.add_news(f"Dividend day -- top yield {top.symbol} {topy*100:.1f}%",
                      (120, 235, 160))
        self.toast("Dividend day -- holders collect", (120, 235, 160))
        if self.snd:
            self.snd.play("cash", 0.3)

    def _core(self):
        for item in self.pending[:]:
            if self.tick >= item[0]:
                self.pending.remove(item)
                s = self.by_sym[item[1]]
                imp = random.uniform(item[3], item[4])
                s.fundamental *= (1 + imp)
                if not s.halted_now(self):
                    s.price *= (1 + imp * 0.5)
                    s.shock += imp * 0.025
                self.add_news(item[2].format(name=s.name, sym=s.symbol),
                              GREEN if imp > 0 else RED)
        for s in self.stocks:
            s.tick(self)
        for t in self.traders:
            nw = t.net_worth(self)
            t.nw_hist.append(nw)
            if len(t.nw_hist) > 2600:
                del t.nw_hist[:-2400]
            t.peak = max(t.peak, nw)
            if t.peak > 0:
                t.max_dd = max(t.max_dd, (t.peak - nw) / t.peak)
            t.cooldown -= 1
            if t.cooldown <= 0:
                t.act(self)
            sv = t.short_value(self)
            if sv > 0:
                t.cash -= sv * 0.00004
        if self.tick > 120 and self.tick % 5 == 0:
            star = max(self.traders, key=lambda t: t.ret_recent())
            if star.ret_recent() > 0.022 and star.last_action:
                s2 = self.by_sym.get(star.last_action["sym"])
                if s2 is not None and not s2.halted_now(self):
                    for t in self.traders:
                        if t is star or t.cooldown < 3:
                            continue
                        if random.random() < 0.05:
                            self.mirror(t, star, star.last_action)
                            break
        for t in self.traders:
            nw = t.net_worth(self)
            for sym, q in list(t.holdings.items()):
                if q < 0:
                    s = self.by_sym[sym]
                    v = -q * s.price
                    if v > 0.60 * max(nw, 1.0):
                        t.order(self, s, v - 0.45 * max(nw, 1.0),
                                f"MARGIN CALL: covering {sym}", force=True)
            if nw < 600 and t.cash < 600:
                t.cash += 5000.0
                t.blowups += 1
                t.status = "blew up -- recapitalized"
                self.toast(f"{t.name} blew up!  emergency +$5,000", RED)
        for s in self.stocks:
            if not s.halted_now(self) and self.tick >= s.cb_arm \
                    and len(s.history) > 31 and abs(s.ret(30)) > 0.11:
                s.halt_until = self.tick + 90
                s.cb_arm = self.tick + 90 + 35
                self.toast(f"CIRCUIT BREAKER · {s.symbol} halted", RED)
                self.add_news(f"Exchange halts {s.name} after violent swings", RED)
        if self.tick % 4 == 0:
            for t in self.traders:
                nw = t.net_worth(self)
                if nw >= 2 * START_CASH and not t.flag2x:
                    t.flag2x = True
                    self.toast(f"{t.name} has DOUBLED their money!", t.color)
                if nw <= 0.5 * START_CASH and not t.flaghalf:
                    t.flaghalf = True
                    self.toast(f"{t.name} is down 50%...  ouch", RED)
            for s in self.stocks:
                if s.halted_now(self):
                    continue
                r = s.ret(12)
                if abs(r) > 0.05 and self.tick - self._flashcd.get(s.symbol, -999) > 150:
                    self._flashcd[s.symbol] = self.tick
                    self.toast(f"{s.symbol} {'surging' if r > 0 else 'tumbling'} "
                               f"{r*100:+.1f}%!", GREEN if r > 0 else RED)
        p = random.random()
        new = self.regime
        if self.regime == "NORMAL":
            if p < 0.0012:   new = "TURBULENT"
            elif p < 0.0024: new = "CALM"
        elif p < 0.008:
            new = "NORMAL"
        if new != self.regime:
            self.regime = new
            self.vmult = {"CALM": 0.55, "NORMAL": 1.0, "TURBULENT": 1.9}[new]
            self.toast(f"market regime -> {new}", (120, 170, 255))
            self.add_news(f"Volatility regime shifts to {new}", (120, 170, 255))
        self.next_news -= 1
        if self.next_news <= 0:
            self.fire_news()
            rng = {"TURBULENT": (60, 150), "NORMAL": (110, 260), "CALM": (200, 380)}
            self.next_news = random.randint(*rng[self.regime])

    def warmup(self, n=320):
        for _ in range(n):
            self._core()
        self.tick = 0
        for s in self.stocks:
            s.halt_until = -1
            s.cb_arm = -1
            s.marks = []
        self.trade_log = []
        self.news = []
        self.toasts = []
        self.pending = []
        self.banner = None
        self.banner_frames = 0
        for t in self.traders:
            t.nw_hist = [START_CASH]
            t.peak = START_CASH
            t.max_dd = 0.0
            t.closed = []
            t.realized = 0.0
            t.orders = 0
            t.blowups = 0
            t.flag2x = False
            t.flaghalf = False
            t.last_action = None
            t.status = "ready"
            t.cooldown = random.randint(4, 16)
        self.q_nw0 = {t.name: t.net_worth(self) for t in self.traders}
        self.add_news(f"Season {self.season} begins -- good luck, bots", (120, 170, 255))

    def step(self):
        if self.over:
            return
        self._core()
        self.tick += 1
        if self.tick % QUARTER == 0:
            q = self.tick // QUARTER
            self.pay_dividends()
            best = max(self.stocks, key=lambda s: s.ret(QUARTER))
            deltas = {t.name: t.net_worth(self) - self.q_nw0.get(t.name, START_CASH)
                      for t in self.traders}
            mvp = max(self.traders, key=lambda t: deltas[t.name])
            lead = max(self.traders, key=lambda t: t.net_worth(self))
            self.banner = (f"Q{q} REPORT ·  leader {lead.name} {money(lead.net_worth(self))}"
                           f"  ·  MVP {mvp.name} {smoney(deltas[mvp.name])}"
                           f"  ·  top stock {best.symbol} {best.ret(QUARTER)*100:+.0f}%")
            self.banner_frames = 220
            self.add_news(f"Quarter {q} closes -- MVP {mvp.name} "
                          f"({smoney(deltas[mvp.name])})", GOLD)
            self.toast(f"Q{q} MVP: {mvp.name} {smoney(deltas[mvp.name])}", mvp.color)
            secs = sorted({s.sector for s in self.stocks})
            hot = random.choice(secs)
            cold = random.choice([x for x in secs if x != hot])
            self.hot_sector, self.cold_sector = hot, cold
            self.add_news(f"SECTOR WATCH -- {hot} heating up, {cold} cooling off",
                          (120, 170, 255))
            self.q_nw0 = {t.name: t.net_worth(self) for t in self.traders}
            if q >= QUARTERS:
                self.over = True
                if self.bet:
                    ranked = sorted(self.traders, key=lambda t: t.net_worth(self),
                                    reverse=True)
                    t = self.traders[self.bet["idx"]]
                    rank = ranked.index(t) + 1
                    mult = {1: 3.0, 2: 1.8, 3: 1.3}.get(rank, 0.0)
                    self.bet_result = {"stake": self.bet["stake"], "name": t.name,
                                       "rank": rank,
                                       "payout": round(self.bet["stake"] * mult)}
            elif self.snd:
                self.snd.play("chime", 0.1)

# --------------------------------------------------------------- drawing --
def draw_title(screen, frame):
    screen.fill(BG)
    for x in range(0, WIDTH + 1, 64):
        pygame.draw.line(screen, (15, 20, 29), (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT + 1, 64):
        pygame.draw.line(screen, (15, 20, 29), (0, y), (WIDTH, y))

    def wave(y0, amp, freq, spd, col, w):
        pts = []
        for x in range(0, WIDTH + 16, 16):
            t = (x + frame * spd) * freq
            pts.append((x, y0 + math.sin(t) * amp
                        + math.sin(t * 0.37 + 1.7) * amp * 0.5))
        pygame.draw.lines(screen, col, False, pts, w)

    wave(196, 30, 0.010, 0.9, (30, 92, 72), 3)
    wave(228, 24, 0.013, -1.3, (96, 58, 64), 3)
    wave(212, 18, 0.017, 1.7, (52, 82, 116), 2)
    crown(screen, WIDTH // 2, 262, 44)
    txt(screen, "AI  TRADING  ARENA", WIDTH // 2, 288, 54, TEXT, bold=True, align="tc")
    txt(screen, "ten bots · one market · zero mercy", WIDTH // 2, 360, 17, DIM, align="tc")
    p = pygame.Rect(WIDTH // 2 - 370, 408, 740, 176)
    panel(screen, p)
    rows = [
        "8 tickers traded live by 10 AI personalities with real strategies",
        "news shocks · dividends · short selling · circuit breakers · hype",
        "watch charts, execution feed & leaderboard -- or bet on the winner",
        "your bankroll & the champion hall-of-fame persist between seasons",
    ]
    y = p.y + 22
    for r in rows:
        pygame.draw.circle(screen, GOLD, (p.x + 28, y + 8), 3)
        txt(screen, r, p.x + 42, y, 14, TEXT)
        y += 34
    if frame % 80 < 55:
        txt(screen, "CLICK   OR   PRESS   ANY   KEY", WIDTH // 2, 634, 20, GOLD,
            bold=True, align="tc")
    txt(screen, "SPACE pause · 1-4 speed · C candles · B bet · M sound · "
        "F fullscreen · R new season", WIDTH // 2, 700, 13, DIM, mono=True, align="tc")
    txt(screen, f"v{__version__} · python + pygame", WIDTH // 2, HEIGHT - 26, 11,
        (100, 112, 130), align="tc")


def draw_topbar(screen, mkt, paused, speed_i, bankroll, clicks):
    pygame.draw.rect(screen, PANEL2, (0, 0, WIDTH, 52))
    pygame.draw.line(screen, BORDER, (0, 52), (WIDTH, 52))
    pygame.draw.line(screen, GREEN, (26, 10), (26, 34), 2)
    pygame.draw.rect(screen, GREEN, (21, 16, 10, 12), border_radius=2)
    pygame.draw.line(screen, RED, (44, 14), (44, 34), 2)
    pygame.draw.rect(screen, RED, (39, 19, 10, 10), border_radius=2)
    txt(screen, "AI TRADING ARENA", 58, 12, 20, TEXT, bold=True)
    w0 = F(20, True).size("AI TRADING ARENA")[0]
    sn = f"SEASON {mkt.season}"
    txt(screen, sn, 66 + w0, 17, 12, GOLD, bold=True, mono=True)
    w1 = F(12, True, True).size(sn)[0]
    txt(screen, "· bots battling for alpha", 76 + w0 + w1, 20, 11, DIM)
    q = min(mkt.tick // QUARTER + 1, QUARTERS)
    d = mkt.tick % QUARTER // 25 + 1
    txt(screen, f"Q{q} · DAY {d} · TICK {mkt.tick}/{TOTAL}", 560, 18, 13,
        DIM, mono=True, align="tc")
    x = WIDTH - 16
    r = pygame.Rect(x - 78, 13, 78, 26)
    button(screen, r, "RESUME" if paused else "PAUSE", paused, clicks,
           ("pause",), size=12, accent=GOLD)
    x -= 88
    for i in range(len(SPEEDS) - 1, -1, -1):
        r = pygame.Rect(x - 46, 13, 46, 26)
        button(screen, r, SPEEDS[i][1], i == speed_i, clicks,
               ("speed", i), size=12, mono=True)
        x -= 52
    if mkt.bet:
        t = mkt.traders[mkt.bet["idx"]]
        r = pygame.Rect(x - 150, 13, 150, 26)
        pygame.draw.rect(screen, (44, 38, 16), r, border_radius=7)
        pygame.draw.rect(screen, GOLD, r, 1, border_radius=7)
        txt(screen, f"BET ${mkt.bet['stake']:,.0f}", r.x + 10, r.centery, 11,
            GOLD, bold=True, mono=True, align="ml")
        txt(screen, trunc(t.name, F(10), 62), r.right - 8, r.centery, 10,
            GOLD, align="mr")
        clicks.append((r, ("bet_open",)))
        x -= 160
    else:
        r = pygame.Rect(x - 108, 13, 108, 26)
        button(screen, r, "PLACE BET (B)", False, clicks, ("bet_open",),
               size=11, accent=GOLD)
        x -= 118
    r = pygame.Rect(x - 140, 13, 140, 26)
    pygame.draw.rect(screen, (16, 34, 26), r, border_radius=7)
    pygame.draw.rect(screen, GREEN, r, 1, border_radius=7)
    txt(screen, f"BANK ${bankroll:,.0f}", r.centerx, r.centery, 12,
        (150, 235, 180), bold=True, mono=True, align="mc")
    clicks.append((r, ("bet_open",)))


def draw_tape(screen, mkt, frame, speed_i):
    r = pygame.Rect(0, 52, WIDTH, 28)
    pygame.draw.rect(screen, PANEL2, r)
    pygame.draw.line(screen, BORDER, (0, 52), (WIDTH, 52))
    pygame.draw.line(screen, BORDER, (0, 79), (WIDTH, 79))
    fnt = F(13, True, True)
    segs, total, GAP = [], 0, 40
    for s in mkt.stocks:
        pct = s.ret(25) * 100
        col = GREEN if pct >= 0 else RED
        w1 = fnt.size(f"{s.symbol} ")[0]
        w2 = fnt.size(f"{s.price:,.2f}  ")[0]
        w3 = fnt.size(f"{pct:+.2f}%")[0]
        segs.append((s.symbol, f"{s.price:,.2f}", f"{pct:+.2f}%", col, w1, w2, w3))
        total += w1 + w2 + w3 + GAP
    off = int(frame * (0.5 + 0.35 * speed_i)) % max(total, 1)
    x = -off
    screen.set_clip(r)
    while x < WIDTH:
        for sym, pxs, pcs, col, w1, w2, w3 in segs:
            if x + w1 + w2 + w3 > 0 and x < WIDTH:
                screen.blit(fnt.render(sym, True, TEXT), (x, 58))
                screen.blit(fnt.render(pxs, True, (150, 162, 180)), (x + w1, 58))
                screen.blit(fnt.render(pcs, True, col), (x + w1 + w2, 58))
            x += w1 + w2 + w3 + GAP
    screen.set_clip(None)


def draw_tabs(screen, mkt, sel, frame, clicks):
    x0, y0, gap = 16, 88, 6
    w = (904 - gap * (len(mkt.stocks) - 1)) // len(mkt.stocks)
    for i, s in enumerate(mkt.stocks):
        r = pygame.Rect(x0 + i * (w + gap), y0, w, 30)
        active = (i == sel)
        pygame.draw.rect(screen, (34, 44, 60) if active else PANEL, r, border_radius=8)
        bc = (90, 110, 140) if active else BORDER
        mv = s.ret(12)
        if abs(mv) > 0.05 and frame % 30 < 15:
            bc = GREEN if mv > 0 else RED
        pygame.draw.rect(screen, bc, r, 1, border_radius=8)
        chg = s.ret(25) * 100
        txt(screen, s.symbol, r.x + 12, r.centery, 13, TEXT if active else DIM,
            bold=True, align="ml")
        txt(screen, f"{chg:+.1f}%", r.right - 10, r.centery, 11,
            GREEN if chg >= 0 else RED, mono=True, align="mr")
        if s.halted_now(mkt):
            txt(screen, "H", r.x + 12 + F(13, True).size(s.symbol)[0] + 6,
                r.centery, 10, RED, bold=True, align="ml")
        if active:
            pygame.draw.rect(screen, GREEN, (r.x + 8, r.bottom - 3, r.w - 16, 2))
        clicks.append((r, ("tab", i)))


def draw_chart(screen, mkt, sel, candle_mode, clicks):
    s = mkt.stocks[sel]
    rect = pygame.Rect(16, 126, 904, 368)
    panel(screen, rect)
    txt(screen, s.symbol, 32, 131, 22, TEXT, bold=True)
    w0 = F(22, True).size(s.symbol)[0]
    txt(screen, f"{s.name}  ·  {s.sector}", 42 + w0, 140, 12, DIM)
    col = GREEN if s.ret(25) >= 0 else RED
    pxs = f"${s.price:,.2f}"
    txt(screen, pxs, 470, 129, 22, col, bold=True, mono=True)
    pw = F(22, True, True).size(pxs)[0]
    cs = f"{s.ret(25)*100:+.2f}%"
    cw = F(12, True).size(cs)[0] + 16
    chip(screen, pygame.Rect(470 + pw + 12, 132, cw, 20), cs, col, size=12)
    nxt = 470 + pw + 12 + cw + 8
    if s.halted_now(mkt):
        chip(screen, pygame.Rect(nxt, 132, 74, 20), "HALTED", RED, size=11)
    txt(screen, f"fair value ${s.fundamental:,.2f}", rect.right - 104, 138, 11,
        FVGOLD, mono=True, align="tr")
    button(screen, pygame.Rect(rect.right - 92, 129, 80, 24),
           "CANDLES" if candle_mode else "LINES", candle_mode, clicks,
           ("candle",), size=10, mono=True)
    P = pygame.Rect(34, 170, 838, 246)
    V = pygame.Rect(34, 424, 838, 44)
    hist, vh = s.history, s.vhist
    if candle_mode:
        n = min(CANDLE_N, (len(hist) - 1) // CANDLE_PER)
        off = len(hist) - n * CANDLE_PER
        opens  = [hist[off + i * CANDLE_PER] for i in range(n)]
        closes = [hist[off + i * CANDLE_PER + CANDLE_PER - 1] for i in range(n)]
        highs  = [max(hist[off + i * CANDLE_PER:off + (i + 1) * CANDLE_PER]) for i in range(n)]
        lows   = [min(hist[off + i * CANDLE_PER:off + (i + 1) * CANDLE_PER]) for i in range(n)]
        vols   = [sum(vh[off + i * CANDLE_PER:off + (i + 1) * CANDLE_PER]) for i in range(n)]
        step = P.w / max(n, 1)
        xs = lambda i: P.x + (i + 0.5) * step
    else:
        n = min(VIS, len(hist))
        off = len(hist) - n
        closes = hist[-n:]
        opens, highs, lows = closes, closes, closes
        vols = vh[-n:]
        step = P.w / max(n - 1, 1)
        xs = lambda i: P.x + i * step
    if n < 2:
        return
    lo = min(min(lows), s.fundamental)
    hi = max(max(highs), s.fundamental)
    pad = (hi - lo) * 0.08 + 1e-9
    lo -= pad
    hi += pad
    Y = lambda p: P.bottom - (p - lo) / (hi - lo) * P.h
    for k in range(5):
        yy = P.y + P.h * k / 4
        pygame.draw.line(screen, (28, 35, 46), (P.x, yy), (P.right, yy))
        val = hi - (hi - lo) * k / 4
        lab = f"{val:,.2f}" if val < 10 else f"{val:,.0f}"
        txt(screen, lab, P.right + 8, yy - 6, 10, DIM, mono=True)
    for i in (range(0, n, 20) if candle_mode else range(0, n, 52)):
        xx = xs(i)
        pygame.draw.line(screen, (24, 30, 40), (xx, P.y), (xx, P.bottom))
        t_abs = off + (i * CANDLE_PER + CANDLE_PER - 1 if candle_mode else i)
        if xx < P.right - 22:
            txt(screen, f"D{t_abs//25+1}", xx, P.bottom - 13, 9, (90, 100, 116),
                mono=True, align="mc")
    screen.set_clip(P)
    dline(screen, (P.x, Y(s.fundamental)), (P.right, Y(s.fundamental)), FVGOLD)
    spts = []
    for i in range(n):
        g = off + ((i + 1) * CANDLE_PER - 1 if candle_mode else i)
        if g >= 19:
            spts.append((xs(i), Y(sum(hist[g - 19:g + 1]) / 20)))
    if len(spts) > 1:
        pygame.draw.lines(screen, BLUE, False, [(int(a), int(b)) for a, b in spts])
    if candle_mode:
        bw = max(2.0, step * 0.6)
        for i in range(n):
            xx = xs(i)
            cc = GREEN if closes[i] >= opens[i] else RED
            pygame.draw.line(screen, cc, (xx, Y(highs[i])), (xx, Y(lows[i])))
            top, bot = Y(max(opens[i], closes[i])), Y(min(opens[i], closes[i]))
            pygame.draw.rect(screen, cc, (xx - bw / 2, top, bw, max(1, bot - top)))
    else:
        ppts = [(xs(i), Y(p)) for i, p in enumerate(closes)]
        pygame.draw.lines(screen, tuple(int(c * 0.3) for c in col), False,
                          [(int(a), int(b)) for a, b in ppts], 4)
        pygame.draw.lines(screen, col, False, [(int(a), int(b)) for a, b in ppts], 2)
        pygame.draw.circle(screen, col, (int(ppts[-1][0]), int(ppts[-1][1])), 3)
    for (t, p, side, cc) in s.marks[-100:]:
        i = (t - off) // CANDLE_PER if candle_mode else t - off
        if 0 <= i < n:
            xx, yy = xs(i), Y(p)
            up = (side in ("BUY", "COVER"))
            cy = yy + 11 if up else yy - 11
            tri(screen, xx, cy, up, (12, 16, 22), 7)
            tri(screen, xx, cy, up, cc, 5)
    mp = MOUSE
    if P.collidepoint(mp):
        i = max(0, min(n - 1, int((mp[0] - P.x) / step) if candle_mode
                       else int((mp[0] - P.x) / P.w * (n - 1))))
        val = closes[i]
        xx, yy = xs(i), Y(val)
        dline(screen, (xx, P.y), (xx, P.bottom), (96, 108, 126))
        dline(screen, (P.x, yy), (P.right, yy), (96, 108, 126))
        pygame.draw.circle(screen, (240, 244, 248), (int(xx), int(yy)), 2)
        tr = pygame.Rect(P.right - 64, int(yy) - 9, 64, 18)
        pygame.draw.rect(screen, (230, 235, 240), tr, border_radius=4)
        txt(screen, f"{val:,.2f}", tr.centerx, tr.centery, 11, (12, 16, 22),
            bold=True, mono=True, align="mc")
        t_abs = off + (i * CANDLE_PER + CANDLE_PER - 1 if candle_mode else i)
        lx = min(max(xx + 8, P.x + 4), P.right - 96)
        txt(screen, f"D{t_abs//25+1} · T{t_abs}", lx, P.y + 4, 10,
            (150, 162, 180), mono=True)
    screen.set_clip(None)
    ty = min(max(Y(s.price), P.y + 10), P.bottom - 10)
    tag = pygame.Rect(P.right - 58, int(ty) - 10, 58, 20)
    pygame.draw.line(screen, col, (tag.x - 6, ty), (P.right, ty), 1)
    pygame.draw.rect(screen, col, tag, border_radius=4)
    txt(screen, f"{s.price:,.2f}", tag.centerx, tag.centery, 11, (10, 14, 18),
        bold=True, mono=True, align="mc")
    if s.halted_now(mkt):
        ov = pygame.Surface(P.size, pygame.SRCALPHA)
        ov.fill((255, 60, 50, 22))
        screen.blit(ov, P.topleft)
        txt(screen, "TRADING HALTED -- circuit breaker active", P.centerx,
            P.y + 10, 13, RED, bold=True, align="mc")
    maxv = max(vols) + 1e-9
    txt(screen, f"VOL · peak {fmt_k(maxv)}/tick", V.x, V.y - 12, 9, DIM)
    pygame.draw.line(screen, (28, 35, 46), (V.x, V.bottom), (V.right, V.bottom))
    bw = max(2.0, step * 0.6) if candle_mode else max(1.0, P.w / n - 1.0)
    for i, vv in enumerate(vols):
        if candle_mode:
            cc = GREEN if closes[i] >= opens[i] else RED
        else:
            prev = closes[i - 1] if i > 0 else closes[0]
            cc = GREEN if closes[i] >= prev else RED
        hh = vv / maxv * V.h
        xx = xs(i)
        shade = tuple(int(c * (0.85 if i == n - 1 else 0.45)) for c in cc)
        pygame.draw.rect(screen, shade, (xx - bw / 2, V.bottom - hh, bw, hh))
    ly, lx = 478, 36
    pygame.draw.line(screen, col, (lx, ly + 6), (lx + 18, ly + 6), 2)
    lx += 24
    txt(screen, "price", lx, ly, 10, DIM)
    lx += F(10).size("price")[0] + 16
    dline(screen, (lx, ly + 6), (lx + 18, ly + 6), FVGOLD)
    lx += 24
    txt(screen, "fair value", lx, ly, 10, DIM)
    lx += F(10).size("fair value")[0] + 16
    pygame.draw.line(screen, BLUE, (lx, ly + 6), (lx + 18, ly + 6), 2)
    lx += 24
    txt(screen, "SMA20", lx, ly, 10, DIM)
    lx += F(10).size("SMA20")[0] + 16
    tri(screen, lx + 5, ly + 7, True, GREEN, 4)
    lx += 14
    txt(screen, "buy", lx, ly, 10, DIM)
    lx += F(10).size("buy")[0] + 12
    tri(screen, lx + 5, ly + 7, False, RED, 4)
    lx += 14
    txt(screen, "sell", lx, ly, 10, DIM)
    lx += F(10).size("sell")[0] + 14
    pygame.draw.rect(screen, (60, 110, 80), (lx, ly + 2, 14, 9))
    txt(screen, "volume", lx + 20, ly, 10, DIM)


def draw_feeds(screen, mkt, clicks):
    rect = pygame.Rect(16, 502, 592, 146)
    panel(screen, rect)
    txt(screen, "EXECUTION FEED", 28, 510, 11, DIM, bold=True)
    txt(screen, "click a fill to open the dossier", 596, 511, 9, (90, 100, 116),
        align="tr")
    fnt = F(12, mono=True)
    y = 528
    for e in reversed(mkt.trade_log[-6:]):
        row = pygame.Rect(24, y - 3, 560, 16)
        if row.collidepoint(MOUSE):
            pygame.draw.rect(screen, (30, 38, 50), row, border_radius=4)
        parts = [(f"D{e['t']//25+1:<3}", DIM),
                 (f"{e['ai'].name:<14}", e['ai'].color),
                 (f"{e['side']:<6}", SIDE_COLORS.get(e['side'], TEXT)),
                 (f"{fq(e['qty'])} {e['sym']}", TEXT),
                 (f"@ ${e['px']:,.2f}", DIM)]
        x = 28
        for st, c in parts:
            img = fnt.render(st, True, c)
            screen.blit(img, (x, y))
            x += img.get_width() + 8
        clicks.append((row, ("feed", mkt.traders.index(e['ai']))))
        y += 18
    rect = pygame.Rect(616, 502, 304, 146)
    panel(screen, rect)
    txt(screen, "MARKET NEWS", 628, 510, 11, DIM, bold=True)
    fnt2 = F(11)
    y = 528
    for (t, head, c) in reversed(mkt.news[-9:]):
        lines = wrap(head, fnt2, 258)
        if y + 14 * len(lines) > 640:
            break
        if mkt.tick - t < 60:
            pygame.draw.rect(screen, (32, 42, 54), (624, y - 3, 288,
                             14 * len(lines) + 5), border_radius=4)
        pygame.draw.rect(screen, c, (628, y + 2, 5, 5), border_radius=2)
        for j, ln in enumerate(lines):
            screen.blit(fnt2.render(ln, True, TEXT), (641, y + j * 14))
        y += 14 * len(lines) + 5


def draw_leaderboard(screen, mkt, clicks):
    rect = pygame.Rect(928, 88, 336, 560)
    panel(screen, rect)
    txt(screen, "LEADERBOARD", 944, 96, 12, DIM, bold=True)
    txt(screen, "click rows for dossier", 1248, 97, 9, (90, 100, 116), align="tr")
    txt(screen, "net worth", 1248, 108, 10, DIM, mono=True, align="tr")
    ranked = sorted(mkt.traders, key=lambda t: t.net_worth(mkt), reverse=True)
    y = 122
    for i, t in enumerate(ranked):
        idx = mkt.traders.index(t)
        row = pygame.Rect(938, y, 316, 50)
        hov = row.collidepoint(MOUSE)
        pygame.draw.rect(screen, (30, 38, 50) if hov else PANEL2, row, border_radius=8)
        bc = GOLD if i == 0 else ((100, 115, 135) if hov else BORDER)
        if mkt.bet and mkt.bet["idx"] == idx and i != 0:
            bc = (150, 130, 40)
        pygame.draw.rect(screen, bc, row, 1, border_radius=8)
        pygame.draw.rect(screen, t.color, (row.x + 5, y + 7, 4, 36), border_radius=2)
        medal = (GOLD, (200, 206, 214), (205, 127, 50))[i] if i < 3 else DIM
        txt(screen, str(i + 1), row.x + 16, y + 6, 12, medal, bold=True, mono=True)
        if i == 0:
            crown(screen, row.x + 33, y + 12, 13)
        nx = row.x + 44
        txt(screen, t.name, nx, y + 5, 13, t.color, bold=True)
        txt(screen, "> " + trunc(t.status, F(10), 156), nx, y + 25, 10,
            (150, 162, 180))
        sr = pygame.Rect(row.x + 208, y + 8, 54, 34)
        spark(screen, sr, t.nw_hist[-240:], t.color)
        tx = row.right - 10
        nw = t.net_worth(mkt)
        txt(screen, f"${nw:,.0f}", tx, y + 5, 13, TEXT, bold=True, mono=True, align="tr")
        pct = (nw / START_CASH - 1) * 100
        txt(screen, f"{pct:+.1f}%", tx, y + 23, 11, GREEN if pct >= 0 else RED,
            mono=True, align="tr")
        if mkt.bet and mkt.bet["idx"] == idx:
            txt(screen, "BET", row.right - 12, y + 39, 8, GOLD, bold=True, align="tr")
        clicks.append((row, ("row", idx)))
        y += 53


def draw_guide(screen):
    rect = pygame.Rect(16, 656, 300, 186)
    panel(screen, rect)
    txt(screen, "SPECTATOR GUIDE", 28, 664, 11, DIM, bold=True)
    rows = [("SPACE", "pause · N step one tick"),
            ("1-4",   "speed · TAB next chart"),
            ("C",     "candles/line · M sound"),
            ("B",     "place a side bet"),
            ("F",     "fullscreen · R restart"),
            ("CLICK", "rows, tiles, fills, chart")]
    y = 684
    for k, v in rows:
        txt(screen, k, 30, y, 11, TEXT, bold=True, mono=True)
        txt(screen, v, 92, y, 11, DIM)
        y += 20
    dline(screen, (30, y + 4), (284, y + 4), BORDER)
    tri(screen, 36, y + 16, True, GREEN, 4)
    txt(screen, "buy", 46, y + 10, 10, DIM)
    tri(screen, 80, y + 16, False, RED, 4)
    txt(screen, "sell", 90, y + 10, 10, DIM)
    dline(screen, (122, y + 16), (140, y + 16), FVGOLD)
    txt(screen, "fair value", 146, y + 10, 10, DIM)
    txt(screen, f"v{__version__}", rect.right - 12, rect.bottom - 16, 9,
        (90, 100, 116), align="tr")


def draw_heatmap(screen, mkt, sel, frame, clicks):
    rect = pygame.Rect(324, 656, 402, 186)
    panel(screen, rect)
    txt(screen, "MARKET HEATMAP · session %", 336, 664, 11, DIM, bold=True)
    tw, th, gap, x0, y0 = 88, 66, 8, 336, 684
    for i, s in enumerate(mkt.stocks):
        r = pygame.Rect(x0 + (i % 4) * (tw + gap), y0 + (i // 4) * (th + gap), tw, th)
        pct = s.ret(100) * 100
        k = min(1.0, abs(pct) / 0.09)
        col = GREEN if pct >= 0 else RED
        bg = tuple(int(PANEL2[c] * (1 - k * 0.55) + col[c] * k * 0.55) for c in range(3))
        pygame.draw.rect(screen, bg, r, border_radius=8)
        bc = (120, 140, 170) if i == sel else BORDER
        mv = s.ret(12)
        if abs(mv) > 0.05 and frame % 30 < 15:
            bc = GREEN if mv > 0 else RED
        pygame.draw.rect(screen, bc, r, 1, border_radius=8)
        txt(screen, s.symbol, r.centerx, r.y + 8, 12, TEXT, bold=True, align="tc")
        txt(screen, f"{pct:+.1f}%", r.centerx, r.y + 25, 14,
            col if abs(pct) > 0.001 else DIM, bold=True, mono=True, align="tc")
        if s.halted_now(mkt):
            txt(screen, "HALTED", r.centerx, r.y + 46, 8, RED, bold=True, align="tc")
        else:
            txt(screen, s.sector[:14], r.centerx, r.bottom - 14, 8,
                (140, 152, 170), align="tc")
        clicks.append((r, ("tile", i)))


def draw_sentiment(screen, mkt):
    rect = pygame.Rect(734, 656, 530, 186)
    panel(screen, rect)
    txt(screen, "MARKET SENTIMENT", 746, 664, 11, DIM, bold=True)
    rc = {"CALM": (86, 214, 255), "NORMAL": (200, 206, 214), "TURBULENT": RED}[mkt.regime]
    chip(screen, pygame.Rect(746, 684, 128, 34), mkt.regime, rc, size=14)
    txt(screen, "volatility regime", 746, 724, 9, DIM)
    txt(screen, f"HOT: {mkt.hot_sector}", 746, 742, 11, (120, 235, 160), bold=True)
    txt(screen, f"COLD: {mkt.cold_sector}", 746, 760, 11, (140, 170, 255), bold=True)
    vix = arena_vix(mkt)
    vc = GREEN if vix < 16 else (GOLD if vix < 30 else RED)
    txt(screen, f"{vix:.0f}", 906, 682, 22, vc, bold=True, mono=True)
    txt(screen, "ARENA VOL INDEX", 906, 712, 9, DIM)
    txt(screen, "calm <16 · wild >30", 906, 726, 9, (110, 122, 140))
    above = sum(1 for s in mkt.stocks if s.sma(20) and s.price > s.sma(20))
    txt(screen, f"{above}/{len(mkt.stocks)}", 1035, 682, 22, TEXT, bold=True, mono=True)
    txt(screen, "above SMA20", 1035, 712, 9, DIM)
    avg = sum(s.ret(40) for s in mkt.stocks) / len(mkt.stocks)
    txt(screen, f"{avg*100:+.2f}%", 1250, 682, 22, GREEN if avg >= 0 else RED,
        bold=True, mono=True, align="tr")
    txt(screen, "avg drift (40 ticks)", 1250, 712, 9, DIM, align="tr")
    g = pygame.Rect(756, 792, 486, 20)
    pygame.draw.rect(screen, PANEL2, g, border_radius=4)
    m = max(-1.0, min(1.0, avg / 0.05))
    cx, half = g.centerx, g.w / 2 - 4
    if abs(m) > 0.01:
        wdt = abs(m) * half
        xx = cx if m > 0 else cx - wdt
        pygame.draw.rect(screen, GREEN if m > 0 else RED,
                         (int(xx), g.y + 2, int(wdt), g.h - 4), border_radius=3)
    pygame.draw.line(screen, BORDER, (cx, g.y + 2), (cx, g.bottom - 2), 2)
    pygame.draw.rect(screen, BORDER, g, 1, border_radius=4)
    xn = int(cx + m * half)
    pygame.draw.polygon(screen, TEXT, [(xn - 5, g.y - 7), (xn + 5, g.y - 7), (xn, g.y + 1)])
    txt(screen, "BEAR", g.x, g.bottom + 4, 9, DIM)
    txt(screen, "BULL", g.right, g.bottom + 4, 9, DIM, align="tr")


def draw_banner(screen, mkt):
    if mkt.banner_frames <= 0 or not mkt.banner or mkt.over:
        return
    mkt.banner_frames -= 1
    a = min(235, 80 + mkt.banner_frames * 3)
    surf = pygame.Surface((800, 52), pygame.SRCALPHA)
    pygame.draw.rect(surf, (14, 19, 27, a), surf.get_rect(), border_radius=12)
    pygame.draw.rect(surf, (*GOLD, a), surf.get_rect(), 2, border_radius=12)
    txt(surf, mkt.banner, 400, 26, 14, GOLD, bold=True, align="mc")
    screen.blit(surf, ((WIDTH - 800) // 2, 128))


def draw_toasts(screen, mkt):
    for t in mkt.toasts:
        t["ttl"] -= 1
    mkt.toasts[:] = [t for t in mkt.toasts if t["ttl"] > 0]
    y = 142
    for t in mkt.toasts[-4:]:
        a = min(1.0, t["ttl"] / 60)
        f = F(13, True)
        w = f.size(t["text"])[0] + 30
        r = pygame.Rect(640 - w // 2, y, w, 26)
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (12, 16, 24, int(215 * a)), s.get_rect(), border_radius=13)
        pygame.draw.rect(s, (*t["color"], int(255 * a)), s.get_rect(), 1, border_radius=13)
        screen.blit(s, r.topleft)
        img = f.render(t["text"], True, t["color"])
        img.set_alpha(int(255 * a))
        screen.blit(img, (r.x + 15, r.y + 6))
        y += 32


def draw_inspector(screen, mkt, t, clicks, bankroll):
    idx = mkt.traders.index(t)
    pr = pygame.Rect(250, 108, 780, 644)
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((6, 9, 14, 165))
    screen.blit(dim, (0, 0))
    panel(screen, pr)
    pygame.draw.rect(screen, (90, 110, 140), pr, 2, border_radius=10)
    pygame.draw.rect(screen, t.color, (pr.x + 18, pr.y + 18, 10, 44), border_radius=3)
    txt(screen, t.name, pr.x + 40, pr.y + 16, 20, t.color, bold=True)
    txt(screen, f"{t.blurb}   ·   {t.kind.upper()}", pr.x + 40, pr.y + 42, 12, DIM)
    txt(screen, "status: " + trunc(t.status, F(12), 540), pr.x + 40, pr.y + 64, 12, DIM)
    ranked = sorted(mkt.traders, key=lambda x: x.net_worth(mkt), reverse=True)
    rank = ranked.index(t) + 1
    medal = (GOLD, (200, 206, 214), (205, 127, 50))[rank - 1] if rank <= 3 else DIM
    probs = win_probs(mkt)
    txt(screen, f"RANK #{rank} / {len(mkt.traders)}", pr.right - 20, pr.y + 18, 14,
        medal, bold=True, mono=True, align="tr")
    txt(screen, f"win prob ~{probs[idx]*100:.0f}%", pr.right - 20, pr.y + 40, 12,
        DIM, mono=True, align="tr")
    nw = t.net_worth(mkt)
    u = t.unrealized(mkt)
    wr = (sum(1 for p in t.closed if p > 0) / len(t.closed)) if t.closed else None
    col1 = [("net worth", money(nw)), ("cash", money(t.cash)),
            ("realized p&l", smoney(t.realized)), ("unrealized p&l", smoney(u)),
            ("max drawdown", f"{t.max_dd*100:.1f}%")]
    col2 = [("orders", str(t.orders)), ("closed trades", str(len(t.closed))),
            ("win rate", f"{wr*100:.0f}%" if wr is not None else "--"),
            ("best trade", smoney(max(t.closed)) if t.closed else "--"),
            ("worst trade", smoney(min(t.closed)) if t.closed else "--"),
            ("blowups", str(t.blowups))]
    y0 = pr.y + 92
    for i, (k, v) in enumerate(col1):
        txt(screen, k, pr.x + 40, y0 + i * 24, 11, DIM)
        txt(screen, v, pr.x + 170, y0 + i * 24 - 2, 14, TEXT, bold=True, mono=True)
    for i, (k, v) in enumerate(col2):
        txt(screen, k, pr.x + 380, y0 + i * 24, 11, DIM)
        txt(screen, v, pr.x + 510, y0 + i * 24 - 2, 14, TEXT, bold=True, mono=True)
    eq = pygame.Rect(pr.x + 40, pr.y + 246, 700, 148)
    txt(screen, "EQUITY CURVE (season)", eq.x, eq.y - 16, 11, DIM, bold=True)
    pygame.draw.rect(screen, PANEL2, eq, border_radius=8)
    pygame.draw.rect(screen, BORDER, eq, 1, border_radius=8)
    data = t.nw_hist
    if len(data) >= 2:
        mn, mx = min(data), max(data)
        if mx - mn < 1e-9:
            mx = mn + 1
        pad = (mx - mn) * 0.08
        mn -= pad
        mx += pad
        n = len(data)
        X = lambda i: eq.x + 6 + i * (eq.w - 12) / (n - 1)
        Y = lambda v: eq.bottom - 8 - (v - mn) / (mx - mn) * (eq.h - 16)
        if mn <= START_CASH <= mx:
            dline(screen, (eq.x + 4, Y(START_CASH)), (eq.right - 4, Y(START_CASH)),
                  (70, 84, 102))
        pts = [(X(i), Y(v)) for i, v in enumerate(data)]
        pygame.draw.lines(screen, tuple(int(c * 0.4) for c in t.color), False,
                          [(int(a), int(b)) for a, b in pts], 4)
        pygame.draw.lines(screen, t.color, False, [(int(a), int(b)) for a, b in pts], 2)
        pygame.draw.circle(screen, t.color, (int(pts[-1][0]), int(pts[-1][1])), 3)
        txt(screen, f"{mx:,.0f}", eq.right - 8, eq.y + 4, 10, DIM, mono=True, align="tr")
        txt(screen, f"{mn:,.0f}", eq.right - 8, eq.bottom - 14, 10, DIM, mono=True,
            align="tr")
    else:
        txt(screen, "collecting data...", eq.centerx, eq.centery, 12, DIM, align="mc")
    py = eq.bottom + 16
    txt(screen, "OPEN POSITIONS", pr.x + 40, py, 11, DIM, bold=True)
    hy = py + 17
    for hlab, hx in (("SYMBOL", pr.x + 40), ("SIDE", pr.x + 130), ("QTY", pr.x + 190),
                     ("AVG COST", pr.x + 270), ("LAST", pr.x + 370),
                     ("P&L $", pr.x + 460), ("P&L %", pr.x + 560)):
        txt(screen, hlab, hx, hy, 10, (110, 122, 140), bold=True)
    yy = hy + 15
    holds = sorted(t.holdings.items(),
                   key=lambda kv: abs(kv[1] * mkt.by_sym[kv[0]].price), reverse=True)
    if not holds:
        txt(screen, "flat -- sitting in cash", pr.x + 40, yy + 4, 12, DIM)
    for sym, q in holds[:7]:
        s = mkt.by_sym[sym]
        ac = t.avg_cost.get(sym, s.price)
        if q > 0:
            pnl, pc, side, sc = (s.price - ac) * q, s.price / ac - 1, "LONG", GREEN
        else:
            pnl, pc, side, sc = (ac - s.price) * (-q), ac / s.price - 1, "SHORT", RED
        txt(screen, sym, pr.x + 40, yy, 12, TEXT, bold=True, mono=True)
        txt(screen, side, pr.x + 130, yy, 11, sc, bold=True)
        txt(screen, fq(q), pr.x + 190, yy, 12, TEXT, mono=True)
        txt(screen, f"{ac:,.2f}", pr.x + 270, yy, 12, DIM, mono=True)
        txt(screen, f"{s.price:,.2f}", pr.x + 370, yy, 12, TEXT, mono=True)
        txt(screen, smoney(pnl), pr.x + 460, yy, 12, GREEN if pnl >= 0 else RED, mono=True)
        txt(screen, f"{pc*100:+.1f}%", pr.x + 560, yy, 12, GREEN if pnl >= 0 else RED,
            mono=True)
        yy += 20
    fy = pr.bottom - 54
    if mkt.bet is None and not mkt.over and bankroll >= 100:
        button(screen, pygame.Rect(pr.x + 40, fy, 210, 38), "BET ON THIS BOT",
               True, clicks, ("m_bet", idx), size=13, accent=GOLD)
    else:
        why = ("season over" if mkt.over else
               ("bet already in play" if mkt.bet else "bankroll too low"))
        txt(screen, f"betting unavailable -- {why}", pr.x + 40, fy + 12, 12, DIM)
    txt(screen, "ESC closes · data updates live", pr.x + 300, fy + 12, 10, DIM)
    button(screen, pygame.Rect(pr.right - 140, fy, 100, 38), "CLOSE", False,
           clicks, ("m_close",), size=13)


def draw_betdialog(screen, mkt, sel, stake, bankroll, clicks):
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((6, 9, 14, 175))
    screen.blit(dim, (0, 0))
    pr = pygame.Rect(390, 216, 500, 428)
    panel(screen, pr)
    pygame.draw.rect(screen, GOLD, pr, 2, border_radius=10)
    txt(screen, "PLACE A SIDE BET", pr.centerx, 234, 19, GOLD, bold=True, align="tc")
    txt(screen, "payouts --  #1: 3.0x    #2: 1.8x    #3: 1.3x", pr.centerx, 262, 12,
        DIM, align="tc")
    if mkt.over:
        txt(screen, "season over -- betting closed", pr.centerx, 340, 14, RED, align="tc")
        button(screen, pygame.Rect(pr.centerx - 70, pr.bottom - 64, 140, 36),
               "CLOSE", False, clicks, ("m_cancel",), size=13)
        return
    if mkt.bet:
        t = mkt.traders[mkt.bet["idx"]]
        txt(screen, "BET IN PLAY", pr.centerx, 316, 13, DIM, bold=True, align="tc")
        txt(screen, f"${mkt.bet['stake']:,.0f} on {t.name}", pr.centerx, 340, 18,
            t.color, bold=True, align="tc")
        probs = win_probs(mkt)
        txt(screen, f"current win prob ~{probs[mkt.bet['idx']]*100:.0f}%  ·  "
            f"settles at season end", pr.centerx, 372, 12, DIM, align="tc")
        button(screen, pygame.Rect(pr.centerx - 70, pr.bottom - 64, 140, 36),
               "CLOSE", False, clicks, ("m_cancel",), size=13)
        return
    t = mkt.traders[sel]
    for r, lab, act in ((pygame.Rect(pr.x + 36, 296, 44, 44), "<", ("m_prev",)),
                        (pygame.Rect(pr.right - 80, 296, 44, 44), ">", ("m_next",))):
        pygame.draw.rect(screen, PANEL2, r, border_radius=8)
        pygame.draw.rect(screen, BORDER, r, 1, border_radius=8)
        txt(screen, lab, r.centerx, r.centery, 18, TEXT, bold=True, align="mc")
        clicks.append((r, act))
    txt(screen, t.name, pr.centerx, 300, 18, t.color, bold=True, align="tc")
    txt(screen, t.blurb, pr.centerx, 324, 11, DIM, align="tc")
    probs = win_probs(mkt)
    rank = sorted(mkt.traders, key=lambda x: x.net_worth(mkt), reverse=True).index(t) + 1
    txt(screen, f"rank #{rank}  ·  win prob ~{probs[sel]*100:.0f}%", pr.centerx, 344,
        12, (155, 168, 186), mono=True, align="tc")
    txt(screen, "STAKE", pr.centerx, 380, 11, DIM, bold=True, align="tc")
    txt(screen, f"${stake:,.0f}", pr.centerx, 396, 24, TEXT, bold=True, mono=True,
        align="tc")
    opts = [("+100", 100), ("+500", 500), ("+1K", 1000), ("MAX", "max"), ("CLR", "clr")]
    bw, gap = 84, 8
    x0 = pr.centerx - (bw * 5 + gap * 4) // 2
    for i, (lab, val) in enumerate(opts):
        r = pygame.Rect(x0 + i * (bw + gap), 434, bw, 30)
        button(screen, r, lab, False, clicks, ("m_stake", val), size=12, mono=True)
    if stake > bankroll:
        txt(screen, "not enough bankroll", pr.centerx, 478, 12, RED, align="tc")
    elif 0 < stake < 100:
        txt(screen, "minimum bet is $100", pr.centerx, 478, 12, RED, align="tc")
    else:
        txt(screen, f"bankroll ${bankroll:,.0f}  ->  ${bankroll - stake:,.0f} after bet",
            pr.centerx, 478, 12, DIM, mono=True, align="tc")
    ok = 100 <= stake <= bankroll
    button(screen, pygame.Rect(pr.x + 44, pr.bottom - 62, 190, 38), "PLACE BET",
           ok, clicks, ("m_place",), size=14, accent=GOLD)
    button(screen, pygame.Rect(pr.right - 234, pr.bottom - 62, 190, 38), "CANCEL",
           False, clicks, ("m_cancel",), size=13)


def draw_pause(screen):
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((6, 9, 14, 170))
    screen.blit(dim, (0, 0))
    txt(screen, "PAUSED", WIDTH // 2, HEIGHT // 2 - 44, 42, TEXT, bold=True, align="mc")
    txt(screen, "SPACE resume · N advance one tick", WIDTH // 2, HEIGHT // 2 + 8,
        15, DIM, align="mc")
    txt(screen, QUIT_HINT, WIDTH // 2, HEIGHT // 2 + 32, 13, (110, 122, 140), align="mc")
    txt(screen, "click a trader row to study their dossier", WIDTH // 2,
        HEIGHT // 2 + 56, 13, (110, 122, 140), align="mc")


def draw_gameover(screen, mkt, frame, bankroll, save):
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((6, 9, 14, 205))
    screen.blit(dim, (0, 0))
    pr = pygame.Rect(WIDTH // 2 - 390, 66, 780, 724)
    panel(screen, pr)
    pygame.draw.rect(screen, GOLD, pr, 2, border_radius=10)
    txt(screen, f"SEASON {mkt.season} COMPLETE", WIDTH // 2, 84, 26, GOLD,
        bold=True, align="tc")
    ranked = sorted(mkt.traders, key=lambda t: t.net_worth(mkt), reverse=True)
    w = ranked[0]
    nw = w.net_worth(mkt)
    crown(screen, WIDTH // 2, 148, 30)
    txt(screen, w.name, WIDTH // 2, 166, 24, w.color, bold=True, align="tc")
    txt(screen, f"final net worth {money(nw)}   ·   return {(nw/START_CASH-1)*100:+.1f}%",
        WIDTH // 2, 196, 13, DIM, mono=True, align="tc")
    base, maxv = 352, max(ranked[0].net_worth(mkt), 1)
    trio = [(ranked[1], 490), (ranked[0], 600), (ranked[2], 710)]
    for t, bx in trio:
        v = t.net_worth(mkt)
        h = 36 + (v / maxv) * 110
        r = pygame.Rect(bx, base - h, 92, h)
        pygame.draw.rect(screen, tuple(int(c * 0.35) for c in t.color), r)
        pygame.draw.rect(screen, GOLD if t is w else t.color, r, 1)
        txt(screen, f"${v:,.0f}", r.centerx, r.y - 14, 10, TEXT, mono=True, align="tc")
        txt(screen, trunc(t.name, F(10), 100), r.centerx, base + 6, 10, t.color,
            bold=True, align="tc")
    pygame.draw.line(screen, BORDER, (280, 396), (1000, 396))
    txt(screen, "#", 280, 406, 10, (110, 122, 140), bold=True)
    txt(screen, "trader", 312, 406, 10, (110, 122, 140), bold=True)
    txt(screen, "orders", 520, 406, 10, (110, 122, 140), bold=True)
    txt(screen, "net worth", 930, 406, 10, (110, 122, 140), bold=True, align="tr")
    txt(screen, "return", 1010, 406, 10, (110, 122, 140), bold=True, align="tr")
    y = 426
    for i, t in enumerate(ranked):
        tv = t.net_worth(mkt)
        tp = (tv / START_CASH - 1) * 100
        rc = (GOLD, (200, 206, 214), (205, 127, 50))[i] if i < 3 else DIM
        txt(screen, str(i + 1), 280, y, 13, rc, bold=True, mono=True)
        txt(screen, t.name, 312, y, 13, t.color, bold=True)
        txt(screen, str(t.orders), 520, y + 2, 11, DIM, mono=True)
        txt(screen, f"${tv:,.0f}", 930, y, 13, TEXT, bold=True, mono=True, align="tr")
        txt(screen, f"{tp:+.1f}%", 1010, y, 12, GREEN if tp >= 0 else RED,
            mono=True, align="tr")
        y += 24
    b = max(mkt.stocks, key=lambda s: s.ret(TOTAL))
    wo = min(mkt.stocks, key=lambda s: s.ret(TOTAL))
    txt(screen, f"season best {b.symbol} {b.ret(TOTAL)*100:+.0f}%   ·   "
        f"worst {wo.symbol} {wo.ret(TOTAL)*100:+.0f}%", WIDTH // 2, 660, 12,
        TEXT, mono=True, align="tc")
    if mkt.bet_result:
        br = mkt.bet_result
        if br["payout"] > 0:
            msg, cc = (f"YOUR BET · ${br['stake']:,.0f} on {br['name']} -> finished "
                       f"#{br['rank']} -> paid ${br['payout']:,.0f}!", GREEN)
        else:
            msg, cc = (f"YOUR BET · ${br['stake']:,.0f} on {br['name']} -> finished "
                       f"#{br['rank']} -> stake lost", RED)
        txt(screen, msg, WIDTH // 2, 684, 13, cc, bold=True, align="tc")
    else:
        txt(screen, "no side bet placed this season", WIDTH // 2, 684, 11, DIM,
            align="tc")
    txt(screen, f"bankroll ${bankroll:,.0f} · record {save['wins']}W-{save['losses']}L",
        WIDTH // 2, 708, 12, DIM, mono=True, align="tc")
    hof = sorted(save.get("hof", {}).items(), key=lambda kv: -kv[1])[:4]
    if hof:
        txt(screen, "HALL OF FAME · " + "   ".join(f"{n} x{c}" for n, c in hof),
            WIDTH // 2, 730, 11, GOLD, mono=True, align="tc")
    if frame % 70 < 45:
        txt(screen, "press  R  for a new season", WIDTH // 2, 756, 16, GOLD,
            bold=True, align="tc")
    txt(screen, f"AI Trading Arena v{__version__}", WIDTH // 2, 778, 9,
        (95, 105, 122), align="tc")

# ------------------------------------------------------------------- main --
def main():
    global MOUSE
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    pygame.init()
    try:
        pygame.display.set_icon(make_icon())
    except Exception:
        pass
    pygame.display.set_caption(f"AI Trading Arena v{__version__}")
    win = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    canvas = pygame.Surface((WIDTH, HEIGHT))
    try:
        pygame.event.set_blocked(pygame.MOUSEMOTION)
    except Exception:
        pass
    clock = pygame.time.Clock()
    snd = SoundKit()
    snd.ensure()                          # desktop: audio ready immediately
    save = load_save()
    bankroll = save["bankroll"]
    if bankroll < 100:
        bankroll += 500.0
    season_num = save["season"] + 1

    def start_season(sn):
        m = Market(sn)
        m.snd = snd
        m.warmup()
        return m

    mkt = start_season(season_num)
    scene = "title"
    paused, speed_i, acc, sel, frame = False, 0, 0.0, 0, 0
    candle = False
    modal = None
    bet_sel, bet_stake = 0, 0
    clicks, mclicks = [], []
    running = True

    def open_bet(preselect=None):
        nonlocal modal, bet_sel, bet_stake
        if mkt.bet or mkt.over:
            mkt.toast("bet already in play" if mkt.bet else "betting closed", RED)
            return
        if bankroll < 100:
            mkt.toast("bankroll too low (min $100)", RED)
            return
        if preselect is not None:
            bet_sel = preselect
        bet_stake = min(1000, int(bankroll))
        modal = ("bet",)

    def place_bet():
        nonlocal modal, bet_stake, bankroll
        if not (100 <= bet_stake <= bankroll):
            return
        mkt.bet = {"idx": bet_sel, "stake": float(bet_stake)}
        bankroll -= bet_stake
        save["bankroll"] = bankroll
        save_save(save)
        t = mkt.traders[bet_sel]
        mkt.toast(f"Bet placed: ${bet_stake:,.0f} on {t.name}", GOLD)
        mkt.add_news(f"Spectator bets ${bet_stake:,.0f} on {t.name}!", GOLD)
        snd.play("cash")
        modal = None

    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.1)
        frame += 1
        w, h = win.get_size()
        scale = min(w / WIDTH, h / HEIGHT)
        ox = (w - WIDTH * scale) / 2.0
        oy = (h - HEIGHT * scale) / 2.0
        mp = pygame.mouse.get_pos()
        MOUSE = (int((mp[0] - ox) / scale), int((mp[1] - oy) / scale)) if scale > 0 else mp
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == WFL or (e.type == pygame.ACTIVEEVENT
                                   and getattr(e, "gain", 1) == 0):
                if scene == "game" and not mkt.over:
                    paused = True
            elif e.type == pygame.KEYDOWN:
                if scene == "title":
                    scene = "game"
                elif e.key == pygame.K_ESCAPE:          # desktop: quit
                    if modal:
                        modal = None
                    else:
                        running = False
                elif e.key == pygame.K_q and paused:
                    running = False
                elif e.key == pygame.K_SPACE:
                    paused = not paused
                elif e.key == pygame.K_n and paused and not mkt.over:
                    mkt.step()
                elif pygame.K_1 <= e.key <= pygame.K_4:
                    speed_i = e.key - pygame.K_1
                elif e.key == pygame.K_c:
                    candle = not candle
                elif e.key == pygame.K_m:
                    snd.ensure()
                    snd.on = not snd.on
                    mkt.toast("sound ON" if snd.on else "sound OFF", (120, 170, 255))
                elif e.key == pygame.K_f:
                    try:
                        pygame.display.toggle_fullscreen()
                    except Exception:
                        pass
                elif e.key == pygame.K_b:
                    open_bet()
                elif e.key == pygame.K_TAB:
                    sel = (sel + 1) % len(mkt.stocks)
                elif e.key == pygame.K_r:
                    save["season"] = season_num
                    save["bankroll"] = bankroll
                    save_save(save)
                    season_num += 1
                    mkt = start_season(season_num)
                    sel, paused, acc, modal = 0, False, 0.0, None
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if scene == "title":
                    scene = "game"
                else:
                    if scale > 0:
                        mx = int((e.pos[0] - ox) / scale)
                        my = int((e.pos[1] - oy) / scale)
                    else:
                        mx, my = e.pos
                    source = mclicks if modal else clicks
                    for r, act in source:
                        if r.collidepoint(mx, my):
                            kind = act[0]
                            if kind == "pause":
                                paused = not paused
                            elif kind == "speed":
                                speed_i = act[1]
                            elif kind in ("tab", "tile"):
                                sel = act[1]
                            elif kind == "candle":
                                candle = not candle
                            elif kind in ("row", "feed"):
                                modal = ("insp", act[1])
                                snd.play("click")
                            elif kind == "bet_open":
                                open_bet()
                            elif kind in ("m_close", "m_cancel"):
                                modal = None
                            elif kind == "m_prev":
                                bet_sel = (bet_sel - 1) % len(mkt.traders)
                            elif kind == "m_next":
                                bet_sel = (bet_sel + 1) % len(mkt.traders)
                            elif kind == "m_stake":
                                v = act[1]
                                if v == "max":
                                    bet_stake = int(bankroll)
                                elif v == "clr":
                                    bet_stake = 0
                                else:
                                    bet_stake = min(bet_stake + v, int(bankroll))
                            elif kind == "m_place":
                                place_bet()
                            elif kind == "m_bet":
                                open_bet(act[1])
                            break
        if mkt.over and not mkt.resolved:
            mkt.resolved = True
            ranked = sorted(mkt.traders, key=lambda t: t.net_worth(mkt), reverse=True)
            save["hof"] = dict(save.get("hof", {}))
            save["hof"][ranked[0].name] = save["hof"].get(ranked[0].name, 0) + 1
            if mkt.bet_result:
                bankroll += mkt.bet_result["payout"]
                if mkt.bet_result["payout"] > 0:
                    save["wins"] += 1
                else:
                    save["losses"] += 1
            save["bankroll"] = bankroll
            save_save(save)
            snd.play("fanfare")
        if scene == "game" and not paused and not mkt.over:
            acc += SPEEDS[speed_i][0] * dt
            steps = int(acc)
            if steps > 0:
                acc -= steps
                for _ in range(min(steps, 200)):
                    mkt.step()
        clicks, mclicks = [], []
        bg_clicks = mclicks if modal else clicks
        canvas.fill(BG)
        if scene == "title":
            draw_title(canvas, frame)
        else:
            draw_topbar(canvas, mkt, paused, speed_i, bankroll, bg_clicks)
            draw_tape(canvas, mkt, frame, speed_i)
            draw_tabs(canvas, mkt, sel, frame, bg_clicks)
            draw_chart(canvas, mkt, sel, candle, bg_clicks)
            draw_feeds(canvas, mkt, bg_clicks)
            draw_leaderboard(canvas, mkt, bg_clicks)
            draw_guide(canvas)
            draw_heatmap(canvas, mkt, sel, frame, bg_clicks)
            draw_sentiment(canvas, mkt)
            draw_banner(canvas, mkt)
            draw_toasts(canvas, mkt)
            if modal:
                if modal[0] == "insp":
                    draw_inspector(canvas, mkt, mkt.traders[modal[1]], mclicks, bankroll)
                else:
                    draw_betdialog(canvas, mkt, bet_sel, bet_stake, bankroll, mclicks)
            elif mkt.over:
                draw_gameover(canvas, mkt, frame, bankroll, save)
            elif paused:
                draw_pause(canvas)
        if abs(scale - 1.0) < 1e-3 and abs(ox) < 0.5 and abs(oy) < 0.5:
            win.blit(canvas, (int(ox), int(oy)))
        else:
            sw, sh = max(1, int(WIDTH * scale)), max(1, int(HEIGHT * scale))
            win.fill((5, 7, 10))
            win.blit(pygame.transform.scale(canvas, (sw, sh)), (int(ox), int(oy)))
        pygame.display.flip()
    save["season"] = season_num
    save["bankroll"] = bankroll
    save_save(save)
    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        pygame.quit()
        raise