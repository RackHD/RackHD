'''
Copyright 2016, EMC, Inc.

  Purpose: This test script performs the RedFish API ComputerSystem.Reset
           and verify the task status is correct and the power command occurs

'''
import fit_path  # NOQA: unused import
import time
import json
import fit_common
import test_api_utils
from nose.plugins.attrib import attr

# get list of compute nodes once for this test suite
NODELIST = fit_common.node_select()


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


def get_taskid_data(taskid):
    """
    This utility returns the data associated with the taskid
    reported by the Redfish API /redfish/v1/TaskService/Tasks/<taskid>
    :param taskid: task id returned by a command
    :return:
        taskid dictionary on success
        empty on failure or error
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
            print "Error in API command, url: {}".format(on_url)
    if fit_common.VERBOSITY >= 2:
        print json.dumps(taskid_json, indent=4)
    return taskid_json


def rackhd_compute_node_power_action(nodeid, action):
    """
    Routine to perform a power command against a specified compute node.
    It will return the taskid associated with the workflow
    :param nodeid:   rackhd node id
    :param action:   string for the specific power options
    :returns:
       taskid on success
       None on failure
    """
    taskid = None

    valid_actions = [
        "On",
        "ForceOff",
        "ForceOn",
        "ForceRestart"
    ]

    # Utility returns a valid task id for the user, so check
    # the call made to the functin is ok
    if action not in valid_actions:
        if fit_common.VERBOSITY >= 2:
            print "ERROR: invalid action in function call - ", str(action)
    else:
        on_url = "/redfish/v1/Systems/" + nodeid + "/Actions/ComputerSystem.Reset"
        on_payload = {"reset_type": action}
        on_data = fit_common.rackhdapi(on_url, action='post', payload=on_payload)
        if on_data['status'] == 202:
            taskid = on_data['json']["@odata.id"].split('/')[-1]
            if fit_common.VERBOSITY >= 2:
                print "TaskID", taskid
        else:
            if fit_common.VERBOSITY >= 2:
                print "ERROR: could not perform power command " + action + " Url: " + on_url

    return taskid


def workflow_tasklist_status_poller(tasklist, tasktype, timeout=180):
    """
    This utility will poll the list of taskids for a change from Running state
    It will poll for the specified timeout.
    :param taskid:  list of task ids to poll
    :param timeout: timeout in seconds when polling should fail, default is 600 seconds, 10 minutes
    :return:
        errorlist of taskids, node, status
    """
    count = 0           # loops for timeout
    polltime = 3        # sleep 3 seconds
    taskid_json = []
    task_errorlist = []

    # if timeout set too short, make it one above polltime
    if timeout < polltime:
        timeout = polltime + 1

    if fit_common.VERBOSITY >= 2:
        print("\n===============================")
        print("Polling for power update task completion....")

    # spin thru the list of tasks and taskstates
    while count < timeout:
        for task in tasklist:
            taskid_json = get_taskid_data(task)
            if taskid_json:
                if taskid_json.get("Name") != tasktype:
                    task_errorlist.append("Error: TaskName incorrect, expected {}".format(tasktype))
                taskstate = taskid_json.get("TaskState")
                if taskstate in ['Exception', 'Killed']:
                    node = taskid_json["Oem"]["RackHD"].get('SystemId')
                    nodetype = test_api_utils.get_rackhd_nodetype(node)
                    task_errorlist.append("Error: Node {} {} Task Failure: {}".format(node, nodetype, taskid_json))
                    tasklist.remove(task)
                elif taskstate in ['Completed']:
                    # quit polling the completed tasks, remove from list
                    tasklist.remove(task)
        # break out of loop if all tasks have ended
        if not tasklist:
            break
        time.sleep(polltime)
        count += polltime

    # if any tasks left in tasklist, add to error list
    if tasklist:
        task_errorlist.append("Error: Timeout on Task Completion: {} ".format(tasklist))
        for task in tasklist:
            task_errorlist.append("Error Task: {}, {}".format(task, get_taskid_data(task)))

    return task_errorlist

# Test Cases


@attr(all=True, regression=False, smoke=False)
class redfish10_api_computer_system_reset_base_suite(fit_common.unittest.TestCase):
    # This test suite covers the basic reset options supported by most compute
    # nodes - ON, ForceOff, ForceOn, ForceRestart
    # Due to required OS support and task exceptions other tests cover PushPowerButton,
    # GracefulRestart, GracefulShutdown

    # Clean out all the active workflows on each compute node before starting
    def setUp(self):
        for node in NODELIST:
            fit_common.cancel_active_workflows(node)

    def test_1_redfish_v1_computer_reset_on(self):
        # This test will verify the compute node workflow power reset option power On
        # and corresponding task status.

        if fit_common.VERBOSITY >= 2:
            msg = "Description: Verify the Computer.reset option \"On\" task data"
            print("\n\t{}".format(msg))

        errorlist = []
        tasklist = []

        for node in NODELIST:
            nodetype = test_api_utils.get_rackhd_nodetype(node)
            if fit_common.VERBOSITY >= 2:
                print("\nNode: {} {}".format(node, nodetype))
                print("\nPower node via ComputerSystem.reset On")

            # Perform ComputerSystem.reset On command
            taskid = rackhd_compute_node_power_action(node, "On")
            if taskid:
                tasklist.append(taskid)

        # Poll for task end status
        tasktype = "PowerOn Node"
        errorlist = workflow_tasklist_status_poller(tasklist, tasktype)

        if errorlist:
            print json.dumps(errorlist, indent=4)
        self.assertEqual(errorlist, [], "Errors found".format(errorlist))

        # allow power action to work a little
        time.sleep(5)

    def test_2_redfish_v1_computer_reset_force_off(self):
        # This test will verify the compute node workflow power reset option ForceOff
        # and corresponding task status.

        if fit_common.VERBOSITY >= 2:
            msg = "Description: Verify the Onrack Computer.reset option \"ForceOff\" task data"
            print("\n\t{}".format(msg))

        errorlist = []
        tasklist = []
        for node in NODELIST:
            nodetype = test_api_utils.get_rackhd_nodetype(node)
            if fit_common.VERBOSITY >= 2:
                print("\n===============================")
                print("\nNode: {} {}".format(node, nodetype))
                print("\nPower node via ComputerSystem.reset ForceOff")

            # Perform ComputerSystem.reset ForceOff command
            taskid = rackhd_compute_node_power_action(node, "ForceOff")
            if taskid:
                tasklist.append(taskid)

        # Poll for task end status
        tasktype = "PowerOff Node"
        errorlist = workflow_tasklist_status_poller(tasklist, tasktype)

        if errorlist:
            print json.dumps(errorlist, indent=4)
        self.assertEqual(errorlist, [], "Errors found".format(errorlist))

        # allow power action to work a little
        time.sleep(5)

    def test_3_redfish_v1_computer_reset_force_on(self):
        # This test will verify the compute node workflow power reset option ForceOn
        # and corresponding task status.

        if fit_common.VERBOSITY >= 2:
            msg = "Description: Verify the Onrack Computer.reset option \"ForceOn\" task data"
            print("\n\t{}".format(msg))

        errorlist = []
        tasklist = []

        for node in NODELIST:
            nodetype = test_api_utils.get_rackhd_nodetype(node)
            if fit_common.VERBOSITY >= 2:
                print("\n===============================")
                print("\nNode: {}".format(node))
                print("NodeType: {}".format(nodetype))
                print("\nPower node via ComputerSystem.reset ForceOn")

            # Perform ComputerSystem.reset ForceOn command
            taskid = rackhd_compute_node_power_action(node, "ForceOn")
            if taskid:
                tasklist.append(taskid)

        # Poll for task end status
        tasktype = "PowerOn Node"
        errorlist = workflow_tasklist_status_poller(tasklist, tasktype)

        if errorlist:
            print json.dumps(errorlist, indent=4)
        self.assertEqual(errorlist, [], "Errors found".format(errorlist))

        # allow power action to work a little
        time.sleep(5)

    def test_4_redfish_v1_computer_reset_force_restart(self):
        # This test will verify the compute node workflow power reset option ForceRestart
        # and corresponding task status.

        if fit_common.VERBOSITY >= 2:
            msg = "Description: Verify Redfish ComputerSystem.reset option \"ForceRestart\" task data"
            print("\n\t{}".format(msg))

        errorlist = []
        tasklist = []

        for node in NODELIST:
            nodetype = test_api_utils.get_rackhd_nodetype(node)
            if fit_common.VERBOSITY >= 2:
                print("\n===============================")
                print("\nNode: {} {}".format(node, nodetype))
                print("\nPower node via ComputerSystem.reset ForceRestart")

            # Perform ComputerSystem.reset ForceRestart command
            taskid = rackhd_compute_node_power_action(node, "ForceRestart")
            if taskid:
                tasklist.append(taskid)

        # Poll for task end status
        tasktype = "Reboot Node"
        errorlist = workflow_tasklist_status_poller(tasklist, tasktype)

        if errorlist:
            print json.dumps(errorlist, indent=4)
        self.assertEqual(errorlist, [], "Errors found".format(errorlist))

        # allow power action to work a little
        time.sleep(20)


if __name__ == '__main__':
    fit_common.unittest.main()
