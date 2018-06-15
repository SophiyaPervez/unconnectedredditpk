# coding=utf-8
import re
import ujson as json
import redis, time, random
from urlparse import urlparse
from location import REDLOC5
from score import THUMB_HEIGHT, EXTRA_PADDING, PERSONAL_GROUP_SAVE_MSGS
from page_controls import PERSONAL_GROUP_OBJECT_CEILING, PERSONAL_GROUP_OBJECT_FLOOR, PERSONAL_GROUP_BLOB_SIZE_LIMIT, PERSONAL_GROUP_PHT_XFER_IVTS, \
PERSONAL_GROUP_MAX_PHOTOS, MOBILE_NUM_CHG_COOLOFF, PERSONAL_GROUP_SMS_LOCK_TTL, PERSONAL_GROUP_SMS_IVTS, PERSONAL_GROUP_SAVED_CHAT_COUNTER, \
PERSONAL_GROUP_REJOIN_RATELIMIT, PERSONAL_GROUP_SOFT_DELETION_CUTOFF, PERSONAL_GROUP_HARD_DELETION_CUTOFF, EXITED_PERSONAL_GROUP_HARD_DELETION_CUTOFF,\
PERSONAL_GROUP_INVITES,PERSONAL_GROUP_INVITES_COOLOFF, USER_GROUP_LIST_CACHING_TIME, URL_POSTINGS_ALLOWED, USER_FRIEND_LIST_CACHING_TIME
from redis4 import retrieve_bulk_credentials, retrieve_credentials, log_personal_group_exit_or_delete, purge_exit_list, cache_meta_data, get_cached_meta_data
from redis2 import bulk_delete_pergrp_notif, get_latest_notif_obj_pgh, update_pg_obj_del
from get_meta_data import get_meta_data
from urlmarker import URL_REGEX1

'''
##########Redis Namespace##########

personal_group is a key used to produce group_ids for personal groups
all_pgs is a sorted set that contains IDs of all groups created (alongwith creation times)

'personal_group_attendance' is a sorted set of last access times of all personal groups. It helps in making deletion decisions
'exited_personal_groups' is a sorted set of all exited personal groups (alongwith time of exit). It is used for deletion

pgp:<group_id> 'personal_group_participants' contains IDs of participating users
pgah:<group_id> 'personal_group_attribute_hash' contains personal_group attributes
pgd:<group_id> 'personal_group_data' contains JSON data dump of the personal group
pgc:<user_id> 'personal_group_credentials' contains JSON data dump of user credentials (username and avatar url)
pgld:<user_id>:<start_idx>:<end_idx> 'personal_group_list_data' contains JSON data dump of a user's chat list

pgsl:<group_id>:<own_id> 'personal_group_save_list' is a list of saved blob hashes in a personal group
pgl:<group_id> 'personal_group_list' contains a list of group content
pgpl:<group_id> 'personal_group_photo_list' contains a list of photo content shared in group

pgsh:<group_id>:<own_id>:<save_blob_id> 'personal_group_saved_hash' is a hash containing saved chat content 
pgh:<group_id>:<blob_id> 'personal_group_hash' is a hash containing actual content of a 'blob' displayed in a personal group
pgih:<group_id>:<image_id> 'personal_group_image_hash' is a hash containing data of image shared in a personal group

pgbid:<group_id> generates blob_id for personal groups
pgiid:<group_id> generates image_id for personal group image storage

pgmdrl:<group_id>:<own_id> 'personal_group_mass_deletion_rate_limit' is used to rate limit mass deletion calls to personal group
pgdrl:<group_id>:<own_id> 'personal_group_deletion_rate_limit' is used to rate limit post deletion from chat or photo settings (both)
pgxic:<group_id>:<their_id> 'personal_group_transfer_invite_cooloff' is a key that cools off the rate of sending image transfer invitations in personal groups
pgsmsic:<group_id>:<their_id> 'personal_group_sms_invite_cooloff' is a key that cools off the rate of sending sms invitations in personal groups
pgsrl:<group_id>:<own_id> 'personal_group_save_rate_limiting' enables rate-limiting of the save feature
pgdsrl:<group_id>:<own_id> 'personal_group_deleting_savedata_rate_limit' enables rate-limiting deletion of saved chat
pggrrl:<group_id>:<own_id> 'personal_group_group_restoration_rate_limit' rate limits people from quickly suspending group again after having unsuspended it

pgrl:<group_id>:<blob_id>:<target_index> 'response_list' containing all response IDs to a specific msg. Used in deletion

pgrp:<own_id>:<target_id> 'personal_group' contains the group ID associated with the two people in the key name
pgil:<user_id> 'personal_group_invite_list' contains all interactive invites sent by and to user_id
ilt:<user_id> 'invite_list_trimming' is a key that cools off the rate of trimming the invites sorted set
pgirl:<user_id> 'personal_group_invite_rate_limit' is a key that cools off excessive invite-sending behavior

pgii:<own_id>:<their_id> 'personal_group_ignore_invite' means they invited me and I ignore it. This key lives till the original invite was supposed to live
pgiia:<own_id>:<their_id> 'personal_group_ignore_invite' means they invited me anonymously, and I just ignored it

pgmvtid:<own_id> 'personal_group_mobile_verification_target_id' enables a mobile verifying user to return to the correct personal group
pgmvcsrf:<own_id> 'personal_group_mobile_verification_csrf' enables a mobile verifying user to identify their CSRF for 'PARTIAL AUTHENTICATION'
nchdis:<own_id> 'number_change_disallowed' enables rate-limiting mobile number re-verifications
ssl:<user_id>:<target_id> 'sms_sending_locked' enabled rate-limiting sms sending in personal groups

uname:<user_id> hash storing nickname of 'user_id'

pgfgm:<user_id> personal_group_friend_group_mapping is a sorted set containing group_id:friend_id pairs sorted by latest touch time

rlus:<own_id>:<group_id> rate_limited_url_submissions ascertains whether url scraping is currently rate limited or not
usl:<own_id>:<group_id> url_submissions_left is used to determine whether it's time to rate limit the user

pgfl:<user_id> 'personal_group_friend_list' is a key containing cached friend_list credentials for user with id 'user_id

rlfs:<user_id> 'rate_limit_photo_sharing' is a key that rate limits sharing behavior in personal groups

###########
'''

POOL = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=REDLOC5, db=0)

THREE_SECS = 3
SIX_SECS = 6
ONE_MIN = 60
TWO_MINS = 120
FOUR_MINS = 4*60
FIVE_MINS = 5*60
EIGHT_MINS = 8*60
TEN_MINS = 10*60
THIRTY_MINS = 30*60
ONE_DAY = 60*60*24
TWO_DAYS = 60*60*24*2
SEVEN_DAYS = 60*60*24*7
ONE_MONTH = 60*60*24*30

LOWER_RES_BOUND = 0.55
UPPER_RES_BOUND = 2.85

LEAST_CHARS = 4
MOST_CHARS = 50


"""
Group types:

personal: a 1-on-1 private chat room
"""


def small_image_width(big_img_width, big_img_height):
	wpercent = THUMB_HEIGHT/big_img_height
	return int(big_img_width*wpercent)


def small_photo_caption(caption, img_reso):
	"""
	Returns truncated captions for images with small widths
	"""
	if not caption:
		return ''
	else:
		cap_size = len(caption)
		if img_reso < LOWER_RES_BOUND:
			if cap_size <= LEAST_CHARS:
				return caption
			else: 
				return caption[:LEAST_CHARS]+' ..'
		# panoramic thumbnail
		elif img_reso > UPPER_RES_BOUND:
			if cap_size <= MOST_CHARS:
				return caption
			else:
				return caption[:MOST_CHARS]+' ..'
		# in between
		else:
			size = LEAST_CHARS+int(((MOST_CHARS-LEAST_CHARS)*((img_reso-LOWER_RES_BOUND)/(UPPER_RES_BOUND-LOWER_RES_BOUND))))
			if cap_size <= size:
				return caption
			else:
				return caption[:size]+' ..'


def invalidate_cached_user_data(user_id):
	"""
	Removes cached user credentials after user has changed their profile
	"""
	redis.Redis(connection_pool=POOL).delete('pgc:'+str(user_id))
	

def get_target_username(their_id, my_server=None):
	"""
	Retrieves 'their' username
	"""
	if not my_server:
		my_server = redis.Redis(connection_pool=POOL)
	their_cred_key = 'pgc:'+their_id
	their_cred = my_server.get(their_cred_key)
	if their_cred:
		return json.loads(their_cred)[0]
	else:
		their_uname, their_avurl = retrieve_credentials(their_id,decode_uname=True)
		my_server.setex(their_cred_key,json.dumps([their_uname, their_avurl]),THIRTY_MINS)
		return their_uname


def get_single_user_credentials(user_id, my_server=None,as_list=True):
	"""
	Retrieves credentials' local copy for a single user
	"""
	if not my_server:
		my_server = redis.Redis(connection_pool=POOL)
	cred_key = 'pgc:'+user_id
	cred = my_server.get(cred_key)
	if not cred:
		uname, avurl = retrieve_credentials(user_id,decode_uname=True)
		cred_list = [uname,avurl]
		my_server.setex(cred_key,json.dumps(cred_list),THIRTY_MINS)
		if as_list:
			return cred_list
		else:
			return uname, avurl
	if as_list:
		return json.loads(cred)
	else:
		data = json.loads(cred)
		return data[0], data[1]


def get_user_credentials(own_id, their_id, my_server=None):
	"""
	Retrieves user credentials (username and avatar_url for both participating users)

	Either gets locally cached copy, then fall-backs to cached copy from redis4, then fall-backs to postgresqsl DB (in that order)
	"""
	if not my_server:
		my_server = redis.Redis(connection_pool=POOL)
	own_cred_key, their_cred_key = 'pgc:'+own_id, 'pgc:'+their_id
	own_cred, their_cred = my_server.mget(own_cred_key, their_cred_key)
	if not own_cred and not their_cred:
		raw_user_cred = retrieve_bulk_credentials([own_id,their_id],decode_unames=True)
		int_oid, int_tid = int(own_id), int(their_id)
		own_cred = [raw_user_cred[int_oid]['uname'],raw_user_cred[int_oid]['avurl']]
		their_cred = [raw_user_cred[int_tid]['uname'],raw_user_cred[int_tid]['avurl']]
		my_server.setex(own_cred_key,json.dumps(own_cred),THIRTY_MINS)
		my_server.setex(their_cred_key,json.dumps(their_cred),THIRTY_MINS)
		return own_cred, their_cred
	elif not own_cred:
		own_uname, own_avurl = retrieve_credentials(own_id,decode_uname=True)
		own_cred = [own_uname, own_avurl]
		my_server.setex(own_cred_key,json.dumps(own_cred),THIRTY_MINS)
		return own_cred, json.loads(their_cred)
	elif not their_cred:
		their_uname, their_avurl = retrieve_credentials(their_id,decode_uname=True)
		their_cred = [their_uname, their_avurl]
		my_server.setex(their_cred_key,json.dumps(their_cred),THIRTY_MINS)
		return json.loads(own_cred), their_cred
	else:
		return json.loads(own_cred), json.loads(their_cred)
		

def retrieve_content_from_personal_group(group_id, own_id, target_id, time_now, chat_data=True):
	"""
	Returns essential personal group data required to render it
	"""
	own_id, target_id = str(own_id), str(target_id)
	group_key, own_last_seen = "pgah:"+group_id, 'last_seen'+own_id
	my_server = redis.Redis(connection_pool=POOL)
	own_anon_status, their_anon_status, auto_del_called, is_suspended, prev_time, their_last_seen_time = \
	my_server.hmget(group_key,'anon'+own_id,'anon'+target_id,'autodel','is_sus',own_last_seen,'last_seen'+target_id)
	my_server.hset(group_key,own_last_seen,time_now) # putting these in pipeline doesn't speed up the commands (already profiled)
	prev_time = time_now - THIRTY_MINS if prev_time is None else float(prev_time)
	if chat_data is False:
		return prev_time, own_anon_status, their_anon_status, auto_del_called, their_last_seen_time, is_suspended, \
		get_target_username(target_id, my_server)
	else:
		personal_group_list = my_server.lrange("pgl:"+group_id, 0, -1)
		pipeline2 = my_server.pipeline()
		for key in personal_group_list:
			pipeline2.hgetall("pgh:"+group_id+":"+key.split(":")[0]) #key.split(":")[0] is 'blob_id'
		result = pipeline2.execute()
		own_cred, their_cred = get_user_credentials(own_id, target_id, my_server)
		return prev_time, own_anon_status, their_anon_status, auto_del_called, their_last_seen_time, is_suspended, result, own_cred, their_cred



def get_cached_personal_group_data(group_id):
	"""
	Retrievs cached personal group data
	"""
	return redis.Redis(connection_pool=POOL).get('pgd:'+group_id)


def cache_personal_group_data(json_obj, group_id):
	"""
	Caches personal group's data as an optimization
	"""
	redis.Redis(connection_pool=POOL).setex('pgd:'+group_id,json_obj,ONE_DAY)


########################################### Update Last Seen in Personal Group ###########################################

def update_personal_group_last_seen(own_id, group_id, time_now = None):
	"""
	Update user's last seen in group
	"""
	redis.Redis(connection_pool=POOL).hset("pgah:"+group_id,'last_seen'+str(own_id),time_now if time_now else time.time())

######################################## Content Deletion/Hiding in Personal Group ########################################


def check_single_chat_current_status(blob_id, idx, own_id, group_id):
	"""
	Returns deletion status of a post
	"""
	blob_hash = "pgh:"+group_id+":"+blob_id
	my_server = redis.Redis(connection_pool=POOL)
	blob_owner_id = my_server.hget(blob_hash,'id')
	if blob_owner_id == str(own_id):
		if idx == '-1': #'-1' is passed for response blobs
			return my_server.hget(blob_hash,'status')
		else:
			return my_server.hget(blob_hash,'status'+idx)
	else:
		return None


def delete_or_hide_chat_from_personal_group(blob_id, idx, own_id, group_id, img_id, action):
	"""
	Deleting a post (text or photo) from private chat
	"""
	own_id = str(own_id)
	my_server = redis.Redis(connection_pool=POOL)
	ttl = my_server.ttl("pgdrl:"+group_id+":"+own_id)
	if ttl > 0:
		return False, ttl
	to_delete, to_hide = action in ('del','undel'), action in ('hide','unhide')
	parent_blob = "pgh:"+group_id+":"+blob_id
	# if blob has been deleted, blow_owner_id and target_img_id should come out to be None
	blob_owner_id, target_img_id = my_server.hmget(parent_blob,'id','img_id' if idx == '-1' else 'img_id'+idx)
	if to_delete:
		own_blob = blob_owner_id == own_id
		field, target_field, value = 'status' if idx == '-1' else 'status'+idx, 't_status', action
		if own_blob:
			image_hash = 'pgih:'+group_id+":"+target_img_id if target_img_id else None
			image_hash_exists = my_server.exists(image_hash) if image_hash else False
			list_of_blob_hashes = my_server.lrange("pgrl:"+group_id+":"+blob_id+":"+idx,0,-1)
			pipeline1 = my_server.pipeline()
			pipeline1.hset(parent_blob,field,value)
			for blob_hash in list_of_blob_hashes:
				pipeline1.hset(blob_hash,target_field,value)
			if image_hash_exists:
				my_server.hset(image_hash,'status',value)
			pipeline1.delete('pgd:'+group_id)
			pipeline1.execute()
			# if latest blob of the group was own blob and it was the same as the deleted blob, update it's status in pgah:group_id
			group_key = "pgah:"+group_id
			if my_server.hget(group_key,'lt_msg_wid') == own_id:
				latest_blob = my_server.lindex("pgl:"+group_id,0)
				if latest_blob:
					latest_blob = latest_blob.split(":")#blob_id:writer_id:comment_count
					if blob_id == latest_blob[0] and idx == latest_blob[2]:
						if value == 'undel':
							if my_server.hget(parent_blob,'hidden' if idx == '-1' else 'hidden'+idx) == 'yes':
								my_server.hset(group_key,'lt_msg_st','yes')
							else:
								my_server.hset(group_key,'lt_msg_st',value)
						else:
							my_server.hset(group_key,'lt_msg_st',value)
			# ratelimiting:
			my_server.setex("pgdrl:"+group_id+":"+own_id,1,SIX_SECS)
			return True, None
		else:
			return False, None
	elif to_hide:
		image_hash = 'pgih:'+group_id+":"+img_id
		img_match = target_img_id == img_id
		not_self = blob_owner_id and own_id != blob_owner_id
		field, target_field, value = 'hidden' if idx == '-1' else 'hidden'+idx, 't_hidden', 'yes' if action == 'hide' else 'no'
		if img_match and not_self:
			target_blobs = []
			all_blobs = my_server.lrange('pgl:'+group_id,0,-1)
			for blob in all_blobs:
				blob = blob.split(":")
				bid, writer_id, cc = blob[0], blob[1], blob[2]
				if cc == '-1' and writer_id == own_id:
					bh = "pgh:"+group_id+":"+bid
					t_img_id = my_server.hget(bh,'t_img_id')
					if t_img_id == img_id:
						target_blobs.append(bh)
			image_hash = 'pgih:'+group_id+":"+img_id
			image_hash_exists = my_server.exists(image_hash)
			pipeline1 = my_server.pipeline()
			# delete from response blobs
			for blob in target_blobs:
				pipeline1.hset(blob,target_field,value)
			# delete from the associated parent blob (and index)
			pipeline1.hset(parent_blob,field,value)
			# delete from pgpl. delete the associated image hash
			if image_hash_exists:
				pipeline1.hset(image_hash,'hidden',value)
			pipeline1.delete('pgd:'+group_id)
			pipeline1.execute()
			# if hidden blob's img_id was the same as the latest blob's img_id, change the latest blob's status
			group_key = "pgah:"+group_id
			if my_server.hget(group_key,'lt_img_id') == img_id:
				my_server.hset(group_key,'lt_msg_st',value)
			# ratelimiting
			my_server.setex("pgdrl:"+group_id+":"+own_id,1,SIX_SECS)
			return True, None
		else:
			return False, None
	else:
		return False, None



def delete_or_hide_photo_from_settings(own_id, group_id, blob_id, idx, img_id, action):
	"""
	Deleting/hiding photo from personal group settings

	Must cater to the case where blob containing the photo has already been trimmed
	"""
	own_id = str(own_id)
	my_server = redis.Redis(connection_pool=POOL)
	ttl = my_server.ttl("pgdrl:"+group_id+":"+own_id)
	if ttl > 0:
		return False, ttl
	img_id = str(img_id)
	to_delete, to_hide = action in ('del','undel'), action in ('hide','unhide')
	if to_delete:
		field = 'status'
		target_field = 't_status'
		value = action
	elif to_hide:
		field = 'hidden'
		target_field = 't_hidden'
		value = 'yes' if action == 'hide' else 'no'
	else:
		return False, None
	image_hash = 'pgih:'+group_id+":"+img_id
	target_blobs = []
	img_owner_id = my_server.hget(image_hash,'owner_id')
	own_photo = img_owner_id == own_id
	if (to_delete and own_photo) or (to_hide and not own_photo):
		all_blobs = my_server.lrange('pgl:'+group_id,0,-1)
		for blob in all_blobs:
			blob = blob.split(":")
			bid, writer_id, cc = blob[0], blob[1], blob[2]
			if (to_delete and cc == '-1' and writer_id != own_id) or (to_hide and cc == '-1' and writer_id == own_id):
				blob_hash = "pgh:"+group_id+":"+bid
				t_img_id = my_server.hget(blob_hash,'t_img_id')
				if t_img_id == img_id:
					target_blobs.append(blob_hash)
		parent_blob = "pgh:"+group_id+":"+str(blob_id)
		image_id = my_server.hget(parent_blob,'img_id' if idx == '-1' else 'img_id'+idx)
		# final deletion/hiding happening below (in one go)
		pipeline1 = my_server.pipeline()
		# delete/hide from response blobs
		for blob in target_blobs:
			pipeline1.hset(blob,target_field,value)
		# delete/hide from the associated parent blob (and index)
		if image_id == img_id:
			pipeline1.hset(parent_blob,field if idx == '-1' else field+idx,value)
		# delete the associated image hash
		pipeline1.hset(image_hash,field,value)
		pipeline1.delete('pgd:'+group_id)
		pipeline1.execute()
		# if affected image was the latest one, change its status
		group_key = "pgah:"+group_id
		if img_id == my_server.hget(group_key,'lt_img_id'):
			if value == 'undel':
				# check if the image is hidden
				if my_server.hget(parent_blob,'hidden' if idx == '-1' else 'hidden'+idx) == 'yes':
					my_server.hset(group_key,'lt_msg_st','yes')
				else:
					my_server.hset(group_key,'lt_msg_st',value)
			else:
				my_server.hset(group_key,'lt_msg_st',value)
		# ratelimiting:
		my_server.setex("pgdrl:"+group_id+":"+own_id,1,SIX_SECS)
	return True, None


def update_pg_obj_notif_after_bulk_deletion(group_id):
	"""
	Updates status of obj notif after mass deletion in group
	
	ALL TYPES of txt_types: 'notif','img','img_res','text','text_res','action','reentry','exited','creation'
	"""
	latest_notif_obj_pgh, latest_idx, latest_type, latest_deletion_status = get_latest_notif_obj_pgh(group_id,send_status=True)
	if latest_type in ('img','img_res','text','text_res'):
		my_server = redis.Redis(connection_pool=POOL)
		hash_list, pgh_list = my_server.lrange("pgl:"+group_id, 0, -1), []
		for key in hash_list:
			pgh_list.append("pgh:"+group_id+":"+key.split(":")[0]) #key.split(":")[0] is 'blob_id'
		if latest_notif_obj_pgh in pgh_list:
			blob_deletion_status = my_server.hget(latest_notif_obj_pgh,'status' if latest_type in ('img_res','text_res') else 'status'+latest_idx)
			if blob_deletion_status != latest_deletion_status:
				#sync them
				blob_id = latest_notif_obj_pgh.split(":")[2]
				update_pg_obj_del(blob_deletion_status,blob_id,latest_idx,group_id)


def delete_all_photos_from_personal_group(own_id, group_id, undelete=None, server=None):
	"""
	Deletes all photos of user from personal_group
	"""
	own_id = str(own_id)
	if not server:
		server = redis.Redis(connection_pool=POOL)
	ttl = server.ttl("pgmdrl:"+group_id+":"+own_id)
	if ttl > 0:
		return False, ttl
	status = 'undel' if undelete else 'del'
	all_photos = server.lrange("pgpl:"+group_id,0,-1)
	if all_photos:
		own_photos, own_photo_id_pool = [], []
		for photo in all_photos:
			photo = photo.split(":")
			img_id, blob_id, index, owner_id = photo[0], photo[1], photo[2], photo[3]
			if own_id == owner_id:
				own_photos.append((blob_id, index))
				own_photo_id_pool.append(img_id)
		if own_photos:
			all_blobs = server.lrange('pgl:'+group_id,0,-1)
			target_response_blobs = []
			for blob in all_blobs:
				blob = blob.split(":")
				bid, writer_id, cc = blob[0], blob[1], blob[2]
				if cc == '-1' and writer_id != own_id:#'-1' is for response blobs
					blob_hash = "pgh:"+group_id+":"+bid
					t_img_id = server.hget(blob_hash,'t_img_id')
					if t_img_id in own_photo_id_pool:
						target_response_blobs.append(blob_hash)
			# final deletion happening below (in one go)
			pipeline1 = server.pipeline()
			for photo in own_photos:
				blob = "pgh:"+group_id+":"+photo[0]
				pipeline1.hset(blob, 'status' if photo[1] == '-1' else 'status'+photo[1],status)
			for photo_id in own_photo_id_pool:
				pipeline1.hset('pgih:'+group_id+":"+photo_id,'status',status)
			for res_blob in target_response_blobs:
				pipeline1.hset(res_blob,'t_status',status)
			pipeline1.delete('pgd:'+group_id)
			pipeline1.execute()	
		# if latest blob's lt_img_id is not None and its writer is self, change its status
		group_key = "pgah:"+group_id
		latest_img_id, latest_msg_writer_id = server.hmget(group_key,'lt_img_id','lt_msg_wid')
		if latest_img_id and latest_msg_writer_id == own_id:
			if status == 'undel':
				# first check if latest image is hidden or not
				first_element = server.lindex("pgl:"+group_id,0).split(":")
				blob_hash = "pgh:"+group_id+":"+first_element[0]
				idx = server.hget(blob_hash,'idx')
				is_hidden = server.hget(blob_hash,'hidden'+idx if idx else 'hidden')
				if is_hidden == 'yes':
					server.hset(group_key,'lt_msg_st','yes')
				else:
					server.hset(group_key,'lt_msg_st',status)
			else:
				server.hset(group_key,'lt_msg_st',status)
		# ratelimiting
		server.setex("pgmdrl:"+group_id+":"+own_id,1,TWO_MINS)
	return True, None


def delete_all_user_chats_from_personal_group(own_id, group_id, undelete=None):
	"""
	Deletes all currently visible chat of user (excluding action blobs)
	"""
	own_id = str(own_id)
	my_server = redis.Redis(connection_pool=POOL)
	ttl = my_server.ttl("pgmdrl:"+group_id+":"+own_id)
	if ttl > 0:
		return False, ttl
	own_normal_blobs, own_res_blobs, their_res_blobs, own_photo_id_pool = [], [], [], []
	status = 'undel' if undelete else 'del'
	personal_group_list = "pgl:"+group_id
	all_chat = my_server.lrange(personal_group_list,0,-1)
	if all_chat:
		for chat in all_chat:
			tup = chat.split(":")
			blob_id, writer_id, comment_count = tup[0], tup[1], int(tup[2])
			if comment_count < 0:
				if writer_id == own_id:
					own_res_blobs.append(blob_id)
				else:
					their_res_blobs.append(blob_id)
			elif comment_count > 0 and writer_id == own_id:
				own_normal_blobs.append((blob_id,comment_count))
			else:
				pass
		personal_group_photo_list = "pgpl:"+group_id
		all_photos = my_server.lrange(personal_group_photo_list,0,-1)
		for photo in all_photos:
			photo = photo.split(":")
			img_id, owner_id = photo[0], photo[3]
			if own_id == owner_id:
				own_photo_id_pool.append(img_id)
		# final deletion happening below (in one go)
		pipeline1 = my_server.pipeline()
		for blob_id, comment_count in own_normal_blobs:
			blob_hash = "pgh:"+group_id+":"+blob_id
			for i in range(1, comment_count+1):
				pipeline1.hset(blob_hash,'status'+str(i),status)
		for blob_id in own_res_blobs:
			blob_hash = "pgh:"+group_id+":"+blob_id
			pipeline1.hset(blob_hash,'status',status)
		for blob_id in their_res_blobs:
			blob_hash = "pgh:"+group_id+":"+blob_id
			pipeline1.hset(blob_hash,'t_status',status)
		for photo_id in own_photo_id_pool:
			pipeline1.hset('pgih:'+group_id+":"+photo_id,'status',status)
		pipeline1.delete('pgd:'+group_id)
		pipeline1.execute()
		# if latest blob is a chat/img blob, and its writer is own self, then change its status
		group_key = "pgah:"+group_id
		latest_msg_writer_id, latest_msg_type = my_server.hmget(group_key,'lt_msg_wid','lt_msg_tp')
		if latest_msg_writer_id == own_id and latest_msg_type in ('text','text_res','img','img_res'):
			if status == 'undel' and latest_msg_type in ('img','img_res'):
				# is the image being undeleted hidden by other user?
				first_element = my_server.lindex("pgl:"+group_id,0).split(":")
				blob_hash = "pgh:"+group_id+":"+first_element[0]
				idx = my_server.hget(blob_hash,'idx')
				is_hidden = my_server.hget(blob_hash,'hidden'+idx if idx else 'hidden')
				if is_hidden == 'yes':
					my_server.hset(group_key,'lt_msg_st','yes')
				else:
					my_server.hset(group_key,'lt_msg_st',status)
			else:
				my_server.hset(group_key,'lt_msg_st',status)
		# ratelimiting:
		my_server.setex("pgmdrl:"+group_id+":"+own_id,1,TWO_MINS)
	return True, None


def trim_personal_group(group_id, num_of_objs_in_group):
	"""
	Trims personal_group when it grows beyond a certain size
	"""
	personal_group_list = "pgl:"+group_id
	my_server = redis.Redis(connection_pool=POOL)
	blobs_to_del = personal_group_deletion_inspection(personal_group_list, num_of_objs_in_group, my_server)
	if blobs_to_del:
		personal_group_permanent_deletion(group_id, personal_group_list, blobs_to_del, my_server)


def personal_group_deletion_inspection(personal_group_list, num_of_objs_in_group, server=None):
	"""
	Returns blob_ids that are candidates for permanent deletion
	"""
	if not server:
		server = redis.Redis(connection_pool=POOL)
	overflow, to_delete = num_of_objs_in_group - PERSONAL_GROUP_OBJECT_FLOOR, []
	all_objs = server.lrange(personal_group_list,0,-1)
	for obj in reversed(all_objs):
		tup = obj.split(":")
		cc, blob_id = int(tup[2]), tup[0] # cc is comment_count
		cc = 1 if cc in (0,-1) else cc # set cc to 1 for both 'action' and 'response' blobs (their cc is set to 0 and -1 by default)
		if cc > overflow:
			break
		elif cc == overflow:
			to_delete.append((blob_id,obj))
			break
		else:
			to_delete.append((blob_id,obj))
			overflow -= cc
	return to_delete
		

def personal_group_permanent_deletion(group_id, personal_group_list, objs_to_delete_fully, server=None):
	"""
	Permanently deleting blobs and related keys
	"""
	if not server:
		server = redis.Redis(connection_pool=POOL)
	pipeline1 = server.pipeline()
	for blob_id, obj_name in objs_to_delete_fully:
		how_many_to_del = int(obj_name.split(":")[2]) # how_many_to_del is '-1' if 'res' blob, '0' if 'action' blob, and non-zero +int otherwise
		if how_many_to_del < 0: 
			# deleting related 'pgrl' objects
			pipeline1.delete("pgrl:"+group_id+":"+blob_id+":-1")
		elif how_many_to_del > 0:
			# deleting related 'pgrl' objects
			for num in range(how_many_to_del):
				idx = str(num+1)
				pipeline1.delete("pgrl:"+group_id+":"+blob_id+":"+idx)
		else:
			pass
		# deleting hash object
		hash_name = "pgh:"+group_id+":"+blob_id
		pipeline1.delete(hash_name)
		# removing obj_name from personal_group_list
		pipeline1.lrem(personal_group_list,obj_name,num=-1)
		# recalculating number of objects in personal_group
		how_many_to_del = 1 if how_many_to_del in (0,-1) else how_many_to_del
		pipeline1.hincrby("pgah:"+group_id,'oc',amount=-(how_many_to_del))
	pipeline1.delete('pgd:'+group_id)
	pipeline1.execute()
	server.hset("pgah:"+group_id,'autodel','1')


def reset_all_group_chat(group_id, my_server=None):
	"""
	Reset group chat (e.g. if the group's returning from a suspension, or flagged for deletion)
	"""
	if not my_server:
		my_server = redis.Redis(connection_pool=POOL)
	personal_group_list = "pgl:"+group_id
	all_objs = my_server.lrange(personal_group_list,0,-1)
	# gathering all possible related keys
	related_keys = []
	for obj in all_objs:
		tup = obj.split(":")
		blob_id, writer_id, comment_count = tup[0], tup[1], tup[2]
		if comment_count == '-1':
			# response - can have related hash list
			related_object_list = 'pgrl:'+group_id+":"+blob_id+":-1"
			related_keys.append(related_object_list)
		elif comment_count == '0':
			# notif or action - no related hash list
			pass
		else:
			# normal - can have related hash list
			for num in range(int(comment_count)):
				related_object_list = 'pgrl:'+group_id+":"+blob_id+":"+str(num+1)
				related_keys.append(related_object_list)
	# deleting everything at once
	pipeline1 = my_server.pipeline()
	# deleting all related keys first				
	for related_hash_list in related_keys:
		pipeline1.delete(related_hash_list)
	# deleting all chat blobs next
	for composite_obj in all_objs:
		blob_id = composite_obj.split(":")[0]
		pipeline1.delete("pgh:"+group_id+":"+blob_id)
	# deleting list of all chat blobs
	pipeline1.delete(personal_group_list)
	# get rid of related pgd
	pipeline1.delete("pgd:"+group_id)
	# reset object_count in pgah
	pipeline1.hset("pgah:"+group_id,'oc',0)
	pipeline1.execute()


def permanently_delete_entire_personal_group(group_id, my_server=None):
	"""
	Permanently delete all keys related to personal group
	"""
	if not my_server:
		my_server = redis.Redis(connection_pool=POOL)
	reset_all_group_chat(group_id, my_server=my_server)
	payload = my_server.get("pgp:"+group_id)
	try:
		participants = payload.split(":")
		user_1, user_2 = participants[0], participants[1]
		group_with_user_1 = group_id+":"+user_1
		group_with_user_2 = group_id+":"+user_2
		pipeline1 = my_server.pipeline()
		pipeline1.delete("pgrp:"+user_1+":"+user_2)
		pipeline1.delete("pgrp:"+user_2+":"+user_1)
		pipeline1.zrem("pgfgm:"+user_1,group_with_user_2)
		pipeline1.zrem("pgfgm:"+user_2,group_with_user_1)
		pipeline1.execute()
		user_1_saved_list = 'pgsl:'+group_with_user_1
		user_2_saved_list = 'pgsl:'+group_with_user_2
		blob_ids_1 = my_server.lrange(user_1_saved_list, 0, -1)
		blob_ids_2 = my_server.lrange(user_2_saved_list, 0, -1)
		pipeline2 = my_server.pipeline()
		for blob_id in blob_ids_1:
			pipeline2.delete('pgsh:'+group_id+":"+user_1+":"+blob_id)
		for blob_id in blob_ids_2:
			pipeline2.delete('pgsh:'+group_id+":"+user_2+":"+blob_id)
		pipeline2.delete(user_1_saved_list)
		pipeline2.delete(user_2_saved_list)
		pipeline2.execute()
		user_photos = 'pgpl:'+group_id
		all_photos = my_server.lrange(user_photos,0,-1)
		pipeline3 = my_server.pipeline()
		pipeline3.delete("pgp:"+group_id)
		pipeline3.delete("pgah:"+group_id)
		pipeline3.delete('pgiid:'+group_id)
		pipeline3.delete('pgbid:'+group_id)
		pipeline3.delete('pgd:'+group_id)
		for payload in all_photos:
			pipeline3.delete('pgih:'+group_id+":"+payload.split(":")[0])
		pipeline3.delete(user_photos)
		pipeline3.execute()
	except IndexError, AttributeError:
		pass


######################################## Managing Saved Content in Personal Group ########################################


def prepare_saved_content(own_id, target_id, list_of_dict, my_server = None):
	"""
	Insert username and avatar_url in saved content to make it ready for rendering
	"""
	if not my_server:
		my_server = redis.Redis(connection_pool=POOL)
	own_cred, their_cred = get_user_credentials(own_id, target_id, my_server)
	own_uname, own_avurl, their_uname, their_avurl = own_cred[0], own_cred[1], their_cred[0], their_cred[1]
	for dictionary in list_of_dict:
		is_own_content = True if dictionary["id"] == str(own_id) else False
		is_res_blob = True if dictionary.get("res_time",None) else False
		if is_own_content:
			dictionary['username'] = own_uname 
			dictionary['av_url'] = own_avurl
			if is_res_blob:
				dictionary['t_username'] = their_uname
				dictionary['t_av_url'] = their_avurl
		else:
			dictionary['username'] = their_uname
			dictionary['av_url'] = their_avurl
			if is_res_blob:
				dictionary['t_username'] = own_uname
				dictionary['t_av_url'] = own_avurl
		if 'owner_uname' in dictionary:
			dictionary['owner_uname'] = dictionary['owner_uname'].decode('utf-8')
	return list_of_dict


def retrieve_personal_group_saved_content(own_id, target_id, group_id):
	"""
	Retrieve all saved content of a personal group for a specific user
	"""
	my_server = redis.Redis(connection_pool=POOL)
	own_id = str(own_id)
	saved_blob_list = 'pgsl:'+group_id+":"+own_id
	all_saved_blob_ids = my_server.lrange(saved_blob_list,0,-1)
	pipeline1 = my_server.pipeline()
	for blob_id in all_saved_blob_ids:
		pipeline1.hgetall('pgsh:'+group_id+":"+own_id+":"+blob_id)
	return prepare_saved_content(own_id, target_id, pipeline1.execute(),my_server)
	

def delete_all_personal_group_saved_content(own_id, group_id, server=None):
	"""
	Deleting entire saved content of a personal group for a user
	"""
	own_id = str(own_id)
	if not server:
		server = redis.Redis(connection_pool=POOL)
		ratelimit = "pgdsrl:"+group_id+":"+own_id
		if server.exists(ratelimit):
			return False
		else:
			saved_blob_list = 'pgsl:'+group_id+":"+own_id
			all_saved_blob_ids = server.lrange(saved_blob_list,0,-1)
			pipeline1 = server.pipeline()
			for blob_id in all_saved_blob_ids:
				pipeline1.delete('pgsh:'+group_id+":"+own_id+":"+blob_id)
			pipeline1.delete(saved_blob_list)
			pipeline1.hset('pgah:'+group_id,'svrem'+own_id,PERSONAL_GROUP_SAVED_CHAT_COUNTER)
			pipeline1.setex(ratelimit,1,TWO_MINS)
			pipeline1.execute()
			return True
	else:
		saved_blob_list = 'pgsl:'+group_id+":"+own_id
		all_saved_blob_ids = server.lrange(saved_blob_list,0,-1)
		pipeline1 = server.pipeline()
		for blob_id in all_saved_blob_ids:
			pipeline1.delete('pgsh:'+group_id+":"+own_id+":"+blob_id)
		pipeline1.delete(saved_blob_list)
		pipeline1.hset('pgah:'+group_id,'svrem'+own_id,PERSONAL_GROUP_SAVED_CHAT_COUNTER)
		pipeline1.execute()


def delete_single_personal_group_saved_content(own_id,group_id, target_blob_id):
	"""
	Deleting single instance of saved personal group content
	"""
	if not target_blob_id:
		return False
	my_server = redis.Redis(connection_pool=POOL)
	own_id = str(own_id)
	ratelimit = "pgdsrl:"+group_id+":"+own_id
	if my_server.exists(ratelimit):
		return False
	else:
		saved_blob_list = 'pgsl:'+group_id+":"+own_id
		removed = my_server.lrem(saved_blob_list,target_blob_id,num=0)
		if removed > 0:
			ratelimit = "pgdsrl:"+group_id+":"+own_id
			pipeline1 = my_server.pipeline()
			pipeline1.delete('pgsh:'+group_id+":"+own_id+":"+target_blob_id)
			pipeline1.hincrby('pgah:'+group_id,'svrem'+own_id,amount=removed)
			pipeline1.setex(ratelimit,1,THREE_SECS)
			pipeline1.execute()
			return True
		else:
			return False


def toggle_save_permission(own_id, group_id):
	"""
	Allow own chat to be saved in personal group
	"""
	if group_id is None:
		return False
	my_server = redis.Redis(connection_pool=POOL)
	own_id = str(own_id)
	current_perm = my_server.hget("pgah:"+group_id,'svprm'+own_id)
	if current_perm == '1':
		new_perm = '0'
		my_server.hset("pgah:"+group_id,'svprm'+own_id,new_perm)
	elif current_perm == '0':
		new_perm = '1'
		my_server.hset("pgah:"+group_id,'svprm'+own_id,new_perm)
	else:
		new_perm = '0'
		my_server.hset("pgah:"+group_id,'svprm'+own_id,new_perm)
	return new_perm


def own_save_permission_status(own_id, group_id):
	"""
	Return own save permission value
	"""
	return redis.Redis(connection_pool=POOL).hget("pgah:"+group_id,'svprm'+str(own_id))


def is_save_permission_granted_by_target(own_id,target_id):
	"""
	Check whether user can save target's chat in personal group
	"""
	my_server = redis.Redis(connection_pool=POOL)
	group_id, exists = personal_group_already_exists(own_id, target_id, my_server)
	if exists:
		if my_server.hget("pgah:"+group_id,'svprm'+target_id) == '1':
			return True
		else:
			return False
	else:
		return False


def purge_all_saved_chat_of_user(own_id, tid, group_id):
	"""
	Delete all saved chat of self, plus own chat saved by target user
	"""
	my_server = redis.Redis(connection_pool=POOL)
	tid, own_id = str(tid), str(own_id)
	# retrieve all target saved chat
	target_saved_blobs = my_server.lrange('pgsl:'+group_id+':'+tid,0,-1)
	pipeline1 = my_server.pipeline()
	for saved_blob in target_saved_blobs:
		pipeline1.hget('pgsh:'+group_id+":"+tid+":"+saved_blob,'id')
	result1, counter = pipeline1.execute(), 0
	# mark target saved chat that belongs to own self
	marked_for_deletion, marked_for_alteration = [], []
	for saved_blob in target_saved_blobs:
		if result1[counter] == own_id:
			marked_for_deletion.append(saved_blob)
		else:
			blob_parts = saved_blob.split(":")
			if blob_parts[1] == '-1':
				marked_for_alteration.append(saved_blob)
		counter += 1
	# delete all marked chat
	pipeline2 = my_server.pipeline()
	for marked_blob in marked_for_deletion:
		pipeline2.delete('pgsh:'+group_id+":"+tid+":"+marked_blob)
		pipeline2.lrem('pgsl:'+group_id+":"+tid,marked_blob,num=0)
	result2 = pipeline2.execute()
	pipeline3 = my_server.pipeline()
	# add sum of removed blobs to target's 'svrem' settings
	pipeline3.hincrby('pgah:'+group_id,'svrem'+tid,amount=int(sum(result2[1::2])))
	# alter all marked chat
	for marked_blob in marked_for_alteration:
		pipeline3.hset('pgsh:'+group_id+":"+tid+":"+marked_blob,'t_status','del')
	pipeline3.execute()
	# delete all own saved chat
	delete_all_personal_group_saved_content(own_id, group_id, server=my_server)


def save_personal_group_content(own_id, their_id, group_id, blob_id, index):
	"""
	Saves a post in personal group
	"""
	if blob_id is None:
		return False, PERSONAL_GROUP_SAVE_MSGS['err8'], None
	my_server = redis.Redis(connection_pool=POOL)
	own_id, group_hash = str(own_id), 'pgah:'+group_id
	ratelimit = "pgsrl:"+group_id+":"+own_id
	if my_server.exists(ratelimit):
		return False, PERSONAL_GROUP_SAVE_MSGS['err5'], my_server.ttl(ratelimit)
	saves_remaining, their_save_perm = my_server.hmget(group_hash,'svrem'+own_id,'svprm'+their_id)
	if int(saves_remaining) < 1:
		return False, PERSONAL_GROUP_SAVE_MSGS['err6'], None
	hash_name = "pgh:{}:{}".format(group_id, blob_id)
	blob_contents = my_server.hgetall(hash_name)
	if blob_contents:
		if blob_contents.get("id",None) != own_id and their_save_perm != '1':
			# you're not permitted to save their chat - don't save
			return False, PERSONAL_GROUP_SAVE_MSGS['err9'], None
		elif blob_contents.get("which_blob",None) in ('action','notif'):
			# is an action blob - don't save
			return False, PERSONAL_GROUP_SAVE_MSGS['err1'], None 
		elif blob_contents.get("res_time",None):
			# is a response blob
			if blob_contents.get("status",None) == 'del':
				# is user-deleted - don't save
				return False, PERSONAL_GROUP_SAVE_MSGS['err2'], None
			elif blob_contents.get("hidden",None) == 'yes':
				# is hidden - don't save
				return False, PERSONAL_GROUP_SAVE_MSGS['err3'], None
			else:
				# save it
				new_save_blob_id = blob_contents['blob_id']+":-1"
				if my_server.exists('pgsh:'+group_id+":"+own_id+":"+new_save_blob_id):
					# it was already saved - don't save
					return False, PERSONAL_GROUP_SAVE_MSGS['err7'], None
				else:
					blob_contents["save_time"] = time.time()
					blob_contents["save_blob_id"] = new_save_blob_id
					pipeline1 = my_server.pipeline()
					# push into user's save list and save contents in a hash
					pipeline1.lpush('pgsl:'+group_id+':'+own_id,new_save_blob_id)
					pipeline1.hmset('pgsh:'+group_id+':'+own_id+":"+new_save_blob_id,blob_contents)
					# decrementing saves remaining counter
					pipeline1.hincrby(group_hash,'svrem'+own_id,amount=-1)
					# ratelimiting:
					pipeline1.setex(ratelimit,1,FIVE_MINS)
					pipeline1.execute()
					return True, PERSONAL_GROUP_SAVE_MSGS['msg1'], FIVE_MINS
		else:
			# normal chat blob
			if not blob_contents.get("time"+index,None):
				# index does not exist - don't save
				return False, PERSONAL_GROUP_SAVE_MSGS['err1'], None
			elif blob_contents.get("status"+index,None) == 'del':
				# is user-deleted - don't save
				return False, PERSONAL_GROUP_SAVE_MSGS['err2'], None
			elif blob_contents.get("hidden"+index,None) == 'yes':
				# is hidden - don't save
				return False, PERSONAL_GROUP_SAVE_MSGS['err3'], None
			else:
				#save it
				new_save_blob_id = blob_contents['blob_id']+":"+index
				if my_server.exists('pgsh:'+group_id+":"+own_id+":"+new_save_blob_id):
					# it was already saved - don't save
					return False, PERSONAL_GROUP_SAVE_MSGS['err7'], None
				else:
					if blob_contents['type'+index] == 'text':
						filtered_blob_contents = {'id':blob_contents['id'],'save_time':time.time(),'blob_id':blob_contents['blob_id'],\
						'save_blob_id':new_save_blob_id,'type':blob_contents['type'+index],'which_blob':blob_contents['which_blob'], \
						'text':blob_contents['text'+index],'time':blob_contents['time'+index],'status':blob_contents['status'+index]}
					elif blob_contents['type'+index] == 'img':
						filtered_blob_contents = {'id':blob_contents['id'],'blob_id':blob_contents['blob_id'],'save_blob_id':new_save_blob_id,\
						'img_hw_ratio':blob_contents['img_hw_ratio'+index],'which_blob':blob_contents['which_blob'],'time':blob_contents['time'+index],\
						'type':blob_contents['type'+index],'img_width':blob_contents['img_width'+index],'img_height':blob_contents['img_height'+index],\
						'img':blob_contents['img'+index],'img_caption':blob_contents['img_caption'+index],'status':blob_contents['status'+index],\
						'img_id':blob_contents['img_id'+index],'img_s_caption':blob_contents['img_s_caption'+index],'hidden':blob_contents['hidden'+index],\
						'save_time':time.time()}
					elif blob_contents['type'+index] == 'shared_img':
						filtered_blob_contents = {'id':blob_contents['id'],'blob_id':blob_contents['blob_id'],'save_blob_id':new_save_blob_id,\
						'img_hw_ratio':blob_contents['img_hw_ratio'+index],'which_blob':blob_contents['which_blob'],'time':blob_contents['time'+index],\
						'type':blob_contents['type'+index],'img_width':blob_contents['img_width'+index],'img_height':blob_contents['img_height'+index],\
						'shared_img':blob_contents['shared_img'+index],'img_caption':blob_contents['img_caption'+index],'status':blob_contents['status'+index],\
						'img_id':blob_contents['img_id'+index],'img_s_caption':blob_contents['img_s_caption'+index],'hidden':blob_contents['hidden'+index],\
						'save_time':time.time(),'owner_uname':blob_contents['owner_uname'+index]}
					pipeline1 = my_server.pipeline()
					# push into user's save list and save contents in a hash
					pipeline1.lpush('pgsl:'+group_id+':'+own_id,new_save_blob_id)
					pipeline1.hmset('pgsh:'+group_id+':'+own_id+":"+new_save_blob_id,filtered_blob_contents)
					# decrementing saves remaining counter
					pipeline1.hincrby(group_hash,'svrem'+own_id,amount=-1)
					# ratelimiting:
					pipeline1.setex(ratelimit,1,FIVE_MINS)
					pipeline1.execute()
					return True, PERSONAL_GROUP_SAVE_MSGS['msg1'], FIVE_MINS
	else:
		# can't save blob that doesn't exist any more
		return False, PERSONAL_GROUP_SAVE_MSGS['err4'], None


######################################## Content Manipulation in Personal Group ########################################

"""
Content types:

msg: typical message written in group
sms notif:
reply:
photo:
action:
"""


def add_content_to_personal_group(content, type_, writer_id, group_id, res_blob=None):
	"""
	Adding chat blobs to personal groups
	"""
	my_server = redis.Redis(connection_pool=POOL)
	personal_group = "pgah:"+group_id
	if my_server.hget(personal_group,'is_sus') == '1':
		return 0, PERSONAL_GROUP_OBJECT_CEILING, None, None, None, '-1', None, None#'-1' img_id ensures image won't be saved separately
	writer_id, img_id, img_wid, img_hw_ratio = str(writer_id), '-1', None, None
	personal_group_list = "pgl:"+group_id
	is_response = (type_ == 'text_res' or type_ == 'img_res')
	is_normal_chat = (type_ == 'text' or type_ == 'img')
	is_shared_content = type_ == 'shared_img'
	if content and (type_=='action' or type_=='notif'):
		# creating new blob
		new_blob_id = str(my_server.incr("pgbid:"+group_id))
		personal_group_hash, append = "pgh:"+group_id+":"+new_blob_id, False #'append' is used at the end
		t_now, comment_count = time.time(),'0'#set '-1' for response blobs and '0' for action blobs
		hash_content = {'id':writer_id,type_:content,'time':t_now,'blob_id':new_blob_id,'which_blob':type_,\
		'status':'open' if type_=='notif' else 'permanent'}
		list_content, bid, idx = new_blob_id+":"+writer_id+":"+comment_count, new_blob_id, '-1'
		group_content = {'lt_msg_tp':type_,'lt_msg_t':t_now,'lt_msg_wid':writer_id,'lt_msg_tx':content,'lt_msg_img':'','lt_msg_st':'','lt_img_id':''}
	elif content and is_normal_chat:
		first_element = my_server.lindex(personal_group_list,0) #blob_id:writer_id:comment_count
		if first_element is not None:
			info = first_element.split(":")
			prev_blob_id, prev_writer_id, prev_comment_count = info[0], info[1], int(info[2])
		else:
			prev_blob_id, prev_writer_id, prev_comment_count = None, None, None
		if writer_id == prev_writer_id and 0 < prev_comment_count < PERSONAL_GROUP_BLOB_SIZE_LIMIT:
			# append to existing blob
			personal_group_hash, append = "pgh:"+group_id+":"+prev_blob_id, True
			################################
			# creating blob content
			prev_comment_count += 1
			comment_count, t_now = str(prev_comment_count), time.time()
			if type_ == 'img':
				img_wid, img_height, img_caption = content["img_width"], content["img_height"], content["img_caption"]
				content = content["img_url"]
				img_s_caption = small_photo_caption(img_caption, float(img_wid)/float(img_height))
				img_id = str(my_server.incr("pgiid:"+group_id))
				img_hw_ratio = int((float(img_height)/(2*float(img_wid)))*100)
				hash_content = {type_+comment_count:content, 'time'+comment_count:t_now, 'type'+comment_count:type_, 'idx':comment_count,\
				'img_width'+comment_count:img_wid+EXTRA_PADDING,'img_height'+comment_count:img_height, 'img_caption'+comment_count:img_caption,\
				'status'+comment_count:'undel','img_id'+comment_count:img_id,'img_s_caption'+comment_count:img_s_caption,\
				'hidden'+comment_count:'no','img_hw_ratio'+comment_count:img_hw_ratio}
				group_content = {'lt_msg_tp':type_,'lt_msg_t':t_now,'lt_msg_wid':writer_id,'lt_msg_tx':img_caption,'lt_msg_img':content,'lt_msg_st':'undel',\
				'lt_img_id':img_id}
			else:
				hash_content = {type_+comment_count:content, 'time'+comment_count:t_now, 'type'+comment_count:type_,'idx':comment_count,\
				'status'+comment_count:'undel'}
				group_content = {'lt_msg_tp':type_,'lt_msg_t':t_now,'lt_msg_wid':writer_id,'lt_msg_tx':content,'lt_msg_img':'','lt_msg_st':'undel',\
				'lt_img_id':''}
			list_content, bid, idx = prev_blob_id+":"+writer_id+":"+comment_count, prev_blob_id, comment_count
		else:
			# create a new blob
			new_blob_id = str(my_server.incr("pgbid:"+group_id))
			personal_group_hash, append = "pgh:"+group_id+":"+new_blob_id, False
			################################
			# creating blob content
			comment_count, t_now = '1', time.time()
			if type_ == 'img':
				img_wid, img_height, img_caption = content["img_width"], content["img_height"], content["img_caption"]
				content = content["img_url"]
				img_s_caption = small_photo_caption(img_caption, float(img_wid)/float(img_height))
				img_id = str(my_server.incr("pgiid:"+group_id))
				img_hw_ratio = int((float(img_height)/(2*float(img_wid)))*100)
				hash_content = {'status'+comment_count:'undel',type_+comment_count:content,'time'+comment_count:t_now,\
				'type'+comment_count:type_,'which_blob':'nor','img_id'+comment_count:img_id, 'blob_id':new_blob_id,\
				'img_s_caption'+comment_count:img_s_caption,'hidden'+comment_count:'no', 'id':writer_id, \
				'img_caption'+comment_count:img_caption,'img_width'+comment_count:img_wid+EXTRA_PADDING,\
				'img_height'+comment_count:img_height,'img_hw_ratio'+comment_count:img_hw_ratio,'idx':comment_count}
				group_content = {'lt_msg_tp':type_,'lt_msg_t':t_now,'lt_msg_wid':writer_id,'lt_msg_tx':img_caption,'lt_msg_img':content,'lt_msg_st':'undel',\
				'lt_img_id':img_id}
			else:
				hash_content = {'id':writer_id,type_+comment_count:content,'time'+comment_count:t_now,'idx':comment_count,\
				'type'+comment_count:type_,'which_blob':'nor','status'+comment_count:'undel','blob_id':new_blob_id}
				group_content = {'lt_msg_tp':type_,'lt_msg_t':t_now,'lt_msg_wid':writer_id,'lt_msg_tx':content,'lt_msg_img':'','lt_msg_st':'undel',\
				'lt_img_id':''}
			list_content, bid, idx = new_blob_id+":"+writer_id+":"+comment_count, new_blob_id, comment_count
	elif content and is_response:
		# fish out required content
		target_blob_id, target_index, target_content_type = res_blob["target_blob_id"], res_blob["target_index"], res_blob["target_content_type"]
		target_blob = "pgh:"+group_id+":"+target_blob_id
		target_blob_exists = my_server.exists(target_blob) and my_server.hget(target_blob,'hidden') != 'yes'
		if target_blob_exists:
			if target_index == '-1':
				# response to a response; there was no index
				target_content, target_writing_time, target_id, target_img_caption, target_status, target_img_id,target_image_width, \
				target_image_height, target_img_s_caption, target_hidden = my_server.hmget(target_blob,"res_content","res_time","id",\
					"img_caption","status",'img_id','img_width','img_height','img_s_caption','hidden')
			else:
				# response to normal chat; there was an index
				target_content, target_writing_time, target_id, target_img_caption, target_status, target_image_width, target_image_height, \
				target_img_id, target_img_s_caption, target_hidden = my_server.hmget(target_blob,target_content_type+target_index,\
					'time'+target_index,"id","img_caption"+target_index,"status"+target_index,'img_width'+target_index,\
					'img_height'+target_index,'img_id'+target_index,'img_s_caption'+target_index, 'hidden'+target_index)
			if target_content is None:
				return 0, PERSONAL_GROUP_OBJECT_CEILING, None, None, None, '-1', None, None#'-1' img_id ensures image won't be saved separately
			else:
				# always create a new blob for direct responses
				new_blob_id = str(my_server.incr("pgbid:"+group_id))
				personal_group_hash, append = "pgh:"+group_id+":"+new_blob_id, False
				################################
				# creating blob content
				comment_count, t_now = '-1', time.time() #set '-1' for response blobs and '0' for action blobs
				if type_ == 'img_res':
					img_wid, img_height, img_caption = content["img_width"], content["img_height"], content["img_caption"]
					content = content["img_url"]
					img_s_caption = small_photo_caption(img_caption, float(img_wid)/float(img_height))
					img_id = str(my_server.incr("pgiid:"+group_id))
					img_hw_ratio = int((float(img_height)/(2*float(img_wid)))*100)
					hash_content = {'id':writer_id,'res_content':content,'res_time':t_now,'res_type':'img','which_blob':'res',\
					'img_width':img_wid+EXTRA_PADDING,'img_height':img_height,'img_caption':img_caption,'blob_id':new_blob_id,\
					't_content':target_content,'t_writing_time':target_writing_time,'img_s_caption':img_s_caption,'hidden':'no',\
					't_type':target_content_type,'status':'undel','t_status':target_status,'t_img_s_caption':'',\
					'img_id':img_id,'img_hw_ratio':img_hw_ratio}
					if target_content_type in ('img','shared_img'):#about 25% faster than doing two '==' comparisons (benchmarked)
						hash_content["t_img_id"] = target_img_id
						hash_content["t_img_caption"] = target_img_caption
						hash_content["t_img_s_caption"] = target_img_s_caption
						hash_content["t_hidden"] = target_hidden
						hash_content["t_img_s_width"] = small_image_width(float(target_image_width)-EXTRA_PADDING, float(target_image_height))
					group_content = {'lt_msg_tp':type_,'lt_msg_t':t_now,'lt_msg_wid':writer_id,'lt_msg_tx':img_caption,'lt_msg_img':content,'lt_msg_st':'undel',\
					'lt_img_id':img_id}
				elif type_ == 'text_res':
					hash_content = {'id':writer_id,'res_content':content,'res_time':t_now,'res_type':'text','status':'undel',\
					'blob_id':new_blob_id,'t_content':target_content,'t_writing_time':target_writing_time,'which_blob':'res',\
					't_type':target_content_type,'t_status':target_status,'t_img_s_caption':''}
					if target_content_type in ('img','shared_img'):#about 20% faster than doing two '==' comparisons (benchmarked)
						hash_content["t_img_id"] = target_img_id
						hash_content["t_img_caption"] = target_img_caption
						hash_content["t_img_s_caption"] = target_img_s_caption
						hash_content["t_hidden"] = target_hidden
						hash_content["t_img_s_width"] = small_image_width(float(target_image_width)-EXTRA_PADDING, float(target_image_height))
					group_content = {'lt_msg_tp':type_,'lt_msg_t':t_now,'lt_msg_wid':writer_id,'lt_msg_tx':content,'lt_msg_img':'','lt_msg_st':'undel',\
					'lt_msg_id':''}
				list_content, bid, idx = new_blob_id+":"+writer_id+":"+comment_count, new_blob_id, '-1'
		else:
			# target blob no longer exists
			return 0, PERSONAL_GROUP_OBJECT_CEILING, None, None, None, '-1', None, None#'-1' img_id ensures image won't be saved separately
	elif content and is_shared_content:
		first_element = my_server.lindex(personal_group_list,0) #blob_id:writer_id:comment_count
		if first_element is None:
			prev_blob_id, prev_writer_id, prev_comment_count = None, None, None
		else:
			info = first_element.split(":")
			prev_blob_id, prev_writer_id, prev_comment_count = info[0], info[1], int(info[2])
		if writer_id == prev_writer_id and 0 < prev_comment_count < PERSONAL_GROUP_BLOB_SIZE_LIMIT:
			# append to existing blob
			personal_group_hash, append = "pgh:"+group_id+":"+prev_blob_id, True
			################################
			# creating blob content
			prev_comment_count += 1
			comment_count, t_now = str(prev_comment_count), time.time()
			# if type_ == 'img':
			img_wid, img_height, img_caption, owner_uname = content["img_width"], content["img_height"], content["img_caption"], content["owner_uname"]
			content = content["img_url"]
			# print img_caption
			img_s_caption = small_photo_caption(img_caption, float(img_wid)/float(img_height))
			# print img_s_caption
			img_id = str(my_server.incr("pgiid:"+group_id))
			img_hw_ratio = int((float(img_height)/(2*float(img_wid)))*100)
			hash_content = {type_+comment_count:content, 'time'+comment_count:t_now, 'type'+comment_count:type_, 'idx':comment_count,\
			'img_width'+comment_count:int(img_wid)+EXTRA_PADDING,'img_height'+comment_count:img_height, 'img_caption'+comment_count:img_caption,\
			'status'+comment_count:'undel','img_id'+comment_count:img_id,'img_s_caption'+comment_count:img_s_caption,'hidden'+comment_count:'no',\
			'img_hw_ratio'+comment_count:img_hw_ratio,'owner_uname'+comment_count:owner_uname}
			group_content = {'lt_msg_tp':type_,'lt_msg_t':t_now,'lt_msg_wid':writer_id,'lt_msg_tx':img_caption,'lt_msg_img':content,'lt_msg_st':'undel',\
			'lt_img_id':img_id}
			list_content, bid, idx = prev_blob_id+":"+writer_id+":"+comment_count, prev_blob_id, comment_count
		else:
			# create a new blob
			new_blob_id = str(my_server.incr("pgbid:"+group_id))
			personal_group_hash, append = "pgh:"+group_id+":"+new_blob_id, False
			################################
			# creating blob content
			comment_count, t_now = '1', time.time()
			# if type_ == 'img':
			img_wid, img_height, img_caption, owner_uname = content["img_width"], content["img_height"], content["img_caption"], content["owner_uname"]
			content = content["img_url"]
			# print img_caption
			img_s_caption = small_photo_caption(img_caption, float(img_wid)/float(img_height))
			# print img_s_caption
			img_id = str(my_server.incr("pgiid:"+group_id))
			img_hw_ratio = int((float(img_height)/(2*float(img_wid)))*100)
			hash_content = {'status'+comment_count:'undel',type_+comment_count:content,'time'+comment_count:t_now,\
			'type'+comment_count:type_,'which_blob':'nor','img_id'+comment_count:img_id, 'blob_id':new_blob_id,\
			'img_s_caption'+comment_count:img_s_caption,'hidden'+comment_count:'no', 'id':writer_id, \
			'img_caption'+comment_count:img_caption,'img_width'+comment_count:int(img_wid)+EXTRA_PADDING,\
			'img_height'+comment_count:img_height,'img_hw_ratio'+comment_count:img_hw_ratio,'idx':comment_count,\
			'owner_uname'+comment_count:owner_uname}
			group_content = {'lt_msg_tp':type_,'lt_msg_t':t_now,'lt_msg_wid':writer_id,'lt_msg_tx':img_caption,'lt_msg_img':content,'lt_msg_st':'undel',\
			'lt_img_id':img_id}
			list_content, bid, idx = new_blob_id+":"+writer_id+":"+comment_count, new_blob_id, comment_count
	################################
	# setting blob content
	pipeline1 = my_server.pipeline()
	pipeline1.delete('pgd:'+group_id)
	if append:
		pipeline1.lset(personal_group_list,0,list_content)
	else:
		pipeline1.lpush(personal_group_list,list_content)
	if is_response:
		pipeline1.lpush("pgrl:"+group_id+":"+target_blob_id+":"+target_index,personal_group_hash)
	pipeline1.hmset(personal_group_hash, hash_content)
	pipeline1.hmset(personal_group,group_content) #object_count
	pipeline1.hincrby(personal_group,'oc',amount=1) # incrementing object_count
	result = pipeline1.execute()
	return result[-1], PERSONAL_GROUP_OBJECT_CEILING, group_id, bid, idx, img_id, img_wid, img_hw_ratio


def set_uri_metadata_in_personal_group(own_id, text, group_id, blob_id, idx, type_):
	"""
	Checks content and turns URLs clickable
	"""
	my_server, own_id = redis.Redis(connection_pool=POOL), str(own_id)
	rate_limit_key = "rlus:"+own_id+":"+group_id
	rate_limited = my_server.get(rate_limit_key)#rate limit url submission
	if not rate_limited:
		start_time = time.time()
		urls = re.findall(URL_REGEX1, text)# check if this regex can be optimized
		parsing_time = time.time() - start_time
		if urls:
			url = urls[0]
			is_yt = '1' if ('youtube.com/watch' in url or 'youtu.be/' in url) else '0'# detect youtube url
 			components = urlparse(url)
			# first search in cache, else fall back to BeautifulSoup
			location = components.netloc+components.path+components.query+components.fragment
			url = url if components.netloc else 'http://'+url
			meta_data = get_cached_meta_data(location)
			if meta_data:
				# cached metadata exists, use that
				# print "meta data from cache: %s" % meta_data
				meta_data['url'] = url
			else:
				# if nothing is cached
				meta_data, time_taken = get_meta_data(url=url)
				# print "meta data from the internet: {} in {} seconds".format(meta_data,time_taken)
				# if meaningful metadata was successfully retrieved, cache it
				if 'doc' in meta_data:
					cache_meta_data(location, meta_data, time_taken, parsing_time, is_yt, meta_data['doc'])
					meta_data['url'] = url
			meta_data['yt'] = is_yt
			if 'doc' in meta_data and meta_data['doc'] != '0':
				if idx != '-1':
					meta_data['doc'+idx], meta_data['url'+idx], meta_data['yt'+idx] = meta_data['doc'], meta_data['url'], meta_data['yt']
					del meta_data['doc']
					del meta_data['url']
					del meta_data['yt']
					if 'url_desc' in meta_data:
						meta_data['url_desc'+idx] = meta_data['url_desc']
						del meta_data['url_desc']
					if 'url_title' in meta_data:
						meta_data['url_title'+idx] = meta_data['url_title']
						del meta_data['url_title']
					if 'url_img' in meta_data:
						meta_data['url_img'+idx] = meta_data['url_img']
						del meta_data['url_img']
					if 'url_iw' in meta_data:
						meta_data['url_iw'+idx] = meta_data['url_iw']
						del meta_data['url_iw']
					if 'url_ih' in meta_data:
						meta_data['url_ih'+idx] = meta_data['url_ih']
						del meta_data['url_ih']
					if 'url_hw_ratio' in meta_data:
						meta_data['url_hw_ratio'+idx] = meta_data['url_hw_ratio']
						del meta_data['url_hw_ratio']
				######## set the relevant blob ########
				blob_hash = "pgh:"+group_id+":"+blob_id
				my_server.hmset(blob_hash,meta_data)
				my_server.delete('pgd:'+group_id)
				######### checking ratelimit ##########
				tries = 'usl:'+own_id+":"+group_id
				tries_used = my_server.incrby(tries,amount=1)#url submissions left
				if tries_used == 1:
					# it's the first try in some time
					my_server.expire(tries,FOUR_MINS)
				elif tries_used >= URL_POSTINGS_ALLOWED:
					# if it' the 3rd url (or more) within 4 mins, rate limit the spamming user for 5 mins 
					my_server.setex(rate_limit_key,'1',FIVE_MINS)




########################################## Personal Group Exit Settings ###########################################

def exit_already_triggered(own_id, target_id, group_id, sus_time=False):
	"""
	Check whether personal group has already been exited by at least one of the participants
	"""
	my_server = redis.Redis(connection_pool=POOL)
	if sus_time:
		suspended_by_self, suspended_by_them, suspension_time = my_server.hmget('pgah:'+group_id,'susgrp'+str(own_id),'susgrp'+target_id,'sus_time')
		if suspended_by_self == '1':
			return True, False, suspension_time
		elif suspended_by_them == '1':
			return False, True, suspension_time
		else:
			return False, False, suspension_time
	else:
		suspended_by_self, suspended_by_them = my_server.hmget('pgah:'+group_id,'susgrp'+str(own_id),'susgrp'+target_id)
		if suspended_by_self == '1':
			return True, False
		elif suspended_by_them == '1':
			return False, True
		else:
			return False, False

def get_suspension_details(own_id, target_id, group_id):
	"""
	Retreive details of suspended group
	"""
	own_suspension, their_suspension, suspension_time = redis.Redis(connection_pool=POOL).hmget("pgah:"+group_id,'susgrp'+str(own_id),\
		'susgrp'+str(target_id),'sus_time')
	suspended_by = 'self' if own_suspension else 'them'
	try:
		time_diff = time.time() - float(suspension_time)
	except TypeError:
		time_diff = 0
	can_rejoin = True if time_diff > PERSONAL_GROUP_REJOIN_RATELIMIT else False
	return suspended_by, suspension_time, can_rejoin, None if can_rejoin else ONE_DAY-time_diff

def suspend_personal_group(suspended_by_id, their_id, group_id):
	"""
	Suspend personal group when a user uses the 'exit' feature
	"""
	my_server = redis.Redis(connection_pool=POOL)
	suspended_by_id = str(suspended_by_id)
	already_suspended_by_them, already_suspended_by_self = my_server.hmget("pgah:"+group_id,'susgrp'+str(their_id),'susgrp'+suspended_by_id)
	if already_suspended_by_them == '1':
		return False, None
	elif already_suspended_by_self == '1':
		return None, None
	else:
		if my_server.exists('pggrrl:'+group_id+":"+suspended_by_id):
			return True, my_server.ttl('pggrrl:'+group_id+":"+suspended_by_id)
		else:
			# exit personal group and reset all sharing permissions
			exit_time = time.time()
			mapping = {'susgrp'+suspended_by_id:'1','is_sus':'1','sus_time':exit_time,'smsrec'+suspended_by_id:'0','smsrec'+their_id:'0',\
			'phrec'+suspended_by_id:'0','phrec'+their_id:'0','svprm'+suspended_by_id:'0','svprm'+their_id:'0','lt_msg_t':exit_time,\
			'lt_msg_tp':'suspend','lt_msg_wid':suspended_by_id,'last_seen'+suspended_by_id:exit_time,'lt_msg_tx':'','lt_msg_img':'','lt_msg_st':'',\
			'lt_msg_id':''}
			pipeline1 = my_server.pipeline()
			pipeline1.hmset("pgah:"+group_id,mapping)
			pipeline1.zadd('exited_personal_groups',group_id,exit_time)
			pipeline1.zadd("pgfgm:"+suspended_by_id,group_id+":"+their_id,exit_time)
			pipeline1.zadd("pgfgm:"+their_id,group_id+":"+suspended_by_id,exit_time)
			pipeline1.execute()
			return True, None


def unsuspend_personal_group(own_id, target_id,group_id):
	"""
	Reopen personal group for user and allow them to enter it
	"""
	my_server = redis.Redis(connection_pool=POOL)
	own_id, group_hash = str(own_id), "pgah:"+group_id
	suspended_by_self = my_server.hget(group_hash,'susgrp'+own_id)
	if suspended_by_self:
		#unsuspend
		unsuspend_time = time.time()
		keys = ['susgrp'+own_id,'susgrp'+target_id,'is_sus','sus_time']
		pipeline1 = my_server.pipeline()
		pipeline1.hdel(group_hash,*keys)
		pipeline1.zrem('exited_personal_groups',group_id)
		pipeline1.setex('pggrrl:'+group_id+":"+own_id,1,ONE_DAY)
		pipeline1.zadd("pgfgm:"+own_id,group_id+":"+target_id,unsuspend_time)
		pipeline1.zadd("pgfgm:"+target_id,group_id+":"+own_id,unsuspend_time)
		pipeline1.execute()
		mapping = {'lt_msg_tp':'unsuspend','lt_msg_wid':own_id,'lt_msg_t':unsuspend_time,'lt_msg_tx':'','lt_msg_img':'','lt_msg_st':'',\
		'lt_img_id':''}
		my_server.hmset(group_hash,mapping)
		purge_exit_list(group_id, own_id)
		return True
	else:
		return False


########################################## Personal Group SMS Settings ###########################################


def set_sms_notif_from_chat(group_id, their_id, blob_id):
	"""
	Resolving SMS notif in personal group chat
	"""
	my_server = redis.Redis(connection_pool=POOL)
	blob_hash = "pgh:"+group_id+":"+blob_id
	blob_owner_id, blob_status = my_server.hmget(blob_hash,'id','status')
	if blob_owner_id == str(their_id) and blob_status == 'open':
		# it's a notif blob owned by their_id
		pipeline1 = my_server.pipeline()
		pipeline1.hset(blob_hash, 'status','resolved')
		pipeline1.delete('pgd:'+group_id)
		pipeline1.execute()


def personal_group_sms_invite_allwd(their_id, group_id):
	"""
	Checking whether it's OK to send the target an sms-perm invite in personal group
	"""
	my_server = redis.Redis(connection_pool=POOL)
	hash_name, their_id = "pgah:"+group_id, str(their_id)
	tries_left = my_server.hget(hash_name,'smsivt'+their_id)
	if int(tries_left) < 1:
		# all tries depleted
		return False
	else:
		# an invite was recently sent, apply rate limit and don't send again
		cooloff_key = "pgsmsic:"+group_id+":"+their_id
		if my_server.exists(cooloff_key):
			return False
		else:
			# send the invite and set the rate limit
			pipeline1 = my_server.pipeline()
			pipeline1.hincrby(hash_name,'smsivt'+their_id,amount=-1)
			pipeline1.setex(cooloff_key,1,ONE_DAY)
			pipeline1.execute()
			return True


def get_user_sms_setting(target_id, group_id, with_cred=False):
	"""
	Returns current sms reception settings of target
	"""
	my_server = redis.Redis(connection_pool=POOL)
	target_id = str(target_id)
	if with_cred:
		allwd, sms_text, mob_idx = my_server.hmget("pgah:"+group_id,'smsrec'+target_id,'smsrectxt'+target_id,'smsrecmobidx'+target_id)
		allwd = False if allwd == '0' else True
		return allwd, sms_text, mob_idx
	else:
		allwd = False if my_server.hget("pgah:"+group_id,'smsrec'+target_id) == '0' else True
		return allwd


def lock_sms_sending(user_id,target_id):
	"""
	Locking sms sending in personal groups
	"""
	return redis.Redis(connection_pool=POOL).setex("ssl:"+str(user_id)+":"+target_id,time.time(),PERSONAL_GROUP_SMS_LOCK_TTL)


def sms_sending_locked(user_id,target_id):
	"""
	Checking whether user sms sending behavior should be rate limited
	"""
	return redis.Redis(connection_pool=POOL).get("ssl:"+str(user_id)+":"+target_id)


def enable_personal_group_sms_rec(own_id, group_id, target_num_idx, sms_text):
	"""
	Enable user to receive SMS
	"""
	own_id = str(own_id)
	hash_name = "pgah:"+group_id
	mapping = {'smsrec'+own_id:'1','smsrectxt'+own_id:sms_text,'smsrecmobidx'+own_id:target_num_idx}
	redis.Redis(connection_pool=POOL).hmset(hash_name,mapping)


def disable_personal_group_sms_rec(own_id, group_id):
	"""
	Disable user to receive SMS
	"""
	my_server = redis.Redis(connection_pool=POOL)
	own_id = str(own_id)
	hash_name = "pgah:"+group_id
	pipeline1 = my_server.pipeline()
	pipeline1.hset(hash_name,'smsrec'+own_id,'0')
	pipeline1.hdel(hash_name,'smsrectxt'+own_id)
	pipeline1.hdel(hash_name,'smsrecmobidx'+own_id)
	pipeline1.execute()

########################################## Personal Group Photo Settings ###########################################


def set_personal_group_photo_permission(own_id, group_id, blob_id, allow=False, resolve_notif=False):
	"""
	Setting photo reception permission

	Also resolves notifcation blob in personal group if need be
	"""
	my_server = redis.Redis(connection_pool=POOL)
	personal_group_hash, own_id = "pgah:"+group_id, str(own_id)
	if resolve_notif is False and allow is False:
		pass
	elif resolve_notif is False and allow is True:
		my_server.hset(personal_group_hash,'phrec'+own_id,'1')
	else:
		blob_hash = "pgh:"+group_id+":"+str(blob_id)
		type_, notif = my_server.hmget(blob_hash,'which_blob','notif')
		pipeline1 = my_server.pipeline()
		if allow is False:
			if type_=='notif' and notif == '1':
				# only process if it's a notif of type '1'
				pipeline1.hset(personal_group_hash,'phrec'+own_id,'0')
				pipeline1.hset(blob_hash, 'status','resolved')
		else:
			if type_=='notif' and notif == '1':
				# only process if it's a notif of type '1'
				pipeline1.hset(personal_group_hash,'phrec'+own_id,'1')
				pipeline1.hset(blob_hash, 'status','resolved')
		pipeline1.delete('pgd:'+group_id)
		pipeline1.execute()


def personal_group_photo_xfer_invite_allwd(their_id, group_id):
	"""
	Checking whether it's OK to send the target a photo transfer invite in chat
	"""
	my_server = redis.Redis(connection_pool=POOL)
	hash_name, their_id = "pgah:"+group_id, str(their_id)
	tries_left = my_server.hget(hash_name,'xfivt'+their_id)
	if int(tries_left) < 1:
		# all tries depleted
		return False
	else:
		# an invite was recently sent, apply rate limit and don't send again
		cooloff_key = "pgxic:"+group_id+":"+their_id
		if my_server.exists(cooloff_key):
			return False
		else:
			# send the invite and set the rate limit
			pipeline1 = my_server.pipeline()
			pipeline1.hincrby(hash_name,'xfivt'+their_id,amount=-1)
			pipeline1.setex(cooloff_key,1,ONE_DAY)
			pipeline1.execute()
			return True


def personal_group_image_transfer_not_permitted(their_id, group_id):
	"""
	Checking whether a user can send a photo in a personal group
	"""
	hash_name, their_id = "pgah:"+group_id, str(their_id)
	no_perm = True if redis.Redis(connection_pool=POOL).hget(hash_name,'phrec'+their_id) == '0' else False
	return no_perm


def toggle_personal_group_photo_settings(own_id, target_id, setting_type, group_id=None):
	"""
	Manage photo settings of personal group

	Setting type '1' means photo reception permissions
	Setting type '2' means photo mass deletion
	Setting type '3' means photo mass restoration
	"""
	my_server = redis.Redis(connection_pool=POOL)
	if not group_id:
		group_id, exists = personal_group_already_exists(own_id, target_id, my_server)
	if group_id:
		hash_name, own_id = "pgah:"+group_id, str(own_id)
		if setting_type == '1':
			photo_rec_perm = my_server.hget(hash_name,'phrec'+own_id)
			if photo_rec_perm == '0':
				my_server.hset(hash_name,'phrec'+own_id,'1')
				new_value = '1'
			else:
				my_server.hset(hash_name,'phrec'+own_id,'0')
				new_value = '0'
			return new_value, None, None
		elif setting_type == '2':
			undelete = False
			deleted, ttl = delete_all_photos_from_personal_group(own_id, group_id, undelete=undelete, server=my_server)
			if deleted:
				new_value = '1'
			else:
				new_value = None
			return new_value, ttl, undelete
		elif setting_type == '3':
			undelete = True
			deleted, ttl = delete_all_photos_from_personal_group(own_id, group_id, undelete=undelete, server=my_server)
			if deleted:
				new_value = '0'
			else:
				new_value = None
			return new_value, ttl, undelete
		else:
			return None, None, None
	else:
		return None, None, None


def get_personal_group_photo_rec_settings(own_id, target_id):
	"""
	Retrieves current photo settings of personal group
	"""
	my_server = redis.Redis(connection_pool=POOL)
	group_id, exists = personal_group_already_exists(own_id, target_id, my_server)
	if exists:
		return my_server.hget("pgah:"+group_id,'phrec'+str(own_id))
	else:
		return None, None



def set_personal_group_image_storage(img_url, img_id, img_wid, hw_ratio, img_quality, blob_id, index, own_id, group_id, is_shared=False, op=None):
	"""
	Saves photo separately in personal group photo settings, for later viewing
	"""
	if img_id != '-1':
		list_payload = img_id+":"+blob_id+":"+index+":"+str(own_id)
		if is_shared:
			mapping = {'img_url':img_url,'owner_id':own_id,'blob_id':blob_id,'index':index,'status':'undel','img_quality':img_quality,'img_id':img_id,\
			'hidden':'no','img_width':img_wid,'img_b_width':int(img_wid)+EXTRA_PADDING,'hw_ratio':hw_ratio,'is_shared':True,'owner_uname':op} 
		else:
			mapping = {'img_url':img_url,'owner_id':own_id,'blob_id':blob_id,'index':index,'status':'undel','img_quality':img_quality,'img_id':img_id,\
			'hidden':'no','img_width':img_wid,'img_b_width':int(img_wid)+EXTRA_PADDING,'hw_ratio':hw_ratio} 
		photo_list = "pgpl:"+group_id
		my_server = redis.Redis(connection_pool=POOL)
		pipeline1 = my_server.pipeline()
		pipeline1.lpush(photo_list,list_payload)
		pipeline1.hmset('pgih:'+group_id+":"+img_id,mapping)
		pipeline1.execute()
		if my_server.llen(photo_list) > PERSONAL_GROUP_MAX_PHOTOS:
			removed_img_id = my_server.rpop(photo_list).split(":")[0]
			my_server.delete('pgih:'+group_id+":"+removed_img_id)
			


def retrieve_all_personal_group_images(group_id):
	"""
	Retrieve all photos shared in personal group (capped at 25)
	"""
	my_server = redis.Redis(connection_pool=POOL)
	photo_list = "pgpl:"+group_id
	all_photos = my_server.lrange(photo_list,0,-1)
	pipeline1 = my_server.pipeline()
	for payload in all_photos:
		img_hash = 'pgih:'+group_id+":"+payload.split(":")[0]
		pipeline1.hgetall(img_hash)
	return pipeline1.execute()


def can_share_photo(group_ids,user_id):
	"""
	Checks with user with user_id can share a photo in list of groups (group_ids)
	"""
	user_id = str(user_id)
	my_server = redis.Redis(connection_pool=POOL)
	# retrieve group members (if they exist)
	if len(group_ids) > 3:
		pipeline1 = my_server.pipeline()
		for group_id in group_ids:
			pipeline1.get("pgp:"+group_id)
		result1, groups, counter = pipeline1.execute(), {}, 0
		for group_id in group_ids:
			groups[group_id] = result1[counter]
			counter += 1
	else:
		groups = {}
		for group_id in group_ids:
			groups[group_id] = my_server.get("pgp:"+group_id)
	# check user_id's membership in retrieved groups
	legit_groups, nonlegit_groups = {}, []
	for group_id in group_ids:
		try:
			participants = groups[group_id].split(":")#don't use maxsplit [e.g. split(":",1)] since it's 9 times slower than vanilla/regular split (tested)
		except AttributeError:
			participants = ''#i.e. if the group with group_id doesn't exist
		if user_id in participants:
			legit_groups[group_id] = participants[0] if participants[1] == user_id else participants[1]# legit_groups is a dictionary {group_id:their_id} containing groups user_id is a member of
		else:
			nonlegit_groups.append(group_id)# nonlegit_groups is a list containing group_ids that user_id isn't a member of (or they don't exist)
	photo_allwd, photo_disallwd = [],[]
	if len(legit_groups) > 3:
		pipeline2 = my_server.pipeline()
		for group_id,their_id in legit_groups.iteritems():
			pipeline2.hget("pgah:"+group_id,'phrec'+their_id)
		result2, counter = pipeline2.execute(), 0
		for group_id,their_id in legit_groups.iteritems():
			pht_perm = result2[counter]
			if pht_perm == '0':
				photo_disallwd.append(group_id)
			else:
				photo_allwd.append(group_id)
			counter += 1
	else:
		for group_id,their_id in legit_groups.iteritems():
			pht_perm = my_server.hget("pgah:"+group_id,'phrec'+their_id)
			if pht_perm == '0':
				photo_disallwd.append(group_id)
			else:
				photo_allwd.append(group_id)
	return photo_allwd, photo_disallwd, legit_groups, nonlegit_groups


def rate_limit_personal_group_sharing(user_id):
	"""
	Setting rate limit for photo sharing in personal groups
	"""
	redis.Redis(connection_pool=POOL).setex('rlfs:'+str(user_id),'1',ONE_MIN)


def get_rate_limit_in_personal_group_sharing(user_id):
	"""
	Checking whether photo sharing in personal groups is rate limited for user with id 'user_id'
	"""
	ttl = redis.Redis(connection_pool=POOL).ttl('rlfs:'+str(user_id))
	if ttl > 0:
		return True, ttl
	else:
		return False, None

############################################ User Personal Group Lists #############################################


def retrieve_user_group_list_contents(user_id, start_idx, end_idx):
	"""
	Construct list of replies from active user groups
	"""
	user_id = str(user_id)
	cached_data_key = 'pgld:'+user_id+":"+ str(start_idx)+":"+str(end_idx)
	my_server = redis.Redis(connection_pool=POOL)
	json_data = my_server.get(cached_data_key)
	if json_data:
		data = json.loads(json_data)
		return data[0], data[1]
	else:
		groups_and_friends_with_times = my_server.zrevrange("pgfgm:"+user_id,start_idx,end_idx,withscores=True)
		group_list, friend_list = [], []
		for pairs,int_time in groups_and_friends_with_times:
			ids = pairs.split(":")
			group_list.append((ids[0], ids[1]))
			friend_list.append(ids[1])
		friend_credentials = retrieve_bulk_credentials(friend_list, decode_unames=True)#friend_credentials is a dict_of_dictionaries
		pipeline1 = my_server.pipeline()
		for group_id, friend_id in group_list:
			pipeline1.hmget("pgah:"+group_id,'lt_msg_tp','lt_msg_t','lt_msg_wid','anon'+friend_id,'last_seen'+user_id,'last_seen'+friend_id,\
				'lt_msg_tx','lt_msg_img','lt_msg_st','lt_img_id')
		result1 = pipeline1.execute()
		payload, counter = [], 0
		for group_id, friend_id in group_list:
			data = {'lt_msg_type':result1[counter][0],'lt_msg_time':result1[counter][1],'lt_msg_wid':result1[counter][2],\
			'is_friend_anon':result1[counter][3],'own_last_seen':result1[counter][4],'friend_last_seen':result1[counter][5],\
			'friend_username':friend_credentials[int(friend_id)]['uname'],'friend_av_url':friend_credentials[int(friend_id)]['avurl'],\
			'group_id':group_id,'friend_id':friend_id,'lt_msg_tx':result1[counter][6],'lt_msg_img':result1[counter][7],\
			'lt_msg_st':result1[counter][8],'lt_img_id':result1[counter][9]} # constructing retrieved data dictionary
			payload.append(data)
			counter += 1
		num_of_grps = my_server.zcard("pgfgm:"+user_id) if payload else 0
		my_server.setex(cached_data_key,json.dumps([payload,num_of_grps]),USER_GROUP_LIST_CACHING_TIME)#cached for 10 secs
		return payload, num_of_grps


def get_user_friend_list(user_id):
	"""
	Returns list of friend names and avatar urls for any user

	Must return anonymization status where warranted
	"""
	user_id = str(user_id)
	cached_data_key = 'pgfl:'+user_id
	my_server = redis.Redis(connection_pool=POOL)
	json_data = my_server.get(cached_data_key)
	if json_data:
		return json.loads(json_data)
	else:
		groups_and_friends = my_server.zrevrange("pgfgm:"+user_id,0,-1,withscores=True)
		fid_gid, friend_list, gid_seen = {}, [], {}
		for tup,touch_time in groups_and_friends:
			data = tup.split(":")
			gid, fid = data[0], data[1]
			fid_gid[fid] = gid
			gid_seen[gid] = touch_time
			friend_list.append(fid)
		friend_credentials = retrieve_bulk_credentials(friend_list, decode_unames=True)#friend_credentials is a dict_of_dictionaries
		group_and_friend, dict_of_grps_and_frnds = [], {}
		for fid in friend_list:
			group_and_friend.append((fid_gid[fid],friend_credentials[int(fid)]))
			dict_of_grps_and_frnds[fid_gid[fid]] = fid
		groups_anon_status = are_users_anon(dict_of_grps_and_frnds, my_server=my_server) #returns dictionary {group_id:anon_state of friend}
		for tup in group_and_friend:
			tup[1]['is_anon'] = groups_anon_status[tup[0]]#adding 'anon' information
			tup[1]['last_seen'] = gid_seen[tup[0]]#adding 'seen' information
			tup[1]['fid'] = dict_of_grps_and_frnds[tup[0]]
		my_server.setex(cached_data_key, json.dumps(group_and_friend, ensure_ascii=False),USER_FRIEND_LIST_CACHING_TIME)#cached for 5 mins
		return group_and_friend


########################################### Personal Group Sanitization ############################################


def mark_personal_group_attendance(own_id, target_id, group_id, time_now):
	"""
	Mark attendance to facilitate deletion of unattended personal groups

	This is only fired if a new input is entered in the personal group
	"""
	own_id = str(own_id)
	pipeline1 = redis.Redis(connection_pool=POOL).pipeline()
	pipeline1.zadd("personal_group_attendance",group_id,time_now)
	pipeline1.zadd("pgfgm:"+own_id,group_id+":"+target_id,time_now)
	pipeline1.zadd("pgfgm:"+target_id,group_id+":"+own_id,time_now)
	pipeline1.execute()

# call every 3 days
def personal_group_soft_deletion():
	"""
	Deleting chat in personal groups that have been unattended for a week
	"""
	my_server = redis.Redis(connection_pool=POOL)
	seven_days_ago = time.time() - PERSONAL_GROUP_SOFT_DELETION_CUTOFF
	group_ids = my_server.zrangebyscore("personal_group_attendance",'-inf', seven_days_ago)
	for group_id in group_ids:
		reset_all_group_chat(group_id, my_server=my_server)


# call every 6 days
def personal_group_hard_deletion():
	"""
	Permanently deleting all data of groups gone cold (unattended for a month)
	"""
	thirty_days_ago = time.time() - PERSONAL_GROUP_HARD_DELETION_CUTOFF
	my_server = redis.Redis(connection_pool=POOL)
	group_ids = my_server.zrangebyscore("personal_group_attendance",'-inf', thirty_days_ago)
	if group_ids:
		pgp_keys = []
		for group_id in group_ids:
			pgp_keys.append("pgp:"+group_id)
		user_id_pairs = my_server.mget(*pgp_keys)
		count, groups_and_participants = 0, []
		for group_id in group_ids:
			try:
				participants = user_ids_pairs[count].split(":")
				groups_and_participants.append((group_id,participants[0],participants[1]))
			except (AttributeError, IndexError):
				pass
			count += 1
		for group_id in group_ids:
			permanently_delete_entire_personal_group(group_id, my_server=my_server)
		pipeline1 = my_server.pipeline()
		pipeline1.zrem("personal_group_attendance",*group_ids)
		pipeline1.zrem("exited_personal_groups",*group_ids)
		pipeline1.execute()
		log_personal_group_exit_or_delete(group_id=group_ids, action_type='del_idle')
		bulk_delete_pergrp_notif(groups_and_participants)

#call daily
def exited_personal_group_hard_deletion(group_ids=None):
	"""
	Permanently deleting all data of groups that have been exited
	"""
	my_server = redis.Redis(connection_pool=POOL)
	if not group_ids:
		seven_days_ago = time.time() - EXITED_PERSONAL_GROUP_HARD_DELETION_CUTOFF
		group_ids = my_server.zrangebyscore("exited_personal_groups",'-inf', seven_days_ago)
	if group_ids:
		pgp_keys = []
		for group_id in group_ids:
			pgp_keys.append("pgp:"+group_id)
		user_id_pairs = my_server.mget(*pgp_keys)
		count, groups_and_participants = 0, []
		for group_id in group_ids:
			try:
				participants = user_id_pairs[count].split(":")
				groups_and_participants.append((group_id,participants[0],participants[1]))
			except (AttributeError, IndexError):
				pass
			count += 1
		for group_id in group_ids:
			permanently_delete_entire_personal_group(group_id, my_server=my_server)
		pipeline1 = my_server.pipeline()
		pipeline1.zrem("exited_personal_groups",*group_ids)
		pipeline1.zrem("personal_group_attendance",*group_ids)
		pipeline1.execute()
		log_personal_group_exit_or_delete(group_id=group_ids, action_type='del_exit')
		bulk_delete_pergrp_notif(groups_and_participants)

########################################### Personal Group Anonymization ###########################################

def set_personal_group_anon_state(own_id, target_id):
	"""
	Setting anon status of user in personal group
	"""
	my_server = redis.Redis(connection_pool=POOL)
	group_id, exists = personal_group_already_exists(own_id, target_id, my_server)
	if exists:
		hash_name = "pgah:"+group_id
		own_id = str(own_id)
		anon_status = my_server.hget(hash_name,'anon'+own_id)
		if anon_status == '1':
			my_server.hset(hash_name,'anon'+own_id,'0')
			new_value = '0'
		elif anon_status == '0':
			my_server.hset(hash_name,'anon'+own_id,'1')
			new_value = '1'
		else:
			my_server.hset(hash_name,'anon'+own_id,'1')
			new_value = '1'
		return new_value
	else:
		return None

def get_personal_group_anon_state(own_id, target_id):
	"""
	Getting anon status of user in personal group
	"""
	my_server = redis.Redis(connection_pool=POOL)
	group_id, exists = personal_group_already_exists(own_id, target_id, my_server)
	if exists:
		own_anon_status, their_anon_status = my_server.hmget("pgah:"+group_id,'anon'+str(own_id),'anon'+target_id)
		if own_anon_status == '1':
			result1 = True
		else:
			result1 = False
		if their_anon_status == '1':
			result2 = True
		else:
			result2 = False
		return result1, result2, group_id
	else:
		return None, None, None


def are_users_anon(groups_and_friends,my_server=None):
	"""
	Retrieves anon_state of users in various groups

	Must be fed {group_id:friend_id} dictionary
	"""
	if not my_server:
		my_server = redis.Redis(connection_pool=POOL)
	if len(groups_and_friends) > 3:
		pipeline1 = my_server.pipeline()
		for group_id, friend_id in groups_and_friends.iteritems():
			pipeline1.hget('pgah:'+group_id,'anon'+friend_id)
		result1, counter, group_anon_states = pipeline1.execute(), 0, {}
		for group_id, friend_id in groups_and_friends.iteritems():
			group_anon_states[group_id] = result1[counter]
			counter += 1
		return group_anon_states
	else:
		group_anon_states = {}
		for group_id, friend_id in groups_and_friends.iteritems():
			group_anon_states[group_id] = my_server.hget('pgah:'+group_id,'anon'+friend_id)
		return group_anon_states


# def get_obj_state(pgh, index=None):
# 	"""
# 	Retrieves the 'del' and 'hidden' status of a message
# 	"""
# 	my_server = redis.Redis(connection_pool=POOL)
# 	is_hidden, is_deleted = my_server.hmget(pgh,'hidden'+index,'status'+index) if index else my_server.hmget(pgh,'hidden','status')
# 	is_hidden = 'no' if not is_hidden else is_hidden
# 	return is_hidden, is_deleted

######################################## Personal Group Mobile Verification ########################################


def get_personal_group_target_id_and_csrf(own_id):
	own_id = str(own_id)
	tid_key, csrf_key = "pgmvtid:"+own_id, "pgmvcsrf:"+own_id
	tid, csrf = redis.Redis(connection_pool=POOL).mget(tid_key, csrf_key)
	return tid, csrf


def set_personal_group_target_id_and_csrf(own_id, target_id, csrf):
	my_server = redis.Redis(connection_pool=POOL)
	own_id = str(own_id)
	pipeline1 = my_server.pipeline()
	pipeline1.setex("pgmvtid:"+own_id,target_id,ONE_DAY)
	pipeline1.setex("pgmvcsrf:"+own_id,csrf,ONE_DAY)
	pipeline1.execute()


def set_personal_group_mobile_num_cooloff(own_id):
	"""
	Setting mobile number verification cooloff of personal group user
	"""
	redis.Redis(connection_pool=POOL).setex("nchdis:"+str(own_id),1,MOBILE_NUM_CHG_COOLOFF)


def can_change_number(own_id):
	"""
	Check whether a number change is allowed for the personal group user or not
	"""
	return not redis.Redis(connection_pool=POOL).exists("nchdis:"+str(own_id))


################################################ Invite Functionality ################################################


def reset_ttl(sorted_set, server=None):
	"""
	Sets the TTL of the invite list to the TTL of the latest item in it
	"""
	if not server:
		server = redis.Redis(connection_pool=POOL)
	invite_and_expiry = server.zrange(sorted_set,-1,-1,withscores=True)[0]
	server.expireat(sorted_set,int(invite_and_expiry[1]))


def personal_group_invite_status(own_id, own_username, target_id, target_username):
	"""
	Determines whether a sender was already invited by the invite receiver (or not)

	This can also check for the case where the receiver had invited earlier, the sender had cancelled it, but the sender is now inviting them anyway
	Returning '0' means 'i_already_invited_them'
	Returning '1' means 'i_already_invited_them_anonymously'
	Returning '2' means 'they_already_invited_me'
	Returning '3' means 'they_already_invited_me_anonymously'
	"""
	my_server = redis.Redis(connection_pool=POOL)
	own_id, target_id = str(own_id), str(target_id)
	sorted_set = "pgil:"+str(own_id)
	i_invited_them = own_id+":"+own_username+":"+target_id+":"+target_username
	i_invited_them_anonymously = own_id+":*"+own_username[:1].upper()+own_username+":"+target_id+":"+target_username
	they_invited_me = target_id+":"+target_username+":"+own_id+":"+own_username
	they_invited_me_anonymously = target_id+":*"+target_username[:1].upper()+target_username+":"+own_id+":"+own_username
	pipeline1 = my_server.pipeline()
	pipeline1.zscore(sorted_set,i_invited_them)
	pipeline1.zscore(sorted_set,i_invited_them_anonymously)
	expiry_time = pipeline1.execute()
	if expiry_time[0]:
		return '0', expiry_time[0] - TWO_DAYS, False
	elif expiry_time[1]:
		return '1', expiry_time[1] - TWO_DAYS, False
	else:
		# they already invited me:
		pipeline2 = my_server.pipeline()
		key_name1 = "pgii:"+own_id+":"+target_id
		key_name2 = "pgiia:"+own_id+":"+target_id#'personal_group_ignore_invite' means they invited me 'anonymously', and I declined it
		pipeline2.zscore(sorted_set,they_invited_me)
		pipeline2.zscore(sorted_set,they_invited_me_anonymously)
		pipeline2.get(key_name1)
		pipeline2.get(key_name2)
		expiry_time = pipeline2.execute()
		if expiry_time[0]:
			return '2', expiry_time[0] - TWO_DAYS, False
		elif expiry_time[1]:
			return '3', expiry_time[1] - TWO_DAYS, False
		elif expiry_time[2]:
			try:
				return '2', float(expiry_time[2]) - TWO_DAYS, True # 'recently_declined' is set to True
			except TypeError:
				return '2', None, True
		elif expiry_time[3]:
			try:
				return '3', float(expiry_time[2]) - TWO_DAYS, True # 'recently_declined' is set to True
			except TypeError:
				return '3', None, True # 'recently_declined' is set to True
		else:
			return 'nothing', None, False



def return_invite_list(own_id, start_idx, end_idx):
	"""
	Displays invites from previous two days.

	It trims the list of any extraneous invites before returning it.
	"""
	my_server = redis.Redis(connection_pool=POOL)
	own_id = str(own_id)
	sorted_set, rate_limit_key = "pgil:"+own_id, "ilt:"+own_id
	# trim list before returning
	if not my_server.exists(rate_limit_key):
		pipeline1 = my_server.pipeline()
		pipeline1.zremrangebyscore(sorted_set,'-inf',time.time()-1.0)
		# ratelimiting trimming call
		pipeline1.setex("ilt:"+own_id,1,EIGHT_MINS)
		pipeline1.execute()
	return my_server.zrevrange(sorted_set,start_idx,end_idx,withscores=True), TWO_DAYS, my_server.zcard(sorted_set)
 


def interactive_invite_privacy_settings(own_id, own_username, target_id, target_username, visible):
	"""
	Anonymizing own invite.

	This happens after user accesses privacy settings right after sending an invite.
	"""
	my_server = redis.Redis(connection_pool=POOL)
	own_id, target_id = str(own_id), str(target_id)
	invite = own_id+":"+own_username+":"+target_id+":"+target_username
	new_invite = own_id+":*"+own_username[:1].upper()+own_username+":"+target_id+":"+target_username
	if visible == '0':
		expiry_time = my_server.zscore("pgil:"+str(target_id), invite)
		if expiry_time:
			pipeline1 = my_server.pipeline()
			pipeline1.zadd("pgil:"+target_id, new_invite, expiry_time)
			pipeline1.zadd("pgil:"+own_id, new_invite, expiry_time)
			pipeline1.zrem("pgil:"+target_id, invite)
			pipeline1.zrem("pgil:"+own_id, invite)
			pipeline1.execute()
			reset_ttl("pgil:"+target_id,my_server)
			reset_ttl("pgil:"+own_id,my_server)


def ignore_invite(own_id, own_username, their_id, their_username):
	"""
	Ignoring incoming invite from invite list

	This removes the invite from own list, but maintains it in the senders list so that they still run into a rate limit
	"""
	my_server = redis.Redis(connection_pool=POOL)
	own_id, their_id = str(own_id), str(their_id)
	they_invited_me = their_id+":"+their_username+":"+own_id+":"+own_username
	they_invited_me_anonymously = their_id+":*"+their_username[:1].upper()+their_username+":"+own_id+":"+own_username
	invites = [they_invited_me, they_invited_me_anonymously]
	sorted_set = "pgil:"+own_id
	# setting personal_group_ignore_invite key and its expiry
	pipeline1 = my_server.pipeline()
	pipeline1.zscore(sorted_set,they_invited_me)
	pipeline1.zscore(sorted_set,they_invited_me_anonymously)
	expiry_time = pipeline1.execute()
	pipeline2 = my_server.pipeline()
	key_name1 = 'pgii:'+own_id+":"+their_id # they invite me, and I just ignored it
	key_name2 = 'pgiia:'+own_id+":"+their_id # they invite me anonymously, and I just ignored it
	if expiry_time[0]:
		pipeline2.set(key_name1,expiry_time[0])
		pipeline2.expireat(key_name1,int(expiry_time[0]))
	elif expiry_time[1]:
		pipeline2.set(key_name2,expiry_time[1])
		pipeline2.expireat(key_name2,int(expiry_time[1]))
	else:
		# can this happen?
		pass
	pipeline2.execute()
	# removing invites
	my_server.zrem(sorted_set,*invites)
	# reseting invite list TTL
	if my_server.exists(sorted_set):
		reset_ttl(sorted_set, my_server)


def process_invite_sending(own_id, own_username, target_id, target_username):
	"""
	This processes a sent invite, adding it to relevant tables and setting expire times.
	"""
	my_server = redis.Redis(connection_pool=POOL)
	own_id, target_id = str(own_id), str(target_id)
	rate_limit_key = "pgirl:"+own_id
	invites_left = my_server.get(rate_limit_key)
	if invites_left is None:
		# proceed with the invite and set the rate_limit_key to have 4 invites
		my_server.setex(rate_limit_key,PERSONAL_GROUP_INVITES,PERSONAL_GROUP_INVITES_COOLOFF)
	elif int(invites_left) > 0:
		# proceed with the invite and subtract 1 invite from rate_limit_key
		my_server.incrby(rate_limit_key,amount=-1)
	else:
		cooloff_time = my_server.ttl(rate_limit_key)
		return False, cooloff_time
	# invite is rate limited for as long as PERSONAL_GROUP_INVITES_COOLOFF
	invite = own_id+":"+own_username+":"+target_id+":"+target_username
	target_sorted_set, own_sorted_set, expiry_time = "pgil:"+target_id, "pgil:"+own_id, int(time.time() + TWO_DAYS)
	pipeline1 = my_server.pipeline()
	pipeline1.zadd(target_sorted_set, invite, expiry_time)
	pipeline1.zadd(own_sorted_set, invite, expiry_time)
	pipeline1.expireat(target_sorted_set, expiry_time)
	pipeline1.expireat(own_sorted_set, expiry_time)
	pipeline1.execute()
	return True, None


def sanitize_personal_group_invites(own_id, own_username, target_id, target_username):
	"""
	Run once personal group has been created
	"""
	my_server = redis.Redis(connection_pool=POOL)
	own_id, target_id = str(own_id), str(target_id)
	target_sorted_set, own_sorted_set = "pgil:"+target_id, "pgil:"+own_id
	their_invite = [target_id+":"+target_username+":"+own_id+":"+own_username, \
	target_id+":*"+target_username[:1].upper()+target_username+":"+own_id+":"+own_username]
	key_name1 = "pgii:"+own_id+":"+target_id
	key_name2 = "pgiia:"+own_id+":"+target_id
	pipeline1 = my_server.pipeline()
	pipeline1.zrem(target_sorted_set, *their_invite)	
	pipeline1.zrem(own_sorted_set, *their_invite)
	pipeline1.delete(key_name1)
	pipeline1.delete(key_name2)
	pipeline1.execute()
	if my_server.exists(target_sorted_set):
		reset_ttl(target_sorted_set, my_server)
	if my_server.exists(own_sorted_set):
		reset_ttl(own_sorted_set, my_server)



######################################## Personal Group Creation & Existence ########################################


def personal_group_exists(group_id,own_id,target_id):
	"""
	Checks for existence via the group_id route
	"""
	own_id = str(own_id)
	key1, key2 = own_id+":"+target_id, target_id+":"+own_id
	users = redis.Redis(connection_pool=POOL).get("pgp:"+group_id)
	if users in (key1,key2):
		return True
	else:
		return False


def personal_group_already_exists(own_id, target_id, server=None):
	"""
	Elaborate check for existence; returns group_id as well
	"""
	if not target_id:
		return None, False
	if not server:
		server = redis.Redis(connection_pool=POOL)
	group_id = server.get("pgrp:"+str(own_id)+":"+target_id)
	if group_id:
		return group_id, True
	else:
		return None, False


def create_personal_group(own_id, target_id, own_anon='0', target_anon='0',own_rec_photo='0', target_rec_photo='0', own_del='0', target_del='0',\
	autodel='0',own_rec_sms='0',target_rec_sms='0',own_num_chg='1',target_num_chg='1',target_svch_perm='0',own_svch_perm='0',\
	own_saves_remaining=PERSONAL_GROUP_SAVED_CHAT_COUNTER,target_saves_remaining=PERSONAL_GROUP_SAVED_CHAT_COUNTER):
	own_id, target_id = str(own_id), str(target_id)
	my_server = redis.Redis(connection_pool=POOL)
	group_id, already_exists = personal_group_already_exists(own_id, target_id, my_server)
	if group_id:
		return group_id, True
	else:
		time_now = time.time()
		mapping = {'ct':time_now, 'anon'+own_id:own_anon, 'anon'+target_id:target_anon,'phrec'+own_id:own_rec_photo,'autodel':autodel,\
		'lt_msg_t':time_now,'lt_msg_tp':'creation','lt_msg_wid':own_id,'phrec'+target_id:target_rec_photo, 'xfivt'+own_id:PERSONAL_GROUP_PHT_XFER_IVTS,\
		'xfivt'+target_id:PERSONAL_GROUP_PHT_XFER_IVTS,'smsrec'+own_id:own_rec_sms,'smsrec'+target_id:target_rec_sms,'numchg'+own_id:own_num_chg,\
		'numchg'+target_id:target_num_chg,'smsivt'+own_id:PERSONAL_GROUP_SMS_IVTS,'smsivt'+target_id:PERSONAL_GROUP_SMS_IVTS,'last_seen'+own_id:time_now+0.1,\
		'last_seen'+target_id:'-1','svrem'+own_id:own_saves_remaining,'svrem'+target_id:target_saves_remaining,'svprm'+own_id:own_svch_perm,\
		'svprm'+target_id:target_svch_perm,'lt_msg_tx':'','lt_msg_img':'','lt_msg_st':'','lt_img_id':''}
		group_id = str(my_server.incr("personal_group"))
		pipeline1 = my_server.pipeline()
		pipeline1.hmset("pgah:"+group_id,mapping)
		pipeline1.mset({"pgp:"+group_id:own_id+":"+target_id,"pgrp:"+own_id+":"+target_id:group_id,"pgrp:"+target_id+":"+own_id:group_id})
		pipeline1.zadd("all_pgs",group_id,time.time())
		###### No need to touch these sets, they're done in mark_personal_group_attendance ######
		# pipeline1.zadd("pgfgm:"+own_id,group_id+":"+target_id,time_now)
		# pipeline1.zadd("pgfgm:"+target_id,group_id+":"+own_id,time_now)
		#########################################################################################
		pipeline1.execute()
		return group_id, False