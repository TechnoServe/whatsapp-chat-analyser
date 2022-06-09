import matplotlib.pyplot as plt
from datetime import datetime
from analyser.models import MessageLog
from analyser.chat.MessageHistory import MessageHistory

import nltk
import itertools
from nltk.corpus import stopwords
from string import punctuation
from nltk.probability import FreqDist
import pandas as pd
from wordcloud import WordCloud

msgHistory = MessageHistory()

class Chart:
    def CategoriesOfInformation(data):
        # Pie chart, where the slices will be ordered and plotted counter-clockwise:
        labels = 'Images', 'Messages', 'Links', 'Emojis'
        
        explode = (0, 0.1, 0, 0)  # only "explode" the 2nd slice (i.e. 'Hogs')

        fig1, ax1 = plt.subplots(figsize=(20, 10))

        ax1.pie(data, explode=explode, labels=labels, autopct='%1.1f%%',
                shadow=True, startangle=90)
        ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

        plt.legend(['Images', 'Messages', 'Links', 'Emojis'], loc="lower right")
        plt.suptitle('Categories of Information Sent', fontsize=20)

        plt.savefig("analyser/templates/jinja2/pdf_templates/pie_chart.png")
        plt.clf()
        plt.close()
        return True

    
    def activeDaysChart(data):
        
        fig = plt.figure(figsize = (20, 10))

        plt.suptitle('Active Days', fontsize=45)

        plt.xlabel('Date', fontsize=25)
        plt.ylabel('Messages Count', fontsize=25)      

        dates = data['dates']
        dates = [datetime.strptime(date, '%Y-%m-%d') for date in dates]

        messages = data['messages']

        plt.bar(dates, messages)
        plt.savefig("analyser/templates/jinja2/pdf_templates/active_days.png")
        plt.clf()
        plt.close('all')

        return True

    
    def wordCloud(group_id):
        nltk.download('punkt')
        nltk.download('stopwords')

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
        #len(uniqueValues)

        length = len(uniqueValues) if len(uniqueValues)%2 == 0 else len(uniqueValues)+1
        length = round(length/2)
        unq = uniqueValues[length :]


        filteredDict = dict()
        # Iterate over all the items in dictionary and filter items which has even keys
        for (key, value) in fdist.items():
        # Check if key is even then add pair to new dictionary
            if fdist[key] in unq and not len(key) == 1:       #newDict[key] = value
                filteredDict[key] = value

        cleaned_tokens_mm = ' '.join(filteredDict)

        wordcloud = WordCloud(width=1800, height=1000, max_font_size=200, background_color="white").generate(cleaned_tokens_mm)
        # plt the image generated by WordCloud class
        plt.figure(figsize=(20,10))
        plt.suptitle('Word Cloud', fontsize=50)
        plt.imshow(wordcloud)
        plt.axis("off")
        plt.savefig("analyser/templates/jinja2/pdf_templates/word_cloud.png")
        plt.clf()
        plt.close('all')

        return True
    

    def emotionsGraph(group_id):
        emotions = msgHistory.getEmotions(group_id)

        fig = plt.figure(figsize = (20, 10))
        plt.suptitle('Graph of Emotions', fontsize=45)

        plt.bar(range(len(emotions)), list(emotions.values()), align='center')
        plt.xticks(range(len(emotions)), list(emotions.keys()))
        plt.xticks(rotation=70)

        plt.savefig("analyser/templates/jinja2/pdf_templates/emotions.png")
        plt.close('all')
        

    def sentimentGraph(group_id):
        sentiment = msgHistory.getSentiment(group_id)
        fig = plt.figure(figsize = (20, 10))
        plt.suptitle('Graph of Sentiment Analysis', fontsize=45)

        plt.bar(range(len(sentiment)), list(sentiment.values()), align='center')
        plt.xticks(range(len(sentiment)), list(sentiment.keys()))

        plt.savefig("analyser/templates/jinja2/pdf_templates/sentiment.png")
        plt.close('all')