import requests

class NotificationInterface:
    def __init__(self, notification_level):
        print("notification level: ", notification_level)
        self.mattermost = NotificationMattermost()

    def critical(self, message):
        self.mattermost.critical(message)


class NotificationMattermost:
    def __init__(self):
        self.base_url = "https://mattermost.web.cern.ch/hooks/"
        # self.websocket_id = "uf36fct9winqbgtin5k5jzuz9r"
        self.websocket_id = "yhzroeesubdszfxnhs6of4eunh"

    def critical(self, message):
        print("CRITICAL")
        url = self.base_url + self.websocket_id
        critical_message = "[critical] " + message
        critical_data = {"text": critical_message}
        print(url)
        print(str(critical_data))
        r = requests.post(url, json = critical_data)
        print(r.text)

# curl -i -X POST -H 'Content-Type: application/json' -d '{"text": "Hello, this is some text\nThis is more text. :tada:"}' https://mattermost.web.cern.ch/hooks/uf36fct9winqbgtin5k5jzuz9r
