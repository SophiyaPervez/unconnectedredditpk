import os, time, datetime, random, ast#, math
from collections import defaultdict, Counter
from operator import itemgetter
from location import MEMLOC
from unconnectedreddit import celery_app1
from django.core.cache import get_cache, cache
from django.db.models import Count, Q, F, Sum
from datetime import datetime, timedelta
from django.utils import timezone
from cricket_score import cricket_scr
from imagestorage import delete_from_blob
from image_processing import clean_image_file_with_hash
from send_sms import process_sms, bind_user_to_twilio_notify_service
from score import PUBLIC_GROUP_MESSAGE, PRIVATE_GROUP_MESSAGE, PUBLICREPLY, PHOTO_HOT_SCORE_REQ, UPVOTE, DOWNVOTE, SUPER_DOWNVOTE,\
SUPER_UPVOTE, GIBBERISH_PUNISHMENT_MULTIPLIER
from .models import Photo, LatestSalat, Photo, PhotoComment, Link, Publicreply, TotalFanAndPhotos, Report, UserProfile, \
Video, HotUser, PhotoStream, HellBanList#, Vote
from redis3 import add_search_photo, bulk_add_search_photos, log_gibberish_text_writer, get_gibberish_text_writers, \
queue_punishment_amount, save_used_item_photo, del_orphaned_classified_photos, save_single_unfinished_ad, save_consumer_number, \
process_ad_final_deletion, process_ad_expiry
from .redis4 import expire_online_users, get_recent_online
from .redis2 import set_benchmark, get_uploader_percentile, bulk_create_photo_notifications_for_fans, \
bulk_update_notifications, update_notification, create_notification, update_object, create_object, add_to_photo_owner_activity,\
get_active_fans, public_group_attendance, expire_top_groups, public_group_vote_incr, clean_expired_notifications, get_top_100,\
get_fan_counts_in_bulk, get_all_fans, is_fan#, get_latest_online
from .redis1 import add_filtered_post, add_unfiltered_post, all_photos, add_video, save_recent_video, add_to_deletion_queue, \
delete_queue, photo_link_mapping, add_home_link, get_group_members, set_best_photo, get_best_photo, get_previous_best_photo, \
add_photos_to_best, retrieve_photo_posts, account_created, set_prev_retort, get_current_cricket_match, del_cricket_match, \
update_cricket_match, del_delay_cricket_match, get_cricket_ttl, get_prev_status, set_prev_replies, set_prev_group_replies, \
delete_photo_report, insert_hash, delete_avg_hash, log_urdu#, retrieve_first_page
from ecomm_tracking import insert_latest_metrics
from links.azurevids.azurevids import uploadvid
from namaz_timings import namaz_timings, streak_alive
from django.contrib.auth.models import User
from facebook_api import photo_poster
from math import log

# from mixpanel import Mixpanel
# from unconnectedreddit.settings import MIXPANEL_TOKEN

# mp = Mixpanel(MIXPANEL_TOKEN)

VOTE_WEIGHT = 1.5 # used for calculating daily benchmark
FLOOR_PERCENTILE = 0.5
CEILING_PERCENTILE = 0.9 # (inclusive)
MIN_FANS_TARGETED = 0.1 # 10%
MAX_FANS_TARGETED = 0.95 # 95%

def convert_to_epoch(time):
	return (time-datetime(1970,1,1)).total_seconds()

def set_rank(netvotes,upload_time):
	# Based on reddit ranking algo at https://medium.com/hacking-and-gonzo/how-reddit-ranking-algorithms-work-ef111e33d0d9
	if netvotes == None:
		netvotes = 0
	order = log(max(abs(netvotes), 1), 10) #0.041392685 for zero votes, log 1 = 0
	sign = 1 if netvotes > 0 else -1 if netvotes < 0 else 0
	secs = upload_time - 1432201843 # Thu, 21 May 2015 09:50:43 GMT coverted to epoch time
	return round(sign * order + secs / 45000, 8)

def fans_targeted(current_percentile):
	overall_range = CEILING_PERCENTILE - FLOOR_PERCENTILE
	current_range = current_percentile - FLOOR_PERCENTILE
	proportion = (current_range*1.0)/overall_range
	fans_targeted_delta = MAX_FANS_TARGETED - MIN_FANS_TARGETED
	percentage_to_target = (proportion * fans_targeted_delta * 1.0) + MIN_FANS_TARGETED
	return percentage_to_target

def fans_to_notify_in_ua(user_id, percentage_of_fans_to_notify,fan_ids_list):
	num_of_fans_to_notify = len(fan_ids_list) * percentage_of_fans_to_notify
	if num_of_fans_to_notify:
		fan_ids_to_notify = get_active_fans(user_id,int(num_of_fans_to_notify))
	try:
		fan_ids_to_notify = map(int, fan_ids_to_notify)
		remaining_fan_ids = set(fan_ids_list) - set(fan_ids_to_notify)
		return remaining_fan_ids, fan_ids_to_notify
	except:
		return fan_ids_list,0

def punish_gibberish_writers(dict_of_targets):
	for user_id, score_penalty in dict_of_targets.items():
		UserProfile.objects.filter(user_id=user_id).update(score=F('score')-score_penalty)
		queue_punishment_amount(user_id,score_penalty)
	# for user_id,payable_score in payables:
	# 	UserProfile.objects.filter(user_id=user_id).update(score=F('score')+payable_score)

@celery_app1.task(name='tasks.save_consumer_credentials')
def save_consumer_credentials(account_kit_id, mobile_data, user_id):
	save_consumer_number(account_kit_id,mobile_data,user_id)

@celery_app1.task(name='tasks.save_unfinished_ad')
def save_unfinished_ad(context):
	save_single_unfinished_ad(context)

@celery_app1.task(name='tasks.save_ecomm_photo_hash')
def save_ecomm_photo_hash(photo1_payload, photo2_payload, photo3_payload):
	if photo1_payload:
		photo1_payload = ast.literal_eval(photo1_payload)
		insert_hash(photo1_payload[0],photo1_payload[1],'ecomm') #perceptual hash of item photo 1
	if photo2_payload:
		photo2_payload = ast.literal_eval(photo2_payload)
		insert_hash(photo2_payload[0],photo2_payload[1],'ecomm') #perceptual hash of item photo 2
	if photo3_payload:
		photo3_payload = ast.literal_eval(photo3_payload)
		insert_hash(photo3_payload[0],photo3_payload[1],'ecomm') #perceptual hash of item photo 3

@celery_app1.task(name='tasks.upload_ecomm_photo')
def upload_ecomm_photo(photo_id, user_id, ad_id):
	# insert_hash(photo_id, avghash, 'ecomm') #perceptual hash of the item photo
	save_used_item_photo(user_id, ad_id, photo_id)

# schedule this every 2.5 hours
@celery_app1.task(name='tasks.sanitize_unused_ecomm_photos')
def sanitize_unused_ecomm_photos(photo_ids=None):
	if not photo_ids:
		photo_ids = del_orphaned_classified_photos()
	if photo_ids:
		# deleting model objects
		qset = Photo.objects.filter(id__in=photo_ids)
		images_and_hashes = qset.values_list('image_file','avg_hash')#flat=True)
		image_names, avg_hashes= zip(*images_and_hashes)
		qset.delete()
		# deleting actual images+thumbnails in azure storage
		delete_avg_hash(avg_hashes,categ='ecomm')
		delete_from_blob(image_names)

@celery_app1.task(name='tasks.set_user_binding_with_twilio_notify_service')
def set_user_binding_with_twilio_notify_service(user_id,phone_number):
	bind_user_to_twilio_notify_service(user_id,phone_number)

# execute every 55 mins
@celery_app1.task(name='tasks.expire_classifieds')
def expire_classifieds():
	process_ad_expiry()

# execute every 2 days
@celery_app1.task(name='tasks.delete_expired_classifieds')
def delete_expired_classifieds():
	process_ad_final_deletion()

# execute every 24 hours
@celery_app1.task(name='tasks.calc_ecomm_metrics')
def calc_ecomm_metrics():
	insert_latest_metrics()


@celery_app1.task(name='tasks.log_gibberish')
def log_gibberish_writer(user_id,text,length_of_text):
	if length_of_text > 10 and ' ' not in text:
		log_gibberish_text_writer(user_id)

@celery_app1.task(name='tasks.capture_urdu')
def capture_urdu(text):
	log_urdu(text)

@celery_app1.task(name='tasks.enqueue_sms')
def enqueue_sms(mobile_number, ad_id, status=None, buyer_number=None):
	process_sms(mobile_number,ad_id,status, buyer_number)

@celery_app1.task(name='tasks.delete_notifications')
def delete_notifications(user_id):
	clean_expired_notifications(user_id)

@celery_app1.task(name='tasks.calc_gibberish_punishment')
def calc_gibberish_punishment():
	all_gibberish_writers = get_gibberish_text_writers()
	if all_gibberish_writers:
		all_gibberish_writers_above_threshold = {k:v for k,v in all_gibberish_writers if v>3}
		if all_gibberish_writers_above_threshold:
			gibberish_punishment = {}
			for k in all_gibberish_writers_above_threshold.keys():
				all_gibberish_writers_above_threshold[k] *= GIBBERISH_PUNISHMENT_MULTIPLIER
			punish_gibberish_writers(all_gibberish_writers_above_threshold)

@celery_app1.task(name='tasks.calc_photo_quality_benchmark')
def calc_photo_quality_benchmark():
	two_days = datetime.utcnow()-timedelta(hours=24*2)
	photos_total_score_list = Photo.objects.filter(upload_time__gte=two_days).values_list('owner_id','visible_score')
	# print photos_total_score_list
	if photos_total_score_list:
		total_photos_per_user = Counter(elem[0] for elem in photos_total_score_list) #dictionary, e.g. Counter({2: 8, 1: 7})
		# print "total photos per user: %s" % total_photos_per_user
		total_scores_per_user = defaultdict(int)
		for key,val in photos_total_score_list:
			total_scores_per_user[key] += val
		# print "total scores per user: %s" % total_scores_per_user
		uploader_scores = []
		for key,val in total_scores_per_user.items():
			uploader_scores.append(key)
			uploader_scores.append(float(val)/total_photos_per_user[key])
		# print uploader_scores
		set_benchmark(uploader_scores)

@celery_app1.task(name='tasks.bulk_create_notifications')
def bulk_create_notifications(user_id, photo_id, epochtime, photourl, name, caption):
	fan_ids_list, total_fans, recent_fans = get_all_fans(user_id)
	if fan_ids_list:
		fans_notified_in_ua = 0
		percentage_of_users_beaten = get_uploader_percentile(user_id)
		if 0 <= percentage_of_users_beaten < FLOOR_PERCENTILE:
			notify_in_ua = []
			fans_notified_in_ua = 0
			percentage_of_fans_to_notify = 0
			bulk_create_photo_notifications_for_fans(viewer_id_list=fan_ids_list,object_id=photo_id,seen=False,updated_at=epochtime,\
				unseen_activity=False)
		elif FLOOR_PERCENTILE <= percentage_of_users_beaten <= CEILING_PERCENTILE:
			percentage_of_fans_to_notify = fans_targeted(percentage_of_users_beaten)
			remaining_ids, notify_in_ua = fans_to_notify_in_ua(user_id, percentage_of_fans_to_notify, fan_ids_list)
			if notify_in_ua:
				bulk_create_photo_notifications_for_fans(viewer_id_list=notify_in_ua,object_id=photo_id,seen=False,\
					updated_at=epochtime,unseen_activity=True)
				fans_notified_in_ua = len(notify_in_ua)
			else:
				fans_notified_in_ua = 0
			bulk_create_photo_notifications_for_fans(viewer_id_list=remaining_ids,object_id=photo_id,seen=False,\
				updated_at=epochtime,unseen_activity=False)
		elif CEILING_PERCENTILE < percentage_of_users_beaten <= 1:
			fans_notified_in_ua = len(fan_ids_list)
			notify_in_ua = fan_ids_list
			percentage_of_fans_to_notify = 1
			bulk_create_photo_notifications_for_fans(viewer_id_list=fan_ids_list,object_id=photo_id,seen=False,updated_at=epochtime,\
				unseen_activity=True)
		else:
			notify_in_ua = 0
			fans_notified_in_ua = 0
			percentage_of_fans_to_notify = 0
			bulk_create_photo_notifications_for_fans(viewer_id_list=fan_ids_list,object_id=photo_id,seen=False,updated_at=epochtime,\
				unseen_activity=False)
		# object and notification for self, that reports how many fans we reached out to!
		create_object(object_id=photo_id, object_type='1',object_owner_id=user_id,photourl=photourl, vote_score=total_fans, \
			slug=fans_notified_in_ua, res_count=notify_in_ua,is_thnks=percentage_of_fans_to_notify,object_owner_name=name, \
			object_desc=caption)
		create_notification(viewer_id=user_id,object_id=photo_id,object_type='1',seen=False, updated_at=epochtime,\
			unseen_activity=True)

@celery_app1.task(name='tasks.trim_top_group_rankings')
def trim_top_group_rankings():
	expire_top_groups()

@celery_app1.task(name='tasks.trim_whose_online')
def trim_whose_online():
	expire_online_users()

#ensuring photo reports dont have photo_id related complaints
@celery_app1.task(name='tasks.sanitize_photo_report')
def sanitize_photo_report(photo_id):#return price paid (as a default)
	payables,case_closed = delete_photo_report(photo_id,True)
	if case_closed and payables:
		for user_id,payable_score in payables:
			UserProfile.objects.filter(user_id=user_id).update(score=F('score')+payable_score)

#paying back points spent by photo reporters
@celery_app1.task(name='tasks.process_reporter_payables')
def process_reporter_payables(payables):
	for user_id,payable_score in payables:
		UserProfile.objects.filter(user_id=user_id).update(score=F('score')+payable_score)

#auto-populating photo thumbs in search results (triggered whenever a user profile is visited)
@celery_app1.task(name='tasks.populate_search_thumbs')
def populate_search_thumbs(username,ids_with_urls):
	bulk_add_search_photos(username,ids_with_urls)

#used to calculate group ranking
@celery_app1.task(name='tasks.public_group_vote_tasks')
def public_group_vote_tasks(group_id,priority):
	public_group_vote_incr(group_id,priority)

@celery_app1.task(name='tasks.public_group_attendance_tasks')
def public_group_attendance_tasks(group_id,user_id):
	public_group_attendance(group_id,user_id)

#bulk update others' notifications in groups
@celery_app1.task(name='tasks.group_notification_tasks')
def group_notification_tasks(group_id,sender_id,group_owner_id,topic,reply_time,poster_url,poster_username,reply_text,priv,\
	slug,image_url,priority,from_unseen):
	if from_unseen:
		update_object(object_id=group_id,object_type='3',lt_res_time=reply_time,lt_res_avurl=poster_url,lt_res_text=reply_text,\
			lt_res_sub_name=poster_username,reply_photourl=image_url, object_desc=topic)
	else:
		created = create_object(object_id=group_id,object_type='3',object_owner_id=group_owner_id,object_desc=topic,\
			lt_res_time=reply_time,lt_res_avurl=poster_url,lt_res_sub_name=poster_username,lt_res_text=reply_text,\
			group_privacy=priv,slug=slug)
		if not created:
			update_object(object_id=group_id,object_type='3',lt_res_time=reply_time,lt_res_avurl=poster_url,lt_res_text=reply_text,\
				lt_res_sub_name=poster_username,reply_photourl=image_url, object_desc=topic)
	all_group_member_ids = list(User.objects.filter(username__in=get_group_members(group_id)).values_list('id',flat=True))
	all_group_member_ids.remove(sender_id)
	if all_group_member_ids:
		bulk_update_notifications(viewer_id_list=all_group_member_ids,object_id=group_id,object_type='3',seen=False,
			updated_at=reply_time,single_notif=True,unseen_activity=True,priority=priority)
	updated=update_notification(viewer_id=sender_id,object_id=group_id,object_type='3',seen=True,updated_at=reply_time,\
		unseen_activity=True,single_notif=False,priority=priority,bump_ua=True)
	if not updated:
		create_notification(viewer_id=sender_id,object_id=group_id,object_type='3',seen=True,updated_at=reply_time,\
			unseen_activity=True)
	set_prev_group_replies(sender_id,reply_text)
	# set_prev_retort(sender_id,reply_text)

@celery_app1.task(name='tasks.rank_all_photos')
def rank_all_photos():
	previous_best_photo_id = get_previous_best_photo()
	# print "previous best_photo: %s" % previous_best_photo_id
	current_best_photo_id = get_best_photo()
	# print "current best_photo: %s" % current_best_photo_id
	if current_best_photo_id is not None:
		if previous_best_photo_id is not None:
			if previous_best_photo_id == current_best_photo_id:
				pass
			else:
				# print "uploading %s to Facebook..." % current_best_photo_id
				set_best_photo(current_best_photo_id)
				photo = Photo.objects.get(id=current_best_photo_id)
				photo_poster(photo.image_file, photo.caption, current_best_photo_id)
		else:
			set_best_photo(current_best_photo_id)
			photo = Photo.objects.get(id=current_best_photo_id)
			photo_poster(photo.image_file, photo.caption, current_best_photo_id)
	else:
		pass

@celery_app1.task(name='tasks.rank_all_photos1')
def rank_all_photos1():
	enqueued_match = get_current_cricket_match()
	if 'team1' in enqueued_match:# and get_cricket_ttl() < 1:
		#refresh the result
		teams_with_results = cricket_scr()
		match_to_follow = 0
		for match in teams_with_results:
			if match[0][0] == enqueued_match['team1']:
				match_to_follow = match
		if match_to_follow:
			team1 = match_to_follow[0][0]
			team2 = match_to_follow[1][0]
			try:
				score1 = match_to_follow[0][1]
			except:
				score1 = None #this side is yet to score
			try:
				score2 = match_to_follow[1][1]
			except:
				score2 = None #this side is yet to score
			status = match_to_follow[2]
			if not status:
				if score2:
					status = str(team1)+" "+str(score1)+" vs "+str(team2)+" "+str(score2)
				else:
					status = str(team1)+" "+str(score1)+" vs "+str(team2)
			# decide whether to go on, or delete match
			prev_status = get_prev_status().lower()
			if "won by" in prev_status or "drawn" in prev_status or "tied" in prev_status:
				#match ended
				del_delay_cricket_match(status,enqueued_match['id']) #key will expire in 20 mins
			elif "abandoned" in prev_status or "begin" in prev_status:
				#match not begun, or abandoned. Dequeue immediately
				del_cricket_match(enqueued_match['id'])
			else:
				update_cricket_match(team_to_follow=team1, team1=team1, score1=score1, team2=team2, \
					score2=score2, status=status)
		else:
			#match not found, dequeue it
			del_cricket_match(enqueued_match['id'])

@celery_app1.task(name='tasks.rank_photos')
def rank_photos():
	photos = retrieve_photo_posts(all_photos())
	photo_id_and_scr = []
	for photo in photos:
		try:
			if int(photo['vo']) > -2:
				rank = set_rank(int(photo['vi']),float(photo['t']))
				photo_id_and_scr.append(photo['i'])
				photo_id_and_scr.append(rank)
		except:
			pass
	add_photos_to_best(photo_id_and_scr)

@celery_app1.task(name='tasks.whoseonline')
def whoseonline():
	user_ids = get_recent_online()
	cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 67,
		})
	cache_mem.set('online', user_ids)

@celery_app1.task(name='tasks.fans')
def fans():
	user_ids = get_top_100()
	user_ids_and_fan_counts = get_fan_counts_in_bulk(user_ids)
	user_ids_and_user_objects = User.objects.select_related('userprofile','totalfanandphotos').in_bulk(user_ids)
	top_list = []
	for user_id in user_ids:
		top_list.append((user_ids_and_user_objects[int(user_id)],user_ids_and_user_objects[int(user_id)].totalfanandphotos.total_photos,\
			user_ids_and_user_objects[int(user_id)].userprofile,user_ids_and_fan_counts[user_id]))
	cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 1260,
		})
	cache_mem.set('fans', top_list)

@celery_app1.task(name='tasks.salat_info')
def salat_info():
	salat_timings = {}
	now = datetime.utcnow()+timedelta(hours=5)
	current_minute = now.hour * 60 + now.minute
	previous_namaz, next_namaz, namaz, next_namaz_start_time, current_namaz_start_time, current_namaz_end_time = namaz_timings[current_minute]
	salat_timings['previous_namaz'] = previous_namaz
	salat_timings['next_namaz'] = next_namaz
	salat_timings['namaz'] = namaz
	salat_timings['next_namaz_start_time'] = next_namaz_start_time
	salat_timings['current_namaz_start_time'] = current_namaz_start_time
	salat_timings['current_namaz_end_time'] = current_namaz_end_time
	cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 70,
		})
	cache_mem.set('salat_timings', salat_timings)

@celery_app1.task(name='tasks.salat_streaks')
def salat_streaks():
	now = datetime.utcnow()+timedelta(hours=5)
	current_minute = now.hour * 60 + now.minute
	twelve_hrs_ago = now - timedelta(hours=12)
	previous_namaz, next_namaz, namaz, next_namaz_start_time, current_namaz_start_time, current_namaz_end_time = namaz_timings[current_minute]
	if namaz == 'Fajr':
		salat = '1'
		object_list = LatestSalat.objects.filter(Q(latest_salat='1')|Q(latest_salat='5')).exclude(when__lte=twelve_hrs_ago).order_by('-salatee__userprofile__streak')[:500]
	elif namaz == 'Zuhr':
		salat = '2'
		object_list = LatestSalat.objects.filter(Q(latest_salat='2')|Q(latest_salat='1')).exclude(when__lte=twelve_hrs_ago).order_by('-salatee__userprofile__streak')[:500]
	elif namaz == 'Asr':
		salat = '3'
		object_list = LatestSalat.objects.filter(Q(latest_salat='3')|Q(latest_salat='2')).exclude(when__lte=twelve_hrs_ago).order_by('-salatee__userprofile__streak')[:500]
	elif namaz == 'Maghrib':
		salat = '4'
		object_list = LatestSalat.objects.filter(Q(latest_salat='4')|Q(latest_salat='3')).exclude(when__lte=twelve_hrs_ago).order_by('-salatee__userprofile__streak')[:500]
	elif namaz == 'Isha':
		salat = '5'
		object_list = LatestSalat.objects.filter(Q(latest_salat='5')|Q(latest_salat='4')).exclude(when__lte=twelve_hrs_ago).order_by('-salatee__userprofile__streak')[:500]
	else:
		salat = '1'
		object_list = LatestSalat.objects.filter(Q(latest_salat='1')|Q(latest_salat='5')).exclude(when__lte=twelve_hrs_ago).order_by('-salatee__userprofile__streak')[:500]
	cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
		'LOCATION': MEMLOC, 'TIMEOUT': 120,
	})
	status = cache_mem.set('salat_streaks', object_list)  # expiring in 120 seconds

@celery_app1.task(name='tasks.queue_for_deletion')
def queue_for_deletion(link_id_list):
	llen = add_to_deletion_queue(link_id_list)
	if llen > 200:
		delete_queue()

@celery_app1.task(name='tasks.photo_upload_tasks')
def photo_upload_tasks(banned, user_id, photo_id, timestring, device):
	photo = Photo.objects.get(id=photo_id)
	user = User.objects.get(id=user_id)
	timeobj = datetime.strptime(timestring, "%Y-%m-%dT%H:%M:%S.%f")
	updated = TotalFanAndPhotos.objects.filter(owner_id=user_id).update(last_updated=datetime.utcnow()+timedelta(hours=5), total_photos=F('total_photos')+1)
	if not updated:
		TotalFanAndPhotos.objects.create(owner_id=user_id, total_fans=0, total_photos=1, last_updated=datetime.utcnow()+timedelta(hours=5))
	stream = PhotoStream.objects.create(cover_id = photo_id, show_time = timeobj)
	photo.which_stream.add(stream) # CAN REMOVE? m2m field, thus 'append' a stream to the "which_stream" attribute
	UserProfile.objects.filter(user_id=user_id).update(score=F('score')-3)
	hotuser = HotUser.objects.filter(which_user_id=user_id).latest('id')
	add_search_photo(photo.image_file.url,photo_id,user.username)
	if hotuser.allowed and hotuser.hot_score > PHOTO_HOT_SCORE_REQ:
		link = Link.objects.create(description=photo.caption, submitter_id=user_id, device=device, cagtegory='6', which_photostream_id=stream.id)#
		photo_link_mapping(photo_id, link.id)
		try:
			av_url = user.userprofile.avatar.url
		except:
			av_url = None
		add_home_link(link_pk=link.id, categ='6', nick=user.username, av_url=av_url, desc=photo.caption, awld='1', hot_sc=hotuser.hot_score, \
			img_url=photo.image_file.url, v_sc=photo.vote_score, ph_pk=photo_id, ph_cc=photo.comment_count, scr=user.userprofile.score, \
			cc=0, writer_pk=user_id, device=device)
		if banned == '1':
			add_unfiltered_post(link.id)
		else:
			add_filtered_post(link.id)
			add_unfiltered_post(link.id)

@celery_app1.task(name='tasks.unseen_comment_tasks')
def unseen_comment_tasks(user_id, photo_id, epochtime, photocomment_id, count, text, it_exists, commenter, commenter_av, is_citizen):
	user = User.objects.get(id=user_id)
	photo = Photo.objects.select_related('owner__userprofile').get(id=photo_id)
	photo_owner_id = photo.owner_id
	try:
		owner_url = photo.owner.userprofile.avatar.url
	except:
		owner_url = None
	update_object(object_id=photo_id, object_type='0', lt_res_time=epochtime,lt_res_avurl=commenter_av,lt_res_sub_name=commenter,\
		lt_res_text=text,res_count=(count+1),vote_score=photo.vote_score)
	if photo_owner_id == user_id:
		is_seen = True
		unseen_activity = True
		single_notif = None
		same_writer = True
	else:
		is_seen = False
		unseen_activity = True
		single_notif = True
		same_writer = False
	create_notification(viewer_id=photo_owner_id, object_id=photo_id, object_type='0', seen=is_seen,\
		updated_at=epochtime, unseen_activity=unseen_activity, single_notif=single_notif, priority='photo_tabsra')
	all_commenter_ids = list(set(PhotoComment.objects.filter(which_photo_id=photo_id).order_by('-id').\
		values_list('submitted_by', flat=True)[:25]))
	if photo_owner_id not in all_commenter_ids:
		all_commenter_ids.append(photo_owner_id)
	try:
		all_commenter_ids.remove(user_id)
	except:
		pass
	if all_commenter_ids:
		bulk_update_notifications(viewer_id_list=all_commenter_ids, object_id=photo_id, object_type='0',\
			seen=False, updated_at=epochtime, single_notif=True, unseen_activity=True,priority='photo_tabsra') #only update if it existed
	updated = update_notification(viewer_id=user_id, object_id=photo_id, object_type='0', seen=True, updated_at=epochtime, \
		single_notif=False, unseen_activity=True,priority='photo_tabsra', bump_ua=True)
	if not updated:
		create_notification(viewer_id=user_id, object_id=photo_id, object_type='0', seen=True, updated_at=epochtime, \
			unseen_activity=True)
	photo.second_latest_comment = photo.latest_comment
	photo.latest_comment_id = photocomment_id
	photo.comment_count = count+1
	set_prev_replies(user_id,text)
	if is_fan(photo_owner_id,user_id):
		add_to_photo_owner_activity(photo_owner_id, user_id)
	if user_id != photo_owner_id and not it_exists:
		user.userprofile.score = user.userprofile.score + 2 #giving score to the commenter
		if is_citizen:
			photo.owner.userprofile.media_score = photo.owner.userprofile.media_score + 2 #giving media score to the photo poster
			photo.owner.userprofile.score = photo.owner.userprofile.score + 2 # giving score to the photo poster
			photo.visible_score = photo.visible_score + 2
			photo.owner.userprofile.save()
	photo.save()
	user.userprofile.save()

@celery_app1.task(name='tasks.photo_tasks')
def photo_tasks(user_id, photo_id, epochtime, photocomment_id, count, text, it_exists, commenter, commenter_av, is_citizen):
	user = User.objects.get(id=user_id)
	photo = Photo.objects.select_related('owner__userprofile').get(id=photo_id)
	photo_owner_id = photo.owner_id
	try:
		owner_url = photo.owner.userprofile.avatar.url
	except:
		owner_url = None
	created = create_object(object_id=photo_id, object_type='0', object_owner_avurl=owner_url,object_owner_id=photo_id,\
		object_owner_name=photo.owner.username,object_desc=photo.caption,lt_res_time=epochtime,lt_res_avurl=commenter_av,\
		lt_res_sub_name=commenter,lt_res_text=text,res_count=(count+1),vote_score=photo.vote_score,\
		photourl=photo.image_file.url)
	if not created:
		update_object(object_id=photo_id, object_type='0', lt_res_time=epochtime,lt_res_avurl=commenter_av,\
			lt_res_sub_name=commenter,lt_res_text=text,res_count=(count+1),vote_score=photo.vote_score)
	if photo_owner_id == user_id:
		is_seen = True
		unseen_activity = True
		single_notif = None
		same_writer = True
	else:
		is_seen = False
		unseen_activity = True
		single_notif = True
		same_writer = False
	created_for_parent = create_notification(viewer_id=photo_owner_id, object_id=photo_id, object_type='0', seen=is_seen,\
		updated_at=epochtime, unseen_activity=unseen_activity, single_notif=single_notif, priority='photo_tabsra')
	all_commenter_ids = list(set(PhotoComment.objects.filter(which_photo_id=photo_id).order_by('-id').\
		values_list('submitted_by', flat=True)[:25]))
	if photo_owner_id not in all_commenter_ids:
		all_commenter_ids.append(photo_owner_id)
	try:
		all_commenter_ids.remove(user_id)
	except:
		pass
	if created_for_parent and not same_writer:
		try:
			all_commenter_ids.remove(photo_owner_id)
		except:
			pass
	if all_commenter_ids:
		bulk_update_notifications(viewer_id_list=all_commenter_ids, object_id=photo_id, object_type='0',\
			seen=False, updated_at=epochtime, single_notif=True, unseen_activity=True,priority='photo_tabsra')
	if not created_for_parent or not same_writer:
		updated = update_notification(viewer_id=user_id, object_id=photo_id, object_type='0', seen=True, updated_at=epochtime, \
			single_notif=False, unseen_activity=True,priority='photo_tabsra', bump_ua=True)
		if not updated:
			create_notification(viewer_id=user_id, object_id=photo_id, object_type='0', seen=True, updated_at=epochtime, \
				unseen_activity=True)
	photo.second_latest_comment = photo.latest_comment
	photo.latest_comment_id = photocomment_id
	photo.comment_count = count+1
	set_prev_replies(user_id,text)
	if is_fan(photo_owner_id,user_id):
		add_to_photo_owner_activity(photo_owner_id, user_id)
	if user_id != photo_owner_id and not it_exists:
		user.userprofile.score = user.userprofile.score + 2 #giving score to the commenter
		if is_citizen:
			photo.owner.userprofile.media_score = photo.owner.userprofile.media_score + 2 #giving media score to the photo poster
			photo.owner.userprofile.score = photo.owner.userprofile.score + 2 # giving score to the photo poster
			photo.visible_score = photo.visible_score + 2
			photo.owner.userprofile.save()
	photo.save()
	user.userprofile.save()

@celery_app1.task(name='tasks.video_vote_tasks')
def video_vote_tasks(video_id, user_id, vote_score_increase, visible_score_increase, media_score_increase, score_increase):
	Video.objects.filter(id=video_id).update(vote_score=F('vote_score')+vote_score_increase, visible_score=F('visible_score')+visible_score_increase)
	UserProfile.objects.filter(user_id=user_id).update(media_score=F('media_score')+media_score_increase, score=F('score')+score_increase)

@celery_app1.task(name='tasks.photo_vote_tasks')
def photo_vote_tasks(photo_id, user_id, vote_score_increase, visible_score_increase, media_score_increase, score_increase, voter_id):
	Photo.objects.filter(id=photo_id).update(vote_score=F('vote_score')+vote_score_increase, visible_score=F('visible_score')+visible_score_increase)
	v_scr = Photo.objects.get(id=photo_id).vote_score
	update_object(object_id=photo_id,object_type='0',vote_score=v_scr, just_vote=True)
	UserProfile.objects.filter(user_id=user_id).update(media_score=F('media_score')+media_score_increase, score=F('score')+score_increase)
	if is_fan(user_id,voter_id):
		add_to_photo_owner_activity(user_id, voter_id)

@celery_app1.task(name='tasks.vote_tasks')
def vote_tasks(own_id, target_user_id,target_link_id,vote_value):
	target_userprofile = UserProfile.objects.get(user_id=target_user_id)
	target_link = Link.objects.get(id=target_link_id)
	#simply hellban the user in case their score is too low, and that's all
	if target_userprofile.score < -25:
		if not HellBanList.objects.filter(condemned_id=target_user_id).exists(): #only insert user in hell-ban list if she isn't there already
			HellBanList.objects.create(condemned_id=target_user_id) #adding user to hell-ban list
			target_userprofile.score = random.randint(10,71)
			target_userprofile.save()		
	elif vote_value == '1':
		# Vote.objects.create(voter_id=own_id, link_id=target_link_id, value=vote_value)
		target_userprofile.score = target_userprofile.score + UPVOTE
		target_link.net_votes = target_link.net_votes + 1
		target_userprofile.save()
		target_link.save()
	elif vote_value == '2':
		# Vote.objects.create(voter_id=own_id, link_id=target_link_id, value=vote_value)
		target_userprofile.score = target_userprofile.score + SUPER_UPVOTE
		target_link.net_votes = target_link.net_votes + 1
		target_userprofile.save()
		target_link.save()
	elif vote_value == '-1':
		# Vote.objects.create(voter_id=own_id, link_id=target_link_id, value=vote_value)
		target_userprofile.score = target_userprofile.score + DOWNVOTE
		target_link.net_votes = target_link.net_votes - 1
		target_userprofile.save()
		target_link.save()
	elif vote_value == '-2':
		# Vote.objects.create(voter_id=own_id, link_id=target_link_id, value=vote_value)
		target_userprofile.score = target_userprofile.score + SUPER_DOWNVOTE
		target_link.net_votes = target_link.net_votes - 1
		target_userprofile.save()
		target_link.save()
	else:
		pass

@celery_app1.task(name='tasks.registration_task')
def registration_task(ip,username,user_id):
	account_created(ip,username)
	# insert_nickname(username)
	# mp.track(user_id,'sign_ups')

@celery_app1.task(name='tasks.video_tasks')
def video_tasks(user_id, video_id, timestring, videocomment_id, count, text, it_exists):
	user = User.objects.get(id=user_id)
	video = Video.objects.get(id=video_id)
	video.second_latest_comment = video.latest_comment
	video.latest_comment_id = videocomment_id
	video.comment_count = count
	set_prev_retort(user_id,text)
	if user_id != video.owner_id and not it_exists:
		user.userprofile.score = user.userprofile.score + 2 #giving score to the commenter
		video.owner.userprofile.media_score = video.owner.userprofile.media_score + 2 #giving media score to the video poster
		video.owner.userprofile.score = video.owner.userprofile.score + 2 # giving score to the video poster
		video.visible_score = video.visible_score + 2
		video.owner.userprofile.save()
	video.save()
	user.userprofile.save()	

@celery_app1.task(name='tasks.publicreply_tasks')
def publicreply_tasks(user_id, reply_id, link_id, description):
	Link.objects.filter(id=link_id).update(reply_count=F('reply_count')+1, latest_reply=reply_id)  #updating comment count and latest_reply for DB link
	UserProfile.objects.filter(user_id=user_id).update(score=F('score')+PUBLICREPLY)
	set_prev_replies(user_id,description)

@celery_app1.task(name='tasks.publicreply_notification_tasks')
def publicreply_notification_tasks(link_id,sender_id,link_submitter_url,link_submitter_id,link_submitter_username,link_desc,\
	reply_time,reply_poster_url,reply_poster_username,reply_desc,is_welc,reply_count,priority,from_unseen):
	if from_unseen:
		update_object(object_id=link_id, object_type='2', lt_res_time=reply_time,lt_res_avurl=reply_poster_url,\
			lt_res_sub_name=reply_poster_username,lt_res_text=reply_desc,res_count=reply_count)
		all_reply_ids = list(set(Publicreply.objects.filter(answer_to=link_id).order_by('-id').\
			values_list('submitted_by', flat=True)[:25]))
		if link_submitter_id not in all_reply_ids:
			all_reply_ids.append(link_submitter_id)
		try:
			all_reply_ids.remove(sender_id)
		except:
			pass
		if all_reply_ids:
			bulk_update_notifications(viewer_id_list=all_reply_ids, object_id=link_id, object_type='2',seen=False, \
				updated_at=reply_time, single_notif=True, unseen_activity=True,priority=priority)
		updated = update_notification(viewer_id=sender_id, object_id=link_id, object_type='2', seen=True, \
			updated_at=reply_time, single_notif=False, unseen_activity=True,priority='home_jawab', bump_ua=True)
		if not updated:
			create_notification(viewer_id=sender_id, object_id=link_id, object_type='2', seen=True, \
				updated_at=reply_time, unseen_activity=True)
	else:
		created = create_object(object_id=link_id, object_type='2', object_owner_avurl=link_submitter_url,\
			object_owner_id=link_submitter_id,object_owner_name=link_submitter_username,object_desc=link_desc,lt_res_time=reply_time,\
			lt_res_avurl=reply_poster_url,lt_res_sub_name=reply_poster_username,lt_res_text=reply_desc,is_welc=is_welc,\
			res_count=reply_count)
		if not created:
			update_object(object_id=link_id, object_type='2', lt_res_time=reply_time,lt_res_avurl=reply_poster_url,\
				lt_res_sub_name=reply_poster_username,lt_res_text=reply_desc,res_count=reply_count)
		if link_submitter_id == sender_id:
			is_seen = True
			unseen_activity = True
			single_notif = None
			same_writer = True
		else:
			is_seen = False
			unseen_activity = True
			single_notif = True
			same_writer = False
		created_for_parent = create_notification(viewer_id=link_submitter_id, object_id=link_id, object_type='2', seen=is_seen,\
				updated_at=reply_time, unseen_activity=unseen_activity, single_notif=single_notif,priority=priority)
		all_reply_ids = list(set(Publicreply.objects.filter(answer_to=link_id).order_by('-id').values_list('submitted_by', flat=True)[:25]))
		if link_submitter_id not in all_reply_ids:
			all_reply_ids.append(link_submitter_id)
		try:
			all_reply_ids.remove(sender_id)
		except:
			pass
		if created_for_parent and not same_writer:
			try:
				#remove link_submitter_id from all_reply_ids so it doesn't get updated again in 'bulk update notifcations'
				all_reply_ids.remove(link_submitter_id)
			except:
				pass
		if all_reply_ids:
			bulk_update_notifications(viewer_id_list=all_reply_ids, object_id=link_id, object_type='2',seen=False, \
				updated_at=reply_time, single_notif=True, unseen_activity=True,priority=priority)
		#create or update notification for self, but not when it's the first-ever reply and that too, by parent obj owner, i.e. not(created_for_parent and same_writer) = (not created_for_parent or not same_writer) - logical operation
		if not created_for_parent or not same_writer:
			updated = update_notification(viewer_id=sender_id, object_id=link_id, object_type='2', seen=True, updated_at=reply_time, \
				single_notif=False, unseen_activity=True, priority=priority, bump_ua=True)
			if not updated:
				create_notification(viewer_id=sender_id, object_id=link_id, object_type='2', seen=True, updated_at=reply_time, \
					unseen_activity=True)

@celery_app1.task(name='tasks.report')
def report(reporter_id, target_id, report_origin=None, report_reason=None, which_link_id=None, which_publicreply_id=None, which_photo_id=None, which_photocomment_id=None, which_group_id=None, which_reply_id=None, nickname=None):
	if report_origin == '1':
		#origin:chupair
		Report.objects.create(reporter_id=reporter_id, target_id=target_id, report_reason='Chupair', report_origin=report_origin, which_link_id=which_link_id)
	elif report_origin == '2':
		#origin:publicreply
		Report.objects.create(reporter_id=reporter_id, target_id=target_id, report_reason='Publicreply', report_origin=report_origin, which_publicreply_id=which_publicreply_id)
	elif report_origin == '7':
		#origin:photocomment
		Report.objects.create(reporter_id=reporter_id, target_id=target_id, report_reason='PhotoComment', report_origin=report_origin, which_photocomment_id=which_photocomment_id, which_photo_id=which_photo_id)
	elif report_origin == '3':
		#origin:nickname
		userprofile = UserProfile.objects.get(user_id=reporter_id)
		target = User.objects.get(id=target_id)
		latest_user = User.objects.latest('id')
		userprofile.score = userprofile.score - 10
		userprofile.save()
		if int(latest_user.id) - int(target_id) < 50:
			Report.objects.create(reporter_id=reporter_id, target_id=target_id, report_reason=target.username, report_origin=report_origin)
		else:
			# i.e. do nothing if it's an old id
			pass
	elif report_origin == '4':
		#origin:profile
		if report_reason == '1':
			reason = 'gali di'
		elif report_reason == '2':
			reason = 'dhamki di'
		elif report_reason == '3':
			reason = 'fake profile'
		elif report_reason == '4':
			reason = 'gandi baat'
		elif report_reason == '5':
			reason = 'password manga'
		elif report_reason == '6':
			reason = 'firqa wariyat'
		elif report_reason == '7':
			reason = 'gandi photo'
		elif report_reason == '8':
			reason = 'fake admin'
		else:
			reason = report_reason
		Report.objects.create(reporter_id=reporter_id, target_id=target_id, report_origin=report_origin, report_reason=reason)

@celery_app1.task(name='tasks.video_upload_tasks')
def video_upload_tasks(video_name, video_id, user_id):
	lst = uploadvid(video_name)
	low_res_thumb = "//"+lst[0].partition('://')[2]
	small_thumb = "//"+lst[1].partition('://')[2]
	low_res_video = "//"+lst[2].partition('://')[2]
	high_res_video = "//"+lst[3].partition('://')[2]
	video = Video.objects.filter(id=video_id).update(low_res_thumb=low_res_thumb, small_thumb=small_thumb, low_res_video=low_res_video, high_res_video=high_res_video, processed=True)
	if video:
		add_video(video_id)
		save_recent_video(user_id, video_id)
		UserProfile.objects.filter(user_id=user_id).update(score=F('score')-5)
	else:
		pass

@celery_app1.task(name='tasks.fan_recount')
def fan_recount(owner_id,fan_increment,fan_decrement):
	if fan_decrement:
		TotalFanAndPhotos.objects.filter(owner_id=owner_id).update(total_fans=F('total_fans')-1,last_updated=datetime.utcnow()+timedelta(hours=5))
	elif fan_increment:
		updated = TotalFanAndPhotos.objects.filter(owner_id=owner_id).update(total_fans=F('total_fans')+1,last_updated=datetime.utcnow()+timedelta(hours=5)) #move to tasks
		if not updated:
			TotalFanAndPhotos.objects.create(owner_id=star_id, total_fans=1, total_photos=0, last_updated=datetime.utcnow()+timedelta(hours=5))
	else:
		pass

obj1 = locals()['salat_info']
# obj2 = locals()['rank_photos']
obj1.run()
# obj2.run()