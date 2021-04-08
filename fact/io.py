import warnings
from os import path
import json
import tables
import h5py
import pandas as pd
import sys
import logging
import numpy as np
from copy import copy
import astropy.units as u
import tempfile
import warnings


__all__ = [
    'write_data',
    'to_native_byteorder',
    'read_data',
    'read_h5py',
    'read_h5py_chunked',
    'check_extension',
    'to_h5py',
    'create_blosc_compression_options',
]

log = logging.getLogger(__name__)


allowed_extensions = ('.hdf', '.hdf5', '.h5', '.json', '.jsonl', '.jsonlines', '.csv')
native_byteorder = native_byteorder = {'little': '<', 'big': '>'}[sys.byteorder]


def create_blosc_compression_options(complevel=5, complib='blosc:zstd', shuffle=True):
    '''Create correct kwargs for h5py.create_dataset to use the more modern
    compression filters, default is zstandard with moderate compression settings
    See https://github.com/h5py/h5py/issues/611#issuecomment-353694301
    '''
    shuffle = 2 if shuffle == 'bit' else 1 if shuffle else 0
    compressors = tables.filters.blosc_compressor_list()
    try:
        complib = ['blosc:' + c for c in compressors].index(complib)
    except ValueError:
        raise ValueError('Unsupported compression "{}"'.format(complib))

    args = {
        'compression': 32001,
        'compression_opts': (0, 0, 0, 0, complevel, shuffle, complib)
    }
    if shuffle:
        args['shuffle'] = False
    return args


DEFAULT_COMPRESSION = {}
with tempfile.NamedTemporaryFile(suffix='.hdf5') as f:
    try:
        zstd_opts = create_blosc_compression_options()
        with h5py.File(f.name, 'w') as of:
            of.create_dataset('test', dtype='float64', shape=(1, ), **zstd_opts)

        DEFAULT_COMPRESSION.update(zstd_opts)
    except ValueError:
        warnings.warn(
            'BLOSC compression for hdf5 not available, you will not be able'
            ' to create or read blosc compressed datasets'
            ' make sure tables and h5py are linked against the same hdf5 library'
            ' e.g. by installing hdf5 in your system and doing '
            ' `pip install --no-binary=tables --no-binary=h5py tables h5py`'
            ' or using conda'
        )


def write_data(df, file_path, key='data', use_h5py=True, **kwargs):
    '''
    Write a pandas DataFrame to several output formats, determined by the
    extension of `file_path`

    Supported file types are:
        * hdf5, used when extensions are `.hdf`, `.hdf5` or `.h5`.
          By default h5py with one dataset per column is used.
          Pandas to_hdf5 is used if `use_h5py=False`
        * json, if extension is json
        * jsonlines if extension is `jsonl` or `jsonline`
        * csv, if extension is `csv`

    Arguments
    ---------

    df: pd.DataFrame
        DataFrame to save
    file_path: str
        Path to the outputfile
    key: str
        Groupkey, only used for hdf5
    use_h5py: bool
        wheither to write h5py style or pandas style hdf5

    All other key word arguments are passed to the actual writer functions.
    '''

    name, extension = path.splitext(file_path)

    if extension in ['.hdf', '.hdf5', '.h5']:
        if use_h5py is True:
            to_h5py(df, file_path, key=key, **kwargs)
        else:
            df.to_hdf(file_path, key=key, **kwargs)

    elif extension == '.json':
        df.to_json(file_path, **kwargs)

    elif extension in ('.jsonl', '.jsonline'):
        df.to_json(file_path, lines=True, orient='records', **kwargs)

    elif extension == '.csv':
        index = kwargs.pop('index', False)
        df.to_csv(file_path, index=index, **kwargs)

    else:
        raise IOError(
            'cannot write tabular data with format {}. Allowed formats: {}'.format(
                extension, allowed_extensions,
            )
        )


def to_native_byteorder(array):
    ''' Convert numpy array to native byteorder '''

    # '|' : not-applicable, '=': native
    if array.dtype.byteorder not in ('|', '=', native_byteorder):
        return array.byteswap().newbyteorder()

    return array


def read_h5py(
        file_path,
        key='data',
        columns=None,
        mode='r',
        parse_dates=True,
        first=None,
        last=None):
    '''
    Read a hdf5 file written with h5py into a dataframe

    Parameters
    ----------
    file_path: str
        file to read in
    key: str
        name of the hdf5 group to read in
    columns: iterable[str]
        Names of the datasets to read in. If not given read all 1d datasets
    parse_dates: bool
        Convert columns with attrs['timeformat'] to timestamps
    first: int or None
        first row to read from the file
    last: int or None
        last event to read from the file

    '''
    with h5py.File(file_path, mode) as f:
        group = f.get(key)
        if group is None:
            raise IOError('File does not contain group "{}"'.format(key))

        # get all columns of which don't have more than one value per row
        if columns is None:
            columns = [col for col in group.keys() if group[col].ndim == 1]
        else:
            columns = copy(columns)

        df = pd.DataFrame()
        for col in columns:
            dataset = group[col]
            array = to_native_byteorder(dataset[first:last])

            # decode unicode strings to str
            if array.dtype.kind in {'S', 'O'}:
                array = array.astype('U')

            if parse_dates and dataset.attrs.get('timeformat') is not None:
                array = pd.to_datetime(array, infer_datetime_format=True)

            if array.ndim == 1:
                df[col] = array
            elif array.ndim == 2:
                for i in range(array.shape[1]):
                    df[col + '_{}'.format(i)] = array[:, i]
            else:
                log.warning('Skipping column {}, not 1d or 2d'.format(col))

        if 'index' in df.columns:
            df.set_index('index', inplace=True)
            df.index.name = None

    return df


def h5py_get_n_rows(file_path, key='data', mode='r'):

    with h5py.File(file_path, mode) as f:
        group = f.get(key)

        if group is None:
            raise IOError('File does not contain group "{}"'.format(key))

        return group[next(iter(group.keys()))].shape[0]


def read_h5py_chunked(
        file_path,
        key='data',
        columns=None,
        chunksize=None,
        mode='r',
        parse_dates=True):
    '''
    Generator function to read from h5py hdf5 in chunks,
    returns an iterator over pandas dataframes.

    When chunksize is None, use 1 chunk
    '''
    with h5py.File(file_path, mode) as f:
        group = f.get(key)
        if group is None:
            raise IOError('File does not contain group "{}"'.format(key))

        # get all columns of which don't have more than one value per row
        if columns is None:
            columns = [col for col in group.keys() if group[col].ndim == 1]
        else:
            columns = copy(columns)

        n_rows = h5py_get_n_rows(file_path, key=key)

        if chunksize is None:
            n_chunks = 1
            chunksize = n_rows
        else:
            n_chunks = int(np.ceil(n_rows / chunksize))
            log.info('Splitting data into {} chunks'.format(n_chunks))

        for col in copy(columns):
            if group[col].ndim > 2:
                columns.remove(col)
                log.warning('Ignoring column {}, not 1d or 2d'.format(col))

    for chunk in range(n_chunks):

        start = chunk * chunksize
        end = min(n_rows, (chunk + 1) * chunksize)

        df = read_h5py(
            file_path,
            key=key,
            columns=columns,
            parse_dates=parse_dates,
            first=start,
            last=end
        )
        df.index = np.arange(start, end)

        yield df, start, end


def read_data(file_path, key=None, columns=None, **kwargs):
    '''
    This is a utility wrapper for other reading functions.
    It will look for the file extension and try to use the correct
    reader and return a dataframe.

    Currently supported are hdf5 (pandas and h5py), json, jsonlines and csv

    Parameters
    ----------
    file_path: str
        Path to the input file

    All kwargs are passed to the individual reading function:

    pandas hdf5:   pd.read_hdf
    h5py hdf5:     fact.io.read_h5py
    json:          pd.DataFrame(json.load(file))
    jsonlines:     pd.read_json
    csv:           pd.read_csv
    '''
    name, extension = path.splitext(file_path)

    if extension in ['.hdf', '.hdf5', '.h5']:
        try:
            df = pd.read_hdf(file_path, key=key, columns=columns, **kwargs)
        except (TypeError, ValueError):
            df = read_h5py(file_path, key=key, columns=columns, **kwargs)
        return df

    if extension == '.json':
        with open(file_path, 'r') as j:
            d = json.load(j)
            df = pd.DataFrame(d)

    elif extension in ('.jsonl', '.jsonlines'):
        df = pd.read_json(file_path, lines=True, **kwargs)

    elif extension == '.csv':
        df = pd.read_csv(file_path, **kwargs)

    else:
        raise NotImplementedError('Unknown data file extension {}'.format(extension))

    if columns:
        df = df[columns]

    return df


def check_extension(file_path, allowed_extensions=allowed_extensions):
    p, extension = path.splitext(file_path)
    if extension not in allowed_extensions:
        raise IOError('Allowed formats: {}'.format(allowed_extensions))


def to_h5py(df, filename, key='data', mode='a', dtypes=None, index=True, **kwargs):
    '''
    Write pandas dataframe to h5py style hdf5 file

    Parameters
    ----------
    df: pd.DataFrame
        The data to write out
    filename: str
        output file name
    key: str
        the name for the hdf5 group to hold all datasets, default: data
    mode: str
        'w' to overwrite existing files, 'a' to append
    dtypes: dict
        if given, a mapping of column names to dtypes for conversion.
    index: bool
        If bool, also save the index of the dataframe

    All `**kwargs` are passed to h5py.create_dataset
    '''
    assert mode in ('w', 'a'), 'mode has to be either "a" or "w"'

    array = df.to_records(index=index)

    if dtypes is not None:
        array = change_recarray_dtype(array, dtypes)

    with h5py.File(filename, mode=mode) as f:
        if key not in f:
            initialize_h5py(f, array, key=key, **kwargs)

        append_to_h5py(f, array, key=key)


def change_recarray_dtype(array, dtypes):
    '''
    Change dtypes of recarray columns

    Parameters
    ----------
    array: np.recarray
      The array to modify
    dtypes: dict
        if given, a mapping of column names to dtypes for conversion.

    Returns
    -------
    array: np.recarray
        Copy of the original array with changed dtypes
    '''

    # get a modifieabale list of dtypes
    dt = array.dtype.descr
    # create a mapping from column name to index
    idx = {k: i for i, (k, d) in enumerate(dt)}

    for col, new_type in dtypes.items():
        dt[idx[col]] = (col, new_type)

    dt = np.dtype(dt)

    return array.astype(dt)


def initialize_h5py(f, array, key='events', **kwargs):
    '''
    Create a group with name `key` and empty datasets for each
    entry in dtypes.

    Parameters
    ----------
    f: h5py.File
        the hdf5 file, opened either in write or append mode
    array: numpy structured array
        The data
    key: str
        the name for the hdf5 group to hold all datasets, default: data

    All kwargs are passed to h5py create_dataset
    '''
    group = f.require_group(key)

    dtypes = array.dtype
    for name in dtypes.names:
        create_empty_h5py_dataset(
            array[name],
            group,
            name,
            **kwargs,
        )

    return group


def create_empty_h5py_dataset(array, group, name, **kwargs):
    '''
    Create a new h5py dataset for the content of `array`.

    datetime64 objects are stored as fixed length strings
    arrays of lists are stored as 2d arrays (so they have to be fixed length)
    strings are stored as special dtype for strings

    Parameters
    ----------
    array: numpy.array or numpy.recarray
        the numpy array to get the dtype and shape from
    dataset: h5py.Group
        the hdf5 group the dataset should be created in
    name: str
        name for the new dataset
    **kwargs:
        all **kwargs are passed to create_dataset, useful for e.g. compression
    '''
    dtype = array.dtype
    maxshape = [None] + list(array.shape)[1:]
    shape = [0] + list(array.shape)[1:]
    attrs = {}

    if dtype.base == object:
        if isinstance(array[0], list):
            dt = np.array(array[0]).dtype
            shape = [0, len(array[0])]
            maxshape = [None, len(array[0])]
        else:
            dt = h5py.special_dtype(vlen=str)

    elif dtype.type == np.datetime64:
        # save dates as ISO string, create dummy date to get correct length
        dt = np.array(0, dtype=dtype).astype('S').dtype
        attrs['timeformat'] = 'iso'

    else:
        dt = dtype.base

    # add default compression options if no options are given
    if 'compression' not in kwargs:
        kwargs.update(DEFAULT_COMPRESSION)

    dataset = group.create_dataset(
        name,
        shape=tuple(shape),
        maxshape=tuple(maxshape),
        dtype=dt,
        **kwargs
    )

    for k, v in attrs.items():
        dataset.attrs[k] = v

    return dataset


def append_to_h5py_dataset(array, dataset):
    '''
    Append a single numpy array to an h5py dataset.

    datetime64 objects are stored as fixed length strings
    arrays of lists are stored as 2d arrays (so they have to be fixed length)

    Parameters
    ----------
    array: numpy.array or numpy.recarray
        the numpy array to append
    dataset: h5py.Dataset
        the hdf5 dataset to append to
    '''
    n_existing_rows = dataset.shape[0]
    n_new_rows = array.shape[0]

    dataset.resize(n_existing_rows + n_new_rows, axis=0)

    # swap byteorder if not native
    if array.dtype.byteorder not in ('=', native_byteorder, '|'):
        data = array.newbyteorder().byteswap()
    else:
        data = array

    if data.dtype.type == np.datetime64:
        data = data.astype('S')

    if data.dtype.base == object:
        if isinstance(data[0], list):
            data = np.array([o for o in data])

    dataset[n_existing_rows:] = data


def append_to_h5py(f, array, key='events'):
    '''
    Append a numpy record or structured array to the given hdf5 file
    The file should have been previously initialized with initialize_hdf5

    Parameters
    ----------
    f: h5py.File
        the hdf5 file, opened either in write or append mode
    array: numpy.array or numpy.recarray
        the numpy array to append
    key: str
        the name for the hdf5 group with the corresponding data sets
    '''

    group = f.get(key)

    for column in array.dtype.names:
        dataset = group.get(column)
        if dataset is None:
            raise KeyError('No such dataset {}'.format(column))
        append_to_h5py_dataset(array[column], dataset)


def read_simulated_spectrum(corsika_headers_path):
    '''
    Read the properties of the simulated spectrum
    from a corsika headers hdf5 file.

    Looks in the `corsika_runs` group for the keys
    `n_showers`, `energy_min`, `energy_max`, `x_scatter`
    and `energy_spectrum_slope`.

    For older versions, it checks the hdf5 attribute `scatter_radius`
    of the `corsika_runs` groups.
    '''
    runs = read_h5py(corsika_headers_path, key='corsika_runs')

    summary = {}
    if 'n_showers' in runs.columns:
        n_showers = runs['n_showers']
    else:
        n_showers = runs['n_events']

    summary['n_showers'] = n_showers.sum()

    with h5py.File(corsika_headers_path, 'r') as f:
        summary['n_reuse'] = f['corsika_runs'].attrs.get('n_reuse', 1)

        if 'n_reuse' in runs.columns:
            # if reuse is not the same for all runs, multply n_showers
            # and set reuse to 1
            unique = runs['n_reuse'].unique()
            if len(unique) > 1:
                summary['n_showers'] = (n_showers * runs['n_reuse']).sum()
                summary['n_reuse'] = 1

            else:
                summary['n_reuse'] = runs['n_reuse'].iloc[0]

    keys = {'energy_min': u.GeV, 'energy_max': u.GeV, 'energy_spectrum_slope': None}
    if 'x_scatter' in runs.columns:
        keys['x_scatter'] = u.cm
    else:
        with h5py.File(corsika_headers_path, 'r') as f:
            r = f['corsika_runs'].attrs.get('scatter_radius')
            unit = f['corsika_runs'].attrs.get('scatter_radius_unit', u.m)
            if r is None:
                warnings.warn(
                    'File does neither contain column `/corsika_runs/x_scatter` '
                    'nor the attribute `scatter_radius`'
                )
            else:
                summary['x_scatter'] = u.Quantity(r, u.m)

    for key, unit in keys.items():
        unique_values = runs[key].unique()
        if len(unique_values) > 1:
            raise ValueError('Only simulations with the same "{}" supported'.format(key))
        summary[key] = u.Quantity(unique_values[0], unit)

    return summary
