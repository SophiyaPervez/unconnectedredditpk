
# coding=utf-8
import ujson as json
import redis, time, random
from datetime import datetime
from django.contrib.auth.models import User
from location import REDLOC4
from score import BAN_REASON, RATELIMIT_TTL, SUPER_FLOODING_THRESHOLD, FLOODING_THRESHOLD, LAZY_FLOODING_THRESHOLD, SHORT_MESSAGES_ALWD, \
SHARED_PHOTOS_CEILING, PHOTO_DELETION_BUFFER
from models import UserProfile, Photo

'''
##########Redis Namespace##########

city_shops = "city_shops"
"historical_calcs"
lip:<user_id> 'stores latest ip of a user for up to 5 mins'
logged_users = "logged_users"
sorted_set = "online_users"
user_ban = "ub:"+str(user_id)
user_times = "user_times:"+str(user_id)

pusk:<user_id>:<secret_key> # photo_upload_secret_key
tisk:<user_id>:<obj_type>:<obj_id> # text input secret_key

rlfh:<user_id> - rate limited from home (e.g. because of abusive reasons)
rlfpg:<user_id> - rate limited from public group (e.g. because of spammy behavior)
rlfpvg:<user_id> - rate limited from private group (e.g. because of spammy behavior)
rlfpc:<user_id> - rate limited from photo comments (e.g. because of spammy behavior)
rlfhr:<user_id> - rate limited from home replies (e.g. because of spammy behavior)

hir:<user_id> - home input rate (list holding times of posting on home for a specific user)
pgir:<user_id> - public group input rate (list holding times of posting in public group for a specific user)
pvgir:<user_id> - private group input rate (list holding times of posting in public group for a specific user)
pcir:<user_id> - photo comment input rate (list holding times of posting on photo comments for a specific user)
hrir:<user_id> - home reply input rate (list holding times of posting in home replies)

hit:<user_id> - home input text (list holding previous text of home posting for a specific user)
pgit:<user_id> - public group input text (list holding text of public group posting for a specific user in a specific group)
pvgit:<user_id> - private group input rate (list holding times of posting in private group for a specific user)
pcit:<user_id> - photo comment input text (list holding text of photo comments for a specific user and a specific photo)
hrit:<user_id> - home reply input text (list holding text of home replies for a specific user under a specific home sentence)

sm:<user_id>:<section>:<obj_id> - counter to count short messages sent on home objects

user_id:<username> is a key containing user_ids of certain usernames
uname:<user_id> is a hash containing username and avatar_url data of a user
pht:<photo_id> is a hash containing image_url and caption data of a photo posted by user
phd:<user_id> contains cached photo sharing data for a specific user_id (cached for 20 mins)
aurl:<user_id> is 'avatar_uploading_rate_limit', and is used to rate limit how frequently a user can change their avatar

vb:<star_id>:<visitor_id> 'visited_by' key that stores which star_id was visited by which visitor_id

------------ Personal Group Metrics ------------

lig_pm:<group_id> contains user_id that performed latest interaction in private mehfil with id group_id
lig_pg:<group_id> contains user_id that performed latest interaction in private chat with id group_id
pm_ch contains list of private mehfil IDs alongwith number of chats occuring in those private mehfils
pm_sw contains list of private mehfil IDs alongwith number of switchovers occuring in those private mehfils
pg_ch contains list of private chat IDs alongwith number of chats occuring in those private chats
pg_sw contains list of private chat IDs alongwith number of switchovers occuring in those private chats

gs_pm:<group_id>:<user_id> contains a 'session key' that idenitifies whether a new session has started for a user visiting a particular private mehfil
gs_pg:<group_id>:<user_id> contains a 'session key' that idenitifies whether a new session has started for a user visiting a particular private chat
pm_sess contains <group_id>:<user_id> pairs alongwith number of 24 hour sessions for that pair
pg_sess contains <group_id>:<user_id> pairs alongwith number of 24 hour sessions for that pair

p2p_sms is a list of <sent_by_id>:<sent_to_id>:<sending_time> tuples, tracking SMSes in private chat
rc:<sent_to_id> sets a key as a "red carpet" for sent_to_id (waits for them to return to Damadam as a result of an SMS sent by a friend)
sms_eft tracks sms effectiveness. It contains <user_id>:<time_passed_since_sms> pairs for users who returned to Damadam after being sent an SMS

exits contains <group_id>:<exit_by_id> pairs alongwith times of exiting a private chat. Useful for charting average life of a private chat.
del_after_exit contains groups and exit times for groups that were deleted due to exiting
del_after_idle contains groups and exit times for groups that were deleted due to idleness

------------ Social Sharing ------------

as:<photp_id>:<sharer_id> key to check whether a photo was already shared by a certain user (in whatsapp)

pdim:<photo_id> key that temporarily caches a shared photo's width and height

"sp:<photo_owner_id> is a sorted set containing information about photos shared of each user

###########
'''

POOL = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=REDLOC4, db=0)

TWO_WEEKS = 60*60*24*7*2
THREE_DAYS = 60*60*24*3
ONE_DAY = 60*60*24
ONE_HOUR = 60*60
TWELVE_HOURS = 60*60*12
THIRTY_MINS = 30*60
TWENTY_MINS = 20*60
TEN_MINS = 10*60
SEVEN_MINS = 7*60
FIVE_MINS = 5*60
THREE_MINS = 3*60
ONE_MIN = 60


def convert_to_epoch(time):
	return (time-datetime(1970,1,1)).total_seconds()


def save_deprecated_photo_ids_and_filenames(deprecated_photos):
	my_server = redis.Redis(connection_pool=POOL)
	final_list = []
	for filename, photo_id in deprecated_photos:
		filename = filename.split('photos/')[1]
		final_list.append(filename)
		final_list.append(photo_id)
	my_server.zadd("deprecated_photos",*final_list)


# def log_pic_uploader_status(user_id, is_verified):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	verified = '1' if is_verified else '0'
# 	my_server.lpush('uploaded_pics',verified+":"+str(user_id))

# def save_user_choice(user_id, choice):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	my_server.lpush("new_user_choice",{'user_id':user_id,'user_choice':choice})

# def log_referrer(referrer, loc, user_id):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	my_server.lpush("referrer",{'referrer':referrer,'origin':loc, 'user_id':user_id, 'time_stamp':time.time()})

def return_referrer_logs(log_name):
	return redis.Redis(connection_pool=POOL).lrange(log_name,0,-1)


# def error_logger(obj_creator_reported_id, object_creator_actual_id,actual_object_attributes, reported_link_attributes, from_loc, is_post_request,referrer):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	my_server.lpush("block_error",{'obj_creator_reported_id':obj_creator_reported_id,'object_creator_actual_id':object_creator_actual_id,\
# 		'actual_object_attributes':actual_object_attributes, 'reported_link_attributes':reported_link_attributes,'where_from':from_loc, \
# 		'is_post_request':is_post_request,'referrer':referrer})


# def log_html_error(obj_list, forms, page, nickname, referrer):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	my_server.lpush("matka_error",{'obj_list':obj_list,'forms':forms, 'page':page, 'username':nickname,'referrer':referrer ,'time':time.time()})

# def log_button_error(target_user_id, id_type,target_username,own_id, object_id,referrer):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	my_server.lpush("button_error",{'target_user_id':target_user_id,'id_type':id_type, 'target_username':target_username,'own_id':own_id, \
# 		'object_id':object_id,'referrer':referrer,'time':time.time()})


# def save_number_verification_error_data(user_id, err_data, err_type=None, on_fbs=None, is_auth=None, which_flow=None):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	if which_flow == 'consumer':
# 		err_data["user_id"], err_data["err_type"], err_data["on_fbs"], err_data["is_auth"] = user_id, err_type, on_fbs, is_auth
# 		my_server.lpush("consumer_number_errors",err_data)
# 	else:
# 		err_data["user_id"], err_data["err_type"], err_data["on_fbs"], err_data["is_auth"] = user_id, err_type, on_fbs, is_auth
# 		my_server.lpush("seller_number_errors",err_data)

#######################Ecomm Metrics######################

def log_ecomm_user_visit(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.lpush("ecomm_visits",user_id)

def get_and_reset_daily_ecomm_visits():
	my_server = redis.Redis(connection_pool=POOL)
	all_visits = my_server.lrange("ecomm_visits",0,-1)
	pipeline1 = my_server.pipeline()
	pipeline1.lpush("weekly_ecomm_visits",all_visits)
	pipeline1.delete("ecomm_visits")
	pipeline1.execute()
	return all_visits, my_server.llen("weekly_ecomm_visits")

def get_and_reset_weekly_ecomm_visits():
	import ast
	my_server = redis.Redis(connection_pool=POOL)
	weekly_visits = my_server.lrange("weekly_ecomm_visits",0,-1)
	weekly_gross_visits = []
	for daily_visits in weekly_visits:
		weekly_gross_visits += ast.literal_eval(daily_visits)
	my_server.delete("weekly_ecomm_visits")
	return weekly_gross_visits


def insert_metrics(ecomm_metrics, reporting_time, period=None):
	my_server = redis.Redis(connection_pool=POOL)
	if period == 'daily':
		mapping = {'entry_time':reporting_time, 'unique_clicks_per_unique_visitor':ecomm_metrics[0], 'unique_clicks_per_unique_clicker':ecomm_metrics[1], \
		'proportion_of_clickers_to_visitors':ecomm_metrics[2], 'unique_new_clickers_per_unique_new_visitors':ecomm_metrics[3], \
		'unique_new_clicks_per_unique_new_visitor':ecomm_metrics[4], 'total_unique_visitors':ecomm_metrics[5], 'total_unique_clicks':ecomm_metrics[6]}
		my_server.lpush("ecomm_metrics",mapping)
	if period == 'weekly':
		mapping = {'entry_time':reporting_time, 'weekly_unique_clicks_per_unique_visitor':ecomm_metrics[0], 'weekly_unique_clicks_per_unique_clicker':ecomm_metrics[1], \
		'weekly_proportion_of_clickers_to_visitors':ecomm_metrics[2], 'weekly_unique_visitors':ecomm_metrics[3], \
		'weekly_unique_clicks':ecomm_metrics[4]}
		my_server.lpush("weekly_ecomm_metrics",mapping)



def return_all_metrics_data():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.lrange("ecomm_metrics", 0, -1), my_server.lrange("weekly_ecomm_metrics", 0, -1)

#######################Photo Secret Key######################

def set_photo_upload_key(user_id, secret_key, group_id=None):
	"""
	Used to prevent double form submission when uploading photos (public photos or personal group photos)
	"""
	my_server = redis.Redis(connection_pool=POOL)
	sec_key = "pusk:"+str(user_id)+":"+group_id if group_id else "pusk:"+str(user_id)
	my_server.setex(sec_key,secret_key,TWENTY_MINS)


def get_and_delete_photo_upload_key(user_id, group_id=None):
	my_server = redis.Redis(connection_pool=POOL)
	user_id = str(user_id)
	sec_key = "pusk:"+user_id+":"+group_id if group_id else "pusk:"+user_id
	secret_key = my_server.get(sec_key)
	if secret_key:
		my_server.delete(sec_key)
		return secret_key
	else:
		return '1'


def set_text_input_key(user_id, obj_id, obj_type, secret_key):
	"""
	Used to prevent double form submission
	"""
	my_server = redis.Redis(connection_pool=POOL)
	sec_key = "tisk:"+str(user_id)+":"+obj_type+":"+str(obj_id)
	my_server.setex(sec_key,secret_key,TWENTY_MINS)


def get_and_delete_text_input_key(user_id, obj_id, obj_type):
	"""
	Checks if secret key exists and returns an appropriate response
	"""
	my_server = redis.Redis(connection_pool=POOL)
	sec_key = "tisk:"+str(user_id)+":"+obj_type+":"+str(obj_id)
	secret_key = my_server.get(sec_key)
	if secret_key:
		my_server.delete(sec_key)
		return secret_key
	else:
		return '1'


######################## Shared urls caching (for private chat) ########################

def cache_meta_data(url, mapping, time_timen_to_sniff, time_taken_to_parse, is_youtube, deg_of_comp):
	"""
	Cache shared url's meta_data for upto a day
	"""
	pipeline1 = redis.Redis(connection_pool=POOL).pipeline()
	pipeline1.hmset(url,mapping)
	pipeline1.expire(url,ONE_DAY)
	pipeline1.lpush("shared_urls",url+":"+is_youtube+":"+"{0:.2f}".format(time_taken_to_parse)+":"+"{0:.2f}".format(time_timen_to_sniff)+":"+"{0:.2f}".format(time.time())+":"+deg_of_comp)
	pipeline1.ltrim("shared_urls",0,999)#saving up to 1000 hits
	pipeline1.execute()

def get_cached_meta_data(url):
	"""
	Returns cached meta data, and extends life of cache by 3 days if it's a successful hit
	"""
	my_server = redis.Redis(connection_pool=POOL)
	meta_data = my_server.hgetall(url)
	if meta_data:
		my_server.expire(url,THREE_DAYS)
		return meta_data
	else:
		return {}


###################### Photo dimensions and data caching ######################

def get_cached_photo_dim(photo_id):
	"""
	Return photo with photo_id's height and width
	"""
	key = 'pdim:'+photo_id
	my_server = redis.Redis(connection_pool=POOL)
	my_server.expire(key,THREE_DAYS)#extending life of cache
	return my_server.hmget(key,'h','w')


def cache_photo_dim(photo_id,img_height,img_width):
	"""
	Cache photo dimensions for use in photo sharing to personal groups
	"""
	mapping, key = {'h':img_height,'w':img_width}, 'pdim:'+photo_id
	my_server = redis.Redis(connection_pool=POOL)
	my_server.hmset(key,mapping)
	my_server.expire(key,THREE_DAYS)


def retrieve_photo_data(photo_ids, owner_id):
	"""
	Retrieves photo data (caption and url)
	"""
	my_server = redis.Redis(connection_pool=POOL)
	photo_data, missing_photos = {}, []
	for photo_id in photo_ids:
		caption, image_url, upload_time = my_server.hmget('pht:'+photo_id,'caption','image_url','upload_time')
		if caption and image_url and upload_time:
			photo_data[photo_id] = {'caption':caption.decode('utf-8'),'image_url':image_url,'id':photo_id,'upload_time':upload_time}
		else:
			missing_photos.append(photo_id)
	if missing_photos:
		missing_data = Photo.objects.filter(id__in=missing_photos).values('id','image_file','caption','upload_time')
		for data in missing_data:
			photo_id = str(data['id'])
			key = 'pht:'+photo_id
			upload_time = str(convert_to_epoch(data['upload_time']))
			photo_data[photo_id] = {'caption':data['caption'],'image_url':data['image_file'],'id':photo_id,'upload_time':upload_time}
			my_server.hmset(key,{'caption':data['caption'],'image_url':data['image_file'],'upload_time':upload_time})
			my_server.expire(key,THREE_DAYS)
	return photo_data

###################### User credentials caching ######################


def retrieve_bulk_credentials(user_ids, decode_unames=False):
	"""
	Returns usernames and avatars if fed a list of user_ids

	Also caches the data for up to TWO days
	If avatar was never uploaded, 'empty' string is returned instead
	Returned format is dictionary of dictionaries, where int(user_ids) serve as keys. This ensures O(1) lookup down the road
	"""
	if not user_ids:
		return {}
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for user_id in user_ids:
		pipeline1.hmget('uname:'+str(user_id),'uname','avurl')
	credentials_wip = pipeline1.execute() #credentials_wip is a list of lists
	counter = 0
	credentials = {}#list of dictionaries
	uncollected_unames, uncollected_avurls = [], []
	for uname,avurl in credentials_wip:
		current_uid = int(user_ids[counter])
		uname = '' if not uname else uname
		avurl = '' if not avurl else avurl
		if decode_unames:
			credentials[current_uid] = {'uname':uname.decode('utf-8'),'avurl':avurl}
		else:
			credentials[current_uid] = {'uname':uname,'avurl':avurl}
		if uname and avurl:
			pass
		elif avurl:
			# log that this user's uname has to be retrieved
			uncollected_unames.append(current_uid)
		elif uname:
			# log that this user's avurl has to be retrieved
			uncollected_avurls.append(current_uid)
		else:
			# log that this user's both credential have to be retrieved
			uncollected_unames.append(current_uid)
			uncollected_avurls.append(current_uid)
		counter += 1
	collected_unames, collected_avurls = [], []
	if uncollected_unames:
		collected_unames = User.objects.filter(id__in=uncollected_unames).values('id','username')
		pipeline2 = my_server.pipeline()
		for uname in collected_unames:
			user_id = uname['id']
			hash_name = 'uname:'+str(user_id)
			credentials[user_id]['uname'] = uname['username']
			pipeline2.hset(hash_name, 'uname', uname['username'])
			pipeline2.expire(hash_name,ONE_DAY)
		pipeline2.execute()
	if uncollected_avurls:
		collected_avurls = UserProfile.objects.filter(user_id__in=uncollected_avurls).values('user_id','avatar')
		pipeline3 = my_server.pipeline()
		for avurl in collected_avurls:
			user_id = avurl['user_id']
			hash_name = 'uname:'+str(user_id)
			if not avurl['avatar']:
				avurl['avatar'] = 'empty'
			credentials[user_id]['avurl'] = avurl['avatar']
			pipeline3.hset(hash_name, 'avurl', avurl['avatar'])
			pipeline3.expire(hash_name,ONE_DAY)
		pipeline3.execute()
	return credentials


def retrieve_bulk_avurls(user_ids):
	"""
	Retrieves avatar_urls in bulk for a given list of user_ids
	"""
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for user_id in user_ids:
		pipeline1.hget('uname:'+str(user_id),'avurl')
	avatars_wip = pipeline1.execute()
	counter = 0
	avatars, uncollected_avurls = {}, []
	for avatar in avatars_wip:
		user_id = int(user_ids[counter])
		if avatar:
			avatars[user_id] = avatar
		else:
			uncollected_avurls.append(user_id)
		counter += 1
	if uncollected_avurls:
		collected_avurls = UserProfile.objects.filter(user_id__in=uncollected_avurls).values('user_id','avatar')
		pipeline2 = my_server.pipeline()
		for avurl in collected_avurls:
			user_id = avurl['user_id']
			hash_name = 'uname:'+str(user_id)
			if not avurl['avatar']:
				avurl['avatar'] = 'empty'
			avatars[user_id] = avurl['avatar']
			pipeline2.hset(hash_name,'avurl',avurl['avatar'])
			pipeline2.expire(hash_name,ONE_DAY)
		pipeline2.execute()
	return avatars


def retrieve_bulk_unames(user_ids, decode=False):
	"""
	Returns usernames in bulk, in id-username dictionary format
	"""
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for user_id in user_ids:
		pipeline1.hget('uname:'+str(user_id),'uname')
	usernames_wip = pipeline1.execute()
	counter = 0
	usernames, uncollected_uname_ids = {}, []
	for username in usernames_wip:
		id_ = int(user_ids[counter])
		if username:
			if decode:
				usernames[id_] = username.decode('utf-8')
			else:
				usernames[id_] = username
		else:
			usernames[id_] = ''
			uncollected_uname_ids.append(id_)
		counter += 1
	if uncollected_uname_ids:
		residual_unames = dict(User.objects.filter(id__in=uncollected_uname_ids).values_list('id','username'))
		pipeline2 = my_server.pipeline()
		for key in residual_unames:
			usernames[key], hash_name = residual_unames[key], 'uname:'+str(key)
			pipeline2.hset(hash_name,'uname',residual_unames[key])
			pipeline2.expire(hash_name,ONE_DAY)
		pipeline2.execute()
	return usernames



def retrieve_uname(user_id,decode=False):
	"""
	Returns user's nickname
	"""
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = 'uname:'+str(user_id)
	username = my_server.hget(hash_name,'uname')
	if username:
		if decode:
			return username.decode('utf-8')
		else:
			return username
	else:
		username = User.objects.filter(id=user_id).values_list('username',flat=True)[0]
		pipeline1 = my_server.pipeline()
		pipeline1.hset(hash_name,'uname',username)
		pipeline1.expire(hash_name,ONE_DAY)
		pipeline1.execute()
		return username


def retrieve_credentials(user_id,decode_uname=False):
	"""
	Returns username and avatar_url for given user_id
	"""
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = 'uname:'+str(user_id)
	username, avurl = my_server.hmget(hash_name,'uname','avurl')
	if username and avurl:
		if decode_uname:
			return username.decode('utf-8'),avurl
		else:
			return username, avurl
	elif username:
		avurl = UserProfile.objects.filter(user_id=user_id).values_list('avatar',flat=True)[0]
		if not avurl:
			avurl = 'empty'
		pipeline1 = my_server.pipeline()
		pipeline1.hset(hash_name,'avurl',avurl)
		pipeline1.expire(hash_name,ONE_DAY)
		pipeline1.execute()
		if decode_uname:
			return username.decode('utf-8'),avurl
		else:
			return username, avurl
	elif avurl:
		username = User.objects.filter(id=user_id).values_list('username',flat=True)[0]
		pipeline1 = my_server.pipeline()
		pipeline1.hset(hash_name,'uname',username)
		pipeline1.expire(hash_name,ONE_DAY)
		pipeline1.execute()
		return username, avurl
	else:
		username = User.objects.filter(id=user_id).values_list('username',flat=True)[0]
		avurl = UserProfile.objects.filter(user_id=user_id).values_list('avatar',flat=True)[0]
		if not avurl:
			avurl = 'empty'
		mapping = {'uname':username,'avurl':avurl}
		pipeline1 = my_server.pipeline()
		pipeline1.hmset(hash_name,mapping)
		pipeline1.expire(hash_name,ONE_DAY)
		pipeline1.execute()
		return username, avurl


def retrieve_user_id(username):
	"""
	Returns user's user_id (for a given username)
	"""
	key = 'user_id:'+username
	my_server = redis.Redis(connection_pool=POOL)
	user_id = my_server.get(key)
	if user_id:
		my_server.expire(key,THREE_DAYS)# extend lease for 3 days
		return user_id
	else:
		try:
			user_id = User.objects.filter(username=username).values_list('id',flat=True)[0]
		except IndexError:
			return None
		my_server.setex(key,user_id,ONE_DAY)
		return str(user_id)


def retrieve_avurl(user_id):
	"""
	Returns user's avatar_url
	"""
	hash_name = 'uname:'+str(user_id)
	my_server = redis.Redis(connection_pool=POOL)
	avurl = my_server.hget(hash_name,'avurl')
	if not avurl:
		avurl = UserProfile.objects.filter(user_id=user_id).values_list('avatar',flat=True)[0]
		if not avurl:
			avurl = 'empty'
		pipeline1 = my_server.pipeline()
		pipeline1.hset(hash_name,'avurl',avurl)
		pipeline1.expire(hash_name,ONE_DAY)
		pipeline1.execute()
	return avurl


def invalidate_avurl(user_id,set_rate_limit=None):
	"""
	Invalidate cached avatar_url if user uploads new avatar

	If set_rate_limit is True, a rate limit is imposed on uploading a new avatar
	"""
	my_server = redis.Redis(connection_pool=POOL)
	user_id = str(user_id)
	my_server.hdel('uname:'+user_id,'avurl')
	if set_rate_limit:
		my_server.setex('aurl:'+user_id,1,THREE_MINS)


def get_aurl(user_id):
	"""
	Retrieves the status of avatar uploading rate limit
	"""
	return redis.Redis(connection_pool=POOL).ttl('aurl:'+str(user_id))


#####################Retention Logger#####################
def log_retention(server_instance, user_id):
	time_now = time.time()
	if server_instance.exists("user_times:"+user_id):
		if time_now - float(server_instance.lrange("user_times:"+user_id,0,0)[0]) > TEN_MINS:
			server_instance.lpush("user_times:"+user_id,time_now)
			server_instance.sadd("logged_users",user_id)
	else:
		# contains a user's times of browsing Damadam
		server_instance.lpush("user_times:"+user_id,time_now)
		# contains all user_ids that have ever been logged
		server_instance.sadd("logged_users",user_id)

def retrieve_retention_ids():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.smembers("logged_users")

def retrieve_retention_data(user_ids):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for id_ in user_ids:
		pipeline1.lrange("user_times:"+id_,0,-1)
	result1 = pipeline1.execute()
	user_times = []
	counter = 0
	for id_ in user_ids:
		user_times.append((id_,result1[counter]))
		counter += 1
	return user_times

# def reduce_retention_data():
	"""
	to delete, get ids of really old "last_active"
	dates from session table in DB (to ensure it's 
	an old user). Then delete those "user_times"+str(user_id)
	"""

#######################Whose Online#######################


def expire_online_users():
	"""
	Expires online_users from tasks.py
	"""
	redis.Redis(connection_pool=POOL).zremrangebyscore("online_users",'-inf','('+str(time.time()-TEN_MINS))



def set_online_users(user_id,user_ip):
	"""
	Invoked from WhoseOnline.py middleware
	"""
	pipeline1 = redis.Redis(connection_pool=POOL).pipeline()
	pipeline1.zadd("online_users",user_id+":"+user_ip,time.time())
	pipeline1.setex("lip:"+user_id,user_ip,FIVE_MINS)
	pipeline1.execute()
	############ logging user retention ############
	# if random.random() < 0.45:
	# 	log_retention(my_server,user_id)


def get_recent_online():
	"""
	Invoked by tasks.py to show whoever is online in OnlineKon
	"""
	sorted_set = "online_users"
	ten_mins_ago = time.time() - TEN_MINS
	online_users = redis.Redis(connection_pool=POOL).zrangebyscore(sorted_set,ten_mins_ago,'+inf')
	online_ids = []
	for user in online_users:
		online_ids.append(user.split(":",1)[0])
	return online_ids


######################################## Detect Clones of User ID ########################################


def get_clones(user_id):
	"""
	Invoked in views.py to show possible clones of users
	"""
	latest_user_ip = "lip:"+str(user_id) #latest ip of user with 'user_id'
	my_server = redis.Redis(connection_pool=POOL)
	user_ip = my_server.get(latest_user_ip)
	if user_ip:
		clones = []
		five_mins_ago = time.time() - FIVE_MINS
		online_users = my_server.zrangebyscore("online_users",five_mins_ago,'+inf')
		for user in online_users:
			if user_ip == user.split(":",1)[1]:
				clones.append(user.split(":",1)[0])
		return clones
	else:
		return None

# def set_site_ban(user_id):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	user_ban = "ub:"+str(user_id) # banning user's ip from logging into website
# 	my_server.set(user_ban,1)
# 	my_server.expire(user_ban,ONE_HOUR)


#########################################################

#calculating installment amount for mobile devices
def get_historical_calcs(base_price=None, time_period_in_months=None, monthly_installment=None, ending_value=None):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	if base_price is None:
		id_ = my_server.get("historical_calcs")
		if id_ is not None:
			for x in range(1,(int(id_)+1)):
				pipeline1.hgetall("cd:"+str(x))
			return pipeline1.execute()
		else:
			return None
	else:
		id_ = my_server.incr("historical_calcs")
		calc_details = "cd:"+str(id_)
		mapping = {'id':id_,'bp':base_price,'tpim':time_period_in_months,'mi':monthly_installment,'ev':ending_value, 't':time.time()}
		my_server.hmset(calc_details,mapping)
		for x in range(1,(id_+1)):
			pipeline1.hgetall("cd:"+str(x))
		return pipeline1.execute()

#########################################################

def save_ad_desc(text, price, user_id,username):
	my_server = redis.Redis(connection_pool=POOL)
	mapping = {'uid':user_id, 'nick':username, 'desc':text,'price':price}
	my_server.lpush("ad_desc",mapping)

#########################################################

def save_careem_data(careem_data):
	my_server = redis.Redis(connection_pool=POOL)
	if my_server.zscore("careem_applicant_nums",careem_data["phonenumber"]):
		# it already exists
		return False
	else:
		# it does not exist
		pipeline1 = my_server.pipeline()
		pipeline1.hmset("cad:"+str(careem_data['phonenumber']),careem_data)
		pipeline1.zadd('careem_applicant_nums',careem_data['phonenumber'],time.time())
		pipeline1.zadd('careem_applicant_nums_live',careem_data['phonenumber'],time.time())
		pipeline1.execute()

		return True

def export_careem_data():
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	user = my_server.zcard("careem_applicant_nums_live")
	if user == 0:
		return False
	else:
		nums = my_server.zrange("careem_applicant_nums_live",0,-1)
		pipeline1 = my_server.pipeline()
		for num in nums:
			pipeline1.hgetall('cad:'+num)
		result1 = pipeline1.execute()
		return result1

def del_careem_data():
	my_server = redis.Redis(connection_pool=POOL)
	my_server.delete("careem_applicant_nums_live")


##################################################Mobile_Shop


def log_buyer_form_err(error_data):
	my_server = redis.Redis(connection_pool=POOL)
	error_id = get_error_id()
	key_name = "error_data:"+str(error_id)
	pipeline1 = my_server.pipeline()
	pipeline1.hmset(key_name,error_data)
	#pipeline1.expire(key_name,TWELVE_HOURS)
	pipeline1.execute()
	return True

def get_error_id():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.incr("ms_error_id")

def save_order_data(order_data):
	my_server = redis.Redis(connection_pool=POOL)
	key_name = "order_data:"+str(order_data['user_id'])
	pipeline1 = my_server.pipeline()
	pipeline1.hmset(key_name,order_data)
	pipeline1.expire(key_name,TWELVE_HOURS)
	pipeline1.execute()
	return True

def save_query_data(query_data):
	my_server = redis.Redis(connection_pool=POOL)
	key_name = "querydata:"+str(query_data['user_id'])
	pipeline1 = my_server.pipeline()
	pipeline1.hmset(key_name,query_data)
	pipeline1.sadd('queryusers',query_data['user_id'])
#	pipeline1.expire(key_name,TWELVE_HOURS)
	pipeline1.execute()
	return True

def delete_query(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	my_server.srem("queryusers",user_id)
	my_server.delete("querydata:"+str(user_id))
	pipeline1.execute()
	return {}


def place_order(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	order_data = False
	order_data = get_temp_order_data(user_id)
	order_id = get_order_id()
	order_data['order_id'] = order_id
	pipeline1.zadd('ordersinprocess',user_id,order_id)
	# after a few months, export this to excel and clean the list (it takes up needless space)
	pipeline1.hmset("placedorders:"+str(order_id),order_data)
	pipeline1.execute()
	return order_data

def delete_order(order_id,user_id):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	# after a few months, export this to excel and clean the list (it takes up needless space)
	my_server.zrem("ordersinprocess",user_id)
	my_server.delete("placedorders:"+str(order_id))
	pipeline1.execute()
	return {}





def get_temp_order_data(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	temp_storage = "order_data:"+str(user_id)
	if my_server.exists(temp_storage):
		order_details = my_server.hgetall("order_data:"+str(user_id))
#		my_server.delete("order_data:"+str(user_id))
		return order_details
	else:
		return {}

def check_orders_processing(user_id):
	user = redis.Redis(connection_pool=POOL).zscore('ordersinprocess',user_id)
	if user == None:
		return False
	else:
		return True

def get_order_id():
	return redis.Redis(connection_pool=POOL).incr("order_id")

def get_total_orders():
	return redis.Redis(connection_pool=POOL).get("order_id")

def show_new_orders():
	total_orders = get_total_orders()
	if total_orders <1:
		return False
	else:
		my_server = redis.Redis(connection_pool=POOL)
		pipeline1 = my_server.pipeline()
		num = 0
		
		while num <= int(total_orders):
			temp_storage = "placedorders:"+str(num)
			if my_server.exists(temp_storage):
				pipeline1.hgetall('placedorders:'+str(num))
			num = num + 1
		orders = pipeline1.execute()
		return orders


def show_new_queries():
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	users = my_server.smembers("queryusers")
	if users == 0:
		return []
	else:
		pipeline1 = my_server.pipeline()
		for obj in users:
			pipeline1.hgetall('querydata:'+obj)
		result1 = pipeline1.execute()
		return result1



'''
####################
M_S Deprecated Key Names
query_data now querydata
query_users now queryusers
orders_in_process now ordersinprocess
placed_orders now placedorders

####################
'''

############ Rate limiting flooding and spamming ############

def is_limited(user_id, section, with_reason = False):
	"""
	"""
	if section == 'home':
		key = "rlfh:"+str(user_id)
	elif section == 'pub_grp':
		key = "rlfpg:"+str(user_id)
	elif section == 'prv_grp':
		key = "rlfpvg:"+str(user_id)
	elif section == 'pht_comm':
		key = "rlfpc:"+str(user_id)
	elif section == 'home_rep':
		key = "rlfhr:"+str(user_id)
	else:
		return False
	my_server = redis.Redis(connection_pool=POOL)
	if with_reason:
		ttl = my_server.ttl(key)
		if ttl > 0:
			reason = my_server.get(key)
			return ttl, reason
		else:
			return 0, None
	else:
		return my_server.ttl(key)

def rate_limit_user(user_id,section,level,ban_reason,my_server=None):
	"""
	Setting blocking rate limits on abusive users on a section of the website

	Level relates to severity of block limit
	1 - lowest (7 mins)
	2 - low (30 mins)
	3 - medium (2 hours)
	4 - med-high (8 hours)
	5 - high (24 hours)
	6 - severe (3 days)
	7 - hardcore (7 days)
	8 - jackpot (30 days)
	"""
	if section == 'home':
		rate_limit_key = "rlfh:"+str(user_id)
	elif section == 'pub_grp':
		rate_limit_key = "rlfpg:"+str(user_id)
	elif section == 'prv_grp':
		rate_limit_key = "rlfpvg:"+str(user_id)
	elif section == 'pht_comm':
		rate_limit_key = "rlfpc:"+str(user_id)
	elif section == 'home_rep':
		rate_limit_key = "rlfhr:"+str(user_id)
	if not my_server:
		my_server = redis.Redis(connection_pool=POOL)
	try:
		my_server.setex(rate_limit_key,ban_reason,RATELIMIT_TTL[level])
		return True
	except KeyError:
		my_server.setex(rate_limit_key,ban_reason,TWENTY_MINS)
		return False

# 1) revert log_input_rate in tasks.py (done)
# 2) revert function definition of log_input_rate in redis4 (done)
# 3) remove pipeline1.execute(key+":logger",text) from log_input_rate (done)
# 4) remove log_rate_limited_conversation() from log_input_rate (done)
# 5) remove function for log_rate_limited_conversation() in redis4 (done)
# 6) remove function called report_rate_limited_conversation() in redis4 (done)
# 7) remove logger url (and view import) from urls_maint.py (done)
# 8) remove reporting view (called rate_limit_logging_report) from end of maint_views (done)
# 9) remove the import for report_rate_limited_conversation() from maint_views (done)
# 10) remove get_section_string() from redis4 (done)

# def report_rate_limited_conversation():
# 	"""
# 	Extracts all rate limited conversations
# 	"""
# 	import csv,ast
# 	my_server = redis.Redis(connection_pool=POOL)
# 	super_ = my_server.lrange("rate_limited_convos:super",0,-1)
# 	normal_ = my_server.lrange("rate_limited_convos:normal",0,-1)
# 	lazy_ = my_server.lrange("rate_limited_convos:lazy",0,-1)
# 	result = [(super_,'super_'),(normal_,'normal_'),(lazy_,'lazy_')]
# 	for logs,log_type in result:
# 		filename = 'ratelimited_convos_'+log_type+str(int(time.time()))+'.csv'
# 		with open(filename,'wb') as f:
# 			wtr = csv.writer(f)
# 			columns = ["Type","Section","#","Conversation"]
# 			wtr.writerow(columns) # writing the columns
# 			num = 0
# 			for payload in logs:
# 				num += 1
# 				payload = ast.literal_eval(payload)
# 				which_section = payload[0]
# 				for string in payload[1]:
# 					type_=log_type
# 					sec=which_section
# 					conv_num=num
# 					conversation=string
# 					to_write = [type_,sec,conv_num,conversation]	
# 					wtr.writerows([to_write])


# def get_section_string(key):
# 	try:
# 		string = key[:2]
# 	except TypeError:
# 		string = 'undef'
# 	if string == 'hi':
# 		return 'home_post'
# 	elif string == 'pg':
# 		return 'public_group'
# 	elif string == 'pv':
# 		return 'private_group'
# 	elif string == 'pc':
# 		return 'photo_comment'
# 	elif string == 'hr':
# 		return 'home_reply'
# 	else:
# 		return 'undefined'	

# def log_rate_limited_conversation(convo_key, severity):
# 	"""
# 	logger for rate limited conversation strings
# 	"""
# 	my_server = redis.Redis(connection_pool=POOL)
# 	which_section = get_section_string(convo_key)
# 	if severity == 'super':
# 		my_server.lpush("rate_limited_convos:super",[which_section,my_server.lrange(convo_key,0,-1)])
# 	elif severity == 'normal':
# 		my_server.lpush("rate_limited_convos:normal",[which_section,my_server.lrange(convo_key,0,-1)])
# 	else:
# 		my_server.lpush("rate_limited_convos:lazy",[which_section,my_server.lrange(convo_key,0,-1)])


# def log_input_rate(section,user_id,time_now):
def log_input_rate(section,user_id,time_now,text=None):
	"""
	Keeps check of writing rates to rate limit abusive users
	"""
	my_server = redis.Redis(connection_pool=POOL)
	if section == 'home':
		key = "hir:"+str(user_id)
	elif section == 'pub_grp':
		key = "pgir:"+str(user_id)	
	elif section == 'prv_grp':
		key = "pvgir:"+str(user_id)
	elif section == 'pht_comm':
		key = "pcir:"+str(user_id)
	elif section == 'home_rep':
		key = "hrir:"+str(user_id)	
	pipeline1 = my_server.pipeline()
	pipeline1.lpush(key,time_now)
	pipeline1.expire(key,ONE_MIN)
	#### remove ####
	# pipeline1.lpush(key+":logger",text)
	# pipeline1.expire(key+":logger",ONE_MIN)
	#### remove ####
	pipeline1.execute()
	####################################
	all_str_values = my_server.lrange(key,0,-1)
	total_inputs = len(all_str_values)
	if total_inputs > 7:
		all_values = map(float, all_str_values)
		sum_of_differences = 0
		for s, t in zip(all_values, all_values[1:]):
			sum_of_differences += t - s
		avg_time_taken_between_sentences = abs(sum_of_differences)/(total_inputs-1)
		if avg_time_taken_between_sentences < SUPER_FLOODING_THRESHOLD:
			rate_limit_user(user_id=user_id,section=section,level='2',ban_reason=BAN_REASON['flooding'],my_server=my_server)
			# log_rate_limited_conversation(key+":logger",'super')
		elif avg_time_taken_between_sentences < FLOODING_THRESHOLD:
			rate_limit_user(user_id=user_id,section=section,level='1',ban_reason=BAN_REASON['flooding'],my_server=my_server)
			# log_rate_limited_conversation(key+":logger",'normal')
		elif avg_time_taken_between_sentences < LAZY_FLOODING_THRESHOLD:
			rate_limit_user(user_id=user_id,section=section,level='0',ban_reason=BAN_REASON['flooding'],my_server=my_server)
			# log_rate_limited_conversation(key+":logger",'lazy')
		else:
			my_server.ltrim(key,0,6)
			#### remove ####
			# my_server.ltrim(key+":logger",0,6)

def log_input_text(section, section_id,text,user_id):
	"""
	Logs previous 4 sentences of each section
	"""
	my_server = redis.Redis(connection_pool=POOL)
	if section == 'home':
		key = "hit:"+str(user_id)+":"+str(section_id)
	elif section == 'pub_grp':
		key = "pgit:"+str(user_id)+":"+str(section_id)	
	elif section == 'prv_grp':
		key = "pvgit:"+str(user_id)+":"+str(section_id)	
	elif section == 'pht_comm':
		key = "pcit:"+str(user_id)+":"+str(section_id)
	elif section == 'home_rep':
		key = "hrit:"+str(user_id)+":"+str(section_id)
	my_server.lpush(key,text)
	my_server.ltrim(key,0,3) # keeping previous 4 sentences
	my_server.expire(key,TEN_MINS)


def retrieve_previous_msgs(section, section_id,user_id):
	"""
	retrieve previous messages stored for a certain section_id
	"""	
	if section == 'home':
		key = "hit:"+str(user_id)+":"+str(section_id)
	elif section == 'pub_grp':
		key = "pgit:"+str(user_id)+":"+str(section_id)	
	elif section == 'prv_grp':
		key = "pvgit:"+str(user_id)+":"+str(section_id)	
	elif section == 'pht_comm':
		key = "pcit:"+str(user_id)+":"+str(section_id)
	elif section == 'home_rep':
		key = "hrit:"+str(user_id)+":"+str(section_id)
	return redis.Redis(connection_pool=POOL).lrange(key,0,-1)


############################ Ratelimiting short messages ###############################

def log_short_message(user_id,section,obj_id):
	short_message = "sm:"+str(user_id)+":"+section+":"+str(obj_id)
	my_server = redis.Redis(connection_pool=POOL)
	my_server.incr(short_message)
	my_server.expire(short_message,THREE_MINS)

def many_short_messages(user_id,section,obj_id):
	"""
	Confirms if trail of short messages have already been left by the user on the given object
	"""
	short_message = "sm:"+str(user_id)+":"+section+":"+str(obj_id)
	my_server = redis.Redis(connection_pool=POOL)
	short_messages_so_far = my_server.get(short_message)
	if short_messages_so_far:
		if int(short_messages_so_far) > SHORT_MESSAGES_ALWD:
			my_server.expire(short_message,SEVEN_MINS) #renew block short messages for 7 mins
			return True
		else:
			False
	else:
		return False

################################################# Logging Sharing in Photos #################################################


def log_share(photo_id, photo_owner_id, sharer_id, share_type='undefined', origin=None):
	"""
	Logs image sharing attempts (via Whatsapp)
	
	1) If origin is 'user_albums', user is originating from user profiles
	1) If origin is 'fresh_photos', user is originating from fresh photos
	"""
	my_server = redis.Redis(connection_pool=POOL)
	if origin == 'user_albums':
		# log shared profiles
		if not my_server.get('as:'+photo_id+":"+str(sharer_id)):
			# this sharer hasn't shared this photo in the last 20 mins
			added = my_server.sadd('shared_user_albums_set',photo_id)
			if added == 1:
				my_server.lpush('shared_user_albums_list',photo_id)
				if my_server.llen('shared_user_albums_list') > SHARED_PHOTOS_CEILING:
					expiring_photo_ids = my_server.lrange('shared_user_albums_list', (SHARED_PHOTOS_CEILING-PHOTO_DELETION_BUFFER), -1)
					pipeline1 = my_server.pipeline()
					pipeline1.ltrim('shared_user_albums_list',0,(SHARED_PHOTOS_CEILING-PHOTO_DELETION_BUFFER-1))	
					pipeline1.zrem('sorted_user_albums_photos',*expiring_photo_ids)
					pipeline1.srem('shared_user_albums_set',*expiring_photo_ids)
					pipeline1.execute()
			my_server.zincrby('sorted_user_albums_photos',photo_id,amount=1)# query this when getting report of which photos were shared the most
			my_server.setex('as:'+photo_id+":"+str(sharer_id),'1',TWENTY_MINS)
	elif origin == 'fresh_photos':
		# log shared photos
		if not my_server.get('as:'+photo_id+":"+str(sharer_id)):
			# this sharer hasn't shared this photo in the last 20 mins
			added = my_server.sadd('shared_public_photos_set',photo_id)
			if added == 1:
				my_server.lpush('shared_public_photos_list',photo_id)
				if my_server.llen('shared_public_photos_list') > SHARED_PHOTOS_CEILING:
					expiring_photo_ids = my_server.lrange('shared_public_photos_list', (SHARED_PHOTOS_CEILING-PHOTO_DELETION_BUFFER), -1)
					pipeline1 = my_server.pipeline()
					pipeline1.ltrim('shared_public_photos_list',0,(SHARED_PHOTOS_CEILING-PHOTO_DELETION_BUFFER-1))
					pipeline1.zrem('sorted_shared_public_photos',*expiring_photo_ids)
					pipeline1.srem('shared_public_photos_set',*expiring_photo_ids)
					pipeline1.execute()
			my_server.zincrby('sorted_shared_public_photos',photo_id,amount=1)# query this when getting report of which photos were shared the most
			my_server.setex('as:'+photo_id+":"+str(sharer_id),'1',TWENTY_MINS)
	else:
		pass



def logging_sharing_metrics(sharer_id, photo_id, photo_owner_id, num_shares, sharing_time, group_ids):
	"""
	Logs metrics for photos shared internally (from public albums to personal groups)

	This is a separate functionality from sharing via Whatsapp
	"""
	sharer_id, num_shares, sharing_time = str(sharer_id), str(num_shares), str(sharing_time)
	key = "sp:"+photo_owner_id
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	
	# use this to calculate total shares in the last week, also total all_time shares (list resets if user inactive for two weeks)
	pipeline1.zadd(key,photo_id+":"+num_shares+":"+sharer_id+":"+sharing_time,sharing_time)
	pipeline1.expire(key,TWO_WEEKS)
	# can also give to each user: latest shared photo, most highly shared photo, and all other shared photos (alongwith num shares)

	# save the act of sharing in a global list as well, for our viewing
	pipeline1.lpush('shared_photos',photo_id+":"+num_shares+":"+photo_owner_id+":"+sharing_time)
	pipeline1.ltrim('shared_photos',0,500)

	pipeline1.execute()
	##################################### SHARER METRICS #####################################
	# one_month_ago = sharing_time - (60*60*24*30)
	# most proflific sharers of own content (remove those inactive for a month)
	# if photo_owner_id == sharer_id:
	# 	my_server.zadd('ocst',sharer_id,sharing_time)#'own content sharing time'
	# 	my_server.zincrby('ocsv',sharer_id,amount=num_shares)#'own content sharing volume'
	# 	expired_sharer_ids = my_server.zrangebyscore("ocst",'-inf',one_month_ago)
	# 	if expired_sharer_ids:
	# 		my_server.zrem('ocst',*expired_sharer_ids)
	# 		my_server.zrem('ocsv',*expired_sharer_ids)
	
	# most prolific sharers of others' content (remove those inactive for a month)
	# else:
	# 	my_server.zadd('cst',sharer_id,sharing_time)#'content sharing time'
	# 	my_server.zincrby('csv',sharer_id,amount=num_shares)#'content sharing volume'
	# 	expired_sharer_ids = my_server.zrangebyscore("cst",'-inf',one_month_ago)
	# 	if expired_sharer_ids:
	# 		my_server.zrem('cst',*expired_sharer_ids)
	# 		my_server.zrem('csv',*expired_sharer_ids)
	
	# most prolific sharers who influence the most number of people. Can use formula volume_shared^(simpson_diversity_index) to calculate 'influencer score'
	# volume_shared is simply total number of shares (it counts each individual share as 1)
	# simpson_diversity_index is here: https://www.youtube.com/watch?v=zxzwvWDeTT8
	

# def log_photo_attention_from_fresh(photo_id, att_giver, photo_owner_id, action, vote_value):
# 	"""
# 	Maintains list of photos that are 'trending' via actvity from fresh photos
	
# 	Note: 'action' may be 'photo_vote' or 'photo_comment'
# 	"""
# 	my_server = redis.Redis(connection_pool=POOL)
# 	if action == 'photo_vote':
# 		if vote_value == '1':
# 			pass
# 		elif vote_value == '-1':
# 			pass
# 		else:
# 			pass

def cache_photo_share_data(json_data,user_id):
	"""
	Caches photo sharing data of given user_id for twenty mins
	"""
	redis.Redis(connection_pool=POOL).setex('phd:'+user_id,json_data,TWENTY_MINS)


def retrieve_fresh_photo_shares_or_cached_data(user_id):
	"""
	Returns shared photos of user_id
	"""
	my_server = redis.Redis(connection_pool=POOL)
	cached_photo_data = my_server.get('phd:'+user_id)
	if cached_photo_data:
		return json.loads(cached_photo_data), True
	else:
		return my_server.zrange("sp:"+user_id,0,-1), False


def logging_profile_view(visitor_id,star_id,viewing_time):
	"""
	Logs profile view if a visitor visits

	Only last 24 hours are preserved
	Ensures self visits don't count
	Ensures repeat visits don't count
	"""
	star_id = str(star_id)
	one_day_ago = viewing_time - ONE_DAY
	viewing_time = str(viewing_time)
	visitor_id = str(visitor_id)
	key = "vb:"+star_id+":"+visitor_id
	my_server = redis.Redis(connection_pool=POOL)
	if not my_server.get(key):
		# can log visit
		sorted_set = 'pf:'+star_id
		my_server.zremrangebyscore(sorted_set,'-inf',one_day_ago)#purging old data
		my_server.zadd(sorted_set,visitor_id+":"+viewing_time,viewing_time)
		my_server.expire(sorted_set,ONE_DAY)#this expires if no new views appear for 24 hours
		my_server.setex(key,'1',THIRTY_MINS)

########################################### Gathering Metrics for Personal Groups ###########################################

def increment_convo_counter(group_id, writer_id, group_type=None):
	"""
	Logs conversation quantity in personal groups and private mehfils

	Helps answer questions such as:
	1) What are avg number of chats produced per type of chat?
	2) What are avg number of switchovers produced per type of chat?
	"""
	if group_type:
		last_interaction_in_group = "lig_"+group_type+":"+group_id
		my_server = redis.Redis(connection_pool=POOL)
		lwid = my_server.getset(last_interaction_in_group,writer_id)
		if lwid:
			interaction_type = 'ch' if lwid == str(writer_id) else 'both'
		else:
			interaction_type = 'ch'
		if interaction_type == 'ch':
			# this logs normal chat
			my_server.zincrby(group_type+"_ch",group_id,amount=1)
		elif interaction_type == 'both':
			# this logs switchover, and normal chat
			my_server.zincrby(group_type+"_sw",group_id,amount=1)
			my_server.zincrby(group_type+"_ch",group_id,amount=1)
		my_server.expire(last_interaction_in_group,ONE_DAY)


def increment_session(group_id, user_id, group_type=None):
	"""
	Increments unique sessions per group per user

	Helps answer questions such as:
	1) What are avg number of sessions per type of chat
	2) What are median number of sessions per type of chat
	3) Calculate correlation between number of sessions and number of switchovers
	4) Calculate coorelation between number of sessions and number of chats
	"""
	my_server, user_id = redis.Redis(connection_pool=POOL), str(user_id)
	if not my_server.get("gs_"+group_type+":"+group_id+":"+user_id):
		# create new session key for the user for this group
		now = datetime.now()
		secs_till_midnight = ((24 - now.hour - 1) * 60 * 60) + ((60 - now.minute - 1) * 60) + (60 - now.second)
		my_server.setex("gs_"+group_type+":"+group_id+":"+user_id,group_id,secs_till_midnight)
		# increment session counter
		my_server.zincrby(group_type+"_sess",group_id+":"+user_id,amount=1)


def track_p2p_sms(sent_by_id, sent_to_id, sending_time):
	"""
	Log which user sent whom an SMS at what time (to entice them to come to Damadam)
	
	Helps answer questions such as:
	1) Number of SMSes generated per chat/per day/per user
	"""
	my_server = redis.Redis(connection_pool=POOL)
	my_server.lpush("p2p_sms",str(sent_by_id)+":"+sent_to_id+":"+str(sending_time))#llen of list reveals number of SMSes sent
	# create 'red carpet' for target user
	my_server.setex("rc:"+sent_to_id,sending_time,ONE_DAY)


def check_p2p_sms(user_id):
	"""
	Logs data in case you were sent an SMS by a friend (asking you to return to Damadam)
	
	Helps answer questions such as:
	1) Number of people responding to SMSes
	2) How soon does an average responder take to return to the chat from which SMS was sent?
	"""
	my_server, user_id = redis.Redis(connection_pool=POOL), str(user_id)
	sms_sent_at = my_server.get("rc:"+user_id)
	if sms_sent_at:
		my_server.delete("rc:"+user_id)
		time_passed_since_sms = time.time() - float(sms_sent_at)
		# log returned user and time taken since sending of SMS
		my_server.lpush("sms_eft",user_id+":"+str(time_passed_since_sms))


def log_personal_group_exit_or_delete(group_id, exit_by_id=None, action_type=None):
	"""
	Logging time of personal group exit or deletion

	Helps answer questions such as:
	1) How many private chats are create (net basis) week-over-week?
	2) What is the average life-time of a private chat?
	"""
	my_server = redis.Redis(connection_pool=POOL)
	if action_type == 'exit':
		my_server.zadd("exits",group_id+":"+exit_by_id,time.time())
	else:
		# group_id is a list of group_ids
		time_now = time.time()
		groups = []
		for gid in group_id:
			groups.append(gid)
			groups.append(time_now)
		if groups:
			if action_type == 'del_exit':
				my_server.zadd("del_after_exit",*groups)
			elif action_type == 'del_idle':
				my_server.zadd("del_after_idle",*groups)


def purge_exit_list(group_id, user_id):
	"""
	Purge a value from 'exits' (called when a user rejoins a group after exiting it)
	"""
	redis.Redis(connection_pool=POOL).zrem("exits",group_id+":"+str(user_id))


########################################### Reporting Metrics for Personal Groups ###########################################

def avg_sessions_per_type():
	"""
	Retrieves session information for personal groups

	1) What are avg number of sessions per type of chat
	2) What are median number of sessions per type of chat
	"""
	my_server = redis.Redis(connection_pool=POOL)
	pgs_sampled = my_server.get('pgs_sampled_for_sess')
	if pgs_sampled:
		results = my_server.mget(['pms_sampled_for_sess','med_sess_per_user_per_pg','med_sess_per_user_per_pm','avg_sess_per_user_per_pg',\
			'avg_sess_per_user_per_pm','avg_users_per_pm','med_users_per_pm','avg_users_per_pg','med_users_per_pg','avg_sess_per_user_per_two_user_pm',\
			'med_sess_per_user_per_two_user_pm','total_two_user_pms','avg_users_per_two_user_pm','med_users_per_two_user_pm'])
		return pgs_sampled, results[0], results[1], results[2], results[3], results[4], results[5], results[6], results[7], results[8], results[9],\
		results[10],results[11], results[12], results[13]
	else:
		pg_data = my_server.zrange('pg_sess',0,-1,withscores=True)
		pg_sample_size = len(pg_data)
		pg_med_idx = int(pg_sample_size/2)

		pm_data = my_server.zrange('pm_sess',0,-1,withscores=True)
		pm_sample_size = len(pm_data)
		pm_med_idx = int(pm_sample_size/2)

		# data contains <group_id>:<user_id> tuples
		pg_sessions, all_pgs, all_pg_users = 0, set(), {}
		for tup in pg_data:
			pg_sessions += int(tup[1])
			payload = tup[0].split(":")
			group_id, user_id = payload[0], payload[1]
			all_pgs.add(group_id)
			all_pg_users[group_id] = {}
		pgs_sampled = len(all_pgs)
		for tup in pg_data:
			payload = tup[0].split(":")
			group_id, user_id = payload[0], payload[1]
			all_pg_users[group_id].update({user_id:'user_id'})
		total_pg_users, pg_users_set = 0, []
		for key, value in all_pg_users.iteritems():
			num_users_in_group = len(value)
			pg_users_set.append(num_users_in_group)
			total_pg_users += num_users_in_group
		# finding median
		array_pg = sorted(pg_users_set)
		half, odd = divmod(len(array_pg), 2)
		if odd:
			med_users_per_pg = array_pg[half]
		else:
			med_users_per_pg = (array_pg[half - 1] + array_pg[half]) / 2.0

		# calculating pm data
		pm_sessions, all_pms, all_pm_users = 0, set(), {}
		for tup in pm_data:
			pm_sessions += int(tup[1])
			payload = tup[0].split(":")
			group_id, user_id = payload[0], payload[1]
			all_pms.add(group_id)
			all_pm_users[group_id] = {}
		pms_sampled = len(all_pms)
		for tup in pm_data:
			payload = tup[0].split(":")
			group_id, user_id = payload[0], payload[1]
			all_pm_users[group_id].update({user_id:'user_id'})
		total_pm_users, pm_users_set, two_user_pms = 0, [], {}
		for key, value in all_pm_users.iteritems():
			num_users_in_group = len(value)
			pm_users_set.append(num_users_in_group)
			if num_users_in_group < 3:
				# retriving 2 user pms
				two_user_pms[key] = num_users_in_group
			total_pm_users += num_users_in_group
		
		# retrieving sessions for 2 user pms in {gid:num_sess} form
		two_user_pm_sess = {}
		for tup in pm_data:
			payload = tup[0].split(":")
			group_id, user_id = payload[0], payload[1]
			if group_id in two_user_pms:
				# it's a two person pm
				if group_id in two_user_pm_sess:
					# already entered data for 1 user
					num_sess = two_user_pm_sess[group_id]
					two_user_pm_sess[group_id] = num_sess + int(tup[1])
				else:
					two_user_pm_sess[group_id] = int(tup[1])

		# we now have two_user_pms {gid:num_users} and two_user_pm_sess {gid:num_sess}
		total_two_user_pm_sess, all_two_user_pm_sess = 0, []
		for key,value in two_user_pm_sess.iteritems():
			total_two_user_pm_sess += int(value)
			all_two_user_pm_sess.append(value)
		total_two_user_pm_users, all_two_user_pm_users = 0, []
		for key,value in two_user_pms.iteritems():
			total_two_user_pm_users += int(value)
			all_two_user_pm_users.append(value)
		avg_sess_per_user_per_two_user_pm = "{0:.2f}".format(float(total_two_user_pm_sess)/total_two_user_pm_users)
		sorted_sess = sorted(all_two_user_pm_sess)
		halved, is_odd = divmod(len(sorted_sess), 2)
		if is_odd:
			med_sess_per_user_per_two_user_pm = sorted_sess[halved]
		else:
			med_sess_per_user_per_two_user_pm = int(sorted_sess[halved - 1] + sorted_sess[halved]) / 2.0
		total_two_user_pms = len(two_user_pms)
		avg_users_per_two_user_pm = "{0:.2f}".format(float(total_two_user_pm_users)/total_two_user_pms)
		sorted_users = sorted(all_two_user_pm_users)
		bisect, isodd = divmod(len(sorted_users), 2)
		if isodd:
			med_users_per_two_user_pm = sorted_users[bisect]
		else:
			med_users_per_two_user_pm = int(sorted_users[bisect - 1] + sorted_users[bisect]) / 2.0
		# we now have avg and median sessions per user per two user pm

		# finding overall median
		array_pm = sorted(pm_users_set)
		half, odd = divmod(len(array_pm), 2)
		if odd:
			med_users_per_pm = array_pm[half]
		else:
			med_users_per_pm = (array_pm[half - 1] + array_pm[half]) / 2.0
		avg_sess_per_user_per_pg = "{0:.2f}".format(float(pg_sessions)/pg_sample_size)
		avg_sess_per_user_per_pm = "{0:.2f}".format(float(pm_sessions)/pm_sample_size)
		avg_users_per_pg = "{0:.2f}".format(float(total_pg_users)/pgs_sampled)
		avg_users_per_pm = "{0:.2f}".format(float(total_pm_users)/pms_sampled)
		med_sess_per_user_per_pg = my_server.zrange('pg_sess',pg_med_idx,pg_med_idx+1,withscores=True)[0]
		med_sess_per_user_per_pm = my_server.zrange('pm_sess',pm_med_idx,pm_med_idx+1,withscores=True)[0]

		# caching the results
		pipeline1 = my_server.pipeline()
		pipeline1.setex('pgs_sampled_for_sess',pgs_sampled,TEN_MINS)
		pipeline1.setex('pms_sampled_for_sess',pms_sampled,TEN_MINS)
		pipeline1.setex('avg_users_per_pm',avg_users_per_pm,TEN_MINS)
		pipeline1.setex('avg_users_per_pg',avg_users_per_pg,TEN_MINS)
		pipeline1.setex('med_users_per_pm',med_users_per_pm,TEN_MINS)
		pipeline1.setex('med_users_per_pg',med_users_per_pg,TEN_MINS)
		pipeline1.setex('total_two_user_pms',total_two_user_pms,TEN_MINS)
		pipeline1.setex('avg_sess_per_user_per_pg',avg_sess_per_user_per_pg,TEN_MINS)
		pipeline1.setex('avg_sess_per_user_per_pm',avg_sess_per_user_per_pm,TEN_MINS)
		pipeline1.setex('med_sess_per_user_per_pg',med_sess_per_user_per_pg,TEN_MINS)
		pipeline1.setex('med_sess_per_user_per_pm',med_sess_per_user_per_pm,TEN_MINS)
		pipeline1.setex('med_sess_per_user_per_pm',med_sess_per_user_per_pm,TEN_MINS)
		pipeline1.setex('avg_users_per_two_user_pm',avg_users_per_two_user_pm,TEN_MINS)
		pipeline1.setex('med_users_per_two_user_pm',med_users_per_two_user_pm,TEN_MINS)
		pipeline1.setex('avg_sess_per_user_per_two_user_pm',avg_sess_per_user_per_two_user_pm,TEN_MINS)
		pipeline1.setex('med_sess_per_user_per_two_user_pm',med_sess_per_user_per_two_user_pm,TEN_MINS)
		pipeline1.execute()
		return pgs_sampled, pms_sampled, med_sess_per_user_per_pg, med_sess_per_user_per_pm, avg_sess_per_user_per_pg, avg_sess_per_user_per_pm,\
		avg_users_per_pm, med_users_per_pm, avg_users_per_pg, med_users_per_pg, avg_sess_per_user_per_two_user_pm, med_sess_per_user_per_two_user_pm,\
		total_two_user_pms, avg_users_per_two_user_pm, med_users_per_two_user_pm
	"""
	Measure 2-user pms vs 2-user pgs
	Get 2-user pms and 2-user pgs from pm_sess and pg_sess (i.e. where sessions for 2 participants were logged)

	Get rid of less than 2 user cases to make it like for like
	"""

def avg_num_of_switchovers_per_type():
	"""
	What are avg number of chats produced per type of chat?
	"""
	my_server = redis.Redis(connection_pool=POOL)
	total_pms = my_server.get('total_pms_sw')
	if total_pms:
		results = my_server.mget(['median_pm_idx_sw','median_pm_tuple_sw','aggregate_pm_sws','avg_sw_per_pm','total_pgs_sw','median_pg_idx_sw',\
			'median_pg_tuple_sw','aggregate_pg_sws','avg_sw_per_pg'])
		return total_pms, results[0], results[1], results[2], results[3], results[4], results[5], results[6], results[7], results[8]
	else:
		pm_data = my_server.zrange('pm_sw',0,-1,withscores=True)
		total_pms = len(pm_data)
		median_pm_idx = int(total_pms/2)
		median_pm_tuple = my_server.zrange('pm_sw',median_pm_idx,median_pm_idx+1,withscores=True)[0]

		pg_data = my_server.zrange('pg_sw',0,-1,withscores=True)	
		total_pgs = len(pg_data)
		median_pg_idx = int(total_pgs/2)
		median_pg_tuple = my_server.zrange('pg_sw',median_pg_idx,median_pg_idx+1,withscores=True)[0]

		# data is list of (group_id,chat_num) type tuples
		aggregate_pm_sws, aggregate_pg_sws = 0, 0
		for tup in pm_data:
			aggregate_pm_sws += int(tup[1])
		for tup in pg_data:
			aggregate_pg_sws += int(tup[1])
		avg_sw_per_pm = "{0:.2f}".format(aggregate_pm_sws/float(total_pms))
		avg_sw_per_pg = "{0:.2f}".format(aggregate_pg_sws/float(total_pgs))

		# caching the results
		pipeline1 = my_server.pipeline()
		pipeline1.setex('total_pms_sw',total_pms,TEN_MINS)
		pipeline1.setex('median_pm_idx_sw',median_pm_idx,TEN_MINS)
		pipeline1.setex('median_pm_tuple_sw',median_pm_tuple,TEN_MINS)
		pipeline1.setex('aggregate_pm_sws',aggregate_pm_sws,TEN_MINS)
		pipeline1.setex('avg_sw_per_pm',avg_sw_per_pm,TEN_MINS)
		pipeline1.setex('total_pgs_sw',total_pgs,TEN_MINS)
		pipeline1.setex('median_pg_idx_sw',median_pg_idx,TEN_MINS)
		pipeline1.setex('median_pg_tuple_sw',median_pg_tuple,TEN_MINS)
		pipeline1.setex('aggregate_pg_sws',aggregate_pg_sws,TEN_MINS)
		pipeline1.setex('avg_sw_per_pg',avg_sw_per_pg,TEN_MINS)
		pipeline1.execute()
		return total_pms, median_pm_idx, median_pm_tuple, aggregate_pm_sws, avg_sw_per_pm, total_pgs, median_pg_idx, median_pg_tuple, \
			aggregate_pg_sws, avg_sw_per_pg

	"""
	Divide green mehfils into 2 person and 2+ person groups. Only 2 person green groups can be compared to private chat
	"""


def avg_num_of_chats_per_type():
	"""
	What are avg number of chats produced per type of chat?
	"""
	my_server = redis.Redis(connection_pool=POOL)
	total_pms = my_server.get('total_pms')
	if total_pms:
		results = my_server.mget(['median_pm_idx','median_pm_tuple','aggregate_pm_chats','avg_chat_per_pm','total_pgs','median_pg_idx','median_pg_tuple',\
			'aggregate_pg_chats','avg_chat_per_pg','pms_with_sws','pgs_with_sws'])
		return total_pms, results[0], results[1], results[2], results[3], results[4], results[5], results[6], results[7], results[8], results[9], results[10]
	else:
		pm_data = my_server.zrange('pm_ch',0,-1,withscores=True)
		total_pms = len(pm_data)
		median_pm_idx = int(total_pms/2)
		median_pm_tuple = my_server.zrange('pm_ch',median_pm_idx,median_pm_idx+1,withscores=True)[0]

		pg_data = my_server.zrange('pg_ch',0,-1,withscores=True)
		total_pgs = len(pg_data)
		median_pg_idx = int(total_pgs/2)
		median_pg_tuple = my_server.zrange('pg_ch',median_pg_idx,median_pg_idx+1,withscores=True)[0]

		# data is list of (group_id,chat_num) type tuples
		aggregate_pm_chats, aggregate_pg_chats = 0, 0
		for tup in pm_data:
			aggregate_pm_chats += int(tup[1])
		for tup in pg_data:
			aggregate_pg_chats += int(tup[1])
		avg_chat_per_pm = "{0:.2f}".format(aggregate_pm_chats/float(total_pms))
		avg_chat_per_pg = "{0:.2f}".format(aggregate_pg_chats/float(total_pgs))

		pms_with_sws = "{0:.2f}".format(my_server.zcard('pm_sw')/float(total_pms)*100)
		pgs_with_sws = "{0:.2f}".format(my_server.zcard('pg_sw')/float(total_pgs)*100)

		# caching the results
		pipeline1 = my_server.pipeline()
		pipeline1.setex('total_pms',total_pms,TEN_MINS)
		pipeline1.setex('median_pm_idx',median_pm_idx,TEN_MINS)
		pipeline1.setex('median_pm_tuple',median_pm_tuple,TEN_MINS)
		pipeline1.setex('aggregate_pm_chats',aggregate_pm_chats,TEN_MINS)
		pipeline1.setex('avg_chat_per_pm',avg_chat_per_pm,TEN_MINS)
		pipeline1.setex('total_pgs',total_pgs,TEN_MINS)
		pipeline1.setex('median_pg_idx',median_pg_idx,TEN_MINS)
		pipeline1.setex('median_pg_tuple',median_pg_tuple,TEN_MINS)
		pipeline1.setex('aggregate_pg_chats',aggregate_pg_chats,TEN_MINS)
		pipeline1.setex('avg_chat_per_pg',avg_chat_per_pg,TEN_MINS)
		pipeline1.setex('pms_with_sws',pms_with_sws,TEN_MINS)
		pipeline1.setex('pgs_with_sws',pgs_with_sws,TEN_MINS)
		pipeline1.execute()
		return total_pms, median_pm_idx, median_pm_tuple, aggregate_pm_chats, avg_chat_per_pm, total_pgs, median_pg_idx, median_pg_tuple, \
		aggregate_pg_chats, avg_chat_per_pg, pms_with_sws, pgs_with_sws