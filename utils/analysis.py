import calendar
import os
import random
import re
import string
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import emoji
import pandas as pd
import requests

from mspark_whatsapp_analyzer import settings


def import_messages(path=''):
    # date - sender: message
    regex = r'(\d+\/\d+\/\d+, (?:(?:\d+|\d+\d+):\d+\d+) (?:AM -|PM -|-)) (.*?): ([\s\S]+?)(?=\d+/\d+/\d+)'
    f = open(path, encoding='utf-8')
    messages = re.findall(regex, f.read())
    f.close()

    # convert list to a dataframe and name the columns
    df = pd.DataFrame(messages, columns=['Timestamp', 'Name', 'GroupMessage'])
    df['Timestamp'] = df['Timestamp'].str.replace(r' -', '')
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], exact=False, infer_datetime_format=True)
    df['Date'] = df['Timestamp'].apply(lambda x: x.date())
    df['Day'] = df['Timestamp'].apply(lambda x: calendar.day_abbr[x.weekday()])
    df['Hour'] = df.apply(lambda row: row.Timestamp.hour, axis=1)

    # return df.to_json()
    return df


def import_events(path=''):
    # date - notification
    try:
        regex = r'(\d+\/\d+\/\d+, (?:(?:\d+|\d+\d+):\d+\d+) (?:AM -|PM -|-)) ([^:]*)\n'
        f = open(path, encoding='utf-8')
        events = re.findall(regex, f.read())
        f.close()

        # convert list to dataframe
        df = pd.DataFrame(data=events, columns=['Timestamp', 'Notification'])
        df['Timestamp'] = df['Timestamp'].str.replace(r' -', '')
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], exact=False, infer_datetime_format=True)
        df['Date'] = df['Timestamp'].apply(lambda x: x.date())
        df['Day'] = df['Timestamp'].apply(lambda x: calendar.day_abbr[x.weekday()])
        df['Hour'] = df.apply(lambda row: row.Timestamp.hour, axis=1)
        return df
    except Exception as e:
        print(e)


def extract_emojis(str):
    # print("extract_emojis: ", ' '.join(char for char in str if char in emoji.UNICODE_EMOJI))
    # extract emoji from the messages
    return ' '.join(char for char in str if char in emoji.UNICODE_EMOJI)


def extract_links(str):
    # get links contained in messages
    regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(regex, str)


def get_attrition(value):
    # Returns the number of people joining or leaving
    if 'added' in value or 'removed' in value:
        return value.count(' and ') + value.count(', ') + 1 if value.count(', ') == 0 else value.count(', ') + 1
    if 'joined' in value or 'left' in value:
        return 1

    return 0


def user_stats(df):
    # name, messages, words per message, sent Media, most used words
    # number of messages, number of emojis
    user_stats = []
    stopwords = [string.punctuation, 'in', 'is', 'the', 'i', 'how', 'to', 'ni',
                 'are', 'we', 'at', 'for', 'and', 'as', 'it', 'of', 'if']

    for name in df.Name.unique():
        n_messages = len(df[df.Name == name])
        words = [x for sublist in df[(df.Name == name) & (df.GroupMessage != '<Media omitted>\n')].GroupMessage.values
                 for x in sublist.split(' ')]
        n_words = len(words)
        # remove new line characters and puntuation marks
        words = [re.sub(r'[\n\s]', '', word) for word in words if word.lower() not in stopwords]
        top_words = ', '.join([word for word, word_count in Counter(words).most_common(5)])
        n_media = len(df[(df.Name == name) & (df.GroupMessage == '<Media omitted>\n')])

        emojis = extract_emojis(str(df[df.Name == name].GroupMessage.values))
        n_emojis = len(list(filter(None, emojis.split(' '))))
        emoji_list = emojis.split(' ')
        top_emojis = ', '.join([emoji for emoji, emoji_count in Counter(emoji_list).most_common(5)])

        # links
        links = extract_links(str(df[df.Name == name].GroupMessage.values))
        n_links = len(links)
        links = ',  '.join([link for link, link_count in Counter(links).most_common(5)])

        user_stats.append({
            'Name': name,
            'Messages': n_messages,
            'Words': n_words,
            'Emojis': n_emojis,
            'Media': n_media,
            'Links': n_links,
            'Top_emojis': top_emojis,
            'Top_words': top_words,
            'Top_links': links,
        })

    out = pd.DataFrame(user_stats)

    # return out.to_json()
    return out


def group_stats(df):
    # number of messages
    n_messages = df.GroupMessage.count()

    # number of pictures ?* <Did number of media files>
    n_media = len(df[df.GroupMessage == '<Media omitted>\n'])

    # number of emojis
    emojis = extract_emojis(str(df.GroupMessage.values))
    n_emojis = len(list(filter(None, emojis.split(' '))))

    # number of shared links
    n_links = len(extract_links(str(df.GroupMessage.values)))

    out = pd.DataFrame({
        'Messages': n_messages,
        'Media': n_media,
        'Emojis': n_emojis,
        'Links': n_links,
    }, index=[0])

    return out


def attrition_levels(df):
    # how many people are joining and leaving the group
    left_n = 0
    joined_n = 0

    for value in df.Notification.values:

        count = get_attrition(value)

        if 'added' in value or 'joined' in value:
            joined_n += count
        if 'removed' in value or 'left' in value:
            left_n += count

    out = {
        'Joined': joined_n,
        'Left': left_n,
    }

    return out


def is_file_path_url(url):
    return urlparse(url).scheme != ""


def get_filename_from_cd(cd):
    """ Get filename from content-disposition """
    if not cd:
        return None
    fname = re.findall('attachment;filename=(.+)', cd)
    # print("fname: ", fname[0].split(';')[0].replace('"', ''))
    if len(fname) == 0:
        return None
    return fname[0].split(';')[0].replace('"', '')


def create_chat_file_directory():
    # chat_file_directory = os.path.join(settings.MEDIA_ROOT, filename)
    letters = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(letters) for i in range(1, 9))
    chat_file_directory = os.path.join(settings.MEDIA_ROOT, result_str)
    if not os.path.exists(chat_file_directory):
        os.makedirs(chat_file_directory)
    return chat_file_directory


def download_chat_file(url):
    '''
    :returns chat file path and dir downloaded from google drive link
    :param url:
    :return file_directory : str:
    '''
    r = requests.get(url, allow_redirects=True)
    filename = get_filename_from_cd(r.headers.get('content-disposition'))
    chat_directory = create_chat_file_directory()
    chat_file_path = os.path.join(chat_directory, filename)
    with open(chat_file_path, 'wb') as f:
        f.write(r.content)
        f.close()
    return dict(chat_file_path=chat_file_path, chat_directory=chat_directory)


def get_most_active_days(df):
    # returns the top ten most active days
    out = df['Date'].value_counts().head(10)
    return out.to_json()


def get_most_active_time(df):
    # returns the most active hour of the day
    out = df['Hour'].value_counts().head(10)
    return out.to_json()


def get_most_active_members(df):
    # returns top 10 most active members of the group
    out = df['Name'].value_counts().head(10)
    return out.to_json()


def get_most_popular_emojis(df):
    # returns the top 10 most popular emojis for the group
    emojis = extract_emojis(str(df.GroupMessage.values))
    emoji_list = emojis.split(' ')
    top_emojis = ', '.join([emoji for emoji, emoji_count in Counter(emoji_list).most_common(5)])
    return top_emojis


def process_chat_file(filepath):
    try:
        # get dir and path from filepath given
        # generate events, message, members dir
        # process data
        # return file paths

        # print("is_file_path_url(filepath): ", is_file_path_url(filepath))
        if is_file_path_url(filepath):
            doc = download_chat_file(filepath)
            chat_directory = doc.get('chat_directory')
            chat_file_path = doc.get('chat_file_path')

        else:
            path = Path(filepath)
            chat_directory = path.parent.absolute()
            chat_file_path = filepath

        event_file_path = os.path.join(chat_directory, 'events.csv')
        users_file_path = os.path.join(chat_directory, 'users.csv')
        messages_file_path = os.path.join(chat_directory, 'messages.csv')
        group_file_path = os.path.join(chat_directory, 'groups.csv')

        print("importing events")
        events = import_events(path=chat_file_path)
        events.to_csv(event_file_path, index=True, encoding='utf-8')
        print("importing messages")
        df = import_messages(path=chat_file_path)
        df.to_csv(messages_file_path, index=True, encoding='utf-8')
        print("importing users")
        user = user_stats(df)
        user.to_csv(users_file_path, index=True, encoding='utf-8')
        print("importing groups")
        group = group_stats(df)

        group.to_csv(group_file_path, index=True, encoding='utf-8')
        most_active_members = get_most_active_members(df)
        most_active_days = get_most_active_days(df)
        attrition = attrition_levels(events)
        most_active_time = get_most_active_time(df)
        most_popular_emojis = get_most_popular_emojis(df)

        file_info = dict(
            events=event_file_path, groups=group_file_path, users=users_file_path,
            messages=messages_file_path,
            attrition=attrition, most_active_days=most_active_days,
            most_active_time=most_active_time,
            most_active_members=most_active_members, most_popular_emojis=most_popular_emojis
        )
        return file_info
    except Exception as e:
        print(e)

    finally:
        pass
