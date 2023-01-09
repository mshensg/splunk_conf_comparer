import os
import sys
import time
import datetime
import json
import re
import hashlib


def getCommonKeys(object1,object2):
    # extract the same keys exit in both dict object
    ok1 = object1.keys()
    ok2 = object2.keys()
    results = []
    [results.append(i) if i in ok2 else None for i in ok1]
    return results

def comparevalue(value1,value2,makeboolasnumber=False):
    #compare two values to see if they are the same
    result = True
    if not makeboolasnumber:
        result = value1==value2
    else:
        if type(value1) is bool:
            v1 = str(int(value1))
        elif type(value1) is str and value1.upper() == "TRUE":
            v1 = '1'
        elif type(value1) is str and value1.upper() == "FALSE":
            v1 = '0'
        else:
            v1 = str(value1)
        if type(value2) is bool:
            v2 = str(int(value2))
        elif type(value2) is str and value2.upper() == "TRUE":
            v2 = '1'
        elif type(value2) is str and value2.upper() == "FALSE":
            v2 = '0'
        else:
            v2 = str(value2)
        #print(v1)
        #print(v2)
        result = v1 == v2
    return result

def diffdict(object1,object2, keepempty=False, makeboolasnumber=True):
    # compare two dict object to find the difference
    result1 = {}
    result2 = {}
    if type(object1) is dict and type(object2) is dict:
        dictkeys1 = list(object1.keys())
        dictkeys2 = list(object2.keys())
        dictkeys1.extend(dictkeys2)
        dictkeys = list(set(dictkeys1))
        #dictkeys.sort()
        for k in dictkeys:
            if k in object1 and k not in object2:
                result1[k] = object1[k]
            if k not in object1 and k in object2:
                result2[k] = object2[k]
            if k in object1 and k in object2 and not comparevalue(object1[k],object2[k],makeboolasnumber):
                if type(object1[k]) is dict or type(object2[k]) is dict:
                    o1,o2 = diffdict(object1[k],object2[k])
                else:
                    o1,o2 = object1[k],object2[k]
                if o1!={} or keepempty:
                    result1[k] = o1
                if o2!={} or keepempty:
                    result2[k] = o2
    else:
        result1 = object1
        result2 = object2
    return result1,result2

def convertConf2Json(configdata,containsdebug=False):
    # convert conf format to json format dict object
    if containsdebug:
        r = re.compile("(\S+)\s+(.+)")
        config=[r.match(i).groups()[1] for i in configdata]
    else:
        config=configdata

    re_section = re.compile("\[([^\[\]]*)\]")
    re_content = re.compile("^([^=]*)=((?:(?!\s+#).)*)")#("^([^=]*)=([^#]*)")
    finished = True

    jsonconfig = {}
    section = None

    for entry in config:
        line = entry.strip()
        if len(line) == 0:
            if finished==False: #if the previous line is not completed (endswith \), now it is completed
                finished=True
                if not section:
                    section="default"
                    jsonconfig[section]={}
                #if section:
                if value.isnumeric():
                    value = int(value)
                elif type(value) is str and value.upper() == "TRUE":
                    value = True
                elif type(value) is str and value.upper() == "FALSE":
                    value = False
                jsonconfig[section][key] = value
        elif line[0] == '#':
            if not finished and section:
                configuration[section][key] = value
            finished = True
            #pass #ignore comment and keep the status.
        elif line[0] == '[' and line[-1] == ']' and finished:
            finished = True
            results = re_section.match(line)
            section = results.groups()[0]
            jsonconfig[section] = {}
        else:
            if not finished:
                value = value[0:-1] +"\n" + line
            else:
                results = re_content.match(line)
                if results is None:
                    key=line
                    value=""
                else:
                    key = results.groups()[0].strip()
                    value = results.groups()[1].strip()
            if line[-1] == "\\":
                finished = False
            else:
                finished = True
                if not section:
                    section="default"
                    jsonconfig[section]={}
                #if section:
                if value.isnumeric():
                    value = int(value)
                elif type(value) is str and value.upper() == "TRUE":
                    value = True
                elif type(value) is str and value.upper() == "FALSE":
                    value = False
                jsonconfig[section][key] = value

    return jsonconfig


file1="/opt/compare/8.0.6/splunk/etc/system/default/props.conf"
file2="/opt/compare/9.0.3/splunk/etc/system/default/props.conf"

if os.path.exists(file1):
    with open(file1,"r") as f:
        conf_content = f.readlines()
        f.close()
    json1=convertConf2Json(conf_content)

if os.path.exists(file2):
    with open(file2,"r") as f:
        conf_content = f.readlines()
        f.close()
    json2=convertConf2Json(conf_content)

diff1,diff2 = diffdict(json1,json2)

if diff1=={} and diff2=={}:
    # No difference
    pass
else:
    if diff1=={}:
        subaction="remove"
    elif diff2=={}:
        subaction="add"
    else:
        subaction="edit"
    changesummary={"filename1":file1,
                   "filename2":file2,
                   "added":diff1,
                   "removed":diff2,
                   "action":subaction}

print(json.dumps(changesummary,indent=4))
