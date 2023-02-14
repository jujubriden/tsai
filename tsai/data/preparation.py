# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/004_data.preparation.ipynb.

# %% ../../nbs/004_data.preparation.ipynb 3
from __future__ import annotations
from numpy.lib.stride_tricks import sliding_window_view
from ..imports import *
from ..utils import *
warnings.simplefilter(action='ignore', category=FutureWarning)

# %% auto 0
__all__ = ['df2xy', 'split_xy', 'SlidingWindowSplitter', 'SlidingWindowPanelSplitter', 'prepare_idxs',
           'prepare_sel_vars_and_steps', 'apply_sliding_window', 'df2Xy', 'split_Xy', 'df2np3d',
           'add_missing_value_cols', 'add_missing_timestamps', 'time_encoding', 'forward_gaps', 'backward_gaps',
           'nearest_gaps', 'get_gaps', 'add_delta_timestamp_cols', 'SlidingWindow', 'SlidingWindowPanel',
           'identify_padding', 'basic_data_preparation_fn', 'check_safe_conversion', 'prepare_forecasting_data']

# %% ../../nbs/004_data.preparation.ipynb 4
def prepare_idxs(o, shape=None):
    if o is None:
        return slice(None)
    elif is_slice(o) or isinstance(o, Integral):
        return o
    else:
        if shape is not None:
            return np.array(o).reshape(shape)
        else:
            return np.array(o)
        
def prepare_sel_vars_and_steps(sel_vars=None, sel_steps=None, idxs=False):
    sel_vars = prepare_idxs(sel_vars)
    sel_steps = prepare_idxs(sel_steps)
    if not is_slice(sel_vars) and not isinstance(sel_vars, Integral):
        if is_slice(sel_steps) or isinstance(sel_steps, Integral):
            _sel_vars = [sel_vars, sel_vars.reshape(1, -1)]
        else:
            _sel_vars = [sel_vars.reshape(-1, 1), sel_vars.reshape(1, -1, 1)]
    else:
        _sel_vars = [sel_vars] * 2
    if not is_slice(sel_steps) and not isinstance(sel_steps, Integral):
        if is_slice(sel_vars) or isinstance(sel_vars, Integral):
            _sel_steps = [sel_steps, sel_steps.reshape(1, -1)]
        else:
            _sel_steps = [sel_steps.reshape(1, -1), sel_steps.reshape(1, 1, -1)]
    else:
        _sel_steps = [sel_steps] * 2
    if idxs:
        n_dim = np.sum([isinstance(o, np.ndarray) for o in [sel_vars, sel_steps]])
        idx_shape = (-1,) + (1,) * n_dim
        return _sel_vars, _sel_steps, idx_shape
    else:
        return _sel_vars[0], _sel_steps[0]
    
def apply_sliding_window(
    data, # and array-like object with the input data 
    window_len:int|list, # sliding window length. When using a list, use negative numbers and 0.
    horizon:int|list=0, # horizon
    x_vars:int|list=None, # indices of the independent variables
    y_vars:int|list=None, # indices of the dependent variables (target). [] means no y will be created. None means all variables.
    ):
    "Applies a sliding window on an array-like input to generate a 3d X (and optionally y)"
  
    if isinstance(data, pd.DataFrame): data = data.to_numpy()
    if isinstance(window_len, list):
        assert np.max(window_len) == 0
        x_steps = abs(np.min(window_len)) + np.array(window_len)
        window_len = abs(np.min(window_len)) + 1
    else:
        x_steps = None
        
    X_data_windowed = sliding_window_view(data, window_len, axis=0)

    # X
    sel_x_vars, sel_x_steps = prepare_sel_vars_and_steps(x_vars, x_steps)
    if horizon == 0:
        X = X_data_windowed[:, sel_x_vars, sel_x_steps]
    else:
        X = X_data_windowed[:-np.max(horizon):, sel_x_vars, sel_x_steps]
    if x_vars is not None and isinstance(x_vars, Integral):
        X = X[:, None] # keep 3 dim

    # y
    if y_vars == []:
        y = None
    else:
        if isinstance(horizon, Integral) and horizon == 0:
            y = data[-len(X):, y_vars]
        else:
            y_data_windowed = sliding_window_view(data, np.max(horizon) + 1, axis=0)[-len(X):]
            y_vars, y_steps = prepare_sel_vars_and_steps(y_vars, horizon)
            y = np.squeeze(y_data_windowed[:, y_vars, y_steps])
    return X, y

# %% ../../nbs/004_data.preparation.ipynb 10
def df2Xy(df, sample_col=None, feat_col=None, data_cols=None, target_col=None, steps_in_rows=False, to3d=True, splits=None,
          sort_by=None, ascending=True, y_func=None, return_names=False):
    r"""
    This function allows you to transform a pandas dataframe into X and y numpy arrays that can be used to create a TSDataset.
    sample_col: column that uniquely identifies each sample.
    feat_col: used for multivariate datasets. It indicates which is the column that indicates the feature by row.
    data_col: indicates ths column/s where the data is located. If None, it means all columns (except the sample_col, feat_col, and target_col)
    target_col: indicates the column/s where the target is.
    steps_in_rows: flag to indicate if each step is in a different row or in a different column (default).
    to3d: turns X to 3d (including univariate time series)
    sort_by: this is used to pass any colum/s that are needed to sort the steps in the sequence. 
             If you pass a sample_col and/ or feat_col these will be automatically used before the sort_by column/s, and 
             you don't need to add them to the sort_by column/s list. 
    y_func: function used to calculate y for each sample (and target_col)
    return_names: flag to return the names of the columns from where X was generated
    """
    if feat_col is not None:
        assert sample_col is not None, 'You must pass a sample_col when you pass a feat_col'

    passed_cols = []
    sort_cols = []
    if sample_col is not None:
        if isinstance(sample_col, pd.core.indexes.base.Index): sample_col = sample_col.tolist()
        sample_col = listify(sample_col)
        if sample_col[0] not in sort_cols: sort_cols += listify(sample_col)
        passed_cols += sample_col
    if feat_col is not None:
        if isinstance(feat_col, pd.core.indexes.base.Index): feat_col = feat_col.tolist()
        feat_col = listify(feat_col)
        if feat_col[0] not in sort_cols: sort_cols += listify(feat_col)
        passed_cols += feat_col
    if sort_by is not None:
        if isinstance(sort_by, pd.core.indexes.base.Index): sort_by = sort_by.tolist()
        sort_cols += listify(sort_by)
    if data_cols is not None:
        if isinstance(data_cols, pd.core.indexes.base.Index): data_cols = data_cols.tolist()
        data_cols = listify(data_cols)
    if target_col is not None:
        if isinstance(target_col, pd.core.indexes.base.Index): target_col = target_col.tolist()
        target_col = listify(target_col)
        passed_cols += target_col
    if data_cols is None:
        data_cols = [col for col in df.columns if col not in passed_cols]
    if target_col is not None: 
        if any([t for t in target_col if t in data_cols]): print(f"Are you sure you want to include {target_col} in X?")
    if sort_cols:
        df.sort_values(sort_cols, ascending=ascending, inplace=True)

    # X
    X = df.loc[:, data_cols].values
    if X.dtype == 'O':
        X = X.astype(np.float32)
    if sample_col is not None:
        unique_ids = df[sample_col[0]].unique().tolist()
        n_samples = len(unique_ids)
    else:
        unique_ids = np.arange(len(df)).tolist()
        n_samples = len(df)
    if to3d:
        if feat_col is not None:
            n_feats = df[feat_col[0]].nunique()
            X = X.reshape(n_samples, n_feats, -1)
        elif steps_in_rows:
            X = X.reshape(n_samples, -1, len(data_cols)).swapaxes(1,2)
        else:
            X = X.reshape(n_samples, 1, -1)

    # y
    if target_col is not None:
        if sample_col is not None:
            y = []
            for tc in target_col:
                _y = np.concatenate(df.groupby(sample_col)[tc].apply(np.array).reset_index()[tc]).reshape(n_samples, -1)
                if y_func is not None: _y = y_func(_y)
                y.append(_y)
            y = np.concatenate(y, -1)
        else:
            y = df[target_col].values
        y = np.squeeze(y)
    else:
        y = None

    # Output
    if splits is None: 
        if return_names: return X, y, data_cols
        else: return X, y
    else: 
        if return_names: return split_xy(X, y, splits), data_cols
        return split_xy(X, y, splits)

# %% ../../nbs/004_data.preparation.ipynb 11
def split_Xy(X, y=None, splits=None):
    if splits is None: 
        if y is not None: return X, y
        else: return X
    if not is_listy(splits[0]): splits = [splits]
    else: assert not is_listy(splits[0][0]), 'You must pass a single set of splits.'
    _X = []
    _y = []
    for split in splits:
        _X.append(X[split])
        if y is not None: _y.append(y[split])
    if len(splits) == 1: return _X[0], _y[0]
    elif len(splits) == 2: return _X[0], _y[0], _X[1], _y[1]
    elif len(splits) == 3: return _X[0], _y[0], _X[1], _y[1], _X[2], _y[2]
    
df2xy = df2Xy
split_xy = split_Xy

# %% ../../nbs/004_data.preparation.ipynb 24
def df2np3d(df, groupby, data_cols=None):
    """Transforms a df (with the same number of rows per group in groupby) to a 3d ndarray"""
    if data_cols is None: data_cols = df.columns
    return np.stack([x[data_cols].values for _, x in df.groupby(groupby)]).transpose(0, 2, 1)

# %% ../../nbs/004_data.preparation.ipynb 26
def add_missing_value_cols(df, cols=None, dtype=float, fill_value=None):
    if cols is None: cols = df.columns
    elif not is_listy(cols): cols = [cols]
    for col in cols:
        df[f'missing_{col}'] = df[col].isnull().astype(dtype)
        if fill_value is not None:
            df[col].fillna(fill_value)
    return df

# %% ../../nbs/004_data.preparation.ipynb 28
def add_missing_timestamps(df, datetime_col, groupby=None, fill_value=np.nan, range_by_group=True, freq=None):
    """Fills missing timestamps in a dataframe to a desired frequency
    Args:
        df:                      pandas DataFrame
        datetime_col:            column that contains the datetime data (without duplicates within groups)
        groupby:                 column used to identify unique_ids
        fill_value:              values that will be insert where missing dates exist. Default:np.nan
        range_by_group:          if True, dates will be filled between min and max dates for each group. Otherwise, between the min and max dates in the df.
        freq:                    frequence used to fillin the missing datetime
    """
    if is_listy(datetime_col): 
        assert len(datetime_col) == 1, 'you can only pass a single datetime_col'
        datetime_col = datetime_col[0]
    dates = pd.date_range(df[datetime_col].min(), df[datetime_col].max(), freq=freq)
    if groupby is not None:
        if is_listy(groupby): 
            assert len(groupby) == 1, 'you can only pass a single groupby'
            groupby = groupby[0]
        keys = df[groupby].unique()
        if range_by_group:
            # Fills missing dates between min and max for each unique id
            min_dates = df.groupby(groupby)[datetime_col].min()
            max_dates = df.groupby(groupby)[datetime_col].max()
            idx_tuples = flatten_list([[(d, key) for d in pd.date_range(min_date, max_date, freq=freq)] for min_date, max_date, key in \
                                       zip(min_dates, max_dates, keys)])
            multi_idx = pd.MultiIndex.from_tuples(idx_tuples, names=[datetime_col, groupby])
            df = df.set_index([datetime_col, groupby]).reindex(multi_idx, fill_value=np.nan).reset_index()
        else:
            # Fills missing dates between min and max - same for all unique ids
            multi_idx = pd.MultiIndex.from_product((dates, keys), names=[datetime_col, groupby])
            df = df.set_index([datetime_col, groupby]).reindex(multi_idx, fill_value=np.nan)
            df = df.reset_index().sort_values(by=[groupby, datetime_col]).reset_index(drop=True)
    else: 
        index = pd.Index(dates, name=datetime_col)
        df = df.set_index([datetime_col]).reindex(index, fill_value=fill_value)
        df = df.reset_index().reset_index(drop=True)
    return df

# %% ../../nbs/004_data.preparation.ipynb 42
def time_encoding(series, freq, max_val=None):
    """Transforms a pandas series of dtype datetime64 (of any freq) or DatetimeIndex into 2 float arrays
    
    Available options: microsecond, millisecond, second, minute, hour, day = day_of_month = dayofmonth, 
    day_of_week = weekday = dayofweek, day_of_year = dayofyear, week = week_of_year = weekofyear, month and year
    """

    if freq == 'day_of_week' or freq == 'weekday': freq = 'dayofweek'
    elif freq == 'day_of_month' or freq == 'dayofmonth': freq = 'day'
    elif freq == 'day_of_year': freq = 'dayofyear'
    available_freqs = ['microsecond', 'millisecond', 'second', 'minute', 'hour', 'day', 'dayofweek', 'dayofyear', 'week', 'month', 'year']
    assert freq in available_freqs
    if max_val is None:
        idx = available_freqs.index(freq)
        max_val = [1_000_000, 1_000, 60, 60, 24, 31, 7, 366, 53, 12, 10][idx]
    try:
        series = series.to_series()
    except:
        pass
    if freq == 'microsecond': series = series.dt.microsecond
    elif freq == 'millisecond': series = series.dt.microsecond // 1_000
    elif freq == 'second': series = series.dt.second
    elif freq == 'minute': series = series.dt.minute
    elif freq == 'hour': series = series.dt.hour
    elif freq == 'day': series = series.dt.day
    elif freq == 'dayofweek': series = series.dt.dayofweek
    elif freq == 'dayofyear': series = series.dt.dayofyear
    elif freq == 'week': series = series.dt.isocalendar().week
    elif freq == 'month': series = series.dt.month
    elif freq == 'year': series = series.dt.year - series.dt.year // 10 * 10
    sin = np.sin(series.values / max_val * 2 * np.pi)
    cos = np.cos(series.values / max_val * 2 * np.pi)
    return sin, cos

# %% ../../nbs/004_data.preparation.ipynb 46
def forward_gaps(o, normalize=True):
    """Number of sequence steps since previous real value along the last dimension of 3D arrays or tensors"""

    b,c,s=o.shape
    if isinstance(o, torch.Tensor):
        o = torch.cat([torch.zeros(*o.shape[:2], 1, device=o.device), o], -1)
        idx = torch.where(o==o, torch.arange(s + 1, device=o.device), 0)
        idx = torch.cummax(idx, axis=-1).values
        gaps = (torch.arange(1, s + 2, device=o.device) - idx)[..., :-1]
    elif isinstance(o, np.ndarray):
        o = np.concatenate([np.zeros((*o.shape[:2], 1)), o], -1)
        idx = np.where(o==o, np.arange(s + 1), 0)
        idx = np.maximum.accumulate(idx, axis=-1)
        gaps = (np.arange(1, s + 2) - idx)[..., :-1]
    if normalize:
        gaps = gaps / s
    return gaps


def backward_gaps(o, normalize=True):
    """Number of sequence steps to next real value along the last dimension of 3D arrays or tensors"""

    if isinstance(o, torch.Tensor): o = torch_flip(o, -1)
    elif isinstance(o, np.ndarray): o = o[..., ::-1]
    gaps = forward_gaps(o, normalize=normalize)
    if isinstance(o, torch.Tensor): gaps = torch_flip(gaps, -1)
    elif isinstance(o, np.ndarray): gaps = gaps[..., ::-1]
    return gaps


def nearest_gaps(o, normalize=True):
    """Number of sequence steps to nearest real value along the last dimension of 3D arrays or tensors"""

    forward = forward_gaps(o, normalize=normalize)
    backward = backward_gaps(o, normalize=normalize)
    if isinstance(o, torch.Tensor):
        return torch.fmin(forward, backward)
    elif isinstance(o, np.ndarray):
        return np.fmin(forward, backward)


def get_gaps(o : torch.Tensor, forward : bool = True, backward : bool = True, 
             nearest : bool = True, normalize : bool = True):
    """Number of sequence steps from previous, to next and/or to nearest real value along the 
    last dimension of 3D arrays or tensors"""
    
    _gaps = []
    if forward or nearest:  
        fwd = forward_gaps(o, normalize=normalize)
        if forward: 
            _gaps.append(fwd)
    if backward or nearest: 
        bwd = backward_gaps(o, normalize=normalize)
        if backward: 
            _gaps.append(bwd)
    if nearest:
        if isinstance(o, torch.Tensor): 
            nst = torch.fmin(fwd, bwd)
        elif isinstance(o, np.ndarray): 
            nst = np.fmin(fwd, bwd)
        _gaps.append(nst)
    if isinstance(o, torch.Tensor): 
        gaps = torch.cat(_gaps, 1)
    elif isinstance(o, np.ndarray):
        gaps = np.concatenate(_gaps, 1)
    return gaps

# %% ../../nbs/004_data.preparation.ipynb 48
def add_delta_timestamp_cols(df, cols=None, groupby=None, forward=True, backward=True, nearest=True, normalize=True):
    if cols is None: cols = df.columns
    elif not is_listy(cols): cols = [cols]
    if forward or nearest:
        if groupby:
            forward_time_gaps = df[cols].groupby(df[groupby]).apply(lambda x: forward_gaps(x.values.transpose(1,0)[None], normalize=normalize))
            forward_time_gaps = np.concatenate(forward_time_gaps, -1)[0].transpose(1,0)
        else:
            forward_time_gaps = forward_gaps(df[cols].values.transpose(1,0)[None], normalize=normalize)[0].transpose(1,0)
        if forward : 
            df[[f'{col}_dt_fwd' for col in cols]] = forward_time_gaps
            df[[f'{col}_dt_fwd' for col in cols]] = df[[f'{col}_dt_fwd' for col in cols]]
    if backward or nearest:
        if groupby:
            backward_time_gaps = df[cols].groupby(df[groupby]).apply(lambda x: backward_gaps(x.values.transpose(1,0)[None], normalize=normalize))
            backward_time_gaps = np.concatenate(backward_time_gaps, -1)[0].transpose(1,0)
        else:
            backward_time_gaps = backward_gaps(df[cols].values.transpose(1,0)[None], normalize=normalize)[0].transpose(1,0)
        if backward: 
            df[[f'{col}_dt_bwd' for col in cols]] = backward_time_gaps
            df[[f'{col}_dt_bwd' for col in cols]] = df[[f'{col}_dt_bwd' for col in cols]]
    if nearest:
        df[[f'{col}_dt_nearest' for col in cols]] = np.fmin(forward_time_gaps, backward_time_gaps)
        df[[f'{col}_dt_nearest' for col in cols]] = df[[f'{col}_dt_nearest' for col in cols]]
    return df

# %% ../../nbs/004_data.preparation.ipynb 54
# # SlidingWindow vectorization is based on "Fast and Robust Sliding Window Vectorization with NumPy" by Syafiq Kamarul Azman
# # https://towardsdatascience.com/fast-and-robust-sliding-window-vectorization-with-numpy-3ad950ed62f5

def SlidingWindow(
  window_len:int, #length of lookback window
  stride:Union[None, int]=1, # n datapoints the window is moved ahead along the sequence. Default: 1. If None, stride=window_len (no overlap)
  start:int=0, # determines the step where the first window is applied: 0 (default) or a given step (int). Previous steps will be discarded.
  pad_remainder:bool=False, #allows to pad remainder subsequences when the sliding window is applied and get_y == [] (unlabeled data).
  padding:str="post", #'pre' or 'post' (optional, defaults to 'pre'): pad either before or after each sequence. If pad_remainder == False, it indicates the starting point to create the sequence ('pre' from the end, and 'post' from the beginning)
  padding_value:float=np.nan, #value (float) that will be used for padding. Default: np.nan       
  add_padding_feature:bool=True, #add an additional feature indicating whether each timestep is padded (1) or not (0).
  get_x:Union[None, int, list]=None, # indices of columns that contain the independent variable (xs). If None, all data will be used as x.
  get_y:Union[None, int, list]=None, # indices of columns that contain the target (ys). If None, all data will be used as y. [] means no y data is created (unlabeled data).
  y_func:Optional[callable]=None, # optional function to calculate the ys based on the get_y col/s and each y sub-window. y_func must be a function applied to axis=1!
  output_processor:Optional[callable]=None, # optional function to process the final output (X (and y if available)). This is useful when some values need to be removed.The function should take X and y (even if it's None) as arguments.
  copy:bool=False, # copy the original object to avoid changes in it.
  horizon:Union[int, list]=1, #number of future datapoints to predict (y). If get_y is [] horizon will be set to 0.
                            # * 0 for last step in each sub-window.
                            # * n > 0 for a range of n future steps (1 to n).
                            # * n < 0 for a range of n past steps (-n + 1 to 0).
                            # * list : for those exact timesteps.
  seq_first:bool=True, # True if input shape (seq_len, n_vars), False if input shape (n_vars, seq_len)
  sort_by:Optional[list]=None, # column/s used for sorting the array in ascending order
  ascending:bool=True, # used in sorting
  check_leakage:bool=True, # checks if there's leakage in the output between X and y
):

    """
    Applies a sliding window to a 1d or 2d input (np.ndarray, torch.Tensor or pd.DataFrame)
    \nInput:\n
        You can use np.ndarray, pd.DataFrame or torch.Tensor as input\n
        shape: (seq_len, ) or (seq_len, n_vars) if seq_first=True else (n_vars, seq_len)
    """

    if get_y == []: horizon = 0
    if horizon == 0: horizon_rng = np.array([0])
    elif is_listy(horizon): horizon_rng = np.array(horizon)
    elif isinstance(horizon, Integral): horizon_rng = np.arange(1, horizon + 1) if horizon > 0 else np.arange(horizon + 1, 1)
    min_horizon = min(horizon_rng)
    max_horizon = max(horizon_rng)
    _get_x = slice(None) if get_x is None else get_x.tolist() if isinstance(get_x, pd.core.indexes.base.Index) else [get_x] if not is_listy(get_x) else get_x
    _get_y = slice(None) if get_y is None else get_y.tolist() if isinstance(get_y, pd.core.indexes.base.Index) else [get_y] if not is_listy(get_y) else get_y
    if min_horizon <= 0 and y_func is None and get_y != [] and check_leakage:
        assert get_x is not None and  get_y is not None and len([y for y in _get_y if y in _get_x]) == 0,  \
        'you need to change either horizon, get_x, get_y or use a y_func to avoid leakage'
    if stride == 0 or stride is None:
        stride = window_len
    if pad_remainder: assert padding in ["pre", "post"]

    def _inner(o):
        if copy:
            if isinstance(o, torch.Tensor):  o = o.clone()
            else: o = o.copy()
        if not seq_first: o = o.T
        if isinstance(o, pd.DataFrame):
            if sort_by is not None: o.sort_values(by=sort_by, axis=0, ascending=ascending, inplace=True, ignore_index=True)
            if get_x is None: X = o.values
            elif isinstance(_get_x, str) or (is_listy(_get_x) and isinstance(_get_x[0], str)): X = o.loc[:, _get_x].values
            else: X = o.iloc[:, _get_x].values
            if get_y == []: y = None
            elif get_y is None: y = o.values
            elif isinstance(_get_y, str) or (is_listy(_get_y) and isinstance(_get_y[0], str)): y = o.loc[:, _get_y].values
            else: y = o.iloc[:, _get_y].values
        else:
            if isinstance(o, torch.Tensor): o = o.numpy()
            if o.ndim < 2: o = o[:, None]
            if get_x is None: X = o
            else: X = o[:, _get_x]
            if get_y == []: y = None
            elif get_y is None: y = o
            else: y = o[:, _get_y]

        # X
        if start != 0:
            X = X[start:]
        X_len = len(X)
        if not pad_remainder:
            if X_len < window_len + max_horizon:
                return None, None
            else:
                n_windows = 1 + (X_len - max_horizon - window_len) // stride
        else:
            n_windows = 1 + max(0, np.ceil((X_len - max_horizon - window_len) / stride).astype(int))
        
        X_max_len = window_len + max_horizon + (n_windows - 1) * stride # total length required (including y)
        X_seq_len = X_max_len - max_horizon

        if pad_remainder and X_len < X_max_len:
            if add_padding_feature:
                X = np.concatenate([X, np.zeros((X.shape[0], 1))], axis=1)
            _X = np.empty((X_max_len - X_len, *X.shape[1:]))
            _X[:] = padding_value
            if add_padding_feature:
                _X[:, -1] = 1
            if padding == "pre":
                X = np.concatenate((_X, X))
            elif padding == "post":
                X = np.concatenate((X, _X))
        if X_max_len != X_seq_len:
            if padding == "pre":
                X_start = X_len - X_max_len
                X = X[-X_max_len:-X_max_len + X_seq_len]
            elif padding == "post":
                X_start = 0
                X = X[:X_seq_len]
        else: 
            X_start = 0
        
        X_sub_windows = (np.expand_dims(np.arange(window_len), 0) +
                         np.expand_dims(np.arange(n_windows * stride, step=stride), 0).T)
        X = np.transpose(X[X_sub_windows], (0, 2, 1))

        # y
        if get_y != [] and y is not None:
            y_start = start + X_start + window_len + min_horizon - 1
            y_max_len = max_horizon - min_horizon + 1 + (n_windows - 1) * stride
            y = y[y_start:y_start + y_max_len]
            y_len = len(y)
            y_seq_len = y_max_len

            if pad_remainder and y_len < y_max_len:
                _y = np.empty((y_max_len - y_len, *y.shape[1:]))
                _y[:] = padding_value
                if padding == "pre":
                    y = np.concatenate((_y, y))
                elif padding == "post":
                    y = np.concatenate((y, _y))

            y_sub_windows = (np.expand_dims(horizon_rng - min_horizon, 0)+
                             np.expand_dims(np.arange(n_windows * stride, step=stride), 0).T)
            y = y[y_sub_windows]

            if y_func is not None and len(y) > 0:
                y = y_func(y)
            if y.ndim >= 2:
                for d in np.arange(1, y.ndim)[::-1]:
                    if y.shape[d] == 1: y = np.squeeze(y, axis=d)
            if y.ndim == 3:
                y = y.transpose(0, 2, 1)
        if output_processor is not None:
            X, y = output_processor(X, y)
        return X, y
    return _inner

SlidingWindowSplitter = SlidingWindow

# %% ../../nbs/004_data.preparation.ipynb 90
def SlidingWindowPanel(window_len:int, unique_id_cols:list, stride:Union[None, int]=1, start:int=0,
                       pad_remainder:bool=False, padding:str="post", padding_value:float=np.nan, add_padding_feature:bool=True,
                       get_x:Union[None, int, list]=None,  get_y:Union[None, int, list]=None, y_func:Optional[callable]=None,
                       output_processor:Optional[callable]=None, copy:bool=False, horizon:Union[int, list]=1, seq_first:bool=True, sort_by:Optional[list]=None,
                       ascending:bool=True, check_leakage:bool=True, return_key:bool=False, verbose:bool=True):

    """
    Applies a sliding window to a pd.DataFrame.

    Args:
        window_len          = length of lookback window
        unique_id_cols      = pd.DataFrame columns that will be used to identify a time series for each entity.
        stride              = n datapoints the window is moved ahead along the sequence. Default: 1. If None, stride=window_len (no overlap)
        start               = determines the step where the first window is applied: 0 (default), a given step (int), or random within the 1st stride (None).
        pad_remainder       = allows to pad remainder subsequences when the sliding window is applied and get_y == [] (unlabeled data).
        padding             = 'pre' or 'post' (optional, defaults to 'pre'): pad either before or after each sequence. If pad_remainder == False, it indicates
                              the starting point to create the sequence ('pre' from the end, and 'post' from the beginning)
        padding_value       = value (float) that will be used for padding. Default: np.nan
        add_padding_feature = add an additional feature indicating whether each timestep is padded (1) or not (0).
        horizon             = number of future datapoints to predict (y). If get_y is [] horizon will be set to 0.
                            * 0 for last step in each sub-window.
                            * n > 0 for a range of n future steps (1 to n).
                            * n < 0 for a range of n past steps (-n + 1 to 0).
                            * list : for those exact timesteps.
        get_x               = indices of columns that contain the independent variable (xs). If None, all data will be used as x.
        get_y               = indices of columns that contain the target (ys). If None, all data will be used as y.
                              [] means no y data is created (unlabeled data).
        y_func              = function to calculate the ys based on the get_y col/s and each y sub-window. y_func must be a function applied to axis=1!
        output_processor    = optional function to filter output (X (and y if available)). This is useful when some values need to be removed. The function
                              should take X and y (even if it's None) as arguments.
        copy                = copy the original object to avoid changes in it.
        seq_first           = True if input shape (seq_len, n_vars), False if input shape (n_vars, seq_len)
        sort_by             = column/s used for sorting the array in ascending order
        ascending           = used in sorting
        check_leakage       = checks if there's leakage in the output between X and y
        return_key          = when True, the key corresponsing to unique_id_cols for each sample is returned
        verbose             = controls verbosity. True or 1 displays progress bar. 2 or more show records that cannot be created due to its length.


    Input:
        You can use np.ndarray, pd.DataFrame or torch.Tensor as input
        shape: (seq_len, ) or (seq_len, n_vars) if seq_first=True else (n_vars, seq_len)
    """
    global unique_id_values

    if not is_listy(unique_id_cols): unique_id_cols = [unique_id_cols]
    if sort_by is not None:
        if not is_listy(sort_by): sort_by = [sort_by]
        sort_by = [sb for sb in sort_by if sb not in unique_id_cols]
    sort_by = unique_id_cols + (sort_by if sort_by is not None else [])

    def _SlidingWindowPanel(o):

        if copy:
            o = o.copy()
        o.sort_values(by=sort_by, axis=0, ascending=ascending, inplace=True, ignore_index=True, kind="mergesort")
        unique_id_values = o[unique_id_cols].drop_duplicates().values
        _x = []
        _y = []
        _key = []
        if verbose: print('processing data...')
        for v in progress_bar(unique_id_values, display=verbose, leave=False):
            x_v, y_v = SlidingWindow(window_len, stride=stride, start=start, pad_remainder=pad_remainder, padding=padding, padding_value=padding_value,
                                     add_padding_feature=add_padding_feature, get_x=get_x, get_y=get_y, y_func=y_func, output_processor=output_processor,
                                     copy=False, horizon=horizon, seq_first=seq_first,
                                     check_leakage=check_leakage)(o[(o[unique_id_cols].values == v).sum(axis=1) == len(v)])
            if x_v is not None and len(x_v) > 0:
                _x.append(x_v)
                if return_key: _key.append([v.tolist()] * len(x_v))
                if y_v is not None and len(y_v) > 0: _y.append(y_v)
            elif verbose>=2:
                print(f'cannot use {unique_id_cols} = {v} due to not having enough records')

        if verbose: 
            print('...data processed')
            print('concatenating X...')
        X = np.concatenate(_x)
        print('...X concatenated')
        if _y != []:
            print('concatenating y...')
            y = np.concatenate(_y)
            print('...y concatenated')
            for d in np.arange(1, y.ndim)[::-1]:
                if y.shape[d] == 1: y = np.squeeze(y, axis=d)
        else: y = None
        if return_key:
            key = np.concatenate(_key)
            if key.ndim == 2 and key.shape[-1] == 1: key = np.squeeze(key, -1)
            if return_key: return X, y, key
        else: return X, y

    return _SlidingWindowPanel


SlidingWindowPanelSplitter = SlidingWindowPanel

# %% ../../nbs/004_data.preparation.ipynb 97
def identify_padding(float_mask, value=-1):
    """Identifies padded subsequences in a mask of type float
    
    This function identifies as padded subsequences those where all values == nan 
    from the end of the sequence (last dimension) across all channels, and sets
    those values to the selected value (default = -1)
    
    Args:
        mask: boolean or float mask
        value: scalar that will be used to identify padded subsequences 
    """
    padding = torch.argmax((torch.flip(float_mask.mean((1)) - 1, (-1,)) != 0).float(), -1)
    padded_idxs = torch.arange(len(float_mask))[padding != 0]
    if len(padded_idxs) > 0:
        padding = padding[padding != 0]
        for idx,pad in zip(padded_idxs, padding): float_mask[idx, :, -pad:] = value
    return float_mask

# %% ../../nbs/004_data.preparation.ipynb 100
def basic_data_preparation_fn(
    df, # dataframe to preprocess
    drop_duplicates=True, # flag to indicate if rows with duplicate datetime info should be removed
    datetime_col=None, # str indicating the name of the column/s that contains the datetime info
    use_index=False, # flag to indicate if the datetime info is in the index
    keep='last', # str to indicate what data should be kept in case of duplicate rows
    add_missing_datetimes=True, # flaf to indicate if missing datetimes should be added
    freq='1D', # str to indicate the frequency used in the datetime info. Used in case missing timestamps exists
    method=None, # str indicating the method used to fill data for missing timestamps: None, 'bfill', 'ffill'
    sort_by=None, # str or list of str to indicate if how to sort data. If use_index=True the index will be used to sort the dataframe.
    ):

    cols = df.columns
    if drop_duplicates:
        assert datetime_col is not None or use_index, "you need to either pass a datetime_col or set use_index=True"
        # Remove duplicates (if any)
        if use_index:
            dup_rows = df.index.duplicated(keep=keep)
        else:
            dup_rows = df[datetime_col].duplicated(keep=keep)
        if dup_rows.sum():
            df = df[~dup_rows].copy()
    
    if use_index:
        df.sort_index(inplace=True)
    if sort_by is not None:
        df.sort_values(sort_by, inplace=True)
        
    if add_missing_datetimes:
        if not use_index:
            # We'll set the timestamp column as index
            df.set_index(datetime_col, drop=True, inplace=True)
        # Add missing timestamps (if any) between start and end datetimes and forward-fill data
        df = df.asfreq(freq=freq, method=method)
        if not use_index:
            df.reset_index(drop=False, inplace=True)
    
    return df[cols]

# %% ../../nbs/004_data.preparation.ipynb 102
def check_safe_conversion(o, dtype='float32', cols=None):
    "Checks if the conversion to float is safe"
    
    def _check_safe_conversion(o, dtype='float32'):

        if isinstance(o, (Integral, float)):
            o_min = o_max = o
        elif isinstance(o, pd.Series):
            o_min = o.min()
            o_max = o.max()
        else:
            o_min = np.asarray(o).min()
            o_max = np.asarray(o).max()
        
        dtype = np.dtype(dtype)
        if dtype == 'float16':
            return -2**11 <= o_min and o_max <= 2**11
        elif dtype == 'float32':
            return -2**24 <= o_min and o_max <= 2**24
        elif dtype == 'float64':
            return -2**53 <= o_min and o_max <= 2**53
        elif dtype == 'int8':
            return np.iinfo(np.int8).min <= o_min and o_max <= np.iinfo(np.int8).max
        elif dtype == 'int16':
            return np.iinfo(np.int16).min <= o_min and o_max <= np.iinfo(np.int16).max
        elif dtype == 'int32':
            print(np.iinfo(np.int32).min, o_min, o_max, np.iinfo(np.int32).max)
            return np.iinfo(np.int32).min <= o_min and o_max <= np.iinfo(np.int32).max
        elif dtype == 'int64':
            return np.iinfo(np.int64).min <= o_min and o_max <= np.iinfo(np.int64).max
        else:
            raise ValueError("Unsupported data type")
    
    if isinstance(o, pd.DataFrame):
        cols = o.columns if cols is None else cols
        checks = [_check_safe_conversion(o[c], dtype=dtype) for c in cols]
        if all(checks): return True
        warnings.warn(f"Unsafe conversion to {dtype}: {dict(zip(cols, checks))}")
        return False
    else:
        return _check_safe_conversion(o, dtype=dtype)
    

# %% ../../nbs/004_data.preparation.ipynb 104
def prepare_forecasting_data(
    df:pd.DataFrame, # dataframe containing a sorted time series for a single entity or subject
    fcst_history:int, # # historical steps used as input.
    fcst_horizon:int=1, # # steps forecasted into the future. 
    x_vars:str|list=None, # features used as input
    y_vars:str|list=None,  # features used as output
    dtype:str=None, # data type
    unique_id_cols:str|list=None, # unique identifier column/s used in panel data
)->tuple(np.ndarray, np.ndarray):

    def _prepare_forecasting_data(df, x_vars, y_vars):
        x_np = df.to_numpy(dtype=dtype) if x_vars is None else df[x_vars].to_numpy(dtype=dtype)
        y_np = x_np if x_vars == y_vars else df.to_numpy(dtype=dtype) if y_vars is None else df[y_vars].to_numpy(dtype=dtype)
        X = sliding_window_view(x_np[:len(x_np) - fcst_horizon], fcst_history, axis=0)
        y = sliding_window_view(y_np[fcst_history:], fcst_horizon, axis=0)
        return X, y
    
    x_vars = None if (x_vars is None or feat2list(x_vars) == list(df.columns)) else feat2list(x_vars)
    y_vars = None if (y_vars is None or feat2list(y_vars) == list(df.columns)) else feat2list(y_vars)
    if dtype is not None:
        assert check_safe_conversion(df, dtype=dtype, cols=x_vars)
        if y_vars != x_vars:
            assert check_safe_conversion(df, dtype=dtype, cols=y_vars)
    if unique_id_cols:
        grouped = df.groupby(unique_id_cols)
        if x_vars is None and y_vars is None:
            output = grouped.apply(lambda x: _prepare_forecasting_data(x, x_vars=None, y_vars=None))
        elif x_vars == y_vars:
            output = grouped[x_vars].apply(lambda x: _prepare_forecasting_data(x, x_vars=None, y_vars=None))
        else:
            output = grouped.apply(lambda x: _prepare_forecasting_data(x, x_vars, y_vars))
        output = output.reset_index(drop=True)
        X, y = zip(*output)
        X = np.concatenate(X, 0)
        y = np.concatenate(y, 0)
    else:
        if x_vars is None and y_vars is None:
            X, y = _prepare_forecasting_data(df, x_vars=None, y_vars=None)
        elif x_vars == y_vars:
            X, y = _prepare_forecasting_data(df[x_vars], x_vars=None, y_vars=None)
        else:
            X, y = _prepare_forecasting_data(df[x_vars], x_vars=x_vars, y_vars=y_vars)
    return X, y
