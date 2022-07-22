class Fsm:
    def __init__(self):
        self.states = [
            "None",
            "Initialized",
            "Configured",
            "Running",
            "Paused",
            "Error",
            "Step"            
            ]
        self.actions = {
            "initialize":{"from":["None"], "to":"Initialized"},
            "configure":{"from":["Initialized"], "to":"Configured"},
            "start":{"from":["Configured"], "to":"Running"},
            "stop":{"from":["Running","Paused"], "to":"Configured"},
            "pause":{"from":["Running"], "to":"Paused"},
            "resume":{"from":["Paused"], "to":"Running"},
            "fail":{"from":["Initialized", "Configured", "Running", "Paused"], "to":"Error"},
            "reset":{"from":["Error","Step"],"to":"None"}, # action used for autorestart only
            "step":{"from":["Running"],"to":"Step"}
        }
        self.state = "None"
        self.performingAction = "None"

    def checkFromState(self, actionName):
        if self.performingAction != "None":
            return False
        if actionName in self.actions:
            if self.state in self.actions[actionName]["from"]:
                self.performingAction = actionName
                return True
            else:
                print("[Fsm][checkFromState] Wrong state for this action.")
                return False
        else:
            print("[Fsm][checkFromState] Action not existing in FSM.")
            return False

    def setNewState(self, actionName):
        self.state = self.actions[actionName]["to"]
        self.performingAction = "None"
        return self.state
