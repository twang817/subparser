Purpose:
========

Easy handling of subparsers.

Usage:
======

    import sys
    from subparser import subparser

    subcommand = subparser()

    @subcommand
    def sub1(ns):
        print 'top:', ns.top
        print 'a:', ns.a
    sub1.add_argument('-a', type=int)

    @subcommand
    def sub2(ns):
        print 'top:', ns.top
        print 'bg', ns.b
    sub2.add_argument('-b', type=int)

    if __name__ == '__main__':
        subcommand.set_defaults(**{
            'foo': 'bar',
        })
        subcommand.add_argument('--top', type=str)
        subcommand.dispatch()
        sys.exit(0)

Config File:
============

foo.ini:

    [foo]
    opt = iniopt

test.py:

    import subparser

    subcommand = subparser.subparser()

    @subcommand
    def foo(ns):
        print 'foo', ns
    foo.add_argument('--opt', type=str, default=subparser.RawConfigParserAction.Setting('foo', 'opt', 'defaultopt'))

    @subcommand
    def bar(ns):
        print 'bar', ns
    bar.add_argument('--flag', type=str, default=subparser.RawConfigParserAction.Setting('bar', 'flag', 'defaultflag'))

    subcommand.add_config('-c', default='foo.ini', action=subparser.RawConfigParserAction)
    subcommand.dispatch()


    > python test.py foo
    foo Namespace(c=Config(source='foo.ini', config=<subparser.ConfigImpl instance at 0x10b2f15f0>), command='foo', func=<function foo at 0x10b184140>, opt='iniopt')

    > python test.py foo --opt cmdopt
    foo Namespace(c=Config(source='foo.ini', config=<subparser.ConfigImpl instance at 0x106fff5f0>), command='foo', func=<function foo at 0x106e93140>, opt='cmdopt')

    > python test.py bar --flag cmdflag
    bar Namespace(c=Config(source='foo.ini', config=<subparser.ConfigImpl instance at 0x1031665f0>), command='bar', flag='cmdflag', func=<function bar at 0x10315c668>)

    > python test.py bar
    bar Namespace(c=Config(source='foo.ini', config=<subparser.ConfigImpl instance at 0x1066ab5f0>), command='bar', flag='defaultflag', func=<function bar at 0x1066a1668>)
