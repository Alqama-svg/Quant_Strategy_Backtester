# ---------------
# Strategy params
# ---------------
DAILY_TREND_WINDOW    = 5
INTRADAY_LOOKBACK     = 15
ATR_WINDOW            = 14

Z_THRESHOLD           = 0.65
CONFIRM_BARS          = 0
VOLUME_MIN_FACTOR     = 0.35

RISK_PER_TRADE        = 0.035
MAX_POSITION_FRACTION = 0.05
MAX_GROSS_EXPOSURE    = 2.2
MAX_OPEN_POSITIONS_TOTAL = 14

STOP_LOSS_PCT         = 0.022
TAKE_PROFIT_PCT       = 0.10

TRANSACTION_COST_PCT  = 0.0002
SLIPPAGE_PCT          = 0.0005
MINUTES_PER_DAY       = 390
SKIP_FIRST_MINUTES    = 3
SKIP_LAST_MINUTES     = 5

INITIAL_CAPITAL       = 1_000_000.0

ROLL_STD_FLOOR = 1e-4
VOL_FLOOR = 1e-4
ATR_FLOOR = 1e-4

# Output paths & behaviour
OUT_DIR = "./quantx_reports"
os.makedirs(OUT_DIR, exist_ok=True)
GENERATE_PDF = True
MAX_TICKER_CHARTS = 32            # max per-ticker images
MAX_TRADES_PER_TICKER_ZOOM = 0    # 0 = disabled (avoid 322 extra charts)

# ------------------------
# RUN_MODE -> dates
# ------------------------
if RUN_MODE == "JAN":
    START_DATE, END_DATE = "2024-01-02", "2024-01-31"
elif RUN_MODE == "FEB":
    START_DATE, END_DATE = "2024-02-01", "2024-02-29"
elif RUN_MODE == "JAN_FEB":
    START_DATE, END_DATE = "2024-01-02", "2024-02-29"
elif RUN_MODE == "JAN_JUN":
    START_DATE, END_DATE = "2024-01-02", "2024-06-28"
elif RUN_MODE == "JUL_SEP":
    START_DATE, END_DATE = "2024-07-01", "2024-09-30"
elif RUN_MODE == "OCT_DEC":
    START_DATE, END_DATE = "2024-10-01", "2024-12-31"
else:
    START_DATE, END_DATE = "2024-01-02", "2024-12-31"

TICKERS = ALL_TICKERS

print(f"QuantX FINAL Backtest | RUN_MODE={RUN_MODE}")
print(f"Running {len(TICKERS)} tickers: {TICKERS}")
print(f"Date range: {START_DATE} → {END_DATE}\n")

# ------------------------
# IO helper (robust & cached)
# ------------------------
_day_cache = {}
def _find_file_for_day(ticker, date_str):
    """
    Look inside DATA_ROOT/ticker for any file containing date_str in its filename and return full path.
    Accepts parquet, csv, pkl. Returns None if nothing found.
    """
    folder = os.path.join(DATA_ROOT, ticker)
    if not os.path.isdir(folder):
        return None
    # search for common extensions
    for ext in ("*.parquet", "*.parq", "*.csv", "*.pkl"):
        for fn in glob.glob(os.path.join(folder, f"*{date_str}*{ext.replace('*','')}")):
            return fn
    # fallback: any file with date_str substring
    for fn in os.listdir(folder):
        if date_str in fn:
            return os.path.join(folder, fn)
    return None

def load_minute_parquet_for_day(ticker, date_str):
    """
    Return pandas DataFrame with columns: timestamp, open, high, low, close, volume, ms_of_day
    or None if not available.
    """
    key = (ticker, date_str)
    if key in _day_cache:
        return _day_cache[key]

    candidate = _find_file_for_day(ticker, date_str)
    if candidate is None:
        _day_cache[key] = None
        return None
    try:
        if candidate.endswith((".parquet",".parq")):
            df_pl = pl.read_parquet(candidate)
            df = df_pl.to_pandas()
        elif candidate.endswith(".csv"):
            df = pd.read_csv(candidate)
        elif candidate.endswith(".pkl"):
            df = pd.read_pickle(candidate)
        else:
            # try read parquet/csv heuristics
            try:
                df_pl = pl.read_parquet(candidate)
                df = df_pl.to_pandas()
            except Exception:
                df = pd.read_csv(candidate)
    except Exception:
        _day_cache[key] = None
        return None

    # normalize columns and construct timestamp (support a couple of naming conventions)
    if 'date' not in df.columns or 'ms_of_day' not in df.columns:
        # try to infer
        if 'timestamp' in df.columns:
            # assume timestamp is epoch ms or ISO string
            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            except Exception:
                pass
        # if we don't have required columns, give up
    # If 'date' exists and 'ms_of_day' exists -> create timestamp
    if 'date' in df.columns and 'ms_of_day' in df.columns:
        df['date_dt'] = pd.to_datetime(df['date'].astype(str), format="%Y%m%d", errors='coerce')
        df['timestamp'] = df['date_dt'] + pd.to_timedelta(df['ms_of_day'], unit='ms')
    # else try parse 'timestamp' column (already)
    if 'timestamp' not in df.columns:
        _day_cache[key] = None
        return None

    # restrict to market hours if we can
    try:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.loc[
            (df['timestamp'].dt.time >= time(9,30)) &
            (df['timestamp'].dt.time <= time(16,0))
        ]
    except Exception:
        pass

    # standardize numeric columns existence
    for c in ['open','high','low','close','volume','ms_of_day']:
        if c not in df.columns:
            df[c] = np.nan

    df = df.sort_values('timestamp').reset_index(drop=True)
    if df.empty:
        _day_cache[key] = None
        return None
    _day_cache[key] = df[['timestamp','open','high','low','close','volume','ms_of_day']].copy()
    return _day_cache[key]