#!/usr/bin/env python
# coding: utf-8
import time
import multiprocessing
from functools import partial
import pandas as pd
from itertools import combinations, permutations
import numpy as np

from trading_table import trading_table
import auxiliary as aux
import signals

start = time.time()
folder_path = '/home/ugur/bist_data/202011.csv'

data = pd.read_csv(folder_path, parse_dates=['time'])
data.time = data.time.apply(lambda x: pd.Timestamp(int(x)))
data = data[data.time.dt.hour < 15]
data['mid_price'] = (data['bid_price'] + data['ask_price']) / 2

reverse = False

pair_names = list(combinations(data.symbol.unique(), 2))

if reverse:
    all_pairs = list(permutations(data.symbol.unique(), 2))
    pair_names = list(set(all_pairs) - set(pair_names))


# data = data[data.symbol.isin(['GARAN', 'TSKB'])]


def run(pair_name: str, opt: dict, signal_func) -> pd.DataFrame:
    print(pair_name)
    # pair_name = ('GARAN', 'TSKB')
    mid_freq = opt['mid_freq']
    window_size = opt['window_size']
    threshold = opt['threshold']
    intercept = opt['intercept']
    wavelet = opt['wavelet']
    ln = opt['ln']

    pair_bid, pair_ask, pair_mid = aux.create_bid_ask_mid(pair_name, data)

    pair_mid = pair_mid.groupby(pd.Grouper(freq='D')).resample(mid_freq).mean().droplevel(0)
    if 'D' in mid_freq:
        pair_mid = pair_mid.ffill()
    else:
        pair_mid = pair_mid.resample('D').apply(aux.fill_nan).droplevel(0)

    if ln:
        pair_mid = np.log(pair_mid)

    pair_ask = pair_ask.resample('D').apply(aux.fill_nan).droplevel(0)

    pair_bid = pair_bid.resample('D').apply(aux.fill_nan).droplevel(0)

    pair_mid.dropna(inplace=True)
    pair_ask.dropna(inplace=True)
    pair_bid.dropna(inplace=True)

    trade_table = trading_table(pair_mid, pair_ask, pair_bid, window_size, threshold, intercept, wavelet, signal_func)
    return trade_table


def parallel_run(core, pairs, opt, signal_func):
    pool = multiprocessing.Pool(processes=core)
    run_with_opt = partial(run, opt=opt, signal_func=signal_func)
    result = pool.map(run_with_opt, pairs)
    return pd.concat(result)


if __name__ == '__main__':
    core = 8
    mid_freq = '1D',
    window_size = 7,
    threshold = 1,
    intercept = False,
    wavelet = False,
    ln = False,

    signal_func = signals.get_signal2

    opts = aux.multi_opt(mid_freq=mid_freq,
                         window_size=window_size,
                         threshold=threshold,
                         intercept=intercept,
                         wavelet=wavelet,
                         ln=ln)

    if isinstance(opts, dict):
        opt = opts
        df_trade_table = parallel_run(core, pair_names, opt, signal_func)
        file_name = aux.get_file_name(opt) + '_signalFunc_' + signal_func.__name__
        df_trade_table.to_csv(file_name + '_tradeTable' + '.csv', index=False)
    else:
        for opt in opts:
            df_trade_table = parallel_run(core, pair_names, opt, signal_func)
            file_name = aux.get_file_name(opt) + '_signalFunc_' + signal_func.__name__
            df_trade_table.to_csv(file_name + '_tradeTable' + '.csv', index=False)
print(time.time() - start)
