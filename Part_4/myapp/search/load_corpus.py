import pandas as pd
from collections import defaultdict
from myapp.core.utils import load_json_file
from myapp.search.objects import Document

_corpus = {}

## OUR CODE

def load_processed_tweets_from_csv(path):
    df = pd.read_csv(path).drop(columns=['Unnamed: 0'])
    return df

def extract_tweet_vocabulary(tweet, docId):
    return {term: docId for term in tweet.split(' ')}
def merge_dicts(dicts):
    vocab = defaultdict(list)
    for dic in dicts:
        for term in dic:
            vocab[term].append(dic[term])
    return dict(vocab)

## END OF OUR CODE
def load_corpus(path) -> [Document]:
    """
    Load file and transform to dictionary with each document as an object for easier treatment when needed for displaying
     in results, stats, etc.
    :param path:
    :return:
    """
    df = _load_corpus_as_dataframe(path)
    df.apply(_row_to_doc_dict, axis=1)
    return _corpus

def docID2tweetID():
    docs_path = '../data/tweet_document_ids_map.csv'

    # reading file line by line, each one is a mapping for a specific tweet 
    with open(docs_path) as fp:
        lines = fp.read().split("\n") 
    lines = [l for l in lines if l != ""] # ensure there are no empty lines
    print("Total number of tweet documents in the corpus: {}".format(len(lines)))
    # we store pairs (tweetId, docId) into 2 dictionaries 

    tweet2doc = dict()
    doc2tweet = dict()

    for line in lines:
        docID, tweetID = tuple(line.split("\t"))
        tweet2doc[tweetID] = docID
        doc2tweet[docID] = tweetID
    return tweet2doc, doc2tweet


def docID2tweet(path): 
    tweet2doc, doc2tweet = docID2tweetID()
    json_data = load_json_file(path)
    
    print(type(json_data))
    doc2tweet = dict()
    for c in json_data:
        docID = tweet2doc.get(c["id_str"])
        doc2tweet[docID] = c['full_text']
    return  doc2tweet

def _load_corpus_as_dataframe(path):
    """
    Load documents corpus from file in 'path'
    :return:
    """
    with open(path) as fp:
        tweets = fp.read().split("\n") # each tweet is a new line 
    tweets = [t for t in tweets if t != ""]
    json_data=[]
    for t in tweets:
        json_data.append(json.loads(t))

    print(type(json_data))
    tweets_df = _load_tweets_as_dataframe(json_data)
    _clean_hashtags_and_urls(tweets_df)
    # Rename columns to obtain: Tweet | Username | Date | Hashtags | Likes | Retweets | Url | Language
    corpus = tweets_df.rename(
        columns={"id": "Id", "full_text": "Tweet", "screen_name": "Username", "created_at": "Date",
                 "favorite_count": "Likes",
                 "retweet_count": "Retweets", "lang": "Language"})

    # select only interesting columns
    filter_columns = ["Id", "Tweet", "Username", "Date", "Hashtags", "Likes", "Retweets", "Url", "Language"]
    corpus = corpus[filter_columns]
    
    return corpus


def _load_tweets_as_dataframe(json_data):
    data = pd.DataFrame.from_dict(json_data).transpose()
    # parse entities as new columns
    data = pd.concat([data.drop(['entities'], axis=1), data['entities'].apply(pd.Series)], axis=1)
    # parse user data as new columns and rename some columns to prevent duplicate column names
    data = pd.concat([data.drop(['user'], axis=1), data['user'].apply(pd.Series).rename(
        columns={"created_at": "user_created_at", "id": "user_id", "id_str": "user_id_str", "lang": "user_lang"})],
                     axis=1)
    return data


def _build_tags(row):
    tags = []
    # for ht in row["hashtags"]:
    #     tags.append(ht["text"])
    for ht in row:
        tags.append(ht["text"])
    return tags


def _build_url(row):
    url = ""
    try:
        url = row["entities"]["url"]["urls"][0]["url"]  # tweet URL
    except:
        try:
            url = row["retweeted_status"]["extended_tweet"]["entities"]["media"][0]["url"]  # Retweeted
        except:
            url = ""
    return url


def _clean_hashtags_and_urls(df):
    df["Hashtags"] = df["hashtags"].apply(_build_tags)
    df["Url"] = df.apply(lambda row: _build_url(row), axis=1)
    # df["Url"] = "TODO: get url from json"
    df.drop(columns=["entities"], axis=1, inplace=True)


def load_tweets_as_dataframe2(json_data):
    """Load json into a dataframe

    Parameters:
    path (string): the file path

    Returns:
    DataFrame: a Panda DataFrame containing the tweet content in columns
    """
    # Load the JSON as a Dictionary
    tweets_dictionary = json_data.items()
    # Load the Dictionary into a DataFrame.
    dataframe = pd.DataFrame(tweets_dictionary)
    # remove first column that just has indices as strings: '0', '1', etc.
    dataframe.drop(dataframe.columns[0], axis=1, inplace=True)
    return dataframe


def load_tweets_as_dataframe3(json_data):
    """Load json data into a dataframe

    Parameters:
    json_data (string): the json object

    Returns:
    DataFrame: a Panda DataFrame containing the tweet content in columns
    """

    # Load the JSON object into a DataFrame.
    dataframe = pd.DataFrame(json_data).transpose()

    # select only interesting columns
    filter_columns = ["id", "full_text", "created_at", "entities", "retweet_count", "favorite_count", "lang"]
    dataframe = dataframe[filter_columns]
    return dataframe


def _row_to_doc_dict(row: pd.Series):
    _corpus[row['Id']] = Document(row['Id'], row['Tweet'][0:100], row['Tweet'], row['Date'], row['Likes'],
                                  row['Retweets'],
                                  row['Url'], row['Hashtags'])
