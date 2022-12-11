import json
import random


class AnalyticsData:
    """
    An in memory persistence object.
    Declare more variables to hold analytics tables.
    """
    # statistics table 1
    # fact_clicks is a dictionary with the click counters: key = doc id | value = click counter
    fact_clicks = dict([])
    
    # statistics table 2 
    #fact_query is a dictionary with the search counters: key = query | value = search counter
    #fact_query_length is a list of the query lengths
    fact_query = dict([])
    fact_query_len = list()

    # statistics table 3
    #fact_query_time is a dictionary with the last time search: key = query | value = last time searched
    fact_query_time = dict([])
    
    # statistics table 3
    #fact_doc_query is a dictionary with the queries related to a visited document: key = doc id | value = list of queries
    fact_doc_query = dict([])
    def save_query_terms(self, terms: str) -> int:
        print(self)
        return random.randint(0, 100000)


class ClickedDoc:
    def __init__(self, doc_id, description, counter):
        self.doc_id = doc_id
        self.description = description
        self.counter = counter

    def to_json(self):
        return self.__dict__

    def __str__(self):
        """
        Print the object content as a JSON string
        """
        return json.dumps(self)
