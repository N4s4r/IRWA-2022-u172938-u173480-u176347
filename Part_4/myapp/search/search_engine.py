import random
from nltk.corpus import stopwords
import re
import contractions
from myapp.search.objects import ResultItem, Document
from nltk.stem import PorterStemmer
from nltk.stem import WordNetLemmatizer
import numpy as np

def build_demo_results(corpus: dict, search_id):
    """
    Helper method, just to demo the app
    :return: a list of demo docs sorted by ranking
    """
    res = []
    size = len(corpus)
    ll = list(corpus.values())
    for index in range(random.randint(0, 40)):
        item: Document = ll[random.randint(0, size)]
        res.append(ResultItem(item.id, item.title, item.description, item.doc_date,
                              "doc_details?id={}&search_id={}&param2=2".format(item.id, search_id), random.random()))

    # for index, item in enumerate(corpus['Id']):
    #     # DF columns: 'Id' 'Tweet' 'Username' 'Date' 'Hashtags' 'Likes' 'Retweets' 'Url' 'Language'
    #     res.append(DocumentInfo(item.Id, item.Tweet, item.Tweet, item.Date,
    #                             "doc_details?id={}&search_id={}&param2=2".format(item.Id, search_id), random.random()))

    # simulate sort by ranking
    res.sort(key=lambda doc: doc.ranking, reverse=True)
    return res

def build_terms(line):
    """
    Preprocess the tweet content removing stop words, contractionas and urls
    lemmatizing and stemming words to keep a single word for each family of words
    transforming in lowercase, removing special characters [#, @, .] 
    (since it is included in another column on the dataframe)
    
    return tokenized tweet (list of words after applying the previous steps).
    
    Argument:
    line -- string (tweet) to be preprocessed
    
    Returns:
    line - a list of tokens corresponding to the input text after the preprocessing
    """
    ## START CODE
    line = line.lower() ##Transform in lowercase
    line = re.sub(r"[^A-Za-z 0-9 ']+", '', line) # remove emojis and any other special character
    stop_words = set(stopwords.words("english")) # removing stopwords
    line = ' '.join([contractions.fix(x) for x in line.split(' ')]) # expaning verb abreviations: i'll -> i will 
    line = re.sub("'", '', line) 
    line = line.split(' ')
    line = [x for x in line if x and x not in stop_words]
    line = filter(lambda x:x[0:5]!='https', line) # removing links
    line = [x for x in line]
    ps = PorterStemmer() 
    lemmatizer = WordNetLemmatizer() 
    line = [lemmatizer.lemmatize(x) for x in line] # keeping the singular form of each noun: feet --> foot
    line = [ps.stem(x) for x in line] # keeping the root of each family of words: dancer --> danc
    
    ## END CODE
    return ' '.join(line)

def BM25(query, vocabulary, k1, b, L_ave, doc_contents):
    '''
    vocabulary = inverted index, dictionary with keys = terms an values = list of doc_ids
    k1 = value to regulate xx
    b = value to regulate yy
    L_ave = average length of docs in words
    doc_contents = dictionary where keys = doc_ids and values = list of terms (after text processing)
    '''
    
    RSV = dict()
    N = len(doc_contents)
    terms_q = list(set(build_terms(query).split()))
    idf = dict()
    
    # calculate idf for each term in the query 
    for t in terms_q:
        f_tq = terms_q.count(t)
        if t not in vocabulary:
            continue
        df_t = len(vocabulary[t])
        idf[t] = np.log(N/df_t)
        
    # calculate RSVd for each document  
    for doc in doc_contents.keys():
        RSV[doc] = 0
        Ld = len(doc_contents[doc])
        for t in idf.keys():
            tf_t_d = doc_contents[doc].count(t)

            second_term = ((k1+1)*tf_t_d) / (k1*((1-b)+b*(Ld/L_ave))+tf_t_d)
            RSV[doc] += idf[t]*second_term
            
    return {k: v for k, v in sorted(RSV.items(), key=lambda item: item[1], reverse=True)}

def format_results_BM25(doc2tweet, results, top, df, search_id):
    res = []
    for i in range(top):
        doc, score = list(results.items())[i]
        item = df[df.DocID == doc].iloc[0]
        #print(item)
        tweet = doc2tweet[doc]
        res.append(ResultItem(item['DocID'], item['Username']+': '+tweet[0:40]+'...', tweet, item['Date'], item['Url'], i+1))
        # "doc_details?id={}&search_id={}&param2=2".format(item['DocID'], search_id), random.random()
    return res

class SearchEngine:
    """educational search engine"""

    def search(self, search_query, search_id, vocabulary, L_ave, dictionary_doc, df):
        print("Search query:", search_query)

        results = []
        ##### your code here #####
        results_BM25 = BM25(search_query, vocabulary, 1, 0.75, L_ave, dictionary_doc)#build_demo_results(corpus, search_id)  # replace with call to search algorithm
        results = format_results_BM25(doc2tweet, results_BM25, 20, df, search_id)
        # results = search_in_corpus(search_query)
        ##### your code here #####

        return results
