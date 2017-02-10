'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import fit_path  # NOQA: unused import
import os
import sys
import subprocess
import fit_common

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd20_api_files(fit_common.unittest.TestCase):
    def setUp(self):
        # create test file
        TESTFILE = open(fit_common.TEST_PATH + 'testfile','w+')
        TESTFILE.write("1234567890ABCDEF")
        TESTFILE.close()
        # delete any instance of testfile on host
        api_data = fit_common.rackhdapi('/api/2.0/files')
        for item in api_data['json']:
            if item['filename'] == 'testfile':
                fit_common.rackhdapi('/api/2.0/files/' + item['uuid'], action="delete")
    def tearDown(self):
        os.remove(fit_common.TEST_PATH + 'testfile')
    def test_api_20_files_put_get_delete(self):
        # put file fia files API, then check data
        api_data = fit_common.rackhdapi('/api/2.0/files/testfile', action="binary-put", payload = file(fit_common.TEST_PATH + 'testfile').read())
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        # Retrieve file
        fileid = ""
        api_data = fit_common.rackhdapi('/api/2.0/files')
        for item in api_data['json']:
            if item['filename'] == 'testfile':
                fileid = item['uuid']
        api_data = fit_common.rackhdapi('/api/2.0/files/' + fileid)
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertEqual(open(fit_common.TEST_PATH + 'testfile').read(), api_data['text'], 'File corrupted, ID: ')
        # list all
        api_data = fit_common.rackhdapi('/api/2.0/files')
        self.assertIn(fileid, fit_common.json.dumps(api_data['json']), 'File ID missing in file list.')
        # check md5
        api_data = fit_common.rackhdapi('/api/2.0/files/testfile/md5')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        # check metadata
        api_data = fit_common.rackhdapi('/api/2.0/files/testfile/metadata')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in ['md5', 'name', 'sha256', 'uuid']:
            if fit_common.VERBOSITY >= 2:
                print "Checking:", item
            self.assertGreater(len(api_data['json'][item]), 0, item + ' field error')
        # delete file
        api_data = fit_common.rackhdapi('/api/2.0/files/' + fileid, action='delete')
        self.assertEqual(api_data['status'], 204, 'Incorrect HTTP return code, expected 204, got:' + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()


