"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import optparse
import re
from pexpect.pxssh import pxssh


class StreamToLogger(object):
    def __init__(self, logger, prefix):
        """
        This is a fake stream-ish device to allow us to turn raw
        stream data into logger calls to the passed in logger.

        Buffers output to new-line boundaries (to allow catching:
        "running test foo ... ok" as one entry.
        """
        self.__use_logger = logger
        self.__prefix = prefix
        self.__buffer = ''

    def write(self, data):
        self.__buffer += data
        while '\n' in self.__buffer:
            line, rest = self.__buffer.split('\n', 1)
            line = line.replace('\r', '')
            self.__use_logger.debug('%s%s', self.__prefix, line)
            self.__buffer = rest

    def flush(self):
        """
        We don't actually want to flush, since we could be mid-line
        """
        pass

    def real_flush(self):
        if len(self.__buffer) > 0:
            self.__use_logger.debug('%s%s', self.__prefix, self.__buffer)
            self.__buffer = ''


class SSHHelper(pxssh):
    _parser_options = None

    def __init__(self, device='dut', why='ssh:', *args, **kwargs):
        # differed import of flogging since we are inside the plugin
        # structure:
        from flogging import get_loggers
        self.__logs = get_loggers()
        self.__stream_to_log = None
        if 'logfile' not in kwargs:
            stream_to_log = StreamToLogger(self.__logs.idl, why)
            kwargs['logfile'] = stream_to_log
            self.__stream_to_log = stream_to_log

        super(SSHHelper, self).__init__(*args, **kwargs)
        assert device == 'dut', \
            'multiple targets not supported yet'
        assert self._parser_options is not None, \
            'attempt to create ssh helper before nose-plugin-begin step called'
        host = self._parser_options.sm_dut_ssh_host
        port = self._parser_options.sm_dut_ssh_port
        user = self._parser_options.sm_dut_ssh_user
        password = self._parser_options.sm_dut_ssh_password
        self.login(host, user, password, port=port)
        self.sendline('sudo su -')
        index = self.expect(['assword', '#'])
        if index == 0:
            self.sendline(password)
            self.expect(['#'])
        self.set_unique_prompt()
        self.dut_ssh_host = host
        self.dut_ssh_port = port

    def logout(self):
        self.sendline('exit')
        super(SSHHelper, self).logout()
        if self.__stream_to_log is not None:
            self.__stream_to_log.real_flush()

    def sendline_and_stat(self, cmd, must_be_0=False):
        self.sendline(cmd)
        self.prompt()
        cmd_out = self.before
        self.__logs.idl.debug("Going to execute remote command '%s'", cmd)
        self.sendline('echo xx $? xx')
        self.prompt()
        echo_data = self.before
        res_match = re.search(r'''xx\s(?P<ecode>\d+)\sxx''', echo_data)
        assert res_match is not None, \
            'unable to find output of just executed echo command {}'.format(echo_data)
        ecode = int(res_match.group('ecode'))
        if must_be_0:
            assert ecode == 0, \
                "failed command '{}' ecode={}, output={}".format(cmd, ecode, cmd_out)
        return cmd, ecode, cmd_out

    @classmethod
    def add_nose_parser_opts(cls, parser):
        """
        If the plugin needs to go and "talk" with the dut, we will
        need contact information. Primary use is setting up a test-AMQP
        user, but this is also needed to implement 'tail -f xxx.log' ON
        box at a later point.

        note: needs to be extended for HA (i.e., multiple ssh targets)
        """
        dut_ssh_group = optparse.OptionGroup(parser, 'DUT ssh options')
        parser.add_option_group(dut_ssh_group)
        dut_ssh_group.add_option(
            '--sm-dut-ssh-user', dest='sm_dut_ssh_user', default='vagrant',
            help="User to ssh into DUT using.")
        dut_ssh_group.add_option(
            '--sm-dut-ssh-password', dest='sm_dut_ssh_password', default='vagrant',
            help="Password to ssh into DUT using.")
        dut_ssh_group.add_option(
            '--sm-dut-ssh-port', dest='sm_dut_ssh_port', default=2222,
            help="Port of ssh server on DUT.")
        dut_ssh_group.add_option(
            '--sm-dut-ssh-host', dest='sm_dut_ssh_host', default='localhost',
            help="Hostname of DUT.")

    @classmethod
    def get_parser_options_sm_dut_ssh_host(cls):
        return cls._parser_options.sm_dut_ssh_host

    @classmethod
    def set_options(cls, parser_options):
        cls._parser_options = parser_options
