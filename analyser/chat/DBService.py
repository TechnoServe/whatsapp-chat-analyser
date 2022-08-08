from django.db import transaction, connection
from django.db.models import Q, Sum, Count, IntegerField, Min, Max, Avg, F, CharField, functions
from django.conf import settings
from requests import request

from analyser.models import Personnel, WhatsAppGroup, WhatsAppChatFile, GroupDailyStats, UserDailyStats, MessageLog, GroupNameChanges, STATUS_CHOICES, CounselorGroupAssignment, CounselorAdvisorAssignment
from analyser.serializers import GroupDailyStatsSerializer
from analyser.chat.Utilities import Utilities

from analyser.chat.UserManagement import UserManagement

from hashids import Hashids
from analyser.common_tasks import Notification, Terminal

import pandas as pd
import sentry_sdk

from datetime import datetime, timedelta
from tzlocal import get_localzone

import json

terminal = Terminal()
sentry_sdk.init(settings.SENTRY_DSN)
my_hashids = Hashids(min_length=5, salt=settings.SECRET_KEY)



class DBService:
    def get_all_chats(self, request):
        try:
            start = int(request.POST['start'])
            length_ = int(request.POST['length'])

            filters = Q()
            if 'search[value]' in request.POST and request.POST['search[value]'] != '':
                filters = Q(group__group_name__icontains=request.POST['search[value]']) | Q(title__icontains=request.POST['search[value]'])


            all_items_ = WhatsAppChatFile.objects.select_related('group').filter(filters).values('id', 'google_id', 'web_content_link', 'title', 'datetime_created', 'filesize', 'status', 'comments', group_name=F('group__group_name')).order_by('-datetime_created').all()[start:start+length_]

            all_filtered_items = WhatsAppChatFile.objects.select_related('group').filter(filters).values('id', 'google_id', 'web_content_link', 'title', 'datetime_created', 'filesize', 'status', 'comments', group_name=F('group__group_name')).order_by('-datetime_created').all()

            all_items = list(all_items_)
            
            return {
                'data': all_items, # JsonResponse(all_items, safe=False),
                "recordsTotal": WhatsAppChatFile.objects.count(),
                "draw": int(request.POST['draw']),
                "recordsFiltered": len(all_filtered_items)
            }

        except Exception as e:
            if settings.DEBUG: terminal.tprint(str(e), 'fail')
            sentry_sdk.capture_exception(e)
            raise Exception('There was an error while fetching data from the database')

    def fetch_groups_info(self):
        to_return = {}
        all_groups = GroupDailyStats.objects.select_related('group').values('group_id').annotate(group_name=F('group__group_name'), created_by=F('group__created_by'), new_users_=Sum('new_users'), left_users_=Sum('left_users'), no_messages_=Sum('no_messages'), no_images_=Sum('no_images'), no_links_=Sum('no_links'), date_created=functions.Cast('group__datetime_created', output_field=CharField() )).all()

        to_return['group_info'] = []

        for grp in all_groups:
            # get counselor assigned to group
            qs = CounselorGroupAssignment.objects.filter(group=grp['group_id']).select_related()
            if not qs:
                grp['counselor_'] = ''
            else:
                grp['counselor_'] = qs[0].counselor.first_name + " " + qs[0].counselor.last_name
            
            grp['group_id'] = my_hashids.encode(grp['group_id'])

            to_return['group_info'].append(grp)
        
        return to_return
    
    def fetch_ba_groups_info(self, advisor):
        groups = []
        userManagement = UserManagement()
        # get all counselors assigned to advisor
        counselors = CounselorAdvisorAssignment.objects.filter(advisor=advisor)
        
        # get all groups assigned to counselors of this advisor
        for user in counselors:
            counselor = Personnel.objects.filter(id=user.counselor_id).get()
            qs = CounselorGroupAssignment.objects.filter(counselor=counselor)
            
            for val in qs:
                groups.append(val.group_id)

        to_return = {}
        all_groups = GroupDailyStats.objects.filter(group_id__in=groups).select_related('group').values('group_id').annotate(group_name=F('group__group_name'), created_by=F('group__created_by'), new_users_=Sum('new_users'), left_users_=Sum('left_users'), no_messages_=Sum('no_messages'), no_images_=Sum('no_images'), no_links_=Sum('no_links'), date_created=functions.Cast('group__datetime_created', output_field=CharField() )).all()

        to_return['group_info'] = []

        for grp in all_groups:
            # get counselor assigned to group
            qs = CounselorGroupAssignment.objects.filter(group=grp['group_id']).select_related()
            if not qs:
                grp['counselor_'] = ''
            else:
                grp['counselor_'] = qs[0].counselor.first_name + " " + qs[0].counselor.last_name
            
            grp['group_id'] = my_hashids.encode(grp['group_id'])

            to_return['group_info'].append(grp)
        
        return to_return

    def fetch_bc_groups_info(self, counselor):
        groups = []
        userManagement = UserManagement()
        
        qs = CounselorGroupAssignment.objects.filter(counselor=counselor)
            
        for val in qs:
            groups.append(val.group_id)

        to_return = {}
        all_groups = GroupDailyStats.objects.filter(group_id__in=groups).select_related('group').values('group_id').annotate(group_name=F('group__group_name'), created_by=F('group__created_by'), new_users_=Sum('new_users'), left_users_=Sum('left_users'), no_messages_=Sum('no_messages'), no_images_=Sum('no_images'), no_links_=Sum('no_links'), date_created=functions.Cast('group__datetime_created', output_field=CharField() )).all()

        to_return['group_info'] = []

        for grp in all_groups:
            # get counselor assigned to group
            qs = CounselorGroupAssignment.objects.filter(group=grp['group_id']).select_related()
            if not qs:
                grp['counselor_'] = ''
            else:
                grp['counselor_'] = qs[0].counselor.first_name + " " + qs[0].counselor.last_name
            
            grp['group_id'] = my_hashids.encode(grp['group_id'])

            to_return['group_info'].append(grp)
        
        return to_return

    def save_day_stats(self, cur_day_details, group_id, chat_file_id):
        # 1. Save the group
        # 2. Save the group daily stats
        # 3. Save the user daily stats
        self.cur_file_messages = []
        max_count = {'hr': -1, 'count': -1}
        for hr_, count_ in cur_day_details['active_hrs'].items(): max_count={'hr':hr_, 'count':count_} if count_>max_count['count'] else max_count
        try:
            sgs = GroupDailyStats.objects.filter(group_id=group_id, stats_date=cur_day_details['date_']).get()

            # ok some stats exist, check if they all check out
            if(
                sgs.new_users == cur_day_details['new_users'] and sgs.left_users == cur_day_details['left_users'] and sgs.most_active_hr == max_count['hr'] and sgs.emojis == cur_day_details['emojis'] and
                sgs.no_messages == cur_day_details['no_messages'] and sgs.no_images == cur_day_details['no_images'] and sgs.no_links == cur_day_details['no_links']
            ):
                # we have a duplicate stat from another file... ignore it for noww
                return 'Duplicate GroupStats'
            else:
                # we have a mismatch.... so lets email the admins
                # sgs_serial= GroupDailyStatsSerializer(sgs, many=True)
                # print(json.dumps(sgs_serial.data, indent=3))
                cur_file = WhatsAppChatFile.objects.get(id=chat_file_id)
                cur_filename = cur_file.title

                first_file = WhatsAppChatFile.objects.get(id=sgs.chat_file_id)
                first_filename = first_file.title
                
                group = WhatsAppGroup.objects.get(id=sgs.group_id)
                group_name = group.group_name

                sgs_data = {
                    'new_users': sgs.new_users, 'left_users': sgs.left_users, 'most_active_hr': sgs.most_active_hr, 'emojis': sgs.emojis, 'no_messages': sgs.no_messages, 'no_images': sgs.no_images, 'no_links': sgs.no_links
                }

                stats_date = cur_day_details['date_']
                current_stats = {
                    'stats_date': cur_day_details['date_'],
                    'new_users': cur_day_details['new_users'],
                    'left_users': cur_day_details['left_users'],
                    'most_active_hr': max_count['hr'],
                    'emojis': cur_day_details['emojis'],
                    'no_messages': cur_day_details['no_messages'],
                    'no_images': cur_day_details['no_images'],
                    'no_links': cur_day_details['no_links']
                }
                
                stats_mismatch_comments = "There exists a group daily stats record for '%s' group for '%s' that was extracted from '%s'. However I have other stats for the same group for the same day extracted from '%s'. I don't know what to do. <br/><strong>Stats from %s</strong><br/><pre>%s</pre><br/><br/><strong>Stats from %s</strong><br/><pre>%s</pre><br/>" % (group_name, stats_date, first_filename, cur_filename, first_filename, json.dumps(sgs_data, indent=3), cur_filename, json.dumps(current_stats, indent=3))

                self.cur_file_messages.append(stats_mismatch_comments)
                notify = Notification()
                notify.send_sentry_message(stats_mismatch_comments, 'info', [{'tag': 'saved_stats', 'value': sgs_data}, {'tag':'new_stats', 'value': json.dumps(current_stats, indent=3)}])
                return 'Mismatched GroupStats'

        except GroupDailyStats.DoesNotExist: pass   # the stats dont exist which is good

        grp_stats = GroupDailyStats(
            group_id=group_id,
            chat_file_id=chat_file_id,
            stats_date=cur_day_details['date_'],
            new_users=cur_day_details['new_users'],
            left_users=cur_day_details['left_users'],
            most_active_hr=max_count['hr'],
            emojis=cur_day_details['emojis'],
            no_messages=cur_day_details['no_messages'],
            no_images=cur_day_details['no_images'],
            no_links=cur_day_details['no_links']
        )
        grp_stats.full_clean()
        grp_stats.save()

        for u_name_phone, us in cur_day_details['users'].items():
            us_count = {'hr': -1, 'count': -1}
            for hr_, count_ in us['active_hrs'].items(): us_count={'hr':hr_, 'count':count_} if count_>us_count['count'] else us_count

            try:
                uds = UserDailyStats.objects.filter(name_phone=u_name_phone, group_id=group_id, stats_date=cur_day_details['date_']).get()

                # check if its a duplicate
                if uds.most_active_hr == us_count['hr'] and uds.emojis == us['emojis'] and uds.no_messages == us['no_messages'] and uds.no_images == us['no_images'] and uds.no_links == us['no_links']:
                    return 'Duplicate UserStats'
                else:
                    cur_file = WhatsAppChatFile.objects.get(id=chat_file_id)
                    cur_filename = cur_file.title

                    first_file = WhatsAppChatFile.objects.get(id=uds.chat_file_id)
                    first_filename = first_file.title
                    
                    group = WhatsAppGroup.objects.get(id=uds.group_id)
                    group_name = group.group_name

                    uds_data = {
                        'most_active_hr': uds.most_active_hr, 'emojis': uds.emojis, 'no_messages': uds.no_messages, 'no_images': uds.no_images, 'no_links': uds.no_links
                    }

                    stats_date = cur_day_details['date_']
                    current_stats = {
                        'most_active_hr': us_count['hr'],
                        'emojis': us['emojis'],
                        'no_messages': us['no_messages'],
                        'no_images': us['no_images'],
                        'no_links': us['no_links']
                    }
                    
                    stats_mismatch_comments = "There exists a group daily stats record for '%s' group for '%s' that was extracted from '%s'. However I have other stats for the same group for the same day extracted from '%s'. I don't know what to do. <br/><strong>Stats from %s</strong><br/><pre>%s</pre><br/><br/><strong>Stats from %s</strong><br/><pre>%s</pre><br/>" % (group_name, stats_date, first_filename, cur_filename, first_filename, json.dumps(uds_data, indent=3), cur_filename, json.dumps(current_stats, indent=3))

                    self.cur_file_messages.append(stats_mismatch_comments)
                    notify = Notification()
                    notify.send_sentry_message(stats_mismatch_comments, 'info', [{'tag': 'saved_stats', 'value': uds_data}, {'tag':'new_stats', 'value': json.dumps(current_stats, indent=3)}])

                    return 'Mismatched UserStats'

            except UserDailyStats.DoesNotExist: pass

            stats_ = UserDailyStats(
                name_phone=u_name_phone,
                group_id=group_id,
                chat_file_id=chat_file_id,
                stats_date=cur_day_details['date_'],
                most_active_hr=us_count['hr'],
                emojis=us['emojis'],
                no_messages=us['no_messages'],
                no_images=us['no_images'],
                no_links=us['no_links']
            )
            stats_.full_clean()
            stats_.save()

            for mssg in us['messages']:
                ml = MessageLog(
                    chat_file_id=chat_file_id,
                    user=stats_,
                    datetime_sent=mssg[0],
                    message=mssg[2]
                )
                ml.full_clean()
                ml.save()

                # raise Exception('tarn tramps %s ' % json.dumps(cur_day_details))

        return 'Saved'

    def save_group_name_changes(self, grp_names, group_id):
        for name_ in grp_names:
            name_change = GroupNameChanges(
                group_id=group_id,
                change_datetime=name_['date_time'],
                from_name=name_['from'],
                to_name=name_['to']
            )
            name_change.full_clean()
            name_change.save()

    def fetch_group_meta(self, group_id, date_range):
        grp = WhatsAppGroup.objects.get(id=group_id)
        last_date = GroupDailyStats.objects.filter(group_id=group_id).values('stats_date').order_by('-stats_date').first()
        first_date = GroupDailyStats.objects.filter(group_id=group_id).values('stats_date').order_by('stats_date').first()
        if last_date is None: return {'info_message': 'The processed database is empty. Please run the initial processing.', 'empty_db': True}
        to_return = Utilities.determine_dateranges(date_range, first_date['stats_date'], last_date['stats_date'])
        to_return['group_name'] = grp.group_name
        s_date = to_return['ss_date']
        e_date = to_return['ee_date']

        # most active day
        most_active_day = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).values('stats_date', 'no_messages').order_by('-no_messages').first()
        if date_range is None:
            to_return['info_message'] = 'Date range is not defined. Showing analysis for the period %s - %s' % (to_return['min_date'], to_return['max_date'])
            

        elif most_active_day is None:
            # put a good time range
            to_return['info_message'] = 'No records were found in the specified time period %s - %s. The last chat date is %s. Showing analysis for the period %s - %s' % (to_return['s_date'], to_return['e_date'], to_return['max_date'], to_return['min_date'], to_return['max_date'])
            to_return['s_date'] = to_return['min_date']
            to_return['e_date'] = to_return['max_date']
            s_date = datetime.strptime(to_return['s_date'], '%d/%m/%Y')
            e_date = datetime.strptime(to_return['e_date'], '%d/%m/%Y')

            most_active_day = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).values('stats_date', 'no_messages').order_by('-no_messages').first()
            

        period_stats = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).aggregate(lefties=Sum('left_users'), joinies=Sum('new_users'), images_count=Sum('no_images'), links_count=Sum('no_links'), messages_count=Sum('no_messages'))

        total_users = GroupDailyStats.objects.filter(stats_date__lte=e_date, group_id=group_id).aggregate(lefties=Sum('left_users'), joinies=Sum('new_users'))
        to_return['name_changes'] = GroupNameChanges.objects.filter(group_id=group_id).extra(select={'change_datetime_':"DATE_FORMAT(change_datetime, '%%b %%d %%Y, %%r')"}).values('to_name', 'from_name', 'change_datetime_').annotate(tn=Count('change_datetime')).order_by('-change_datetime').all()

        # most active user
        most_active_user = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).values('name_phone').annotate(sum_messages=Sum('no_messages')).order_by('-sum_messages').first()
        

        #Most Active users # Gladys
        week_2_before = last_date['stats_date'] - timedelta(days=14)
        month_before = last_date['stats_date'] - timedelta(days=30)
        last_active_users_2_week_before = UserDailyStats.objects.filter(stats_date__gte=week_2_before, stats_date__lte=last_date['stats_date'], group_id=group_id).values('name_phone').annotate(sum_messages=Sum('no_messages')).order_by('-sum_messages')[:10]
        last_active_users_month_before = UserDailyStats.objects.filter(stats_date__gte=month_before, stats_date__lte=last_date['stats_date'], group_id=group_id).values('name_phone').annotate(sum_messages=Sum('no_messages')).order_by('-sum_messages')[:10]
        

        # most active time of the day
        most_active_time = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).exclude(most_active_hr=-1).values('most_active_hr').annotate(messages_count=Count('most_active_hr')).order_by('-messages_count').first()



        # active days
        datelist = pd.date_range(s_date, e_date).tolist()
        all_data_df = pd.DataFrame(list( GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).extra(select={'stats_date_':"DATE_FORMAT(stats_date, '%%Y-%%m-%%d')"}).values('stats_date_', 'no_messages').order_by('stats_date_').all() ))
        
        active_users_df = pd.DataFrame(list( UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).extra(select={'stats_date_':"DATE_FORMAT(stats_date, '%%Y-%%m-%%d')"}).values('stats_date_').annotate(no_users=Count('name_phone')).order_by('stats_date_').all() ))
        
        recs = all_data_df.set_index('stats_date_').T.to_dict('records')[0]
        all_users = active_users_df.set_index('stats_date_').T.to_dict('records')[0]

        cool_dates = []
        cool_messages = []
        cool_users = []
        for date_ in datelist:
            cool_date = date_.strftime('%Y-%m-%d')
            cool_dates.append(cool_date)

            if str(cool_date) not in recs: cool_messages.append(0)
            else: cool_messages.append(recs[cool_date])

            if str(cool_date) not in all_users: cool_users.append(0)
            else: cool_users.append(all_users[cool_date])

        # emojis
        sumd_emojis = {}
        emoji_count = 0
        all_emojis = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).values('emojis').all()
        for al_ in all_emojis:
            emoji_stats = Utilities.emoji_count(al_['emojis'])
            for k in set(emoji_stats): emoji_count += emoji_stats.get(k, 0)

            sumd_emojis = {k: emoji_stats.get(k, 0) + sumd_emojis.get(k, 0) for k in set(emoji_stats) | set(sumd_emojis) }

        to_return['emojis'] = [ {'e': k, 'y': v} for k, v in sorted(sumd_emojis.items(), key=lambda x: x[1], reverse=True) ]
        to_return['emojis_count'] = emoji_count
        to_return['links_count'] = period_stats['links_count']
        to_return['messages_count'] = period_stats['messages_count']
        to_return['images_count'] = period_stats['images_count']

        to_return['active_user'] = most_active_user
        to_return['no_users'] = total_users['joinies'] - total_users['lefties']
        to_return['totals'] = emoji_count + period_stats['images_count'] + period_stats['links_count'] + period_stats['messages_count']
        to_return['most_active_day'] = most_active_day['stats_date'].strftime('%d/%m/%Y, %A')
        to_return['most_active_time'] = most_active_time
        to_return['active_dates'] = {'dates': cool_dates, 'messages': cool_messages, 'users': cool_users}


        #Gladys
        to_return['last_active_users_2_week_before'] = last_active_users_2_week_before
        to_return['last_active_users_month_before'] = last_active_users_month_before


        to_return = {**to_return, **period_stats}
        
        return to_return

    def fetch_user_meta(self, group_id, user_, date_range):
        grp = WhatsAppGroup.objects.get(id=group_id)
        last_date = UserDailyStats.objects.filter(group_id=group_id, name_phone=user_).values('stats_date').order_by('-stats_date').first()
        first_date = UserDailyStats.objects.filter(group_id=group_id, name_phone=user_).values('stats_date').order_by('stats_date').first()
        if last_date is None: return {'info_message': 'The processed database is empty. Please run the initial processing.', 'empty_db': True}
        to_return = Utilities.determine_dateranges(date_range, first_date['stats_date'], last_date['stats_date'])
        to_return['user_name'] = '%s of %s' % (user_, grp.group_name)
        s_date = to_return['ss_date']
        e_date = to_return['ee_date']

        # most active day
        most_active_day = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id, name_phone=user_).values('stats_date', 'no_messages').order_by('-no_messages').first()
        if date_range is None:
            to_return['info_message'] = 'Date range is not defined. Showing analysis for the period %s - %s' % (to_return['min_date'], to_return['max_date'])

        elif most_active_day is None:
            # put a good time range
            to_return['info_message'] = 'No records were found in the specified time period %s - %s. The last chat date is %s. Showing analysis for the period %s - %s' % (to_return['s_date'], to_return['e_date'], to_return['max_date'], to_return['min_date'], to_return['max_date'])
            to_return['s_date'] = to_return['min_date']
            to_return['e_date'] = to_return['max_date']
            s_date = datetime.strptime(to_return['s_date'], '%d/%m/%Y')
            e_date = datetime.strptime(to_return['e_date'], '%d/%m/%Y')

            most_active_day = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id, name_phone=user_).values('stats_date', 'no_messages').order_by('-no_messages').first()
            
        period_stats = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id, name_phone=user_).aggregate(images_count=Sum('no_images'), links_count=Sum('no_links'), messages_count=Sum('no_messages'))

        # group interaction
        grp_stats = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id).aggregate(messages_count=Sum('no_messages'))
        to_return['grp_interaction'] = float('{0:.1f}'.format( ((period_stats['messages_count'] / grp_stats['messages_count']) * 100) ))

        # most active time of the day
        most_active_time = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id, name_phone=user_).exclude(most_active_hr=-1).values('most_active_hr').annotate(messages_count=Count('most_active_hr')).order_by('-messages_count').first()

        # active days
        datelist = pd.date_range(s_date, e_date).tolist()
        all_ = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id, name_phone=user_).extra(select={'stats_date_':"DATE_FORMAT(stats_date, '%%Y-%%m-%%d')"}).values('stats_date_', 'no_messages').order_by('stats_date_').all()
        all_data_df = pd.DataFrame(list( all_ ))
        
        recs = all_data_df.set_index('stats_date_').T.to_dict('records')[0]
        cool_dates = []
        cool_messages = []
        for date_ in datelist:
            cool_date = date_.strftime('%Y-%m-%d')
            cool_dates.append(cool_date)

            if str(cool_date) not in recs: cool_messages.append(0)
            else: cool_messages.append(recs[cool_date])

        # emojis
        sumd_emojis = {}
        emoji_count = 0
        all_emojis = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id=group_id, name_phone=user_).values('emojis').all()
        for al_ in all_emojis:
            emoji_stats = Utilities.emoji_count(al_['emojis'])
            for k in set(emoji_stats): emoji_count += emoji_stats.get(k, 0)

            sumd_emojis = {k: emoji_stats.get(k, 0) + sumd_emojis.get(k, 0) for k in set(emoji_stats) | set(sumd_emojis) }

        # actual messages
        all_messages = list(MessageLog.objects.select_related('user').filter(user__stats_date__gte=s_date, user__stats_date__lte=e_date, user__group_id=group_id, user__name_phone=user_).extra(select={'dt':"DATE_FORMAT(datetime_sent, '%%Y-%%m-%%d %%H:%%i')"}).values('dt').annotate(mssg=F('message')).order_by('datetime_sent').all())

        to_return['emojis'] = [ {'e': k, 'y': v} for k, v in sorted(sumd_emojis.items(), key=lambda x: x[1], reverse=True) ]
        to_return['all_messages'] = all_messages
        to_return['emojis_count'] = emoji_count
        to_return['most_active_day'] = most_active_day['stats_date'].strftime('%d/%m/%Y, %A')
        to_return['most_active_time'] = most_active_time
        to_return['active_dates'] = {'dates': cool_dates, 'messages': cool_messages}
        
        to_return = {**to_return, **period_stats}
        
        return to_return

    def fetch_all_meta(self, date_range):
        last_date = GroupDailyStats.objects.values('stats_date').order_by('-stats_date').first()
        first_date = GroupDailyStats.objects.values('stats_date').order_by('stats_date').first()
        if last_date is None: return {'info_message': 'The processed database is empty. Please run the initial processing.', 'empty_db': True}
        to_return = Utilities.determine_dateranges(date_range, first_date['stats_date'], last_date['stats_date'])
        s_date = to_return['ss_date']
        e_date = to_return['ee_date']

        # Whatsapp groups
        emoji_count = 0
        all_emojis = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date).values('emojis').all()
        for al_ in all_emojis:
            emoji_stats = Utilities.emoji_count(al_['emojis'])
            for k in set(emoji_stats): emoji_count += emoji_stats.get(k, 0)

        to_return['file_status'] = { st_[0]: 0 for st_ in STATUS_CHOICES }
        status_counts = list(WhatsAppChatFile.objects.values('status').annotate(s_count=Count('status')).all())
        all_count = 0
        for st_ in status_counts:
            to_return['file_status'][st_['status']] = st_['s_count']
            all_count += st_['s_count']

        to_return['perc_processed'] = float('{0:.1f}'.format( (( to_return['file_status']['processed'] / all_count ) * 100) )) 
        to_return['no_groups'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date).values('group_id').annotate(g_count=Count('group_id')).count()
        to_return['no_users'] = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date).values('group_id', 'name_phone').annotate(g_count=Count('group_id'), u_count=Count('name_phone')).count()
        to_return['no_messages'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date).aggregate(g_count=Sum('no_messages'))['g_count']
        to_return['no_images'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date).aggregate(g_count=Sum('no_images'))['g_count']
        to_return['no_links'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date).aggregate(g_count=Sum('no_links'))['g_count']
        to_return['no_emojis'] = emoji_count

        return to_return


    def fetch_all_meta_bc(self, date_range, counselor):
        groups = []
        userManagement = UserManagement()
        
        qs = CounselorGroupAssignment.objects.filter(counselor=counselor)
            
        for val in qs:
            groups.append(val.group_id)

        last_date = GroupDailyStats.objects.filter(group_id__in=groups).values('stats_date').order_by('-stats_date').first()
        first_date = GroupDailyStats.objects.filter(group_id__in=groups).values('stats_date').order_by('stats_date').first()
        if last_date is None: return {'info_message': 'The processed database is empty. Please run the initial processing.', 'empty_db': True}
        to_return = Utilities.determine_dateranges(date_range, first_date['stats_date'], last_date['stats_date'])
        s_date = to_return['ss_date']
        e_date = to_return['ee_date']

        # Whatsapp groups
        emoji_count = 0
        all_emojis = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id__in=groups).values('emojis').all()
        for al_ in all_emojis:
            emoji_stats = Utilities.emoji_count(al_['emojis'])
            for k in set(emoji_stats): emoji_count += emoji_stats.get(k, 0)

        to_return['file_status'] = { st_[0]: 0 for st_ in STATUS_CHOICES }
        status_counts = list(WhatsAppChatFile.objects.filter(group_id__in=groups).values('status').annotate(s_count=Count('status')).all())
        # print(status_counts)
        all_count = 0
        for st_ in status_counts:
            to_return['file_status'][st_['status']] = st_['s_count']
            all_count += st_['s_count']

        to_return['perc_processed'] = float('{0:.1f}'.format( (( to_return['file_status']['processed'] / all_count ) * 100) )) 
        to_return['no_groups'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id__in=groups).values('group_id').annotate(g_count=Count('group_id')).count()
        to_return['no_users'] = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id__in=groups).values('group_id', 'name_phone').annotate(g_count=Count('group_id'), u_count=Count('name_phone')).count()
        to_return['no_messages'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id__in=groups).aggregate(g_count=Sum('no_messages'))['g_count']
        to_return['no_images'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id__in=groups).aggregate(g_count=Sum('no_images'))['g_count']
        to_return['no_links'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id__in=groups).aggregate(g_count=Sum('no_links'))['g_count']
        to_return['no_emojis'] = emoji_count

        return to_return

    def fetch_all_meta_ba(self, date_range, advisor):
        groups = []
        userManagement = UserManagement()
        
        # get all counselors assigned to advisor
        counselors = CounselorAdvisorAssignment.objects.filter(advisor=advisor)
        
        # get all groups assigned to counselors of this advisor
        for user in counselors:
            counselor = Personnel.objects.filter(id=user.counselor_id).get()
            qs = CounselorGroupAssignment.objects.filter(counselor=counselor)
            
            for val in qs:
                groups.append(val.group_id)

        last_date = GroupDailyStats.objects.filter(group_id__in=groups).values('stats_date').order_by('-stats_date').first()
        first_date = GroupDailyStats.objects.filter(group_id__in=groups).values('stats_date').order_by('stats_date').first()
        if last_date is None: return {'info_message': 'The processed database is empty. Please run the initial processing.', 'empty_db': True}
        to_return = Utilities.determine_dateranges(date_range, first_date['stats_date'], last_date['stats_date'])
        s_date = to_return['ss_date']
        e_date = to_return['ee_date']

        # Whatsapp groups
        emoji_count = 0
        all_emojis = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id__in=groups).values('emojis').all()
        for al_ in all_emojis:
            emoji_stats = Utilities.emoji_count(al_['emojis'])
            for k in set(emoji_stats): emoji_count += emoji_stats.get(k, 0)

        to_return['file_status'] = { st_[0]: 0 for st_ in STATUS_CHOICES }
        status_counts = list(WhatsAppChatFile.objects.filter(group_id__in=groups).values('status').annotate(s_count=Count('status')).all())
        all_count = 0
        for st_ in status_counts:
            to_return['file_status'][st_['status']] = st_['s_count']
            all_count += st_['s_count']

        to_return['perc_processed'] = float('{0:.1f}'.format( (( to_return['file_status']['processed'] / all_count ) * 100) )) 
        to_return['no_groups'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id__in=groups).values('group_id').annotate(g_count=Count('group_id')).count()
        to_return['no_users'] = UserDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id__in=groups).values('group_id', 'name_phone').annotate(g_count=Count('group_id'), u_count=Count('name_phone')).count()
        to_return['no_messages'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id__in=groups).aggregate(g_count=Sum('no_messages'))['g_count']
        to_return['no_images'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id__in=groups).aggregate(g_count=Sum('no_images'))['g_count']
        to_return['no_links'] = GroupDailyStats.objects.filter(stats_date__gte=s_date, stats_date__lte=e_date, group_id__in=groups).aggregate(g_count=Sum('no_links'))['g_count']
        to_return['no_emojis'] = emoji_count

        return to_return


    def fetch_engaged_users(self, request):
        start = int(request.POST['start'])
        length_ = int(request.POST['length'])

        if 'search[value]' in request.POST and request.POST['search[value]'] != '':
            filters = Q(name_phone__icontains=request.POST['search[value]']) | Q(group__group_name__icontains=request.POST['search[value]'])

        else:
            filters = Q()

        if 'order[0][column]' not in request.POST:
            order_col = 'id' 
        else:
            if request.POST['order[0][column]'] == '0': order_col = 'id'
            else:
                order_dir = '' if request.POST['order[0][dir]'] == 'asc' else '-'
                order_col = '%s%s' % (order_dir, request.POST['columns[%s][data]' % request.POST['order[0][column]']])

            # filters = reduce(lambda q, f: q | Q(creator=f), filters_, Q())

        all_items = UserDailyStats.objects.select_related('group').filter(filters).values('name_phone', 'group_id', 'group__group_name').annotate(name_phone_=Count('name_phone'), group_id_=Count('group_id'), no_messages=Sum('no_messages'), no_images=Sum('no_images'), no_links=Sum('no_links'), group_name=F('group__group_name')).order_by(order_col)
        filtered_items = all_items[start:start+length_]
        all_filtered_items = len(all_items)

        filtered_items_ = []
        for fi in filtered_items:
            fi['group_id'] = my_hashids.encode(fi['group_id'])
            filtered_items_.append(fi)
        
        returnees_ = {
            'data': filtered_items_, # JsonResponse(all_items, safe=False),
            "recordsTotal": UserDailyStats.objects.values('group_id', 'name_phone').annotate(g_count=Count('group_id'), u_count=Count('name_phone')).count(),
            "draw": int(request.POST['draw']),
            "recordsFiltered": all_filtered_items
        }

        return returnees_
        return {**to_return, **returnees_}
