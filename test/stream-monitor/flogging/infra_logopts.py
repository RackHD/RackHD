"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import logging
import re
import argparse
import optparse
import sys


class _LoggingConfigFilter(logging.Filter):
    """
    Python logging Filter subclass that handles the following qualities:
    * An override handler-threshold. Say from DEBUG_5 to override console-capture's normal INFO.
    * which loggers connected to this handler should be tested against the override.
      (I.E., you can set 'infra.run', and 'test.run' to DEBUG_5, and this filter will only
       check infra.run and test.run loggers. Others will be checked against the 'unmatched_levelno'.
    * An 'unmatched_levelno' to use when the logger is NOT in the list. (see note below)
    * An optional file-pattern. Only checked within a matching logger.

    The filter is applied on a 1:1 basis with a single handler.

    Note that the unmatched_levelno is needed, because in order to get message records TO this
    filter, the loggers that feed them need to have their threshold dropped low enough, BUT we
    still want to apply their old handler threshold. This is how we do it.
    """
    def __init__(self, which_lgs, levelno, unmatched_levelno, name, file_pat=None):
        super(_LoggingConfigFilter, self).__init__(name)
        self.__which_loggers = which_lgs
        self.__levelno = levelno
        self.__unmatched_levelno = unmatched_levelno
        if file_pat is None:
            self.__file_matcher = re.compile('.*')  # match ANYTHING
        else:
            self.__file_matcher = re.compile(file_pat)

    def filter(self, record):
        if record.name in self.__which_loggers:
            if record.levelno >= self.__levelno:
                if self.__file_matcher.search(record.filename):
                    return True
            return False
        if record.levelno >= self.__unmatched_levelno:
            return True
        return False

    def __str__(self):
        rs = 'level {0} threshold for {1} loggers, umatched={2}'.format(
            self.__levelno, self.__which_loggers, self.__unmatched_levelno)
        return rs


class _ArgparseToOptparseWrapper(object):
    def __init__(self, parser):
        """
        Wrapper for optparser based objects that map argparse style operations
        to optparser ones. This is done to allow 'nose' (which still uses optparse!!!!) to
        function.
        """
        self.__parser = parser

    def add_argument_group(self, *args, **kwargs):
        new_group = optparse.OptionGroup(self.__parser, *args, **kwargs)
        new_wr_group = _ArgparseToOptparseWrapper(new_group)
        self.__parser.add_option_group(new_group)
        return new_wr_group

    def add_argument(self, *args, **kwargs):
        self.__parser.add_option(*args, **kwargs)

    def error(self, message):
        print >>sys.stderr, message
        sys.exit(2)


class LoggerArgParseHelper(object):
    def __init__(self, parser):
        """
        This is a class that can be instantiated with a parser (either optparse OR argparse) that
        adds options to control the infra-logging system.
        """
        if not isinstance(parser, argparse.ArgumentParser):
            parser = _ArgparseToOptparseWrapper(parser)

        self.__parser = parser
        list_group = parser.add_argument_group('listing log settings')
        list_group.add_argument(
            '--sm-list-logging', dest='list_logging', action='store_true', default=False,
            help='list logging settings')
        list_group.add_argument(
            '--sm-list-level', nargs=1, default=1, dest='list_logging_level',
            help='detail level if --list-logging is used')
        set_group = parser.add_argument_group(
            'setting log options',
            "note: both 'logger-name's and 'handler-name's can contain wild-card characters to match multiple items.")
        set_group.add_argument(
            '--sm-set-logger-level', nargs=2, default=[],
            dest='set_logger_level_list', action='append',
            metavar=('logger-name', 'level-name-or-value'),
            help="Set a logger's capture threshold. Loggers are evaluated before handlers.")
        set_group.add_argument(
            '--sm-set-handler-level', nargs=2, default=[],
            dest='set_handler_level_list', action='append',
            metavar=('handler-name[:logger-name]', 'level-name-or-value'),
            help="Set a handler's capture threshold.")

        set_group.add_argument(
            '--sm-set-combo-level', nargs=2, default=[],
            dest='set_combo_level_list', action='append',
            metavar=('handler-name[:logger-name]', 'level-name-or-value'),
            help="Set a handler's capture threshold AND all loggers feeding it.")

        set_group.add_argument(
            '--sm-set-file-level', nargs=3, dest='set_file_level',
            metavar=('file-pattern', '[handler-name[:logger-name] [level-name-or-value]]'),
            help="Same as --sm-set-combo-level, but restricts the change in output to the files that match the file-pattern")

    def __display_filter(self, indent, filter, detail):
        """
        Print a bit of info on the given filter.
        """
        indent_txt = ' ' * indent
        print >>sys.stderr, 'F{0}{1}: {2}'.format(indent_txt, filter.name, str(filter))

    def __display_handler(self, indent, handler, detail):
        """
        Print out a bit of info on the given handler and then display its filters
        """
        indent_txt = ' ' * indent
        if isinstance(handler, logging.StreamHandler):
            extra_info = ', stream={0}'.format(handler.stream)
        else:
            extra_info = ''
        print >>sys.stderr, 'H{0}{1}({2}): level={3}{4}'.format(
            indent_txt, handler.get_name(), handler.__class__.__name__,
            handler.level, extra_info)
        for filter in handler.filters:
            self.__display_filter(indent + 1, filter, detail)

    def __recurse_list(self, indent, logger, detail):
        """
        Print the passed in logger, its handlers, and then recurse on other
        loggers under its space.
        """
        indent_txt = ' ' * indent
        print >>sys.stderr, 'L{0}{1}: level={2}'.format(indent_txt, logger.name, logger.level)
        for handler in logger.handlers:
            self.__display_handler(indent + 1, handler, detail)
        for lg_name, lg_obj in logging.Logger.manager.loggerDict.items():
            if isinstance(lg_obj, logging.PlaceHolder):
                continue
            if lg_obj.parent == logger:
                self.__recurse_list(indent + 3, lg_obj, detail)

    def __do_list(self, detail):
        """
        Entry point for listing state of python logging stuff. Just grabs the root
        and jumps into recursing off of it.
        """
        lg = logging.root
        self.__recurse_list(0, lg, detail)

    def __fail_level_parse(self, level_arg):
        """
        Common error routine for not-understanding a specified level
        """
        valid_nums = []
        valid_names = []
        for lv_key in logging._levelNames.keys():
            if isinstance(lv_key, int):
                valid_nums.append(lv_key)
            else:
                valid_names.append(lv_key)

        self.__parser.error(
            "Invalid level '{0}'. Valid numbers: {1}, names: {2}".format(
                level_arg, valid_nums, valid_names))

    def __parse_level(self, level):
        """
        Util method to turn any passed in level (int or string) into
        its number AND name
        """
        levelno = None
        try:
            levelno = int(level)
        except ValueError:
            pass
        if levelno is None:
            # could not parse, so should be a name?
            # Note: we need to handle that foo_2 == foo, BUT there won't be
            #  a mapping inside logging for foo_2. (It would cause 'FOO' to always show up in
            #  the logs as 'FOO_5'. Still iffy on if it should or shoudn't, but that's why
            #  we check and strip _2 here!)
            str_level = str(level)
            if str_level.endswith('_2'):
                str_level = str_level[:-2]   # hack off _2!

            levelno = logging.getLevelName(str_level)
            if not isinstance(levelno, int):
                self.__fail_level_parse(level)

        level_name = logging.getLevelName(levelno)
        bad_name = 'Level {0}'.format(levelno)
        if level_name == bad_name:
            self.__fail_level_parse(level)
        return levelno, level_name

    def __find_loggers(self, search_lg_name):
        """
        Method to search loggers for a matching name. We allow regex, but also
        do 'glob' style expansion of '*' to '.*' and stick a '$' on the end.
        Note that re.match has to match from the start of the string, so no '^' is
        needed.
        """
        regex_form = search_lg_name.replace('*', '.*') + '$'
        matcher = re.compile(regex_form)
        logger_list = []
        for lg_name, lg_obj in self.__loggers_by_name.items():
            if matcher.match(lg_name):
                logger_list.append(lg_obj)

        if len(logger_list) == 0:
            self.__parser.error(
                "Could not locate any loggers matching '{0}'".format(
                    search_lg_name))
        return logger_list

    def __do_logger_settings(self, logger_level_list):
        """
        Routine to look through the list of options like 'infra.run' 'DEBUG_2'.
        For each one, we search for loggers matching the name (wildcards are allowed) and
        for each of those, go in and set the level of the logger to the requested
        level. Remember loggers are independent of handlers. FIRST a candidate message
        has to get past a logger before being considered by a handler or propagated up.
        """
        for lg_name, level in logger_level_list:
            levelno, level_name = self.__parse_level(level)
            target_loggers = self.__find_loggers(lg_name)
            for target_logger in target_loggers:
                target_logger.setLevel(levelno)

    def __find_handlers(self, search_hd_name):
        """
        Locate handlers matching a specific name. It is basically a regex with an
        extra 'glob' like mode added along with a '$' to match EOS. Note that regex's
        'match()' will only match the start of a string.
        """
        regex_form = search_hd_name.replace('*', '.*') + '$'
        matcher = re.compile(regex_form)
        handler_list = []
        for hd_name, hd_obj in self.__handlers_by_name.items():
            if matcher.match(str(hd_name)):
                handler_list.append(hd_obj)

        if len(handler_list) == 0:
            self.__parser.error(
                "Could not locate any handlers matching '{0}'".format(
                    search_hd_name))
        return handler_list

    def __update_handler(self, handler, for_loggers, levelno, file_pat=None):
        """
        Routine to update a single handler by adding a filter to it that is
        includes the level, optional file-pattern, and a list of all the loggers
        that feed into the handler. The filter will "take over" threshhold handling
        of any handler we want to use the filter on. Otherwise, if the handler's level is
        set higher than our per-logger override, the check won't reach our
        filter. Of course, at the same time, we don't want the behavior to
        change for handler + logger combinations we aren't trying to override!
        Note: only one filter has to return a False to kill emitting a
          record, so it doesn't hurt to "overwrite" the level multiple times.

        The option "file_pat" param is used to limit output to only files matching that pattern.
        """
        for_names = []
        for logger in for_loggers:
            for_names.append(logger.name)

        orig_level = handler.level
        name = 'Filter({0}@{1})'.format(for_names, levelno)
        filter = _LoggingConfigFilter(for_names, levelno, orig_level, name,
                                      file_pat=file_pat)
        handler.addFilter(filter)
        handler.setLevel(logging.NOTSET)

    def __do_a_handler(self, log_and_handler, level, file_pat=None, bump_loggers=False):
        """
        Handles changing levels on a handler or handlers.

        The 'log_and_handler' is the name of the handler (possibly with wildcarding)
        and optionally the list of loggers to restrict the change to. By default,
        changing the handler level will "discover" all the loggers that point to it. In either
        case, that list of loggers is passed into each __update_handler call so the logging
        will be able to discern if it should act or not.

        Finally, the "bump_loggers" option, which is used by the combo option,
        will cause us to go back and drag the logger threshholds as well if set.
        """
        levelno, level_name = self.__parse_level(level)
        if ':' in log_and_handler:
            hd_name, lg_name = log_and_handler.split(':', 1)
        else:
            hd_name = log_and_handler
            lg_name = '*'
        target_handlers = self.__find_handlers(hd_name)
        for_loggers = self.__find_loggers(lg_name)
        for target_handler in target_handlers:
            self.__update_handler(target_handler, for_loggers, levelno)
        if bump_loggers:
            for logger in for_loggers:
                if logger.level > levelno:
                    logger.setLevel(levelno)

    def __do_handler_settings(self, handler_level_list, bump_loggers=False):
        """
        Entry point for walking handler and setting handler thresholds. It is also used
        for "combo" settings via the "bump_loggers" param. This routine is just in
        charge of walking the possible list of settings from the arg-parser though.
        """
        for log_and_handler, level in handler_level_list:
            self.__do_a_handler(log_and_handler, level, bump_loggers=bump_loggers)

    def __do_set_file_level(self, set_file_settings):
        """
        Cranks up the output for a regex/glob file-name. It can be targeted just like
        a combo setting.
        """
        if len(set_file_settings) > 3:
            self.__parser.error('Too many values for --set-file-level')
        if len(set_file_settings) == 1:
            set_file_settings.append('*')
        if len(set_file_settings) == 2:
            set_file_settings.append('DEBUG_9')
        file_pat, log_and_handler, level = set_file_settings
        self.__do_a_handler(log_and_handler, level, file_pat, True)

    def __build_ref_lists(self):
        """
        Build up easy-to-use lists of loggers and handlers.
        """
        ll = {}
        hl = {}
        loggers = dict(logging.Logger.manager.loggerDict)
        loggers[''] = logging.getLogger('')
        loggers['root'] = logging.getLogger('')
        for lg_name, lg_obj in loggers.items():
            if not isinstance(lg_obj, logging.PlaceHolder):
                ll[lg_name] = lg_obj
                for handler in lg_obj.handlers:
                    hl[handler.get_name()] = handler
        self.__loggers_by_name = ll
        self.__handlers_by_name = hl

    def process_parsed(self, optargs):
        """
        This method needs to be called -after- the parser is run with the results dictionary.
        It basically coordinates which filters to build up, with the bulk of the
        work being done in sub-methods.
        """
        # Build up handy list of map of loggers and handlers
        self.__build_ref_lists()
        # If the user set any logger values, deal with them.
        self.__do_logger_settings(optargs.set_logger_level_list)
        # If the user set any handlers values, now deal with them.
        self.__do_handler_settings(optargs.set_handler_level_list)
        # Now the combos (auto-magic logger + handlers tweaks)
        self.__do_handler_settings(optargs.set_combo_level_list, True)

        # And finally the kind of "meta" option of just turning the volume up
        # on a single file.
        if optargs.set_file_level is not None:
            self.__do_set_file_level(optargs.set_file_level)

        # And last, does the user want to see the settings. We do this here, so if they
        # opt for a list, they can see if AFTER the settings are made. We still
        # exit, however.
        if optargs.list_logging:
            self.__do_list(optargs.list_logging_level)
            sys.exit(0)
