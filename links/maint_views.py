import random, itertools
from verified import FEMALES
from operator import itemgetter
from datetime import datetime, timedelta
from user_sessions.models import Session
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from models import Link, Photo, PhotoComment, UserProfile, Publicreply, Reply,UserFan, ChatPic
from redis1 import get_inactives, set_inactives, get_inactive_count, create_inactives_copy, delete_inactives_copy, bulk_sanitize_group_invite_and_membership
from redis3 import insert_nick_list, get_nick_likeness, skip_outage, retrieve_all_mobile_numbers, retrieve_numbers_with_country_codes
from redis4 import save_deprecated_photo_ids_and_filenames#, report_rate_limited_conversation
from redis2 import bulk_sanitize_notifications

######################################## Notifications ########################################

@csrf_protect
def skip_outage_notif(request, *args, **kwargs):
	if request.method == "POST":
		which_user = request.POST.get("skip",None)
		origin = request.POST.get("orig",'1')
		if which_user is not None:
			skip_outage(which_user)
		if origin == '1':
				return redirect("home")
		elif origin == '2':
			return redirect("best_photo")
		elif origin == '0':
			return redirect("photo")
		else:
			return redirect("home")
	else:
		return redirect("home")


def damadam_cleanup(request, *args, **kwargs):
	context = {'referrer':request.META.get('HTTP_REFERER',None)}
	return render(request,"damadam_cleanup.html",context)

######################################## Username Sanitzation ########################################

@csrf_protect
# IN THE FUTURE, ENSURE CHANGED NICKS' PHONE NUMBERS ARE RELEASED TOO
def change_nicks(request,*args,**kwargs):
	"""This frees up the name space of nicks, 100K at a time.

	Nicks, once taken, are locked out of the namespace.
	This changes nicknames that aren't in use anymore to a random string.
	"""
	if request.user.username == 'mhb11':
		if request.method=='POST':
			decision = request.POST.get("dec",None)
			count = int(request.POST.get("count",None))
			if decision == 'No':
				return redirect("home")
			elif decision == 'Yes':
				inactives, last_batch = get_inactives(get_10K=True)
				id_list = map(itemgetter(1), inactives) #list of ids to deprecate
				id_len = len(id_list)
				start = count*100000
				end = start+100000-1
				rand_nums = random.sample(xrange(start,end), id_len+10)
				counter = 0
				for pk in id_list:
					# change 'i_i__' next time this is run; otherwise there will be collisions
					try:
						nick = "i_i__"+str(rand_nums[counter])
						# print "changing user id %s to %s" % (User.objects.get(id=int(pk)).username, nick)
						User.objects.filter(id=int(pk)).update(username=nick)
					except:
						pass
					counter += 1
				if last_batch:
					return render(request,'deprecate_nicks.html',{})
				else:
					return render(request,'change_nicks.html',{'count':count+1,'nicks_remaining':get_inactive_count()})
		else:
			return render(request,'change_nicks.html',{'count':1,'nicks_remaining':get_inactive_count()})



def export_nicks(request,*args,**kwargs):
	"""Exports deprecated nicks in a CSV.

	This writes all nicks, scores and ids into a CSV.
	The CSV is then exported.
	"""
	if request.user.username == 'mhb11':
		inactives = get_inactives()
		import csv
		with open('inactives.csv','wb') as f:
			wtr = csv.writer(f, delimiter=',')
			columns = "username score id".split()
			wtr.writerow(columns)
			for inactive in inactives:
				tup = inactive[0].split(":")
				username = tup[0]
				try:
					score = tup[1]
				except:
					score = None
				id_ = inactive[1]
				to_write = [username, score, id_]
				wtr.writerows([to_write])
		return render(request,'deprecate_nicks.html',{})
	else:
		return render(request,'404.html',{})



def deprecate_nicks(request,*args,**kwargs):
	"""This singles out user_ids and nicks that haven't been in use over the past 3 months.

	It looks at criteria such as last messaging time and a ton of other things.
	It ensures pink stars are not included in the list.
	Only 'mhb11' can run this function.
	"""
	if request.user.username == 'mhb11':
		# all user ids who last logged in more than 3 months ago
		three_months_ago = datetime.utcnow()-timedelta(days=90)
		all_old_ids = set(User.objects.filter(last_login__lte=three_months_ago).values_list('id',flat=True))
		# user ids not found in Sessions
		current_users = Session.objects.filter(user__isnull=False,last_activity__gte=three_months_ago).values_list('user_id',flat=True)
		logged_out_users = set(User.objects.exclude(id__in=current_users).values_list('id',flat=True))
		# # messaged on home more than 3 months ago
		current_home_messegers = Link.objects.filter(submitted_on__gte=three_months_ago).values_list('submitter_id',flat=True)
		never_home_message = set(User.objects.exclude(id__in=current_home_messegers).values_list('id',flat=True))
		# # never submitted a publicreply
		current_public_repliers = Publicreply.objects.filter(submitted_on__gte=three_months_ago).values_list('submitted_by_id',flat=True)
		never_publicreply = set(User.objects.exclude(id__in=current_public_repliers).values_list('id',flat=True))
		# never sent a photocomment
		current_photo_commenters = PhotoComment.objects.filter(submitted_on__gte=three_months_ago).values_list('submitted_by_id',flat=True)
		never_photocomment = set(User.objects.exclude(id__in=current_photo_commenters).values_list('id',flat=True))
		# never wrote in a group
		current_group_writers = Reply.objects.filter(submitted_on__gte=three_months_ago).values_list('writer_id',flat=True)
		never_groupreply = set(User.objects.exclude(id__in=current_group_writers).values_list('id',flat=True))
		# # never uploaded a photo
		current_photo_uploaders = Photo.objects.filter(upload_time__gte=three_months_ago).values_list('owner_id',flat=True)
		never_uploaded_photo = set(User.objects.exclude(id__in=current_photo_uploaders).values_list('id',flat=True))
		# # never sent a chatpic
		current_chat_pic_users = ChatPic.objects.filter(upload_time__gte=three_months_ago).values_list('owner_id',flat=True)
		never_sent_chat_pic = set(User.objects.exclude(id__in=current_chat_pic_users).values_list('id',flat=True))
		# # never fanned anyone
		# # change this to never fanned ever (not in the last 3 months, because that could include people like 'Sit' too)
		current_fanners = UserFan.objects.filter(fanning_time__gte=three_months_ago).values_list('fan_id',flat=True)
		never_fanned = set(User.objects.exclude(id__in=current_fanners).values_list('id',flat=True))
		# # score is below 15000
		less_than_15000 = set(UserProfile.objects.filter(score__lte=15000).values_list('user_id',flat=True))
		# # intersection of all such ids
		sets = [all_old_ids, logged_out_users, never_home_message, never_publicreply, never_photocomment, never_uploaded_photo, never_fanned, less_than_15000, \
		never_groupreply, never_sent_chat_pic]
		inactive = set.intersection(*sets)
		#################
		#sanitize pink stars:
		pink_stars = set(User.objects.filter(username__in=FEMALES).values_list('id',flat=True))
		inactive = inactive - pink_stars
		#################
		inactives = []
		inactives_data = User.objects.select_related('userprofile').filter(id__in=inactive).values_list('username','id','userprofile__score')
		for inact in inactives_data:
			inactives.append((inact[0]+":"+str(inact[2]),inact[1]))
		size = len(inactives)
		list1 = inactives[:size/2]
		list2 = inactives[size/2:]
		from itertools import chain
		# breaking it into two lists avoids socket time out
		set_inactives([x for x in chain.from_iterable(list1)])
		set_inactives([x for x in chain.from_iterable(list2)])
		return render(request,'deprecate_nicks.html',{})
	else:
		return render(request,'404.html',{})



def insert_nicks(request,*args,**kwargs):
	"""Inserts nicks in a redis sorted set for quick checking at the time of sign up

	All nicknames are first retrieved from the database.
	They are then inserted, chunk-wise, into the redis sorted set.
	It's a standalone function. One only needs to block new signups before running this.
	"""
	if request.user.username == 'mhb11':
		nicknames = User.objects.values_list('username',flat=True)
		list_len = len(nicknames)
		each_slice = int(list_len/10)
		counter = 0
		slices = []
		while counter < list_len:
			slices.append((counter,counter+each_slice))
			counter += each_slice
		for sublist in slices:
			insert_nick_list(nicknames[sublist[0]:sublist[1]])
		return render(request,'nicks_populated.html',{})
	else:
		return render(request,'404.html',{})



######################################## Redis Sanitzation ########################################

@csrf_protect
def remove_inactives_notification_activity(request,*args,**kwargs):
	"""Sanitize all notification acitivity of inactive users from redis2.

	We will be removing the following for each inactive user:
	1) sn:<user_id> --- a sorted set containing home screen 'single notifications',
	2) ua:<user_id> --- a sorted set containing notifications for 'matka',
	3) uar:<user_id> --- a sorted set containing resorted notifications,
	4) np:<user_id>:*:* --- all notification objects associated to the user,
	5) o:*:* --- any objects that remain with 0 subscribers,
	We will do everything in chunks of 10K, so that no server timeouts are encountered.
	"""
	if request.user.username == 'mhb11':
		if request.method == "POST":
			decision = request.POST.get("dec",None)
			if decision == 'No':
				delete_inactives_copy()
				return redirect("home")
			elif decision == 'Yes':
				inactives, last_batch = get_inactives(get_5K=True, key="copy_of_inactive_users")
				id_list = map(itemgetter(1), inactives) #list of user ids
				notification_hash_deleted, sorted_sets_deleted, object_hash_deleted = bulk_sanitize_notifications(id_list)
				if last_batch:
					delete_inactives_copy(delete_orig=True)
				return render(request,'sanitize_inactives_activity.html',{'inactives_remaining':get_inactive_count(key_name="copy_of_inactive_users"),\
					'last_batch':last_batch,'notif_deleted':notification_hash_deleted,'sorted_sets_deleted':sorted_sets_deleted,\
					'objs_deleted':object_hash_deleted})
		else:
			return render(request,'sanitize_inactives_activity.html',{'inactives_remaining':create_inactives_copy()})
	else:
		return redirect("missing_page")

@csrf_protect
def remove_inactives_groups(request,*args,**kwargs):
	"""Sanitize all group invites and memberships.

	"""
	if request.user.username == 'mhb11':
		if request.method == "POST":
			decision = request.POST.get("dec",None)
			if decision == 'No':
				delete_inactives_copy()
				return redirect("home")
			elif decision == 'Yes':
				inactives, last_batch = get_inactives(get_50K=True, key="copy_of_inactive_users")
				id_list = map(itemgetter(1), inactives) #list of user ids
				bulk_sanitize_group_invite_and_membership(id_list)
				if last_batch:
					delete_inactives_copy(delete_orig=True)
				return render(request,"sanitize_groups.html",{'last_batch':last_batch, \
					'inactives_remaining':get_inactive_count(key_name="copy_of_inactive_users")})
		else:
			return render(request,"sanitize_groups.html",{'inactives_remaining':create_inactives_copy()})
	else:
		return redirect("missing_page")


######################################## PSQL Sanitzation ########################################

@csrf_protect
def remove_inactive_user_sessions(request,*args,**kwargs):
	"""Sanitize all sessions of deprecated ids.

	"""
	if request.user.username == 'mhb11':
		if request.method == "POST":
			decision = request.POST.get("dec",None)
			if decision == 'No':
				delete_inactives_copy()
				return redirect("home")
			elif decision == 'Yes':
				inactives, last_batch = get_inactives(get_10K=True, key="copy_of_inactive_users")
				id_list = map(itemgetter(1), inactives) #list of user ids
				# print "Deleting %s sessions created by %s users" % (Session.objects.filter(user_id__in=id_list).count(), len(id_list))
				Session.objects.filter(user_id__in=id_list).delete()
				if last_batch:
					delete_inactives_copy(delete_orig=True)
				return render(request,'sanitize_inactive_sessions.html',{'last_batch':last_batch, \
					'inactives_remaining':get_inactive_count(key_name="copy_of_inactive_users")})
		else:
			return render(request,'sanitize_inactive_sessions.html',{'inactives_remaining':create_inactives_copy()})
	else:
		return redirect("missing_page")




# def process_filenames(list_of_filenames):
# 	"""Parse filenames and save them in redis for exporting

# 	"""
# 	for filename,photo_id in list_of_filenames:
# 		filename = filename.split('photos/')[1]


def confirm_uninteresting(photo_ids):
	"""Returns photo_ids of photos that are uninteresting

	1) Photos that have no related comments, and comment_count is 0
	2) Where the vote score was 0 (although, this could be net 0 couting positives and negatives both. Acknowledging and ignoring that)
	3) Where latest_comment and second_latest_comment were null
	"""
	############
	photo_ids_with_associated_comments = PhotoComment.objects.filter(which_photo_id__in=photo_ids).values_list('which_photo_id',flat=True)
	return list(set(photo_ids) - set(photo_ids_with_associated_comments))
	############

@csrf_protect
def remove_inactives_photos(request,*args,**kwargs):
	"""Sanitize all inactives' photos that garnered 0 comments.

	1) We get the list of inactive ids (divided into batches for performance)
	2) For each batch, find all photo ids
	3) For each photo id, mark photos that do not have a corresponding photocomment
	4) Retrieve the file name of all such photos and store them in a redis list
	"""
	if request.user.username == 'mhb11':
		if request.method == "POST":
			decision = request.POST.get("dec",None)
			if decision == 'No':
				delete_inactives_copy()
				return redirect("home")
			elif decision == 'Yes':
				inactives, last_batch = get_inactives(get_10K=True, key="copy_of_inactive_users")
				id_list = map(itemgetter(1), inactives) #list of user ids
				uninteresting_photo_ids = Photo.objects.filter(owner_id__in=id_list, comment_count=0,vote_score=0,latest_comment__isnull=True).\
				values_list('id',flat=True)
				uninteresting_photo_ids = confirm_uninteresting(uninteresting_photo_ids)
				filenames_and_ids = Photo.objects.filter(id__in=uninteresting_photo_ids).values_list('image_file','id')
				save_deprecated_photo_ids_and_filenames(filenames_and_ids)
				if last_batch:
					delete_inactives_copy(delete_orig=True)
				return render(request,"sanitize_photos.html",{'last_batch':last_batch, \
					'inactives_remaining':get_inactive_count(key_name="copy_of_inactive_users")})
		else:
			return render(request,"sanitize_photos.html",{'inactives_remaining':create_inactives_copy()})
	else:
		return redirect("missing_page")



# def remove_inactives_groups(request,*args,**kwargs):
# 	"""Sanitize all home links and publicreplies.

# 	1) We pick a date constant from over 5 months ago.
# 	2) Set all latest_reply fields to 0 among links created before 5 months ago.
# 	3) Delete all links created before 5 months ago.
# 	4) Delete all publicreplies created before 5 months ago.

#     """
#     if request.user.username == 'mhb11':
#     	if request.method == "POST":
#     		decision = request.POST.get("dec",None)
# 			if decision == 'No':
# 				delete_inactives_copy()
# 				return redirect("home")
# 			elif decision == 'Yes':
# 				inactives, last_batch = get_inactives(get_50K=True, key="copy_of_inactive_users")
# 				id_list = map(itemgetter(1), inactives) #list of user ids
# 				if last_batch:
# 					delete_inactives_copy(delete_orig=True)
# 				return render(request,"santize_groups.html",{'last_batch':last_batch, \
# 					'inactives_remaining':get_inactive_count(key_name="copy_of_inactive_users")})
#     	else:
#     		return render(request,"sanitize_groups.html",{'inactives_remaining':create_inactives_copy()})
#     else:
#     	return redirect("missing_page")

######################################## Mobile Number Sanitzation ########################################

def isolate_non_national_phone_numbers(request):
	all_numbers_and_user_ids = retrieve_all_mobile_numbers() # this produces a list of tuples
	dictionary_of_nums_and_ids = dict(all_numbers_and_user_ids)
	bogus_numbers, users = [], []
	for number, user_id in all_numbers_and_user_ids:
		users.append(int(float(user_id)))
	all_numbers = retrieve_numbers_with_country_codes(set(users))
	import ast
	for entry in all_numbers:
		for number in entry:
			number = ast.literal_eval(number)
			if number["country_prefix"] != '92':
				bogus_numbers.append(((int(float(dictionary_of_nums_and_ids[number["national_number"]]))),number["number"]))
	processed_bogus_pairs = []
	for user_id, number in bogus_numbers:
		user = User.objects.filter(id=user_id).values_list('username',flat=True)[0]
		processed_bogus_pairs.append((user,number))
	return render(request,"show_bogus_mobile_user_ids.html",{'bogus_pairs':processed_bogus_pairs,'total':len(processed_bogus_pairs)})

# ############################################### Logger ###############################################

# def rate_limit_logging_report(request):
# 	report_rate_limited_conversation()
# 	return redirect("missing_page")