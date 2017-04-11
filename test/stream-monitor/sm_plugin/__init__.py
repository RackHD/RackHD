"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
from stream_monitor import StreamMonitorPlugin, smp_get_stream_monitor, smp_get_stream_monitor_plugin


def AMQPStreamMonitor():
    """
    This makes the plugin-based-singleton look more like a normal
    import.
    """
    return smp_get_stream_monitor('amqp')


__all__ = [StreamMonitorPlugin, smp_get_stream_monitor_plugin, smp_get_stream_monitor,
           AMQPStreamMonitor]
