import os
import re
import datetime
import json

# Log files to be parsed
filename_atop = "cpu_mem_net_disk.log"
filename_process = "pid.log"
filename_caseinfo = "case_info.log"
filename_summary = "summary.log"
filename_mongo_document = "db_document.log"
filename_mongo_disk = "db_disk.log"

# Generated output files that will be used by front-end code
filename_atop_summary_js = "atop_summary.js"
filename_mongo_doc_summary_js = "db_doc_summary.js"
filename_mongo_disk_summary_js = "db_disk_summary.js"
filename_mongo_document_js = "db_document.js"
filename_caseinfo_js = "case_info.js"
filename_compare_list_js = "compare_list.js"

# The column line definition on the atop log file
ATOP_LINE_COL = [
    "PID",
    "SYSCPU",
    "USRCPU",
    "VSIZE",
    "RSIZE",
    "RDDSK",
    "WRDSK",
    "RNET",
    "SNET",
    "RNETBW",
    "RNETBW_U",
    "SNETBW",
    "SNETBW_U",
    "CPU"
]

# The matrix that can be parsed from atop log file
ATOP_MATRIX = [
    "SYSCPU",
    "USRCPU",
    "VSIZE",
    "RSIZE",
    "RDDSK",
    "WRDSK",
    "RNET",
    "SNET",
    "RNETBW",
    "SNETBW",
    "CPU"
]

# The matrix that can be parsed from mongo document log file
MONGO_DOCUMENT_MATRIX = [
    "dataSize",
    "storageSize"
]

# Parser for mongo document log file.
# The log file look like:
#
# {
# 	"dataSize" : 6286556,
# 	"storageSize" : 12083200,
# }
# {
# 	"dataSize" : 6286556,
# 	"storageSize" : 12083200,
# }
def parse_mongo_document(input_file):
    mongo_doc_records = {}
    for matrix in MONGO_DOCUMENT_MATRIX:
        mongo_doc_records[matrix] = []

    with open(input_file, 'r') as f:
        for line in f:
            for matrix in MONGO_DOCUMENT_MATRIX:
                if line.find(matrix) >= 0:
                    splited_line = split_line_by_colon(line)
                    mongo_doc_records[matrix].append(int(splited_line[1]))
                    break
    return mongo_doc_records

# Parser for mongo disk log file
# The log file look like:
# {
# 	"fileSize" : 201326592,
# 	"nsSizeMB" : 16,
# }
# 3.1G	/var/lib/mongodb/journal/
def parse_mongo_disk(input_file):
    mongo_disk_records = {}

    with open(input_file, 'r') as f:
        for line in f:
            if line.find('fileSize') >= 0:
                splited_line = split_line_by_colon(line)
                mongo_disk_records["fileSize"] = int(splited_line[1])
                continue
            if line.find('nsSize') >= 0:
                splited_line = split_line_by_colon(line)
                mongo_disk_records["nsSize"] = int(splited_line[1]) * 1024 * 1024
                continue
            if line.find('journal') >= 0:
                splited_line = split_line_by_space(line)
                mongo_disk_records["journal"] = parse_size(splited_line[0])
                continue
    return mongo_disk_records

# Parser for case info log file
# The log file look like:
# {
# 	"interval": 1,
# 	"log path": "20160323-032739",
# 	"case name": "poller",
#     "time marker":
#     {
#         "start":"2016/03/16 11:33:57",
#         "node finish": "2016/03/16 11:38:57",
#         "end":"2016/03/16 11:43:57"
#     }
# }
def parse_case_info(filename):
    with open(filename, 'r') as f:
        case_info_json = json.load(f)
    # print(case_info_json)
    return case_info_json

# Parser for CPU time string from ATOP log
def parse_cpu_time(time):
    #return number of micro second
    # time may be '12m53s', or '0.01s'
    hour_match = re.findall(r'\d+h', time)
    minute_match = re.findall(r'\d+m', time)
    sec_match = re.findall(r'[0-9]+\.*[0-9]*s', time)

    if len(hour_match) == 0:
        hour = 0
    else:
        hour = int(hour_match[0][:-1])

    if len(minute_match) == 0:
        minute = 0
    else:
        minute = int(minute_match[0][:-1])

    if len(sec_match) == 0:
        sec = 0
    else:
        sec = float(sec_match[0][:-1])

    # Return time in unit of ms (microsecond)
    time_ret = int((sec + (minute * 60) + (hour * 3600)) * 1000)
    return time_ret

# Parser for memory of disk string from ATOP log
def parse_size(size):
    # return size of byte of memory usage, or disk usage
    # size may be '1.2T', '1.3G', '348.2M', '95488K', or '0K'
    size_match = re.findall(r'[0-9]+\.*[0-9]*[TGMK]', size)
    size_str = size_match[0]

    scale = 1
    if size_str[-1] == 'T':
        scale = 1000000000000
    elif size_str[-1] == 'G':
        scale = 1000000000
    elif size_str[-1] == 'M':
        scale = 1000000
    elif size_str[-1] == 'K':
        scale = 1000

    size = float(size_str[:-1])
    # Return time in unit of BYTE
    size_ret = int(size * scale)
    return size_ret

# Parser for network IO string from ATOP log
def parse_network_io(io):
    # return the amount of network io activity
    # size may be '7515', '104e4', or '989e3'
    io_match = re.findall(r'(?P<base>[0-9]+)e*(?P<exponent>[0-9]*)', io)
    io_str_base = io_match[0][0]
    io_str_exponent = io_match[0][1]

    io_base = int(io_str_base)
    if io_str_exponent == '':
        io_exponent = 0
    else:
        io_exponent = int(io_str_exponent)

    # Return number of IOs
    io_ret = io_base * pow(10, io_exponent)
    return io_ret

# Parser for network bandwidth string from ATOP log
def parse_network_bw(bw, unit):
    # return the network bandwidth in unit of bps (byte per second)
    # bw may be '13' or '989'
    # unit may be 'Kbps', 'Mbps', 'Gbps' or 'Tbps'
    scale = 1
    if unit == 'Tbps':
        scale = 1000000000000
    elif unit == 'Gbps':
        scale = 1000000000
    elif unit == 'Mbps':
        scale = 1000000
    elif unit == 'Kbps':
        scale = 1000

    # Return bandwidth in unit of bps (byte per second)
    bw_ret = int(bw) * scale
    return bw_ret

# Write summary data to js file that will be used by front-end code
# Time stamp is added as a prefix to var to avoid conflict
# It take data from different sources
# Output will look like:
#
# var 20160323_032739_atop_statistics =
# {
#     "beam.smp": {
#         "RDDSK": {
#             "min": 0,
#             "max": 0,
#             "sum": 0,
#             "avg": 0.0
#         },
#         "RNETBW": {
#             "min": 0,
#             "max": 251000,
#             "sum": 1065000,
#             "avg": 295.5870108243131
#         }
#     },
#     "on-http": {
#             "RDDSK": {
#                 "min": 0,
#                 "max": 0,
#                 "sum": 0,
#                 "avg": 0.0
#             }
#     }
# }
# var 20160323_032739_mongo_document_statistics = {}
# var 20160323_032739_mongo_disk_statistics = {}
def write_summary_to_js(statistic_data,
                        var_name,
                        case_information,
                        output_filename):
    timestamp = case_information["log path"].replace('-', '_')

    with open(output_filename, 'w') as f:
        f.write('var ' + var_name + '_' + timestamp + ' = \n')
        json_str = json.dumps(statistic_data, indent=4)
        f.write(json_str)

def write_case_info_to_js(case_information, output_filename):
    with open(output_filename, 'w') as f:
        f.write('var case_info = \n')
        json_str = json.dumps(case_information, indent=4)
        f.write(json_str)

# Calculate statistic values from ATOP parsed result
# The return object will look like:
# {
#     "RSIZE": {
#         "on-syslog": {
#             "max": 74600000,
#             "min": 74600000,
#             "avg": 74600000.0
#         },
#         "on-taskgraph": {
#             "max": 100900000,
#             "min": 98300000,
#             "avg": 99428863.72467388
#         }
#     },
#     "RNET": {
#         "on-syslog": {
#             "max": 0,
#             "sum": 0,
#             "min": 0,
#             "avg": 0.0
#         },
#         "on-taskgraph": {
#             "max": 254,
#             "sum": 4986,
#             "min": 0,
#             "avg": 1.3838467943380517
#         }
#     }
# }
def calc_max_min_avg_atop(matrix_data):
    matrix_need_no_sum = [
        "VSIZE",
        "RSIZE",
        "RNETBW",
        "SNETBW",
        "CPU"
    ]
    max_min_avg_ret = {}
    for matrix in ATOP_MATRIX:
        max_min_avg_ret[matrix] = {}

    for process in matrix_data.keys():
        matrix_list = {}

        for matrix in ATOP_MATRIX:
            matrix_list[matrix] = []

        records = matrix_data[process]

        for record in records:
            for matrix in ATOP_MATRIX:
                matrix_list[matrix].append(record[ATOP_MATRIX.index(matrix)])

        for matrix in ATOP_MATRIX:
            if matrix in matrix_need_no_sum:
                max_min_avg_ret[matrix][process] = calc_statistic(matrix_list[matrix], True)
            else:
                max_min_avg_ret[matrix][process] = calc_statistic(matrix_list[matrix], False)

    return max_min_avg_ret

# Calculate statistic values from mongo document parsed result
# The return object will look like:
# {
#     "dataSize": {
#         "max": 1234,
#         "min": 12,
#         "avg": 111,
#         "sum": 12132
#     },
#     "storageSize": {
#         "max": 1234,
#         "min": 12,
#         "avg": 111,
#         "sum": 12132
#     }
# }
def calc_max_min_avg_mongo(matrix_data):
    max_min_avg_ret = {}
    for matrix in matrix_data.keys():
        max_min_avg_ret[matrix] = calc_statistic(matrix_data[matrix], True)
    return max_min_avg_ret

# Return a object with the max/min/sum/average value of a list.
def calc_statistic(list_data, no_sum = False):
    ret_val = {}

    ret_val["max"] = max(list_data)
    ret_val["min"] = min(list_data)
    list_sum = sum(list_data)
    ret_val["avg"] = list_sum/(float(len(list_data)))
    if not no_sum:
        ret_val["sum"] = list_sum

    return ret_val

# Write parsed atop result to js that can be used for generating graphs in
# front-end code
# Time stamp is added as a prefix to var to avoid conflict
# One js file for each matrix in atop log file, the string has to be formed
# in CSV format. An example as below:
#
# 20160323_032739_syscpu_data =
# "Time,beam.smp,dhcpd,mongod,on-dhcp-proxy,on-http,on-syslog,on-taskgraph,on-tftp,\n" +
# "2016-03-16 11:33:57,0,0,0,0,0,0,0,0,\n" +
# "2016-03-16 11:34:02,0,0,0,0,0,0,0,0,\n" +
# "2016-03-16 11:34:07,0,0,0,0,0,0,0,0,\n" +
# "2016-03-16 11:34:12,0,0,0,0,0,0,0,0,\n" +
# "2016-03-16 11:34:17,0,0,0,0,0,0,10,0,\n" +
# "2016-03-16 11:34:22,0,0,0,0,0,0,0,0,\n" +
# "2016-03-16 16:34:07,0,0,0,0,0,0,0,0,"
def write_atop_matrix_to_js(matrix_data, case_information, out_dir):
    starttime_str = case_information["time marker"]["start"]
    sample_interval = case_information["interval"]
    timestamp = case_information["log path"].replace('-', '_')

    start_time = datetime.datetime.strptime(starttime_str, "%Y/%m/%d %H:%M:%S")

    matrix_list = {}
    padding_str = ',\\n\" + \n'

    pid_name_list = matrix_data.keys()
    pid_name_list_str = ",".join(sorted(pid_name_list))

    record_length_list = []
    for pid, pid_record in matrix_data.items():
        record_length_list.append(len(pid_record))

    record_cnt = min(record_length_list)

    # Get output files ready, one per each matrix
    for matrix_idx in range(len(ATOP_MATRIX)):    # No need to loop the PID matrix
        matrix_value = ATOP_MATRIX[matrix_idx].lower()
        filename = matrix_value + '.js'
        file_dir_name = os.path.join(out_dir, filename)
        file_open = open(file_dir_name, 'w')
        matrix_list[matrix_value] = file_open

        # write headers
        file_open.write('var ' + matrix_value + '_data_' + timestamp + ' = \n')
        file_open.write('\"Time,' + pid_name_list_str + padding_str)

        for record in range(record_cnt):     # Remove the first record
            line_records = []
            for pid in sorted(pid_name_list):
                # print(pid + ' ' + str(record)+ ' ' + ' '+ str(matrix_idx))
                line_records.append(str(matrix_data[pid][record][matrix_idx]))
            if record == (record_cnt - 1):
                padding = ',\"'
            else:
                padding = padding_str

            current_time = start_time + datetime.timedelta(seconds = record * sample_interval)
            current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
            line = "\"" + current_time_str + ',' + ",".join(line_records) + padding
            file_open.write(line)

# Write parsed atop result to js that can be used for generating graphs in
# front-end code
# Time stamp is added as a prefix to var to avoid conflict
# One js file for each matrix in mongo document log file, the string has to be formed
# in CSV format. An example as below:

# 20160323_032739_mongo_document_data =
# "Time,dataSize,storageSize,\n" +
# "2016-03-16 11:33:57,6286556,12083200,\n" +
# "2016-03-16 11:34:02,6286556,12083200,\n" +
# "2016-03-16 11:34:07,6286556,12083200,\n" +
# "2016-03-16 11:34:12,6286556,12083200,\n" +
# "2016-03-16 16:22:17,6286556,12083200,"
def write_mongo_doc_to_js(matrix_data, case_information, filename):
    starttime_str = case_information["time marker"]["start"]
    sample_interval = case_information["interval"]
    timestamp = case_information["log path"].replace('-', '_')

    start_time = datetime.datetime.strptime(starttime_str, "%Y/%m/%d %H:%M:%S")

    padding_str = ',\\n\" + \n'

    matrix_name_list = matrix_data.keys()
    matrix_name_list_str = ",".join(sorted(matrix_name_list))

    file_open = open(filename, 'w')

    # write headers
    file_open.write('var ' + 'mongo_document_data_' + timestamp + ' = \n')
    file_open.write('\"Time,' + matrix_name_list_str + padding_str)

    record_length_list = []
    for matrix, records in matrix_data.items():
        record_length_list.append(len(records))

    record_cnt = min(record_length_list)

    for record in range(record_cnt):
        line_records = []
        for matrix in sorted(matrix_name_list):
            line_records.append(str(matrix_data[matrix][record]))

        if record == (record_cnt - 1):
            padding = ',\"'
        else:
            padding = padding_str

        current_time = start_time + datetime.timedelta(seconds = record * sample_interval)
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        line = "\"" + current_time_str + ',' + ",".join(line_records) + padding
        file_open.write(line)

# Return a list with items from line spited by space
def split_line_by_space(line):
    splited_line = re.split("\s+", line)
    #remove empty element
    while '' in splited_line:
        splited_line.remove('')
    return splited_line

# Return a list with items from line spited by colon
def split_line_by_colon(line):
    splited_line = re.split(":", line)
    #remove empty element
    while '' in splited_line:
        splited_line.remove('')
    splited_line[1] = splited_line[1][0:-2] # remove the tailing ',\n'
    return splited_line

# Return a dict mapping PID to process name, according to info parsed from pid.log
# Return dict look like:

# {
#     "1077": "mongod",
#     "1106": "on-tftp"
# }
def parse_process_list(filename):
    PROCESS_LIST = [
        "on-http",
        "on-syslog",
        "on-taskgraph",
        "on-tftp",
        "on-dhcp-proxy",
        "beam.smp",
        "mongod",
        "dhcpd"
    ]
    processes = {}
    with open(filename, 'r') as f:
        for line in f:
            param_list = split_line_by_space(line)

            for process in PROCESS_LIST:
                if line.find(process) >= 0:
                    processes[param_list[0]] = process
                    break

    return processes

# Return a process name from PID per dict lookup
def get_process_name(process_dict, pid_str):
    return process_dict[pid_str]

# Line parser for atop log file
# Return a list of decoded matrix value:
# [syscpu, usrcpu, vsize, rsize, rddsk, wrdsk, rnet, snet, rnetbw, snetbw, cpu]
def parse_line_atop(line):
    ret_val = {}
    param_list = split_line_by_space(line)

    if len(param_list) < len(ATOP_LINE_COL):
        return {}

    # parse PID
    pid_col = ATOP_LINE_COL.index('PID')
    pid = param_list[pid_col]
    ret_val['process'] = pid

    # Parse SYSCPU
    syscpu_col = ATOP_LINE_COL.index('SYSCPU')
    syscpu_str = param_list[syscpu_col]
    syscpu = parse_cpu_time(syscpu_str)
    # Parse USRCPU
    usrcpu_col = ATOP_LINE_COL.index('USRCPU')
    usrcpu_str = param_list[usrcpu_col]
    usrcpu = parse_cpu_time(usrcpu_str)

    # Parse memory VSIZE
    vsize_col = ATOP_LINE_COL.index('VSIZE')
    vsize_str = param_list[vsize_col]
    vsize = parse_size(vsize_str)

    # Parse memory RSIZE
    rsize_col = ATOP_LINE_COL.index('RSIZE')
    rsize_str = param_list[rsize_col]
    rsize = parse_size(rsize_str)

    # Parse memory RDDSK
    rddsk_col = ATOP_LINE_COL.index('RDDSK')
    rddsk_str = param_list[rddsk_col]
    rddsk = parse_size(rddsk_str)

    # Parse memory WRDSK
    wrdsk_col = ATOP_LINE_COL.index('WRDSK')
    wrdsk_str = param_list[wrdsk_col]
    wrdsk = parse_size(wrdsk_str)

    # Parse network RNET
    rnet_col = ATOP_LINE_COL.index('RNET')
    rnet_str = param_list[rnet_col]
    rnet = parse_network_io(rnet_str)

    # Parse network SNET
    snet_col = ATOP_LINE_COL.index('SNET')
    snet_str = param_list[snet_col]
    snet = parse_network_io(snet_str)

    # Parse network RNETBW
    rnetbw_col = ATOP_LINE_COL.index('RNETBW')
    rnetbw_u_col = ATOP_LINE_COL.index('RNETBW_U')
    rnetbw_str = param_list[rnetbw_col]
    rnetbw_u_str = param_list[rnetbw_u_col]
    rnetbw = parse_network_bw(rnetbw_str, rnetbw_u_str)

    # Parse network SNETBW
    snetbw_col = ATOP_LINE_COL.index('SNETBW')
    snetbw_u_col = ATOP_LINE_COL.index('SNETBW_U')
    snetbw_str = param_list[snetbw_col]
    snetbw_u_str = param_list[snetbw_u_col]
    snetbw = parse_network_bw(snetbw_str, snetbw_u_str)

    # Parse CPU utilization
    cpu_col = ATOP_LINE_COL.index('CPU')
    cpu_str = param_list[cpu_col]
    cpu = int(cpu_str[0:-1])
    # print('CPU: ' + str(cpu))
    ret_val['list'] = [syscpu, usrcpu, vsize, rsize, rddsk, wrdsk,
                       rnet, snet, rnetbw, snetbw, cpu]

    return ret_val

# parse atop log file
def parse_atop(filename, proc_list):
    ret_val = {}
    with open(filename, 'r') as f:
        for line in f:
            parsed_line = parse_line_atop(line)

            if parsed_line == {}:
                continue

            pid = parsed_line['process']
            process_name = get_process_name(proc_list, pid)

            if process_name not in ret_val:
                ret_val[process_name] = []
                continue

            ret_val[process_name].append(parsed_line['list'])
    return ret_val

# scan for a list of data that can be used for compare
# and write the list to js file which will be used by front-end code
# output will be look like:
# 20160323_032739_compare_list =
# {
#     "20160323_032739" : ["case1", "case2"],
#     "20160323_032812" : ["case1", "case2"],
#     "20160323_032923" : ["case1", "case2"]
# }
def write_compare_list_to_js(log_dir_str, case_information, output_filename):
    result_list = {}
    timestamp = case_information["log path"].replace('-', '_')

    # scan compare list
    path_par_par = os.path.abspath(os.path.join(log_dir_str, os.pardir, os.pardir))

    for name in os.listdir(path_par_par):
        pathname = os.path.join(path_par_par, name)
        if not os.path.isfile(pathname):
            result_list[name] = []
            # further scan each folder to get a list of test cases
            for case_name in os.listdir(pathname):
                case_pathname = os.path.join(pathname, case_name)
                if not os.path.isfile(pathname):
                    result_list[name].append(case_name)

    with open(output_filename, 'w') as f:
        f.write('var ' + 'compare_list_' + timestamp + ' = \n')
        json_str = json.dumps(result_list, indent=4)
        f.write(json_str)
    pass

# The overall parser.
# specify log_dir as the absolute directory where all the log files resides.
# parsed output file will be placed at a folder called 'data' under log_dir
def parse(log_dir):
    if not os.path.exists(log_dir):
        # print "log dir " + log_dir + " does not exist"
        return

    output_dir = os.path.join(log_dir, 'data')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # parse mongodb document usage
    pathname_mongo_document = os.path.join(log_dir, filename_mongo_document)
    mongo_document = parse_mongo_document(pathname_mongo_document)

    # parse mongodb disk usage
    pathname_mongo_disk = os.path.join(log_dir, filename_mongo_disk)
    mongo_disk = parse_mongo_disk(pathname_mongo_disk)

    # parse case info
    pathname_caseinfo = os.path.join(log_dir, filename_caseinfo)
    case_info = parse_case_info(pathname_caseinfo)

    # parse process list
    pathname_process = os.path.join(log_dir, filename_process)
    process_list = parse_process_list(pathname_process)

    # parse atop log file
    pathname_atop = os.path.join(log_dir, filename_atop)
    atop_matrix = parse_atop(pathname_atop, process_list)
    # calc max/min/avg from result
    max_min_avg_atop = calc_max_min_avg_atop(atop_matrix)
    max_min_avg_mongo = calc_max_min_avg_mongo(mongo_document)

    pathname_atop_summary_js = os.path.join(output_dir, filename_atop_summary_js)
    write_summary_to_js(max_min_avg_atop,
                        "atop_statistics",
                        case_info,
                        pathname_atop_summary_js)

    pathname_mongo_doc_summary_js = os.path.join(output_dir, filename_mongo_doc_summary_js)
    write_summary_to_js(max_min_avg_mongo,
                        "mongo_document_statistics",
                        case_info,
                        pathname_mongo_doc_summary_js)

    pathname_mongo_disk_summary_js = os.path.join(output_dir, filename_mongo_disk_summary_js)
    write_summary_to_js(mongo_disk,
                        "mongo_disk_statistics",
                        case_info,
                        pathname_mongo_disk_summary_js)

    # Print to js log file
    write_atop_matrix_to_js(atop_matrix,
                            case_info,
                            output_dir)
    pathname_mongo_document_js = os.path.join(output_dir, filename_mongo_document_js)

    write_mongo_doc_to_js(mongo_document,
                          case_info,
                          pathname_mongo_document_js)

    pathname_caseinfo_js = os.path.join(output_dir, filename_caseinfo_js)
    write_case_info_to_js(case_info, pathname_caseinfo_js)

    pathname_compare_list_js = os.path.join(output_dir, filename_compare_list_js)
    write_compare_list_to_js(log_dir, case_info, pathname_compare_list_js)


if __name__ == '__main__':
    parse(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'test_dir'))

