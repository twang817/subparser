Purpose:
========

Easy handling of subparsers.

Usage:
======

    import sys
    from subparser import subcommand

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
        subcommand._parser.add_argument('--top', type=str)
        subcommand.dispatch()
        sys.exit(0)
