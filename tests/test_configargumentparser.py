from __future__ import print_function

import argparse
import decorator
import json
import os
import pytest

from subparser.subparser import ConfigArgumentParser, ConfigFacade, ns_dispatch
from subparser import subparser, JsonConfig, IniConfig


@pytest.fixture
def inifile(tmpdir):
    p = tmpdir.join('config.ini')
    with open(str(p), 'w') as f:
        f.write('[hello]\n')
        f.write('name = Joe\n')
        f.write('[speak]\n')
        f.write('animal = pig\n')
    return str(p)


@pytest.fixture
def jsonfile(tmpdir):
    p = tmpdir.join('config.json')
    with open(str(p), 'w') as f:
        json.dump({'name': 'Joe',
                   'animal': 'pig'}, f)
    return str(p)


@pytest.fixture
def mockconfig():
    config = JsonConfig()
    config.loaded = True
    config.config = {
        'foo': 'google',
        'num1': 10.0,
        'num2': '20',
    }
    facade = ConfigFacade()
    facade.impl = config
    return facade


def clearenv(func):
    def wrapper(func, *args, **kwargs):
        for a in ENV_VARS:
            if a in os.environ:
                del os.environ[a]
        return func(*args, **kwargs)
    return decorator.decorator(wrapper, func)


ENV_VARS = 'ENV_FOO ENV_NAME ENV_ANIMAL ENV_CONFIG'.split()


@clearenv
def test_set_defaults():
    parser = ConfigArgumentParser(description='test program')
    parser.add_argument('--foo')
    parser.set_defaults(**{'foo': 'bar'})
    args = []
    ns = parser.parse_args(args)
    assert ns.foo == 'bar'
    assert len(vars(ns)) == 1


@clearenv
def test_action_defaults():
    parser = ConfigArgumentParser(description='test program')
    parser.add_argument('--foo', default='blah')
    args = []
    ns = parser.parse_args(args)
    assert ns.foo == 'blah'
    assert len(vars(ns)) == 1


@clearenv
def test_second_defaults_settings_wins():
    parser = ConfigArgumentParser(description='test program')
    parser.set_defaults(**{'foo': 'bar'})
    parser.add_argument('--foo', default='blah')
    args = []
    ns = parser.parse_args(args)
    assert ns.foo == 'blah'
    assert len(vars(ns)) == 1


@clearenv
def test_config_over_defaults(mockconfig):
    parser = ConfigArgumentParser(description='test program')
    parser.add_argument('--foo', env='ENV_FOO', default='cars', config='foo')
    parser._set_config(mockconfig)
    args = []
    ns = parser.parse_args(args)
    assert ns.foo == 'google'
    assert len(vars(ns)) == 1


@clearenv
def test_env_over_defaults():
    os.environ['ENV_FOO'] = 'bats'
    parser = ConfigArgumentParser(description='test program')
    parser.add_argument('--foo', env='ENV_FOO', default='cars', config='foo')
    args = []
    ns = parser.parse_args(args)
    assert ns.foo == 'bats'
    assert len(vars(ns)) == 1


@clearenv
def test_env_over_config(mockconfig):
    os.environ['ENV_FOO'] = 'bats'
    parser = ConfigArgumentParser(description='test program')
    parser.add_argument('--foo', env='ENV_FOO', default='cars', config='foo')
    parser._set_config(mockconfig)
    args = []
    ns = parser.parse_args(args)
    assert ns.foo == 'bats'
    assert len(vars(ns)) == 1


@clearenv
def test_env_not_set():
    parser = ConfigArgumentParser(description='test program')
    parser.add_argument('--foo', env='ENV_FOO', default='cars')
    args = []
    ns = parser.parse_args(args)
    assert ns.foo == 'cars'
    assert len(vars(ns)) == 1


@clearenv
def test_command_over_all(mockconfig):
    os.environ['ENV_FOO'] = 'bats'
    parser = ConfigArgumentParser(description='test program')
    parser.add_argument('--foo', env='ENV_FOO', default='cars', config='foo')
    parser._set_config(mockconfig)
    args = ['--foo', 'red']
    ns = parser.parse_args(args)
    assert ns.foo == 'red'
    assert len(vars(ns)) == 1


@clearenv
def test_coerce_env():
    os.environ['ENV_NUM'] = '10'
    parser = ConfigArgumentParser(description='test program')
    parser.add_argument('--num', env='ENV_NUM', default=0, type=int)
    args = []
    ns = parser.parse_args(args)
    assert ns.num == 10
    assert len(vars(ns)) == 1


@clearenv
def test_coerce_config(mockconfig):
    parser = ConfigArgumentParser(description='test program')
    parser.add_argument('--num1', config='num1', default=0, type=int)
    parser.add_argument('--num2', config='num2', default=0, type=int)
    parser._set_config(mockconfig)
    args = []
    ns = parser.parse_args(args)
    # num1 did not coerce because it was not a string (matches argparse spec)
    assert ns.num1 == 10.0
    # num2 coerced because it was a string in the config
    assert ns.num2 == 20
    assert len(vars(ns)) == 2


@clearenv
def test_subparser(capsys, jsonfile):
    subcommand = subparser()

    @subcommand
    def hello(name):
        print('Hello %s!' % name)
    hello.add_argument('--name', default='John')

    @subcommand('speak')
    def blah(animal):
        if animal == 'dog':
            return 'bark'
        elif animal == 'cat':
            return 'meow'
        elif animal == 'pig':
            return 'oink'
        elif animal == 'duck':
            return 'quack'
        raise Exception('animal not found')
    blah.add_argument('--animal', default='dog')

    # functions are manually callable
    assert blah('dog') == 'bark'

    subcommand.dispatch(['hello'])
    out, err = capsys.readouterr()
    assert out == 'Hello John!\n'
    assert subcommand.dispatch(['speak']) == 'bark'

    subcommand.dispatch(['hello', '--name', 'Joe'])
    out, err = capsys.readouterr()
    assert out == 'Hello Joe!\n'
    assert subcommand.dispatch(['speak', '--animal', 'pig']) == 'oink'

    # test that system exits without subcommand
    with pytest.raises(SystemExit):
        subcommand.dispatch([])
    out, err = capsys.readouterr()
    assert err.startswith('usage: py.test [-h] {hello,speak}')


@clearenv
def test_subparser_config(capsys, jsonfile):
    subcommand = subparser()

    @subcommand
    def hello(name):
        print('Hello %s!' % name)
    hello.add_argument('--name', env='ENV_NAME', config='name', default='John')

    @subcommand('speak')
    def blah(animal):
        if animal == 'dog':
            return 'bark'
        elif animal == 'cat':
            return 'meow'
        elif animal == 'pig':
            return 'oink'
        elif animal == 'duck':
            return 'quack'
        raise Exception('animal not found')
    blah.add_argument('--animal', env='ENV_ANIMAL', config='animal', default='dog')

    subcommand.add_config('-c', dest='config')
    os.environ['ENV_NAME'] = 'Eric'
    os.environ['ENV_ANIMAL'] = 'cat'

    # command-line takes highest precedence
    subcommand.dispatch(['hello', '-c', jsonfile, '--name', 'Robert'])
    out, err = capsys.readouterr()
    assert out == 'Hello Robert!\n'
    assert subcommand.dispatch(['speak', '-c', jsonfile, '--animal', 'duck']) == 'quack'

    # then, environment variables
    subcommand.dispatch(['hello', '-c', jsonfile])
    out, err = capsys.readouterr()
    assert out == 'Hello Eric!\n'
    assert subcommand.dispatch(['speak', '-c', jsonfile]) == 'meow'

    # then, config file values
    del os.environ['ENV_NAME']
    del os.environ['ENV_ANIMAL']
    subcommand.dispatch(['hello', '-c', jsonfile])
    out, err = capsys.readouterr()
    assert out == 'Hello Joe!\n'
    assert subcommand.dispatch(['speak', '-c', jsonfile]) == 'oink'

    # finally, default values
    subcommand.dispatch(['hello'])
    out, err = capsys.readouterr()
    assert out == 'Hello John!\n'
    assert subcommand.dispatch(['speak']) == 'bark'

    # test that help contains config
    with pytest.raises(SystemExit):
        subcommand.dispatch(['-h'])
    out, err = capsys.readouterr()
    assert '-c CONFIG' in [l.strip() for l in out.splitlines()]


@clearenv
def test_subparser_config_error_on_missing_cmdline(capsys):
    subcommand = subparser()

    @subcommand
    def hello(name):
        print('Hello %s!' % name)
    hello.add_argument('--name', env='ENV_NAME', config='name', default='John')

    @subcommand('speak')
    def blah(animal):
        if animal == 'dog':
            return 'bark'
        elif animal == 'cat':
            return 'meow'
        elif animal == 'pig':
            return 'oink'
        elif animal == 'duck':
            return 'quack'
        raise Exception('animal not found')
    blah.add_argument('--animal', env='ENV_ANIMAL', config='animal', default='dog')

    subcommand.add_config('-c', dest='config')

    with pytest.raises(IOError):
        subcommand.dispatch(['hello', '-c', 'foo.json'])


@clearenv
def test_subparser_config_error_on_missing_env(capsys):
    subcommand = subparser()

    @subcommand
    def hello(name):
        print('Hello %s!' % name)
    hello.add_argument('--name', env='ENV_NAME', config='name', default='John')

    @subcommand('speak')
    def blah(animal):
        if animal == 'dog':
            return 'bark'
        elif animal == 'cat':
            return 'meow'
        elif animal == 'pig':
            return 'oink'
        elif animal == 'duck':
            return 'quack'
        raise Exception('animal not found')
    blah.add_argument('--animal', env='ENV_ANIMAL', config='animal', default='dog')

    subcommand.add_config('-c', dest='config', env='ENV_CONFIG', check_file_for='command env'.split())
    os.environ['ENV_CONFIG'] = 'foo.json'

    with pytest.raises(IOError):
        subcommand.dispatch(['hello'])


@clearenv
def test_subparser_config_suppress_on_missing_env(capsys):
    subcommand = subparser()

    @subcommand
    def hello(name):
        print('Hello %s!' % name)
    hello.add_argument('--name', env='ENV_NAME', config='name', default='John')

    @subcommand('speak')
    def blah(animal):
        if animal == 'dog':
            return 'bark'
        elif animal == 'cat':
            return 'meow'
        elif animal == 'pig':
            return 'oink'
        elif animal == 'duck':
            return 'quack'
        raise Exception('animal not found')
    blah.add_argument('--animal', env='ENV_ANIMAL', config='animal', default='dog')

    subcommand.add_config('-c', dest='config', env='ENV_CONFIG')
    os.environ['ENV_CONFIG'] = 'foo.json'

    subcommand.dispatch(['hello'])
    out, err = capsys.readouterr()
    assert out == 'Hello John!\n'


@clearenv
def test_subparser_config_ini(capsys, inifile):
    subcommand = subparser()

    @subcommand
    def hello(name):
        print('Hello %s!' % name)
    hello.add_argument('--name', env='ENV_NAME', config=IniConfig.Key('hello', 'name'), default='John')

    @subcommand('speak')
    def blah(animal):
        if animal == 'dog':
            return 'bark'
        elif animal == 'cat':
            return 'meow'
        elif animal == 'pig':
            return 'oink'
        elif animal == 'duck':
            return 'quack'
        raise Exception('animal not found')
    blah.add_argument('--animal', env='ENV_ANIMAL', config=IniConfig.Key('speak', 'animal'), default='dog')

    subcommand.add_config('-c', dest='config', config_class=IniConfig)
    os.environ['ENV_NAME'] = 'Eric'
    os.environ['ENV_ANIMAL'] = 'cat'

    # command-line takes highest precedence
    subcommand.dispatch(['hello', '-c', inifile, '--name', 'Robert'])
    out, err = capsys.readouterr()
    assert out == 'Hello Robert!\n'
    assert subcommand.dispatch(['speak', '-c', inifile, '--animal', 'duck']) == 'quack'

    # then, environment variables
    subcommand.dispatch(['hello', '-c', inifile])
    out, err = capsys.readouterr()
    assert out == 'Hello Eric!\n'
    assert subcommand.dispatch(['speak', '-c', inifile]) == 'meow'

    # then, config file values
    del os.environ['ENV_NAME']
    del os.environ['ENV_ANIMAL']
    subcommand.dispatch(['hello', '-c', inifile])
    out, err = capsys.readouterr()
    assert out == 'Hello Joe!\n'
    assert subcommand.dispatch(['speak', '-c', inifile]) == 'oink'

    # finally, default values
    subcommand.dispatch(['hello'])
    out, err = capsys.readouterr()
    assert out == 'Hello John!\n'
    assert subcommand.dispatch(['speak']) == 'bark'

    # test that help contains config
    with pytest.raises(SystemExit):
        subcommand.dispatch(['-h'])
    out, err = capsys.readouterr()
    assert '-c CONFIG' in [l.strip() for l in out.splitlines()]


def test_ns_dispatch():
    ns = argparse.Namespace()
    setattr(ns, 'name', 'tommy')
    setattr(ns, 'names', ['tommy', 'john', 'richard'])

    def capitalize(name):
        return name.upper()
    assert ns_dispatch(capitalize, ns) == 'TOMMY'

    def passns(ns):
        return ns.name.upper()
    assert ns_dispatch(passns, ns) == 'TOMMY'

    def passnskwargs(**kwargs):
        return kwargs['ns'].name.upper()
    assert ns_dispatch(passns, ns) == 'TOMMY'

    def passnskwargs(**kwargs):
        return kwargs['name'].upper()
    assert ns_dispatch(passnskwargs, ns) == 'TOMMY'

    def passargs(*names):
        return ','.join(name.upper() for name in names)
    assert ns_dispatch(passargs, ns) == 'TOMMY,JOHN,RICHARD'


def test_argspec():
    '''
    this is more obscure.  basically, we're testing that we didn't change the
    argspec of the original function when we wrapped it.
    '''
    subcommand = subparser()
    @subcommand
    def bar(a, b):
        pass
    import inspect
    spec = inspect.getargspec(bar)
    assert spec.args == ['a', 'b']
