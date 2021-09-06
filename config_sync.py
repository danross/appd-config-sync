
import logging
import requests
import json
import tempfile, os, shutil
import configparser
import io
import json
import sys
from controller import Controller
import re
from argparse import ArgumentParser
from OpsTool import ITMOpsTool

def replace_ignorecase(text, replace, replaceWith):
    insensitive_hippo = re.compile(re.escape(replace), re.IGNORECASE)
    return insensitive_hippo.sub(replaceWith, text)

def main():

    parser = ArgumentParser()
    parser.add_argument("-mo","--mode", dest="mode", help="Select machine,database or application", metavar="mode")

    #application
    parser.add_argument("-san","--SourceAppName", dest="source_appname", help="Select AppDynamics app name", metavar="source_appname")
    parser.add_argument("-sai","--SourceAppId", dest="source_appid", help="Select AppDynamics app id", metavar="source_appid")
    parser.add_argument("-tan","--TargetAppName", dest="target_appname", help="Select AppDynamics app name", metavar="target_appname")
    parser.add_argument("-tai","--TargetAppId", dest="target_appid", help="Select AppDynamics app id", metavar="target_appid")

    #server
    parser.add_argument("-ssg","--SourceSubGroup", dest="source_subgroup", help="Select Source Subggroup", metavar="source_subgroup")
    parser.add_argument("-dsg","--DestSubGroup", dest="dest_subgroup", help="Select Dest Subggroup", metavar="dest_subgroup")

    #database
    parser.add_argument("-l","--Line", dest="line", help="Select a line like PS|BAP|HDEV6-SL0", metavar="line")



    args = parser.parse_args()

    
    Config = configparser.ConfigParser()
    Config.read("config.txt")

    controllerURL = Config.get("CONTROLLER", "controllerURL")
    account = Config.get("CONTROLLER", "account")
    client_name = Config.get("CONTROLLER", "api_client_name")
    client_secret = Config.get("CONTROLLER", "api_client_secret")

    log_file_name = Config.get("LOGGING", "file_name")
    log_level = Config.get("LOGGING", "log_level")
    
    user = Config.get("CONTROLLER", "user")
    password = Config.get("CONTROLLER", "password")
    ceritficateFilePath = Config.get("CONTROLLER", "ceritficateFilePath")

    server_application_id = Config.get("CONTROLLER","server_application_id")
    database_application_id = Config.get("CONTROLLER","database_application_id")
    
    
    logger = logging.getLogger("SYNCHER")
    if log_level == "DEBUG": logger.setLevel(logging.DEBUG)
    elif log_level == "INFO": logger.setLevel(logging.INFO)
    else: 
        print("Logging level not defined - will log to INFO")
        logger.setLevel(logging.INFO)

    fh = logging.FileHandler(log_file_name)
    formatter = logging.Formatter('HR_MIGRATION - %(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ctrl = Controller(account, client_name, client_secret, logger, user=user, password=password, controllerURL=controllerURL, ceritficateFilePath=ceritficateFilePath,server_application_id=server_application_id, database_application_id=database_application_id)
    account, client_name, client_secret = "","",""

    app_name = ""
    app_id = -1
    source_appname, source_appid, target_appname, target_appid,source_subgroup,dest_subgroup = "","","","","",""
    for arg in vars(args):
        value = getattr(args,arg)
        print("'"+str(arg) + "' = '" + str(value)+"'")
        if arg == "mode": mode = value

        #if arg == "source_subgroup": source_subgroup = value
        if arg == "dest_subgroup": dest_subgroup = value

        if arg == "source_appname": source_appname = value
        if arg == "source_appid": source_appid = value
        if arg == "target_appname": target_appname = value
        if arg == "target_appid": target_appid = value
        
        if arg == "line" : line = value

    if mode == "database":
        line = line.split("|")
        opstool = ITMOpsTool("user","pwd")

        db = opstool.getDatabaseByLine(line)
        print("db = " + str(db))
            
        oltp_db = db["oltp_db"]
        olap_db = db["olap_db"]
        print("oltp_db = " + str(oltp_db))
        print("olap_db = " + str(olap_db))
        
        hrs = ctrl.get_health_rules_by_reference_database(database_application_id)


    if mode == "machine":
        ctrl.ui_login()
        
        #if not ctrl.doesSubGroupExist(source_subgroup):
        #    print("source_subgroup '" + str(source_subgroup) + "' does not exist! Exit")
        #    sys.exit(-1)

        if not ctrl.doesSubGroupExist(dest_subgroup):
            print("dest_subgroup '" + str(dest_subgroup) + "' does not exist! Exit")
            sys.exit(-1)

        #hrs = ctrl.get_health_rules_by_server_subgroup(source_subgroup)
        #SubGroup = "Root|Machine|Path|Here"

        hrs = ctrl.get_health_rules_with_details(server_application_id)

        for hr in hrs:
            hr_name = hr["name"]

            if hr_name.lower().endswith("template"):
                print("hr before change = " + str(hr))
                if "serverSelectionCriteria" in hr["affects"]:
                    hr["affects"]["serverSelectionCriteria"]["affectedServers"]["subGroups"] = ["Root|"+dest_subgroup]

                    dest_subgroups_segments = dest_subgroup.split("|")

                    suffix = dest_subgroups_segments[-2] + "-" + dest_subgroups_segments[-1]
                    prefix = ""

                    for i in range(len(dest_subgroups_segments)-2): prefix = prefix + dest_subgroups_segments[i] + "-"
                    prefix = prefix[:-1]


                    hr["name"] = replace_ignorecase(hr["name"], "template", suffix)
                    hr["name"] = prefix + hr["name"]

                    
                print("hr after change = " + str(hr))




        ctrl.create_health_rules(server_application_id, hrs)
        
    if mode == "application":

        if not(source_appname == None) and not(source_appid == None):
            print("Do not provide source_appname and source_appid! Abort")
            sys.exit(-1)

        if not(target_appname == None) and not(target_appid == None):
            print("Do not provide target_appname and target_appid! Abort")
            sys.exit(-1)

        if not(source_appname == ""): source_app_id = ctrl.get_id_by_app_name(source_appname)
        if not(target_appname == ""): target_appid = ctrl.get_id_by_app_name(target_appname)
        
        health_rules = ctrl.get_health_rules(source_app_id)
        health_rules_details = []
        for hr in health_rules: 
            hr_id = hr["id"]
            tmp = ctrl.get_health_rule_details(source_app_id, hr_id)
            health_rules_details.append(tmp)

        ctrl.create_health_rules(target_appid, health_rules_details)



if __name__ == "__main__": main()

