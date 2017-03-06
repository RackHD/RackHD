'''
Copyright 2016, EMC, Inc.

  Purpose: This test script consists of tests to verify the task service API returned data.

'''

import fit_path  # NOQA: unused import
import json
import fit_common
from nose.plugins.attrib import attr


# Utiities for this script
def print_taskid_data(taskid, taskid_json):
    """
    This utility displays the taskjson data for the user
    :param taskjson: valid taskid json structure
    """
    print "\n\tTaskId: ", taskid
    print "\tSystem ID: ", taskid_json["Oem"]["RackHD"].get('SystemId', "")
    print "\tTask State ", taskid_json.get('TaskState', "")
    print "\tTask Status ", taskid_json.get('TaskStatus', "")
    print "\tStartTime: ", taskid_json.get('StartTime', "")
    print "\tEndTime: ", taskid_json.get('EndTime', "")
    print "\tName: ", taskid_json.get('Name', "")


def get_task_srv_tasklist():
    """
    This utility returns the list of all tasks currently in the system
    reported by the Onrack API /redfish/v1/TaskService/Tasks
    :return:
        List of task ids on success
        Otherwise empty on failure or error
    """
    on_url = "/redfish/v1/TaskService/Tasks"
    on_data = fit_common.rackhdapi(url_cmd=on_url)

    tasklist = []
    if on_data['status'] == 200:
        members = on_data['json']["Members"]
        for member in members:
            tasklist.append(member['Id'])
    else:
        if fit_common.VERBOSITY >= 2:
            print "Error in API command. Task Service command returned error."

    return tasklist


def get_node_tasklist(nodeid):
    """
    This utility returns the list of all tasks for a given node id
    reported by the Onrack API /redfish/v1/TaskService/Oem/Tasks
    :return:
        List of task ids on success
        Otherwise empty on failure or error
    """
    on_url = "/redfish/v1/TaskService/Oem/Tasks/" + nodeid
    on_data = fit_common.rackhdapi(url_cmd=on_url)

    tasklist = []
    if on_data['status'] == 200:
        members = on_data['json']["Members"]
        for member in members:
            tasklist.append(member['Id'])
    else:
        if fit_common.VERBOSITY >= 2:
            print "Error in API command. TaskService/Oem/Tasks/" + nodeid + " returned error."

    return tasklist


def get_taskid_data(taskid):
    """
    This utility returns the data associated with the taskid
    reported by the Onrack API /redfish/v1/TaskService/Tasks/<taskid>
    :param taskid: task id returned by a command
    :return:
        taskid dictionary
        Otherwise empty on failure or error
    """

    taskid_json = {}
    on_url = "/redfish/v1/TaskService/Tasks/" + taskid
    on_data = fit_common.rackhdapi(url_cmd=on_url)
    if on_data['status'] == 200:
        try:
            taskid_json = on_data['json']
        except ValueError:
            print "No TaskID data returned"
    else:
        if fit_common.VERBOSITY >= 2:
            print "Error in API command. TaskService/Oem/Tasks/" + taskid + " returned error."

    return taskid_json


@attr(all=True, regression=True, smoke=True)
class redfish10_api_task_suite(fit_common.unittest.TestCase):
    def test_redfish_v1_taskservice_tasklist(self):
        # The API /redfish/v1/TaskService will display the list of tasks in the system

        tasklist = []
        # This test checks the TaskService API
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Get TaskService data"
            print("\t{0}".format(msg))

        on_url = "/redfish/v1/TaskService"
        on_data = fit_common.rackhdapi(url_cmd=on_url)
        self.assertEqual(on_data['status'], 200,
                         "Incorrect HTTP return code, expecting 200, received ".format(on_data['status']))
        for item in ["CompletedTaskOverWritePolicy", "DateTime", "Id", "LifeCycleEventOnTaskStateChange",
                     "Name", "ServiceEnabled", "Status", "Tasks"]:
            if fit_common.VERBOSITY >= 2:
                print "Checking:", item
            self.assertIn(item, on_data['json'], item + ' field not present')

        # Check a few fields
        self.assertEqual(on_data['json']['Id'], "TaskService",
                         "Id field set incorrectly in response data: {0}".format(on_data['json']['Id']))

        writepolicy = on_data['json']['CompletedTaskOverWritePolicy']
        if fit_common.VERBOSITY >= 2:
            print "Checking CompletedTasksOverWritePolicy field"
        self.assertIn(writepolicy, ["Manual", "Oldest"], "Unexpected policy per specification {0}".format(writepolicy))

        tasklist = []
        members = on_data['json']['Tasks']['Members']
        for member in members:
            tasklist.append(member['Id'])
        if fit_common.VERBOSITY >= 2:
            print ("Task Service contains {0} tasks.".format(len(tasklist)))

    def test_redfish_v1_taskservice_check_all_tasks(self):
        # The API TaskService/Tasks will display a list of all the tasks
        # that were run and are active in the system.  This includes tasks for everything,
        # managed and unmanaged nodes and non-node specific tasks.

        tasklist = []
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display the list of Tasks in the System."
            print("\n\t{0}".format(msg))

        on_data = fit_common.rackhdapi('/redfish/v1/TaskService/Tasks')
        self.assertIn(on_data['status'], [200], "Incorrect HTTP return code")
        for item in ["@odata.id", "Name", "@odata.type"]:
            if fit_common.VERBOSITY >= 2:
                print "Checking:", item
            self.assertIn(item, on_data['json'], item + ' field not present')
            if item not in ["Members@odata.count", "Members"]:
                self.assertGreater(len(on_data['json'][item]), 0,
                                   "Required field {0} empty".format(item))
        tasklist = []
        if fit_common.VERBOSITY >= 2:
            print("\tTaskIDs: ")
        members = on_data['json']["Members"]
        for member in members:
            taskid = member['Id']
            tasklist.append(taskid)
            if fit_common.VERBOSITY >= 2:
                print(taskid)
        self.assertNotEqual(tasklist, [], 'No Tasks listed in system.')

        # Check reported Member count equals number of task ids in the list
        membercount = int(on_data['json']['Members@odata.count'])
        listcount = len(tasklist)
        self.assertEqual(membercount, listcount,
                         "Reported member count of {0} not equal length of tasklist {1}".format(membercount, listcount))
        if fit_common.VERBOSITY >= 2:
            print "\tNumber of tasks in the system", membercount

    def test_redfish_v1_taskservice_tasks_per_node(self):
        # The API TaskService/Oem/Tasks/<systemid> will display a list of all tasks that
        # are associated with the specified node id for managed systems.

        # if verbose
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display the list of Tasks for each System"
            print("\n\t{0}".format(msg))

        nodelist = fit_common.node_select()
        if fit_common.VERBOSITY >= 2:
            print "Nodelist: "
            print json.dumps(nodelist, indent=4)
        self.assertNotEqual(nodelist, [], 'No Nodes reported for this stack.')
        for node in nodelist:
            tasklist = get_node_tasklist(node)
            self.assertNotEqual(tasklist, [], 'No Tasks listed for node.')
            for taskid in tasklist:
                taskdata = get_taskid_data(taskid)
                if fit_common.VERBOSITY >= 2:
                    print_taskid_data(taskid, taskdata)

    def test_redfish_v1_taskservice_task_count_per_node(self):
        # The API /redfish/v1/TaskService/Oem/Tasks/<id> will check the count for each list of tasks
        # associated with all node ids.

        if fit_common.VERBOSITY >= 2:
            msg = "Description: Check the reported task count in the list of Tasks for each System"
            print("\n\t{0}".format(msg))

        nodelist = fit_common.node_select()
        self.assertNotEqual(nodelist, [], 'No Nodes reported for this stack.')

        for node in nodelist:
            on_url = "/redfish/v1/TaskService/Oem/Tasks/" + node
            on_data = fit_common.rackhdapi(url_cmd=on_url)
            tasklist = []
            if on_data['status'] == 200:
                members = on_data['json']["Members"]
                for member in members:
                    taskid = member['Id']
                    tasklist.append(taskid)
            taskcount = int(on_data['json']['Members@odata.count'])
            listcount = len(tasklist)
            self.assertEqual(taskcount, listcount,
                             "Reported task count {0} not equal length of tasklist {1}".format(taskcount, listcount))
            if fit_common.VERBOSITY >= 2:
                print("\tNodeID: {0} Number of tasks reported {1}".format(node, taskcount))

    def test_redfish_v1_taskservice_check_task_data_fields(self):
        # The API TaskSerive/Tasks will display the task data associated with the specified task.

        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display the data for each taskid contained in the System."
            print("\n\t{0}".format(msg))

        tasklist = get_task_srv_tasklist()
        self.assertNotEqual(tasklist, [], 'No Tasks found in the system')

        for task in tasklist:
            on_data = fit_common.rackhdapi('/redfish/v1/TaskService/Tasks/' + task)
            self.assertIn(on_data['status'], [200], "Incorrect HTTP return code")

            # check if required fields exist
            for item in ["@odata.id", "Name", "@odata.type", "TaskState", "TaskStatus", "StartTime", "Id"]:
                if fit_common.VERBOSITY >= 2:
                    print ("Task: {} Checking: {}".format(task, item))
                self.assertIn(item, on_data['json'], item + ' field not present')

            # check if task completed, endtime should be populated
            taskstates = ["Completed", "Exception", "Killed"]
            taskstate = on_data['json'].get('TaskState', "")
            if taskstate in taskstates:
                for item in ["EndTime"]:
                    if fit_common.VERBOSITY >= 2:
                        print ("Task: {} Checking: {}".format(task, item))
                    self.assertIn(item, on_data['json'], item + ' field not present')

            if fit_common.VERBOSITY >= 3:
                print_taskid_data(task, on_data['json'])

    def test_redfish_v1_taskservice_check_task_return_status_validity(self):
        '''
        Check the return status in the tasks to be in the valid list
        Mapping of RackHD 1.1 to  Redfish v1 status is:
            running   : Running
            succeeded : Completed
            finished  : Completed
            failed    : Exception
            timeout   : Exception
            cancelled : Killed
            pending   : Pending
        '''
        def task_code_check(tasklist):
            # Following is list as stated by OnRack developers
            validtaskstatus = ["Running", "Pending", "Completed", "Exception", "Killed"]
            '''
            validtaskstatus = ["Running", "Cancelled", "Aborted", "Completed", "Exception", "Killed", "Pending"]
            Following is list defined in Redfish specs
            validtaskstatus = ["New", "Starting", "Running", "Suspended", "Interrupted", "Pending",
                               "Stopping", "Completed", "Killed", "Exception", "Service"]

            Enumeration Description for TaskStates from Redfish 1.0.0 spec:
            New: A new task
            Starting: Task is starting
            Running: Task is running normally
            Suspended: Task has been suspended
            Interrupted: Task has been interrupted
            Pending: Task is pending and has not started
            Stopping: Task is in the process of stopping
            Completed: Task has completed
            Killed: Task was terminated
            Exception: Task has stopped due to an exception condition
            Service: Task is running as a service
            '''
            errorlist = []
            if fit_common.VERBOSITY >= 2:
                print("\tValid Task States per Redfish 1.0 {0}".format(validtaskstatus))

            # Check the task id task state is in list of valid task status codes
            for task in tasklist:
                on_data = fit_common.rackhdapi('/redfish/v1/TaskService/Tasks/' + task)
                if on_data['status'] != 200:
                    errorlist.append("TaskId: {} Incorrect HTTP return code, expecting 200, received {}"
                                     .format(task, on_data['status']))
                if on_data['json']['TaskState'] not in validtaskstatus:
                    print_taskid_data(task, on_data['json'])
                    errorlist.append("TaskID: {} Invalid Task State of : {}".format(task, on_data['json']['TaskState']))
            return errorlist

        if fit_common.VERBOSITY >= 2:
            msg = "Description: Check the return status codes are in list of valid status"
            print("\n\t{0}".format(msg))

        tasklist = get_task_srv_tasklist()
        self.assertNotEqual(tasklist, [], 'No Tasks listed.')
        status = task_code_check(tasklist)

        if status != []:
            print ("Errors reported {} ".format(json.dumps(status, indent=4)))
            self.assertEqual(status, [], "Errors in Returned Task Status.")

    def test_redfish_v1_taskservice_check_library_test_list(self):
        # Return the task list libary from rackhd

        if fit_common.VERBOSITY >= 2:
            msg = "Description: Get list of supported tasks via monorail workflow task library"
            print("\n\t{0}".format(msg))

        supported_tasks = []
        get_task_url = "/api/2.0/workflows/tasks"
        mon_data = fit_common.rackhdapi(url_cmd=get_task_url)
        if mon_data['status'] != 200:
            print 'No data returned from monorail, status = {0}'.format(mon_data['status'])
        else:
            for task in mon_data['json']:
                # handle key error if injectableName not in json
                if task.get('injectableName') is not None:
                    supported_tasks.append(task['injectableName'])

        self.assertNotEqual(supported_tasks, [], 'No tasks listed in task library.')
        if fit_common.VERBOSITY >= 2:
            for key in supported_tasks:
                print("Key: {}".format(key))


if __name__ == '__main__':
    fit_common.unittest.main()
