import re,json,argparse,os,requests
import collections

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
        print(line, finished, section)
        if len(line) == 0:
            pass #no content, ignore and keep the status
        elif line[0] == '#':
            #if not finished and section:
                #jsonconfig[section][key] = value
            #finished = True
            pass #ignore comment and keep the status. if the line starts with #, it will be ignored even it is in middle of another multiline configuration
        elif line[0] == '[' and finished:
            finished = True
            results = re_section.match(line)
            section = results.groups()[0]
            jsonconfig[section] = {}
        else:
            if not finished:
                value = value[0:-1] +"\n" + line
            else:
                results = re_content.match(line)
                key = results.groups()[0].strip()
                value = results.groups()[1].strip()
            if line[-1] == "\\":
                finished = False
            else:
                finished = True
                if section:
                    if value.isnumeric():
                        value = int(value)
                    elif type(value) is str and value.upper() == "TRUE":
                        value = True
                    elif type(value) is str and value.upper() == "FALSE":
                        value = False
                    jsonconfig[section][key] = value

    return jsonconfig


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

def convertRESTJson2Conf(jconf, skiplist=[],asString=False):
    # convert the REST API output JSON file to configuration file. the extra response information from JSON interface will lost.
    # skiplist is a list of string using regex. it has to full match the key so to exclude them.
    if type(skiplist) is not list:
        skiplist = []
    outconf = []
    for i in jconf["entry"]:
        title = i["name"]
        outconf.append("")
        outconf.append("[{}]".format(title))
        for j in i["content"].keys():
            if j[0:4]!="eai:" and not isMatchStringRE(j,skiplist):
                outconf.append("{} = {}".format(j,i["content"][j] if type(i["content"][j]) is not bool else str(i["content"][j]).lower()))
    return "\r\n".join(outconf) if asString else outconf

def isMatchString(subject,skiplist,returnAllResults = False):
    # exclude the parameters which you dont want to bring to config. It automatically do wildcard with add an extra * at the end
    results = [subject[0:len(i)] == i for i in skiplist]
    return True in results if not returnAllResults else results

def isMatchStringRE(subject,skiplist,returnAllResults = False):
    # exclude the parameters which you dont want to bring to config. It automatically do wildcard with add an extra * at the end
    # did not concern about the performance so it is match one by one or should jump out once one matches.
    results = [False if re.compile(i).fullmatch(subject) is None else True for i in skiplist]
    return True in results if not returnAllResults else results

def convertJson2Conf(jconf,asString = False):
    # convert the json object to conf format
    outconf = []
    for i in jconf.keys():
        title = i
        outconf.append("")
        outconf.append("[{}]".format(title))
        for j in jconf[i].keys():
            outconf.append("{} = {}".format(j,jconf[i][j] if type(jconf[i]) is not bool else str(jconf[i]).lower()))
    return "\r\n".join(outconf) if asString else outconf

def getSplunkConfviaREST(server,port,user,password,config,skiplist=[],asJSON=False,asString=False):
    # get the splunk configuration via REST API. if asJSON is true, it disregard the asString config
    # skiplist is a list of string using regex. it has to full match the key so to exclude them. 
    # for example, ['max.*'] filters out all fields started with max. 
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    url="https://{}:{}/services/configs/conf-{}".format(server,port,config)
    #url="https://{}:{}/servicesNS/-/-/configs/conf-{}".format(server,port,config)
    params = {
        "output_mode": "json",
        "count": 0
    }
    response = requests.get(url,params=params,auth=(user,password),verify=False)
    if response.status_code == 200:
        return response.json() if asJSON else converRESTJson2Conf(response.json(),skiplist,asString)
    else:
        return None

def getCommonKeys(object1,object2):
    # extract the same keys exit in both dict object
    ok1 = object1.keys()
    ok2 = object2.keys()
    results = []
    [results.append(i) if i in ok2 else None for i in ok1]
    return results

#----- Read from local file
with open('/home/user/props.conf','r') as f:
    jconf = f.readlines()
    f.close()

conflocal = convertConf2Json(jconf)

#----- Read from remote REST endpoint
user = "admin"
password = "passwd"
server1 = "ipaddress"
port = 8089
config = "props"
# the list of regex is passed for filtering out these keys which you dont want
# by default eai:acl* is added by REST so it is ignored automatically.
respr = getSplunkConfviaREST(server1,port,user,password,config)
confremote = convertConf2Json(respr)

# sample code to compare the output, below is a common analysis steps
o1,o2=diffdict(conflocal,confremote)
# o1 is the key conflocal has but confremote dont
# o2 is the key confremote has but conflocal dont
# use ordereddict to sort the items in the dict so easier to output
od1 = dict(collections.OrderedDict(sorted(o1.items())))
od2 = dict(collections.OrderedDict(sorted(o2.items())))
# list the common keys in the original file
commonkeys = getCommonKeys(conflocal,confremote)
# list the common keys after comparison so we need to pay attention to these keys
attentionkeys = getCommonKeys(od1,od2)
# get the potential conflicting configurations (same key exists in both but configured differently)
co1 = {i:od1[i] for i in od1.keys() if i in attentionkeys}
co2 = {i:od2[i] for i in od2.keys() if i in attentionkeys}


#----- Read from remote REST endpoint dumped json
#with open('./server.json') as f:
#    jconf = json.loads("\r\n".join(f.readlines()))
#    f.close()
#
#outputj = convertRESTJson2Conf(jconf,["conf_replication_include\..*"])
#confj = convertConf2Json(outputj)

