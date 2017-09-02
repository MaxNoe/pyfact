import os.path
import re

__all__ = [
    'parse'
    'template_to_path',
    'tree_path',
]


def template_to_path(night, run, template, **kwargs):
    '''Make path from template and (night, run) using kwargs existing.

    night: int or string
        e.g. night = 20160102 (int)
        is used to create Y,M,D,N template values as:
        Y = "2016"
        M = "01"
        D = "02"
        N = "20160101"
    run: int or string
        e.g. run = 1  or run = "000000001"
        is used to create template value R = "001"
    template: string
        e.g. "/foo/bar/{Y}/baz/{R}_{M}_{D}.gz.{N}"
    kwargs:
        if template contains other place holders than Y,M,D,N,R
        kwargs are used to format these.
    '''
    night = str(int(night))
    if run is not None:
        kwargs['R'] = '{:03d}'.format(int(run))

    kwargs['N'] = night
    kwargs['Y'] = night[0:4]
    kwargs['M'] = night[4:6]
    kwargs['D'] = night[6:8]
    return template.format(**kwargs)


def tree_path(night, run, prefix, suffix):
    '''Make a tree_path from a (night, run) for given prefix, suffix

    night: int or string
        eg. 20160101 or '20160101'
    run: int or string
        eg. 11 or '011' or None (int, string or None accepted)
    prefix: string
        eg. '/fact/raw' or '/fact/aux'
    suffix: string
        eg. '.fits.fz' or '.log' or '.AUX_FOO.fits'
    '''
    if run is not None:
        base_name = '{N}_{R}'
    else:
        base_name = '{N}'

    template = os.path.join(
            prefix,
            '{Y}',
            '{M}',
            '{D}',
            base_name + suffix)
    return template_to_path(night, run, template)


path_regex = re.compile(
    r'(?P<prefix>.*?)' +
    r'((/\d{4})(/\d{2})(/\d{2}))?/' +
    r'(?P<night>\d{8})' +
    r'(_?(?P<run>\d{3}))?' +
    r'(?P<suffix>.*)'
)


def parse(path):
    '''Return a dict with {prefix, suffix, night, run} parsed from path.

    path: string
        any (absolute) path should be fine.
    '''
    d = path_regex.match(path).groupdict()
    if d['run'] is not None:
        d['run'] = int(d['run'])
    d['night'] = int(d['night'])
    return d
