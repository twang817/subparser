from __future__ import absolute_import

import argparse
import collections
import contextlib

from six.moves import configparser


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
