import os
from json import JSONEncoder

# pip install httpagentparser
import httpagentparser  # for getting the user agent as json
import nltk
from flask import Flask, render_template, session
from flask import request

from myapp.analytics.analytics_data import AnalyticsData, ClickedDoc
from myapp.search.load_corpus import *
from myapp.search.objects import Document, StatsDocument
from myapp.search.search_engine import SearchEngine

import numpy as np

# *** for using method to_json in objects ***
def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj)


_default.default = JSONEncoder().default
JSONEncoder.default = _default

# end lines ***for using method to_json in objects ***

# instantiate the Flask application
app = Flask(__name__)

# random 'secret_key' is used for persisting data in secure cookie
app.secret_key = 'afgsreg86sr897b6st8b76va8er76fcs6g8d7'
# open browser dev tool to see the cookies
app.session_cookie_name = 'IRWA_SEARCH_ENGINE'

# instantiate our search engine
search_engine = SearchEngine()

# instantiate our in memory persistence
analytics_data = AnalyticsData()

# print("current dir", os.getcwd() + "\n")
# print("__file__", __file__ + "\n")
full_path = os.path.realpath(__file__)
path, filename = os.path.split(full_path)
# print(path + ' --> ' + filename + "\n")
# load documents corpus into memory.
#file_path = path + "/../data/tw_hurricane_data.json"
#corpus = load_corpus(file_path)
#print("loaded corpus. first elem:", list(corpus.values())[0])

## OUR CODE
file_path_processed = path + "/../processed_tweets.csv"
df = load_processed_tweets_from_csv(file_path_processed)
tweets_dicts = map(extract_tweet_vocabulary, df['Tweet'], df['DocID'])
vocabulary = merge_dicts(tweets_dicts)
L_ave = np.mean([len(x.split()) for x in df.Tweet])
dictionary_doc = df.copy().drop(columns=['Username', 'Date', 'Hashtags', 'Likes', 'Retweets', 'Url'])
dictionary_doc = dictionary_doc.set_index('DocID').T.to_dict('list')
dictionary_doc = {k: x[0].split() for k, x in dictionary_doc.items()}
file_path = path + "/../data/tw_hurricane_data.json"
doc2tweet = docID2tweet(file_path)
print(type(doc2tweet))
##END OF OUR CODE

# Home URL "/"
@app.route('/')
def index():
    print("starting home url /...")

    # flask server creates a session by persisting a cookie in the user's browser.
    # the 'session' object keeps data between multiple requests
    session['some_var'] = "IRWA 2021 home"

    user_agent = request.headers.get('User-Agent')
    print("Raw user browser:", user_agent)

    user_ip = request.remote_addr
    agent = httpagentparser.detect(user_agent)

    print("Remote IP: {} - JSON user browser {}".format(user_ip, agent))

    print(session)

    return render_template('index.html', page_title="Welcome")


@app.route('/search', methods=['POST'])
def search_form_post():
    search_query = request.form['search-query']

    session['last_search_query'] = search_query

    search_id = analytics_data.save_query_terms(search_query)

    results = search_engine.search(doc2tweet, search_query, search_id, vocabulary, L_ave, dictionary_doc, df)

    found_count = len(results)
    session['last_found_count'] = found_count

    print(session)

    return render_template('results.html', results_list=results, page_title="Results", found_counter=found_count)


@app.route('/doc_details', methods=['GET'])
def doc_details():
    # getting request parameters:
    # user = request.args.get('user')

    print("doc details session: ")
    print(session)

    res = session["some_var"]

    print("recovered var from session:", res)

    # get the query string parameters from request
    clicked_doc_id = request.args["id"]
    p1 = int(request.args["search_id"])  # transform to Integer
    p2 = int(request.args["param2"])  # transform to Integer
    print("click in id={}".format(clicked_doc_id))

    # store data in statistics table 1
    if clicked_doc_id in analytics_data.fact_clicks.keys():
        analytics_data.fact_clicks[clicked_doc_id] += 1
    else:
        analytics_data.fact_clicks[clicked_doc_id] = 1

    print("fact_clicks count for id={} is {}".format(clicked_doc_id, analytics_data.fact_clicks[clicked_doc_id]))

    return render_template('doc_details.html', clicked_doc_id=clicked_doc_id, page_title='Document Details')


@app.route('/stats', methods=['GET'])
def stats():
    """
    Show simple statistics example. ### Replace with dashboard ###
    :return:
    """

    docs = []
    # ### Start replace with your code ###

    for doc_id in analytics_data.fact_clicks:
        row: Document = df[df.DocID==doc_id].iloc[0]
        count = analytics_data.fact_clicks[doc_id]
        doc = StatsDocument(row.DocID, row.Username, doc2tweet[row.DocID], row.Date, row.Url, count)
        docs.append(doc)

    # simulate sort by ranking
    docs.sort(key=lambda doc: doc.count, reverse=True)
    return render_template('stats.html', clicks_data=docs)
    # ### End replace with your code ###


@app.route('/dashboard', methods=['GET'])
def dashboard():
    visited_docs = []
    print(analytics_data.fact_clicks.keys())
    for doc_id in analytics_data.fact_clicks.keys():
        d: Document = df[df.DocID==doc_id].iloc[0]
        doc = ClickedDoc(doc_id, doc2tweet[d.DocID], analytics_data.fact_clicks[doc_id])
        visited_docs.append(doc)

    # simulate sort by ranking
    visited_docs.sort(key=lambda doc: doc.counter, reverse=True)
    visited_ser=[]
    for doc in visited_docs:
        visited_ser.append(doc.to_json())
    return render_template('dashboard.html', visited_docs=visited_ser)


@app.route('/sentiment')
def sentiment_form():
    return render_template('sentiment.html')


@app.route('/sentiment', methods=['POST'])
def sentiment_form_post():
    text = request.form['text']
    nltk.download('vader_lexicon')
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    sid = SentimentIntensityAnalyzer()
    score = ((sid.polarity_scores(str(text)))['compound'])
    return render_template('sentiment.html', score=score)


if __name__ == "__main__":
    app.run(port=8088, host="0.0.0.0", threaded=False, debug=True)
