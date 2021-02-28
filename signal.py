import pandas as pd


def get_signal(x, thresholds=[]):
    signal_1, signal_2 = [], []

    signal1, signal2 = False, False

    prev_sign = 0

    nan_lock = 1

    idx = x.index

    for val, threshold in zip(x, thresholds):

        sign = np.sign(val)

        if abs(val) > threshold:
            nan_lock = 0
            prev_sign = sign
            if sign == 1:
                signal1 = True
                signal2 = False
            else:
                signal1 = False
                signal2 = True
        else:
            if sign == prev_sign:
                pass
            else:
                prev_sign = sign
                signal1 = False
                signal2 = False
            if nan_lock == 1:
                signal1 = np.nan
                signal2 = np.nan
        signal_1.append(signal1)
        signal_2.append(signal2)

    signal_1 = pd.Series(signal_1, index=idx, name='signal_1').replace({False: 0, True: 1})
    signal_2 = pd.Series(signal_2, index=idx, name='signal_2').replace({False: 0, True: 1})

    return signal_1.shift(), signal_2.shift()


def get_signals2(residuals, std):
    list_signal1, list_signal2 = [], []

    number_of_nans = residuals.isna().value_counts()[True]

    for i in range(number_of_nans):
        print('nan')
        list_signal1.append(np.nan)
        list_signal2.append(np.nan)

    is_prev_above_std = False
    prev_sign = np.sign(residuals[number_of_nans])

    signal1, signal2 = 0, 0

    if residuals[number_of_nans] > std[number_of_nans]:
        is_prev_above_std = True

    list_signal1.append(signal1)
    list_signal2.append(signal2)

    for _res, _std in zip(residuals[number_of_nans + 1:], std[number_of_nans + 1:]):

        current_sign = np.sign(_res)

        if current_sign == prev_sign:
            if (abs(_res) < _std) and is_prev_above_std:
                if current_sign == 1:
                    signal1 = 1
                    signal2 = 0
                else:
                    signal1 = 0
                    signal2 = 1
        else:
            signal1 = 0
            signal2 = 0
            prev_sign = current_sign

        if abs(_res) > _std:
            is_prev_above_std = True
        else:
            is_prev_above_std = False

        list_signal1.append(signal1)
        list_signal2.append(signal2)

    return pd.DataFrame({'signal1': list_signal1, 'signal2': list_signal2})


def signal_points(signal: pd.Series) -> [pd.Index, pd.Index]:
    """
    Returns the entry and exit_points points of the signal. -> (entry,exit_points)
    """
    entry_exit_points = np.trim_zeros(signal.dropna(), 'f').diff().fillna(1)
    entry_points = entry_exit_points[entry_exit_points == 1].index
    exit_points_points = entry_exit_points[entry_exit_points == -1].index
    if len(entry_points) > len(exit_points_points):
        entry_points = entry_points[0:len(exit_points_points)]
        # exit_points_points = exit_points_points.append(pd.DatetimeIndex([signal.index[-1]]))
    return entry_points, exit_points_points