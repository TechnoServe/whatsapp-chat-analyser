# This file contains all regular expressions that will be used by the analyser class


emoji_regex = r'(\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff])'

url_regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"

msg_line_regex = r'^(\d{1,2}\/\d{1,2}\/\d{2,4},\s\d{1,2}:\d{1,2}(?:\s[ap]m)?)\s+\-\s+([a-z\d\-\s\+\'\.,\/\(\)\@_]+):\s(.+)'

intro_regex = r'^\d{1,2}\/\d{1,2}\/\d{2,4},\s\d{1,2}\:\d{1,2}(?:\s[ap]m)?\s\-\s(Messages to this group are .+|Messages and calls are end-to-end encrypted.+)'
group_creator_regex = r'^(\d{1,2}\/\d{1,2}\/\d{2,4},\s\d{1,2}\:\d{1,2}(?:\s[ap]m)?)\s\-\s([a-z\d\-\s\+\'\.,\/\(\)\@_]+)\screated\sgroup\s"(.+)"$'

user_add_regex = r'^(\d{1,2}\/\d{1,2}\/\d{2,4},\s\d{1,2}\:\d{1,2}(?: [ap]m)?)\s\-\s((?:(?:[a-z\d\-\s\+\'\.,\/\(\)\@_]+\sadded\s.+)?\s)|(?:[a-z\d\-\s\+\'\.,\/\(\)\@_]+\sjoined\susing\s(?:your\sinvite|this\sgroup\'s\sinvite\slink))|(?:[a-z\d\-\s\+\'\.,\/\(\)\@_]+was\sadded)|You\sadded\s[a-z\d\-\s\+\'\.,\/\(\)\@_]+|You\swere\sadded)|[a-z\d\-\s\+\'\.,\/\(\)\@_]+\sadded\syou'

# untested... but seem oik
# user_add_regex = r'^(\d{1,2}\/\d{1,2}\/\d{2,4},\s\d{1,2}\:\d{1,2}(?: [ap]m)?)\s\-\s((?:(?:[a-z\d\-\s\+\'\.,\/\(\)\@_]+\sadded\s.+)?\s|(?:[a-z\d\-\s\+\'\.,\/\(\)\@_]+\sjoined\susing\s(?:your\sinvite|this\sgroup\'s\sinvite\slink))|(?:[a-z\d\-\s\+\'\.,\/\(\)\@_]+was\sadded)|You\sadded\s[a-z\d\-\s\+\'\.,\/\(\)\@_]+|You\swere\sadded)|[a-z\d\-\s\+\'\.,\/\(\)\@_]+\sadded\syou)'

user_left_regex = r'^(\d{1,2}\/\d{1,2}\/\d{2,4},\s\d{1,2}\:\d{1,2}(?:\s[ap]m)?)(\s\-\s[a-z\d\-\s\+\'\.,\/\(\)\@_]+)(\sleft)'
removed_users_regex = r'^(\d{1,2}\/\d{1,2}\/\d{2,4},\s\d{1,2}\:\d{1,2}(?:\s[ap]m)?)(\s\-\s[a-z\d\-\s\+\'\.,\/\(\)\@_]+)(\sremoved\s[a-z\d\-\s\+\'\.,\/\(\)\@_]+)'

send_mssg_settings_regex = r'settings to allow (all participants|only admins) to send messages to this group|changed this group\'s settings to allow (only admins|all participants) to edit this group\'s info|You changed the group description|changed the group description|reset this group\'s invite link$'
grp_icon_regex = r'this group\'s icon$'
security_code_change_regex = r'Your security code with .+ changed\. Tap to learn more'
number_change_regex = r'[\+\d\s]+ changed to [\+\d\s]+|[a-z\d\-\s\+\'\.,\/\@_]+ changed their phone number to a new number\. Tap to message or add the new number\.|You\'re now an admin'
group_name_change_regex = r'^(\d{1,2}\/\d{1,2}\/\d{2,4},\s\d{1,2}:\d{1,2}(?:\s[ap]m)?).+changed the subject from "(.+)" to "(.+)"'
