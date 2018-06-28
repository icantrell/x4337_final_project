# lsi-web-crawler
Crawls the web to create an LSI matrix by finding word frequencies in different internet articles.
 To run the web crawler type
 python web_crawler.py
 
 note: The init_urls.txt contains the starting websites to crawl.
 
 next...
 to process the data for the search engine type
 python lsi.py <number of principal components to create> 1 0 <database location(will make db if does not exist> english_words_20k.txt
  
  note: 350 principal components is recommended
  
  then to run the LSI search engine type
  python lsi.py <number of principal components to use for the search> 0 0
  
  then to run the raw TF-IDF search engine type
  python lsi.py <number of principal components to use for the search> 0 1
  
  
  NOTE: This process also takes a while due to lack of multi-threading. This trade was made for what seems to be more memory efficient software.
