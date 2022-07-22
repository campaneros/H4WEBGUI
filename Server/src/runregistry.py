import sys
from copy import deepcopy as dcopy
from datetime import datetime

from influxdb import InfluxDBClient
import urllib3
urllib3.disable_warnings()

dbname = 'ecal_h4'
dbhost = 'ecal-automation-relay.web.cern.ch'
dbport = 80
dbusr = 'ecalgit'
dbpwd = 'ecalPbWO'
dbssl = False

class RunRegistry:
    """
    Update job status and information to the influxdb. 
    Each combination of campaign+era+workflow is called a task.

    The job status is represented by the following table::

       {
           'measurement' : 'run',
           'tags' : {
               'run' : 'H4DAQ run',
               'campaign' : 'TB campaign',
               'trigtype' : 'DAQ trigger mode'
           },
           'time' : timestamp,
           'fields' : {
               'running' : boolean,
               'nspills' : boolean,
               'nevents' : boolean
           }        
       }
    """

    def __init__(self):
        """                              
        Create a new RunRegistry workflow    
        """

        ### create point data template
        self.current_run = self.get_template()
        
        self.db = InfluxDBClient(host=dbhost, port=dbport, username=dbusr, password=dbpwd, ssl=dbssl, database=dbname)

    def get_template(self):
        """
        Reset rundata template
        """

        return {
            'measurement' : 'run',
            'tags' : {
                'run' : -1,
                'campaign' : '',
                'trigtype' : ''
            },
            'time' : None,
            'fields' : {
                'running' : False,
                'crashed' : False,
                'nspills' : 0,
                'nevents' : 0,
                'trigrate' : 0.,
            }
        }
        
    def logRunStart(self, run, campaign='', trigtype=''):
        """
        Log the start of a new run
        
        :param run: H4DAQ run number
        :type run: int
        :param campaign: H4DAQ TB campaign
        :type campaign: str
        """

        data = []

        ### force log the stop of the previous run if still running.
        if self.current_run['fields']['running']:
            data.append(dcopy(self.current_run))
            data[-1]['fields']['running'] = False
            data[-1]['fields']['crashed'] = True
            data[-1]['time'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        ### insert new run into registry and reset counters
        self.current_run = self.get_template()
        data.append(self.current_run)
        data[-1]['time'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        data[-1]['tags']['run'] = int(run)
        data[-1]['tags']['campaign'] = str(campaign)
        data[-1]['tags']['trigtype'] = str(trigtype)
        data[-1]['fields']['running'] = True
        data[-1]['fields']['nspills'] = 0
        data[-1]['fields']['nevents'] = 0
        
        return self.db.write_points(data)

    def logSpill(self, spill, nevents=0, trigrate=-1): 
        """
        Log info from new spill
        
        :param spill: H4DAQ spill number
        :type spill: int
        :param nevents: number of events collected in this spill
        :type nevents: int
        :param trigrate: trigger rate in current spill
        :type trigrate: float
        """

        ### increment counters and push info to db if new spill
        data = self.current_run
        if spill > data['fields']['nspills']:
            data['time'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            data['fields']['running'] = True
            data['fields']['nspills'] = int(spill)
            data['fields']['nevents'] += int(nevents)
            data['fields']['trigrate'] = float(trigrate)
            
            return self.db.write_points([data])

        return 0        

    def logRunStop(self):
        """
        Log the stop of a the current run
        """

        ### insert new run into registry and reset counters
        data = self.current_run
        data['time'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        data['fields']['running'] = False
        
        return self.db.write_points([data])
