from django.db import transaction, connection
from django.db.models import Q, Sum, Count, IntegerField, Min, Max, Avg, F, CharField, functions
from django.conf import settings

from analyser.models import Personnel, WhatsAppGroup, WhatsAppChatFile, GroupDailyStats, UserDailyStats, MessageLog, GroupNameChanges, STATUS_CHOICES
from analyser.serializers import GroupDailyStatsSerializer, MessageLogSerializer
from analyser.chat.Utilities import Utilities

from hashids import Hashids
from analyser.common_tasks import Notification, Terminal

import pandas as pd
import sentry_sdk

from datetime import datetime
from tzlocal import get_localzone

import matplotlib.pyplot as plt

import string
from  collections import Counter
from nltk.tokenize import word_tokenize
from nltk.corpus.reader import WordListCorpusReader
from nltk.corpus import stopwords
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.sentiment.util import *
from textblob import TextBlob
from nltk import tokenize
import pandas as pd
import matplotlib.pyplot as plt

from textblob import TextBlob

class MessageHistory:

    def getMessageLogByDate(self, date, group_id):
        #all_messages = list(MessageLog.objects.select_related('user').filter(datetime_sent=date, chat_file_id=group_id).extra(select={'dt':"DATE_FORMAT(datetime_sent, '%%Y-%%m-%%d %%H:%%i')"}).values('dt').annotate(mssg=F('message')).order_by('datetime_sent').all())
        qs = MessageLog.objects.select_related('user').filter(datetime_sent__date=date, chat_file=group_id).extra(select={'dt':"DATE_FORMAT(datetime_sent, '%%Y-%%m-%%d %%H:%%i')"}).all()

        result = MessageLogSerializer(qs, many=True)
        return result.data

    
    def getAllMessages(self):
        qs = MessageLog.objects.all().values_list('message')


    def getGroupMessages(self,group_id):
        chat_file = WhatsAppChatFile.objects.filter(group=group_id).values_list('id')
        messages = MessageLog.objects.filter(chat_file=chat_file[0][0]).all()

        return messages
    
    def getEmotions(self,group_id):
        stopwords_sw = ["mimi", "yangu", "mwenyewe", "sisi", "yetu", "wenyewe",
         "wewe", "yako", "yeye", "wake", "ni", "yake", "yenyewe", "wao" ,
          "nini", "yupi", "nani", "huyu", "huyo", "hawa", "wale", "wapo",
           "ilikuwa", "walikuwa", "kuwa", "amekuwa", "alikuwa", "na", "kufanya" ,
            "anafanya", "alifanya", "alifanya", "hiyo", "lakini", "ikiwa", "au",
             "kwa sababu", "kama", " mpaka", "wakati", "ya", "kwa", "pamoja na",
              "karibu", "dhidi ya", "kati", 
             "ndani", "kupitia", "kabla", "baada ya", "juu", "chini", "hadi", "kutoka", "nje",
              "washa", "zima", "tena", "zaidi", "basi", "mara moja", "hapa", "hapo", "wakati",
               "wapi", "kwa nini", "vipi", "wote" , "yoyote", "kila", "wachache",
                "zaidi", "wengi", "nyingine",
                "baadhi", "kama", "hapana", "wala",
              "sio", "tu ", "miliki", "sawa", "hivyo", "kuliko", "pia", "sana", "naweza",
               "unaweza", "anaweza", "tu", "lazima", "sasa "]
        messages = self.getGroupMessages(group_id)
        tokenized_words= []
        for message in messages:
            message = message.message
            message = message.lower()
            # print(message[0:5]=='https')
            if message[0:4] != 'http': 
                cleaned_text = message.translate(str.maketrans('','',string.punctuation))

                # splitting text into words
                tokenized_words += word_tokenize(cleaned_text) 

        final_words = []
        for word in tokenized_words:
            if (word not in stopwords.words('english'))  and (word not in stopwords_sw):
                final_words.append(word)

        # find emotions from chat
        emotion_list = []
        with open('analyser/chat/emotions_en_sw.txt','r') as file:
            for line in file:
                clear_line = line.replace('\n','').replace("'",'').replace("'","").replace(" ",'').strip()
                word, emotion = clear_line.split(':')

                if word in final_words:
                    # print(word)
                    emotion_list.append(emotion.replace(",",''))

        emotions_counter = dict(Counter(emotion_list))

        return  emotions_counter
    
    def getSentiment(self, group_id):
        df = pd.DataFrame()

        messages = self.getGroupMessages(group_id)
        tokenized_words= []
        message_list = []
        sentiment_list = []
        polarity_list = []
        for message in messages:
            message = message.message
            message = message.lower()
            if message[0:4] != 'http': 

                cleaned_text = message
                # cleaned_text = message.translate(str.maketrans('','',string.punctuation))

            message_list.append(cleaned_text)
            text_blob = TextBlob(cleaned_text).sentiment.polarity
            polarity_list.append(text_blob)
            if text_blob > 0:
                sentiment_list.append('Positive')
            elif text_blob < 0:
                sentiment_list.append('Negative')
            else:
                sentiment_list.append('Neutral')

        data = {"Polarity":sentiment_list}
        sentiment_count = dict(Counter(sentiment_list))
        df = pd.DataFrame(data)

        return sentiment_count
