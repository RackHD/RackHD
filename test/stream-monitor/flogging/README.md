# (FIT) Infra-structure logging component.

This logging system is part of the overall 'stream_monitor' nose plugin, but can
in theory work independently of that. This document starts with a set of examples
for how someone working with run_test.py might accomplish different different
use-cases. After that, it goes on to describe the basic structure of
the logging system, the options available to control it, and how to use it within FIT
tests.

## Cheat-sheet of example run_test.py uses
This is a "quick start" section to give you a set of "if you want to do this, type this." You may wish to skim two sections following this
one for an overview of how python's logging system works, and how that is used for the testing system. A minimal set of information to use this is:

* the logging system generates files in 'logging_output/run_<timedate-stamp.d' with a symlink from 'log_output/run_last.d' to the most recent.
    * The files 'infra_run.log', 'infra_data.log', 'test_run.log', and 'test_data.log' each contain DEBUG and higher log data for each of those loggers respectively. These are the "main logger" files.
    * The file 'all_all.log' contains all the lines from those four logs.
    * The file 'console_capture.log' contains the same data sent to the real console. As an example, the contents of this file should match what is seen in the console-output for a Jenkins job.
* console output (including the 'console_capture.log' mentioned in the files bullets) is limited to INFO and above. It is meant to show high-level status/flow by default, with the main logger files containing more detailed diagnostic/debug information for post-morterm and debug.
* levels are based on syslog style DEBUG, INFO, WARNING, ERROR, and CRITICAL levels, but have been expanded:
    * There are now levels like {name}_0, {name}_1, through {name}_9. For example DEBUG_0, DEBUG_1, INFO_5 and so on.
    * Each base name maps to {name}_5. For example 'INFO' and 'INFO_5' are the same.

The following are "if you want to see _this_, use a command like _this_" recipes. In some cases, there is more
than one way to accomplish the goal, often including use of the run_test.py's "-v" option. The latter may change
some as RAC-3984 is persued, but the goal of that ticket is to preserve this simple for of the current
"-v" option and also make other "short cuts" available.

### "I want to have every log statement show up in the log files and on the console"
        python run_tests.py -stack <stack> --sm-set-combo-level 'console.*' DEUBG_9
        python run_tests.py -stack <stack> -v 9

### "I want to increase the amount of information stored to the main log files"
        python run_tests.py -stack <stack> --sm-set-logger-level 'infra.*|test.*' DEUBG_9

### "I want to capture a lot more info from a specific intermittent test failure"
note: an upcoming story will add the ability to specify a specific test. At this time, the granularity is limited to
a file or files.
        python run_tests.py -stack <stack> --sm-set-file-level 'tests/rackhd11/test_rackhd11_api_catalogs.py'

### "I'm developing new tests and just want to see everything while I'm doing that"
        python run_tests.py -stack <stack> -test tests/rackhd11/test_rackhd11_api_catalogs.py:rackhd11_api_catalogs.test_api_11_catalog --sm-set-combo-level 'console.*' DEBUG_9
        python run_tests.py -stack <stack> -test tests/rackhd11/test_rackhd11_api_catalogs.py:rackhd11_api_catalogs.test_api_11_catalog -v 9

### "What does the help information about the '-v' option really mean?"
There is only so much info that can be put into a --help line. The following
shows a breakout of what the different '-v n' shortcuts mean. Note that currently, these are _also_
tied to the older verbosity based print statements. These are being converted, but currently
the output will be a mix of stdout/print data and logging messages. _The descriptions
here are for the logging entries_. So, for example, '-v 0' is actually the default
level of logging output as described in this section. '-v 1' is the option default and shows
default level output via the unconverted verbosity based print statements. In terms of mapping
to logging, it is the same as '-v 0'.
* -v 0 : no special output.
* -v 1 : default for unconverted verbosity based print statements. Same as -v 0 for logging.
* -v 2 : turn console display of infra.run and test.run to the level DEBUG. This should be test and infra flow logic.
* -v 4 : turn console display of test.data to the level DEBUG. This should add rest calls and status information.
* -v 6 : turn console display of infra.data to the level DEBUG. This should add things like ipmi and ssh information.
* -v 9 : turn console and log file display of all areas to the level of DEBUG_9. This basically turns on _everything_.

Note that the levels are additive: -v 6 implies -v 4 and -v 2. Options not shown here "round down" to the nearest value. For example, -v 5 effectively means -v 4.

Notice: if you are developing tests using '-v 9' (or any "-v n") and find yourself altering or removing log statements
to tune the volume of logs produced, _please don't_. Instead take the time to read the rest of this file and learn
more about how to segment the logging information and levels. The "-v" option is an extremely
powerful tool for quickly getting access to all the log information, but it is primarily a
test developer or feature developer running specific tests. Altering the logging content,
detail, and volume to fit that single use case, breaks many of the other use cases.

## Basic structure

The infra-logging system is meant to make instrumenting, and then debugging FIT tests
easier at both all points in the life-cycle of test development:
- Gobs of information while writing the a test, either directly to console and/or within log files
- Basic flow information, to the console when executing in a Jenkins type environment or by a non-test developer running the suite against their code during development.
- More detailed debug info located in log files for that same Jenkins type environment.

Combined with the stream-monitor plugin, the system will, when RAC-3849 is implemented,
also "raise" the more detailed info from the log files to console output on test failure/errors.

## Brief introduction to how python logging _works_
These concepts are buried within the python logging documentation, but require some
time to pull out in any meaningful way. This section is a brief overview of the
core structures and terminology:

* A "logger" is a named entity that is really the entry point for _doing_ the logging. Important properties:
    * It has a name. The name can be split up with '.'s to create hierarchies.
    * It is where one starts a log message from. For example a_logger.debug("message") or a_logger.info("message")
    * It can have zero or more "handler"s attached to it (see below).
    * It has a "level" threshold. If the level of the log-message is >= to the logger, it will process the message
      by checking the message against each handler. It will also "climb" (progagate)
      messages to less specific loggers. For example, if 'foo.bar' accepts the message, the system will then
      check logger 'foo', and finally the 'root' logger or ''.
* A "handler" is a named entity that is responsible for emitting the a message a logger matched. Properties:
    * It also has a name, though it doesn't have any of the hierarchy abilities.
    * More than one logger can be pointing to it. (or no loggers, but it will never do anything in that case!)
    * It also has a level and if the message's level less, the handler won't process the message.
    * It may also have 0 or more "filter"s (see below). Each filter is checked against the message and can
      indicate if processing should continue or not in this handler. Filters can do other things, as described
      below
    * It can have a 'formatter' attribute that describes how the line is printed.
    * It will also have handler-type specific information. For example:
        * a "RotatingFileHandler" requires a name and may also include overrides to rotation settings.
        * a "StreamHandler" will contain the stream-io information required to write to things like stdout.
* A "filter" provides two bits of functionality:
    * It can add or alter properties attached to the message being logged before the formatter is used. For example,
      it could add a '.greenlet_name' or trim off the common part of '.filename'.
    * It can do further checks to see if the handler should emit the message or not, returning False if it
      should not, or True if it should continue looking through more filters. Filters that just alter/add
      properties always return True.

## A note on 'levels'
The default syslog based loglevels are limited to 'CRITICAL', 'ERROR', 'WARNING, 'INFO', and 'DEBUG', and suffer
the same problem all syslog derived system face of only having one level of, say, DEBUG.

Luckily, the values assigned to the level names are DEBUG=10, INFO=20, and so on. The infra-logging system takes
advantage of this, and adds entries for each primary level plus _0, _1, _2, through _9 where _5 is the same as the
primary. I.E. DEBUG_5 is the same as plain DEBUG. So, a test writer can use the 'test.run' logger.debug_1(message)
to indicate a message more verbose than logger.debug_0. Under default settings, this means that data flowing
to the main log files include DEBUG_0 to DEBUG_5, leavning _6 to _9 for levels of debug/diagnostic information
considered too verbose for including on every run. Note that because the logging is still syslog-like in
its core, however, changing the threshhold level of say the root logger to 'DEBUG', will also mean it starts
matching INFO_1, INFO_2 ... INFO_9.

## How the infra-logging system uses this

The infra-logging system defines four main loggers, a root logger, seven handlers, and one filter:

* Loggers:
    * The main loggers, 'infra.run', 'infra.data', 'test.run', and 'test.data'. Each of these:
        * Has a level of 'DEBUG'.
        * Points to its own log-file handler. This handler doesn't test for a level.
        * Points to a second log-file handler that the other three main loggers also point to. Again, with no
          level test, so if the logger matches, the line gets written to its specific file and to the combined file.
    * A root logger. This logger ends up handling both propegation from the main loggers, and from any other
      logger that gets defined elsewhere in the system. By default, it is set at 'INFO'. It has two handlers:
        * 'console', which sends to stdout. 'console' also has a level of 'INFO'.
        * 'console-capture', which writes to a file in the logging directory. This allows capture of the main
          console from a run even if the stdout one was not piped to a file.

The handlers were covered in place, and the filter is attached to every handler to add more fields.

# Controlling logging:
The following nose options are available to control and examine the loggers:


    listing log settings:
        --sm-list-logging   list logging settings
        --sm-list-level=LIST_LOGGING_LEVEL
                            detail level if --list-logging is used

      setting log options:
        note: both 'logger-name's and 'handler-name's can contain wild-card
        characters to match multiple items.

        --sm-set-logger-level=('logger-name', 'level-name-or-value')
                            Set a logger's capture threshold. Loggers are
                            evaluated before handlers.
        --sm-set-handler-level=('handler-name[:logger-name]', 'level-name-or-value')
                            Set a handler's capture threshold.
        --sm-set-combo-level=('handler-name[:logger-name]', 'level-name-or-value')
                            Set a handler's capture threshold AND all loggers
                            feeding it.
        --sm-set-file-level=('file-pattern', '[handler-name[:logger-name] [level-name-or-value]]')
                            Same as --sm-set-combo-level, but restricts the change
                            in output to only the files that match the file-
                            pattern

## The 'set' options:
The following goes through each option and explains what it does:
        --sm-set-logger-level=('logger-name', 'level-name-or-value')
                            Set a logger's capture threshold. Loggers are
                            evaluated before handlers.

This will change the logger level. For example, '--sm-set-logger-level test.run DEBUG_5' will change the logger level
from DEBUG(_0) to DEBUG_5. I.E. DEBUG_6 will still be dropped by the test.run logger. The way things are wired,
this only impacts the level of messages flowing to test_run.log and combined_all_all.log. The messages would still be
dropped by the root-logger, since it is at INFO.

Note that the logger name can be wild-carded: 'test.*' or 'test*' to change both test.run and test.data, or '*.data' to raise up the volume of data dumps.

    --sm-set-handler-level=('handler-name[:logger-name]', 'level-name-or-value')
                        Set a handler's capture threshold.

But what if you wanted to have more than just DEBUG flow to stdout? This option seems like it would work:
'--sm-set-handler-level console DEBUG'. This will actually have less impact than you would think, since
both the root logger AND the console handler have a level threshold of 'INFO'.
The actual usefull application of this option would be to lower levels '--sm-set-handler-level console WARNING'.
This would mean only warnings and above to the console, while still sending INFO and above to the
console_capture file.

Mostly, this is here for completeness, and for use 'behind the scenes' on the more usefull next option:

    --sm-set-combo-level=('handler-name[:logger-name]', 'level-name-or-value')
                        Set a handler's capture threshold AND all loggers
                        feeding it.

Doing a '--sm-set-combo-level console DEBUG' will go and change the handler level for 'console' AND all loggers
feeding into it. Because 'console' is attached to the root logger, this ends up override ALL the
loggers (that had been created at this point. That is a key limitation). Of course, this means that the console is
being spammed with DEBUG output from everything. '--sm-set-combo-level console*:*.run DEBUG_5' will have the
affect of of routing 'infra.run', and 'test.run' at DEBUG_5 to both the console and console_capture.

Finally:
    --sm-set-file-level=('file-pattern', '[handler-name[:logger-name] [level-name-or-value]]')
                       Same as --sm-set-combo-level, but restricts the change
                       in output to only the files that match the file-
                       pattern

This last option can be used to target increased (or decreased) output for a specific file or files. The handler and logger
name parts are just like in the combo. The file pattern is a regex applied against the filename seen in the
output records.

## The 'list' options:
Currently, only the flag-option '--sm-list-logging' has any effect, and just dumps some basic information
about the loggers, handlers, and filters before existing.  '--sm-list-level=#' currently has no impact on the
amount of detail provided for each item, but is the placeholder for that functionality.


# How to use:
This section will cover how to intstrument the test and test-infrastructure code and the general rules, etc.

A very basic sketch is:
        '''
        Some file.py
        '''
        import flogging

        logs = flogger.get_loggers()


The "logs" instance here provides both default and advanced access to the main loggers. For example:
        logs.debug("My test is doing this")
will use the 'test.run' logger as its base to log from. The "logs" instance supports all the normal logger
methods as well as the expanded ranges. For example: logs.info(), logs.info_1, logs.critical() and so on.

It also contains the following:
* .irl, which is the 'infra.run' logger instance.
* .idl, which is the 'infra.data; logger instance.
* .trl, which is _also_ the 'test.run' logger instance. Technically 'logs' delegates all access like .debug and such to .trl to handle.
* .tdl, which is the 'test.data' logger instance.
* .data_log, which is a synonym for the 'test.data' logger instance.

These different loggers should be used as follows:
* test.run via logs.trl (or just plain loggers) should explain what _your_ test is doing. It's path.
* test.data via logs.tdl (or logs.data_log) should be data being moved around as _part_ of the test. This could be REST data and response for a service being tested. It should _not_ be REST calls that are not part of the service under test, if possible. Nor should it include the more infra-structure like data such as ssh traffic for remote commands that aren't _what_ is being tested.
* infra.run via logs.irl is for logic flow of testing infrastructure code.
* infra.data via logs.idl is for bulk data being moved around. The output from a pyexpect based ssh would be a perfect example of this.

In general, use 'INFO' for core flow. 'starting test A' and so on. *most of these should be in infra.run*. Exceptions
to that would be some form of progress information for longer running test-pieces. For example "Starting node 1 of 5"
or such.

Remember that .debug is captured to the logfiles, jenkins, and when RAC-3849 is done, .debug will be sent
to console output on an error or failure.
