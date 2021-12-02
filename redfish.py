#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import requests
import json
import base64
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RedFish(object):
    # hostname, username, password
    # output: 
    #   instance -  success
    #   None - error
    def __init__(self, hostname, username, password):
        self.hostname = hostname
        self.base_url = 'https://' + hostname + '/redfish/v1/'
        self.auth = (username, password)
        url = self.base_url + 'Systems/System.Embedded.1/'
        status, json_str = self.req_get(url)
        if status != 200:
            print('ERROR: %s' % status)
            sys.exit(-1)
        attr = ['AssetTag', 'BiosVersion', 'HostName', 'Manufacturer', 'Name', 'Model', 'PartNumber', 'SKU', 'SerialNumber']
        for i in json_str.items():
            if any(x == i[0] for x in attr):
                print(i[0] + ": " + i[1])

    def req_get(self, url):
        response = requests.get(url, verify=False, auth=self.auth)
        json_str = ''
        try:
            json_str = json.loads(response.text)
        except:
            pass
        return response.status_code, json_str

    def req_post(self, url, data):
        response = requests.post( url, 
                                  data=json.dumps(data), 
                                  headers={'content-type': 'application/json'}, 
                                  verify=False, auth=self.auth)
        time.sleep(1)
        json_str = ''
        try:
            json_str = json.loads(response.text)
        except:
            pass
        return response.status_code, json_str

    # -----------------------------------------------------------------------------
    def set_bios_attribute(self, attr, value):
        url = self.base_url + 'Systems/System.Embedded.1/Bios/Settings'
        payload_patch = {"Attributes":{}}
        payload_patch["Attributes"][attr] = value
        status, json_str = self.req_get(self.base_url + 'Systems/System.Embedded.1/Bios/BiosRegistry')
        for i in payload_patch["Attributes"].items():
            for ii in json_str['RegistryEntries']['Attributes']:
                if i[0] in ii.values():
                    if ii['Type'] == "Integer":
                        payload_patch['Attributes'][i[0]] = int(i[1])
        headers = {'content-type': 'application/json'}
        response = requests.patch(  url, 
                                    data=json.dumps(payload_patch), 
                                    headers=headers, verify=False, auth=self.auth)
        statusCode = response.status_code
        if statusCode == 200:
            print("\n- PASS: PATCH command passed to set BIOS attribute pending values")
        else:
            print("\n- FAIL, Command failed, errror code is %s" % statusCode)

    def create_bios_config_job():
        url = self.base_url + 'Managers/iDRAC.Embedded.1/Jobs'
        payload = {"TargetSettingsURI":"/redfish/v1/Systems/System.Embedded.1/Bios/Settings"}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
        statusCode = response.status_code
        if statusCode == 200:
            print("- PASS: Command passed to create target config job, status code 200 returned.")
        else:
            print("\n- FAIL, Command failed, status code is %s\n" % statusCode)

    def get_job_status():
        while True:
            req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
            statusCode = req.status_code
            if statusCode == 200:
                pass
                #print("- PASS, Command passed to check job status, code 200 returned")
                time.sleep(10)
            else:
                print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
                print("Extended Info Message: {0}".format(req.json()))
                sys.exit()
            data = req.json()
            if data['Message'] == "Task successfully scheduled.":
                print("- PASS, %s job id successfully scheduled, rebooting the server to apply config changes" % job_id)
                break
            else:
                print("- WARNING: JobStatus not scheduled, current status is: %s" % data['Message'])
    # -----------------------------------------------------------------------------

    def set_bios_attr(self, attr, value):
        url = self.base_url + 'Systems/System.Embedded.1/Bios/Settings'
        status, json_str = self.req_post(url, {attr: value})
        time.sleep(1)
        status_str = 'POST status: %s. ' % status
        return status_str, json_str

    # attr = BIOS attribute
    # output: string
    def get_bios_attr(self, attr):
        url = self.base_url + 'Systems/System.Embedded.1/Bios'
        status, json_str = self.req_get(url)
        if status == 200:
            for i in json_str['Attributes'].items():
                if i[0] == attr:
                    return i[1]
        return ''

    # output: JSON
    def get_attributes(self):
        url = self.base_url + 'Systems/System.Embedded.1/Bios'
        status, json_str = self.req_get(url)
        if status == 200:
            return json_str['Attributes']
        return None

    # Output: 'On', 'Off'
    def get_power_state(self):
        url = self.base_url + 'Systems/System.Embedded.1/'
        status, json_str = self.req_get(url)
        if status == 200:
            return json_str['PowerState']
        return ''

    # state = ['On', 'ForceOff', 'ForceRestart', 'GracefulShutdown', 'PushPowerButton', 'Nmi', 'PowerCycle']
    # output: 
    #   True -  success
    #   False - error
    def set_power_state(self, state):
        url = self.base_url + 'Systems/System.Embedded.1/Actions/ComputerSystem.Reset'
        status, json_str = self.req_post(url, {'ResetType': state})
        time.sleep(1)
        status_str = 'POST status: %s. ' % status
        try:
            status_str += json_str['error']['@Message.ExtendedInfo'][0]['Message']
        except:
            pass
        if status < 300 or status == 409:
            return True, status_str
        return False, status_str

    # output is png image binary
    # output: 
    #   binary  - success
    #   None    - error or system in S5 mode
    def get_screenshot(self):
        url = self.base_url + 'Dell/Managers/iDRAC.Embedded.1/DellLCService/Actions/DellLCService.ExportServerScreenShot'
        status, json_str = self.req_post(url, {'FileType': 'ServerScreenShot'})
        if status == 202 or status == 200:
            return base64.b64decode(json_str['ServerScreenShotFile'])
        return None

    # output: string
    def get_model_name(self):
        url = self.base_url + 'Systems/System.Embedded.1/'
        status, json_str = self.req_get(url)
        if status == 200:
            for i in json_str.items():
                if i[0] == 'Model':
                    return i[1]
        return ''

    # output: string
    def get_bios_version(self):
        url = self.base_url + 'Systems/System.Embedded.1/'
        status, json_str = self.req_get(url)
        if status == 200:
            for i in json_str.items():
                if i[0] == 'BiosVersion':
                    return i[1]
        return ''

    # media = 'CD', 'RemovableDisk'
    # link = 'http://192.168.0.200/cd.iso', 'http://192.168.0.200/usb.img'
    #   True -  success
    #   False - error
    def insert_virtual_media(self, media, link):
        url = self.base_url + 'Managers/iDRAC.Embedded.1/VirtualMedia/' + media
        url += '/Actions/VirtualMedia.InsertMedia'
        status, json_str = self.req_post(url, {'Image': link})
        status_str = 'POST status: %s. ' % status
        try:
            status_str += json_str['error']['@Message.ExtendedInfo'][0]['Message']
        except:
            pass
        time.sleep(1)
        if status == 204 or status == 200:
            return True, status_str
        return False, status_str

    # media = 'CD', 'RemovableDisk'
    # output: 
    #   True -  success
    #   False - error
    def eject_virtual_media(self, media):
        url = self.base_url + 'Managers/iDRAC.Embedded.1/VirtualMedia/' + media
        status, json_str = self.req_get(url)
        try:
            if json_str['Inserted'] == False:
                return True, 'No Virtual Media device connected'
        except:
            pass
        url += '/Actions/VirtualMedia.EjectMedia'
        status, json_str = self.req_post(url, {})
        status_str = 'POST status: %s. ' % status
        try:
            status_str += json_str['error']['@Message.ExtendedInfo'][0]['Message']
        except:
            pass
        time.sleep(3)
        if status == 204 or status == 500: #or status == 400:
            return True, status_str
        return False, status_str

    def close(self):
        pass
