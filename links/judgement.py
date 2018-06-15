import time
from verified import FEMALES
from redis2 import update_object
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.db.models import F
from django.shortcuts import redirect, render
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from django.middleware import csrf
from datetime import timedelta
from operator import itemgetter
from forms import PhotoReportForm
from models import Photo, UserProfile
from redis4 import return_referrer_logs
from page_controls import ITEMS_PER_PAGE
from views import get_price, get_addendum, get_page_obj, convert_to_epoch
from score import PERMANENT_RESIDENT_SCORE, PHOTO_REPORT_PROMPT,PHOTO_CASE_COMPLETION_BONUS
from tasks import process_reporter_payables, sanitize_photo_report, sanitize_expired_bans, post_banning_tasks
from redis3 import set_inter_user_ban, temporarily_save_user_csrf, remove_single_ban, is_already_banned, get_banned_users, \
save_ban_target_credentials, get_ban_target_credentials, delete_ban_target_credentials, get_global_ban_leaderboard
from redis1 import set_photo_complaint, get_photo_complaints, get_complaint_details, delete_photo_report,remove_from_photo_upload_ban, \
remove_from_photo_vote_ban, get_num_complaints,add_photo_culler,first_time_photo_culler,first_time_photo_judger,add_photo_judger,\
first_time_photo_curator,add_photo_curator, resurrect_home_photo, in_defenders, first_time_photo_defender, check_photo_upload_ban,\
get_photo_votes, ban_photo, add_to_photo_upload_ban, add_user_to_photo_vote_ban, add_to_photo_vote_ban, add_photo_defender_tutorial, \
add_banner, first_time_banner


SEVEN_MINS = 7*60
TWENTY_MINS = 20*60

#####################################################Intra User Banning#####################################################

def ban_underway(request):
	banned_by_yourself = request.session.pop("banned_by_yourself",None)
	target_username = request.session.pop("target_username",None)
	banned_by = request.session.pop("banned_by",None)
	ban_time = request.session.pop("ban_time",None)
	origin = request.session.pop("where_from",None)
	uname = request.session.pop("own_uname",None)
	if origin == 'fan':	
		return render(request,"cant_fan.html",{'own_id':str(request.user.id),'target_username':target_username,'ban_time':ban_time,\
			'banned_by_yourself':banned_by_yourself})
	else:
		return render(request,"ban_system_check.html",{'own_id':str(request.user.id),'banned_by':banned_by,'ban_time':ban_time, 'origin':origin,'uname':uname})

def banned_users_list(request):
	banned_ids_to_show_with_ttl, banned_ids_to_show, banned_ids_to_unban, own_id = {}, [], [], request.user.id
	all_banned_ids_with_ttl = get_banned_users(own_id)
	if all_banned_ids_with_ttl:
		for banned_id, ttl in all_banned_ids_with_ttl:
			if ttl < 5:
				banned_ids_to_unban.append(banned_id)
			else:
				banned_ids_to_show.append(banned_id)
				banned_ids_to_show_with_ttl[int(banned_id)] = ttl
		sanitize_expired_bans.delay(own_id, banned_ids_to_unban)
		banned_users = User.objects.select_related('userprofile').filter(id__in=banned_ids_to_show)
		banned_users_with_ttl = []
		for user in banned_users:
			banned_users_with_ttl.append((user,banned_ids_to_show_with_ttl[user.id]))
		return render(request,"banned_users_list.html",{'banned_users_with_ttl':banned_users_with_ttl,'females':FEMALES,\
			'status':request.session.pop("user_ban_change_status",None),'cooloff_ttl':request.session.pop("user_ban_cooloff_ttl",None),\
			'target_username':request.session.pop("user_ban_cooloff_username",None)})
	else:
		return render(request,"banned_users_list.html",{'status':request.session.pop("user_ban_change_status",None),\
			'females':None,'cooloff_ttl':request.session.pop("user_ban_cooloff_ttl",None),'banned_users_with_ttl':[],\
			'target_username':request.session.pop("user_ban_cooloff_username",None)})

def first_time_inter_user_banner(request):
	user_id = request.user.id
	target_username = get_ban_target_credentials(own_id=user_id, username_only=True, destroy=True)
	if not target_username or not first_time_banner(user_id) or not request.mobile_verified:
		return redirect("home")
	return render(request,"inter_user_ban.html",{'first_time_banner_instructions':True,'target_username':target_username,\
		'own_username':request.user.username})

def inter_user_ban_not_permitted(request):
	delete_ban_target_credentials(request.user.id)
	if request.mobile_verified:
		return render(request,"404.html",{})
	else:
		CSRF = csrf.get_token(request)
		temporarily_save_user_csrf(str(request.user.id), CSRF)
		return render(request,"inter_user_ban.html",{'not_verified':True,'csrf':CSRF})


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def enter_inter_user_ban(request,*args,**kwargs):
	"""
	Responsible for setting the ban on a certain target_id
	"""
	if request.method == "POST":
		can_unban = request.POST.get("can_unban",None)
		second_decision = request.POST.get("sec_dec",None)
		initial_decision = request.POST.get("init_dec",None)
		user_id = request.user.id
		if second_decision:
			if second_decision == '0':
				if can_unban:
					# unbanning user
					credentials= get_ban_target_credentials(own_id=user_id, destroy=True)
					try:
						target_user_id, target_username = credentials["target_id"], credentials["target_username"]
					except KeyError:
						return redirect("banned_users_list")
					banned = False
					if target_user_id and target_username:
						banned = remove_single_ban(user_id, target_user_id)
					request.session["user_ban_change_status"] = '0' if banned else '2'
					request.session.modified = True
				return redirect("banned_users_list")
			else:
				# set ban on user
				credentials = get_ban_target_credentials(own_id=user_id)
				try:
					target_user_id, target_username = credentials["target_id"], credentials["target_username"]
				except KeyError:
					return redirect("banned_users_list")
				try:
					object_id, origin = credentials["object_id"], credentials["origin"]
				except KeyError:
					object_id, origin = None, None
				CONVERT_DUR_CODE_TO_DURATION = {'1':604800,'2':604800,'3':604800,'4':2628000,'5':7884000}
				if target_user_id and target_username:
					time_now = time.time()
					banned, ttl = set_inter_user_ban(own_id=user_id, target_id=target_user_id, target_username=target_username, \
						ttl=CONVERT_DUR_CODE_TO_DURATION[second_decision], time_now=time_now, can_unban=can_unban, \
						recent_joiner= True if (time_now-convert_to_epoch(request.user.date_joined)<TWENTY_MINS) else False)
					if banned is None and ttl:
						request.session["user_ban_cooloff_username"] = target_username
						request.session["user_ban_cooloff_ttl"] = ttl
						request.session["user_ban_change_status"] = '3'
						request.session.modified = True
						return redirect("banned_users_list")
					elif can_unban and banned:
						delete_ban_target_credentials(user_id)
						if object_id and origin:
							post_banning_tasks.delay(own_id=user_id, target_id=target_user_id, object_id=object_id, origin=origin)
						request.session["user_ban_change_status"] = '1'
						request.session.modified = True
						return redirect("banned_users_list")
					elif can_unban and not banned:
						delete_ban_target_credentials(user_id)
						request.session["user_ban_change_status"] = '2'
						request.session.modified = True
						return redirect("banned_users_list")
					elif first_time_banner(user_id) and banned:
						if object_id and origin:
							post_banning_tasks.delay(own_id=user_id, target_id=target_user_id, object_id=object_id, origin=origin)
						add_banner(user_id)
						return redirect("first_time_inter_user_banner")
					elif banned:
						delete_ban_target_credentials(user_id)
						if object_id and origin:
							post_banning_tasks.delay(own_id=user_id, target_id=target_user_id, object_id=object_id, origin=origin)
						return redirect("banned_users_list")
					else:
						# could be malicious
						delete_ban_target_credentials(user_id)
						return redirect("home")
				else:
					return redirect("banned_users_list")
		elif initial_decision:
			if initial_decision == '1':
				is_verified = request.mobile_verified
				if not is_verified:
					return redirect("inter_user_ban_not_permitted")
				elif is_verified:
					return render(request,"inter_user_ban.html",{'target_username':get_ban_target_credentials(own_id=user_id, username_only=True),\
						'decide_time':True})
				else:
					return redirect("inter_user_ban_not_permitted")
			elif initial_decision == '0':
				# take user to origin
				delete_ban_target_credentials(user_id)
				return redirect("home")
		else:
			target_user_id = int(request.POST.get("tuid",None)[2:-2],16) #converting hex number to int
			if target_user_id == user_id:
				return redirect("home")
			elif target_user_id != user_id:
				target_username = User.objects.filter(id=target_user_id).values_list('username',flat=True)
				object_id, origin = request.POST.get("oid",None),request.POST.get("origin",None)
				if target_username:
					target_username = target_username[0]
					save_ban_target_credentials(own_id=user_id, target_id=target_user_id, target_username=target_username, object_id=object_id, origin=origin)
					banner_id, existing_ttl = is_already_banned(own_id=user_id, target_id=target_user_id, return_banner=True)
					if existing_ttl is None or existing_ttl is False:
						return render(request,"inter_user_ban.html",{'target_username':target_username,'to_ban':True})
					else:
						if banner_id == str(user_id):
							return render(request,"inter_user_ban.html",{'target_username':target_username,'target_user_id':target_user_id,'already_banned':True, \
								'banned_by':'self'})
						else:
							return render(request,"inter_user_ban.html",{'target_username':target_username,'target_user_id':target_user_id,'already_banned':True, \
								'banned_by':'other'})
			else:
				return redirect("home")
	else:
		return redirect("banned_users_list")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def change_ban_time(request):
	if request.method == "POST":
		banned_user_id, banned_username = request.POST.get("buid",None), request.POST.get("bun",None)
		if banned_user_id and banned_username:
			save_ban_target_credentials(own_id=request.user.id, target_id=banned_user_id, target_username=banned_username)
			return render(request,"inter_user_ban.html",{'target_username':banned_username,'decide_time':True, 'can_unban':True})
		else:
			return redirect("banned_users_list")
	else:
		return redirect("banned_users_list")


def ban_leaderboard(request):
	global_list_with_scores = get_global_ban_leaderboard()
	dictionary = dict(global_list_with_scores)
	ids, scores = zip(*global_list_with_scores)
	users = User.objects.filter(id__in=ids).values('id','username')
	id_username_mapping = {}
	for d in users:
		id_username_mapping[d["id"]] = d["username"]
	result = []
	for id_,score in global_list_with_scores:
		result.append((id_username_mapping[int(id_)], score))
	return render(request,"global_banned_user_list.html",{'result':result})


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def user_ban_help(request):
	if request.method == 'POST':
		target_username = request.POST.get('tunm',None)
		return render(request,"user_ban_help.html",{'target_username':target_username,'decide_time':True})
	else:
		return render(request,"user_ban_help.html",{})


# def export_block_error(request):
# 	logs = return_referrer_logs('block_error')
# 	filename = 'blocked.csv'
# 	if logs:
# 		import csv, ast
# 		with open(filename,'wb') as f:
# 			wtr = csv.writer(f)
# 			columns = ["obj_creator_reported_id","object_creator_actual_id","object_attributes"]
# 			wtr.writerow(columns) # writing the columns
# 			for log in logs:
# 				dictionary = ast.literal_eval(log)
# 				reported_id = dictionary["obj_creator_reported_id"]
# 				creator_id = dictionary["object_creator_actual_id"]
# 				object_attributes = dictionary["object_attributes"]
# 				to_write = [reported_id,creator_id,object_attributes]
# 				wtr.writerows([to_write])
# 	return render(request,"404.html",{})

########################################################Admin Banning#######################################################

def find_time_to_go(photo_owner_id):
	banned, time_remaining = check_photo_upload_ban(photo_owner_id)
	return ('0' if not banned else ('-1' if time_remaining == '-1' else timezone.now()+timedelta(seconds=time_remaining)))

def process_photo_punishment_options(user_id,decision,photo_url,photo_id,photo_owner_id,photo_owner_username,link_id,origin):
	if in_defenders(user_id):
		if decision == '1':
			# edit the photo uploading ban
			context = {'purl':photo_url,'pid':photo_id,'poid':photo_owner_id,'oun':photo_owner_username,\
			'already_banned':find_time_to_go(photo_owner_id),'origin':origin,'link_id':link_id,'dec':decision}
		elif decision == '2':
			# edit the vote ban
			photovote_usernames_and_values = get_photo_votes(photo_id)
			number_of_voters = len(photovote_usernames_and_values)
			context={'nameandval':photovote_usernames_and_values,'purl':photo_url,'oun':photo_owner_username,'num':number_of_voters,\
			'pid':photo_id,'origin':origin,'link_id':link_id,'dec':decision}
		elif decision == '3':
			# edit both photo uploading and vote ban together in one giant screen!
			photovote_usernames_and_values = get_photo_votes(photo_id)
			number_of_voters = len(photovote_usernames_and_values)
			context={'already_banned':find_time_to_go(photo_owner_id),'nameandval':photovote_usernames_and_values,'num':number_of_voters,\
			'poid':photo_owner_id,'oun':photo_owner_username,'pid':photo_id,'purl':photo_url,'origin':origin,'link_id':link_id,'dec':decision}
		elif decision == '0':
			#resurrect photo
			Photo.objects.filter(id=photo_id).update(vote_score=0, visible_score=0)
			update_object(object_id=photo_id,object_type='0',vote_score=0,just_vote=True)
			ban_photo(photo_id=photo_id,ban=False) #changes photo score in best_photos.html and photos.html
			resurrect_home_photo(link_id)
			photovote_usernames_and_values = get_photo_votes(photo_id)
			number_of_voters = len(photovote_usernames_and_values)
			context={'nameandval':photovote_usernames_and_values,'num':number_of_voters,'poid':photo_owner_id,'oun':photo_owner_username,\
			'pid':photo_id,'purl':photo_url,'origin':origin,'link_id':link_id,'dec':decision}
		return context
	else:
		return []

def process_photo_upload_ban(duration,photo_id,photo_owner_id,ban_time,unban=False):
	if unban:
		remove_from_photo_upload_ban(photo_owner_id) #removing uploading ban
		remove_from_photo_vote_ban(photo_owner_id) #removing voting ban
	else:
		photo = Photo.objects.filter(id=photo_id).update(vote_score = -100) #to censor the photo from the list
		update_object(object_id=photo_id,object_type='0',vote_score=-100,just_vote=True)
		ban_photo(photo_id=photo_id,ban=True)
		add_to_photo_upload_ban(photo_owner_id, ban_time) #to impede from adding more photos
		add_user_to_photo_vote_ban(photo_owner_id, ban_time) #to impede from voting on other photos

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def ban_photo_upload_and_voters(request,*args,**kwargs):
	if request.method == 'POST':
		if in_defenders(request.user.id):
			dec = request.POST.get('dec',None)
			if dec == '1':
				# only ban photo uploader
				dur = request.POST.get('dur',None)
				pid = request.POST.get('pid',None)
				oun = request.POST.get('oun',None)
				orig = request.POST.get('orig',None)
				poid = request.POST.get('poid',None)
				lid = request.POST.get('lid',None)
				if dur == '1':
					#i.e. ban for 24 hrs
					process_photo_upload_ban(dur,pid,poid,'1')
				elif dur == '2':
					#i.e. ban for 1 week
					process_photo_upload_ban(dur,pid,poid,'7')
				elif dur == '3':
					#i.e. ban forever
					process_photo_upload_ban(dur,pid,poid,'-1')
				elif dur == '0':
					#i.e. unban
					process_photo_upload_ban(dur,pid,poid,'0',True)
				else:
					pass
			elif dec == '2' or dec == '0':
				# only ban photo voters
				unames = request.POST.getlist('unames',[])
				pid = request.POST.get('pid',None)
				oun = request.POST.get('oun',None)
				orig = request.POST.get('orig',None)
				lid = request.POST.get('lid',None)
				vdur = request.POST.get('vdur',None)
				if unames and vdur != '0':
					targets = User.objects.filter(username__in=unames).values_list('id',flat=True)
					if vdur == '1':
						add_to_photo_vote_ban(targets, '0.1')
					elif vdur == '2':
						add_to_photo_vote_ban(targets, '3')
					elif vdur == '3':
						add_to_photo_vote_ban(targets, '7')
					elif vdur == '4':
						add_to_photo_vote_ban(targets, '-1')
				else:
					pass
			elif dec == '3':
				# ban both photo uploader and voters
				dur = request.POST.get('dur',None)
				vdur = request.POST.get('vdur',None)
				pid = request.POST.get('pid',None)
				oun = request.POST.get('oun',None)
				orig = request.POST.get('orig',None)
				poid = request.POST.get('poid',None)
				lid = request.POST.get('lid',None)
				unames = request.POST.getlist('unames',[])
				if dur == '1':
					#i.e. ban for 24 hrs
					process_photo_upload_ban(dur,pid,poid,'1')
				elif dur == '2':
					#i.e. ban for 1 week
					process_photo_upload_ban(dur,pid,poid,'7')
				elif dur == '3':
					#i.e. ban forever
					process_photo_upload_ban(dur,pid,poid,'-1')
				elif dur == '0':
					#i.e. unban
					process_photo_upload_ban(dur,pid,poid,'0',True)
				else:
					pass
				if unames and vdur != '0':
					targets = User.objects.filter(username__in=unames).values_list('id',flat=True)
					if vdur == '1':
						add_to_photo_vote_ban(targets, '0.1')
					elif vdur == '2':
						add_to_photo_vote_ban(targets, '3')
					elif vdur == '3':
						add_to_photo_vote_ban(targets, '7')
					elif vdur == '4':
						add_to_photo_vote_ban(targets, '-1')
				else:
					pass
			else:
				pass
			sanitize_photo_report.delay(pid)
			return return_to_photo(request,orig,pid,lid,oun)
		else:
			#user not a defender!
			context = {'pk': 'pk'}
			return render(request, 'not_defender.html', context)
	else:
		#no GET requests allowed, redirect user
		return render(request,"404.html",{})

def return_to_photo(request,origin,photo_id=None,link_id=None,target_uname=None):
	if origin == '1':
		# originated from taza photos page
		request.session["target_photo_id"] = photo_id
		return redirect("photo_loc")
	elif origin == '2':
		# originated from best photos page
		request.session["target_best_photo_id"] = photo_id
		return redirect("best_photo_loc")
	elif origin == '3':
		# originated from home
		request.session["target_id"] = link_id
		return redirect("home_loc")
	elif origin == '4':
		# originated from user profile
		request.session["photograph_id"] = photo_id
		return redirect("profile", target_uname)
	elif origin == '5':
		# originated from photo detail
		return redirect("photo_detail", photo_id)
	elif origin == '6':
		# originated from 'cull_photos' (a defender view)
		if in_defenders(request.user.id):
			return redirect("cull_photo")
		else:
			return redirect("best_photo")
	else:
		# take the voter to best photos by default
		return redirect("best_photo")

def cull_photo_loc(request,photo_id,*args,**kwargs):
	complaints = get_photo_complaints()
	try:
		index = complaints.index("phr:"+str(photo_id))
	except:
		index = 0
	# from .views import get_addendum
	page_num, addendum = get_addendum(index,ITEMS_PER_PAGE)
	page_obj = get_page_obj(page_num,complaints,ITEMS_PER_PAGE)
	detailed_complaints = get_complaint_details(page_obj.object_list)
	object_list = sorted(detailed_complaints,key=itemgetter('nc'),reverse=True) #sorting by the number of complaints
	url = reverse_lazy("cull_photo")+addendum
	request.session['page_object'] = page_obj
	request.session['oblst'] = object_list
	request.session['total'] = len(complaints)
	return redirect(url)

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def cull_photo(request,*args,**kwargs):
	if in_defenders(request.user.id):
		if request.method == 'POST':
			posted_from_screen = request.POST.get("scr",None)
			if posted_from_screen == '1':
				pid = request.POST.get("pid",None)
				dec = request.POST.get("dec",None) #decision (radio button number)
				purl = request.POST.get("purl",None)
				poid = Photo.objects.values_list('owner_id',flat=True).get(id=pid) #photo owner id
				if poid == request.user.id:
					return render(request,'judging_own_photo.html',{'purl':purl})
				elif first_time_photo_judger(request.user.id):
					add_photo_judger(request.user.id)
					return render(request,'judgement_tutorial.html',{'pid':pid})
				else:	
					if pid and dec == '1':
						#complaints were justified
						payables, case_closed = delete_photo_report(pid,True)
						if case_closed:
							process_reporter_payables.delay(payables)
							UserProfile.objects.filter(user_id=request.user.id).update(score=F('score')+PHOTO_CASE_COMPLETION_BONUS)
							context={'points_added':PHOTO_CASE_COMPLETION_BONUS,'dec':dec,'pid':pid,'purl':purl,'further_action':True}
							return render(request,'photo_case_completion.html',context)
						else:
							context={'purl':purl}
							return render(request,'photo_case_preclosed.html',context)
					elif pid and dec == '2':
						#complaints weren't justified - but return the price they paid
						payables, case_closed = delete_photo_report(pid,True)
						if case_closed:
							process_reporter_payables.delay(payables)
							UserProfile.objects.filter(user_id=request.user.id).update(score=F('score')+PHOTO_CASE_COMPLETION_BONUS)
							context={'points_added':PHOTO_CASE_COMPLETION_BONUS,'dec':dec,'pid':pid,'purl':purl,'further_action':False}
							return render(request,'photo_case_completion.html',context)
						else:
							context={'purl':purl}
							return render(request,'photo_case_preclosed.html',context)
					elif pid and dec == '3':
						#complaints weren't justfied, so don't return the price they paid
						payables, case_closed = delete_photo_report(pid,False)
						if case_closed:
							UserProfile.objects.filter(user_id=request.user.id).update(score=F('score')+PHOTO_CASE_COMPLETION_BONUS)
							context={'points_added':PHOTO_CASE_COMPLETION_BONUS,'dec':dec,'pid':pid,'purl':purl,'further_action':False}
							return render(request,'photo_case_completion.html',context)
						else:
							context={'purl':purl}
							return render(request,'photo_case_preclosed.html',context)
						return render(request,'photo_case_completion.html',context)
					else:
						# there was no pid or no dec, is this a malicious user? return user to their own profile
						return redirect("profile",request.user)
			elif posted_from_screen == '2':
				#render screen that gives options of vote ban, photo ban, both ban
				pid = request.POST.get("pid",None)
				poid = Photo.objects.values_list('owner_id',flat=True).get(id=pid)
				oun = User.objects.get(id=poid).username
				return render(request,'photo_case_punishment.html',{'pid':pid,'purl':request.POST.get("purl",None),'poid':poid,'oun':oun,\
					'already_banned':find_time_to_go(poid)})
			elif posted_from_screen == '3':
				#render voting punishment options
				context = process_photo_punishment_options(request.user.id,request.POST.get("dec",None),request.POST.get("purl",None),\
					request.POST.get("pid",None),request.POST.get("poid",None),request.POST.get("oun",None),0,6)
				if context:
					return render(request,'ban_photo_upload_and_voters.html',context)
				else:
					return render(request,'404.html',{})
			else:
				# what other possibility is there? maybe the user shouldn't be here! revert user to their profile
				return redirect("profile",request.user)
		else:
			if first_time_photo_culler(request.user.id):
				add_photo_culler(request.user.id)
				return render(request,'photo_culler_tutorial.html',{})
			elif 'page_object' in request.session and 'oblst' in request.session and 'total' in request.session:
				if request.session['page_object'] and request.session['oblst'] and request.session['total']:
					page_obj = request.session['page_object']
					object_list = request.session['oblst']
					total = request.session['total']
				else:
					complaints = get_photo_complaints()
					page_num = request.GET.get('page', '1')
					page_obj = get_page_obj(page_num,complaints,ITEMS_PER_PAGE)
					detailed_complaints = get_complaint_details(page_obj.object_list)
					object_list = sorted(detailed_complaints,key=itemgetter('nc'),reverse=True) #sorting by the number of complaints
					total = len(complaints)
				del request.session["page_object"]
				del request.session["oblst"]
				del request.session["total"]
			else:
				complaints = get_photo_complaints()
				page_num = request.GET.get('page', '1')
				page_obj = get_page_obj(page_num,complaints,ITEMS_PER_PAGE)
				detailed_complaints = get_complaint_details(page_obj.object_list)
				object_list = sorted(detailed_complaints,key=itemgetter('nc'),reverse=True) #sorting by the number of complaints
				total = len(complaints)
			context = {'object_list':object_list,'page':page_obj,'total':total}
			return render(request,'photo_complaints.html',context)
	else:
		return render(request,'404.html',{})

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def cull_single_photo(request,*args,**kwargs):
	if request.method == 'POST':
		context = process_photo_punishment_options(request.user.id,request.POST.get("dec",None),request.POST.get("purl",None),\
			request.POST.get("pid",None),request.POST.get("poid",None),request.POST.get("oun",None),request.POST.get("lid",None),\
			request.POST.get("orig",None))
		if context:
			return render(request,'ban_photo_upload_and_voters.html',context)
		else:
			return render(request,'404.html',{})	
	else:
		return render(request,'404.html',{})

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def curate_photo(request,*args,**kwargs):
	if request.method == 'POST':
		own_id = request.user.id
		defender = in_defenders(own_id)
		if defender:
			if first_time_photo_defender(own_id):
				add_photo_defender_tutorial(own_id)
				context = {'pid':request.POST.get("curate",None),'purl':request.POST.get("purl",None),'oun':request.POST.get("oun",None),\
				'oid':request.POST.get("oid",None),'orig':request.POST.get("orig",None),'lid':request.POST.get("lid",None),\
				'vsc':request.POST.get("vsc",None)}
				return render(request, 'photo_defender_tutorial.html', context)
			else:
				poid = request.POST.get("oid",None)
				if poid == str(request.user.id):
					return render(request,'reporting_own_photo.html',{'purl':request.POST.get("purl",None),'orig':request.POST.get("orig",None),\
						'pid':request.POST.get("curate",None),'lid':request.POST.get("lid",None),'oun':request.POST.get("oun",None),\
						'complaints':get_num_complaints()})
				context={'pid':request.POST.get("curate",None),'purl':request.POST.get("purl",None),'oun':request.POST.get("oun",None),\
				'poid':poid,'orig':request.POST.get("orig",None),'lid':request.POST.get("lid",None),'already_banned':find_time_to_go(poid),\
				'single_photo':True,'complaints':get_num_complaints(),'vsc':request.POST.get("vsc",None)}
				return render(request,'photo_case_punishment.html',context)
		else:
			posted_from_screen = request.POST.get("scr",None)
			if first_time_photo_curator(request.user.id):
				add_photo_curator(request.user.id)
				return render(request,'photo_curator_tutorial.html',{'pid':request.POST.get("curate",None),'cap':request.POST.get("cap",None),\
					'purl':request.POST.get("purl",None),'orig':request.POST.get("orig",None),'poid':request.POST.get("oid",None),\
					'oun':request.POST.get("oun",None),'lid':request.POST.get("lid",None)})
			elif posted_from_screen == '1':
			# progress user to screen 2. Include variables gotten from screen 1
				dec = request.POST.get("dec",None) #decision (radio button number)
				if dec == '0':
					#nevermind
					return return_to_photo(request,request.POST.get("orig",""),request.POST.get("pid",""),\
						request.POST.get("lid",""),request.POST.get("oun",""))
				else:
					orig = request.POST.get("orig","") #origin 
					cap = request.POST.get("cap","") #caption
					isr = request.POST.get("isr","") #is_resident flag
					prc = request.POST.get("prc","") #price of reporting
					pid = request.POST.get("pid","") #photo_id
					lid = request.POST.get("lid","") #link_id (if originating from home)
					oun = request.POST.get("oun","") #username (if originating from a profile)
					purl = request.POST.get("purl","") #photo_url
					form = PhotoReportForm()
					context={'dec':dec, 'orig':orig, 'isr':isr, 'prc':prc, 'pid':pid, 'lid':lid, 'oun':oun, 'form':form, 'purl':purl,\
					'cap':cap}
					return render(request,'photo_report_text.html',context)
			elif posted_from_screen == '2':
			# finalize user report. Get all variables
				form = PhotoReportForm(request.POST)
				if form.is_valid():
					isr = request.POST.get("isr","") #is_resident flag
					purl = request.POST.get("purl","") #photo_url
					orig = request.POST.get("orig","") #origin
					pid = request.POST.get("pid","") #photo_id
					cap = request.POST.get("cap","") #caption
					lid = request.POST.get("lid","") #link_id (if originating from home)
					oun = request.POST.get("oun","") #username (if originating from a profile)
					if isr == 'False':
						return render(request,'photo_report_sent.html',{'purl':purl,'orig':orig,'pid':pid,'lid':lid,'oun':oun})
					else:	
						decision = request.POST.get("dec",None) #decision (radio button number)
						prc = request.POST.get("prc","") #price of reporting
						description = form.cleaned_data.get("description")
						try:
							ttl = set_photo_complaint(PHOTO_REPORT_PROMPT[decision], description, cap, purl, pid, prc, request.user.id)
							if ttl:
								return render(request,'cant_photo_report.html',{'orig':orig,'pid':pid,'lid':lid,'oun':oun,'ttl':ttl})
							else:
								UserProfile.objects.filter(user_id=request.user.id).update(score=F('score')-int(prc))
								return render(request,'photo_report_sent.html',{'purl':purl,'orig':orig,'pid':pid,'lid':lid,'oun':oun})
						except:
							return return_to_photo(request,orig,pid,lid,oun)
				else:
					# form is invalid, reload
					dec = request.POST.get("dec","") #decision (radio button number)
					orig = request.POST.get("orig","") #origin 
					isr = request.POST.get("isr","") #is_resident flag
					prc = request.POST.get("prc","") #price of reporting
					pid = request.POST.get("pid","") #photo_id
					lid = request.POST.get("lid","") #link_id (if originating from home)
					oun = request.POST.get("oun","") #username (if originating from a profile)
					purl = request.POST.get("purl","") #photo_url
					context={'dec':dec, 'orig':orig, 'isr':isr, 'prc':prc, 'pid':pid, 'lid':lid, 'oun':oun, 'form':form, 'purl':purl}
					return render(request,'photo_report_text.html',context)
			else:
			# show options with radio buttons to user (screen 1)
				score = request.user.userprofile.score
				price_of_report = get_price(request.user.userprofile.score)
				photo_id = request.POST.get("curate","")
				orig = request.POST.get("orig","") #origin 
				caption = request.POST.get("cap","")
				purl = request.POST.get("purl","") #photo_url
				reporting_self = (True if str(request.user.id) == request.POST.get("oid","") else False)
				if price_of_report > score:
					#disallow reporting
					context={'is_resident':False,'pid':photo_id,'orig':orig,'oun':request.POST.get("oun",None),'lid':request.POST.get("lid",None),\
					'purl':purl}
					return render(request,'photo_rep_scr_req.html',context)
				elif score > PERMANENT_RESIDENT_SCORE:
					#give options 
					context={'is_resident':True,'price':price_of_report,'photo_id':photo_id,'reporting_self':reporting_self,'orig':orig,\
					'owner_uname':request.POST.get("oun",None),'link_id':request.POST.get("lid",None),'reporting_cooldown':None,\
					'purl':purl, 'cap':caption}
					return render(request,"photo_report.html",context)
				else:
					# give options, but report doesn't count
					context={'is_resident':False,'price':price_of_report,'photo_id':photo_id,'reporting_self':reporting_self,'orig':orig,\
					'owner_uname':request.POST.get("oun",None),'link_id':request.POST.get("lid",None),'reporting_cooldown':None,\
					'purl':purl, 'cap':caption}
					return render(request,"photo_report.html",context)
	else:
		return render(request,'404.html',{})