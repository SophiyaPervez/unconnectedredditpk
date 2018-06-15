# coding=utf-8
import redis, time
from multiprocessing import Pool
from random import randint, random
from location import REDLOC1
from score import VOTE_TEXT
from home_post_rating_algos import recency_and_length_score
from html_injector import pinkstar_formatting, category_formatting, device_formatting, scr_formatting, \
username_formatting, av_url_formatting#, comment_count_formatting

'''
##########Redis Namespace##########

perceptual_hash_set
filteredposts:1000
unfilteredposts:1000
photos:1000
bestphotos:1000
videos:1000
set_name = "defenders" # set of all Damadam defenders

###########
ad_feedback_counter = "af:"+advertiser
hash_name = "cah:"+str(user_id) #cah is 'comment abuse hash', it contains latest integrity value
cant_photo_report = "cpr:"+str(reporter_id)
cricket = "cricket"
set_name = "ftux:"+str(user_id)
hash_name = "giu:"+str(group_id)+str(user_id)#giu is 'group invite for user' - stores the invite_id that was sent to the user (for later retrieval)
hash_name = "hafs:"+str(user_id)+str(reporter_id) #hafs is 'hash abuse feedback set', it contains strings about the person's wrong doings
registered_ip = "ip:"+str(ip)
sorted_set = "ipg:"+str(user_id) #ipg is 'invited private/public group' - this stores the group_id a user has already been invited to - limited to 500 invites
hash_name = "lah:"+str(user_id)
link_vote_cooldown = "lc:"+str(user_id)
hash_name = "lk:"+str(link_pk) #lk is 'link'
hash_name = "rlk:"+str(parent_id) #rlk is ranked 'set of links'
my_server.setex("lgr:"+str(group_id),reply_id,ONE_WEEK) #latest group_reply_id is stored here
hash_name = "lpvt:"+str(photo_id) #lpvt is 'last photo vote time'
hash_name = "lvt:"+str(video_id) #lvt is 'last vote time'
hash_name = "nah:"+str(target_id) #nah is 'nick abuse hash', it contains latest integrity value
set_name = "nas:"+str(target_id) #nas is 'nick abuse set', it contains IDs of people who reported this person
hash_name = "pah:"+str(user_id) #pah is 'publicreply abuse hash', it contains latest integrity value
hash_name = "pcbah:"+str(user_id) #pcbah is 'profile cyber bullying abuse hash', it contains latest integrity value
hash_name = "ph:"+str(photo_id)
hash_name = "poah:"+str(user_id) #poah is 'profile obscenity abuse hash', it contains latest integrity value
set_name = "pgm:"+str(group_id) #pgm is private/public_group_members
photo_report = "phr:"+str(photo_id) #photo report hash - contains all complaints, appended toegether
list_name = "phts:"+str(user_id)
hash_name = "plm:"+str(photo_pk) #plm is 'photo_link_mapping'
photo_payables = "pp:"+str(photo_id) #photo payables sorted set - contains all point amounts owed to all reporter ids
prev_times = "pt6:"+str(user_id) # set 6 previous times
photo_votes_allowed = "pva:"+str(user_id) #photo votes allowed to user_id
hash_name = "pvb:"+str(user_id) #pub is 'photo vote ban'
hash_name = "pub:"+str(user_id) #pub is 'photo upload ban'
sorted_set = "public_group_rankings"
unsorted_set = "pir:"+str(user_id) #pir is 'private/public invite reply' - stores every 'active' invite_id - deleted if reply seen or X is pressed
reported_photos = "reported_photos" #sorted set containing all reported photos
hash_name = "rut:"+str(user_id)#ru is 'recent upload time' - stores the last video upload time of user
short_message = "sm:"+str(user_id)
set_name = "unl:"+str(user_id)
set_name = "ug:"+str(user_id) #ug is user's groups
sorted_set = "v:"+str(link_pk) #set of all votes cast against a 'home link'.
votes_allowed = "va:"+str(user_id) #votes allowed to user_id
sorted_set = "vp:"+str(photo_id)
sorted_set = "vv:"+str(video_id) #vv is 'voted video'
list_name = "vids:"+str(user_id)
website_feedback = "wf:"+str(data["user_id"])
feedback_set = "website_feedback"
##########
'''
# POOL = redis.ConnectionPool(host='127.0.0.1', port=6379, db=0)
POOL = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=REDLOC1, db=0)

INTERVAL_SIZE = 4*60

GRP_TGR = 700

VOTE_LIMIT = 6

TWO_WEEKS = 2*7*24*60*60 
ONE_WEEK = 7*24*60*60
FOUR_DAYS = 4*24*60*60
THREE_DAYS = 3*24*60*60
ONE_DAY = 24*60*60
TWELVE_HOURS = 12*60*60
SIX_HOURS = 6*60*60
THREE_HOURS = 3*60*60
ONE_HOUR = 60*60
TWENTY_MINS = 20*60
TEN_MINS = 10*60
FOUR_MINS = 4*60
THREE_MINS = 3*60
FORTY_FIVE_SECS = 45

VOTE_SPREE_ALWD = 6
PHOTO_VOTE_SPREE_ALWD = 6



def create_inactives_copy():
	"""Creates a copy of the sorted set using redis' zunionstore.

	"""
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.zunionstore("copy_of_inactive_users",["inactive_users"])

def delete_inactives_copy(delete_orig=False):
	"""Deletes the copy of the sorted set using redis' zunionstore.

	Can optionally delete the original version as well.
	"""
	my_server = redis.Redis(connection_pool=POOL)
	if delete_orig:
		pipeline1 = my_server.pipeline()
		pipeline1.delete("copy_of_inactive_users")
		pipeline1.delete("inactive_users")
		pipeline1.execute()
	else:
		my_server.delete("copy_of_inactive_users")



def get_inactive_count(server=None, key_name=None):
	if not server:
		server = redis.Redis(connection_pool=POOL)
	if not key_name:
		return server.zcard("inactive_users")
	else:
		return server.zcard(key_name)


def get_inactives(get_50K=False, get_10K=False, get_5K=False, key=None):
	my_server = redis.Redis(connection_pool=POOL)
	if not key:
		key = "inactive_users"
	if get_50K:
		remaining = get_inactive_count(server=my_server,key_name = None if key == 'inactive_users' else key)
		if remaining < 50000:
			data = my_server.zrange(key,0,-1,withscores=True)
			my_server.delete(key)
			return data, True
		else:
			data = my_server.zrange(key,0,49999,withscores=True)
			my_server.zremrangebyrank(key,0,49999)
			return data, False
	elif get_10K:
		remaining = get_inactive_count(server=my_server,key_name = None if key == 'inactive_users' else key)
		if remaining < 10000:
			data = my_server.zrange(key,0,-1,withscores=True)
			my_server.delete(key)
			return data, True
		else:
			data = my_server.zrange(key,0,9999,withscores=True)
			my_server.zremrangebyrank(key,0,9999)
			return data, False
	elif get_5K:
		remaining = get_inactive_count(server=my_server,key_name = None if key == 'inactive_users' else key)
		if remaining < 5000:
			data = my_server.zrange(key,0,-1,withscores=True)
			my_server.delete(key)
			return data, True
		else:
			data = my_server.zrange(key,0,4999,withscores=True)
			my_server.zremrangebyrank(key,0,4999)
			return data, False
	else:
		return my_server.zrange(key,0,-1,withscores=True)

def set_inactives(inactive_list):
	my_server = redis.Redis(connection_pool=POOL)
	if inactive_list:
		my_server.zadd("inactive_users", *inactive_list)

#####################Photo Reports######################

def delete_photo_report(photo_id, return_points=False):
	my_server = redis.Redis(connection_pool=POOL)
	photo_payables = "pp:"+str(photo_id)
	photo_report = "phr:"+str(photo_id)
	reported_photos = "reported_photos"
	if my_server.exists(photo_report):
		if return_points:
			payables = my_server.zrange(photo_payables,0,-1,withscores=True)
		else:
			payables = []
		pipeline1 = my_server.pipeline()
		pipeline1.delete(photo_payables) #deleting the payables sorted set
		pipeline1.delete(photo_report) #deleting the photo report hash
		pipeline1.zrem(reported_photos,photo_report) #removing the photo report from the sorted set of all reports
		pipeline1.execute()
		return payables, True #'True' signifies case closed by user
	else:
		return [], None #'None' signifies case was already closed by someone else!

def get_complaint_details(complaint_list):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	complaints_with_details = []
	for complaint in complaint_list:
		pipeline1.hgetall(complaint)
	result1 = pipeline1.execute()
	for complaint in result1:
		complaints_with_details.append(complaint)
	return complaints_with_details

def get_num_complaints():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.zcard("reported_photos")

def get_photo_complaints():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.zrevrange("reported_photos",0,-1)

def set_photo_complaint(rep_type,text,caption,purl,photo_id,price_paid,reporter_id):
	my_server = redis.Redis(connection_pool=POOL)
	#is reporter_id allowed to report?
	cant_photo_report = "cpr:"+str(reporter_id)
	if my_server.exists(cant_photo_report):
		return my_server.ttl(cant_photo_report)
	else:
		#photo report hash - contains all complaints, appended together
		photo_report = "phr:"+str(photo_id)
		report_text = '<b class="clb">'+rep_type+'</b>:<br>'+'<span class="bw cgy">'+text+'</span><br>'
		if my_server.exists(photo_report):
			existing_reports = my_server.hget(photo_report,'tx')
			my_server.hset(photo_report,'tx',report_text+existing_reports)
			nc = my_server.hincrby(photo_report,'nc',amount=1)
		else:
			nc = 1
			mapping = {'tx':report_text,'url':purl,'pid':photo_id,'nc':nc,'c':caption}
			my_server.hmset(photo_report,mapping)
		#photo payables sorted set - contains all point amounts owed to all reporter ids - triggered when photo's fate is decided
		photo_payables = "pp:"+str(photo_id)
		prev_payable = my_server.zscore(photo_payables,reporter_id)
		new_amnt_owed = (price_paid if prev_payable is None else prev_payable+int(price_paid))
		my_server.zadd(photo_payables,reporter_id,new_amnt_owed)
		#sorted set containing all reported photos
		reported_photos = "reported_photos"
		pipeline1 = my_server.pipeline()
		pipeline1.zadd(reported_photos,photo_report,nc)
		pipeline1.setex(cant_photo_report,1,TEN_MINS)
		pipeline1.execute()
		return None

#####################Cricket Widget#####################

def current_match_comments(match_id):
	my_server = redis.Redis(connection_pool=POOL)
	match_comments = "cricmatch:"+str(match_id)
	return my_server.lrange(match_comments, 0, -1)

def current_match_unfiltered_comments(match_id):
	my_server = redis.Redis(connection_pool=POOL)
	match_comments = "unfilcricmatch:"+str(match_id)
	return my_server.lrange(match_comments, 0, -1)

def get_cricket_ttl():
	my_server = redis.Redis(connection_pool=POOL)
	cricket = "cricket"
	return my_server.ttl(cricket)

def get_prev_status():
	my_server = redis.Redis(connection_pool=POOL)
	cricket = "cricket"
	return my_server.hget(cricket,'status')

def incr_unfiltered_cric_comm(link_id, match_id):
	my_server = redis.Redis(connection_pool=POOL)
	match_comments = "unfilcricmatch:"+str(match_id)
	my_server.lpush(match_comments, link_id)
	my_server.ltrim(match_comments, 0, 199)

def incr_cric_comm(link_id, match_id):
	my_server = redis.Redis(connection_pool=POOL)
	cricket = "cricket"
	my_server.hincrby(cricket,'cc',amount=1)
	match_comments = "cricmatch:"+str(match_id)
	my_server.lpush(match_comments, link_id)
	my_server.ltrim(match_comments, 0, 199)

def get_current_cricket_match():
	my_server = redis.Redis(connection_pool=POOL)
	cricket = "cricket"
	return my_server.hgetall(cricket)

def create_cricket_match(team_to_follow, team1, score1, team2, score2, status):
	my_server = redis.Redis(connection_pool=POOL)
	cricket = "cricket"
	match_id = my_server.incr("cric")
	mapping = {'team_to_follow':team_to_follow,'team1':team1,'score1':score1,\
	'team2':team2,'score2':score2,'status':status,'ended':'0','cc':0,'id':match_id}
	my_server.hmset(cricket, mapping)

def update_cricket_match(team_to_follow, team1, score1, team2, score2, status):
	my_server = redis.Redis(connection_pool=POOL)
	cricket = "cricket"
	match_id = my_server.get("cric")
	mapping = {'team_to_follow':team_to_follow,'team1':team1,'score1':score1,\
	'team2':team2,'score2':score2,'status':status,'ended':'0','id':match_id}
	my_server.hmset(cricket, mapping)

def del_cricket_match(match_id):
	my_server = redis.Redis(connection_pool=POOL)
	cricket = "cricket"
	match_comments = "cricmatch:"+str(match_id)
	my_server.delete(cricket)
	my_server.expire(match_comments,ONE_WEEK)

def del_delay_cricket_match(final_status,match_id):
	my_server = redis.Redis(connection_pool=POOL)
	cricket = "cricket"
	match_comments = "cricmatch:"+str(match_id)
	if my_server.exists(cricket) and my_server.ttl(cricket) < 0:
		pipeline1 = my_server.pipeline()
		pipeline1.hset(cricket,'ended','1')
		pipeline1.hset(cricket,'status',final_status)	
		pipeline1.expire(cricket,TWENTY_MINS)
		pipeline1.expire(match_comments,ONE_WEEK)
		pipeline1.execute()

#####################Authorization#####################

def account_creation_disallowed(ip):
	my_server = redis.Redis(connection_pool=POOL)
	if my_server.exists("ip:"+str(ip)):
		return True
	else:
		return False

def account_created(ip,username):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.setex("ip:"+str(ip),username,FOUR_MINS)

# def insert_nickname(username):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	my_server.zadd("nicks",username, 0.0)	

#######################Defenders#######################

def in_defenders(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "defenders" # set of all Damadam defenders
	if my_server.sismember(set_name, user_id):
		return True
	else:
		return False

def ban_time_remaining(ban_time, ban_type):
	current_time = time.time()
	time_difference = current_time - float(ban_time)
	if ban_type == '0.1':
		if time_difference < THREE_HOURS:
			time_remaining = (float(ban_time)+THREE_HOURS)-current_time
			return True, time_remaining
		else:
			return False, None
	elif ban_type == '1':
		if time_difference < ONE_DAY:
			time_remaining = (float(ban_time)+ONE_DAY)-current_time
			return True, time_remaining
		else:
			return False, None
	elif ban_type == '3':
		if time_difference < THREE_DAYS:
			time_remaining = (float(ban_time)+THREE_DAYS)-current_time
			return True, time_remaining
		else:
			return False, None
	elif ban_type == '7':
		if time_difference < ONE_WEEK:
			time_remaining = (float(ban_time)+ONE_WEEK)-current_time
			return True, time_remaining
		else:
			return False, None

def check_photo_vote_ban(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "pvb:"+str(user_id) #pvb is 'photo vote ban'
	hash_contents = my_server.hgetall(hash_name)
	if hash_contents:
		ban_type = hash_contents["b"]
		if ban_type == '-1':
			#this person is banned forever
			return True, '-1'
		elif ban_type == '0.1':
			ban_time = hash_contents["t"]
			return ban_time_remaining(ban_time, ban_type)			
		elif ban_type == '1':
			ban_time = hash_contents["t"]
			return ban_time_remaining(ban_time, ban_type)
		elif ban_type == '3':
			ban_time = hash_contents["t"]
			return ban_time_remaining(ban_time, ban_type)		
		elif ban_type == '7':	
			ban_time = hash_contents["t"]
			return ban_time_remaining(ban_time, ban_type)
		else:
			return False, None
	else:
		return False, None

def check_photo_upload_ban(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "pub:"+str(user_id) #pub is 'photo upload ban'
	hash_contents = my_server.hgetall(hash_name)
	if hash_contents:
		ban_type = hash_contents["b"]
		if ban_type == '-1':
			return True, '-1'
		elif ban_type == '1':
			ban_time = hash_contents["t"]
			return ban_time_remaining(ban_time, ban_type)
		elif ban_type == '7':
			ban_time = hash_contents["t"]
			return ban_time_remaining(ban_time, ban_type)
		else:
			return False, None
	else:
		return False, None

def remove_from_photo_upload_ban(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "pub:"+str(user_id) #pub is 'photo upload ban'
	my_server.delete(hash_name)

def remove_from_photo_vote_ban(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "pvb:"+str(user_id) #pub is 'photo vote ban'
	my_server.delete(hash_name)

def add_to_photo_upload_ban(user_id, ban_type):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "pub:"+str(user_id) #pub is 'photo upload ban'
	current_time = time.time()
	mapping = {'t':current_time, 'b':ban_type}
	my_server.hmset(hash_name, mapping)

def add_user_to_photo_vote_ban(user_id, ban_type): #for single user
	my_server = redis.Redis(connection_pool=POOL)
	current_time = time.time()
	hash_name = "pvb:"+str(user_id) #pub is 'photo vote ban'
	last_ban_type = my_server.hget(hash_name, 'b') # don't over-ride if this person was photo banned for a longer time previously
	if last_ban_type == '-1':
		#this person is already banned forever, so let the ban be
		pass
	else:
		mapping = {'t':current_time, 'b':ban_type}
		my_server.hmset(hash_name, mapping)

def add_to_photo_vote_ban(user_ids, ban_type): #for multiple users
	my_server = redis.Redis(connection_pool=POOL)
	current_time = time.time()
	for user_id in user_ids:
		hash_name = "pvb:"+str(user_id) #pub is 'photo vote ban'
		last_ban_type = my_server.hget(hash_name, 'b') # don't over-ride if this person was photo banned for a longer time previously
		if last_ban_type == '-1':
			#this person is already banned forever, so let the ban be
			pass
		else:
			mapping = {'t':current_time, 'b':ban_type}
			my_server.hmset(hash_name, mapping)

###################Feature Unlocked####################

#username search feature: '1'

def is_uname_search_unlocked(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "unl:"+str(user_id)
	if my_server.sismember(set_name,'1'):
		return True
	else:
		return False

def unlock_uname_search(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "unl:"+str(user_id)
	my_server.sadd(set_name, '1')

#######################Tutorials#######################

#mehfil refresh button: '1'
#photo defender:        '2'    (deprecated)
#inbox (matka):         '3'
#fan:                   '4'
#password change:       '5'
#photo uploader:        '6'
#psl supporter:         '7'
#home replier:          '8'
#photo defender:        '9'
#photo culler:          '10'
#photo judger:          '11'
#photo curator:         '12'
#website feedbacker:    '13'
#exchange visitor:      '14'
#classified_contacter:  '15'
#log_outter:            '16'
#photo_ads_visitor:     '17'
#first_time_banner:     '18'

def first_time_banner(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'18'):
		return False
	else:
		return True	

def first_time_photo_ads_visitor(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'17'):
		return False
	else:
		return True	

def first_time_log_outter(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'16'):
		return False
	else:
		return True	

def first_time_exchange_visitor(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'14'):
		return False
	else:
		return True	

def first_time_classified_contacter(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'15'):
		return False
	else:
		return True	

def first_time_feedbacker(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'13'):
		return False
	else:
		return True	

def first_time_photo_curator(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'12'):
		return False
	else:
		return True	

def first_time_photo_judger(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'11'):
		return False
	else:
		return True	

def first_time_photo_culler(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'10'):
		return False
	else:
		return True	

def first_time_home_replier(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'8'):
		return False
	else:
		return True	

def first_time_psl_supporter(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'7'):
		return False
	else:
		return True

def first_time_photo_uploader(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'6'):
		return False
	else:
		return True

def first_time_password_changer(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'5'):
		return False
	else:
		return True

def first_time_fan(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name,'4'):
		return False
	else:
		return True

def first_time_inbox_visitor(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name, '3'):
		return False
	else:
		return True

#was it a first-time experience with defending photos?
def first_time_photo_defender(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	if my_server.sismember(set_name, '9'):
		return False
	else:
		return True

#was it a first-time interaction with the refresh button in mehfils?
def first_time_refresher(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id) #first time user experiences set
	if my_server.sismember(set_name, '1'):
		return False #user is not a first-timer
	else:
		return True #user is a first-timer

def add_photo_defender_tutorial(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '9')

def add_refresher(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '1')

def add_inbox(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '3')

def add_fan(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '4')

def add_password_change(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '5')

def add_photo_uploader(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '6')

def add_psl_supporter(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '7')

def add_home_replier(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '8')

def add_photo_culler(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '10')

def add_photo_judger(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '11')

def add_photo_curator(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '12')

def add_website_feedbacker(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '13')

def add_classified_contacter(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '15')

def add_exchange_visitor(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '14')

def add_log_outter(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '16')

def add_photo_ad_visitor(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '17')

def add_banner(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '18')


#####################Publicreplies#####################

#This failed in boosting performance - thus was deprecated

# def get_publicreplies(link_id):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	publicreply_writer_pairs = my_server.lrange("prw:"+str(link_id), 0, -1)
# 	return (p.split(":")[0] for p in publicreply_writer_pairs)

# def get_replywriters(link_id):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	publicreply_writer_pairs = my_server.lrange("prw:"+str(link_id), 0, -1)
# 	#return set(w.split(":")[1] for w in publicreply_writer_pairs)
# 	return {item.partition(":")[2] for item in publicreply_writer_pairs}

# def add_publicreply_to_link(publicreply_id, writer_id, link_id):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	my_server.lpush("prw:"+str(link_id), str(publicreply_id)+":"+str(writer_id)) #'pr' is 'public reply & writer'
# 	my_server.ltrim("prw:"+str(link_id), 0, 49) # save the most recent 50 publicreplies
# 	# use the following to delete out-dated publicreply redis lists
# 	hash_name = "lpr:"+str(link_id) #lpr is 'last public reply' time
# 	current_time = time.time()
# 	mapping = {'t':current_time}
# 	my_server.hmset(hash_name, mapping)

#####################Photo objects#####################

# helper function for add_photo_comment and update_comment_in_home_link
def truncate_payload(payload):
	# on average, truncate this after 10 messages have been aggregated
	if random() < 0.1:
		raw_text_set = filter(None,payload.split('#el#'))[-5:] #just keeping the latest 5 entries
		payload = '#el#'.join(raw_text_set)+"#el#" #reforming the payload
	return payload
	

def retrieve_photo_posts(photo_id_list):
	my_server = redis.Redis(connection_pool=POOL)
	list_of_dictionaries = []
	photo_ids = []
	non_photo_link_ids = []
	pipeline1 = my_server.pipeline()
	for photo_id in photo_id_list:
		hash_name="ph:"+str(photo_id)
		pipeline1.hgetall(hash_name)
	result1 = pipeline1.execute()
	count = 0
	for hash_obj in result1:
		if 'u' in hash_obj:#'u' is image_url
			list_of_dictionaries.append(hash_obj)
		count += 1
	return list_of_dictionaries 

def add_photo_entry(photo_id=None,owner_id=None,owner_av_url=None,image_url=None,\
	upload_time=None,invisible_score=None,caption=None,photo_owner_username=None,\
	device=None,from_fbs=None):
	hash_name = "ph:"+str(photo_id)
	mapping = {'i':photo_id,'oi':owner_id,'oa':owner_av_url,'u':image_url,'t':upload_time,\
	'in':invisible_score,'ca':caption,'o':photo_owner_username,'d':device,'vi':'0','vo':'0',\
	'fbs':'1' if from_fbs else '0'}
	my_server = redis.Redis(connection_pool=POOL)
	my_server.hmset(hash_name, mapping)
	my_server.expire(hash_name,ONE_DAY) #expire the key after 24 hours


def add_photo_comment(photo_id=None,photo_owner_id=None,latest_comm_text=None,latest_comm_writer_id=None,\
	latest_comm_av_url=None,latest_comm_writer_uname=None,comment_count=None, exists=None, citizen=None, \
	time=None):
	"""
	Adds comment to photo object (only if it exists)
	"""
	hash_name = "ph:"+str(photo_id)
	my_server = redis.Redis(connection_pool=POOL)
	if my_server.exists(hash_name):
		#################################Saving latest photo comment################################
		existing_payload = my_server.hget(hash_name,'comments')
		payload = str(latest_comm_av_url)+"#"+latest_comm_writer_uname+"#"+str(time)+"#"+str(latest_comm_writer_id)+"#"+str(photo_id)+"#"+\
		latest_comm_text+"#el#" #el# signifies an end-of-line character
		if existing_payload:
			existing_payload = truncate_payload(existing_payload)
			payload = existing_payload.decode('utf-8')+payload
		my_server.hset(hash_name,'comments',payload)
		my_server.hincrby(hash_name,'co',amount=1)
		if photo_owner_id != latest_comm_writer_id and not exists and citizen: #only give score if writer didn't upload photo, and hasn't written before, and is a citizen
			my_server.hincrby(hash_name,'vi',amount=2)



def get_raw_comments(photo_id):
	"""
	Returns comments associated to a photo
	"""
	return redis.Redis(connection_pool=POOL).hget("ph:"+str(photo_id),"comments")


def ban_photo(photo_id,ban):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "ph:"+str(photo_id)
	if my_server.exists(hash_name):
		if ban is True:
			my_server.hset(hash_name,'vo','-100')
		elif ban is False:
			mapping={'vo':'0','vi':'0'}
			my_server.hmset(hash_name,mapping)
		else:
			pass

def add_vote_to_photo(photo_id, username, value,is_pinkstar, is_citizen):
	sorted_set = "vp:"+str(photo_id) #vv is 'voted photo'
	hash_name = "ph:"+str(photo_id)
	my_server = redis.Redis(connection_pool=POOL)
	already_exists = my_server.zscore(sorted_set, username)
	if already_exists != 0 and already_exists != 1:
		#add the voter's username and vote_value (for display later)
		my_server.zadd(sorted_set, username, value)
		#add vote to photo_obj
		if my_server.exists(hash_name) and is_citizen:
			# vote score (for photos and top photos pages respectively)
			if value == 0:
				my_server.hincrby(hash_name,'vo',amount=-1)
				my_server.hincrby(hash_name,'vi',amount=-1)
			else:
				my_server.hincrby(hash_name,'vo',amount=1)
				my_server.hincrby(hash_name,'vi',amount=1)
		##################Updating link vote##################
		link_id = my_server.hget("plm:"+str(photo_id),'l') # a home_page link corresponds with this photo
		if link_id:
			hash_name2 = "lk:"+str(link_id)
			if my_server.exists(hash_name2) and is_citizen:
				my_server.hincrby(hash_name2,"v",amount = 1 if value == 1 else -1) #vote score (in case photo got published on home page)
		##################HTML injection##################
			add_vote_to_home_photo(link_id,value,username,is_pinkstar)
		##################################################
		return True
	else:
		return False

#home_photo version of def add_vote_to_link
def add_vote_to_home_photo(link_id, value, username,is_pinkstar):
	my_server = redis.Redis(connection_pool=POOL)
	plain_username = username
	hash_name = "lk:"+str(link_id) #lk is 'link'
	vote_text = my_server.hget(hash_name,'vt')
	username = username_formatting(username.encode('utf-8'),is_pinkstar,'small',True)
	index = '3' if value == 1 else '-3'
	if vote_text:
		new_text = username+VOTE_TEXT[index]
		text = new_text+vote_text.decode('utf-8')
		my_server.hset(hash_name,'vt',text)
	else:
		text = username+VOTE_TEXT[index]
		my_server.hset(hash_name,'vt',text)

def resurrect_home_photo(link_id):
	my_server = redis.Redis(connection_pool=POOL)
	if link_id:
		hash_name = "lk:"+str(link_id) #lk is 'link'
		my_server.hset(hash_name,'v',0)

def get_photo_owner(photo_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "ph:"+str(photo_id)
	return my_server.hget(hash_name,'oi')

def get_photo_votes(photo_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "vp:"+str(photo_id)
	return my_server.zrange(sorted_set, 0, -1, withscores=True)

def voted_for_photo(photo_lst_of_dict,username):
	my_server = redis.Redis(connection_pool=POOL)
	photos_voted = []
	pipeline1 = my_server.pipeline()
	for photo in photo_lst_of_dict:
		sorted_set = "vp:"+photo['i']
		pipeline1.zscore(sorted_set, username)
	already_exists_list =  pipeline1.execute()
	count = 0
	for already_exists in already_exists_list:
		if already_exists == 0 or already_exists == 1:
			# i.e. upvote or downvote already exists, thus this photo.id counts!
			photos_voted.append(photo_lst_of_dict[count]['i'])
		count += 1
	return photos_voted

def voted_for_photo_qs(photo_qs,username):
	my_server = redis.Redis(connection_pool=POOL)
	photos_voted = []
	pipeline1 = my_server.pipeline()
	for photo in photo_qs:
		sorted_set = "vp:"+str(photo.id)
		pipeline1.zscore(sorted_set, username)
	already_exists_list =  pipeline1.execute()
	count = 0
	for already_exists in already_exists_list:
		if already_exists == 0 or already_exists == 1:
			# i.e. upvote or downvote already exists, thus this photo.id counts!
			photos_voted.append(photo_qs[count].id)
		count += 1
	return photos_voted

def voted_for_single_photo(photo_id, username):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "vp:"+str(photo_id)
	already_exists = my_server.zscore(sorted_set, username)
	if already_exists != 0 and already_exists != 1:
		# i.e. does not already exist
		return False
	else:
		# i.e. already exists
		return True

#vote blocking algorithm that elegently cools down with time
def can_vote_on_photo(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	photo_votes_allowed = "pva:"+str(user_id) #photo votes allowed to user_id
	current_spree = my_server.get(photo_votes_allowed)
	if current_spree is None:
		pipeline1 = my_server.pipeline()
		my_server.incr(photo_votes_allowed)
		my_server.expire(photo_votes_allowed,FORTY_FIVE_SECS)
		pipeline1.execute()
		return None, True
	elif int(current_spree) > (PHOTO_VOTE_SPREE_ALWD-1):
		ttl = my_server.ttl(photo_votes_allowed)
		return ttl, False
	else:
		pipeline1 = my_server.pipeline()
		my_server.incr(photo_votes_allowed)
		my_server.expire(photo_votes_allowed,FORTY_FIVE_SECS*(int(current_spree)+1))
		pipeline1.execute()
		return None, True

def never_posted_photo(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	if my_server.llen("phts:"+str(user_id)):
		return False
	else:
		return True

def get_recent_photos(user_id):
	"""
	Contains last 5 photos

	This list self-deletes if user doesn't upload a photo for more than 4 days
	"""
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.lrange("phts:"+str(user_id), 0, -1)

def save_recent_photo(user_id, photo_id):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	pipeline1.lpush("phts:"+str(user_id), photo_id)
	pipeline1.ltrim("phts:"+str(user_id), 0, 4) # save the most recent 5 photos'
	pipeline1.expire("phts:"+str(user_id),FOUR_DAYS) #ensuring people who don't post anything for 4 days have to restart
	pipeline1.execute()

#####################Video objects#####################

def get_recent_videos(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.lrange("vids:"+str(user_id), 0, -1)

def save_recent_video(user_id, video_id):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.lpush("vids:"+str(user_id), video_id)
	my_server.ltrim("vids:"+str(user_id), 0, 4) # save the most recent 5 vids
	
def get_video_votes(video_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "vv:"+str(video_id) #vv is 'voted video'
	return my_server.zrange(sorted_set, 0, -1, withscores=True)

# def voted_for_video(video_qs,username):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	videos_voted = []
# 	for video in video_qs:
# 		sorted_set = "vv:"+str(video.id)
# 		already_exists = my_server.zscore(sorted_set, username)
# 		if already_exists == 0 or already_exists == 1:
# 			# i.e. upvote or downvote already exists, thus this photo.id counts!
# 			videos_voted.append(video.id)
# 	return videos_voted

def voted_for_video(video_qs,username):
	my_server = redis.Redis(connection_pool=POOL)
	videos_voted = []
	pipeline1 = my_server.pipeline()
	for video in video_qs:
		sorted_set = "vv:"+str(video.id)
		pipeline1.zscore(sorted_set, username)
	already_exists_list =  pipeline1.execute()
	count = 0
	for already_exists in already_exists_list:
		if already_exists == 0 or already_exists == 1:
			# i.e. upvote or downvote already exists, thus this photo.id counts!
			videos_voted.append(video_qs[count].id)
		count += 1
	return videos_voted

def add_vote_to_video(video_id, username, value):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "vv:"+str(video_id) #vv is 'voted video'
	already_exists = my_server.zscore(sorted_set, username)
	if already_exists != 0 and already_exists != 1:
		#add the vote
		my_server.zadd(sorted_set, username, value)
		#update last vote time
		hash_name = "lvt:"+str(video_id) #lvt is 'last vote time'
		current_time = time.time()
		mapping = {'t':current_time}
		my_server.hmset(hash_name, mapping)
		return True
	else:
		return False

def video_uploaded_too_soon(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "rut:"+str(user_id)#ru is 'recent upload time' - stores the last video upload time of user
	most_recent_time = my_server.hget(hash_name, 't') # get the most recent video upload time
	current_time = time.time()
	if most_recent_time and (current_time - float(most_recent_time)) < 300.0:
		# the next video is being uploaded too soon, so don't allow them to upload it
		seconds_to_go = 300.0-(current_time-float(most_recent_time))
		return True, seconds_to_go
	else:
		mapping = {'usr':user_id, 't':current_time}
		my_server.hmset(hash_name, mapping)
		return False, 0

def all_videos():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.lrange("videos:1000", 0, -1)

def add_video(video_id):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.lpush("videos:1000", video_id)
	rand = randint(0,9)
	if rand == 1: #invoking ltrim only 1/10th of the times this function is hit
		my_server.ltrim("videos:1000", 0, 999)

#####################Link objects#####################


def retrieve_all_home_links_with_scores(score_type,urdu_only=False,exclude_photos=False):
	my_server = redis.Redis(connection_pool=POOL)
	if urdu_only:
		all_link_ids = my_server.lrange("filteredurduposts:1000", 0, -1)
	else:
		all_link_ids = my_server.lrange("filteredposts:1000", 0, -1)
	if score_type == 'votes':
		if exclude_photos:
			prefix = 'v:'
		else:
			prefix = 'v:'
	elif score_type == 'comments':
		if exclude_photos:
			prefix = 'rlk1:'
		else:
			prefix = 'rlk:'
	pipeline1 = my_server.pipeline()
	for link_id in all_link_ids:
		pipeline1.zrange(prefix+link_id,0,-1,withscores=True)
	all_sorted_sets = pipeline1.execute()
	return all_sorted_sets, all_link_ids
	

def process_home_links(list_of_dicts):
	photo_result = []
	links_result = []
	count = 0
	for dictionary in list_of_dicts:
		links_result.append(dictionary)
		if 'pi' in dictionary:
			photo_result.append(dictionary)
		count += 1
	return photo_result, links_result

# def process_home_dicts(single_dict):
# 	if 'pi' in single_dict:
# 		return single_dict, single_dict
# 	else:
# 		return [], single_dict


def retrieve_home_links(link_id_list):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for link_id in link_id_list:
		hash_name="lk:"+str(link_id)
		pipeline1.hgetall(hash_name)
	result1 = filter(None, pipeline1.execute())
	return process_home_links(result1)
	# pool = Pool()
	# results = pool.map(process_home_dicts, result1) # returns list of tuples containing a dictionary object and an empty list (for 'pi')
	# photo_result = [i[0] for i in results if i[0]]
	# link_result = [i[1] for i in results]
	# return photo_result, link_result
	

def get_photo_link_mapping(photo_pk):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "plm:"+str(photo_pk) #plm is 'photo_link_mapping'
	return my_server.hget(hash_name,'l')

def photo_link_mapping(photo_pk, link_pk):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "plm:"+str(photo_pk) #plm is 'photo_link_mapping'
	mapping = {'l':link_pk}
	my_server.hmset(hash_name,mapping)

def update_cc_in_home_photo(photo_pk):
	my_server = redis.Redis(connection_pool=POOL)
	link_pk = my_server.hget("plm:"+str(photo_pk), 'l') # get the link id
	hash_name = "lk:"+str(link_pk) #lk is 'link'
	if my_server.exists(hash_name):
		my_server.hincrby(hash_name, "pc", amount=1)

def update_comment_in_home_link(reply,writer,writer_av,time,writer_id,link_pk,is_pinkstar):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "lk:"+str(link_pk) #lk is 'link'
	if my_server.exists(hash_name):
		#################################Saving latest publicreply################################
		latest_reply_head = av_url_formatting(av_url=writer_av, style='round')+"&nbsp;"+username_formatting(writer.encode('utf-8'),is_pinkstar,'medium',False)
		existing_payload = my_server.hget(hash_name,'replies')
		payload = latest_reply_head+"#"+str(time)+"#"+str(writer_id)+"#"+writer+"#"+str(link_pk)+"#"+reply+"#el#" #el# signifies an end-of-line character
		if existing_payload:
			existing_payload = truncate_payload(existing_payload)
			payload = existing_payload.decode('utf-8')+payload
		my_server.hset(hash_name,'replies',payload)
		########################################################################################
		amnt = my_server.hincrby(hash_name, "cc", amount=1) #updating comment count in home link
		return amnt
	else:
		return 0

# maintains a sorted set containing rate-able attributes for any given home_link ("lk:"+str(link_pk))
def add_home_rating_ingredients(parent_id, text, replier_id, time, link_writer_id, photo_post):
	my_server = redis.Redis(connection_pool=POOL)
	parent_id = str(parent_id)
	hash_name = "lk:"+parent_id #lk is 'link'
	if my_server.exists(hash_name):
		my_server.zadd("rlk:"+parent_id,str(replier_id)+":"+str(link_writer_id),recency_and_length_score(epoch_time=time,text=text))
		##################################################################################################################################
		########################################Helps in creating text only home rating###################################################
		if not photo_post:																												 #
			my_server.zadd("rlk1:"+parent_id,str(replier_id)+":"+str(link_writer_id),recency_and_length_score(epoch_time=time,text=text))#
		##################################################################################################################################
		##################################################################################################################################


def add_home_link(link_pk=None, categ=None, nick=None, av_url=None, desc=None, \
	meh_url=None, awld=None, hot_sc=None, img_url=None, v_sc=None, ph_pk=None, \
	ph_cc=None, scr=None, cc=None, writer_pk=None, device=None, by_pinkstar=None):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "lk:"+str(link_pk) #lk is 'link'
	av_url = av_url_formatting(av_url=av_url,style='round',categ=categ)
	scr = scr_formatting(scr)
	device = device_formatting(device)
	categ_head,categ_tail = category_formatting(categ)
	pinkstar = pinkstar_formatting(by_pinkstar)
	# reply_button = comment_count_formatting(cc,link_pk)
	# nick = '🌻'
	if categ == '1':
		# this is a typical link on home
		mapping = {'l':link_pk, 'c':categ, 'n':nick, 'au':av_url, 'de':desc, 'sc':scr, 'cc':cc, 'dc':device, 'w':writer_pk, \
		't':time.time(),'ch':categ_head,'ct':categ_tail,'p':pinkstar}#,'rb':reply_button }
	elif categ == '2':
		# this announces public mehfil creation on home
		mapping = {'l':link_pk, 'c':categ, 'n':nick, 'au':av_url, 'de':desc, 'sc':scr, 'cc':cc, 'dc':device, 'w':writer_pk, \
		'm':meh_url, 't':time.time(),'ch':categ_head,'ct':categ_tail}#,'p':pinkstar,'rb':reply_button }
	elif categ in ('3','4','5','7','8','9','10','11','12','13','14','15','16','18','19','20'):
		# Relates to cricket:
		# '3' Karachi Kings
		# '4' Peshawar Zalmi
		# '5' Lahre Qalandards
		# '7' Quetta Gladiators
		# '8' Islamabad United
		# '10' New Zealand
		# '11' South Africa
		# '12' Pakistan
		# '13' West Indies
		# '14' India
		# '15' Sri Lanka
		# '16' England
		# '18' World Eleven
		# '19' Multan Sultans
		# '20' Australia
		# '9' Other cricket team
		mapping = {'l':link_pk, 'c':categ, 'n':nick, 'au':av_url, 'de':desc, 'sc':scr, 'cc':cc, 'dc':device, 'w':writer_pk, \
		't':time.time(),'ch':categ_head,'ct':categ_tail,'p':pinkstar}
	elif categ == '6':
		# this is a photo-containing link on home
		mapping = {'l':link_pk, 'c':categ, 'n':nick, 'au':av_url, 'de':desc, 'sc':scr, 'cc':cc, 'dc':device, 'w':writer_pk, \
		'aw':awld, 'h':hot_sc, 'i':img_url, 'v':v_sc, 'pi':ph_pk, 'pc':ph_cc, 't':time.time(),'ch':categ_head,'ct':categ_tail,\
		'p':pinkstar }
	elif categ == '17':
		# this is a link in Urdu
		mapping = {'l':link_pk, 'c':categ, 'n':nick, 'au':av_url, 'de':desc, 'sc':scr, 'cc':cc, 'dc':device, 'w':writer_pk, \
		't':time.time(),'ch':categ_head,'ct':categ_tail,'p':pinkstar}#,'rb':reply_button }
	# add the info in a hash
	my_server.hmset(hash_name, mapping)

#vote blocking algorithm that elegently cools down with time
def can_vote_on_link(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	votes_allowed = "va:"+str(user_id) #votes allowed to user_id
	current_spree = my_server.get(votes_allowed)
	if current_spree is None:
		pipeline1 = my_server.pipeline()
		pipeline1.incr(votes_allowed)
		pipeline1.expire(votes_allowed,FORTY_FIVE_SECS)
		pipeline1.execute()
		return None, True
	elif int(current_spree) > (VOTE_SPREE_ALWD-1):
		ttl = my_server.ttl(votes_allowed)
		return ttl, False
	else:
		pipeline1 = my_server.pipeline()
		pipeline1.incr(votes_allowed)
		pipeline1.expire(votes_allowed,FORTY_FIVE_SECS*(int(current_spree)+1))
		pipeline1.execute()
		return None, True

def get_link_writer(link_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "lk:"+str(link_id) #lk is 'link'
	return my_server.hget(hash_name,'w')


def get_latest_group_replies(group_id_list):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for group_id in group_id_list:
		pipeline1.get("lgr:"+group_id)
	return pipeline1.execute()

def set_latest_group_reply(group_id, reply_id):
	"""
	Used to populate group list
	"""
	my_server = redis.Redis(connection_pool=POOL)
	my_server.setex("lgr:"+str(group_id),reply_id,TWO_WEEKS)
	
def voted_for_link(link_id, username):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "v:"+str(link_id)
	already_exists = my_server.zscore(sorted_set, username)
	if already_exists:
		return True
	else:
		return False

def get_home_link_votes(link_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "v:"+str(link_id)
	return my_server.zrange(sorted_set, 0, -1, withscores=True)

def add_vote_to_link(link_pk,value,username,is_pinkstar):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "v:"+str(link_pk) #set of all votes cast against a 'home link'.
	# username = username.encode('utf-8')
	already_exists = my_server.zscore(sorted_set, username)
	if not already_exists:
		plain_username = username
		hash_name = "lk:"+str(link_pk) #lk is 'link'
		vote_text = my_server.hget(hash_name,'vt')
		username = username_formatting(username.encode('utf-8'),is_pinkstar,'small',True)
		if vote_text:
			new_text = username+VOTE_TEXT[value]
			text = new_text+vote_text.decode('utf-8')
			my_server.hset(hash_name,'vt',text)
			my_server.zadd(sorted_set, plain_username, value)
		else:
			text = username+VOTE_TEXT[value]
			my_server.hset(hash_name,'vt',text)
			my_server.zadd(sorted_set, plain_username, value)

def all_best_photos():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.zrevrange("bestphotos:1000", 0, -1, withscores=True)

def add_photos_to_best(photo_scores):
	my_server = redis.Redis(connection_pool=POOL)
	best_photos = "bestphotos:1000"
	#executing the following commands as a single transaction
	try:
		pipeline1 = my_server.pipeline()
		pipeline1.delete(best_photos)
		pipeline1.zadd(best_photos,*photo_scores)
		pipeline1.execute()
	except:
		pass

def get_best_photo():
	my_server = redis.Redis(connection_pool=POOL)
	try:
		return my_server.zrange("bestphotos:1000",-1,-1)[0]
	except:
		return None

def get_previous_best_photo():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.get("best_photo")

def set_best_photo(photo_id):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.set("best_photo",photo_id)

def all_photos():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.lrange("photos:1000", 0, -1)

def add_photo(photo_id):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.lpush("photos:1000", photo_id)
	my_server.ltrim("photos:1000", 0, 999)

def all_unfiltered_posts():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.lrange("unfilteredposts:1000", 0, -1)

def set_best_posts_on_home(link_ids,urdu_only=False,exclude_photos=False):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	if exclude_photos:
		if urdu_only:
			pipeline1.delete("besturduposts")
			pipeline1.lpush("besturduposts",*link_ids)
		else:
			# contains text_only best posts
			pipeline1.delete("bestposts_2")
			pipeline1.lpush("bestposts_2",*link_ids)
	else:
		if urdu_only:
			pipeline1.delete("besturduposts")
			pipeline1.lpush("besturduposts",*link_ids)
		else:
			pipeline1.delete("bestposts")
			pipeline1.lpush("bestposts",*link_ids)
	pipeline1.execute()
		

def all_best_urdu_posts():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.lrange("besturduposts", 0, -1)

def all_best_posts():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.lrange("bestposts", 0, -1)

###############################################################################################################################
#########################################################Optimizely Exp########################################################

# def all_best_posts_1():
# 	my_server = redis.Redis(connection_pool=POOL)
# 	return my_server.lrange("bestposts", 0, -1)

# def all_best_posts_2():
# 	my_server = redis.Redis(connection_pool=POOL)
# 	return my_server.lrange("bestposts_2", 0, -1)

###############################################################################################################################
###############################################################################################################################

def all_filtered_posts():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.lrange("filteredposts:1000", 0, -1)

def all_filtered_urdu_posts():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.lrange("filteredurduposts:1000", 0, -1)

def add_filtered_post(link_id, is_ur=False):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.lpush("filteredposts:1000", link_id)
	my_server.ltrim("filteredposts:1000", 0, 999)
	if is_ur:
		my_server.lpush("filteredurduposts:1000", link_id)
		my_server.ltrim("filteredurduposts:1000", 0, 999)

def add_unfiltered_post(link_id):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.lpush("unfilteredposts:1000", link_id)
	extras = my_server.lrange("unfilteredposts:1000", 1000, -1)
	my_server.ltrim("unfilteredposts:1000", 0, 999)
	return extras

def add_to_deletion_queue(link_id_list):
	#this delays deletion of hashes formed by 'add_home_link'
	my_server = redis.Redis(connection_pool=POOL)
	my_server.lpush("deletionqueue:200", *link_id_list)
	return my_server.llen("deletionqueue:200")

def delete_queue():
	#this deletes hashes formed by 'add_home_link'
	my_server = redis.Redis(connection_pool=POOL)
	hashes = my_server.lrange("deletionqueue:200", 0, -1)
	pipeline1 = my_server.pipeline()
	for link_id in hashes:
		pipeline1.delete("lk:"+link_id)
		pipeline1.delete("rlk:"+link_id)
		pipeline1.delete("v:"+link_id)
	pipeline1.execute()
	my_server.delete("deletionqueue:200")


#####################maintaining group membership#####################

#for each user, keep a list of groups they have been invited to, and list of groups they are a member of
#after 1 week of pushing this update, change group_page to solely a list of groups a person was invited to, or was a member of!

def bulk_check_group_membership(user_ids_list,group_id):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	non_member_ids = []
	for user_id in user_ids_list:
		set_name = "ug:"+str(user_id) #ug is user's groups
		pipeline1.sismember(set_name,group_id)
	result_list = pipeline1.execute()
	count = 0
	for result in result_list:
		if not result:
			non_member_ids.append(user_ids_list[count])
		count += 1
	return non_member_ids

def bulk_sanitize_group_invite_and_membership(user_ids_list):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for user_id in user_ids_list:
		user_id = str(int(user_id))
		pipeline1.delete("ug:"+user_id)
		pipeline1.delete("pir:"+user_id)
	pipeline1.execute()

def remove_user_group(user_id, group_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ug:"+str(user_id) #ug is user's groups
	my_server.srem("ug:"+str(user_id), group_id)

def get_user_groups(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ug:"+str(user_id) #ug is user's groups
	return my_server.smembers(set_name)

def add_user_group(user_id, group_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ug:"+str(user_id) #ug is user's groups
	my_server.sadd(set_name, group_id)

def get_active_invites(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	unsorted_set = "pir:"+str(user_id) #pir is 'private/public invite reply' - stores every 'active' invite_id - deleted if reply seen or X is pressed
	return my_server.smembers(unsorted_set)

def remove_group_invite(user_id, group_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "giu:"+str(group_id)+str(user_id)#giu is 'group invite for user' - stores the invite_id that was sent to the user (for later retrieval)
	invite_id = my_server.hget(hash_name, 'ivt') # get the invite_id to be removed
	my_server.srem("pir:"+str(user_id), invite_id)
	my_server.delete(hash_name)

# def bulk_check_group_invite(user_id_list,group_id):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	non_invited_ids = []
# 	for user_id in user_id_list:
# 		sorted_set = "ipg:"+str(user_id)
# 		already_exists = my_server.zscore(sorted_set, group_id)
# 		if not already_exists:
# 			non_invited_ids.append(user_id)
# 	return non_invited_ids

def bulk_check_group_invite(user_id_list,group_id):
	my_server = redis.Redis(connection_pool=POOL)
	non_invited_ids = []
	pipeline1 = my_server.pipeline()
	for user_id in user_id_list:
		sorted_set = "ipg:"+str(user_id)
		already_exists = pipeline1.zscore(sorted_set, group_id)
	already_exists_list = pipeline1.execute()
	count = 0
	for already_exists in already_exists_list:
		if not already_exists:
			non_invited_ids.append(user_id_list[count])
		count += 1
	return non_invited_ids

def check_group_invite(user_id, group_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "ipg:"+str(user_id) #ipg is 'invited private/public group' - this stores the group_id a user has already been invited to - limited to 100 invites
	already_exists = my_server.zscore(sorted_set, group_id)
	if not already_exists:
		return False
	else:
		return True

def add_group_invite(user_id, group_id, invite_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "ipg:"+str(user_id) #ipg is 'invited private/public group' - this stores the group_id a user has already been invited to - limited to 100 invites
	already_exists = my_server.zscore(sorted_set, group_id)
	if not already_exists:
		unsorted_set = "pir:"+str(user_id) #pir is 'private/public invite reply' - stores every 'active' invite_id - deleted if reply seen or X is pressed
		hash_name = "giu:"+str(group_id)+str(user_id)#giu is 'group invite for user' - stores the invite_id that was sent to the user (for later retrieval)
		size = my_server.zcard(sorted_set)
		limit = 100
		if size > limit: #don't let it overflow - limit its size
			element = my_server.zrange(sorted_set, 0, 0) # get the group_id to be removed
			old_invite_id = my_server.hget("giu:"+element[0]+str(user_id), 'ivt') # get the invite_id to be removed
			my_server.srem("pir:"+str(user_id), old_invite_id) #remove the invite_id
			my_server.delete("giu:"+element[0]+str(user_id)) #remove the related hash
			my_server.zremrangebyrank(sorted_set, 0, 0) #remove the element in question from the sorted set
		my_server.zadd(sorted_set, group_id, time.time()) #where time.time() is the score, and group_id is the value
		my_server.sadd(unsorted_set, invite_id) #invited_id is the reply_id that carries the invite
		mapping = {'grp':group_id, 'usr':user_id, 'ivt':invite_id}
		my_server.hmset(hash_name, mapping)

def check_group_member(group_id, username):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "pgm:"+str(group_id) #pgm is private/public_group_members
	if my_server.sismember(set_name, username):
		return True
	else:
		return False

def remove_group_for_all_members(group_id, member_ids):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for mem_id in member_ids:
		set_name = "ug:"+str(mem_id) #ug is user's groups
		pipeline1.srem(set_name,group_id)
	pipeline1.execute()

def remove_latest_group_reply(group_id):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.delete("lgr:"+str(group_id))


def remove_all_group_members(group_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "pgm:"+str(group_id) #pgm is private/public_group_members
	if my_server.exists(set_name):
		my_server.delete(set_name)

def remove_group_member(group_id, username):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "pgm:"+str(group_id) #pgm is private/public_group_members
	if my_server.exists(set_name):
		if my_server.sismember(set_name, username):
			my_server.srem(set_name, username)
		else:
			pass
	else:
		pass
	return my_server.scard(set_name)

def add_group_member(group_id, username):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "pgm:"+str(group_id) #pgm is private_group_members
	if my_server.sismember(set_name, username):
		pass
	else:
		my_server.sadd(set_name, username)

def get_group_members(group_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "pgm:"+str(group_id) #pgm is private_group_members
	if my_server.exists(set_name):
		members = my_server.smembers(set_name)
	else:
		members = []
	return members

#####################checking abuse and punishing#####################

def remove_key(name):
	my_server = redis.Redis(connection_pool=POOL)
	try:
		my_server.delete(name)
	except:
		pass

def document_report_reason(user_id, user_score, reporter_id, reporter_cost, desc):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "hafs:"+str(user_id)+str(reporter_id) #hafs is 'hash abuse feedback set', it contains strings about the person's wrong doings
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		return False#already given feedback
	else:
		mapping = {'tgt':user_id, 'scr':user_score, 'rep':reporter_id, 'paid':reporter_cost, 'txt':desc}
		my_server.hmset(hash_name, mapping)
		my_server.sadd("report_reasons", hash_name)
		return True

def comment_allowed(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "cah:"+str(user_id)
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_contents = my_server.hgetall(hash_name)
		last_hide_time = hash_contents["t"]
		integrity = int(hash_contents["tgr"])
		time_now = time.time()
		if integrity < -1:
			if (time_now-float(last_hide_time)) < ONE_DAY:
				time_remaining = (float(last_hide_time)+ONE_DAY)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 0:
			if (time_now-float(last_hide_time)) < TWELVE_HOURS:
				time_remaining = (float(last_hide_time)+TWELVE_HOURS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 1:
			if (time_now-float(last_hide_time)) < SIX_HOURS:
				time_remaining = (float(last_hide_time)+SIX_HOURS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 2:
			#if last_vote_time was 1 hour ago, let the person post, else he's banned
			if (time_now-float(last_hide_time)) < ONE_HOUR:
				time_remaining = (float(last_hide_time)+ONE_HOUR)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 3:
			#if last_vote_time was 10 mins ago, let the person post, else he's banned
			if (time_now-float(last_hide_time)) < TEN_MINS:
				time_remaining = (float(last_hide_time)+TEN_MINS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 4:
			##if last_hide_time was 3 mins ago, let the person post, else he's banned
			#re-affirm integrity after serving ban
			if (time_now-float(last_hide_time)) < THREE_MINS:
				time_remaining = (float(last_hide_time)+THREE_MINS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 5:
			#not refilling integrity for THREE HOURS, since no punishment was served. Keep the person on thin ice
			if (time_now-float(last_hide_time)) < THREE_HOURS:
				banned = False
				time_remaining = 0
				warned = True
			else:
				#refill integrity after 3 hours of not getting a single hide
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		else:
			#integrity is refilled after 1 hour of no hide, by default
			if (time_now-float(last_hide_time)) < ONE_HOUR:
				banned = False
				time_remaining = 0
				warned = False
			else:
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
	else:
		banned = False
		time_remaining = 0
		warned = False
	return banned, time_remaining, warned

def document_comment_abuse(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "cah:"+str(user_id) #cah is 'comment abuse hash', it contains latest integrity value
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_contents = my_server.hgetall(hash_name)
		old_time = hash_contents["t"]
		new_time = time.time()
		time_difference = new_time - float(old_time) #in seconds
		if time_difference < 300.0:
			#update time and integrity
			my_server.hincrby(hash_name, "tgr", amount=-1)
			my_server.hset(hash_name, "t", new_time)
		else:
			#just update the time 
			my_server.hset(hash_name, "t", new_time)
	else:
		mapping = {'t': time.time(), 'tgr':5}
		my_server.hmset(hash_name, mapping)

def publicreply_allowed(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "pah:"+str(user_id)
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_contents = my_server.hgetall(hash_name)
		last_hide_time = hash_contents["t"]
		integrity = int(hash_contents["tgr"])
		time_now = time.time()
		if integrity < -1:
			if (time_now-float(last_hide_time)) < ONE_DAY:
				time_remaining = (float(last_hide_time)+ONE_DAY)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 0:
			if (time_now-float(last_hide_time)) < TWELVE_HOURS:
				time_remaining = (float(last_hide_time)+TWELVE_HOURS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 1:
			if (time_now-float(last_hide_time)) < SIX_HOURS:
				time_remaining = (float(last_hide_time)+SIX_HOURS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 2:
			#if last_vote_time was 1 hour ago, let the person post, else he's banned
			if (time_now-float(last_hide_time)) < ONE_HOUR:
				time_remaining = (float(last_hide_time)+ONE_HOUR)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 3:
			#if last_vote_time was 10 mins ago, let the person post, else he's banned
			if (time_now-float(last_hide_time)) < TEN_MINS:
				time_remaining = (float(last_hide_time)+TEN_MINS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 4:
			##if last_hide_time was 3 mins ago, let the person post, else he's banned
			#re-affirm integrity after serving ban
			if (time_now-float(last_hide_time)) < THREE_MINS:
				time_remaining = (float(last_hide_time)+THREE_MINS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 5:
			#not refilling integrity for THREE HOURS, since no punishment was served. Keep the person on thin ice
			if (time_now-float(last_hide_time)) < THREE_HOURS:
				banned = False
				time_remaining = 0
				warned = True
			else:
				#refill integrity after 3 hours of not getting a single hide
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		else:
			#integrity is refilled after 1 hour of no hide, by default
			if (time_now-float(last_hide_time)) < ONE_HOUR:
				banned = False
				time_remaining = 0
				warned = False
			else:
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
	else:
		banned = False
		time_remaining = 0
		warned = False
	return banned, time_remaining, warned

def document_publicreply_abuse(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "pah:"+str(user_id) #pah is 'publicreply abuse hash', it contains latest integrity value
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_contents = my_server.hgetall(hash_name)
		old_time = hash_contents["t"]
		new_time = time.time()
		time_difference = new_time - float(old_time) #in seconds
		if time_difference < 300.0:
			#update time and integrity
			my_server.hincrby(hash_name, "tgr", amount=-1)
			my_server.hset(hash_name, "t", new_time)
		else:
			#just update the time 
			my_server.hset(hash_name, "t", new_time)
	else:
		mapping = {'t': time.time(), 'tgr':5}
		my_server.hmset(hash_name, mapping)

#####################checking image perceptual hashes#####################

def already_exists(photo_hash,categ=None):
	my_server = redis.Redis(connection_pool=POOL)
	if categ == 'ecomm':
		exists = my_server.zscore("perceptual_hash_used_item_set", photo_hash)
	else:
		exists = my_server.zscore("perceptual_hash_set", photo_hash)
	return exists

def insert_hash(photo_id, photo_hash,categ=None):
	my_server = redis.Redis(connection_pool=POOL)
	if categ == 'ecomm':
		set_name = "perceptual_hash_used_item_set"
	else:
		set_name = "perceptual_hash_set"
	##########################
	try:
		size = my_server.zcard(set_name)
		if categ == 'ecomm':
			limit = 500
		else:
			limit = 10000
		if size < (limit+1):
			my_server.zadd(set_name, photo_hash, photo_id)
		else:
		   my_server.zremrangebyrank(set_name, 0, (size-limit-1))
		   my_server.zadd(set_name, photo_hash, photo_id)
	except:
		my_server.zadd(set_name, photo_hash, photo_id)

def delete_avg_hash(hash_list, categ=None):
	my_server = redis.Redis(connection_pool=POOL)
	if hash_list:
		if categ == 'ecomm':
			my_server.zrem("perceptual_hash_used_item_set", *hash_list)
		else:
			my_server.zrem("perceptual_hash_set", *hash_list)


############################saving ad feedback############################

def set_ad_feedback(advertiser,feedback,username,user_id,submitted_at):
	my_server = redis.Redis(connection_pool=POOL)
	ad_feedback_counter = "af:"+advertiser
	feedback_id = my_server.incr(ad_feedback_counter)
	ad_feedback = advertiser+":"+str(feedback_id)
	mapping = {'username':username,'user_id':user_id,'feedback':feedback,'submitted_at':submitted_at}
	my_server.hmset(ad_feedback,mapping)
	return True

def get_ad_feedback(ad_campaign):
	my_server = redis.Redis(connection_pool=POOL)
	ad_feedback_counter = "af:"+ad_campaign
	if my_server.exists(ad_feedback_counter):
		feedback_id = my_server.get(ad_feedback_counter)
		pipeline1 = my_server.pipeline()
		for index in range(1,int(feedback_id)+1):
			ad_feedback = ad_campaign+":"+str(index)
			pipeline1.hgetall(ad_feedback)
		results = pipeline1.execute()
		#returns list of dictionaries
		return results, feedback_id
	else:
		return [],0

def save_website_feedback(data):
	my_server = redis.Redis(connection_pool=POOL)
	feedback_set = "website_feedback"
	if not my_server.sismember(feedback_set,data["user_id"]):
		website_feedback = "wf:"+str(data["user_id"])
		# remove 'answer6':data["feedback6"] and 'question6':data["question6"] if only running 5 questions
		mapping = {'question1':data["question1"],'question2':data["question2"],'question3':data["question3"],\
		'question4':data["question4"],'question5':data["question5"],'answer1':data["feedback1"],'answer2':data["feedback2"],\
		'answer3':data["feedback3"],'answer4':data["feedback4"],'answer5':data["feedback5"],'username':data["username"],\
		'score':data["score"],"date_joined":data["date_joined"],"device":data["device"],"time_of_feedback":data["time_of_feedback"],\
		'answer6':data["feedback6"],'question6':data["question6"]}
		my_server.hmset(website_feedback,mapping)
		my_server.sadd(feedback_set,data["user_id"])
		return True
	else:
		return False

def website_feedback_given(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	return True if my_server.sismember("website_feedback",user_id) else False

def save_website_feedback_user_details(data):
	my_server = redis.Redis(connection_pool=POOL)
	feedback_set = "website_feedback"
	if my_server.sismember(feedback_set,data["user_id"]):
		website_feedback = "wf:"+str(data["user_id"])
		mapping = {'mobile':data["mobile"],'age':data["age"],'gender':data["gender"],'city':data["city"]}
		my_server.hmset(website_feedback,mapping)

def get_website_feedback():
	my_server = redis.Redis(connection_pool=POOL)
	feedback_set = "website_feedback"
	feedback_users = my_server.smembers(feedback_set)
	pipeline1 = my_server.pipeline()
	complaints_with_details = []
	for user_id in feedback_users:
		pipeline1.hgetall("wf:"+str(user_id))
	return pipeline1.execute()

def clean_up_feedback():
	my_server = redis.Redis(connection_pool=POOL)
	feedback_set = "website_feedback"
	feedback_users = my_server.smembers(feedback_set)
	complaints_with_details = []
	for user_id in feedback_users:
		my_server.delete("wf:"+str(user_id))
	my_server.delete("website_feedback")