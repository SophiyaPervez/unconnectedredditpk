import redis, time
from random import randint
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

hash_name = "cah:"+str(user_id) #cah is 'comment abuse hash', it contains latest integrity value
set_name = "ftux:"+str(user_id)
hash_name = "giu:"+str(group_id)+str(user_id)#giu is 'group invite for user' - stores the invite_id that was sent to the user (for later retrieval)
hash_name = "hafs:"+str(user_id)+str(reporter_id) #hafs is 'hash abuse feedback set', it contains strings about the person's wrong doings
sorted_set = "ipg:"+str(user_id) #ipg is 'invited private/public group' - this stores the group_id a user has already been invited to - limited to 500 invites
hash_name = "lah:"+str(user_id)
hash_name = "lk:"+str(link_pk) #lk is 'link'
hash_name = "lpvt:"+str(photo_id) #lpvt is 'last photo vote time'
hash_name = "lvt:"+str(video_id) #lvt is 'last vote time'
hash_name = "nah:"+str(target_id) #nah is 'nick abuse hash', it contains latest integrity value
set_name = "nas:"+str(target_id) #nas is 'nick abuse set', it contains IDs of people who reported this person
hash_name = "pah:"+str(user_id) #pah is 'publicreply abuse hash', it contains latest integrity value
hash_name = "pcbah:"+str(user_id) #pcbah is 'profile cyber bullying abuse hash', it contains latest integrity value
hash_name = "poah:"+str(user_id) #poah is 'profile obscenity abuse hash', it contains latest integrity value
set_name = "pgm:"+str(group_id) #pgm is private/public_group_members
list_name = "phts:"+str(user_id)
hash_name = "plm:"+str(photo_pk) #plm is 'photo_link_mapping'
hash_name = "pvb:"+str(user_id) #pub is 'photo vote ban'
hash_name = "pub:"+str(user_id) #pub is 'photo upload ban'
sorted_set = "public_group_rankings"
photo_vote_list = "pvl:"+str(user_id) #'pvl': photo_vote_list
unsorted_set = "pir:"+str(user_id) #pir is 'private/public invite reply' - stores every 'active' invite_id - deleted if reply seen or X is pressed
hash_name = "rut:"+str(user_id)#ru is 'recent upload time' - stores the last video upload time of user
set_name = "ug:"+str(user_id) #ug is user's groups
sorted_set = "v:"+str(link_pk) #set of all votes cast against a 'home link'.
sorted_set = "vp:"+str(photo_id)
sorted_set = "vv:"+str(video_id) #vv is 'voted video'
list_name = "vids:"+str(user_id)

##########
'''
POOL = redis.ConnectionPool(host='127.0.0.1', port=6379, db=0)# change connection from TCP port to UNIX socket

INTERVAL_SIZE = 4*60

GRP_TGR = 700

ONE_WEEK = 7*24*60*60
FOUR_DAYS = 4*24*60*60
THREE_DAYS = 3*24*60*60
ONE_DAY = 24*60*60
TWELVE_HOURS = 12*60*60
SIX_HOURS = 6*60*60
THREE_HOURS = 3*60*60
ONE_HOUR = 60*60
TEN_MINS = 10*60
THREE_MINS = 3*60

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
	hash_name = "pvb:"+str(user_id) #pub is 'photo upload ban'
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

def add_to_photo_upload_ban(user_id, ban_type):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "pub:"+str(user_id) #pub is 'photo upload ban'
	current_time = time.time()
	mapping = {'t':current_time, 'b':ban_type}
	my_server.hmset(hash_name, mapping)

def add_to_photo_vote_ban(user_ids, ban_type):
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

#######################Tutorials#######################

#mehfil refresh button: '1'
#photo defender:        '2'
#inbox (matka):         '3'

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
	if my_server.sismember(set_name, '2'):
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
	my_server.sadd(set_name, '2')

def add_refresher(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '1')

def add_inbox(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	set_name = "ftux:"+str(user_id)
	my_server.sadd(set_name, '3')

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

def get_recent_photos(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.lrange("phts:"+str(user_id), 0, -1)

def save_recent_photo(user_id, photo_id):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.lpush("phts:"+str(user_id), photo_id)
	my_server.ltrim("phts:"+str(user_id), 0, 4) # save the most recent 5 photos

def get_photo_votes(photo_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "vp:"+str(photo_id)
	return my_server.zrange(sorted_set, 0, -1, withscores=True)

# def voted_for_photo2(photo_qs,username):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	photos_voted = []
# 	for photo in photo_qs:
# 		sorted_set = "vp:"+str(photo.id)
# 		already_exists = my_server.zscore(sorted_set, username)
# 		if already_exists == 0 or already_exists == 1:
# 			# i.e. upvote or downvote already exists, thus this photo.id counts!
# 			photos_voted.append(photo.id)
# 	return photos_voted

def voted_for_photo(photo_qs,username):
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

# def voted_for_photo(photo_id, username):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	sorted_set = "vp:"+str(photo_id)
# 	already_exists = my_server.zscore(sorted_set, username)
# 	if already_exists != 0 and already_exists != 1:
# 		# i.e. does not already exist
# 		return False
# 	else:
# 		# i.e. already exists
# 		return True

def add_vote_to_photo(photo_id, username, value):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "vp:"+str(photo_id) #vv is 'voted photo'
	already_exists = my_server.zscore(sorted_set, username)
	if already_exists != 0 and already_exists != 1:
		#add the voter's username and vote_value (for display later)
		my_server.zadd(sorted_set, username, value)
		update_vsc_in_photo(photo_id,value)
		#update 'last vote time'. Maitenance: if this time is older than 7 days (or something) remove 'vp:'
		hash_name = "lpvt:"+str(photo_id) #lpvt is 'last photo vote time'
		current_time = time.time()
		mapping = {'t':current_time}
		my_server.hmset(hash_name, mapping)
		return True
	else:
		return False

def can_photo_vote(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	photo_vote_list = "pvl:"+str(user_id) #'pvl': photo_vote_list
	list_len = my_server.llen(photo_vote_list)
	if list_len >= 5:
		last_vote_time = my_server.lrange(photo_vote_list, 0, 0)
		time_diff = time.time() - float(last_vote_time[0])
		intervals = int(time_diff/INTERVAL_SIZE)
		if intervals == 0:
			#the user has to wait, he/she can't push more votes
			return False, (INTERVAL_SIZE - time_diff)
		elif intervals == 1:
			my_server.rpop(photo_vote_list)
			my_server.lpush(photo_vote_list,time.time())
			return True, None
		elif intervals == 2:
			my_server.ltrim(photo_vote_list, 3, 4)
			my_server.lpush(photo_vote_list,time.time())
			return True, None
		elif intervals == 3:
			my_server.ltrim(photo_vote_list, 2, 4)
			my_server.lpush(photo_vote_list,time.time())
			return True, None
		elif intervals == 4:
			my_server.ltrim(photo_vote_list, 1, 4)
			my_server.lpush(photo_vote_list,time.time())
			return True, None
		elif intervals >= 5:
			my_server.ltrim(photo_vote_list, 0, 4)
			my_server.lpush(photo_vote_list,time.time())
			return True, None
		else:
			return True, None
	else:
		my_server.lpush(photo_vote_list,time.time())
		return True, None

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

def retrieve_home_links(link_id_list):
	my_server = redis.Redis(connection_pool=POOL)
	list_of_dictionaries = []
	photo_ids = []
	non_photo_link_ids = []
	pipeline1 = my_server.pipeline()
	for link_id in link_id_list:
		hash_name = "lk:"+str(link_id)
		pipeline1.hgetall(hash_name)#
	result1 = pipeline1.execute()
	count = 0
	for hash_contents in result1:
		list_of_dictionaries.append(hash_contents)
		try:
			photo_ids.append(hash_contents['pi'])
		except:
			non_photo_link_ids.append(link_id_list[count])
		count += 1
	return photo_ids, non_photo_link_ids, list_of_dictionaries

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

def update_cc_in_home_link(link_pk):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "lk:"+str(link_pk) #lk is 'link'
	if my_server.exists(hash_name):
		amnt = my_server.hincrby(hash_name, "cc", amount=1)
	return amnt

def update_vsc_in_photo(photo_pk, amnt):
	my_server = redis.Redis(connection_pool=POOL)
	link_pk = my_server.hget("plm:"+str(photo_pk), 'l') # get the link id
	hash_name = "lk:"+str(link_pk) #lk is 'link'
	if amnt == '1':
		amnt = 1
	else:
		amnt = -1
	if my_server.exists(hash_name):
		my_server.hincrby(hash_name,"v",amount=amnt)

def add_home_link(link_pk=None, categ=None, nick=None, av_url=None, desc=None, \
	meh_url=None, awld=None, hot_sc=None, img_url=None, v_sc=None, ph_pk=None, \
	ph_cc=None, scr=None, cc=None, writer_pk=None, device=None):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "lk:"+str(link_pk) #lk is 'link'
	if categ == '1':
		# this is a typical link on home
		mapping = {'l':link_pk, 'c':categ, 'n':nick, 'av':av_url, 'de':desc, 's':scr, 'cc':cc, 'dv':device, 'w':writer_pk, \
		't':time.time() }
	elif categ == '6':
		# this is a photo-containing link on home
		mapping = {'l':link_pk, 'c':categ, 'n':nick, 'av':av_url, 'de':desc, 's':scr, 'cc':cc, 'dv':device, 'w':writer_pk, \
		'aw':awld, 'h':hot_sc, 'i':img_url, 'v':v_sc, 'pi':ph_pk, 'pc':ph_cc, 't':time.time() }
	elif categ == '2':
		# this announces public mehfil creation on home
		mapping = {'l':link_pk, 'c':categ, 'n':nick, 'av':av_url, 'de':desc, 's':scr, 'cc':cc, 'dv':device, 'w':writer_pk, \
		'm':meh_url, 't':time.time() }
	# add the info in a hash
	my_server.hmset(hash_name, mapping)

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

def add_vote_to_home_link(link_pk, value, username):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "v:"+str(link_pk) #set of all votes cast against a 'home link'.
	already_exists = my_server.zscore(sorted_set, username)
	if not already_exists:# != -1 and already_exists != 1 and already_exists !=-2 and already_exists != 2:
		#add the vote
		my_server.zadd(sorted_set, username, value)

def all_best_photos():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.zrange("bestphotos:1000", 0, -1, withscores=False)

def add_photo_to_best(photo_id, score):
	my_server = redis.Redis(connection_pool=POOL)
	try:
		size = my_server.zcard("bestphotos:1000")
		limit = 1000
		if size < 1001:
			my_server.zadd("bestphotos:1000", photo_id, score)
		else:
		   my_server.zremrangebyrank("bestphotos:1000", 0, 10)
		   my_server.zadd("bestphotos:1000", photo_id, score)
	except:
		my_server.zadd("bestphotos:1000", photo_id, score)

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

def all_filtered_posts():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.lrange("filteredposts:1000", 0, -1)

def add_filtered_post(link_id):
	my_server = redis.Redis(connection_pool=POOL)
	my_server.lpush("filteredposts:1000", link_id)
	my_server.ltrim("filteredposts:1000", 0, 999)

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
	# print hashes
	pipeline1 = my_server.pipeline()
	for link_id in hashes:
		hash_name = "lk:"+str(link_id)
		sorted_set = "v:"+str(link_id)
		pipeline1.delete(hash_name)
		pipeline1.delete(sorted_set)
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

# def bulk_check_group_membership(user_ids_list,group_id):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	non_member_ids = []
# 	for user_id in user_ids_list:
# 		set_name = "ug:"+str(user_id) #ug is user's groups
# 		if not my_server.sismember(set_name, group_id):
# 			non_member_ids.append(user_id)
# 	return non_member_ids

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
	sorted_set = "ipg:"+str(user_id) #ipg is 'invited private/public group' - this stores the group_id a user has already been invited to - limited to 500 invites
	already_exists = my_server.zscore(sorted_set, group_id)
	if not already_exists:
		return False
	else:
		return True

def add_group_invite(user_id, group_id, invite_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "ipg:"+str(user_id) #ipg is 'invited private/public group' - this stores the group_id a user has already been invited to - limited to 500 invites
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
		members = None
	return members

#####################checking abuse and punishing#####################

def remove_key(name):
	my_server = redis.Redis(connection_pool=POOL)
	try:
		my_server.delete(name)
	except:
		pass

def private_group_posting_allowed(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name1 = "pcbah:"+str(user_id)
	hash_name2 = "poah:"+str(user_id)
	time_now = time.time()
	hash_exists1 = my_server.exists(hash_name1)
	hash_exists2 = my_server.exists(hash_name2)
	if hash_exists1 and hash_exists2:
		integrity1 = my_server.hget(hash_name1, "tgr")
		integrity2 = my_server.hget(hash_name2, "tgr")  
		if int(integrity1) < 1 and int(integrity2) < 1:
			last_report_time = my_server.hget(hash_name1, "t")
			if (time_now-float(last_report_time)) < ONE_HOUR: #just banning for one hour for now
				time_remaining = (float(last_report_time)+ONE_HOUR)-time_now
				banned = True
				ban_type = 3
				warned = False
			else:
				my_server.hset(hash_name1, "tgr", GRP_TGR) #refill integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity1) < 1:
			last_report_time = my_server.hget(hash_name1, "t")
			if (time_now-float(last_report_time)) < ONE_HOUR: #just banning for one hour for now
				time_remaining = (float(last_report_time)+ONE_HOUR)-time_now
				banned = True
				ban_type = 1
				warned = False
			else:
				my_server.hset(hash_name1, "tgr", GRP_TGR) #refill integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity2) < 1:
			last_report_time = my_server.hget(hash_name2, "t")
			if (time_now-float(last_report_time)) < ONE_HOUR: #just banning for one hour for now
				time_remaining = (float(last_report_time)+ONE_HOUR)-time_now
				banned = True
				ban_type = 2
				warned = False
			else:
				my_server.hset(hash_name2, "tgr", GRP_TGR) #refill integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity1) < 100 and int(integrity2) < 100: #both integrities are at dangerously low levels
			last_report_time1 = my_server.hget(hash_name1, "t")
			last_report_time2 = my_server.hget(hash_name2, "t")
			least_time = min(float(last_report_time1),float(last_report_time2))
			if (time_now - least_time) < ONE_DAY:
				time_remaining = None
				banned = False
				ban_type = None
				warned = True
			else:
				my_server.hincrby(hash_name1, "tgr", amount=150) #refill 150 integrity
				my_server.hincrby(hash_name2, "tgr", amount=150) #refill 150 integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity1) < 100:
			last_report_time = my_server.hget(hash_name1, "t")
			if (time_now - float(last_report_time)) < ONE_DAY:
				time_remaining = None
				banned = False
				ban_type = None
				warned = True
			else:
				my_server.hincrby(hash_name1, "tgr", amount=150) #refill 150 integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity2) < 100:
			last_report_time = my_server.hget(hash_name1, "t")
			if (time_now - float(last_report_time)) < ONE_DAY:
				time_remaining = None
				banned = False
				ban_type = None
				warned = True
			else:
				my_server.hincrby(hash_name2, "tgr", amount=150) #refill 150 integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		else: #no need to warn or ban
			time_remaining = None
			banned = False
			ban_type = None
			warned = False
	elif hash_exists1:
		integrity = my_server.hget(hash_name1, "tgr")
		if int(integrity) < 1:
			last_report_time = my_server.hget(hash_name1, "t")
			if (time_now-float(last_report_time)) < ONE_HOUR: #just banning for one hour for now
				time_remaining = (float(last_report_time)+ONE_HOUR)-time_now
				banned = True
				ban_type = 1
				warned = False
			else:
				my_server.hset(hash_name1, "tgr", GRP_TGR) #refill integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity) < 100:
			if (time_now-float(last_report_time)) < ONE_DAY:
				time_remaining = None
				banned = False
				ban_type = None
				warned = True
			else:
				my_server.hincrby(hash_name1, "tgr", amount=150) #refilling 150 integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		else: #no need to warn or ban
			time_remaining = None
			banned = False
			ban_type = None
			warned = False
	elif hash_exists2:
		integrity = my_server.hget(hash_name2, "tgr")
		last_report_time = my_server.hget(hash_name2, "t")
		if int(integrity) < 1:
			if (time_now-float(last_report_time)) < ONE_HOUR: #just banning for one hour for now
				time_remaining = (float(last_report_time)+ONE_HOUR)-time_now
				banned = True
				ban_type = 2
				warned = False
			else:
				my_server.hset(hash_name2, "tgr", GRP_TGR) #refill integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		elif int(integrity) < 100:
			if (time_now-float(last_report_time)) < ONE_DAY:
				time_remaining = None
				banned = False
				ban_type = None
				warned = True
			else:
				my_server.hincrby(hash_name2, "tgr", amount=150) #refilling 150 integrity
				time_remaining = None
				banned = False
				ban_type = None
				warned = False
		else: #no need to warn or ban
			time_remaining = None
			banned = False
			ban_type = None
			warned = False
	else: #no need to warn or ban
		time_remaining = None
		banned = False
		ban_type = None
		warned = False
	return banned, ban_type, time_remaining, warned

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

def document_group_obscenity_abuse(user_id, cost):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "poah:"+str(user_id) #poah is 'profile obscenity abuse hash', it contains latest integrity value
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_time = my_server.hget(hash_name, 't')
		current_time = time.time()
		time_difference = current_time - float(hash_time)
		if time_difference < THREE_HOURS and cost > 80: #if being reported again within three hours and cost paid > 80 (i.e. score 345), increment the punishment_level
			my_server.hincrby(hash_name, "pun", amount=1) #elevating punishment level
			my_server.hset(hash_name, "t", current_time) #updating the time
			integrity_value = my_server.hget(hash_name, 'tgr')
			integrity_value = int(integrity_value) - cost
			if integrity_value < 0:
				integrity_value = 0
			my_server.hset(hash_name, "tgr", integrity_value) #updating the integrity value
		elif time_difference > ONE_WEEK: #if being reported after 7 days, reset punishment and integrity both
			integrity_value = GRP_TGR - cost
			if integrity_value < 0:
				integrity_value = 0
			mapping = {'t': current_time, 'tgr':integrity_value, 'pun':1}
			my_server.hmset(hash_name, mapping)
		elif time_difference > FOUR_DAYS: #if being reported after 4 days, reset the punishment_level
			integrity_value = my_server.hget(hash_name, 'tgr')
			integrity_value = int(integrity_value) - cost
			if integrity_value < 0:
				integrity_value = 0
			mapping = {'t': current_time, 'tgr':integrity_value, 'pun':1}
			my_server.hmset(hash_name, mapping)
		else: #if reported later than three hours but less than 4 days, or less than three hours but low cost, keep punishment_level steady
			my_server.hset(hash_name, "t", current_time)
			integrity_value = my_server.hget(hash_name, 'tgr')
			integrity_value = int(integrity_value) - cost
			if integrity_value < 0:
				integrity_value = 0
			my_server.hset(hash_name, "tgr", integrity_value)
	else:
		value = GRP_TGR #700: around 24 people @ 120 score (30 cost) will cause this person to be banned for 1 hr
		punishment_level = 1
		mapping = {'t': time.time(), 'tgr':value, 'pun':punishment_level}
		my_server.hmset(hash_name, mapping)

def document_group_cyberbullying_abuse(user_id, cost):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "pcbah:"+str(user_id) #pcbah is 'profile cyber bullying abuse hash', it contains latest integrity value
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_time = my_server.hget(hash_name, 't')
		current_time = time.time()
		time_difference = current_time - float(hash_time)
		if time_difference < THREE_HOURS and cost > 80: #if being reported again within three hours and cost paid > 80 (i.e. score 345), increment the punishment_level
			my_server.hincrby(hash_name, "pun", amount=1)
			my_server.hset(hash_name, "t", current_time)
			integrity_value = my_server.hget(hash_name, 'tgr')
			integrity_value = int(integrity_value) - cost
			if integrity_value < 0:
				integrity_value = 0
			my_server.hset(hash_name, "tgr", integrity_value)
		elif time_difference > ONE_WEEK: #if being reported after 7 days, reset punishment and integrity both
			integrity_value = GRP_TGR - cost
			if integrity_value < 0:
				integrity_value = 0
			mapping = {'t': current_time, 'tgr':integrity_value, 'pun':1}
			my_server.hmset(hash_name, mapping)
		elif time_difference > FOUR_DAYS: #if being reported after 4 days, reset the punishment_level
			integrity_value = my_server.hget(hash_name, 'tgr')
			integrity_value = int(integrity_value) - cost
			if integrity_value < 0:
				integrity_value = 0
			mapping = {'t': current_time, 'tgr':integrity_value, 'pun':1}
			my_server.hmset(hash_name, mapping)
		else: #if reported later than three hours but less than 4 days, or less than three hours but low cost, keep punishment_level steady
			my_server.hset(hash_name, "t", current_time)
			integrity_value = my_server.hget(hash_name, 'tgr')
			integrity_value = int(integrity_value) - cost
			if integrity_value < 0:
				integrity_value = 0
			my_server.hset(hash_name, "tgr", integrity_value)
	else:
		value = GRP_TGR #700: around 24 people @ 120 score (30 cost) will cause this person to be banned for 1 hr
		punishment_level = 1
		mapping = {'t': time.time(), 'tgr':value, 'pun':punishment_level}
		my_server.hmset(hash_name, mapping)

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

def document_nick_abuse(target_id, reporter_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "nah:"+str(target_id) #nah is 'nick abuse hash', it contains latest integrity value
	set_name = "nas:"+str(target_id) #nas is 'nick abuse set', it contains IDs of people who reported this person
	set_exists = my_server.scard(set_name) #returns 0 if nothing exists
	if set_exists:
		if my_server.sismember(set_name, reporter_id):
			#already a member, so don't 'double add'
			return 'Falz'
		else:
			#not a member
			my_server.hincrby(hash_name, "tgr", amount=-1)
			my_server.hset(hash_name, "t", time.time())
			my_server.sadd(set_name, reporter_id)
			return my_server.hget(hash_name, "tgr")
	else:
		mapping = {'t': time.time(), 'tgr':3}
		my_server.hmset(hash_name, mapping)
		my_server.sadd(set_name, reporter_id)
		return my_server.hget(hash_name, "tgr")

def document_link_abuse(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "lah:"+str(user_id)
	hash_exists = my_server.exists(hash_name)
	if hash_exists:
		hash_contents = my_server.hgetall(hash_name)
		old_time = hash_contents["t"]
		new_time = time.time()
		time_difference = new_time - float(old_time) #in seconds
		if time_difference < 60.0:
			#update time and integrity
			my_server.hincrby(hash_name, "tgr", amount=-1)
			my_server.hset(hash_name, "t", new_time)
		else:
			#just update the time 
			my_server.hset(hash_name, "t", new_time)
	else:
		mapping = {'t': time.time(), 'tgr':5}
		my_server.hmset(hash_name, mapping)	

def posting_allowed(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	hash_name = "lah:"+str(user_id)
	hash_exists = my_server.exists(hash_name)
	#ban if the integrity score is too less, and not enough time has passed
	#ban times are warning, 3 mins, 10 mins, 1 hour, 6 hours, 24 hours, 1 week
	if hash_exists:
		hash_contents = my_server.hgetall(hash_name)
		last_vote_time = hash_contents["t"]
		integrity = int(hash_contents["tgr"])
		time_now = time.time()
		if integrity < -6:
			#if last_vote_time was 1 week ago, let the person post, else he's banned
			if (time_now-float(last_vote_time)) < ONE_WEEK:
				time_remaining = (float(last_vote_time)+ONE_WEEK)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < -5:
			#if last_vote_time was 24 hrs ago, let the person post, else he's banned
			if (time_now-float(last_vote_time)) < ONE_DAY:
				time_remaining = (float(last_vote_time)+ONE_DAY)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < -4:
			#if last_vote_time was 24 hrs ago, let the person post, else he's banned
			if (time_now-float(last_vote_time)) < TWELVE_HOURS:
				time_remaining = (float(last_vote_time)+TWELVE_HOURS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < -3:
			#if last_vote_time was 6 hrs ago, let the person post, else he's banned
			if (time_now-float(last_vote_time)) < SIX_HOURS:
				time_remaining = (float(last_vote_time)+SIX_HOURS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < -2:
			#if last_vote_time was 1 hour ago, let the person post, else he's banned
			if (time_now-float(last_vote_time)) < ONE_HOUR:
				time_remaining = (float(last_vote_time)+ONE_HOUR)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < -1:
			#if last_vote_time was 10 mins ago, let the person post, else he's banned
			if (time_now-float(last_vote_time)) < TEN_MINS:
				time_remaining = (float(last_vote_time)+TEN_MINS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 0:
			##if last_vote_time was 3 mins ago, let the person post, else he's banned
			#re-affirm integrity after serving ban
			if (time_now-float(last_vote_time)) < THREE_MINS:
				time_remaining = (float(last_vote_time)+THREE_MINS)-time_now
				banned = True
				warned = False
			else:
				#return their integrity since they've served their time
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		elif integrity < 1:
			#not refilling integrity for SIX HOURS, since no punishment was served. Keep the person on thin ice
			if (time_now-float(last_vote_time)) < SIX_HOURS:
				banned = False
				time_remaining = 0
				warned = True
			else:
				#refill integrity after 6 hours of not getting a single downvote
				my_server.hset(hash_name, "tgr", 5)
				banned = False
				time_remaining = 0
				warned = False
		else:
			#integrity is refilled after 1 hour of no downvote, by default
			if (time_now-float(last_vote_time)) < ONE_HOUR:
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

#####################checking image perceptual hashes#####################

def already_exists(photo_hash):
	my_server = redis.Redis(connection_pool=POOL)
	try:
		exists = my_server.zscore("perceptual_hash_set", photo_hash)
		if exists:
			return exists
		else:
			return False
	except:
		return False

def insert_hash(photo_id, photo_hash):
	my_server = redis.Redis(connection_pool=POOL)
	try:
		size = my_server.zcard("perceptual_hash_set")
		limit = 3000
		if size < (limit+1):
			my_server.zadd("perceptual_hash_set", photo_hash, photo_id)
		else:
		   my_server.zremrangebyrank("perceptual_hash_set", 0, (size-limit-1))
		   my_server.zadd("perceptual_hash_set", photo_hash, photo_id)
	except:
		my_server.zadd("perceptual_hash_set", photo_hash, photo_id)