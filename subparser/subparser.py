from __future__ import absolute_import

import argparse
import collections
import functools
import json
import inspect
import os

from six import string_types
from six.moves import configparser


class DispatchWrapper(object):
    '''
    wraps a dispatch function and creates a subparser out of it
    '''
    def __init__(self, subparser, func, name=None):
        self.func = func
        self.name = name or func.__name__
        self.parser = subparser.add_parser(self.name)
        self.parser.set_defaults(func=self.func)
        functools.update_wrapper(self, self.func)

    def __call__(self, *args, **kwargs):
        '''
        allows wrapped function to still be called
        '''
        return self.func(*args, **kwargs)

    def __getattr__(self, attr):
        '''
        provides access to ArgumentParser functions
        '''
        return getattr(self.parser, attr)


class ConfigAction(argparse.Action):
    def __init__(self, *args, **kwargs):
        self.env = kwargs.pop('env', None)
        self.check_file_for = kwargs.pop('check_file_for', ('command',))
        super(ConfigAction, self).__init__(*args, **kwargs)

    def resolve_config(self, ns):
        configfile = getattr(ns, self.dest, None)
        if configfile:
            return configfile, 'command' in self.check_file_for
        if self.env:
            configfile = os.getenv(self.env, None)
            if configfile:
                return configfile, 'env' in self.check_file_for
        return self.default, 'default' in self.check_file_for

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


class Subcommand(object):
    '''
    multi-use object:
        - can be called to be used as a decorator to wrap dispatch functions
        - dispatch allows us to process the command-line and run the dispatch
          function
        - add_config adds an option to loads a config file prior to handling
          command-line options
        - all other methods are passed to the main parser
    '''
    def __init__(self, parser, config):
        self.parser = parser
        self.subparser = parser.add_subparsers(dest='command',
                                               parser_class=parser_factory(
                                                   type(parser),
                                                   config))
        self.subparser.required = True
        self.config_parser = None
        self.config_action = None
        self.config = config

    def __call__(self, name_or_func=None):
        '''
        decorator to wrap dispatch functions
        '''
        if isinstance(name_or_func, string_types):
            def _decorator(f):
                return DispatchWrapper(self.subparser, f, name_or_func)
            return _decorator
        elif callable(name_or_func):
            return DispatchWrapper(self.subparser, name_or_func)
        raise Exception('unrecognized argument to Subcommand')

    def __getattr__(self, attr):
        '''
        act as a ArgumentParser for the main parser
        '''
        return getattr(self.parser, attr)

    def add_config(self, *args, **kwargs):
        '''
        add a config option to load config files prior to command-line
        '''
        self.config.impl = kwargs.pop('config_class', JsonConfig)()
        self.config_parser = argparse.ArgumentParser(add_help=False)
        self.config_action = self.config_parser.add_argument(*args, action=ConfigAction, **kwargs)
        kwargs.pop('check_file_for', None)
        self.parser.add_argument(*args, action=ConfigAction, check_file_for=[], **kwargs)

    def dispatch(self, args=None, namespace=None):
        '''
        process args and dispatch appropriate dispatch function
        '''
        if self.config_parser:
            self.config.reset()
            ns, args = self.config_parser.parse_known_args(args, namespace)
            configfile, required = self.config_action.resolve_config(ns)
            if configfile:
                try:
                    self.config.load(configfile)
                except Exception:
                    if required:
                        raise
                else:
                    self.parser.set_defaults(**{
                        self.config_action.dest: collections.namedtuple('config', 'configfile config')(configfile, self.config.impl)})
        ns = self.parser.parse_args(args, namespace)
        return self._dispatch_to(ns.func, ns)

    def _dispatch_to(self, func, ns):
        '''
        maps values in ns to function's argspec.

        each argument's name in the function's spect is mapped to
        the corresponding dest in the namespace.

        Ex:

        def foo(arg1, arg2):
            arg1 and arg2 in the ns

        def foo(arg1, arg2, **kwargs):
            arg1 and arg2 in the ns
            all other dests in ns goes into kwargs

        def foo(*arg1):
            args1 in the ns gets passed as varargs

        def foo(*arg1, **kwargs):
            args1 in the ns gets passed as varargs
            all other dests in ns goes into kwargs

        def foo(arg2, *args1, **kwargs):
            arg2 in the ns
            args1 in the ns gets passed as varargs
            all other dests in ns goes into kwargs
        '''
        kwargs = {}
        args = []
        values = vars(ns)
        consumed = []
        spec = inspect.getargspec(func)
        for arg in spec.args:
            consumed.append(arg)
            args.append(values[arg])
        if spec.varargs:
            if isinstance(values[spec.varargs], (list, tuple)):
                args.extend(values[spec.varargs])
            else:
                args.append(values[spec.varargs])
        if spec.keywords:
            for k, v in values.items():
                if k not in consumed:
                    kwargs[k] = v
        return func(*args, **kwargs)


class ConfigArgumentParser(argparse.ArgumentParser):
    '''
    an argparse.ArgumentParser that handles config files and environment
    variables for arguments.
    '''
    def __init__(self, *args, **kwargs):
        self._config = None
        self._config_keys = {}
        self._env = {}
        super(ConfigArgumentParser, self).__init__(*args, **kwargs)

    def _set_config(self, config):
        self._config = config

    def add_argument(self, *args, **kwargs):
        config_key = kwargs.pop('config', None)
        env = kwargs.pop('env', None)
        action = super(ConfigArgumentParser, self).add_argument(*args, **kwargs)
        if config_key:
            self._config_keys[action.dest] = config_key
        if env:
            self._env[action.dest] = env

    def parse_known_args(self, args=None, namespace=None):
        # default Namespace built from parser defaults
        if namespace is None:
            namespace = argparse.Namespace()

        # add environment variables to namespace if not already set
        for dest, env_var in self._env.items():
            if not hasattr(namespace, dest):
                env = os.getenv(env_var, None)
                if env:
                    setattr(namespace, dest, env)

        # if i have a valid config object, retrieve values and
        # add them to the namespace if they don't already exist
        if self._config and self._config.valid and self._config.loaded:
            for dest, config_key in self._config_keys.items():
                if not hasattr(namespace, dest):
                    value = self._config.get(config_key, argparse.SUPPRESS)
                    if value is not argparse.SUPPRESS:
                        setattr(namespace, dest, value)

        # call parse_known_args on parent
        return super(ConfigArgumentParser, self).parse_known_args(args, namespace)


class ConfigFacade(object):
    def __init__(self):
        self.impl = None

    @property
    def valid(self):
        return self.impl is not None

    def __getattr__(self, key):
        if self.valid:
            return getattr(self.impl, key)
        raise Exception('getattr of %s called on an invalid facade' % key)


class JsonConfig(object):
    def __init__(self):
        self.reset()

    def load(self, source):
        self.source = source
        self.fetch(source)
        self.loaded = True

    def fetch(self, source):
        with open(source, 'r') as f:
            self.config = json.load(f)

    def get(self, key, default):
        return self.config.get(key, default)

    def reset(self):
        self.config = None
        self.loaded = False
        self.source = None


class IniConfig(object):
    Key = collections.namedtuple('IniKey', 'section option')

    def __init__(self):
        self.reset()

    def load(self, source):
        self.source = source
        self.fetch(source)
        self.loaded = True

    def fetch(self, source):
        with open(source, 'r') as f:
            self.config.readfp(f)

    def get(self, key, default):
        try:
            return self.config.get(key.section, key.option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def reset(self):
        self.config = configparser.RawConfigParser()
        self.loaded = False
        self.source = None


def parser_factory(parser_class, config):
    def _factory(*args, **kwargs):
        parser = parser_class(*args, **kwargs)
        parser._set_config(config)
        return parser
    return _factory


def subparser(*args, **kwargs):
    _config = ConfigFacade()
    _parser = parser_factory(ConfigArgumentParser, _config)(*args, **kwargs)
    return Subcommand(_parser, _config)


subcommand = subparser()
