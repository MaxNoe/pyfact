from fact.path import parse, template_to_path, tree_path
from functools import partial


def test_parse():

    input_paths = [
        '/fact/raw/2016/01/01/20160101_011.fits.fz',
        '/fact/aux/2016/01/01/20160101.FSC_CONTROL_TEMPERATURE.fits',
        '/fact/aux/2016/01/01/20160101.log',
        '/hackypateng/20140115_079_079.root'
    ]

    result_dicts = [
        {'prefix': '/fact/raw',
         'night': 20160101,
         'run': 11,
         'suffix': '.fits.fz'},
        {'prefix': '/fact/aux',
         'night': 20160101,
         'run': None,
         'suffix': '.FSC_CONTROL_TEMPERATURE.fits'},
        {'prefix': '/fact/aux',
         'night': 20160101,
         'run': None,
         'suffix': '.log'},
        {'prefix':
         '/hackypateng',
         'night': 20140115,
         'run': 79,
         'suffix': '_079.root'},
    ]

    for path, expected in zip(input_paths, result_dicts):
        parsed = parse(path)
        assert parsed == expected


def test_tree_path():

    night_run_tuples = [
        (20160101, 1),
        (20160101, 2),
        (20130506, 3),
    ]

    result_paths = [
        '/bar/2016/01/01/20160101_001.phs.jsonl.gz',
        '/bar/2016/01/01/20160101_002.phs.jsonl.gz',
        '/bar/2013/05/06/20130506_003.phs.jsonl.gz',
    ]

    photon_stream_path = partial(
        tree_path,
        prefix='/bar',
        suffix='.phs.jsonl.gz'
    )
    for night_run, result in zip(night_run_tuples, result_paths):
        assert result == photon_stream_path(*night_run)


def test_template_to_path():
    night_run_tuples = [
        (20160101, 1),
        (20160101, 2),
        (20130506, 3),
    ]

    single_pe_path_2runs = partial(
        template_to_path,
        template='/foo/{N}_{R}_{run2:03d}.root'
    )

    result_paths = [
        '/foo/20160101_001_003.root',
        '/foo/20160101_002_004.root',
        '/foo/20130506_003_005.root',
    ]

    for night_run, result in zip(night_run_tuples, result_paths):
        assert result == single_pe_path_2runs(
            *night_run,
            run2=night_run[1]+2)


def test_float_input():
    assert '.' not in tree_path(20170901, 123, 'prefix', '_suffix')
    assert '.' not in tree_path(20170901.0, 123, 'prefix', '_suffix')
    assert '.' not in tree_path(20170901, 123.0, 'prefix', '_suffix')
    assert '.' not in tree_path(20170901.0, 123.0, 'prefix', '_suffix')