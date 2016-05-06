#!/usr/bin/env python
import argparse


class subcommand(object):
    _parser = argparse.ArgumentParser()
    _subparser = _parser.add_subparsers(dest='command')
    def __new__(cls, command_or_f=None, command=None):
        if isinstance(command_or_f, basestring):
            return lambda f: subcommand(f, command_or_f)
        elif callable(command_or_f):
            return object.__new__(cls)
    def __init__(self, function, command=None):
        self.parser = self._subparser.add_parser(command or function.__name__)
        self.parser.set_defaults(function=function)
    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)
    def __getattr__(self, key):
        return getattr(self.parser, key)
    @classmethod
    def parse_args(cls, *args, **kwargs):
        return cls._parser.parse_args(*args, **kwargs)
    @classmethod
    def dispatch(cls, *args, **kwargs):
        ns = cls._parser.parse_args(*args, **kwargs)
        return ns.function(ns)
    @classmethod
    def set_defaults(cls, *args, **kwargs):
        cls._parser.set_defaults(*args, **kwargs)
