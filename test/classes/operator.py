'''
Copyright 2017, DellEMC LLC

     Author: Torrey Cuthbert
      Email: torrey.cuthbert@dell.com
   Filename: operator.py
Create Date: 04/09/2017
Description: Defines a RackHD Operator user role class and methods. An instance of this class allows
             for Operator account permission between the Operator user and the RackHD server APIs.
'''

from user import User

class Operator(User):
    num_operators = 0
    rackhd_token = None
    redfish_token = None

    def __init__(self, username, passwd, role, redfish=False):
        User.__init__(self, username, passwd, role, redfish)
        self.username = username
        self.passwd = passwd
        self.role = role
        self.rackhd_token = self.setRackHDToken(username, passwd)
        if self.rackhd_token is None:
            return None
        self.redfish_token = self.setRedfishToken(username, passwd)
        if self.redfish_token is None:
            return None
        Operator.num_operators += 1
