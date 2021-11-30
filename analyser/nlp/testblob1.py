from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# analysis = TextBlob("TextBlob sure looks like it has some interesting features!")
# analysis = TextBlob("Asant  sana niko tayari kufuata maagizo")

# print(analysis.translate(from_lang='sw', to='en'))
# analysis_eng = analysis.translate(from_lang='sw', to='en')

# print(analysis_eng.tags)

# print(analysis_eng.sentiment)

analyser = SentimentIntensityAnalyzer()

vs = analyser.polarity_scores("VADER Sentiment looks interesting, I have high hopes")

print(vs)