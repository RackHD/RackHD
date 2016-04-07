from benchmark.utils.ansible_control import ansibleControl

ansible_ctl = ansibleControl()
if ansible_ctl.setup_env() == False:
    exit(1)
