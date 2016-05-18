Purpose:
========

Easy handling of subparsers.

Usage:
======

    import sys
    from subparser import subparser

    subcommand = subparser()

    @subcommand
    def sub1(a, top):
        print 'top:', top
        print 'a:', a
    sub1.add_argument('-a', type=int)

    @subcommand
    def sub2(b, top):
        print 'top:', top
        print 'b:', b
    sub2.add_argument('-b', type=int)

    if __name__ == '__main__':
        subcommand.set_defaults(**{
            'foo': 'bar',
        })
        subcommand.add_argument('--top', type=str)
        subcommand.dispatch()
        sys.exit(0)


Config File (IniConfig):
========================

foo.ini:

    [hello]
    name = Tommy

    [speak]
    animal = pig

test.py:

    from __future__ import print_function

    import json
    import os

    from subparser import subparser, IniConfig

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

    subcommand.add_config('-c', dest='config', default='foo.ini', config_class=IniConfig)

    subcommand.dispatch()
