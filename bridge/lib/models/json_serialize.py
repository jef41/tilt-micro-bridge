#import pickle
import json
# debug seems to be used for logging mostly - needs a test in CPython to see output
class JsonSerialize:
    #def json(self):
    def toJson(self):
        #return pickle.encode(self, unpicklable=False)
        return json.dumps(self.__dict__)