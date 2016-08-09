#!/usr/bin/env python
"""
Starts up the rackhd image.
"""
import argparse
import logging
import os
import vagrant

from subprocess import CalledProcessError

FORMAT = '%(asctime)-15s: %(message)s'
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)


def startvm(vm, recreate=False,  provision=False, ignore_error=False,):

    os_env = os.environ.copy()
    # Env variables are strings not bools
    os_env['PXE_NOGUI'] = "True"

    v = vagrant.Vagrant(quiet_stdout=False, env=os_env)

    status = v.status(vm_name=vm)[0].state
    logger.info('{0} in state {1} and recreate is {2}'.format(vm, status, recreate))
    if ignore_error:
        logger.info("Ignoring errors")

    if status != 'not_created' and recreate:
        logger.info('will destroy {0}'.format(vm))
        v.destroy(vm_name=vm)

    if provision:
        v.provision(vm_name=vm)

    logger.info('vagrant up {0}'.format(vm))
    try:
        v.up(vm_name=vm)
    except CalledProcessError as e:
        if ignore_error:
            logger.info("An error was raised, but we were told to ignore it.")
        else:
            raise e


def main():

    parser = argparse.ArgumentParser(description='Start vagrant instances.')
    parser.add_argument('--destroy', dest='destroy', action='store_true', default=False)
    parser.add_argument('--ignore-error', dest='ignore', action='store_true', default=False)
    parser.add_argument('--provision', dest='provision', action='store_true', default=False)
    parser.add_argument('vm_name', type=str, default='rackhd01')
    args = parser.parse_args()
    startvm(args.vm_name, recreate=args.destroy, ignore_error=args.ignore, provision=args.provision)

if __name__ == '__main__':
    main()
