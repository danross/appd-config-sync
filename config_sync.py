
import logging
import requests
import json
import tempfile, os, shutil
import configparser
import io
import json
import sys
from controller import Controller
from argparse import ArgumentParser


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

    ctrl = Controller(account, client_name, client_secret, logger, user=user, password=password, controllerURL=controllerURL, ceritficateFilePath=ceritficateFilePath)
    account, client_name, client_secret = "","",""

    app_name = ""
    app_id = -1
    source_appname, source_appid, target_appname, target_appid,source_subgroup,dest_subgroup = "","","","","",""
    for arg in vars(args):
        value = getattr(args,arg)
        print("'"+str(arg) + "' = '" + str(value)+"'")
        if arg == "mode": mode = value

        if arg == "source_appname": source_appname = value
        if arg == "source_appid": source_appid = value
        if arg == "target_appname": target_appname = value
        if arg == "target_appid": target_appid = value

        if arg == "source_subgroup": source_subgroup = value
        if arg == "dest_subgroup": dest_subgroup = value
        
    if mode == "machine":
        ctrl.ui_login()
        
        if not ctrl.doesSubGroupExist(source_subgroup):
            print("source_subgroup '" + str(source_subgroup) + "' does not exist! Exit")
            sys.exit(-1)

        if not ctrl.doesSubGroupExist(dest_subgroup):
            print("dest_subgroup '" + str(dest_subgroup) + "' does not exist! Exit")
            sys.exit(-1)

        hrs = ctrl.get_health_rules_by_server_subgroup(source_subgroup)
        #SubGroup = "Root|Machine|Path|Here"

        for hr in hrs:
            print("hr = " + str(hr))
            hr["affects"]["serverSelectionCriteria"]["affectedServers"]["subGroups"] = [dest_subgroup]
            hr["name"] = hr["name"].replace("Template",dest_subgroup.rsplit("|", 1)[-1] )
            
        ctrl.create_health_rules(9, hrs)

        
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






    """
    f = open('db_collector_structure.json')
    collector = json.load(f)
    f.close()

    #collector["customMetrics"] = "select count(*) from table"
    for key in collector: print("collector["+str(key)+"] = " + str(collector[key]))

    ctrl.create_db_collector(collector)
    """

    #db_collector = ctrl.get_db_collector(17)
    
    #for key in db_collector:
    #    print("db_collector["+str(key)+"] = " + str(db_collector[key]))
    
    #del db_collector["id"]

    #db_collector["name"] = ""
    
    #print("Printing collectors with customMetrics not null")
    #db_collectors = ctrl.get_all_db_collectors()
    #for collector in db_collectors:
    #    #print("collector = " + str(collector))
    #    customMetrics = collector["config"]["customMetrics"]
    #    if not (customMetrics == None):
    #        print("customMetrics = " + str(customMetrics))
#
#            for key in collector:        
#                print("collector["+str(key)+"] = " + str(collector[key]))
    
    
    
    #rules = [
    #    {"period" : "daily", "time" : "3am", "source_app_id" : 315, "dest_app_id" : 500, "object_type" : "transaction_detection"}
    #]

    #for rule in rules:
    #    source_app_id = rule["source_app_id"]
    #    dest_app_id = rule["dest_app_id"]
    #    object_type = rule["object_type"]
         


if __name__ == "__main__": main()

