import os
import heapq
from web_crawler import Webpage, Storage
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD 
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import Normalizer
import sys
import tensorflow as tf
from tensorflow.contrib.tensorboard.plugins import projector
from scipy.sparse import csr_matrix

#set constants
#set number of principal components, whos closest words we will find.
SHOW_PRIN = 3
#how many of their words, we will show
SHOW_PRIN_WORDS = 10

#the log dir for tensorboard
LOG_DIR = 'events'

#helper functions
def save_file(fname, obj,pickling = True):
    if not pickling:
        f = open(fname, 'wb')
        f.write(obj.encode('utf-8'))
        f.close()
        return
    f = open(fname,'wb')
    pickle.dump(obj,f,2)
    f.close()

def load_file(fname):
    f = open(fname,'rb')
    x = pickle.load(f)
    f.close()
    return x

#necessary user inputs

#number of principal components to use. 350 is recommended for LSI, 100 for LSA(note: this confused me at first)
PCA_COMPONENTS = int(sys.argv[1])
#user inputs
remake = int(sys.argv[2])
#If remake is 0 then. You can enter another mode that does not use LSI bt only TF-IDF. This is for comparison purposes.
use_tfidf = int(sys.argv[3])

#function for opening search a loop.
#user can specify what function they are using to transform the query data into a vector
#and what dataset they are testing against.
def open_search(transform, type_search, comparison_vectors,page_titles,page_urls):
    while 1:
        vec = transform([input('enter search term(' + type_search + '): ')])
        results = []
        for v in comparison_vectors:
            #for each vector find it's angle against each vector in the dataset, which gives similarity.
            #check if sparse matrix since sparse matrix does not have or need a reshape method.
            if isinstance(v,csr_matrix):
                a= cosine_similarity(vec,v)
            else:
                a= cosine_similarity(vec[0,:PCA_COMPONENTS].reshape(1,-1),v[:PCA_COMPONENTS].reshape(1,-1))
            #store results
            results.append(a)
        #sort results to find closest
        results = list(zip(results,page_titles,page_urls))

        #print results
        for res in sorted(results,key=lambda x: x[0])[-20:]:
            res = list(res)
            res[1] = res[1].upper()
            print('{res[1]}\n{res[2]}\nrelevance:{res[0][0][0]}\n\n'.format(res=res))


if remake:
    #user input for remake
    #sqlite database location should have website data in a table.
    db_name = sys.argv[4]
    #dictionary location, text file of words that you want LSI not to ignore.
    fname = sys.argv[5]
    #this script has two modes. It will reprocess the data if remake is 1. If 0 then the search engine will run instead.

    #set up word dictionary and word list. word list holds fast index->word word_dict holds word->index.
    word_dict={}
    #populate word list with data from input file.
    word_list = sorted(open(fname,'r').read().split())

    #populate dict
    for i,word in enumerate(word_list):
        word_dict[word] = i
        assert((word).islower())

    #init TF-IDF vectorizer from sklearn with vocabulary from word list, which means it will only look at words from that list.
    tfidf  = TfidfVectorizer(input = 'content',analyzer = 'word', lowercase = True, vocabulary = word_list, min_df = 0.0, max_df= 1.0, smooth_idf = True)

    #set up SVD, which outputs Principal vectors
    svd = TruncatedSVD(n_components = PCA_COMPONENTS, algorithm = 'arpack')

    #init database storage mechanism
    storage = Storage(dbfile = db_name)

    #if recompute variable is set.
    print('making tf_idf vectors...')

    #fit TF-IDF with databases webpages and get each pages TF-IDF vectors in the form of a sparse matrix.
    tfidf_matrix = tfidf.fit_transform(storage.read_pages_strings())
    save_file('tfidf.dat',tfidf)
    save_file('tfidf_matrix.dat',tfidf_matrix)
    
    #compute approximate SVD with tfidf sparse matrix.
    print('making LSA vectors...')
    lsi_vecs = svd.fit_transform(tfidf_matrix)
    save_file('svd.dat',svd)
    save_file('lsi_vecs.dat',lsi_vecs)

    #get titles for tensorboard meta data and search loop.
    print('getting page titles...') 
    page_titles = list(storage.read_pages_title())
    save_file('page_titles.dat',page_titles)

    #get page url for search loop. Should've made one call to DB.
    print('getting page urls...')
    page_urls = list(storage.read_pages_url())
    save_file('page_urls.dat',page_urls) 

    print('making closest words for principal vectors...')
    #make a structure that will hold the closest words for each principal component.
    max_words = {}
    for w in word_list:
        #for each word get its vector form
        wti = svd.transform(tfidf.transform([w]))

        for i,v in enumerate(lsi_vecs[:SHOW_PRIN]):
            #for each principal component find angle between it and the word.
            cs = cosine_similarity(wti.reshape(1,-1),v.reshape(1,-1))[0][0]
            
            #use heaps to store closest words for each component.
            if i in max_words and cs > max_words[i][0][0]:
                #add word's angle and the word itself to the heap in a tuple.
                if len(max_words[i]) > SHOW_PRIN_WORDS:
                    heapq.heappop(max_words[i])
                heapq.heappush(max_words[i], (cs,w))

            elif i not in max_words:
                max_words[i] = [(cs,w)]

    #save words into file
    save_file('max_words.dat',max_words) 
    
    #make sure as many titles as lsi vectors
    assert(len(lsi_vecs) == len(page_titles))
    print('making metadata for tensorboard...')
    #save page titles to meta data file.
    save_file('events/metadata.tsv','Title\n' + '\n'.join(page_titles),False)
    print('Now run command...')
    print('\n~~~~~~~~~~~~~\npython lsi.py <#principal vectors> 0 0 \nto see LSI based search.')
    print('python lsi.py <#principal vectors> 0 1 \nto see TF-IDF based search.\n~~~~~~~~~~~~\n')

    print('making tensorbaord data...')
    #make tensorboard embedding visual.
    def make_tf_visual(_):
        with tf.Session() as sess:
            #get embedding data variable from website vectors
            embedding_var = tf.Variable(lsi_vecs,name = 'embedding')
            #init variable
            sess.run(tf.global_variables_initializer())

            saver= tf.train.Saver()
            saver.save(sess, os.path.join(LOG_DIR,'model.ckpt'))
            
            
            writer = tf.summary.FileWriter('events/',sess.graph)
            #get tf projector
            config = projector.ProjectorConfig()
            
            #create embedding
            embedding = config.embeddings.add()
            #bind to embedding_var
            embedding.tensor_name = embedding_var.name
            
            #add metadata path to embedding
            embedding.metadata_path =  'metadata.tsv'

            summary_writer = tf.summary.FileWriter(LOG_DIR, sess.graph)
            #run projector
            pv = projector.visualize_embeddings(summary_writer, config)
            
            sess.run(embedding_var) 
    #run the embedding.
    tf.app.run(main = make_tf_visual)

print('loading engine...')
#load saved files
lsi_vecs = load_file('lsi_vecs.dat')
page_titles = load_file('page_titles.dat')
tfidf = load_file('tfidf.dat')
svd = load_file('svd.dat')
page_urls = load_file('page_urls.dat')


if use_tfidf:
    #if in TF-IDF mode. Don't use LSI data for searching but only raw TF-IDF data. For comparison purposes.
    tfidf_matrix = load_file('tfidf_matrix.dat')
    open_search(tfidf.transform, 'tfidf matrix', tfidf_matrix,page_titles,page_urls)

#get the words that were closests to principle components. To find the biggest topics.
max_words = load_file('max_words.dat')
#print the words for each vector.
for i in range(SHOW_PRIN):
    print('\nPrinciple vector ' + str(i) + ':')

    for words in max_words[i]:
        print(words[1])

#open search loop for LSI data.
open_search(lambda x: svd.transform(tfidf.transform(x)), 'LSI data', lsi_vecs, page_titles, page_urls)

