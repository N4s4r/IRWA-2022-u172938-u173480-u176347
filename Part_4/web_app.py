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
import time
from datetime import datetime

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

full_path = os.path.realpath(__file__)
path, filename = os.path.split(full_path)

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
    #initialise num of clicks
    session['Num_clicks'] = 0
    
    if 'dwell_time' in session.keys():
        now_ = time.time()
        session['dwell_time'] = now_ - session['dwell_time']
        
    user_agent = request.headers.get('User-Agent')
    print("Raw user browser:", user_agent)

    user_ip = request.remote_addr
    agent = httpagentparser.detect(user_agent)
    
    browser = agent['browser']['name']
    if browser in analytics_data.fact_browser.keys():
        analytics_data.fact_browser[browser] += 1
    else:
        analytics_data.fact_browser[browser] = 1
        
    print("Remote IP: {} - JSON user browser {}".format(user_ip, agent))

    print(session)
    
    return render_template('index.html', page_title="Welcome")


@app.route('/search', methods=['POST'])
def search_form_post():
    session['Num_clicks']+=1
    search_query = request.form['search-query']
    
    # Add the query to analytics_data
    if search_query in analytics_data.fact_query.keys():
        analytics_data.fact_query[search_query] += 1
    else:
        analytics_data.fact_query[search_query] = 1
        terms = search_query.split()
        for term in terms:
            if term in analytics_data.fact_terms.keys():
                analytics_data.fact_terms[term] += 1
            else:
                analytics_data.fact_terms[term] = 1
    analytics_data.fact_query_len.append(len(search_query.split()))
        
    analytics_data.fact_query_time[search_query] = datetime.now()
    
    session['last_search_query'] = search_query

    search_id = analytics_data.save_query_terms(search_query)

    results = search_engine.search(doc2tweet, search_query, search_id, vocabulary, L_ave, dictionary_doc, df)

    found_count = len(results)
    session['last_found_count'] = found_count

    print(session)
    dwell_time = 0.0
    if 'dwell_time' in session.keys():
        dwell_time = session['dwell_time']
    return render_template('results.html', results_list=results, page_title="Results", found_counter=found_count, dwell_time=round(dwell_time, 2))


@app.route('/doc_details', methods=['GET'])
def doc_details():
    session['Num_clicks']+=1
    session['dwell_time']=time.time()

    print("doc details session: ")
    print(session)

    res = session["some_var"]

    print("recovered var from session:", res)

    # get the query string parameters from request
    clicked_doc_id = request.args["id"]
    p1 = int(request.args["search_id"])  # transform to Integer
    ranking = int(request.args["ranking"])  # transform to Integer
    print("click in id={}".format(clicked_doc_id))

    # store data in statistics table 1
    if clicked_doc_id in analytics_data.fact_clicks.keys():
        analytics_data.fact_clicks[clicked_doc_id] += 1
    else:
        analytics_data.fact_clicks[clicked_doc_id] = 1
        
    if clicked_doc_id not in analytics_data.fact_doc_query.keys():
        analytics_data.fact_doc_query[clicked_doc_id]=set()
    analytics_data.fact_doc_query[clicked_doc_id].add((session['last_search_query'], ranking))
        
    
    print("fact_clicks count for id={} is {}".format(clicked_doc_id, analytics_data.fact_clicks[clicked_doc_id]))
    result_item = df[df.DocID==clicked_doc_id].iloc[0]
    tweet = doc2tweet[clicked_doc_id]
    return render_template('doc_details.html', clicked_doc_id=clicked_doc_id, result_item=result_item, tweet=tweet, page_title='Document Details')


@app.route('/stats', methods=['GET'])
def stats():
    session['Num_clicks']+=1
    """
    Show simple statistics example. ### Replace with dashboard ###
    :return:
    """

    docs = []

    for doc_id in analytics_data.fact_clicks:
        row: Document = df[df.DocID==doc_id].iloc[0]
        count = analytics_data.fact_clicks[doc_id]
        doc = StatsDocument(row.DocID, row.Username, doc2tweet[row.DocID], row.Date, row.Url, count)
        docs.append(doc)

    docs.sort(key=lambda doc: doc.count, reverse=True)
    
    queries = []
    print(analytics_data.fact_query.keys())
    for query in analytics_data.fact_query.keys():
        q: Query = query
        doc = ClickedDoc(query, 'Last time searched: '+str(analytics_data.fact_query_time[query]), analytics_data.fact_query[query])
        queries.append(doc)

    queries.sort(key=lambda doc: doc.counter, reverse=True)
    queries_ser=[]
    for q in queries:
        queries_ser.append(q.to_json())
    doc_queries = []
    for doc_id in analytics_data.fact_doc_query:
        queries = analytics_data.fact_doc_query[doc_id]
        doc = ClickedDoc(doc_id, queries, len(queries))
        doc_queries.append(doc)

    doc_queries.sort(key=lambda doc: doc.counter, reverse=True)
    doc_queries_ser=[]
    for dq in doc_queries:
        doc_queries_ser.append(dq.to_json())
        
    terms=[]
    for term in analytics_data.fact_terms.keys():
        q: Term = term
        term_info = ClickedDoc(term, analytics_data.fact_terms[term], analytics_data.fact_terms[term])
        terms.append(term_info)

    terms.sort(key=lambda term_info: term_info.counter, reverse=True)
    terms_ser=[]
    for t in terms:
        terms_ser.append(t.to_json())
    return render_template('stats.html', clicks_data=docs, searched_queries = queries_ser, doc_queries=doc_queries, terms=terms_ser)
    
    
@app.route('/num_terms', methods=['GET'])
def num_terms():
    session['Num_clicks']+=1
    """
    Show simple statistics example. ### Replace with dashboard ###
    :return:
    """
    X = list(set(analytics_data.fact_query_len))
    Y = list()
    for x in X:
        y = analytics_data.fact_query_len.count(x)
        Y.append(y)
    return render_template('num_terms.html', x=X, y=Y)
    # ### End replace with your code ###
    
@app.route('/browsers', methods=['GET'])
def browsers():
    session['Num_clicks']+=1
    """
    Show simple statistics example. ### Replace with dashboard ###
    :return:
    """
    browsers=analytics_data.fact_browser.items()
    browsers= sorted(browsers, key=lambda x: x[1])
    X_browsers = [str(x[0]) for x in browsers]
    Y_browsers = [x[1] for x in browsers]
    return render_template('browsers.html', x_browsers=X_browsers, y_browsers=Y_browsers)
    # ### End replace with your code ###



    
@app.route('/user', methods=['GET'])
def user():
    session['Num_clicks']+=1
    """
    Show simple statistics example. ### Replace with dashboard ###
    :return:
    """
    user_agent = request.headers.get('User-Agent')
    print("Raw user browser:", user_agent)

    user_ip = request.remote_addr
    agent = httpagentparser.detect(user_agent)

    print("Remote IP: {} - JSON user browser {}".format(user_ip, agent))
    docs = []
    # ### Start replace with your code ###
    info = dict()
    if analytics_data.fact_query_time:
        info['Query']=session['last_search_query']
        info['Date']=analytics_data.fact_query_time[info['Query']]
    else:
        info['Query']='Nothing searched yet'
        info['Date']='-'
    info['Num_queries']=len(analytics_data.fact_query_time.keys())
    info['Num_clicks']=session['Num_clicks']
    
    return render_template('user.html', user=user_agent, ip=user_ip, agent=agent, info=info, session=session)
    # ### End replace with your code ###
    
@app.route('/dashboard', methods=['GET'])
def dashboard():
    session['Num_clicks']+=1
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
        
    queries = []
    print(analytics_data.fact_query.keys())
    for query in analytics_data.fact_query.keys():
        q: Query = query
        doc = ClickedDoc(query, 'Last time searched: '+str(analytics_data.fact_query_time[query]), analytics_data.fact_query[query])
        queries.append(doc)

    # simulate sort by ranking
    queries.sort(key=lambda doc: doc.counter, reverse=True)
    queries_ser=[]
    for q in queries:
        queries_ser.append(q.to_json())
        
    terms=[]
    for term in analytics_data.fact_terms.keys():
        q: Term = term
        term_info = ClickedDoc(term, analytics_data.fact_terms[term], analytics_data.fact_terms[term])
        terms.append(term_info)

    terms.sort(key=lambda term_info: term_info.counter, reverse=True)
    terms_ser=[]
    for t in terms:
        terms_ser.append(t.to_json())
    return render_template('dashboard.html', visited_docs=visited_ser, searched_queries = queries, searched_terms=terms_ser)


@app.route('/sentiment')
def sentiment_form():
    session['Num_clicks']+=1
    return render_template('sentiment.html')


@app.route('/sentiment', methods=['POST'])
def sentiment_form_post():
    session['Num_clicks']+=1
    text = request.form['text']
    nltk.download('vader_lexicon')
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    sid = SentimentIntensityAnalyzer()
    score = ((sid.polarity_scores(str(text)))['compound'])
    return render_template('sentiment.html', score=score)


if __name__ == "__main__":
    app.run(port=8088, host="0.0.0.0", threaded=False, debug=True)
