
class ITMOpsTool:

    __user = ""
    __pwd = ""


    def __init__(self, user, pwd):
        self.__user = user
        self.__pwd = pwd


    def getDatabaseByLine(self, segments):
        return {"id" : 6, "bu" : "PS", "site" : "BaP", "name" : "HDEV6-SL0", "oltp_db" : "BAPOLTP", "olap_db" : "BAPOLAP"}