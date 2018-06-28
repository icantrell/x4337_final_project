#Instructions

to run the web crawler run
python web_crawler.py

to process the collected data run
python lsi.py <number of principal components to create> 1 0 db/webpages.db english_words_20k.txt
  
to run LSI search engine run
python lsi.py <number of principal components to use> 0 0
  
to run raw TF-IDF search engine run
python lsi.py <number of principal components to use> 0 1
