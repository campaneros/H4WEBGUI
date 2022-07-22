from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')
db = client['test']
RunInfos = db['runs_infos']

# "", "-", "cosmic", "-1" replaced by float(-1)
# res = RunInfos.find({'beamEnergy': "-1"})
# for entry in res:
#     RunInfos.update_one({'_id': entry['_id']}, {'$set': {'beamEnergy': float(-1)}})

# If these field exist, then replace them with their corresponding float
# res = RunInfos.find({'beamEnergy':{'$exists': True}})
# for entry in res:
#         RunInfos.update_many({'_id': entry['_id']},{'$set': {'beamEnergy': float(entry['beamEnergy'])}})

# res = RunInfos.find({'evinrun':{'$exists': True}})
# for entry in res:
#         RunInfos.update_many({'_id': entry['_id']},{'$set': {'evinrun': float(entry['evinrun'])}})

# res = RunInfos.find({'tableY':{'$exists': True}})
# for entry in res:
#         RunInfos.update_many({'_id': entry['_id']},{'$set': {'tableY': float(entry['tableY'])}})

runs_map = {}
runs_map['MTD_H4_Sept2018'] = {'min': 12373, 'max': 666666}
runs_map['ECAL_H2_Sept2018'] = {'min': 12111, 'max': 12372}
runs_map['AIDA2020_H4_June2018'] = {'min': 11625, 'max': 12110}
runs_map['ECAL_H4_Jun2018'] = {'min': 11001, 'max': 11624}

import pprint
pprint.pprint (runs_map)

def get_tbcamp_from_run(run):
    for key, val in runs_map.items():
        if run >= val['min'] and run <= val['max']:
            print(key)
            return key
    return "no campaign"

res = RunInfos.find()
for entry in res:
        RunInfos.update_many({'_id': entry['_id']},{'$set': {'tbCamp': get_tbcamp_from_run(entry['_id']) }})
