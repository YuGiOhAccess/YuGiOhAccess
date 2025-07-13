from game.serverinfo import EdoServerInformation


class TestingServer(EdoServerInformation):
    def __init__(self):
        super().__init__("Test Server", "167.99.22.44", 7922, 7911)

class EUCasualServer(EdoServerInformation):
    def __init__(self):
        super().__init__("EU Central (Casual)", "eu.projectignis.org", 7923, 7912)

class EUCompetitiveServer(EdoServerInformation):
    def __init__(self):
        super().__init__("EU Central (Competitive)", "eu.projectignis.org", 7922, 7911)

class USCasualServer(EdoServerInformation):
    def __init__(self):
        super().__init__("US West (Casual)", "us.projectignis.org", 7922, 7911)

class USCompetitiveServer(EdoServerInformation):
    def __init__(self):
        super().__init__("US West (Competitive)", "us.projectignis.org", 7923, 7912)

class AsiaServer(EdoServerInformation):
    def __init__(self):
        #super().__init__("Asia Central (Casual/Competitive)", "ignis-room.ygopro.cn", 443, "ignis-duel.ygopro.cn:44444")
        super().__init__("Asia Central (Casual/Competitive)", "ignis-room.ygopro.cn", 443, 44444)

def get_servers():
    return [TestingServer(), EUCasualServer(), EUCompetitiveServer(), USCasualServer(), USCompetitiveServer()]
