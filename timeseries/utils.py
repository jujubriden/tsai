# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/000_utils.ipynb (unless otherwise specified).

__all__ = ['ToTensor', 'ToArray', 'To3DTensor', 'To2DTensor', 'To1DTensor', 'To3DArray', 'To2DArray', 'To1DArray',
           'To3D', 'To2D', 'To1D', 'To2DPlus', 'To3DPlus', 'To2DPlusTensor', 'To2DPlusArray', 'To3DPlusTensor',
           'To3DPlusArray', 'Todtype', 'bytes2size', 'bytes2GB', 'delete_all_in_dir', 'reverse_dict', 'is_tuple',
           'itemify', 'is_none', 'ifisnone', 'ifnoneelse', 'ifisnoneelse', 'ifelse', 'stack', 'cycle_dl', 'device',
           'cpus']

# Cell
# from timeseries.all import *

# Cell
from fastai2.imports import *
import torch

# Cell
def ToTensor(o):
    if isinstance(o, torch.Tensor): return o
    elif isinstance(o, np.ndarray):  return torch.from_numpy(o)
    assert False, f"Can't convert {type(o)} to torch.Tensor"


def ToArray(o):
    if isinstance(o, np.ndarray): return o
    elif isinstance(o, torch.Tensor): return o.cpu().numpy()
    assert False, f"Can't convert {type(o)} to np.array"


def To3DTensor(o):
    o = ToTensor(o)
    if o.ndim == 3: return o
    elif o.ndim == 1: return o[None, None]
    elif o.ndim == 2: return o[:, None]
    assert False, f'Please, review input dimensions {o.ndim}'


def To2DTensor(o):
    o = ToTensor(o)
    if o.ndim == 2: return o
    elif o.ndim == 1: return o[None]
    elif o.ndim == 3: return o[0]#torch.squeeze(o, 0)
    assert False, f'Please, review input dimensions {o.ndim}'


def To1DTensor(o):
    o = ToTensor(o)
    if o.ndim == 1: return o
    elif o.ndim == 3: return o[0,0]#torch.squeeze(o, 1)
    if o.ndim == 2: return o[0]#torch.squeeze(o, 0)
    assert False, f'Please, review input dimensions {o.ndim}'


def To3DArray(o):
    o = ToArray(o)
    if o.ndim == 3: return o
    elif o.ndim == 1: return o[None, None]
    elif o.ndim == 2: return o[:, None]
    assert False, f'Please, review input dimensions {o.ndim}'


def To2DArray(o):
    o = ToArray(o)
    if o.ndim == 2: return o
    elif o.ndim == 1: return o[None]
    elif o.ndim == 3: return 0[0]#np.squeeze(o, 0)
    assert False, f'Please, review input dimensions {o.ndim}'


def To1DArray(o):
    o = ToArray(o)
    if o.ndim == 1: return o
    elif o.ndim == 3: o = 0[0,0]#np.squeeze(o, 1)
    elif o.ndim == 2: o = 0[0]#np.squeeze(o, 0)
    assert False, f'Please, review input dimensions {o.ndim}'


def To3D(o):
    if o.ndim == 3: return o
    if isinstance(o, np.ndarray): return To3DArray(o)
    if isinstance(o, torch.Tensor): return To3DTensor(o)


def To2D(o):
    if o.ndim == 2: return o
    if isinstance(o, np.ndarray): return To2DArray(o)
    if isinstance(o, torch.Tensor): return To2DTensor(o)


def To1D(o):
    if o.ndim == 1: return o
    if isinstance(o, np.ndarray): return To1DArray(o)
    if isinstance(o, torch.Tensor): return To1DTensor(o)


def To2DPlus(o):
    if o.ndim >= 2: return o
    if isinstance(o, np.ndarray): return To2DArray(o)
    elif isinstance(o, torch.Tensor): return To2DTensor(o)


def To3DPlus(o):
    if o.ndim >= 3: return o
    if isinstance(o, np.ndarray): return To3DArray(o)
    elif isinstance(o, torch.Tensor): return To3DTensor(o)


def To2DPlusTensor(o):
    return To2DPlus(ToTensor(o))


def To2DPlusArray(o):
    return To2DPlus(ToArray(o))


def To3DPlusTensor(o):
    return To3DPlus(ToTensor(o))


def To3DPlusArray(o):
    return To3DPlus(ToArray(o))


def Todtype(dtype):
    def _to_type(o, dtype=dtype):
        if o.dtype == dtype: return o
        elif isinstance(o, torch.Tensor): o = o.to(dtype=dtype)
        elif isinstance(o, np.ndarray): o = o.astype(dtype)
        return o
    return _to_type

# Cell
def bytes2size(size_bytes):
    if size_bytes == 0: return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])

def bytes2GB(byts):
    return round(byts / math.pow(1024, 3), 2)

# Cell
def delete_all_in_dir(tgt_dir, exception=None):
    if exception is not None and len(L(exception)) > 1: exception = tuple(exception)
    for file in os.listdir(tgt_dir):
        if exception is not None and file.endswith(exception): continue
        file_path = os.path.join(tgt_dir, file)
        if os.path.isfile(file_path) or os.path.islink(file_path): os.unlink(file_path)
        elif os.path.isdir(file_path): shutil.rmtree(file_path)

# Cell
def reverse_dict(dictionary):
    return {v: k for k, v in dictionary.items()}

# Cell
def is_tuple(o): return isinstance(o, tuple)

# Cell
def itemify(*o, tup_id=None):
    items = L(*o).zip()
    if tup_id is not None: return L([item[tup_id] for item in items])
    else: return items

# Cell
def is_none(o):
    return o in [[], [None], None]

def ifisnone(a, b):
    "`a` if `a` is None else `b`"
    return None if is_none(a) else b

def ifnoneelse(a, b, c=None):
    "`b` if `a` is None else `c`"
    return b if a is None else ifnone(c, a)

def ifisnoneelse(a, b, c=None):
    "`b` if `a` is None else `c`"
    return b if is_none(a) else ifnone(c, a)

def ifelse(a, b, c):
    "`b` if `a` is True else `c`"
    return b if a else c

# Cell
def stack(o, axis=0):
    if isinstance(o[0], np.ndarray): return np.stack(o, axis)
    elif isinstance(o[0], torch.Tensor): return torch.stack(tuple(o), dim=axis)
    assert False, f'cannot stack this data type {type(o[0])}'

# Cell
# This is a convenience function will use later proposed by Thomas Capelle @tcapelle to be able to easily benchmark performance
def cycle_dl(dl):
    for _ in iter(dl): pass

# Cell
device = 'cuda' if torch.cuda.is_available() else 'cpu'
defaults.device = device
cpus = defaults.cpus