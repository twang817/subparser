import argparse
import collections
import contextlib
import functools
import sys

from six.moves import configparser
from six import string_types


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


class Subcommand(object):
    '''
    multi-use object:
        - can be called to be used as a decorator to wrap dispatch functions
        - dispatch allows us to process the command-line and run the dispatch function
        - add_config adds an option to loads a config file prior to handling command-line options
        - all other methods are passed to the main parser
    '''
    def __init__(self, parser, config):
        self.parser = parser
        parser_factory = functools.partial(type(parser), config)
        self.subparser = parser.add_subparsers(dest='command',
                                               parser_class=parser_factory)
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
        self.config_parser = argparse.ArgumentParser(add_help=False)
        self.config_action = self.config_parser.add_argument(*args, **kwargs)
        self.parser._add_container_actions(self.config_parser)

    def dispatch(self, args=None, namespace=None):
        '''
        process args and dispatch appropriate dispatch function
        '''
        if self.config_parser:
            namespace, args = self.config_parser.parse_known_args(args, namespace)
            self.config.impl = getattr(namespace, self.config_action.dest, None).config
        ns = self.parser.parse_args(args, namespace)
        return ns.func(ns)


class ConfigFacade(object):
    '''
    an object that allows ConfigEnabledArgumentParser to have no knowledge of
    how to actually get a config setting.  defaults to a pass-through if no
    implementation is configured.
    '''
    def __init__(self, impl=None):
        self.impl = impl

    def get_default(self, setting):
        if self.impl is None:
            return setting
        return self.impl.get_default(setting)


class ConfigEnabledArgumentParser(argparse.ArgumentParser):
    '''
    an argparse.ArgumentParser that resolves default values of type _ConfigSetting
    prior to handling command-line options.
    '''
    def __init__(self, config, *args, **kwargs):
        self.config = config
        super(ConfigEnabledArgumentParser, self).__init__(*args, **kwargs)

    def parse_known_args(self, args=None, namespace=None):
        # default Namespace built from parser defaults
        if namespace is None:
            namespace = argparse.Namespace()

        # add any action defaults that aren't present
        for action in self._actions:
            if action.dest is not argparse.SUPPRESS:
                if not hasattr(namespace, action.dest):
                    if action.default is not argparse.SUPPRESS:
                        setattr(namespace, action.dest, self.config.get_default(action.default))

        # add any parser defaults that aren't present
        for dest in self._defaults:
            if not hasattr(namespace, dest):
                setattr(namespace, dest, self.config.get_default(self._defaults[dest]))

        # call parse_known_args on parent
        return super(ConfigEnabledArgumentParser, self).parse_known_args(args, namespace)


class _ConfigAction(argparse.Action):
    '''
    base action class for handling the config option.

    creates a named tuple in namespace containing both the option value (source)
    and the config.
    '''
    ConfigTuple = collections.namedtuple('Config', 'source config')
    ConfigImpl = None

    def __init__(self, *args, **kwargs):
        default = kwargs.pop('default', None)
        config = self.make_config()
        try:
            config.load(default)
        except IOError:
            # ignore if the config file specified in ENV or in default does not exist
            default = None
        super(_ConfigAction, self).__init__(*args, default=self.ConfigTuple(default, config), **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        config = self.make_config()
        config.load(values)
        setattr(namespace, self.dest, self.ConfigTuple(values, config))

    def make_config(self):
        return self.ConfigImpl()


class RawConfigParserImpl(configparser.RawConfigParser):
    '''
    A config object for RawConfigParserAction
    '''
    def get_default(self, setting):
        '''
        gets a value for config setting
        '''
        if not isinstance(setting, RawConfigParserAction.Setting):
            return setting
        try:
            return self.get(setting.section, setting.option)
        except (configparser.NoOptionError, configparser.NoSectionError):
            return setting.default

    def load(self, source):
        '''
        loads the config given a source.
        '''
        if source is not None:
            with self.fetch(source) as fp:
                self.readfp(fp)

    @contextlib.contextmanager
    def fetch(self, source):
        '''
        fetches a config given a source.
        '''
        fp = open(source, 'r')
        try:
            yield fp
        finally:
            fp.close()


class RawConfigParserAction(_ConfigAction):
    '''
    an action for handling config options that are parsed via RawConfigParser.
    '''
    Setting = collections.namedtuple('Setting', 'section option default')
    ConfigImpl = RawConfigParserImpl


def subparser(*args, **kwargs):
    _config = ConfigFacade()
    _parser = ConfigEnabledArgumentParser(_config, *args, **kwargs)
    return Subcommand(_parser, _config)
