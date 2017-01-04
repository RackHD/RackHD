import jsonmerge
import jsonmerge.strategies
from singleton import Singleton
import argparse
import os
import sys
import time
import json

#pylint: disable=invalid-name

class mkcfg(object):

    """
    Manages a RackHD test configuration

    Singleton object creation:
    cfg = mkcfg(config_dir, json_config_files, arg_list)

    Access the singleton
    cfg = mkcfg()

    Methods:
        add : adds additional test configurations to an existing
              mkcfg object.  Individual dictionary values will be
              overwritten by the inbound json_config_file values.

              Example:
              cfg = mkcfg(config_dir, json_config_files, arg_list)
              cfg.add(stack_config_file)

        get : returns the config dictionary

              Example:
              myconfig_dict = cfg.get()

        get_path : returns the config dictionary

              Example:
              config_path = cfg.get_path()

        destroy : destroys the singleton to allow for a new configuration

              Example:
              cfg.destroy()
    """

    # mkcfg is a singleton
    __metaclass__ = Singleton

    config_env = 'FIT_CONFIG'
    default_composition = ['rackhd_default.json', 'credentials_default.json']

    def __init__(self, config_dir=None, json_config_list=None, arg_list=None):

        # handle default mutable types
        if json_config_list is None:
            json_config_list = []
        if arg_list is None:
            arg_list = []

        self.generated_config_path = None
        self.config_dict = dict()
        self.config_dir = config_dir
        self.generated_dir = self.config_dir + '/generated'
        config_path = os.environ.get(self.config_env)
        if not config_path:
            # no test configuration from environment.  create the config
            self.add(json_config_list, arg_list)
        else:
            # load up an existing configuration
            self.generated_config_path = config_path
            self.config_dict = self.__read_config(self.generated_config_path)

    def add(self, json_config_list, arg_list=None):
        """
        add a test configuration

        :config_dir: path to configuration files
        :param config_list: list of json configurations to be applied in order
        :param arg_list: command-line arguments
        :return:
        """
        # apply schema overlays
        schema = {'mergeStrategy': 'objectMerge'}
        for json_config in json_config_list:
            self.config_dict = jsonmerge.merge(self.config_dict,
                                               self.__read_config(self.config_dir + '/' + json_config),
                                               schema)

        # add test-config section
        if 'test-config' not in self.config_dict:
            self.config_dict['test-config'] = dict()

        # add cmd-line-args section
        if 'cmd-line-args' not in self.config_dict:
            if arg_list:
                self.config_dict['cmd-line-args'] = arg_list

        self.generated_config_path = self.__write_config_file()
        os.environ[self.config_env] = self.generated_config_path

    def get(self):
        """
        returns a rackhd test configuration as a dictionary
        :return:
        """
        return self.config_dict

    def get_path(self):
        """
        returns the path to the generated configuration file
        :return:
        """
        return self.generated_config_path

    def destroy(self):
        """
        destroys the existing configuration singleton object
        :return:
        """
        Singleton.purge(mkcfg)

    def __write_config_file(self, prepend=''):
        """
        write a json configuration file with a timestamped name
        :return:
        """
        timestr = prepend + time.strftime("%Y%m%d-%H%M%S")
        config_path = self.generated_dir + '/' + timestr
        with open(config_path, 'w') as outf:
            json.dump(self.config_dict, outf, indent=4, sort_keys=True)
        return config_path

    @staticmethod
    def __read_config(json_config):
        """
        read a json configuration file
        :return:
        """
        try:
            with open(json_config, 'r') as file_handle:
                try:
                    return json.load(file_handle)
                except ValueError as value_e:
                    print value_e
                    return None
        except (OSError, IOError) as load_e:
            print load_e
            return None

    def dump(self):
        """
        print the config dictionary to stdout
        :return:
        """
        print json.dumps(self.config_dict, indent=4, sort_keys=True)


if __name__ == "__main__":

    def usage_docstring(prog_base):
        """
        {0}

        self test of mkcfg

        Options supported:
            -c <config>  : configuration directory
            -a <json config> : overlay file (merged first)
            <-a <json config> : overlay file (merged second)>
            <-a <json config> : overlay file (merged third)>
            ...
            The created configuration is written to stdout

        For example:
            test_config -c config -a rackhd_default.json -a credentials_default.json -a install_default.json
        """
        return usage_docstring.__doc__.format(prog_base)

    PROG_NAME = os.path.basename(sys.argv[0])

    parser = argparse.ArgumentParser()
    parser.add_argument('-c')
    parser.add_argument('-a', action='append')
    args = parser.parse_args()
    config_dir_arg = args.c
    json_config_files_arg = args.a

    # we require config_dir and json_config_files
    if not config_dir_arg or not json_config_files_arg:
        print usage_docstring(PROG_NAME)
        exit(1)

    # specify a sample argument list
    ARGS_LIST = {
        "v": "v_value",
        "config": "config_value",
        "stack": "stack_value",
        "ora": "ora_value",
        "bmc": "bmc_value",
        "sku": "sku_value",
        "obmmac": "obmmac_value",
        "nodeid": "nodeid_value",
        "http": 8080,
        "https": 443
    }

    # Test config creation
    cfg = mkcfg(config_dir_arg, json_config_files_arg, ARGS_LIST)
    cfg.dump()

    # Dump out the configuration path.  We should be able to access with cfg object
    print "path = " + mkcfg().get_path()
    cfg.dump()

    # Get config singleton object and compare dictionaries
    cfg2 = mkcfg()
    if cfg2.config_dict != cfg.config_dict:
        print 'singleton is broken'
        exit(1)

    # throw away configuration
    cfg.destroy()

    # reload from FIT_CONFIG_PATH which should be in the environment from original mkcfg
    cfg = mkcfg(config_dir_arg)
    print "path = " + mkcfg().get_path()
    cfg.dump()

    exit(0)

