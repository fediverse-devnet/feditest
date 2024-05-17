"""
Reporting functionality
"""

import logging
import logging.config
import sys
import traceback

logging.config.dictConfig({
    'version'                  : 1,
    'disable_existing_loggers' : False,
    'formatters'               : {
        'standard' : {
            'format' : '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            'datefmt' : '%Y-%m-%dT%H:%M:%SZ'
        },
    },
    'handlers' : {
        'default' : {
            'level'     : 'DEBUG',
            'formatter' : 'standard',
            'class'     : 'logging.StreamHandler',
            'stream'    : 'ext://sys.stderr'
        }
    },
    'loggers' : {
        '' : { # root logger -- set level to most output that can happen
            'handlers'  : [ 'default' ],
            'level'     : 'WARNING',
            'propagate' : True
        }
    }
})
LOG = logging.getLogger( 'feditest' )

def set_reporting_level(n_verbose_flags: int) :
    if n_verbose_flags == 1:
        LOG.setLevel(logging.INFO)
    elif n_verbose_flags >= 2:
        LOG.setLevel(logging.DEBUG)

def trace(*args):
    """
    Emit a trace message.

    args: the message or message components
    """
    if LOG.isEnabledFor(logging.DEBUG):
        LOG.debug(_construct_msg(True, False, args))


def is_trace_active() :
    """
    Is trace logging on?

    return: True or False
    """
    return LOG.isEnabledFor(logging.DEBUG)


def info(*args):
    """
    Emit an info message.

    args: msg: the message or message components
    """
    if LOG.isEnabledFor(logging.INFO):
        LOG.info(_construct_msg(False, False, args))


def is_info_active():
    """
    Is info logging on?

    return: True or False
    """
    return LOG.isEnabledFor(logging.INFO)


def warning(*args):
    """
    Emit a warning message.

    args: the message or message components
    """

    if LOG.isEnabledFor(logging.WARNING):
        LOG.warning(_construct_msg(False, LOG.isEnabledFor(logging.DEBUG), args))


def is_warning_active():
    """
    Is warning logging on?

    return: True or False
    """
    return LOG.isEnabledFor(logging.WARNING)


def error(*args):
    """
    Emit an error message.

    args: the message or message components
    """
    if LOG.isEnabledFor(logging.ERROR):
        LOG.error(_construct_msg(False, LOG.isEnabledFor(logging.DEBUG), args))


def is_error_active():
    """
    Is error logging on?

    return: True or False
    """
    return LOG.isEnabledFor(logging.ERROR)


def fatal(*args):
    """
    Emit a fatal error message and exit with code 1.

    args: the message or message components
    """

    if args:
        if LOG.isEnabledFor(logging.CRITICAL):
            LOG.critical(_construct_msg(False, LOG.isEnabledFor(logging.DEBUG), args))

    raise SystemExit(255) # Don't call exit() because that will close stdin


def is_fatal_active():
    """
    Is fatal logging on?

    return: True or False
    """
    return LOG.isEnabledFor(logging.CRITICAL)


def _construct_msg(with_loc, with_tb, *args):
    """
    Construct a message from these arguments.

    with_loc: construct message with location info
    with_tb: construct message with traceback if an exception is the last argument
    args: the message or message components
    return: string message
    """
    if with_loc:
        frame  = sys._getframe(2) # pylint: disable=protected-access
        loc    = frame.f_code.co_filename
        loc   += '#'
        loc   += str(frame.f_lineno)
        loc   += ' '
        loc   += frame.f_code.co_name
        loc   += ':'
        ret = loc
    else:
        ret = ''


    def m(a):
        """
        Formats provided arguments into something suitable for log messages.

        a: the argument
        return: string for the log
        """
        if a is None:
            return '<undef>'
        if callable(a):
            return str(a)
        if isinstance(a, OSError):
            return type(a).__name__ + ' ' + str(a)
        return a

    args2 = map(m, *args)
    ret += ' '.join(map(str, args2))

    if with_tb and len(*args) > 0:
        *_, last = iter(*args)
        if isinstance(last, Exception):
            ret += ''.join(traceback.format_exception(type(last), last, last.__traceback__))

    return ret
