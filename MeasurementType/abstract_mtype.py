"""

This holds the abstract measurement type. A measurement type is supposed to take in raw data and output processed data


"""




class abstract_mtype():
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    def parse(self, fname, **idxs):
        pass