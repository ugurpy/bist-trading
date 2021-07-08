import pandas as pd
import numpy as np
import signals
import multiprocessing
from functools import partial
from itertools import combinations, permutations
import auxiliary as aux
import residual
from statsmodels.tsa.ar_model import AutoReg

path = ''
pricesfilename = 'data_18m.csv'
data = pd.read_csv(path + pricesfilename, parse_dates=['time'])
data = data[data.time.dt.hour < 15]
data['mid_price'] = (data['bid_price'] + data['ask_price']) / 2

mid_freq = '5Min'
ln = False
window_size = 96
threshold = 1
intercept = False
wavelet = False
signal_func = signals.get_signal


def get_date_ranges(datetime_list: pd.DatetimeIndex, n: int) -> list:
    """
    Parameters:
        datetime_list: Instance of DatetimeIndex consisting of timestamps.
        n: Number of steps.
    Return:
        list: A tuple list. Each tuple consists of 2 timestamps.

    """
    all_days = np.unique(datetime_list.date)

    all_days = pd.to_datetime(all_days)

    new_days = pd.Series(all_days).shift(-n)

    all_date_ranges = list(zip(all_days, new_days))

    idx_date_ranges = list(range(0, len(all_days), n))

    datetime_ranges = list(all_date_ranges[idx] for idx in idx_date_ranges)

    return datetime_ranges


def auto_req(resids):
    size = resids.dropna().__len__()

    if size < 3:
        return None

    ar_model = AutoReg(list(resids.dropna().cumsum()), lags=1).fit()
    a = ar_model.params[0]
    b = ar_model.params[1]
    residuals_of_ar_model = ar_model.resid
    ar_std = residuals_of_ar_model.std()

    # Obtain coefficients needed for Ornstein-Uhlenbeck model.

    # check conditions

    cond0 = (b > 0) & (b < 1)

    if (cond0):
        import math
        deltat = 1
        cond1 = (b > 0)
        if cond1:
            kappa = -math.log(b) / deltat
        else:
            kappa = np.nan
        mu = a / (1 - b)
        cond2 = (kappa / (1 - b ** 2)) > 0
        if cond2:
            sigma = math.sqrt(2 * kappa / (1 - b ** 2)) * ar_std
        else:
            sigma = np.nan
        if cond1:
            cond3 = kappa > 0
            if cond2:
                cond4 = sigma > 0
        if (cond1) & (cond2):
            if (cond3) & (cond4):
                ratio = (resids.dropna().cumsum()[-1] - mu) / (sigma * math.sqrt(2 * kappa))
            else:
                ratio = np.nan
        else:
            ratio = np.nan
        if (cond1) & (cond2):
            if (cond3) & (cond4):
                print('computed')
            else:
                print('not computed')
        else:
            print('not computed')
    else:
        ratio = np.nan
        print('not computed')
    return ratio


def ar_x(pair_data, datetime_ranges, _intercept, _wavelet):
    arx_list = []
    for date_range in datetime_ranges:
        range_data = pair_data[date_range[0]:date_range[1]]
        residuals = residual.get_resid(range_data)
        arx_value = auto_req(residuals)
        arx_list.append(arx_value)

    res = pd.Series(arx_list, index=pd.DataFrame(datetime_ranges)[0].values)
    return res


def run(pair_name):
    pair_bid, pair_ask, pair_mid = aux.create_bid_ask_mid(pair_name, data)
    pair_bid, pair_ask, pair_mid = aux.convert_bid_ask_mid(pair_bid, pair_ask, pair_mid, mid_freq, ln)
    date_ranges = get_date_ranges(pair_mid.index, 3)
    arx_values = ar_x(pair_mid, date_ranges, intercept, wavelet)
    return arx_values


def parallel_run(data, core):
    pair_names = list(combinations(data.symbol.unique(), 2))
    pool = multiprocessing.Pool(processes=core)
    ratioOUpartial = partial(ratioOU, data=data)
    pair_names_sel = pair_names
    result = pool.map(ratioOUpartial, pair_names_sel)
    return pd.DataFrame(result, index=pair_names_sel)


ratioOUmodelallpairs = ratioOU_allpairs(data, 8)
ratioOUmodelallpairs.to_csv('ratios.csv')

selectedpairs = ratioOUmodelallpairs.dropna().sort_values().tail(50).index
