from actions import Action


class Stdout(Action):
    def __init__(self, log, conf=None):
        Action.__init__(self, log, conf)
        self.log = log
        self.records = []

    def add(self, record):
        self.records.append(record)

    def run(self):
        for record in self.records:
            print(record)
        self.records = []
