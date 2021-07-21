import base64
import json
import requests

class Controller: 
    """ Manage the operations on the controller """

    __account = ""
    __api_base_url = 'https://' + __account + '.saas.appdynamics.com'
    __api_client_name = ''
    __api_client_secret = ''

    __token = ''
    __my_repo = None
    __tmp_folder = ''
    __uiSession = None

    __typ = "" #Should be app, dashboard or global
    __id = -1
    urls = {}
    __apps = None
    __servers = None
    __logger = None
    __verify = False

    def __init__(self, account, client_name, client_secret, logger, controllerURL = "", user="", password="",ceritficateFilePath="") :
        self.__logger = logger
        self.__logger.info("Start initializing Controller object")
        self.__account = account
        self.__api_client_name = client_name
        self.__api_client_secret = client_secret
        if controllerURL == "": self.__api_base_url = 'https://' + account + '.saas.appdynamics.com'
        else: self.__api_base_url = controllerURL
        
        if not(ceritficateFilePath == ""): self.__verify = ceritficateFilePath
        self.__logger.info("self.__verify = " + str(self.__verify))
        self.__logger.info("self.__api_base_url = " + str(self.__api_base_url))
        self.__token = self.generate_token()
        
        self.__user = user
        self.__password = password

        self.__urls = {"action" : "/controller/actions/[application_id]", 
                       "actiontemplate_email" : "/controller/actiontemplate/email",
                       "actiontemplate_http" : "/controller/actiontemplate/httprequest",
                       "dashboard_export" : "/controller/CustomDashboardImportExportServlet?dashboardId=[dashboard_id]",
                       "dashboard_import" : "/controller/CustomDashboardImportExportServlet",
                       "health_rules" : "/controller/alerting/rest/v1/applications/[application_id]/health-rules?output=JSON",
                       "health_rule" :  "/controller/alerting/rest/v1/applications/[application_id]/health-rules/[health-rule-id]",
                       "transaction_detection" : "/controller/transactiondetection/[application_id]/Default%20Scope/custom/",
                       "policies" : "/controller/policies/[application_id]",
                       "applicationanalyticsservice" : "/controller/analyticsdynamicservice/[application_id]",
                       "get_db_collector" : "/controller/rest/databases/collectors/[configurationId]",
                       "get_all_collectors" : "/controller/rest/databases/collectors",
                       "create_db_collector" : "/controller/rest/databases/collectors/create",
                       "ui_login" : "/controller/auth?action=login",
                       "get_machine_ids" : "/controller/sim/v2/user/machines/keys",
                       "get_machines_details" : "/controller/sim/v2/user/metrics/query/machines",
                       "get_machines_bulk" : "/controller/sim/v2/user/machines/bulk"
                       }



        for url in self.__urls: self.__urls[url] = self.__api_base_url + self.__urls[url]
        self.ui_login()

        self.__logger.info("Controller object initialized for account: '" + str(account) + "' on Controller: '" + str(self.__api_base_url) + "'")

    def generate_token(self):
        url = self.__api_base_url + "/controller/api/oauth/access_token"
        self.__logger.info("Using OAUTH to obtain access_token from URL: '" + str(url) + "'")

        d = {"grant_type" : "client_credentials", 
            "client_id" : self.__api_client_name+"@"+self.__account,
            "client_secret" : self.__api_client_secret}
                
        req = requests.post(url, data=d, verify=self.__verify)
        self.__logger.debug("req = " + str(req))
        self.__logger.debug("req.content = " + str(req.content))
        self.__logger.debug("req.json() = " + str(req.json()))
        return req.json()["access_token"]
        
    def ui_login(self):
        loginUrl = self.__urls["ui_login"]

        encoded_pass = base64.b64encode((self.__password.encode('ascii')))
        formData = {"accountName" : self.__account, "userName" : self.__user, "password" : encoded_pass}


        headers = {"Accept" : "application/json"}
        s = requests.Session()

        resp = s.post(loginUrl, data=formData, headers=headers,verify=self.__verify)

        self.__logger.debug("resp = " + str(resp))
        self.__logger.debug("resp.headers = " + str(resp.headers))
        self.__logger.debug("resp.content = " + str(resp.content))
        self.__uiSession = s

    def getServerList(self):
        if self.__servers == None:
            machine_id_url = self.__urls["get_machine_ids"]
            machine_bulk = self.__urls["get_machines_bulk"]

            headers = {
                'Accept': 'application/json, text/plain, */*','Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'   
                }
            data = '{"filter":{"appIds":[],"nodeIds":[],"tierIds":[],"types":["PHYSICAL","CONTAINER_AWARE"]},"sorter":{"field":"HEALTH","direction":"ASC"}}'

            response = self.__uiSession.post(machine_id_url, headers=headers, data=data)
            respJson = response.json()

            machine_ids = [mach["machineId"] for mach in respJson["machineKeys"]]

            data = {"machineIds":machine_ids,"responseFormat":"LITE"}

            response = self.__uiSession.post(machine_bulk, headers=headers, data=json.dumps(data))

            machines = response.json()["machineDTOs"]
            self.__servers = machines
        else: machines = self.__servers

        return [(key, machines[key]["hostId"], machines[key]["name"], machines[key]["hierarchy"]) for key in machines]

    def doesSubGroupExist(self, subgroup):
        subgroup = subgroup.split("|")
        server_list = self.getServerList()
        for server in server_list: 
            if server[-1] == subgroup: return True
        return False

    def get_applications(self):
        if self.__apps == None:
            url = self.__api_base_url + "/controller/rest/applications?output=JSON"
            returnValue = self.get(url)
            self.__apps = returnValue
        return self.__apps

    def get_id_by_app_name(self, appname):
        apps = self.get_applications()

        for app in apps:
            if app["name"] == appname: 
                return app["id"]

        return -1
    
    def post(self, url, data=None, files=None, apiClient=True):
        #url = url + "?output=JSON"
        self.__logger.info("POST " + str(url))
        if apiClient:
            headers = {"Authorization" : "Bearer " + self.__token, "Accept" : "application/json;", "Content-type" : "application/json"}
            req = requests.post(url, headers=headers, files=files, data=json.dumps(data), verify=self.__verify)
        else:
            auth = (self.__user+"@"+self.__account, self.__password)
            headers = {"Accept" : "application/json;", "Content-type" : "application/json"}
            self.__logger.debug("auth = " + str(auth))
            req = requests.post(url, auth=auth, data=json.dumps(data), headers=headers,verify=self.__verify)
            
        return req

    def delete(self, url, data=None, files=None, apiClient=True):
        #url = url + "?output=JSON"
        self.__logger.info("DELETE " + str(url))
        if apiClient:
            headers = {"Authorization" : "Bearer " + self.__token}#, "Accept" : "application/json;", "Content-type" : "application/json"}
            req = requests.delete(url, headers=headers, verify=self.__verify)#, files=files, data=json.dumps(data))
        else:
            auth = (self.__user+"@"+self.__account, self.__password)
            headers = {"Accept" : "application/json;", "Content-type" : "application/json"}
            self.__logger.debug("auth = " + str(auth))
            req = requests.delete(url, auth=auth, data=json.dumps(data), headers=headers, verify=self.__verify)
            
        return req
        
    def get(self, url, apiClient=True):
        self.__logger.info("GET " + str(url))
        if apiClient:
            headers = {"Authorization" : "Bearer " + self.__token}
            #print("get.headers = " + str(headers))
            req = requests.get(url, headers=headers,verify=self.__verify)
        else:
            auth = (self.__user+"@"+self.__account, self.__password)
            #print("auth = " + str(auth))
            req = requests.get(url, auth=auth,verify=self.__verify)
            
            
        #print("get.req = " + str(req))
        
        try:
            returnValue = req.json()
        except ValueError:
            returnValue = req.content
        return returnValue

    def get_health_rules(self, app_id):
        url = self.__urls["health_rules"]
        url = url.replace("[application_id]", str(app_id))
        response = self.get(url)
        return response

    def get_health_rules_by_server_subgroup(self, subgroup):
        hrs = self.get_health_rules(9)
        hr_result = []

        self.__logger.info("subgroup = " + str(subgroup))
        for hr in hrs:
            self.logger.debug("hr = " + str(hr))
            hr_id = hr["id"]
            full_hr = self.get_health_rule_details(9,hr_id)
            serverSelectionScope = full_hr["affects"]["serverSelectionCriteria"]["affectedServers"]["severSelectionScope"]

            if serverSelectionScope == "SERVERS_WITHIN_SUBGROUP":
                currentSubGroups = serverSelectionScope = full_hr["affects"]["serverSelectionCriteria"]["affectedServers"]["subGroups"]

                contains = False
                for currentSubGroup in currentSubGroups: 
                    if subgroup in currentSubGroup: contains = True

                if contains: hr_result.append(full_hr)
        return hr_result

    def get_health_rule_details(self, app_id, health_rule_id):
        url = self.__urls["health_rule"]

        url = url.replace("[application_id]", str(app_id))
        url = url.replace("[health-rule-id]", str(health_rule_id))
        response = self.get(url)
        return response


    def get_health_rule_names(self, app_id):
        existing_hrs = self.get_health_rules(app_id)
        return [(hr["id"], hr["name"]) for hr in existing_hrs]

    def doesHRExists(self, hr_name, targetHRNames):
        hr_name = hr_name.lower()
        for (hr_id,hr) in targetHRNames:
            hr = hr.lower()
            if (hr_name in hr and "custom" in hr) or hr_name == hr:
                    return (hr_id,hr)
        return (None,None)

    def create_health_rules(self, app_id,health_rules):
        
        existing_hrs = self.get_health_rule_names(app_id)
        self.__logger.info("existing_hrs = " + str(existing_hrs))
        create_url = self.__urls["health_rules"]
        create_url = create_url.replace("[application_id]", str(app_id))
        self.__logger.info("create_url = " + str(create_url))
        for hr in health_rules:
            (hr_id,hr_name) = self.doesHRExists(hr["name"],existing_hrs)
            del hr["id"]
            self.__logger.debug("hr = " + str(hr))
            #HR already exists and it not customized
            if not(hr_name == None) and not("custom" in hr_name):
                delete_url = self.__urls["health_rule"]
                delete_url = delete_url.replace("[application_id]", str(app_id))
                delete_url = delete_url.replace("[health-rule-id]", str(hr_id))
                
                self.__logger.debug("Delete existing HR and recreate it: '" + str(hr_name) + "'")
                response = self.delete(delete_url)
                self.__logger.debug("response = " + str(response))
                response = self.post(create_url, data=hr)
                self.__logger.debug("response = " + str(response))

            #HR does not exists
            elif hr_name == None:
                self.__logger.debug("Create new HR as it does not exists in the app")
                response = self.post(create_url, data=hr)
                self.__logger.debug("response.json() = " + str(response.json()))


    #This method use a non-official API which has been obtained from the Controller UI
    def export_dashboard(self, id):
        self.__logger.logging.warning("The export_dashboard method uses an non-official API.")
        
        url = "/controller/restui/dashboards/getAllDashboardsByType/false"
        dashboards = self.get(url)

        dashboard_url = "/controller/CustomDashboardImportExportServlet?dashboardId=" + str(id)
        dashboard_file_name = str(id) + "_dashboard"
        
        self.write_to_git_repo(dashboard_file_name, dashboard_url, "json")
            
			
    def export_controller_wide_config(self):
        self.__logger.info("Exporting controller wide configurations")

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
        url = url.replace("[configurationId]", str(configId))

        data = self.get(url, apiClient=False) 
        return data

    def get_all_db_collectors(self):
        url = self.__urls["get_all_collectors"]        
        self.__logger.info("url = " + str(url))

        data = self.get(url,apiClient=False) 
        return data

    def create_db_collector(self, requestData):
        url = self.__urls["create_db_collector"]
        self.__logger.info("url = " + str(url))

        resp = self.post(url, data=requestData, apiClient=True)
        self.__logger.info("resp = " + str(resp))
        self.__logger.info("resp.reason = " + str(resp.reason))


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
