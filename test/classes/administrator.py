'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

     Author: Torrey Cuthbert
      Email: torrey.cuthbert@dell.com
   Filename: adminstrator.py
Create Date: 04/09/2017
Description: Defines a RackHD Administrator user class and methods. An instance of this class allows
             for Administrator account permission with the RackHD server APIs.
'''

from user import User

class Administrator(User):
    num_admins = 0
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
        Administrator.num_admins += 1
