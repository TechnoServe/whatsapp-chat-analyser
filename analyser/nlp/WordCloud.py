from analyser.models import MessageLog

# NLP imports
import pandas as pd
import nltk
import itertools
from nltk.corpus import stopwords
from string import punctuation
from nltk.probability import FreqDist

class WordCloud:
    def getGroupChat(self, group_id):

        qs = MessageLog.objects.filter(chat_file=group_id).values_list('message')

        # Creating a pandas dataframe out of the returned results
        df = df = pd.DataFrame(qs, columns=['message'])

        # Performing tokenization here
        df['tokenized'] = df.apply(lambda row: nltk.word_tokenize(row['message']), axis=1)
        listOfWords = df['tokenized'].tolist()
        tokens = list(itertools.chain(*listOfWords))

        # Filtering words from the list of tokens
        stop_words = stopwords.words('english')
        stop_words += ['na','kwa',"'t","one","'s","the","n't",'--']
        punctuation_var = list(punctuation)
        cleaned_tokens = [token for token in tokens if token.lower() not in stop_words and token not in punctuation_var]

        # Frequency of tokens
        fdist = FreqDist(cleaned_tokens)


        myList1 = list(fdist.values())
        newList = sorted(myList1)

        uniqueValues = set(newList)
        uniqueValues = list(uniqueValues)
        len(uniqueValues)

        length = len(uniqueValues) if len(uniqueValues)%2 == 0 else len(uniqueValues)+1
        length = round(length/2)
        unq = uniqueValues[length :]


        filteredDict = dict()
        # Iterate over all the items in dictionary and filter items which has even keys
        for (key, value) in fdist.items():
        # Check if key is even then add pair to new dictionary
            if fdist[key] in unq and not len(key) == 1:       #newDict[key] = value
                filteredDict[key] = value

        # merge all tokens to form a text
        text_tokens  = ' '
        for key,value in filteredDict.items():
            text_tokens += (key.lower()+' ')*value
        # print(text_tokens)

        return text_tokens


