from __future__ import print_function

import subparser

subcommand = subparser.subparser()

@subcommand
def foo(ns):
    print('foo', ns)
foo.add_argument('--opt', type=str, default=subparser.RawConfigParserAction.Setting('foo', 'opt', 'defaultopt'))

@subcommand
def bar(ns):
    print('bar', ns)
bar.add_argument('--flag', type=str, default=subparser.RawConfigParserAction.Setting('bar', 'flag', 'defaultflag'))


subcommand.add_config('-c', default='foo.ini', action=subparser.RawConfigParserAction)
subcommand.dispatch()
