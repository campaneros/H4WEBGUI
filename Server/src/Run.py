class Run:
    def __init__(self):
      self._id = 0
      self.startTime = 0
      self.stopTime = 0
      self.scTag = ""
      self.scVer = 0
      self.rkTag = ""
      self.rkVer = 0
      self.activeDRs = []
      self.eventsPerSpill = 0
      self.activeInputs = []
      self.runType = ""
      self.tablePosTag = ""
      self.tablePos = ""
      self.tbCamp = ""
      self.tableX = 0.
      self.tableY = 0.
      self.isGood = True
      self.failed = False
      self.beamEnergy = -1
      self.beamType = ""
      self.evinrun = 0
