#Instructions
Note: I already included the data so it should run directly. You can email me at icantrell617@gmail.com if you have a question. I will try to respond right away.

The data I have on Github only has ~50 websites due to Github limit. The one in class had around 200k but I have a feeling you might be able to use a fraction of that to see significant results but maybe more than 50.

1.(optional)to run the web crawler run<br>
python web_crawler.py

It only crawls english Wikipedia and it is single threaded. 

2.(optional)to process the collected data run<br>
python lsi.py <number of principal components to create> 1 0 db/webpages.db english_words_20k.txt

3.to run LSI search engine run<br>
python lsi.py <number of principal components to use> 0 0

the # of principal components has a different purpose here. It will decide how many to actaully use for comparison and can be raised or increased later with minimal re-processing.

4.(optional)to run raw TF-IDF search engine run<br>
python lsi.py <number of principal components to use> 0 1

This is for comparison against LSI. In theory it should be worse.
