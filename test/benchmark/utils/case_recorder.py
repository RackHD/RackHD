import os
import time
import json

"""
Class to manage case_info file
"""

class caseRecorder(object):
    def __init__(self, path):
        self.__path = path
        self.__str_time = 'time marker'
        self.__write_basic_info()

    def __write_case_info(self, catalog, key, value):
        if not os.path.exists(self.__path):
            os.makedirs(self.__path)

        try:
            pfile = open(os.path.join(self.__path, 'case_info.log'), 'r+')
        except IOError:
            # Create a new file
            pfile = open(os.path.join(self.__path, 'case_info.log'), 'a+')

        try:
            json_data = json.load(pfile)
        except ValueError:
            json_data = {}

        if not json_data.has_key(catalog):
            json_data[catalog] = {}

        if key is None:
            json_data[catalog] = value
        else:
            json_data[catalog][key] = value

        pfile.seek(0)
        pfile.write(json.dumps(json_data, indent=4, separators=(',',': ')))
        pfile.truncate()
        pfile.close()

    def __write_basic_info(self):
        items = self.__path.split('/')
        self.__write_case_info('log path', None, items[len(items) - 2])
        self.__write_case_info('case name', None, items[len(items) - 1])

    def __get_current_time(self):
        return time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(time.time()))

    def write_node_number(self, num):
        self.__write_case_info('node count', None, num)

    def write_interval(self, interval):
        self.__write_case_info('interval', None, interval)

    def write_start(self):
        self.__write_case_info(self.__str_time, 'start', self.__get_current_time())

    def write_end(self):
        self.__write_case_info(self.__str_time, 'end', self.__get_current_time())

    def write_event(self, key):
        self.__write_case_info(self.__str_time, key, self.__get_current_time())
