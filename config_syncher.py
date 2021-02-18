import requests
import json
import tempfile, os, shutil
import configparser
class Controller: 
    """ Manage the operations on the controller """

    __account = "bosch"
    __api_base_url = 'https://' + __account + '.saas.appdynamics.com'
    __api_client_name = 'config_sync'
    __api_client_secret = '7a6c419-7444-4a55-4d293664b8f9'

    __token = ''
    __my_repo = None
    __tmp_folder = ''

    __typ = "" #Should be app, dashboard or global
    __id = -1
    urls = {}


    def __init__(self):
        self.__token = self.generate_token()

        self.__urls = {"action" : "/controller/actions/[application_id]", 
                       "actiontemplate_email" : "/controller/actiontemplate/email",
                       "actiontemplate_http" : "/controller/actiontemplate/httprequest",
                       "dashboard_export" : "/controller/CustomDashboardImportExportServlet?dashboardId=[dashboard_id]",
                       "dashboard_import" : "/controller/CustomDashboardImportExportServlet",
                       "health_rules" : "/controller/healthrules/[application_id]",
                       "transaction_detection" : "/controller/transactiondetection/application_id/[scope_name]/rule_type/[entry_point_type]/[rule_name]",
                       "policies" : "/controller/policies/[application_id]",
                       "applicationanalyticsservice" : "/controller/analyticsdynamicservice/[application_id]"}


    def generate_token(self):        
        url = self.__api_base_url + "/controller/api/oauth/access_token"

        d = {"grant_type" : "client_credentials", 
            "client_id" : self.__api_client_name+"@"+self.__account,
            "client_secret" : self.__api_client_secret}

        req = requests.post(url, data=d)
        print("req = " + str(req))

        return req.json()["access_token"]
        
    def get_applications(self):
        url = self.__api_base_url + "/controller/rest/applications?output=JSON"
        returnValue = self.get(url)
        return returnValue

    
    def post(self, url):
        url = url + "?output=JSON"
        print("POST " + str(url))
        headers = {"Authorization" : "Bearer " + self.__token}
        req = requests.post(url, headers=headers)
        return req.json()

    def get(self, url):

        print("GET " + str(url))
        headers = {"Authorization" : "Bearer " + self.__token}
        req = requests.get(url, headers=headers)

        try:
            returnValue = req.json()
        except ValueError:
            returnValue = req.content

        return returnValue



    def export_dashboard(self, id):
        print("Exporting dashboards")
        
        #This is a non-standard API and may be removed in the future
        url = "/controller/restui/dashboards/getAllDashboardsByType/false"
        url = self.__api_base_url + url

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




def main():

    Config = configparser.ConfigParser()
    Config.read("config.txt")

    account = Config.get("CONTROLLER", "account")
    client_name = Config.get("CONTROLLER", "api_client_name")
    client_secret = Config.get("CONTROLLER", "api_client_secret")

    ctrl = Controller(account, client_name, client_secret)

    apps = ctrl.get_applications()
    for app in apps: print(app)

    rules = [
        {"period" : "daily", "time" : "3am", "source_app_id" : 315, "dest_app_id" : 500, "object_type" : "transaction_detection"}
    ]

    for rule in rules:
        source_app_id = rule["source_app_id"]
        dest_app_id = rule["dest_app_id"]
        object_type = rule["object_type"]
         


if __name__ == "__main__": main()

