import logging
import requests
import json
import tempfile, os, shutil
import configparser
import io

class Controller: 
    """ Manage the operations on the controller """

    __account = ""
    __api_base_url = 'https://' + __account + '.saas.appdynamics.com'
    __api_client_name = ''
    __api_client_secret = ''

    __token = ''
    __my_repo = None
    __tmp_folder = ''

    __typ = "" #Should be app, dashboard or global
    __id = -1
    urls = {}
    __apps = []
    __logger = None

    def __init__(self, account, client_name, client_secret, logger, controllerURL = ""):
        self.__logger = logger
        self.__logger.info("Start initializing Controller object")
        self.__account = account
        self.__api_client_name = client_name
        self.__api_client_secret = client_secret
        if not(controllerURL == ""): self.__api_base_url = 'https://' + account + '.saas.appdynamics.com'
        else: self.__api_base_url = controllerURL
        self.__token = self.generate_token()
        self.__apps = self.get_applications()
        self.__urls = {"action" : "/controller/actions/[application_id]", 
                       "actiontemplate_email" : "/controller/actiontemplate/email",
                       "actiontemplate_http" : "/controller/actiontemplate/httprequest",
                       "dashboard_export" : "/controller/CustomDashboardImportExportServlet?dashboardId=[dashboard_id]",
                       "dashboard_import" : "/controller/CustomDashboardImportExportServlet",
                       "health_rules" : "/controller/healthrules/[application_id]",
                       "transaction_detection" : "/controller/transactiondetection/[application_id]/Default%20Scope/custom/",
                       "policies" : "/controller/policies/[application_id]",
                       "applicationanalyticsservice" : "/controller/analyticsdynamicservice/[application_id]"
                       "get_db_collector" : "/controller/rest/databases/collectors/[configurationId]"
                       }

        for url in self.__urls: self.__urls[url] = self.__api_base_url + self.__urls[url]

        self.__logger.info("Controller object initialized for account: '" + str(account) + "' on Controller: '" + str(self.__api_base_url) + "'")

    def generate_token(self):
        url = self.__api_base_url + "/controller/api/oauth/access_token"
        self.__logger.info("Using OAUTH to obtain access_token from URL: '" + str(url) + "'")     

        d = {"grant_type" : "client_credentials", 
            "client_id" : self.__api_client_name+"@"+self.__account,
            "client_secret" : self.__api_client_secret}
        req = requests.post(url, data=d)

        return req.json()["access_token"]
        
    def get_applications(self):
        if len(self.__apps) > 0: return self.__apps
        url = self.__api_base_url + "/controller/rest/applications?output=JSON"
        returnValue = self.get(url)
        return returnValue

    
    def post(self, url, files=None):
        url = url + "?output=JSON"
        print("POST " + str(url))
        headers = {"Authorization" : "Bearer " + self.__token}
        req = requests.post(url, headers=headers, files=files)
        return req
        
    def get(self, url):
        headers = {"Authorization" : "Bearer " + self.__token}
        req = requests.get(url, headers=headers)

        try:
            returnValue = req.json()
        except ValueError:
            returnValue = req.content
        return returnValue

    #This method use a non-official API which has been obtained from the Controller UI
    def export_dashboard(self, id):
        self.__logger.logging.warning("The export_dashboard method uses an non-official API.")
        
        url = "/controller/restui/dashboards/getAllDashboardsByType/false"
        dashboards = self.get(url)

        dashboard_url = "/controller/CustomDashboardImportExportServlet?dashboardId=" + str(id)
        dashboard_file_name = str(id) + "_dashboard"
        
        self.write_to_git_repo(dashboard_file_name, dashboard_url, "json")
            
			
    def export_controller_wide_config(self):
        print("Exporting controller wide configurations")

        types = {
            "email_action_template" : ["/controller/actiontemplate/email", "json"],        #Email Templates
            "http_request_template" : ["/controller/actiontemplate/httprequest/ ", "json"],
        }

        for typ in types:
            url, form = types[typ]
            filename = "0_" + url.split("/")[-1]
            self.write_to_git_repo(filename, url, form)

    def findApp(self, appname):
        for app in self.__apps:
            if app["name"] == appname:
                return app
        return {}

    def getTransactionDetectionRules(self, app):
        url = self.__urls["transaction_detection"]
        url = url.replace("[application_id]", str(app["id"]))

        data = self.get(url)
        data = data.decode("utf-8")

        return data

    def get_db_collector(self, configId):
        url = self.__urls["get_db_collector"]
        url = url.replace("[configurationId]", configId)

        data = self.get(url)
        data = data.decode("utf-8")
 
        return data


    def postTransactionDetectionRules(self, app, rules):
        f = {"file" : ("file.csv", rules)}
        url = self.__urls["transaction_detection"]
        url = url.replace("[application_id]", str(app["id"]))
        return self.post(url, files=f)

    def migrateConfig(self, sourceAppName, destAppName):
        sourceApp = self.findApp(sourceAppName)
        destApp = self.findApp(destAppName)

        if len(sourceApp) > 0 and len(destApp) > 0:
            self.__logger.info("Start migration from '" + sourceAppName + "' to '" + destAppName + "'")
       
        trx_rules = self.getTransactionDetectionRules(sourceApp)
        resp = self.postTransactionDetectionRules(destApp, trx_rules)
        self.__logger.info("Transaction detection rules migrated. HTTP-Responsecode: " + str(resp.status_code) + " - " +str(resp.reason))


def main():

    Config = configparser.ConfigParser()
    Config.read("config.txt")

    account = Config.get("CONTROLLER", "account")
    client_name = Config.get("CONTROLLER", "api_client_name")
    client_secret = Config.get("CONTROLLER", "api_client_secret")

    log_file_name = Config.get("LOGGING", "file_name")
    log_level = Config.get("LOGGING", "log_level")
    
    logger = logging.getLogger("SYNCHER")
    if log_level == "DEBUG": logger.setLevel(logging.DEBUG)
    elif log_level == "INFO": logger.setLevel(logging.INFO)
    else: 
        print("Logging level not defined - will log to INFO")
        logger.setLevel(logging.INFO)

    fh = logging.FileHandler(log_file_name)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)


    ctrl = Controller(account, client_name, client_secret, logger)
    account, client_name, client_secret = "","",""

    ctrl.migrateConfig("Config-Sync-testSource", "Config-Sync-testDestination")
    
    
    
    rules = [
        {"period" : "daily", "time" : "3am", "source_app_id" : 315, "dest_app_id" : 500, "object_type" : "transaction_detection"}
    ]

    for rule in rules:
        source_app_id = rule["source_app_id"]
        dest_app_id = rule["dest_app_id"]
        object_type = rule["object_type"]
         


if __name__ == "__main__": main()

