'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

     Author: Torrey Cuthbert
   Filename: user.py
Create Date: 04/09/2017
Description: Defines a RackHD User account base class and its methods. All account role types (Administrator, Operator, and
             ReadOnly) inherit from this class. An instance of this class allows for user account creation and maintenance e.g.,
             account password change etc.
'''

import fit_common
import flogging
import json
import requests

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Global
logs = flogging.get_loggers()


class User:
    num_users = 0
    timeout = 5

    def __init__(self, username, passwd, role, redfish=False):
        self.username = username
        self.passwd = passwd
        self.role = role
        if fit_common.AUTH_TOKEN == 'Unavailable' or fit_common.REDFISH_TOKEN == 'None':
            if not fit_common.get_auth_token():
                logs.info("error, unable to obtain fit_common RackHD and Redfish API administrative tokens")
                return None
        # create a Redfish or RackHD account first (redfish=False) depending on the truth of redfish
        # this logic allows the ability to test that an account for each endpoint gets created no matter which
        # one is created first. the constructor does this basic check.
        if not redfish:
            if not self.createRackHDUser():
                return None
        else:
            if not self.createRedfishUser():
                return None
        User.num_users += 1

    def createRackHDUser(self):
        headers = {
            'content-type': 'application/json',
            'accept': 'application/json'
        }
        payload = {
            'username': self.username,
            'password': self.passwd,
            'role': self.role
        }
        url = "https://{0}:{1}/api/2.0/users?auth_token={2}".format(fit_common.fitcfg()['rackhd_host'],
                                                                    str(fit_common.fitports()['https']), fit_common.AUTH_TOKEN)
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=User.timeout, verify=False)
        except requests.exceptions.RequestException as e:
            logs.info("error, {0}", e)
            return False
        if r.status_code != 201:
            logs.info("error status code {0}, could not create RackHD user account", r.status_code)
            return False
        return True

    def createRedfishUser(self):
        headers = {
            'content-type': 'application/json',
            'accept': 'application/json',
            'x-auth-token': fit_common.REDFISH_TOKEN
        }
        payload = {
            'Password': self.passwd,
            'UserName': self.username,
            'RoleId': self.role
        }
        url = "https://{0}:{1}/redfish/v1/AccountService/Accounts".format(fit_common.fitcfg()['rackhd_host'],
                                                                          str(fit_common.fitports()['https']))
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=User.timeout, verify=False)
        except requests.exceptions.RequestException as e:
            logs.info("error, {0}", e)
            return False
        if r.status_code != 201:
            logs.info_4("error status code {0}, could not create Redfish user account '{1}'".format(r.status_code,
                                                                                                    self.username))
            return False
        return True

    def setRackHDToken(self, username, passwd):
        headers = {
            'content-type': 'application/json',
            'accept': 'application/json'
        }
        payload = {
            'username': username,
            'password': passwd
        }
        url = "https://{0}:{1}/login".format(fit_common.fitcfg()['rackhd_host'], str(fit_common.fitports()['https']))
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=User.timeout, verify=False)
        except requests.exceptions.RequestException as e:
            print 'error, {0}'.format(e)
            return None
        if r.status_code != 200:
            logs.info_4("error status code {0}, unable to set user rackhd token".format(r.status_code))
            return None
        return 'JWT ' + json.loads(r.content)['token']

    def setRedfishToken(self, username, passwd):
        headers = {
            'content-type': 'application/json',
            'accept': 'text/html'
        }
        payload = {
            'UserName': username,
            'Password': passwd
        }
        url = "https://{0}:{1}/redfish/v1/SessionService/Sessions".format(fit_common.fitcfg()['rackhd_host'],
                                                                          str(fit_common.fitports()['https']))
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=User.timeout, verify=False)
        except requests.exceptions.RequestException as e:
            print 'error, {0}'.format(e)
            return None
        if r.status_code != 200:
            logs.info("error status code {0}, unable to set redfish token", r.status_code)
            return None
        return r.headers['X-Auth-Token']

    def deleteRackHDUserAccount(self):
        headers = {
            'accept': 'application/json',
            'authorization': 'JWT ' + fit_common.AUTH_TOKEN
        }
        url = "https://{0}:{1}/api/2.0/users/{2}".format(fit_common.fitcfg()['rackhd_host'],
                                                         str(fit_common.fitports()['https']), self.username)
        try:
            r = requests.delete(url, headers=headers, timeout=User.timeout, verify=False)
        except requests.exceptions.RequestException as e:
            logs.info("error, {0}", e)
            return None
        if r.status_code != 204:
            logs.info("error status code {0}, unable to delete RackHD user '{1}'", r.status_code, self.username)
            return None

    def deleteRedfishUserAccount(self):
        headers = {
            'accept': 'application/json',
            'x-auth-token': fit_common.REDFISH_TOKEN
        }
        url = "https://{0}:{1}/redfish/v1/AccountService/Accounts/{2}".format(fit_common.fitcfg()['rackhd_host'],
                                                                              str(fit_common.fitports()['https']),
                                                                              self.username)
        try:
            r = requests.delete(url, headers=headers, timeout=User.timeout, verify=False)
        except requests.exceptions.RequestException as e:
            logs.info("error, {0}", e)
            return None
        if r.status_code != 204:
            logs.info("error status code {0}, unable to delete Redfish user '{1}'", r.status_code, self.username)
            return None
