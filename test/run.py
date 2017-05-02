from proboscis import register
from proboscis import TestProgram
import modules.httpd as httpd
import modules.amqp as amqp
import argparse
import sys


def run_tests(group=['smoke-tests']):

    import tests.api.v2_0 as api_2_0

    register(groups=['api-v2.0'], depends_on_groups=api_2_0.tests)
    register(groups=['smoke-tests'], depends_on_groups=['api-v2.0'])
    register(groups=['regression-tests'], depends_on_groups=['smoke-tests'] +
                    [test for test in api_2_0.regression_tests])

    TestProgram(groups=group).run_and_exit()


if __name__ == '__main__':
    # avoid eating valid proboscis args
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser()
        parser.add_argument('--config', default='config/config.ini', required=False)
        if sys.argv[1] == '--httpd':
            parser.add_argument('--httpd', action='store_const', const=True)
            parser.add_argument('-a', '--address', default='0.0.0.0', required=False)
            parser.add_argument('-p', '--port', default=80, required=False)
            args = parser.parse_args()
            httpd.run_server(args.address, args.port)
            sys.exit(0)
        if sys.argv[1] == '--amqp':
            parser.add_argument('--amqp', action='store_const', const=True)
            parser.add_argument('-e', '--exchange', default='on.events', required=False)
            parser.add_argument('-q', '--queue', default='poller.alert', required=False)
            parser.add_argument('-r', '--key', default='poller.alert.#', required=False)
            args = parser.parse_args()
            amqp.run_listener(amqp.make_queue_obj(args.exchange, args.queue, args.key))
            sys.exit(0)

    group = []
    for v in sys.argv:
        if 'group' in v:
            group = v.split('=')[1:]
    if len(group) > 0:
        run_tests(group)
        sys.exit(0)
    run_tests()
