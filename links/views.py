# coding=utf-8
from math import log, ceil
from urllib import quote
from collections import OrderedDict, defaultdict
from operator import attrgetter,itemgetter
import datetime, time
from datetime import datetime, timedelta
import re, urlmarker, StringIO, urlparse, random, string, uuid, pytz, json, ast
from target_urls import call_aasan_api
from django.utils.decorators import method_decorator
from django.middleware import csrf
from django.core.files.uploadedfile import InMemoryUploadedFile
from scraper import read_image
from cricket_score import cricket_scr
from page_controls import MAX_ITEMS_PER_PAGE, ITEMS_PER_PAGE, PHOTOS_PER_PAGE, CRICKET_COMMENTS_PER_PAGE, FANS_PER_PAGE, STARS_PER_PAGE
from score import PUBLIC_GROUP_MESSAGE, PRIVATE_GROUP_MESSAGE, PUBLICREPLY, PRIVATE_GROUP_COST, PUBLIC_GROUP_COST, UPLOAD_PHOTO_REQ,\
CRICKET_SUPPORT_STARTING_POINT, CRICKET_TEAM_IDS, CRICKET_TEAM_NAMES, CRICKET_COLOR_CLASSES, SEARCH_FEATURE_THRESHOLD
from django.core.cache import get_cache, cache
from django.views.decorators.csrf import csrf_protect
from django.db.models import Max, Count, Q, Sum, F
from verified import FEMALES
from location import MEMLOC
from django.views.decorators.debug import sensitive_post_parameters
from emoticons.settings import EMOTICONS_LIST
from namaz_timings import namaz_timings, streak_alive
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView, DetailView
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.views.generic.edit import UpdateView, CreateView, DeleteView, FormView
from image_processing import clean_image_file, clean_image_file_with_hash
from salutations import SALUTATIONS
from forms import getip
from forms import UserProfileForm, DeviceHelpForm, PhotoScoreForm, BaqiPhotosHelpForm, PhotoQataarHelpForm, PhotoTimeForm, \
ChainPhotoTutorialForm, PhotoJawabForm, PhotoReplyForm, UploadPhotoReplyForm, UploadPhotoForm, ChangePrivateGroupTopicForm, \
ReinvitePrivateForm, ContactForm, InvitePrivateForm, AboutForm, PrivacyPolicyForm, CaptionDecForm, CaptionForm, PhotoHelpForm, \
PicPasswordForm, CrossNotifForm, EmoticonsHelpForm, UserSMSForm, PicHelpForm, DeletePicForm, UserPhoneNumberForm, PicExpiryForm, \
PicsChatUploadForm, VerifiedForm, GroupHelpForm, LinkForm, SmsInviteForm, WelcomeMessageForm, WelcomeForm, MehfilForm, \
MehfildecisionForm, LogoutHelpForm, LogoutReconfirmForm, LogoutPenaltyForm, SmsReinviteForm, OwnerGroupOnlineKonForm, \
AppointCaptainForm, OutsiderGroupForm, InviteForm, DirectMessageCreateForm,DirectMessageForm, PrivateGroupReplyForm, SearchNicknameForm,\
PublicGroupReplyForm, TopForm, LoginWalkthroughForm,RegisterLoginForm, ClosedGroupHelpForm, ChangeGroupRulesForm, ChangeGroupTopicForm, \
GroupTypeForm, GroupOnlineKonForm, GroupTypeForm,GroupListForm, OpenGroupHelpForm, GroupPageForm, ReinviteForm, ScoreHelpForm, \
HistoryHelpForm, UserSettingsForm, HelpForm, WhoseOnlineForm,RegisterHelpForm, VerifyHelpForm, PublicreplyForm, ReportreplyForm, ReportForm, \
UnseenActivityForm, ClosedGroupCreateForm, OpenGroupCreateForm, CommentForm, TopPhotoForm, SalatTutorialForm, SalatInviteForm, \
ExternalSalatInviteForm,ReportcommentForm, MehfilCommentForm, SpecialPhotoTutorialForm, PhotoShareForm, UploadVideoForm, VideoCommentForm, \
VideoScoreForm, FacesHelpForm, FacesPagesForm, VoteOrProfForm, AdAddressForm, AdAddressYesNoForm, AdGenderChoiceForm, AdCallPrefForm, \
AdImageYesNoForm, AdDescriptionForm, AdMobileNumForm, AdTitleYesNoForm, AdTitleForm, AdTitleForm, AdImageForm, TestAdsForm, TestReportForm, \
HomeLinkListForm, ReauthForm, ResetPasswordForm, BestPhotosListForm, PhotosListForm, CricketCommentForm, PublicreplyMiniForm, \
AdFeedbackForm, SearchAdFeedbackForm, PhotoCommentForm#, GroupReportForm
from django.core.urlresolvers import reverse_lazy, reverse
from django.shortcuts import redirect, get_object_or_404, render
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from user_sessions.models import Session
from django.utils import timezone
from django.utils.timezone import utc
from django.views.decorators.cache import cache_page, never_cache, cache_control
from fuzzywuzzy import fuzz
from brake.decorators import ratelimit
from tasks import bulk_create_notifications, photo_tasks, unseen_comment_tasks, publicreply_tasks, photo_upload_tasks, \
video_upload_tasks, video_tasks, video_vote_tasks, photo_vote_tasks, queue_for_deletion, VOTE_WEIGHT, rank_public_groups, \
public_group_attendance_tasks, group_notification_tasks, publicreply_notification_tasks, fan_recount, vote_tasks, populate_search_thumbs, \
home_photo_tasks, sanitize_erroneous_notif, set_input_rate_and_history, log_private_mehfil_session, log_profile_view#, log_organic_attention
from .html_injector import create_gibberish_punishment_text
from .check_abuse import check_photo_abuse, check_video_abuse
from .models import Link, Cooldown, PhotoStream, TutorialFlag, PhotoVote, Photo, PhotoComment, PhotoCooldown, ChatInbox, \
ChatPic, UserProfile, ChatPicMessage, UserSettings, Publicreply, GroupBanList, HellBanList, GroupCaptain, GroupTraffic, \
Group, Reply, GroupInvite, HotUser, UserFan, Salat, LatestSalat, SalatInvite, TotalFanAndPhotos, Logout, Report, Video, \
VideoComment
from redis4 import get_clones, set_photo_upload_key, get_and_delete_photo_upload_key, set_text_input_key, get_and_delete_text_input_key,\
invalidate_avurl, retrieve_user_id
from .redis3 import insert_nick_list, get_nick_likeness, find_nickname, get_search_history, select_nick, retrieve_history_with_pics,\
search_thumbs_missing, del_search_history, retrieve_thumbs, retrieve_single_thumbs, get_temp_id, save_advertiser, get_advertisers, \
purge_advertisers, get_gibberish_punishment_amount, retire_gibberish_punishment_amount, export_advertisers, temporarily_save_user_csrf, \
get_banned_users_count, is_already_banned, is_mobile_verified, get_ranked_public_groups, del_from_rankings#, log_erroneous_passwords
from .redis2 import set_uploader_score, retrieve_unseen_activity, bulk_update_salat_notifications, viewer_salat_notifications, \
update_notification, create_notification, create_object, remove_group_notification, remove_from_photo_owner_activity, \
add_to_photo_owner_activity, get_attendance, del_attendance, retrieve_latest_notification, get_all_fans,delete_salat_notification, \
prev_unseen_activity_visit, SEEN, save_user_presence,get_latest_presence, get_replies_with_seen, remove_group_object, \
retrieve_unseen_notifications, get_photo_fan_count, is_fan, retrieve_object_data
from .redisads import get_user_loc, get_ad, store_click, get_user_ads, suspend_ad
from .redis1 import insert_hash, remove_key, document_publicreply_abuse, publicreply_allowed, document_comment_abuse, comment_allowed, \
document_report_reason, add_group_member, get_group_members, remove_group_member, check_group_member, add_group_invite, TEN_MINS, \
check_group_invite, remove_group_invite, get_active_invites, add_user_group, get_user_groups, remove_user_group, all_unfiltered_posts, \
all_filtered_posts, all_filtered_urdu_posts, add_unfiltered_post, add_filtered_post, add_photo, all_photos, all_best_photos, all_videos, \
video_uploaded_too_soon, add_vote_to_video, voted_for_video, get_video_votes, save_recent_video, save_recent_photo, get_recent_photos, \
get_recent_videos, get_photo_votes, voted_for_photo, add_vote_to_photo, bulk_check_group_membership, first_time_refresher, add_refresher, \
in_defenders, first_time_photo_defender, add_photo_defender_tutorial, check_photo_upload_ban, check_photo_vote_ban, can_vote_on_photo, \
add_home_link, update_cc_in_home_photo, retrieve_home_links, add_vote_to_link, bulk_check_group_invite, first_time_inbox_visitor, \
first_time_fan, add_fan, never_posted_photo, add_photo_entry, add_photo_comment, retrieve_photo_posts, first_time_password_changer, \
add_password_change, voted_for_photo_qs, voted_for_link, add_home_replier, can_vote_on_link, add_video,add_inbox,set_latest_group_reply,\
remove_all_group_members, voted_for_single_photo, first_time_photo_uploader, add_photo_uploader, first_time_psl_supporter, set_inactives,\
add_psl_supporter, create_cricket_match, get_current_cricket_match, del_cricket_match, incr_cric_comm, incr_unfiltered_cric_comm, \
current_match_unfiltered_comments, current_match_comments, update_comment_in_home_link, first_time_home_replier, remove_group_for_all_members, \
get_link_writer, get_photo_owner, get_inactives, unlock_uname_search, is_uname_search_unlocked, set_ad_feedback, get_ad_feedback, \
in_defenders,website_feedback_given, first_time_log_outter, add_log_outter, all_best_posts, all_best_urdu_posts, remove_latest_group_reply, \
get_latest_group_replies#, set_prev_retorts
from .website_feedback_form import AdvertiseWithUsForm

from mixpanel import Mixpanel
from unconnectedreddit.settings import MIXPANEL_TOKEN

# from optimizely_config_manager import OptimizelyConfigManager
# from unconnectedreddit.optimizely_settings import PID

# config_manager = OptimizelyConfigManager(PID)

condemned = HellBanList.objects.values_list('condemned_id', flat=True).distinct()
mp = Mixpanel(MIXPANEL_TOKEN)

def set_rank():
	epoch = datetime(1970, 1, 1).replace(tzinfo=None)
	netvotes = 0
	order = log(max(abs(netvotes), 1), 10) #0.041392685 for zero votes, log 1 = 0
	sign = 1 if netvotes > 0 else -1 if netvotes < 0 else 0
	unaware_submission = datetime.utcnow().replace(tzinfo=None)
	td = unaware_submission - epoch 
	epoch_submission = td.days * 86400 + td.seconds + (float(td.microseconds) / 1000000) #number of seconds from epoch till date of submission
	secs = epoch_submission - 1432201843 #a recent date, coverted to epoch time
	invisible_score = round(sign * order + secs / 45000, 8)
	return invisible_score

def get_page_obj(page_num,obj_list,items_per_page):
	"""
	Pass list of objects and number of objects to show per page, it does the rest
	"""
	paginator = Paginator(obj_list, items_per_page)
	try:
		return paginator.page(page_num)
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		return paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		return paginator.page(paginator.num_pages)

def get_addendum(index,objs_per_page):
	page = (index // objs_per_page)+1 #determining page number
	section = index+1-((page-1)*objs_per_page) #determining section number
	addendum = '?page='+str(page)+"#section"+str(section) #forming url addendum
	return page, addendum #returing page and addendum

def convert_to_epoch(time):
	#time = pytz.utc.localize(time)
	return (time-datetime(1970,1,1)).total_seconds()


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

def spammer_punishment_text(user_id):
	amnt = get_gibberish_punishment_amount(user_id)
	if amnt:
		return create_gibberish_punishment_text(int(amnt))
	else:
		return None

def get_price(points):
	if points < 120:
		price = 30
	elif 120 <= points < 10001:
		x=((((20**(1/2.0))-2)*points)/9880)+1.96997405723 #scaling x between 2 and sqrt(20)
		base = x**2 #squaring x
		price = (((points/base)+9)//10)*10 #roundup the number to nearest 10
	elif 10001 <= points < 500001:
		sqrt1 = 20**(1/2.0)
		sqrt2 = 70**(1/2.0)
		numerator = sqrt2 - sqrt1
		x=((numerator*points)/490000)+4.39265709152 #scaling between sqrt(20) and sqrt(70)
		base = x**2 #squaring x
		price = (((points/base)+9)//10)*10 #roundup the number to nearest 10
	else:
		base = 71
		price = (((points/base)+9)//10)*10 #roundup the number to nearest 10
	return int(price)

def valid_passcode(user,num):
	if user.is_authenticated():
		if ChatPicMessage.objects.filter(sender=user,what_number=num).exists():
			return False
		else:
			return True
	else:
		if ChatPicMessage.objects.filter(sender_id=1,what_number=num).exists():
			return False
		else:
			return True

def add_to_ban(user_id):
	if HellBanList.objects.filter(condemned_id=user_id).exists():
		pass
	else:
		HellBanList.objects.create(condemned_id=user_id)
		UserProfile.objects.filter(user_id=user_id).update(score=random.randint(10,71))

def valid_uuid(uuid):
	if not uuid:
		return False
	regex = re.compile('^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z', re.I)
	match = regex.match(uuid)
	return bool(match)

def number_verification_help(request):
	if request.method == "POST":
		csrf = request.POST.get("csrf",None)
		return render(request,"num_verification_help.html",{'csrf':csrf})
	else:
		return render(request,"num_verification_help.html",{'csrf':None})


# link_id, writer_username, writer_avatar_url, writer_id, link_description
def process_publicreply(request,link_id,text,origin=None,link_writer_id=None):
	parent = Link.objects.select_related('submitter__userprofile').get(id=link_id)
	if link_writer_id and int(link_writer_id) != parent.submitter_id:
		# return a string you're sure is NOT a username
		return ":"
	parent_username = parent.submitter.username
	user_id = request.user.id
	username = request.user.username
	if request.is_feature_phone:
		device = '1'
	elif request.is_phone:
		device = '2'
	elif request.is_tablet:
		device = '4'
	elif request.is_mobile:
		device = '5'
	else:
		device = '3'
	reply = Publicreply.objects.create(description=text, answer_to=parent, submitted_by_id=user_id, device=device)
	reply_time = convert_to_epoch(reply.submitted_on)
	try:
		url = request.user.userprofile.avatar.url
	except ValueError:
		url = None
	try:
		owner_url = parent.submitter.userprofile.avatar.url
	except ValueError:
		owner_url = None
	amnt = update_comment_in_home_link(text,username,url,reply_time,user_id,link_id,(True if username in FEMALES else False))
	publicreply_tasks.delay(user_id, reply.id, link_id, text, reply_time, True if username != parent_username else False, link_writer_id)
	publicreply_notification_tasks.delay(link_id=link_id,link_submitter_url=owner_url,sender_id=user_id,link_submitter_id=parent.submitter_id,\
		link_submitter_username=parent_username,link_desc=parent.description,reply_time=reply_time,reply_poster_url=url,reply_count=amnt,\
		reply_poster_username=username,reply_desc=text,is_welc=False,priority='home_jawab',from_unseen=(True if origin == 'from_unseen' else False))
	return parent_username


def GetLatest(user):
	notif_name, hash_name, latest_notif = retrieve_latest_notification(user.id)
	try:
		if latest_notif['ot'] == '3':
			# group chat - 'g' is privacy status
			return latest_notif['g'], latest_notif, False, False, True, False, False
		elif latest_notif['ot'] == '5':
			return  '5', latest_notif, False, False, False, False, True
		elif latest_notif['ot'] == '2':
			#home publicreply
			return '2', latest_notif, True, False, False, False, False
		elif latest_notif['ot'] == '0':
			#photo comment
			if latest_notif.get('f'):
				if latest_notif['nc'] == 'True':
					# photo notif for fans
					return '1', latest_notif, False, True, False, False, False
				else:
					# photo comment received by fan
					return '0', latest_notif, False, True, False, False, False	
			else:
				# photo comment received by non-fan
				return '0', latest_notif, False, True, False, False, False
		elif latest_notif['ot'] == '4':
			# salat invites
			time_now = datetime.utcnow()+timedelta(hours=5)
			cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
				'LOCATION': MEMLOC, 'TIMEOUT': 70,
			})
			salat_timings = cache_mem.get('salat_timings')
			if not salat_timings['namaz']:
				#time for namaz has gone
				delete_salat_notification(notif_name, hash_name, user.id)
				return None, None, False, False, False, False, False
			else:
				starting_time = datetime.combine(time_now.today(), salat_timings['current_namaz_start_time'])
				ending_time = datetime.combine(time_now.today(), salat_timings['current_namaz_end_time'])
				try:
					latest_namaz = LatestSalat.objects.filter(salatee=user).latest('when')
				except:
					#latest_namaz does not exist
					latest_namaz = None
				if (convert_to_epoch(starting_time) <= float(latest_notif['u']) < convert_to_epoch(ending_time)) and not \
				AlreadyPrayed(latest_namaz,time_now):
					return '4',latest_notif, False, False, False, True, False
				else:
					delete_salat_notification(notif_name, hash_name, user.id)			
					return None, None, False, False, False, False, False
	except (KeyError,TypeError):
		if latest_notif and notif_name:
			sanitize_erroneous_notif.delay(notif_name, user.id)
		return None, None, False, False, False, False, False

def retire_home_rules(request,*args,**kwargs):
	retire_gibberish_punishment_amount(request.user.id)
	return redirect("home")


def is_urdu(text):
	# 0600-06FF and FB50-FEFF Unicode range for Urdu
	for c in text:
		if u'\u0600' <= c <= u'\u06FF' or u'\uFB50' <= c <= u'\uFEFF':
			return True
	return False


@csrf_protect
def feature_unlocked(request,*args,**kwargs):
	if request.method == 'POST':
		fid = request.POST.get("fid") #the feature_id
		score = request.user.userprofile.score
		if fid == '1' and score > SEARCH_FEATURE_THRESHOLD:
			if is_uname_search_unlocked(request.user.id):
				# redirect to page showing search feature
				return redirect("search_username")
			else:
				return render(request,"uname_search_tutorial_I.html",{})
	else:
		return render(request,"404.html",{})

@csrf_protect
def search_uname_unlocking_dec(request,*args,**kwargs):
	if request.method == 'POST':
		dec = request.POST.get("dec")
		if dec == '1':
			unlock_uname_search(request.user.id)
			return render(request,"uname_search_tutorial_II.html",{})
		else:
			return redirect("online_kon")
	else:
		return render(request,"404.html",{})		

@csrf_protect
def search_username(request,*args,**kwargs):
	if is_uname_search_unlocked(request.user.id):
		# search_history = get_search_history(request.user.id)
		page_num = request.GET.get('page', '1')
		unames = get_search_history(request.user.id)
		page_obj = get_page_obj(page_num,unames,ITEMS_PER_PAGE)
		search_history = retrieve_history_with_pics(page_obj.object_list)
		if request.method == 'POST':
			#load the page with results
			form = SearchNicknameForm(request.POST)
			if form.is_valid():
				nickname = form.cleaned_data.get("nickname")
				found_flag,exact_matches,similar = find_nickname(nickname,request.user.id)
				return render(request,'username_search.html',{'form':form,'exact_matches':exact_matches, 'similar':similar, \
					'found_flag':found_flag, 'orig_search':nickname,'search_history':search_history,'page':page_obj})
			else:
				return render(request,'username_search.html',{'form':form,'found_flag':None,'search_history':search_history,'page':page_obj})	
		else:
			#load the page as it ought to be loaded
			form = SearchNicknameForm()
			return render(request,'username_search.html',{'form':form,'found_flag':None,'search_history':search_history,'page':page_obj})
	else:
		return render(request,"404.html",{})

@csrf_protect
def go_to_username(request,nick,*args,**kwargs):
	if request.method == 'POST':
		dec = request.POST.get("dec")
		select_nick(nick,request.user.id)
		if dec == '1':
			# send to profile photos
			return redirect("profile", nick)
		elif dec == '2':
			# send to home history
			return redirect("user_activity", nick)
		elif dec == '3':
			# send to user profile
			return redirect("user_profile", nick)
		else:
			#send to profile photos
			return redirect("profile", nick)
	else:
		return render(request,"404.html",{})

@csrf_protect
def go_to_user_photo(request,nick,add_score=None,*args,**kwargs):
	if request.method == 'POST':
		if add_score == '1':
			select_nick(nick,request.user.id)
		request.session["photograph_id"] = request.POST.get("pid",'')
		return redirect("profile", nick)
	else:
		return render(request,"404.html",{})		

@csrf_protect
def remove_searched_username(request,nick,*args,**kwargs):
	if request.method == 'POST':
		searcher_id = request.POST.get("uid",'')
		del_search_history(searcher_id,nick)
		return redirect("search_username")
	else:
		return render(request,"404.html",{})


def csrf_failure(request, reason=""):
	context = {'referrer':request.META.get('HTTP_REFERER',None)}
	return render(request,"CSRF_failure.html", context)


class NeverCacheMixin(object):
	@method_decorator(never_cache)
	def dispatch(self, *args, **kwargs):
		return super(NeverCacheMixin, self).dispatch(*args, **kwargs)

class DeviceHelpView(FormView):
	form_class = DeviceHelpForm
	template_name = "device_help.html"

	def get_context_data(self, **kwargs):
		context = super(DeviceHelpView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			device = self.kwargs.get("pk")
			if device == '1':
				context["device"] = '1'
			elif device == '2':
				context["device"] = '2'
			elif device == '3':
				context["device"] = '3'
			elif device == '4':
				context["device"] = '4'
			elif device == '5':
				context["device"] = '5'
			else:
				context["device"] = None
		return context

class GroupHelpView(FormView):
	form_class = GroupHelpForm
	template_name = "group_help.html"

class ScoreHelpView(FormView):
	form_class = ScoreHelpForm
	template_name = "score_help.html"

def star_list(request, *args, **kwargs):
	context = {}
	pk = request.user.id
	ids = UserFan.objects.filter(fan_id=pk).values_list('star_id',flat=True).order_by('-fanning_time')
	if ids:
		page_num = request.GET.get('page', '1')
		page_obj = get_page_obj(page_num,ids,STARS_PER_PAGE)
		users_qset = User.objects.filter(id__in=page_obj.object_list).values('id','username','userprofile__score','userprofile__avatar').annotate(photo_count=Count('photo', distinct=True))
		users = {x['id']:x for x in users_qset}
		users_with_photo_counts = [users[id] for id in page_obj.object_list]
		context["page_obj"] = page_obj
		users_with_photo_thumbs = retrieve_thumbs(users_with_photo_counts)
		context["users"] = users_with_photo_thumbs
	else:
		context["page_obj"] = None
		context["users"] = []
		context["fan"] = User.objects.get(id=pk)
		context["girls"] = FEMALES
	return render(request,"star_list.html",context)

def fan_list(request, pk=None, *args, **kwargs):
	page_num = request.GET.get('page', '1')
	all_fan_ids, total_count, new_fan_ids_and_count = get_all_fans(pk)
	new_fan_ids = new_fan_ids_and_count[0]
	new_count = new_fan_ids_and_count[1]
	star = User.objects.get(id=pk)
	existing_users = [(id,False) for id in all_fan_ids if id not in set(new_fan_ids)]
	new_users = [(id,True) for id in new_fan_ids]
	all_users = new_users + existing_users
	if all_users:
		page_obj = get_page_obj(page_num,all_users,FANS_PER_PAGE)
		fan_dict = User.objects.select_related('userprofile').in_bulk(map(itemgetter(0),page_obj.object_list))
		fans = []
		for (user_id,is_new) in page_obj.object_list:
			fans.append((fan_dict[int(user_id)],is_new))
		return render(request,"fan_list.html",{'fans':fans,'star':star, 'count':total_count,'page_obj':page_obj,'girls':FEMALES,'new_count':new_count})
	else:
		return render(request,"fan_list.html",{'fans':None,'star':star, 'count':total_count})

class ReinviteView(FormView):
	form_class = ReinviteForm
	template_name = "reinvite.html"

	def get_context_data(self, **kwargs):
		context = super(ReinviteView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			unique = self.kwargs.get("slug")
			context["unique"] = unique
		return context

class HistoryHelpView(FormView):
	form_class = HistoryHelpForm
	template_name = "history_help.html"

class PhotosHelpView(FormView):
	form_class = PhotoHelpForm
	template_name = "photos_help.html"

	def get_context_data(self, **kwargs):
		context = super(PhotosHelpView, self).get_context_data(**kwargs)
		context["unique"] = self.kwargs.get("slug")
		context["decision"] = self.kwargs.get("pk")
		return context


class LoginWalkthroughView(FormView):	
	form_class = LoginWalkthroughForm
	template_name = "login_walkthrough.html"

class SmsReinviteView(FormView):
	form_class = SmsReinviteForm
	template_name = "sms_reinvite.html"

	def get_context_data(self, **kwargs):
		context = super(SmsReinviteView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			unique = self.request.session["unique_outsider"]#self.kwargs["slug"]
			context["number"] = '03450000000'
			context["sms_url"] = "https://http-damadam-pk.0.freebasics.com/mehfil/"+unique+"/bahir/"
			#context["group"] = Group.objects.get(unique=unique)
		return context

class SmsInviteView(FormView):
	form_class = SmsInviteForm
	template_name = "sms_invite.html"

	def get_context_data(self, **kwargs):
		context = super(SmsInviteView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			unique = self.kwargs["slug"]
			number = self.kwargs["num"]
			name = self.kwargs["name"]
			context["name"] = name
			context["number"] = number
			context["sms_url"] = "https://http-damadam-pk.0.freebasics.com/mehfil/"+unique+"/bahir/"
		return context

class RegisterLoginView(FormView):
	form_class = RegisterLoginForm
	template_name = "register_login.html"

	# def get_context_data(self, **kwargs):
	# 	context = super(RegisterLoginView, self).get_context_data(**kwargs)
	# 	mp.track(self.request.session.get('new_id',None), 'inside_register_login')
	# 	return context

class OpenGroupHelpView(FormView):
	form_class = OpenGroupHelpForm
	template_name = "open_group_help.html"

def website_rules(request):
	return render(request,"website_rules.html",{})

class ContactView(FormView):
	form_class = ContactForm
	template_name = "contact.html"

class AboutView(FormView):
	form_class = AboutForm
	template_name = "about.html"

class PrivacyPolicyView(FormView):
	form_class = PrivacyPolicyForm
	template_name = "privacy_policy.html"

class ClosedGroupHelpView(FormView):
	form_class = ClosedGroupHelpForm
	template_name = "closed_group_help.html"	

class HelpView(FormView):
	form_class = HelpForm
	template_name = "help.html"

class VerifyHelpView(FormView):
	form_class = VerifyHelpForm
	template_name = "verify_help.html"	

class RegisterHelpView(FormView):
	form_class = RegisterHelpForm
	template_name = "register_help.html"


def logout_rules(request):
	user_id = request.user.id
	if request.mobile_verified:
		if first_time_log_outter(user_id):
			add_log_outter(user_id)
			return render(request,"logout_tutorial.html",{})
		else:
			return render(request,"logout_rules.html",{})
	else:
		CSRF = csrf.get_token(request)
		temporarily_save_user_csrf(str(user_id), CSRF)
		return render(request, 'cant_logout_without_verifying.html', {'csrf':CSRF})


class LogoutPenaltyView(FormView):
	form_class = LogoutPenaltyForm
	template_name = "logout_penalty.html"

# class VoteOrProfView(FormView):
# 	form_class = VoteOrProfForm
# 	template_name = "vote_or_profile.html"

# 	def get_context_data(self, **kwargs):
# 		context = super(VoteOrProfView, self).get_context_data(**kwargs)
# 		if self.request.user.is_authenticated():
# 			try:
# 				voter = User.objects.get(username=self.kwargs["slug"])
# 				vote = Vote.objects.get(link_id=self.kwargs["pk"], voter=voter)
# 			except:
# 				# couldn't get vote
# 				context["self"] = -1
# 				context["subject"] = None
# 				context["vote_id"] = None
# 				context["link_submitter_id"] = None
# 				return context
# 			if self.request.user == voter:
# 				#if person looking at own vote
# 				context["self"] = 1
# 				context["subject"] = self.request.user
# 				context["vote_id"] = vote.id
# 				context["link_submitter_id"] = self.kwargs["id"]
# 			elif self.request.user.id == self.kwargs["id"]:
# 				#if person is the link writer too
# 				context["self"] = 2
# 				context["subject"] = voter
# 				context["vote_id"] = vote.id
# 				context["link_submitter_id"] = self.kwargs["id"]
# 			else:
# 				#if person is nor the link writer, or the voter
# 				context["self"] = 0
# 				context["subject"] = voter
# 				context["vote_id"] = vote.id
# 				context["link_submitter_id"] = self.kwargs["id"]
# 		return context

def faces_pages(request, *args, **kwargs):
	form = FacesPagesForm()
	oblist = EMOTICONS_LIST
	page_num = request.GET.get('page', '1')
	page_obj = get_page_obj(page_num,oblist,16)
	context = {'object_list': oblist, 'form':form, 'page':page_obj}
	return render(request, 'faces_pages.html', context)

class FacesHelpView(FormView):
	form_class = FacesHelpForm
	template_name = "faces.html"

	def get_context_data(self, **kwargs):
		context = super(FacesHelpView, self).get_context_data(**kwargs)
		if self.request.is_feature_phone:
			context["is_feature_phone"] = True
		else:
			context["is_feature_phone"] = False
		return context

class EmoticonsHelpView(FormView):
	form_class = EmoticonsHelpForm
	template_name = "emoticons_help.html"

	def get_context_data(self, **kwargs):
		context = super(EmoticonsHelpView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			context["random"] = random.sample(xrange(1,188),15) #select 15 random emoticons out of 188
		return context

class LogoutHelpView(FormView):
	form_class = LogoutHelpForm
	template_name = "logout_help.html"

class LogoutReconfirmView(FormView):
	form_class = LogoutReconfirmForm
	template_name = "logout_reconfirm.html"

	def form_valid(self, form):
		if self.request.user_banned:
			return render(self.request,'500.html',{}) #you can come in any time you like, you can never leave!
		else:
			if self.request.method == 'POST':
				decision = self.request.POST.get("decision")
				if decision == 'Khuda Hafiz':
					try:
						user = self.request.user
						Logout.objects.create(logout_user=user, pre_logout_score=user.userprofile.score)
						user.userprofile.score = 10
						user.userprofile.save()
						return redirect("bahirniklo")
					except:
						return redirect("home")
				else:
					return redirect("home")
			else:
				return redirect("score_help")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def leave_public_group(request):
	if request.method == "POST":
		pk = request.POST.get("gid",None)
		unique = request.POST.get("guuid",None)
		private = request.POST.get("prv",None)
		inside_grp = request.POST.get('insg',None)
		group = Group.objects.get(id=pk)
		if group.owner == request.user:
			context={'unique':unique, 'pk':pk, 'private':private,'topic':group.topic, 'inside_grp':inside_grp}
			return render(request, 'delete_public_group.html', context)
		else:
			context={'unique':unique, 'pk':pk, 'private':private,'topic':group.topic, 'inside_grp':inside_grp}
			return render(request, 'leave_public_group.html', context)
	else:
		return redirect("group_page")

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def leave_private_group(request, *args, **kwargs):
	if request.method == "POST":
		pk = request.POST.get("gid",None)
		unique = request.POST.get("guuid",None)
		private = request.POST.get("prv",None)
		inside_grp = request.POST.get('insg',None)
		topic = Group.objects.get(id=pk).topic
		context={'unique':unique, 'pk':pk, 'private':private,'topic':topic, 'inside_grp':inside_grp}
		return render(request, 'leave_private_group.html', context)
	else:
		return redirect("group_page")

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def left_private_group(request, *args, **kwargs):
	if request.method=="POST":
		user_id = request.user.id
		pk = request.POST.get("gid",None)
		private = request.POST.get("prv",None)
		unique = request.POST.get("guid",None)
		if request.is_feature_phone:
			device = '1'
		elif request.is_phone:
			device = '2'
		elif request.is_tablet:
			device = '4'
		elif request.is_mobile:
			device = '5'
		else:
			device = '3'
		if check_group_member(pk, request.user.username):
			memcount = remove_group_member(pk, request.user.username) #group membership is truncated
			remove_user_group(user_id, pk) #user's groups are truncated
			remove_group_notification(user_id,pk) #group removed from user's notifications
			if memcount < 1:
				remove_group_object(pk)
			Reply.objects.create(which_group_id=pk, writer_id=user_id, text='leaving group', category='6', device=device)
		elif check_group_invite(user_id, pk):
			remove_group_invite(user_id, pk)
			Reply.objects.create(which_group_id=pk, writer_id=user_id, text='unaccepted invite', category='7', device=device)
		else:
			pass
	return redirect("group_page")

def mehfil_help(request, pk=None, num=None, *args, **kwargs):
	if pk.isdigit() and num.isdigit():
		request.session['user_pk'] = pk
		request.session['link_id'] = num
		return redirect("mehfil_help")
	else:
		return redirect("score_help")

class MehfilView(FormView):
	form_class = MehfilForm
	template_name = "mehfil_help.html"

	def get_context_data(self, **kwargs):
		context = super(MehfilView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			try:
				target_id = self.request.session['user_pk']
				link_id = self.request.session['link_id']
				context["target"] = User.objects.get(id=target_id)
				context["link_id"] = link_id
			except:
				context["target"] = None
				context["link_id"] = None
				return context
		return context

	def form_valid(self, form):
		if self.request.method == 'POST':
			user = self.request.user
			report = self.request.POST.get("decision")
			target = self.request.session['user_pk']
			link_id = self.request.session['link_id']
			self.request.session['link_id'] = None
			self.request.session['user_pk'] = None
			if link_id and report == 'Haan':
				if user.userprofile.score < 500:
					context = {'pk': link_id}
					return render(self.request, 'penalty_linkmehfil.html', context)
				else:
					user.userprofile.score = user.userprofile.score - 500
					target_user = User.objects.get(id=target)
					invitee = target_user.username
					topic = invitee+" se gupshup"
					unique = uuid.uuid4()
					try:
						group = Group.objects.create(topic=topic, rules='', owner=user, private='1', unique=unique)
						reply_list = []
						seen_list = []
						reply = Reply.objects.create(text=invitee, category='1', which_group_id=group.id, writer=user)
						add_group_member(group.id, user.username)
						add_group_invite(target, group.id,reply.id)
						add_user_group(user.id, group.id)
						user.userprofile.save()
						self.request.session["unique_id"] = unique
						return redirect("private_group_reply")#, slug=unique)
					except:
						self.request.session["link_pk"] = link_id
						self.request.session.modified = True
						return redirect("publicreply_view")
			else:
				return redirect("home")

class SalatRankingView(ListView):
	template_name = "salat_ranking.html"
	model = LatestSalat
	paginate_by = 50

	def get_queryset(self):
		cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 120,
		})
		users_fans = cache_mem.get('salat_streaks')
		if users_fans:
			return users_fans
		else:
			return []

	def get_context_data(self, **kwargs):
		context=super(SalatRankingView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			context["girls"] = FEMALES
		return context

class SalatSuccessView(ListView):
	template_name = "salat_success.html"
	model = LatestSalat
	paginate_by = 50

	def get_queryset(self):
		cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 120,
		})
		users_fans = cache_mem.get('salat_streaks')
		if users_fans:
			return users_fans
		else:
			return []

	def get_context_data(self, **kwargs):
		context=super(SalatSuccessView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			mins = self.kwargs["mins"]
			previous_namaz, next_namaz, namaz, next_namaz_start_time, current_namaz_start_time, current_namaz_end_time = namaz_timings[int(mins)]
			context["namaz"] = namaz
			context["time"] = next_namaz_start_time
			context["weekday"] = self.kwargs["num"]
			if context["weekday"] == '4' and context["namaz"] == 'Zuhr':
				context["namaz"] = 'Jummah'
			context["girls"] = FEMALES
		return context

@csrf_protect
def report_comment(request, *args, **kwargs):
	if request.method == 'POST':
		decision = request.POST.get("dec",None)
		comment_id = request.POST.get("comm_pk",None) 
		photo_id = request.POST.get("ph_pk",None)
		origin = request.POST.get("org",None)
		slug = request.POST.get("slug",None)
		if decision == 'Haan':
			if PhotoComment.objects.filter(pk=comment_id,which_photo_id=photo_id,abuse=False).exists() and \
			Photo.objects.filter(pk=photo_id,owner=request.user).exists():
				comment = get_object_or_404(PhotoComment, pk=comment_id)
				comment.abuse = True
				comment.save()
				UserProfile.objects.filter(user=comment.submitted_by_id).update(score=F('score')-3)
				if ast.literal_eval(slug):# ensures even string 'None' converts to boolean 'None'
					return redirect("comment_pk", pk=photo_id, origin=origin, ident=slug)
				else:
					return redirect("comment_pk", pk=photo_id, origin=origin)
			else:
				# show 404 if person's trying to 'double report'
				return render(request,"404.html",{})	
		elif decision == 'Nahi':
			if ast.literal_eval(slug):# ensures even string 'None' converts to boolean 'None'
				return redirect("comment_pk", pk=photo_id, origin=origin, ident=slug)
			else:
				return redirect("comment_pk", pk=photo_id, origin=origin)
		elif decision is None:			
			return render(request,"report_comment.html",{'comment_id':comment_id, 'photo_id':photo_id, 'origin':origin, 'slug':slug})
		else:
			return render(request,"404.html",{})	
	else:
		return render(request,"404.html",{})

@ratelimit(rate='3/s')
def reportreply_pk(request, pk=None, num=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# try:
		# 	deduction = 5 * -1
		# 	request.user.userprofile.score = request.user.userprofile.score + deduction
		# 	request.user.userprofile.save()
		# 	context = {'pk': 'pk'}
		# 	return render(request, 'penalty_reportreply.html', context)
		# except:
		# 	context = {'pk': 'pk'}
		# 	return render(request, 'penalty_reportreply.html', context)
		return redirect("missing_page")
	else:
		if pk.isdigit() and num.isdigit():
			request.session["report_pk"] = pk
			request.session["linkreport_pk"] = num
			return redirect("reportreply")
		else:
			return redirect("score_help")

class ReportreplyView(FormView):
	form_class = ReportreplyForm
	template_name = "report_reply.html"

	def get_context_data(self, **kwargs):
		context = super(ReportreplyView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			pk = self.request.session["report_pk"]
			link_id = self.request.session["linkreport_pk"]
			if Publicreply.objects.filter(pk=pk,answer_to=link_id).exists() and Link.objects.filter(pk=link_id,submitter=self.request.user).exists():
				context["reply_id"] = pk
				context["link_id"] = link_id
				context["authorized"] = True
			else:
				context["reply_id"] = None
				context["link_id"] = None
				context["authorized"] = False
		return context

class PhotoDetailView(DetailView):
	model = Photo
	template_name = "photo_detail.html"

	def get_context_data(self, **kwargs):
		context = super(PhotoDetailView, self).get_context_data(**kwargs)
		context["can_vote"] = False
		context["authenticated"] = False
		try:
			pk = self.kwargs["pk"]
			photo = Photo.objects.get(id=pk)
			context["photo_id"] = pk
			context["photo"] = photo
			context["own_photo"] = False
		except:
			context["absent"] = True
			return context
		try:
			context["av_url"] = photo.owner.userprofile.avatar.url
		except:
			context["av_url"] = None
		context["defender"] = False
		context["from_cull_queue"] = False
		context["latest_photocomments"] = None
		if self.request.is_feature_phone or self.request.is_phone or self.request.is_mobile:
			context["is_mob"] = True
		if self.request.user.is_authenticated():
			if 'origin' in self.kwargs:
				if self.kwargs['origin'] == '6':
					context["from_cull_queue"] = True
				context["latest_photocomments"] = PhotoComment.objects.select_related('submitted_by').filter(which_photo_id=pk).order_by('-id')[:25]
				context["other_photos"] = Photo.objects.filter(owner=photo.owner).exclude(id=pk).order_by('-id')[:10] #list of dictionaries
				# test = Photo.objects.filter(owner=photo.owner).exclude(id=pk).order_by('-id').only('id','image_file')[:10] #list of dictionaries
			context["authenticated"] = True
			if in_defenders(self.request.user.id):
				context["defender"] = True
			if self.request.user == photo.owner:
				context["own_photo"] = True
			else:
				context["own_photo"] = False
				score = self.request.user.userprofile.score 
				if score > 9:
					context["can_vote"] = True
					if voted_for_single_photo(pk,self.request.user.username):
						context["voted"] = True
					else:
						context["voted"] = False
				else:
					context["can_vote"] = False
		return context

def skip_presalat(request, *args, **kwargs):
	cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
		'LOCATION': MEMLOC, 'TIMEOUT': 70,
	})
	salat_timings = cache_mem.get('salat_timings')
	if salat_timings['namaz']:
		#i.e. it's not pre-namaz time
		return redirect("home")
	else:
		if salat_timings['next_namaz'] == 'Fajr':
			salat='5'
		elif salat_timings['next_namaz'] == 'Zuhr':
			salat='1'
		elif salat_timings['next_namaz'] == 'Asr':
			salat='2'
		elif salat_timings['next_namaz'] == 'Maghrib':
			salat='3'
		elif salat_timings['next_namaz'] == 'Isha':
			salat='4'
		else:
			return redirect("home")
		try:
			latest_namaz = LatestSalat.objects.filter(salatee=request.user).latest('when')
			latest_namaz.skipped = True
			latest_namaz.when = now
			latest_namaz.save()
		except:
			LatestSalat.objects.create(salatee=request.user, latest_salat=salat, when=now, skipped=True)
		return redirect("home")


def skip_salat(request, skipped=None, *args, **kwargs):
	if skipped:
		# now = datetime.utcnow()+timedelta(hours=5)
		# current_minute = now.hour * 60 + now.minute
		# previous_namaz, next_namaz, namaz, next_namaz_start_time, current_namaz_start_time, current_namaz_end_time = namaz_timings[current_minute]
		cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 70,
		})
		salat_timings = cache_mem.get('salat_timings')
		if not salat_timings['namaz']:
			return redirect("home")
		elif skipped != salat_timings['namaz']:
			return redirect("home")
		else:
			if salat_timings['namaz'] == 'Fajr':
				salat='1'
			elif salat_timings['namaz'] == 'Zuhr':
				salat='2'
			elif salat_timings['namaz'] == 'Asr':
				salat='3'
			elif salat_timings['namaz'] == 'Maghrib':
				salat='4'
			elif salat_timings['namaz'] == 'Isha':
				salat='5'
			else:
				return redirect("home")
		try:
			latest_namaz = LatestSalat.objects.filter(salatee=request.user).latest('when')
			latest_namaz.skipped = True
			latest_namaz.latest_salat = salat
			latest_namaz.when = now
			latest_namaz.save()
		except:
			LatestSalat.objects.create(salatee=request.user, latest_salat=salat, when=now, skipped=True)
		request.user.userprofile.streak = 0
		request.user.userprofile.save()
		return redirect("home")
	else:
		return redirect("home")

def salat_tutorial_init(request, offered=None, *args, **kwargs):
	try:
		tut = TutorialFlag.objects.get(user=request.user)
		if tut.seen_salat_option:
			return redirect("process_salat")
		else:
			return redirect("salat_tutorial")
	except:
		TutorialFlag.objects.create(user=request.user)
		return redirect("salat_tutorial")

def AlreadyPrayed(salat, now):
	current_minute = now.hour * 60 + now.minute
	time_now = now.time()
	date_now = now.date()
	if not salat:
		return False
	datetime_of_latest_salat = salat.when
	minute_of_latest_salat = datetime_of_latest_salat.hour * 60 + datetime_of_latest_salat.minute 
	time_of_latest_salat = datetime_of_latest_salat.time()
	date_of_latest_salat = datetime_of_latest_salat.date()
	if date_now != date_of_latest_salat:
		#prayee has not already prayed, in fact they haven't logged any salat today
		#but cater to edge cases and graceful failure
		return False
	elif date_now == date_of_latest_salat:
		#prayee logged a salat today
		cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 70,
		})
		salat_timings = cache_mem.get('salat_timings')
		previous_salat_done, next_salat_done, salat_done, salat_done_next_start_time, salat_done_start_time, salat_done_end_time = namaz_timings[minute_of_latest_salat]
		if not salat_timings['namaz'] and not salat_done:
			#this is some kind of an error, handle it gracefully
			return True
		elif not salat_timings['namaz']:
			#i.e. it's pre-namaz time right now, and the person has already prayed too
			if salat.skipped:
				return 2
			else:
				return True
		elif salat_done == salat_timings['namaz']:#salat_to_do:
			#i.e. the user has already prayed
			if salat.skipped:
				return 2
			else:
				return True
		elif salat_done != salat_timings['namaz']:#salat_to_do:
			return False
		else:
			return True

def process_salat(request, offered=None, *args, **kwargs):
	now = datetime.utcnow()+timedelta(hours=5)
	current_minute = now.hour * 60 + now.minute
	# previous_namaz, next_namaz, namaz, next_namaz_start_time, current_namaz_start_time, current_namaz_end_time = namaz_timings[current_minute]
	user = request.user
	cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
		'LOCATION': MEMLOC, 'TIMEOUT': 70,
	})
	salat_timings = cache_mem.get('salat_timings')
	try:
		starting_time = datetime.combine(now.today(), salat_timings['current_namaz_start_time']) #i.e. current namaz start time
	except:
		redirect("home")
	if not salat_timings['namaz']:
		#it's not time for any namaz, ABORT
		return redirect("home")
	else:
		if salat_timings['namaz'] == 'Fajr':
			salat='1'
		elif salat_timings['namaz'] == 'Zuhr':
			salat='2'
		elif salat_timings['namaz'] == 'Asr':
			salat='3'
		elif salat_timings['namaz'] == 'Maghrib':
			salat='4'
		elif salat_timings['namaz'] == 'Isha':
			salat='5'
		else:
			return redirect("home")
		try:
			latest_namaz = LatestSalat.objects.filter(salatee=user).latest('when') #when did user pray most recently?
			if AlreadyPrayed(latest_namaz, now):
				return redirect("home")
			else:
				if streak_alive(latest_namaz,salat,now):
					user.userprofile.streak = user.userprofile.streak + 1
				else:
					user.userprofile.streak = 1
				latest_namaz.when = now
				latest_namaz.latest_salat = salat
				latest_namaz.skipped = False
				latest_namaz.save()
				user.userprofile.save()
		except:
			#the person hasn't prayed before, i.e. streak is at 0
			latest_salat = LatestSalat.objects.create(salatee=user, when=now, latest_salat=salat)
			user.userprofile.streak = 1
			user.userprofile.save()
		Salat.objects.create(prayee=user, timing=now, which_salat=salat)
		time = convert_to_epoch(starting_time)
		epochtime = convert_to_epoch(now)
		bulk_update_salat_notifications(viewer_id=user.id, starting_time=time, seen=True, updated_at=epochtime)
		return redirect("salat_success", current_minute, now.weekday())

############################################################################################################################################################

@csrf_protect
@ratelimit(rate='3/s')
# @ratelimit(field='user_id',ip=False,rate='22/38s')
def home_reply(request,pk=None,*args,**kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# context = {'penalty':300}
		# UserProfile.objects.filter(user=request.user).update(score=F('score')-300) #punish the spammer
		# return render(request, 'penalty_homejawab.html', context)
		return redirect("missing_page")
	elif request.user_banned:
		return render(request,"500.html",{})
	else:
		user_id = request.user.id
		lang = request.POST.get("lang",None)
		ipp = MAX_ITEMS_PER_PAGE if lang == 'urdu' else ITEMS_PER_PAGE
		sort_by_best = True if request.POST.get("sort_by",None) == 'best' else False
		######################################################################################################
		######################################################################################################
		# sort_by_best = True if get_user_type(user_id,best=True) == 'True' else False
		######################################################################################################
		######################################################################################################
		if request.method == 'POST':
			link_writer_id = request.POST.get("lwpk",None)
			banned_by, ban_time = is_already_banned(own_id=user_id,target_id=link_writer_id, return_banner=True)
			if banned_by:
				request.session["banned_by"] = banned_by
				request.session["ban_time"] = ban_time
				request.session["where_from"] = 'home'
				request.session.modified = True
				return redirect("ban_underway")
			else:
				##############################################################################################
				##############################################################################################
				# config_manager.get_obj().track('wrote_homereply', user_id)
				##############################################################################################
				##############################################################################################
				form = PublicreplyMiniForm(data=request.POST,user_id=user_id,link_id=pk)
				if form.is_valid():
					text=form.cleaned_data.get("description")
					set_input_rate_and_history.delay(section='home_rep',section_id=pk,text=text,user_id=user_id,time_now=time.time())
					target = process_publicreply(request=request,link_id=pk,text=text,link_writer_id=link_writer_id)
					request.session['target_id'] = pk
					if target == ":":
						return redirect("ban_underway")
					elif first_time_home_replier(user_id):
						add_home_replier(user_id)
						return render(request,'home_reply_tutorial.html', {'target':target,'own_self':request.user.username, 'lang':lang,\
							'sort_by_best':sort_by_best})
					else:
						if lang == 'urdu' and sort_by_best:
							return redirect("home_loc_ur_best", lang)
						elif sort_by_best:
							return redirect("home_loc_best")
						elif lang == 'urdu':
							return redirect("home_loc_ur", lang)
						else:
							return redirect("home_loc")
				else:
					photo_links, list_of_dictionaries, page_obj, replyforms, addendum= home_list(request=request,items_per_page=ipp,lang=lang,notif=pk)
					replyforms[pk] = form
		else:
			photo_links, list_of_dictionaries, page_obj, replyforms, addendum= home_list(request=request,items_per_page=ipp,lang=lang,notif=pk)
			replyforms[pk] = PublicreplyMiniForm()
		request.session['replyforms'] = replyforms
		request.session['list_of_dictionaries'] = list_of_dictionaries
		request.session['page'] = page_obj
		request.session['photo_links'] = photo_links
		request.session.modified = True
		if lang == 'urdu' and sort_by_best:
			url = reverse_lazy("ur_home_best",kwargs={'lang': lang})+addendum
		elif sort_by_best:
			url = reverse_lazy("home_best")+addendum
		elif lang == 'urdu':
			url = reverse_lazy("ur_home",kwargs={'lang': lang})+addendum
		else:
			url = reverse_lazy("home")+addendum
		return redirect(url)

def home_list(request, items_per_page, lang=None, notif=None, sort_by_best=None):
	if request.user_banned:
		obj_list = all_unfiltered_posts()
	else:
		if sort_by_best and lang =='urdu':
			obj_list = all_best_urdu_posts()
			######################################################################################################
			######################################################################################################
			# obj_list = all_filtered_urdu_posts()
			######################################################################################################
			######################################################################################################
		elif sort_by_best:
			obj_list = all_best_posts()
			######################################################################################################
			######################################################################################################
			# determine which algo
			# algo = get_user_type(request.user.id, algo=True)
			# if algo == '1':
			# 	obj_list = all_best_posts_1()
			# elif algo == '2':
			# 	obj_list = all_best_posts_2()
			######################################################################################################
			######################################################################################################
		elif lang=='urdu':
			obj_list = all_filtered_urdu_posts()
		else:
			obj_list = all_filtered_posts()
	if notif:
		try:
			index = obj_list.index(notif)
		except:
			index = 0
		page_num, addendum = get_addendum(index,items_per_page)
	else:
		addendum = '?page=1#section0'
		page_num = request.GET.get('page', '1')
	page_obj = get_page_obj(page_num,obj_list,items_per_page)
	photo_links, list_of_dictionaries = retrieve_home_links(page_obj.object_list)
	replyforms = {}
	for obj in list_of_dictionaries:
		replyforms[obj['l']] = PublicreplyMiniForm() #passing link_id to forms dictionary
	return photo_links, list_of_dictionaries, page_obj, replyforms, addendum

def home_location_pk(request,pk=None,*args,**kwargs):
	request.session['target_id'] = pk
	return redirect("home_loc")

def home_location(request, lang=None, *args, **kwargs):
	link_id = request.session.pop("target_id", 0)
	url_ =request.resolver_match.url_name
	ipp = MAX_ITEMS_PER_PAGE if lang == 'urdu' else ITEMS_PER_PAGE
	sort_by_best = True if (url_ == 'home_loc_best' or url_== 'home_loc_ur_best') else False
	######################################################################################################
	######################################################################################################
	# sort_by_best = True if get_user_type(request.user.id,best=True) == 'True' else False
	######################################################################################################
	######################################################################################################
	photo_links, list_of_dictionaries, page_obj, replyforms, addendum = home_list(request=request, items_per_page=ipp, lang=lang, notif=link_id,\
		sort_by_best=sort_by_best)
	request.session['photo_links'] = photo_links
	request.session['list_of_dictionaries'] = list_of_dictionaries
	request.session['page'] = page_obj
	request.session['replyforms'] = replyforms
	if lang == 'urdu' and sort_by_best:
		url = reverse_lazy("ur_home_best",kwargs={'lang': lang})+addendum
	elif sort_by_best:
		url = reverse_lazy("home_best")+addendum
	elif lang == 'urdu':
		url = reverse_lazy("ur_home",kwargs={'lang': lang})+addendum
	else:
		url = reverse_lazy("home")+addendum
	return redirect(url)

def home_link_list(request, lang=None, *args, **kwargs):
	"""This function renders the current home page.

	It gets the most recent conversational data from redis, and displays it on the template.
	"""
	if request.user.is_authenticated():
		form = HomeLinkListForm()
		context = {}
		user = request.user
		url_ =request.resolver_match.url_name
		ipp = MAX_ITEMS_PER_PAGE if lang == 'urdu' else ITEMS_PER_PAGE
		sort_by_best = True if (url_ == 'home_best' or url_== 'ur_home_best') else False
		######################################################################################################
		######################################################################################################
		# sort_by_best = True if get_user_type(user.id,best=True) =='True' else False
		######################################################################################################
		######################################################################################################
		context["newbie_flag"] = request.session.pop("newbie_flag",None)
		context["newbie_lang"] = request.session["newbie_lang"] if "newbie_lang" in request.session else None
		context["lang"] = lang
		context["sort_by"] = 'best' if sort_by_best else 'recent'
		context["checked"] = FEMALES
		context["form"] = form
		context["csrf"] = csrf.get_token(request)
		context["can_vote"] = False
		context["authenticated"] = False
		if request.is_feature_phone or request.is_phone or request.is_mobile:
			context["is_mob"] = True
		context["mobile_verified"] = request.mobile_verified
		context["ident"] = user.id #own user id
		context["username"] = user.username #own username
		enqueued_match = get_current_cricket_match()
		if 'team1' in enqueued_match:
			context["enqueued_match"] = enqueued_match
		if 'photo_links' in request.session and 'list_of_dictionaries' in request.session \
		and 'page' in request.session and 'replyforms' in request.session:
			# called when user has voted
			if request.session['list_of_dictionaries'] and request.session['page'] and request.session['replyforms']:
				#don't check for photo_links in if clause, since this can be [] in certain allowable situations
				photo_links = request.session['photo_links']
				list_of_dictionaries = request.session['list_of_dictionaries']
				page = request.session['page']
				replyforms = request.session['replyforms']
			else:
				photo_links, list_of_dictionaries, page, replyforms, addendum = home_list(request=request,items_per_page=ipp, lang=lang, \
					sort_by_best=sort_by_best)
			del request.session['photo_links']
			del request.session['list_of_dictionaries']
			del request.session['page']
			del request.session['replyforms']
		else:
			# normal refresh or toggling between pages (via agey or wapis)
			photo_links, list_of_dictionaries, page, replyforms, addendum = home_list(request=request,items_per_page=ipp, lang=lang, \
				sort_by_best=sort_by_best)
		context["link_list"] = list_of_dictionaries
		context["page"] = page
		context["replyforms"] = replyforms
		secret_key = uuid.uuid4()
		context["sk"] = secret_key
		set_text_input_key(context["ident"], '1', 'home', secret_key)
		############################################# Home Rules #################################################
		context["home_rules"] = spammer_punishment_text(context["ident"])
		############################################ Namaz feature ###############################################
		now = datetime.utcnow()+timedelta(hours=5)
		day = now.weekday()
		cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
				'LOCATION': MEMLOC, 'TIMEOUT': 70,
			})
		salat_timings = cache_mem.get('salat_timings')
		context["next_namaz_start_time"] = salat_timings['next_namaz_start_time']
		if salat_timings['namaz'] == 'Zuhr' and day == 4: #4 is Friday
			context["current_namaz"] = 'Jummah'
		else:
			context["current_namaz"] = salat_timings['namaz']
		if salat_timings['next_namaz'] == 'Zuhr' and day == 4:#4 if Friday
			context["next_namaz"] = 'Jummah'	
		else:
			context["next_namaz"] = salat_timings['next_namaz']
		if not salat_timings['namaz'] and not salat_timings['next_namaz']:
			# do not show namaz element at all, some error may have occurred
			context["show_current"] = False
			context["show_next"] = False
		elif not salat_timings['namaz']:
			try:
				latest_salat = LatestSalat.objects.filter(salatee=request.user).latest('when')
				already_prayed = AlreadyPrayed(latest_salat, now)
				if already_prayed == 2:
					#if user skipped previous namaz, no need to show prompt
					context["show_current"] = False
					context["show_next"] = False
				else:
					context["show_current"] = False
					context["show_next"] = True
			except:
				context["show_current"] = False
				context["show_next"] = True
		else:
			try:
				latest_salat = LatestSalat.objects.filter(salatee=request.user).latest('when')
				already_prayed = AlreadyPrayed(latest_salat, now)
				if already_prayed:
					if already_prayed == 2:
						context["show_current"] = False
						context["show_next"] = False
					else:
						context["show_current"] = False
						context["show_next"] = True
				else:
					#i.e. show the CURRENT namaz the user has to offer
					context["show_current"] = True
					context["show_next"] = False
			except:
				#never logged a salat in Damadam, i.e. show the CURRENT namaz the user has to offer
				context["show_current"] = True
				context["show_next"] = False
		################################################################################################################
		if "comment_form" in request.session:
			context["comment_form"] = request.session["comment_form"]
			request.session.pop("comment_form", None)
		else:
			context["comment_form"] = PhotoCommentForm()
		num = random.randint(1,4)
		context["random"] = num #determines which message to show at header
		if num > 2:
			context["newest_user"] = User.objects.latest('id') #for unauthenticated users
		else:
			context["newest_user"] = None
		context["authenticated"] = True
		photo_owners = set(item['w'] for item in photo_links)
		context["fanned"] = []
		if photo_owners:
			context["fanned"] = list(UserFan.objects.filter(star_id__in=photo_owners,fan=user).values_list('star_id',flat=True))
		score = user.userprofile.score
		context["score"] = score #own score
		if score > 9:
			context["can_vote"] = True #allowing user to vote
		if request.user_banned:
			context["process_notification"] = False #hell banned users will never see notifications
		else:
			if "notif_form" in request.session:
				context["notif_form"] = request.session["notif_form"]
				request.session.pop("notif_form", None)
			else:
				context["notif_form"] = UnseenActivityForm()
			context["process_notification"] = True
			context["salat_timings"] = salat_timings
			return render(request, 'link_list.html', context)
		return render(request, 'link_list.html', context)
	else:
		return redirect("unauth_home_new")


##############################################################################################################################
##############################################################################################################################
def new_user_gateway(request,lang=None,*args,**kwargs):
	# set necessary newbie_flags for other parts of damadam too (e.g. for matka: is mein woh sab batien likhi aa jatien hain jin mein tum ne hissa liya (maslan jawab, tabsrey, waghera))
	request.session["newbie_flag"] = True
	request.session.modified = True
	return redirect("first_time_choice", lang=lang)
	# user_id = request.user.id
	# variation = config_manager.get_obj().activate('landing_page_exp', user_id)
	# if variation == 'var_1':
	#   # how things are currently
	#   set_user_type(variation, user_id, best=False, algo=None)
	#   return redirect("first_time_link")
	#   ##########################################################
	# elif variation == 'var_2':
	#   # give users a choice of what to do
	#   request.session["newbie_flag"] = True
	#   request.session.modified = True
	#   set_user_type(variation, user_id, best=False, algo=None)
	#   return redirect("first_time_choice", best=False, algo=None)
	#   ##########################################################
	# elif variation == 'var_3':
	#   # show users best feed (photo heavy) by default
	#   request.session["newbie_flag"] = True
	#   request.session.modified = True
	#   set_user_type(variation, user_id, best=True, algo='1')
	#   return redirect("first_time_best",algo='1')
	#   ##########################################################
	# elif variation == 'var_4':
	#   # show users best feed (text heavy) by default
	#   request.session["newbie_flag"] = True
	#   request.session.modified = True
	#   set_user_type(variation, user_id, best=True, algo='2')
	#   return redirect("first_time_best",algo='2')
	#   ##########################################################
	# elif variation == 'var_5':
	#   # give users a choice of what to do (home has text heavy 'best' feed). No use showing photo heavy best feed here. The user opted for chatting. Why show him photos?
	#   request.session["newbie_flag"] = True
	#   request.session.modified = True
	#   set_user_type(variation, user_id, best=True, algo='2')
	#   return redirect("first_time_choice",best=True, algo='2')
	#   ##########################################################
	# elif variation == 'var_6':
	#   # status quo, but with instructions - trivial case
	#   request.session["newbie_flag"] = True
	#   request.session.modified = True
	#   set_user_type(variation, user_id, best=False, algo=None)
	#   return redirect("first_time_link")
	#   ##########################################################
	# else:
	#   # how things are currently
	#   set_user_type(variation, user_id, best=False, algo=None)
	#   return redirect("first_time_link")
	#   ##########################################################

# def first_time_best(request,algo, *args, **kwargs):
# 	return redirect("home_best")

# def first_time_choice(request, best=False, algo=None, *args, **kwargs):
# 	if request.method == 'POST':
# 		user_id = request.user.id
# 		choice = request.POST.get("choice",None)
# 		best = request.POST.get("best",None)
# 		algo = request.POST.get("algo",None)
# 		# save_user_choice(user_id, choice)
# 		if choice == '1':
# 			# this user wants to chat
# 			if best == 'True':
# 				# handling 'var_5'
# 				return redirect("home_best")
# 			elif best == 'False':
# 				# handling 'var_2'
# 				return redirect("home")
# 		elif choice == '2':
# 			# this user wants to see fotos, handling 'var_2'
# 			return redirect("best_photo")
# 	else:
# 		return render(request,"first_time_choice.html",{'show_best':best,'algo':algo})


def first_time_choice(request,lang=None, *args, **kwargs):
	if request.method == 'POST':
		request.session["newbie_lang"] = lang if lang else 'eng'
		request.session.modified = True
		choice = request.POST.get("choice",None)
		if choice == '1':
			# this user wants to chat
			return redirect("home")
		elif choice == '2':
			# this user wants to see fotos
			return redirect("best_photo")
		else:
			return redirect("home")
	else:
		if lang == 'ur':
			return render(request,"first_time_choice_ur.html")
		else:
			return render(request,"first_time_choice.html")


##############################################################################################################################
##############################################################################################################################


@cache_page(10)
@csrf_protect
def unauth_home_link_list(request, *args, **kwargs):
	if request.user.is_authenticated():
		return redirect("home")
	else:
		context = {}
		context["checked"] = FEMALES
		enqueued_match = get_current_cricket_match()
		if 'team1' in enqueued_match:
			context["enqueued_match"] = enqueued_match
		photo_links, list_of_dictionaries, page, replyforms, addendum = home_list(request=request,items_per_page=ITEMS_PER_PAGE)
		context["link_list"] = list_of_dictionaries
		context["page"] = page
		now = datetime.utcnow()+timedelta(hours=5)
		day = now.weekday()
		cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
				'LOCATION': MEMLOC, 'TIMEOUT': 70,
			})
		salat_timings = cache_mem.get('salat_timings')
		context["next_namaz_start_time"] = salat_timings['next_namaz_start_time']
		if salat_timings['namaz'] == 'Zuhr' and day == 4: #4 is Friday
			context["current_namaz"] = 'Jummah'
		else:
			context["current_namaz"] = salat_timings['namaz']
		if salat_timings['next_namaz'] == 'Zuhr' and day == 4:#4 if Friday
			context["next_namaz"] = 'Jummah'	
		else:
			context["next_namaz"] = salat_timings['next_namaz']
		if not salat_timings['namaz'] and not salat_timings['next_namaz']:
			# do not show namaz element at all, some error may have occurred
			context["show_current"] = False
			context["show_next"] = False
		elif not salat_timings['namaz']:
			context["show_current"] = False
			context["show_next"] = True
		else:
			context["show_current"] = True
			context["show_next"] = False
		form = CreateNickNewForm()
		context["form"] = form
		return render(request, 'unauth_link_list.html', context)

class LinkUpdateView(UpdateView):
	model = Link
	form_class = LinkForm

def appoint_pk(request, pk=None, app=None, *args, **kwargs):
	if pk.isdigit() and app.isdigit():
		request.session["appoint_id"] = pk
		request.session["appoint_decision"] = app
		return redirect("appoint")
	else:
		return redirect("score_help")

class AppointCaptainView(FormView):
	form_class = AppointCaptainForm
	template_name = "appoint_captain.html"

	def get_context_data(self, **kwargs):
		context = super(AppointCaptainView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			try:
				user_id = self.request.session["appoint_id"]
				unique_id = self.request.session["public_uuid"]
				decision = self.request.session["appoint_decision"]
				context["authorized"] = True
				context["candidate"] = User.objects.get(id=user_id)
				context["appoint"] = decision
				context["unique"] = unique_id
			except:
				context["authorized"] = False
				context["candidate"] = None
				context["appoint"] = None
				context["unique"] = None
		return context

	def form_valid(self, form):
		#f = form.save(commit=False)
		if self.request.user_banned:
			return render(self.request,'500.html',{}) #errorbanning
		else:
			candidate = self.request.session["appoint_id"]
			self.request.session["appoint_id"] = None
			unique = self.request.session["public_uuid"]
			group = Group.objects.get(unique=unique)
			appoint = self.request.session["appoint_decision"]
			self.request.session["appoint_decision"] = None
			self.request.session.modified = True
			if appoint == '1' and group.owner == self.request.user and not \
			GroupCaptain.objects.filter(which_user_id = candidate, which_group=group).exists():
				GroupCaptain.objects.create(which_user_id=candidate,which_group=group)
			elif appoint == '0' and group.owner == self.request.user:
				try:
					GroupCaptain.objects.get(which_user_id=candidate,which_group=group).delete()
				except:
					return redirect("owner_group_online_kon")
			else:
				return redirect("public_group", slug=unique)
			return redirect("owner_group_online_kon")

class OwnerGroupOnlineKonView(ListView):
	model = GroupTraffic
	form_class = OwnerGroupOnlineKonForm
	template_name = "owner_group_online_kon.html"

	def get_context_data(self, **kwargs):
		context = super(OwnerGroupOnlineKonView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			global condemned
			context["unauthorized"] = False
			context["legit"] = FEMALES
			try:
				unique = self.request.session["public_uuid"]
				context["unique"] = unique
				group = Group.objects.get(unique=unique)
				context["group"] = group
			except:
				context["group"] = None
				context["unauthorized"] = True
				context["groupies"] = []
				return context
			if group.owner == self.request.user and group.private == '0':
				all_online_ids = get_attendance(group.id)
				visitors = User.objects.select_related('userprofile').filter(id__in=all_online_ids)
				captain_ids = GroupCaptain.objects.filter(which_user_id__in=all_online_ids, which_group=group).values_list("which_user_id",flat=True)
				captains = {captain:captain for captain in captain_ids}
				groupies = []
				for visitor in visitors:
					if visitor.id in captains.keys():
						groupies.append((visitor,visitor.id))
					else:
						groupies.append((visitor,None))
				context["groupies"] = groupies
			else:
				context["groupies"] = []
				context["unauthorized"] = True
		return context

class GroupOnlineKonView(ListView):
	model = GroupTraffic
	form_class = GroupOnlineKonForm
	template_name = "group_online_kon.html"
	paginate_by = 75

	def get_context_data(self, **kwargs):
		context = super(GroupOnlineKonView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			global condemned
			context["unauthorized"] = False
			context["legit"] = FEMALES
			try:
				unique = self.request.session["public_uuid"]
				context["unique"] = unique
				group = Group.objects.get(unique=unique)
				context["group"] = group
			except:
				context["group"] = None
				context["unauthorized"] = True
				context["groupies"] = []
				return context
			if group.private == '0':
				all_online_ids = get_attendance(group.id)
				visitors = User.objects.select_related('userprofile').filter(id__in=all_online_ids)
				captain_ids = GroupCaptain.objects.filter(which_group=group, which_user_id__in=all_online_ids).values_list('which_user_id', flat=True)
				captains = {captain:captain for captain in captain_ids}
				groupies = []
				for visitor in visitors:
					if visitor.id in captains.keys():
						groupies.append((visitor,visitor.id))
					else:
						groupies.append((visitor,None))
				context["groupies"] = groupies
			else:
				context["group"] = None
				context["unauthorized"] = True
				context["groupies"] = []
		return context

class OnlineKonView(ListView):
	model = Session
	template_name = "online_kon.html"
	paginate_by = 100

	def get_queryset(self):
		cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 67,
		})
		try:
			user_ids = cache_mem.get('online')
			queryset = User.objects.filter(id__in=user_ids).values('username', 'userprofile__score', 'userprofile__avatar')
		except:
			queryset = []
		return queryset

	def get_context_data(self, **kwargs):
		context = super(OnlineKonView, self).get_context_data(**kwargs)
		context["with_thumbs"] = False
		if self.request.user.is_authenticated():
			if not context["object_list"]:
				context["whose_online"] = False
			else:
				context["whose_online"] = True
			context["legit"] = FEMALES
			context["show_locked_search"] = (not is_uname_search_unlocked(self.request.user.id)) and \
			(self.request.user.userprofile.score > SEARCH_FEATURE_THRESHOLD)
			if self.request.is_feature_phone:
				on_feature_phone = True
			on_fbs = self.request.META.get('HTTP_X_IORG_FBS',False)
			if not on_fbs:
				context["object_list"] = retrieve_thumbs(context["object_list"])
				context["with_thumbs"] = True
		return context

class WhoseOnlineView(FormView):
	form_class = WhoseOnlineForm
	template_name = "whose_online.html"

	def get_context_data(self, **kwargs):
		context = super(WhoseOnlineView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			context["legit"] = FEMALES
		return context

class LinkDeleteView(DeleteView):
	model = Link
	success_url = reverse_lazy("home")

def user_profile_photo(request, slug=None, photo_pk=None, is_notif=None, *args, **kwargs):
	if is_notif:
		# clicking single notif, for fans
		update_notification(viewer_id=request.user.id, object_id=photo_pk, object_type='0', seen=True, \
			updated_at=time.time(), bump_ua=False, unseen_activity=True, single_notif=False)
	if photo_pk:
		request.session["photograph_id"] = photo_pk
		return redirect("profile", slug)
	else:
		try:
			return redirect("profile", slug)
		except:
			return redirect("profile", request.user.username)

def profile_pk(request, slug=None, key=None, *args, **kwargs):
	request.session["photograph_id"] = key
	return redirect("profile", slug)

class UserProfilePhotosView(ListView):
	model = Photo
	template_name = "user_detail1.html"
	paginate_by = 10

	def get_queryset(self):
		slug = self.kwargs["slug"]
		try:
			user = User.objects.get(username=slug)
			return Photo.objects.select_related('owner__userprofile').filter(owner=user,category='1').order_by('-upload_time')
		except:
			return []

	def get_context_data(self, **kwargs):
		context = super(UserProfilePhotosView, self).get_context_data(**kwargs)
		slug = self.kwargs["slug"]
		context["slug"] = slug
		context["error"] = False
		try:
			subject = User.objects.get(username=slug)
		except:
			context["error"] = True
			return context
		star_id = subject.id
		context["mobile_verified"] = self.request.mobile_verified if star_id == self.request.user.id else is_mobile_verified(star_id)
		###########
		banned, time_remaining = check_photo_upload_ban(star_id)
		if banned:
			context["time_remaining"] = time_remaining
		else:
			context["time_remaining"] = '-2'
			if self.request.is_feature_phone or self.request.is_phone or self.request.is_mobile:
				context["is_mob"] = True
		###########
		context["subject"] = subject
		context["star_id"] = star_id
		context["legit"] = FEMALES
		total_fans, recent_fans = get_photo_fan_count(star_id)
		if total_fans:
			context["fans"] = total_fans
		else:
			context["fans"] = 0
		if recent_fans:
			context["recent_fans"] = recent_fans
		else:
			context["recent_fans"] = 0
		context["can_vote"] = False
		context["manageable"] = False
		if context["object_list"] and search_thumbs_missing(slug):
			ids_with_urls = [(photo.id,photo.image_file.url) for photo in context["object_list"][:5]]
			populate_search_thumbs.delay(slug,ids_with_urls)
		context["defender"] = False
		if self.request.user.is_authenticated():
			user_id = self.request.user.id
			username = self.request.user.username
			if in_defenders(user_id):
				context["defender"] = True
			context["authenticated"] = True
			if in_defenders(user_id):
				context["manageable"] = True
			score = self.request.user.userprofile.score
			context["score"] = score
			if score > 9 and not self.request.user_banned:
				context["can_vote"] = True
			context["voted"] = voted_for_photo_qs(context["object_list"],username)
			if is_fan(star_id, user_id):
				context["not_fan"] = False
			else:
				context["not_fan"] = True
			if username == slug:
				context["allowed_fan"] = False
				context["own_profile"] = True
				context["stars"] = UserFan.objects.filter(fan=self.request.user).count()
				context["blocked"] = get_banned_users_count(user_id)
			else:
				context["subject_id"] = star_id
				context["own_profile"] = False
				context["allowed_fan"] = True
			if star_id != user_id:
				log_profile_view.delay(user_id,star_id,time.time())
		else:
			context["authenticated"] = False
			context["not_fan"] = True
			context["allowed_fan"] = False
			context["own_profile"] = False
		return context

	def get(self, request, *args, **kwargs):
		self.object_list = self.get_queryset()
		allow_empty = self.get_allow_empty()
		if not allow_empty:
			# When pagination is enabled and object_list is a queryset,
			# it's better to do a cheap query than to load the unpaginated
			# queryset in memory.
			if (self.get_paginate_by(self.object_list) is not None
				and hasattr(self.object_list, 'exists')):
				is_empty = not self.object_list.exists()
			else:
				is_empty = len(self.object_list) == 0
			if is_empty:
				raise Http404(_("Empty list and '%(class_name)s.allow_empty' is False.")
						% {'class_name': self.__class__.__name__})
		context = self.get_context_data(object_list=self.object_list)
		try:
			target_id = self.request.session["photograph_id"]
			del self.request.session["photograph_id"]
		except:
			target_id = None
		if target_id:
			try:
				index = list(photo.id for photo in self.object_list).index(int(target_id))
			except:
				index = None
			if 0 <= index <= 9:
				addendum = '#section'+str(index+1)
			elif 10 <= index <= 19:
				addendum = '?page=2#section'+str(index+1-10)
			elif 20 <= index <= 29:
				addendum = '?page=3#section'+str(index+1-20)
			elif 30 <= index <= 39:
				addendum = '?page=4#section'+str(index+1-30)
			elif 40 <= index <= 49:
				addendum = '?page=5#section'+str(index+1-40)
			elif 50 <= index <= 59:
				addendum = '?page=6#section'+str(index+1-50)
			elif 60 <= index <= 69:
				addendum = '?page=7#section'+str(index+1-60)
			elif 70 <= index <= 79:
				addendum = '?page=8#section'+str(index+1-70)
			elif 80 <= index <= 89:
				addendum = '?page=9#section'+str(index+1-80)
			elif 90 <= index <= 99:
				addendum = '?page=10#section'+str(index+1-90)
			elif 100 <= index <= 109:
				addendum = '?page=11#section'+str(index+1-100)
			elif 110 <= index <= 119:
				addendum = '?page=12#section'+str(index+1-110)
			elif 120 <= index <= 129:
				addendum = '?page=13#section'+str(index+1-120)
			elif 130 <= index <= 139:
				addendum = '?page=14#section'+str(index+1-130)
			elif 140 <= index <= 149:
				addendum = '?page=15#section'+str(index+1-140)
			elif 150 <= index <= 159:
				addendum = '?page=16#section'+str(index+1-150)
			elif 160 <= index <= 169:
				addendum = '?page=17#section'+str(index+1-160)
			elif 170 <= index <= 179:
				addendum = '?page=18#section'+str(index+1-170)
			elif 180 <= index <= 189:
				addendum = '?page=19#section'+str(index+1-180)
			elif 190 <= index <= 199:
				addendum = '?page=20#section'+str(index+1-190)
			else:
				addendum = '#section0'		
			return HttpResponseRedirect(addendum)
		else:
			return self.render_to_response(context)

@csrf_protect
def cricket_reply(request, pk=None,*args,**kwargs):
	user_id = request.user.id
	link_writer_id = request.POST.get("lwpk",None)
	banned_by, ban_time = is_already_banned(own_id=user_id,target_id=link_writer_id, return_banner=True)
	if banned_by:
		request.session["banned_by"] = banned_by
		request.session["ban_time"] = ban_time
		request.session["where_from"] = 'cricket_comment_page'
		request.session.modified = True
		return redirect("ban_underway")
	elif request.user_banned:
		return render(request,"500.html",{})
	elif request.method == 'POST':
		user_id = request.user.id
		form = PublicreplyMiniForm(data=request.POST,user_id=user_id,link_id=pk)
		if form.is_valid():
			text=form.cleaned_data.get("description")
			set_input_rate_and_history.delay(section='home_rep',section_id=pk,text=text,user_id=user_id,time_now=time.time())
			target = process_publicreply(request=request,link_id=pk,text=text,link_writer_id=link_writer_id)
			request.session['target_id'] = pk
			if target == ":":
				return redirect("ban_underway")
			elif first_time_home_replier(user_id):
				add_home_replier(user_id)
				return render(request,'cricket_reply_tutorial.html', {'target':target,'own_self':request.user.username})
			else:
				return redirect("cric_loc")
		else:
			enqueued_match = get_current_cricket_match()
			page_obj, list_of_dictionaries, replyforms, page_num, addendum \
			= get_cric_object_list_and_forms(request=request, enqueued_match=enqueued_match, notif=pk)
			replyforms[pk] = form
			request.session['replyforms'] = replyforms
			request.session['list_of_cric_dictionaries'] = list_of_dictionaries
			request.session['cric_page'] = page_obj
			url = reverse_lazy("cricket_comment")+addendum
			return redirect(url)
	else:
		return redirect("cricket_comment")

def cricket_location(request, *args, **kwargs):
	enqueued_match = get_current_cricket_match()
	try:
		link_id = request.session['target_id']
		del request.session['target_id']
	except:
		link_id = 0
	page_obj, list_of_dictionaries, replyforms, page_num, addendum = \
	get_cric_object_list_and_forms(request=request, enqueued_match=enqueued_match, notif=link_id)
	request.session['list_of_cric_dictionaries'] = list_of_dictionaries
	request.session['cric_page'] = page_obj
	request.session['replyforms'] = replyforms
	url = reverse_lazy("cricket_comment")+addendum
	return redirect(url)

@csrf_protect
def cricket_comment(request,*args,**kwargs):
	enqueued_match = get_current_cricket_match()
	if request.method == 'POST':
		user = request.user
		user_id = user.id
		if not request.mobile_verified:
			CSRF = csrf.get_token(request)
			temporarily_save_user_csrf(str(user_id), CSRF)
			return render(request, 'cant_write_on_home_without_verifying.html', {'csrf':CSRF,'from_cric':True})
		form = CricketCommentForm(request.POST,user_id=user_id)
		if form.is_valid():
			description = form.cleaned_data.get("description")
			set_input_rate_and_history.delay(section='home',section_id='1',text=description,user_id=user_id,time_now=time.time())
			if user.userprofile.score < -25:
				if not HellBanList.objects.filter(condemned_id=user_id).exists(): #only insert user in hell-ban list if she isn't there already
					HellBanList.objects.create(condemned_id=user_id) #adding user to hell-ban list
					user.userprofile.score = random.randint(10,71)
			else:
				user.userprofile.score = user.userprofile.score + 1 #adding 1 point every time a user submits new content
			user.userprofile.save()
			category = request.POST.get("btn")
			with_votes = 0
			if request.is_feature_phone:
				device = '1'
			elif request.is_phone:
				device = '2'
			elif request.is_tablet:
				device = '4'
			elif request.is_mobile:
				device = '5'
			else:
				device = '3'
			link = Link.objects.create(description=description,submitter_id=user_id,rank_score=10.1, device=device,\
				cagtegory=category)
			try:
				av_url = user.userprofile.avatar.url
			except ValueError:
				av_url = None
			add_home_link(link_pk=link.id, categ=category, nick=user.username, av_url=av_url, desc=description, \
				scr=user.userprofile.score, cc=0, writer_pk=user_id, device=device,\
				by_pinkstar=(True if user.username in FEMALES else False))
			if request.user_banned:
				incr_unfiltered_cric_comm(link.id,enqueued_match['id'])
				extras = add_unfiltered_post(link.id)
				if extras:
					queue_for_deletion.delay(extras)
			else:
				try:
					incr_cric_comm(link.id,enqueued_match['id']) #adding link to relevant list
					incr_unfiltered_cric_comm(link.id,enqueued_match['id'])
				except KeyError:
					return redirect("home")
				add_filtered_post(link.id)
				extras = add_unfiltered_post(link.id)
				if extras:
					queue_for_deletion.delay(extras)
			return redirect(reverse_lazy("cricket_comment")+"?page=1#section1")
		else:
			nickname = request.user.username
			score = request.user.userprofile.score
			if 'list_of_cric_dictionaries' in request.session and 'cric_page' in request.session and 'replyforms' in request.session:
				if request.session['list_of_cric_dictionaries'] and request.session['cric_page'] and request.session['replyforms']:
					list_of_dictionaries = request.session['list_of_cric_dictionaries']
					page_obj = request.session['cric_page']
					replyforms = request.session['replyforms']
				else:
					page_obj, list_of_dictionaries, replyforms, page_num, addendum \
					= get_cric_object_list_and_forms(request=request, enqueued_match=enqueued_match)
				del request.session['list_of_cric_dictionaries']
				del request.session['cric_page']
				del request.session['replyforms']
			else:
				page_obj, list_of_dictionaries, replyforms, page_num, addendum \
				= get_cric_object_list_and_forms(request=request, enqueued_match=enqueued_match)
			try:
				team_name1, team_name2 = enqueued_match['team1'], enqueued_match['team2']
			except KeyError:
				team_name1, team_name2 = 'Team 1', 'Team 2'
			try:
				cric_summ, cc = assemble_cricket_summary(enqueued_match)
			except KeyError:
				cric_summ, cc = None, '100+'
			secret_key = uuid.uuid4()
			set_text_input_key(request.user.id, '1', 'home', secret_key)
			try:
				context={'form':form,'replyforms':replyforms,'page':page_obj,'status':enqueued_match['status'],\
				'team1':CRICKET_TEAM_NAMES[team_name1],'checked':FEMALES,'object_list': list_of_dictionaries,\
				'team2':CRICKET_TEAM_NAMES[team_name2],'css_class1':CRICKET_COLOR_CLASSES[team_name1],'nickname':nickname,\
				'css_class2':CRICKET_COLOR_CLASSES[team_name2],'team1_id':CRICKET_TEAM_IDS[team_name1],\
				'team2_id':CRICKET_TEAM_IDS[team_name2],'score':score,'cc':cc,'cric_summ':cric_summ,\
				'sk':secret_key}
			except KeyError:
				context={'form':form,'page':page_obj,'status':enqueued_match['status'],'object_list': list_of_dictionaries,\
				'team1':team_name1,'team2':team_name2,'checked':FEMALES,'nickname':nickname,'replyforms':replyforms,\
				'css_class1':CRICKET_COLOR_CLASSES['misc'],'css_class2':CRICKET_COLOR_CLASSES['misc'],'score':score,\
				'team1_id':CRICKET_TEAM_IDS['misc'],'team2_id':CRICKET_TEAM_IDS['misc'],'cc':cc,'cric_summ':cric_summ,\
				'sk':secret_key}
			return render(request,"cricket_comment.html",context)
	else:
		form = CricketCommentForm()
		nickname = request.user.username
		score = request.user.userprofile.score
		if 'list_of_cric_dictionaries' in request.session and 'cric_page' in request.session and 'replyforms' in request.session:
			if request.session['list_of_cric_dictionaries'] and request.session['cric_page'] and request.session['replyforms']:
				list_of_dictionaries = request.session['list_of_cric_dictionaries']
				page_obj = request.session['cric_page']
				replyforms = request.session['replyforms']
			else:
				page_obj, list_of_dictionaries, replyforms, page_num, addendum \
				= get_cric_object_list_and_forms(request=request, enqueued_match=enqueued_match)
			del request.session['list_of_cric_dictionaries']
			del request.session['cric_page']
			del request.session['replyforms']
		else:
			try:
				page_obj, list_of_dictionaries, replyforms, page_num, addendum \
				= get_cric_object_list_and_forms(request=request, enqueued_match=enqueued_match)
			except:
				return render(request,'no_cricket.html',{})
		try:
			team_name1, team_name2 = enqueued_match['team1'], enqueued_match['team2']
		except KeyError:
			team_name1, team_name2 = 'Team 1', 'Team 2'
		try:
			cric_summ, cc = assemble_cricket_summary(enqueued_match)
		except KeyError:
			cric_summ, cc = None, '100+'
		secret_key = uuid.uuid4()
		set_text_input_key(request.user.id, '1', 'home', secret_key)
		try:
			context={'form':form,'replyforms':replyforms,'page':page_obj,'status':enqueued_match['status'],\
			'team1':CRICKET_TEAM_NAMES[team_name1],'checked':FEMALES,'score':score,'nickname':nickname,\
			'team2':CRICKET_TEAM_NAMES[team_name2],'object_list': list_of_dictionaries,'cric_summ':cric_summ,\
			'css_class1':CRICKET_COLOR_CLASSES[team_name1],'css_class2':CRICKET_COLOR_CLASSES[team_name2],\
			'team1_id':CRICKET_TEAM_IDS[team_name1],'team2_id':CRICKET_TEAM_IDS[team_name2],'cc':cc,\
			'sk':secret_key}
		except KeyError:
			context={'form':form,'page':page_obj,'status':enqueued_match['status'],'object_list': list_of_dictionaries,\
			'team1':team_name1,'team2':team_name2,'checked':FEMALES,'nickname':nickname,'replyforms':replyforms,\
			'css_class1':CRICKET_COLOR_CLASSES['misc'],'css_class2':CRICKET_COLOR_CLASSES['misc'],'score':score,\
			'team1_id':CRICKET_TEAM_IDS['misc'],'team2_id':CRICKET_TEAM_IDS['misc'],'cric_summ':cric_summ,'cc':cc,\
			'sk':secret_key}
		return render(request,"cricket_comment.html",context)


def assemble_cricket_summary(enqueued_match):
	"""
	Helper function for summarizing match described in cricket_comment()
	"""
	if enqueued_match['ended'] == '1':
		return enqueued_match['status'], enqueued_match['cc']
	else:
		if enqueued_match['score1'] != 'None' and enqueued_match['score2'] != 'None':
			return enqueued_match['team2']+' '+enqueued_match['score2']+' vs '+enqueued_match['team1']+' '+enqueued_match['score1'], \
			enqueued_match['cc']
		elif enqueued_match['score1'] != 'None':
			return enqueued_match['team1']+' '+enqueued_match['score1']+' vs '+enqueued_match['team2'], enqueued_match['cc']
		elif enqueued_match['score2'] != 'None':
			return enqueued_match['team2']+' '+enqueued_match['score2']+' vs '+enqueued_match['team1'], enqueued_match['cc']
		else:
			return enqueued_match['status'], enqueued_match['cc']


def get_cric_object_list_and_forms(request, enqueued_match, notif=None):
	try:
		if request.user_banned:
			link_objs = current_match_unfiltered_comments(enqueued_match['id']) # list of Link object ids
		else:
			link_objs = current_match_comments(enqueued_match['id']) # list of Link object ids
	except:
		return redirect("home")
	if notif:
		try:
			index = link_objs.index(notif)
		except:
			index = 0
		page_num, addendum = get_addendum(index,CRICKET_COMMENTS_PER_PAGE)
	else:
		addendum = '?page=1#section0'
		page_num = request.GET.get('page', '1')
	page_obj = get_page_obj(page_num,link_objs,CRICKET_COMMENTS_PER_PAGE)
	# photo_ids, non_photo_link_ids, list_of_dictionaries = retrieve_home_links(page_obj.object_list)
	photo_links, list_of_dictionaries = retrieve_home_links(page_obj.object_list)
	replyforms = {}
	for obj in list_of_dictionaries:
		replyforms[obj['l']] = PublicreplyMiniForm() #passing link_id to forms dictionary
	return page_obj, list_of_dictionaries, replyforms, page_num, addendum

@csrf_protect
def cricket_comment_page(request,*args,**kwargs):
	if request.method == 'POST':
		if request.user.userprofile.score < CRICKET_SUPPORT_STARTING_POINT:
			context={"score_req":CRICKET_SUPPORT_STARTING_POINT}
			return render(request,"cric_score_req.html",context)
		else:
			if first_time_psl_supporter(request.user.id):
				add_psl_supporter(request.user.id)
				return render(request,'psl_supporter_tutorial.html',{})
			else:
				return redirect("cricket_comment")
	else:
		return redirect("link_create_pk")

@csrf_protect
def cricket_initiate(request,*args,**kwargs):
	if request.method == 'POST':
		decision = request.POST.get("decision")
		if decision == 'yes':
			team_to_follow = request.POST.get("team")
			team1 = request.POST.get("team1")
			team2 = request.POST.get("team2")
			score1 = request.POST.get("score1")
			score2 = request.POST.get("score2")
			status = request.POST.get("status")
			create_cricket_match(team_to_follow, team1, score1, team2, score2, status)
			context = {'team1':team1, 'score1':score1, 'team2':team2, 'score2':score2}
			return render(request,"cricket_initialization.html",context)
		else:
			return redirect("cricket_dashboard")
	else:
		return redirect("cricket_dashboard")

@csrf_protect
def cricket_remove(request,*args,**kwargs):
	if request.method == 'POST':
		decision = request.POST.get("decision")
		if decision == 'yes':
			enqueued_match = get_current_cricket_match()
			del_cricket_match(enqueued_match['id'])
			return redirect("cricket_dashboard")
		else:
			return redirect("home")
	else:	
		return redirect("home")

@csrf_protect
def cricket_dashboard(request,*args,**kwargs):
	if request.user.username == 'pathan-e-khan' or request.user.username == 'mhb11':
		teams_with_results = cricket_scr()
		enqueued_match = get_current_cricket_match()
		if enqueued_match:
			team1 = enqueued_match['team1']
			score1 = enqueued_match['score1']
			team2 = enqueued_match['team2']
			score2 = enqueued_match['score2']
			context={'team1':team1,'team2':team2,'score1':score1,'score2':score2,'enqueued':1}
			return render(request,"cricket_dashboard.html",context)
		else:
			if request.method == 'POST':
				team_to_follow = request.POST.get("game")
				match_to_follow = 0
				for match in teams_with_results:
					if match[0][0] == team_to_follow:
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
					if "won by" in status.lower() or "drawn" in status.lower() or "tied" in status.lower() \
					or "abandoned" in status.lower():
						#this match should not be enquequed since it's over
						context = {'too_late':1,'score1':score1,'team1':team1,'score2':score2,'team2':team2}
					elif "begin" in status.lower():
						#this match is yet to begin, don't enqueue 
						context = {'too_early':1,'score1':score1,'team1':team1,'score2':score2,'team2':team2}
					else:
						context = {'team1':team1,'score1':score1,'team2':team2,'score2':score2,'status':status,\
						'team_to_follow':team_to_follow}
					return render(request,'cricket_dashboard.html',context)
				else:
					context = {'teams_with_results':teams_with_results}
					return render(request,'cricket_dashboard.html',context)
			else:
				context = {'teams_with_results':teams_with_results}
				return render(request,"cricket_dashboard.html",context)
	else:
		return redirect("home")

class UserProfileDetailView(DetailView):
	model = get_user_model()
	slug_field = "username"
	template_name = "user_detail.html"

	def get_object(self, queryset=None):
		user = super(UserProfileDetailView, self).get_object(queryset)
		UserProfile.objects.get_or_create(user=user)
		return user

	def get_context_data(self, **kwargs):
		context = super(UserProfileDetailView, self).get_context_data(**kwargs)
		context["ratified"] = FEMALES
		if self.request.user.is_authenticated():
			user_id = str(self.request.user.id)
			star_id = retrieve_user_id(self.kwargs["slug"])
			if star_id != user_id:
				log_profile_view.delay(user_id,star_id,time.time())
		return context

class DirectMessageCreateView(FormView):
	model = Group
	form_class = DirectMessageCreateForm

	def form_valid(self, form):
		if self.request.method == 'POST':
			pk = self.kwargs["pk"]
			user = User.objects.get(id=pk)
			user_score = self.request.user.userprofile.score
			if user_score > 500:
				self.request.user.userprofile.score = self.request.user.userprofile.score - 500
				invitee = user.username
				topic = invitee+" se gupshup"
				unique = uuid.uuid4()
				try:
					group = Group.objects.create(topic=topic, rules='', owner=self.request.user, private ='1', unique=unique)
					self.request.user.userprofile.save()
					reply_list=[]
					seen_list=[]
					reply = Reply.objects.create(text=invitee, category='1', which_group_id=group.id, writer=self.request.user)
					add_group_member(group.id, self.request.user.username)
					add_group_invite(pk, group.id,reply.id)
					add_user_group(self.request.user.id, group.id)
					self.request.session["unique_id"] = unique
					return redirect("private_group_reply")#, slug=unique)
				except:
					return redirect("profile", slug=invitee)
			else:
				return redirect("profile",slug=user.username)

class ClosedGroupCreateView(CreateView):
	model = Group
	form_class = ClosedGroupCreateForm
	template_name = "new_closed_group.html"

	def form_valid(self, form):
		if self.request.user.userprofile.score > (PRIVATE_GROUP_COST-1):
			f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
			user = self.request.user
			user_id = user.id
			f.owner = user
			f.private = 1
			unique = uuid.uuid4()
			f.unique = unique
			f.rules = ''
			f.category = '1'
			# set_prev_retort(user_id,f.topic)
			f.save()
			creation_text = 'mein ne new mehfil shuru kar di'
			reply = Reply.objects.create(text=creation_text,which_group=f,writer_id=user_id)
			reply_time = convert_to_epoch(reply.submitted_on)
			try:
				url = user.userprofile.avatar.url
			except ValueError:
				url = None
			create_object(object_id=f.id, object_type='3',object_owner_id=user_id,object_desc=f.topic,lt_res_time=reply_time,\
				lt_res_avurl=url,lt_res_sub_name=user.username,lt_res_text=creation_text,group_privacy=f.private, slug=f.unique,\
				lt_res_wid=user_id)
			create_notification(viewer_id=user_id,object_id=f.id,object_type='3',seen=True,updated_at=reply_time,unseen_activity=True)
			f.owner.userprofile.score = f.owner.userprofile.score - PRIVATE_GROUP_COST
			f.owner.userprofile.save()
			add_group_member(f.id, self.request.user.username)
			add_user_group(user_id, f.id)
			try: 
				return redirect("invite_private", slug=f.unique)
			except:
				self.request.session["unique_id"] = f.unique
				return redirect("private_group_reply")#, slug=unique)
		else:
			return redirect("group_page")

class OpenGroupCreateView(CreateView):
	model = Group
	form_class = OpenGroupCreateForm
	template_name = "new_open_group.html"

	def get_form_kwargs( self ):
		kwargs = super(OpenGroupCreateView,self).get_form_kwargs()
		kwargs['verified'] = self.request.mobile_verified
		return kwargs

	def form_valid(self, form):
		if self.request.user.userprofile.score > (PUBLIC_GROUP_COST-1):
			f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
			user = self.request.user
			user_id = user.id
			f.owner = user
			f.private = 0
			unique = uuid.uuid4()
			f.unique = unique
			# set_prev_retort(user_id,f.topic)
			f.save()
			creation_text = 'mein ne new mehfil shuru kar di'
			reply = Reply.objects.create(text=creation_text,which_group=f,writer=user)
			reply_time = convert_to_epoch(reply.submitted_on)
			try:
				url = user.userprofile.avatar.url
			except ValueError:
				url = None
			f_id = f.id
			create_object(object_id=f_id, object_type='3',object_owner_id=user_id,object_desc=f.topic,lt_res_time=reply_time,\
				lt_res_avurl=url,lt_res_sub_name=user.username,lt_res_text=creation_text,group_privacy=f.private, slug=f.unique,\
				lt_res_wid=user_id)
			create_notification(viewer_id=user_id,object_id=f_id,object_type='3',seen=True,updated_at=reply_time,unseen_activity=True)
			rank_public_groups.delay(group_id=f_id,writer_id=user_id)
			public_group_attendance_tasks.delay(group_id=f_id, user_id=user_id)
			link = Link.objects.create(submitter=user, description=f.topic, cagtegory='2', url=unique)
			try:
				av_url = f.owner.userprofile.avatar.url
			except ValueError:
				av_url = None
			add_home_link(link_pk=link.id, categ='2', nick=f.owner.username, av_url=av_url, desc=f.topic, \
				scr=f.owner.userprofile.score, cc=1, writer_pk=user_id, device='1', meh_url=unique,\
				by_pinkstar = (True if f.owner.username in FEMALES else False))
			if self.request.user_banned:
				extras = add_unfiltered_post(link.id)
				if extras:
					queue_for_deletion.delay(extras)
			else:
				add_filtered_post(link.id)
				extras = add_unfiltered_post(link.id)
				if extras:
					queue_for_deletion.delay(extras)
			f.owner.userprofile.score = f.owner.userprofile.score - PUBLIC_GROUP_COST
			f.owner.userprofile.save()
			add_group_member(f_id, user.username)
			add_user_group(user_id, f_id)
			try: 
				return redirect("invite", slug=unique)
			except:
				return redirect("public_group", slug=unique)
		else:
			return redirect("group_page")

def direct_message(request, pk=None, *args, **kwargs):
	if pk.isdigit():
		request.session["dm"] = pk
		return redirect("direct_message_help")
	else:
		return redirect("score_help")

class DirectMessageView(FormView):
	form_class = DirectMessageForm
	template_name = "direct_message_help.html"

	def get_context_data(self, **kwargs):
		context = super(DirectMessageView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			context["nopk"] = False
			try:
				pk = self.request.session["dm"]
				self.request.session["dm"] = None
				self.request.session.modified = True
			except:
				context["nopk"] = True
				context["target"] = None
				return context
			if pk:
				target = User.objects.get(id=pk)
				context["target"] = target
			else:
				context["nopk"] = True
				context["target"] = None
				return context
		return context


class ReinvitePrivateView(FormView):
	form_class = ReinvitePrivateForm
	template_name = "reinvite_private.html"

	def get_context_data(self, **kwargs):
		context = super(ReinvitePrivateView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			unique = self.request.session["unique_id"]
			context["unique"] = unique
		return context


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def process_public_group_invite(request,*args, **kwargs):
	if request.user_banned:
		return redirect("group_page")
	elif request.method == "POST":	
		uuid = request.POST.get("puid",None)
		pk = request.POST.get("vid",None)
		try:
			group = Group.objects.get(unique=uuid)
			group_id = group.id
		except:
			group_id = -1
		if group_id > -1:
			invitee_username = User.objects.filter(id=pk).values_list('username',flat=True)[0]
			if check_group_invite(pk, group_id) or check_group_member(group_id, invitee_username):
				return redirect("reinvite_help", slug= uuid)
			else:#this person ought to be sent an invite
				#send a notification to this person to check out the group
				reply = Reply.objects.create(text=invitee_username, category='1', which_group_id=group_id,writer=request.user)
				add_group_invite(pk, group_id,reply.id)
		return redirect("invite")
	else:
		return redirect("group_page")

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def process_private_group_invite(request, *args, **kwargs):
	if request.method=="POST":
		if request.user_banned:
			return redirect("group_page")
		else:
			uuid = request.POST.get("puid",None)
			pk = request.POST.get("vid",None)
			try:
				group = Group.objects.get(unique=uuid)
				group_id = group.id
			except:
				group_id = -1
			if group_id > -1:
				invitee_username = User.objects.filter(id=pk).values_list('username',flat=True)[0]
				if check_group_invite(pk, group_id) or check_group_member(group_id, invitee_username):
					return redirect("reinvite_private_help")
				else:#this person ought to be sent an invite
					#send a notification to this person to check out the group
					reply = Reply.objects.create(text=invitee_username, category='1', which_group_id=group_id,writer=request.user)
					reply_id = reply.id
					add_group_invite(pk, group_id,reply_id)
					set_latest_group_reply(group_id,reply_id)
			request.session["unique_id"] = None
			request.session.modified = True
			return redirect("invite_private", slug=uuid)
	else:
		return redirect("group_page")

def invite_private(request, slug=None, *args, **kwargs):
	if valid_uuid(slug):
		request.session["unique_id"] = slug
		return redirect("invite_private_group")
	else:
		return redirect("score_help")

class InviteUsersToPrivateGroupView(ListView):
	model = Session
	template_name = "invite_for_private_group.html"
	paginate_by = 100

	def get_queryset(self):
		if self.request.user_banned:
			return []
		else:
			cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 30,
			})
			global condemned
			try:
				user_ids = cache_mem.get('online')
				group = Group.objects.get(unique=self.request.session["unique_id"])
				users_purified = [pk for pk in user_ids if pk not in condemned]
				non_invited_online_ids = bulk_check_group_invite(users_purified,group.id)
				non_invited_non_member_online_ids = bulk_check_group_membership(non_invited_online_ids,group.id)
				return User.objects.filter(id__in=non_invited_non_member_online_ids).values('id','userprofile__score','userprofile__avatar','username')
			except:
				return []

	def get_context_data(self, **kwargs):
		context = super(InviteUsersToPrivateGroupView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			context["legit"] = FEMALES
			try:	
				unique = self.request.session["unique_id"]
				context["unique"] = unique
				group = Group.objects.get(unique=unique)
				context["authorized"] = True
				context["group"] = group
			except:
				context["authorized"] = False
		return context				


class InviteUsersToGroupView(ListView):
	model = Session
	template_name = "invite_for_groups.html"
	paginate_by = 100
	
	def get_queryset(self):
		if self.request.user_banned:
			return []
		else:
			cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 30,
			})	
			global condemned
			try:
				user_ids = cache_mem.get('online')
				group = Group.objects.get(unique=self.request.session["public_uuid"])
				users_purified = [pk for pk in user_ids if pk not in condemned]
				non_invited_online_ids = bulk_check_group_invite(users_purified,group.id)
				non_invited_non_member_online_ids = bulk_check_group_membership(non_invited_online_ids,group.id)
				return User.objects.filter(id__in=non_invited_non_member_online_ids).values('id','userprofile__score','userprofile__avatar','username')
			except:
				return []

	def get_context_data(self, **kwargs):
		context = super(InviteUsersToGroupView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			try:
				context["legit"] = FEMALES
				unique = self.request.session["public_uuid"]
				context["unique"] = unique
				group = Group.objects.get(unique=unique)
				context["group"] = group
			except:
				context["group"] = None
		return context

class ExternalSalatInviteView(FormView):
	template_name = "salat_sms.html"
	form_class = ExternalSalatInviteForm

	def get_context_data(self, **kwargs):
		context = super(ExternalSalatInviteView, self).get_context_data(**kwargs)
		cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 70,
		})
		salat_timings = cache_mem.get('salat_timings')
		if salat_timings['namaz']:
			context["namaz_time"] = True
			context["namaz"] = salat_timings['namaz']
			context["freebasics_url"] = "https://https-damadam-pk.0.freebasics.com"
			context["regular_url"] = "https://damadam.pk"
		else:
			context["namaz_time"] = False
		return context

class SalatInviteView(FormView):
	template_name = "salat_invite.html"
	form_class = SalatInviteForm

	def get_context_data(self, **kwargs):
		context = super(SalatInviteView, self).get_context_data(**kwargs)
		cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 70,
		})
		salat_timings = cache_mem.get('salat_timings')
		if salat_timings['namaz']:
			context["namaz_time"] = True
			context["namaz"] = salat_timings['namaz']
		else:
			context["namaz_time"] = False
		return context

class InternalSalatInviteView(ListView):
	template_name = "internal_salat_invite.html"

	def get_queryset(self):
		cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 30,
			})
		try:
			user_ids = cache_mem.get('online')
			queryset = User.objects.select_related('userprofile').filter(id__in=user_ids)
		except:
			queryset = None
		return queryset

	def get_context_data(self, **kwargs):
		context = super(InternalSalatInviteView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			#get current namaz start time
			now = datetime.utcnow()+timedelta(hours=5)
			current_minute = now.hour * 60 + now.minute
			previous_namaz, next_namaz, namaz, next_namaz_start_time, current_namaz_start_time, current_namaz_end_time = namaz_timings[current_minute]
			try:
				starting_time = datetime.combine(now.today(), current_namaz_start_time)
			except:
				context["user_list"] = None
				context["unauthorized"] = True #it's not time for any namaz!
				return context
			cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 30,
			})
			user_ids = cache_mem.get('online')
			if namaz:
				context["namaz"] = namaz
				context["unauthorized"] = False
				if namaz == 'Fajr':
					#check which users have been sent an invite for the current namaz, AFTER the current namaz's start time
					invites = SalatInvite.objects.filter(invitee_id__in=user_ids, which_salat='1', sent_at__gte=starting_time).values_list('invitee_id', flat=True)
					already_prayed = LatestSalat.objects.filter(salatee_id__in=user_ids, skipped=False, latest_salat='1',when__gte=starting_time).values_list('salatee_id', flat=True)
					#remove already invited and already prayed users from the object_list:
					context["user_list"] = [user for user in context["object_list"] if user.pk not in set(list(invites) + list(already_prayed))]
				elif namaz == 'Zuhr':
					#check which users have been sent an invite for the current namaz, AFTER the current namaz's start time
					invites = SalatInvite.objects.filter(invitee_id__in=user_ids, which_salat='2', sent_at__gte=starting_time).values_list('invitee_id', flat=True)
					already_prayed = LatestSalat.objects.filter(salatee_id__in=user_ids, skipped=False, latest_salat='2',when__gte=starting_time).values_list('salatee_id', flat=True)
					#remove already invited and already prayed users from the object_list:
					context["user_list"] = [user for user in context["object_list"] if user.pk not in set(list(invites) + list(already_prayed))]
				elif namaz == 'Asr':
					#check which users have been sent an invite for the current namaz, AFTER the current namaz's start time
					invites = SalatInvite.objects.filter(invitee_id__in=user_ids, which_salat='3', sent_at__gte=starting_time).values_list('invitee_id', flat=True)
					already_prayed = LatestSalat.objects.filter(salatee_id__in=user_ids, skipped=False, latest_salat='3',when__gte=starting_time).values_list('salatee_id', flat=True)
					#remove already invited and already prayed users from the object_list:
					context["user_list"] = [user for user in context["object_list"] if user.pk not in set(list(invites) + list(already_prayed))]
				elif namaz == 'Maghrib':
					#check which users have been sent an invite for the current namaz, AFTER the current namaz's start time
					invites = SalatInvite.objects.filter(invitee_id__in=user_ids, which_salat='4', sent_at__gte=starting_time).values_list('invitee_id', flat=True)
					already_prayed = LatestSalat.objects.filter(salatee_id__in=user_ids, skipped=False, latest_salat='4',when__gte=starting_time).values_list('salatee_id', flat=True)
					#remove already invited and already prayed users from the object_list:
					context["user_list"] = [user for user in context["object_list"] if user.pk not in set(list(invites) + list(already_prayed))]
				elif namaz == 'Isha':
					#check which users have been sent an invite for the current namaz, AFTER the current namaz's start time
					invites = SalatInvite.objects.filter(invitee_id__in=user_ids, which_salat='5', sent_at__gte=starting_time).values_list('invitee_id', flat=True)
					already_prayed = LatestSalat.objects.filter(salatee_id__in=user_ids, skipped=False, latest_salat='5',when__gte=starting_time).values_list('salatee_id', flat=True)
					#remove already invited and already prayed users from the object_list:
					context["user_list"] = [user for user in context["object_list"] if user.pk not in set(list(invites) + list(already_prayed))]
				else:
					context["user_list"] = None
					context["unauthorized"] = True #some error must have occurred, abort
			else:
				context["user_list"] = None
				context["unauthorized"] = True #it's not time for any namaz!
			return context
	

class GroupRankingView(ListView):
	model = Group
	form_class = GroupListForm
	template_name = "group_ranking.html"
	paginate_by = 25

	def get_queryset(self):
		trending_groups = []
		group_ids_list = get_ranked_public_groups()
		group_ids_dict = dict(group_ids_list)
		group_ids = map(itemgetter(0), group_ids_list)
		groups = Group.objects.select_related('owner').filter(id__in=group_ids)
		for group in groups:
			group_id = str(group.id)
			trending_groups.append((group,group_ids_dict[group_id]))
		trending_groups.sort(key=itemgetter(1), reverse=True)
		trending_groups = map(itemgetter(0), trending_groups)
		return trending_groups


############################################################################################################

#rate limit this
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@sensitive_post_parameters()
@csrf_protect
def reset_password(request,*args,**kwargs):
	if request.method == 'POST':
		form = ResetPasswordForm(data=request.POST,request=request)
		if form.is_valid():
			form.save()
			password = request.POST.get("password")
			context={'new_pass':password}
			request.session.pop("authentic_password_owner", None)
			request.user.session_set.exclude(session_key=request.session.session_key).delete() # logging the user out of everywhere else
			return render(request,'new_password.html',context)
		else:
			try:
				allowed = request.session['authentic_password_owner']
				if allowed is True:
					context={'form':form,'allowed':True}					
				else:
					context={'form':form,'allowed':False}
			except:
				context={'form':form,'allowed':None}
			return render(request,'reset_password.html',context)	
	else:
		form = ResetPasswordForm()
		try:
			allowed = request.session['authentic_password_owner']
			if allowed is True:
				#can press forward, user is 'allowed'
				context={'form':form,'allowed':allowed}
				return render(request,'reset_password.html',context)
			else:
				#send back for reauth
				return redirect("reauth")
		except:
			#send back for reauth
			return redirect("reauth")

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
@ratelimit(method='POST', rate='7/h')
def reauth(request, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		context={'pk':'pk'}
		return render(request, 'penalty_reauth.html', context)
	elif first_time_password_changer(request.user.id):
		add_password_change(request.user.id)
		context={'username':request.user.username}
		return render(request, 'password_change_tutorial.html', context)
	else:
		if request.method == 'POST':
			form = ReauthForm(data=request.POST,request=request)
			if form.is_valid():
				request.session['authentic_password_owner'] = True
				return redirect("reset_password")
			else:
				context={'form':form}
				return render(request, 'reauth.html', context)
		else:
			form = ReauthForm()
			context = {'form':form}
			return render(request, 'reauth.html', context)

class VerifiedView(ListView):
	model = User
	form_class = VerifiedForm
	template_name = "verified.html"
	paginate_by = 100

	def get_queryset(self):
		global condemned
		return User.objects.filter(username__in=FEMALES).order_by('-userprofile__score')

class TopPhotoView(ListView):
	model = User
	# form_class = TotalFanAndPhotos
	template_name = "top_photo.html"

	def get_queryset(self):
		cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
			'LOCATION': MEMLOC, 'TIMEOUT': 1260,
		})
		top_stars = cache_mem.get('fans')
		return top_stars

	def get_context_data(self, **kwargs):
		context = super(TopPhotoView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			context["verified"] = FEMALES
		return context

class TopView(ListView):
	model = User
	form_class = TopForm
	template_name = "top.html"

	def get_queryset(self):
		return UserProfile.objects.select_related('user').defer('attractiveness','previous_retort','age','gender','bio','shadi_shuda',\
			'media_score','mobilenumber','streak','user__first_name','user__last_name','user__email','user__is_staff','user__is_active',\
			'user__is_superuser','user__email','user__date_joined','user__last_login','user__password','user__id').order_by('-score')[:100]

	def get_context_data(self, **kwargs):
		context = super(TopView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			context["verified"] = FEMALES		
		return context

class GroupPageView(ListView):
	model = Reply
	form_class = GroupPageForm
	template_name = "group.html"
	paginate_by = 15

	def get_queryset(self):
		groups = []
		replies = []
		user_id = self.request.user.id
		group_ids = get_user_groups(user_id)
		replies = filter(None, get_latest_group_replies(group_ids))
		invite_reply_ids = get_active_invites(user_id) #contains all current invites
		invite_reply_ids |= set(replies) #doing union of two sets. Gives us all latest reply ids, minus any deleted replies (e.g. if the group object had been deleted)
		replies_qset = Reply.objects.filter(id__in=invite_reply_ids).values('id','writer__username','which_group__topic','submitted_on','text','which_group',\
			'which_group__unique','writer__userprofile__avatar','which_group__private','category').order_by('-id')[:60]
		return get_replies_with_seen(group_replies=replies_qset,viewer_id=user_id,object_type='3')

	def get_context_data(self, **kwargs):
		context = super(GroupPageView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			context["verified"] = FEMALES
		return context

class GroupTypeView(FormView):
	form_class = GroupTypeForm
	template_name = "group_type.html"

class PhotoJawabView(FormView):
	form_class = PhotoJawabForm
	template_name = "photo_jawab.html"

class PhotoTimeView(FormView):
	form_class = PhotoTimeForm
	template_name = "photo_time.html"

	def get_context_data(self, **kwargs):
		context = super(PhotoTimeView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			ident = self.kwargs["pk"]
			context["photo_time"] = Photo.objects.get(id=ident).upload_time
		return context

class AuthPicsDisplayView(ListView):
	model = ChatPic
	template_name = "pics_display.html"
	paginate_by = 8

	def get_queryset(self):
		if self.request.user.is_authenticated():
			return ChatPic.objects.filter(owner=self.request.user).exclude(is_visible=False).order_by('-upload_time')
		else:
			return 0

def photostream_pk(request, pk=None, ident=None, *args, **kwargs):
	if pk:
		request.session["photo_photostream_id"] = pk
		request.session["photo_stream_id"] = ident
		return redirect("photostream")
	else:
		return redirect("best_photo")

class PhotostreamView(ListView):
	model = Photo
	#form_class = PhotostreamForm
	template_name = "photostream.html"
	paginate_by = 10

	def get_queryset(self):
		try:
			# ps = PhotoStream.objects.filter(id=self.request.session["photo_photostream_id"])
			queryset = Photo.objects.filter(which_stream=ps).order_by('-upload_time')[:200]
		except:
			querset = []
		return queryset

	def get_context_data(self, **kwargs):
		context = super(PhotostreamView, self).get_context_data(**kwargs)
		context["girls"] = FEMALES
		if context["object_list"]:
			context["valid"] = True
		else:
			context["valid"] = False
		pk = self.request.session["photo_photostream_id"]
		context["stream_id"] = pk
		context["can_vote"] = False
		# context["number"] = PhotoStream.objects.get(id=pk).photo_count
		return context

	def get(self, request, *args, **kwargs):
		self.object_list = self.get_queryset()
		allow_empty = self.get_allow_empty()
		if not allow_empty:
			# When pagination is enabled and object_list is a queryset,
			# it's better to do a cheap query than to load the unpaginated
			# queryset in memory.
			if (self.get_paginate_by(self.object_list) is not None
				and hasattr(self.object_list, 'exists')):
				is_empty = not self.object_list.exists()
			else:
				is_empty = len(self.object_list) == 0
			if is_empty:
				raise Http404(_("Empty list and '%(class_name)s.allow_empty' is False.")
						% {'class_name': self.__class__.__name__})
		context = self.get_context_data(object_list=self.object_list)
		try:
			target_id = self.request.session["photo_stream_id"]
			self.request.session["photo_stream_id"] = None
			self.request.session.modified = True
		except:
			target_id = None
		if target_id:
			try:
				index = list(photo.id for photo in self.object_list).index(int(target_id))
			except:
				index = None
			if 0 <= index <= 9:
				addendum = '#section'+str(index+1)
			elif 10 <= index <= 19:
				addendum = '?page=2#section'+str(index+1-10)
			elif 20 <= index <= 29:
				addendum = '?page=3#section'+str(index+1-20)
			elif 30 <= index <= 39:
				addendum = '?page=4#section'+str(index+1-30)
			elif 40 <= index <= 49:
				addendum = '?page=5#section'+str(index+1-40)
			elif 50 <= index <= 59:
				addendum = '?page=6#section'+str(index+1-50)
			elif 60 <= index <= 69:
				addendum = '?page=7#section'+str(index+1-60)
			elif 70 <= index <= 79:
				addendum = '?page=8#section'+str(index+1-70)
			elif 80 <= index <= 89:
				addendum = '?page=9#section'+str(index+1-80)
			elif 90 <= index <= 99:
				addendum = '?page=10#section'+str(index+1-90)
			elif 100 <= index <= 109:
				addendum = '?page=11#section'+str(index+1-100)
			elif 110 <= index <= 119:
				addendum = '?page=12#section'+str(index+1-110)
			elif 120 <= index <= 129:
				addendum = '?page=13#section'+str(index+1-120)
			elif 130 <= index <= 139:
				addendum = '?page=14#section'+str(index+1-130)
			elif 140 <= index <= 149:
				addendum = '?page=15#section'+str(index+1-140)
			elif 150 <= index <= 159:
				addendum = '?page=16#section'+str(index+1-150)
			elif 160 <= index <= 169:
				addendum = '?page=17#section'+str(index+1-160)
			elif 170 <= index <= 179:
				addendum = '?page=18#section'+str(index+1-170)
			elif 180 <= index <= 189:
				addendum = '?page=19#section'+str(index+1-180)
			elif 190 <= index <= 199:
				addendum = '?page=20#section'+str(index+1-190)
			else:
				addendum = '#section0'		
			return HttpResponseRedirect(addendum)
		else:
			return self.render_to_response(context)

class ChainPhotoTutorialView(FormView):
	form_class = ChainPhotoTutorialForm
	template_name = "chain_photo_tutorial.html"

	def form_valid(self, form):
		if self.request.session["ftue_chain"] and self.request.session["reply_photo_id"]:
			self.request.session["ftue_chain"] = None
			pk = self.request.session["reply_photo_id"]
			self.request.session["reply_photo_id"] = None
			self.request.session.modified = True
			if self.request.user_banned:
				return redirect("best_photo")
			else:
				if self.request.method == 'POST':
					option = self.request.POST.get("choice",'')
					if option == 'samajh gaya':
						try:
							TutorialFlag.objects.filter(user=self.request.user).update(seen_chain=True)
							return redirect("upload_photo_reply_pk", pk)
						except:
							return redirect("best_photo")
					else:
						return redirect("best_photo")
				else:
					return redirect("best_photo")
		else:
			return redirect("best_photo")

def upload_photo_reply_pk(request, pk=None, *args, **kwargs):
	if pk:
		request.session["reply_photo_id"] = pk
		try:
			seen_chain = TutorialFlag.objects.get(user=request.user).seen_chain
			if seen_chain:
				return redirect("upload_photo_reply")
			else:
				request.session["ftue_chain"] = True
				return redirect("chain_photo_tutorial")
		except:
			request.session["ftue_chain"] = True
			TutorialFlag.objects.create(user=request.user)
			return redirect("chain_photo_tutorial")
	else:
		return redirect("best_photo")

class UploadPhotoReplyView(CreateView):
	model = Photo
	form_class = UploadPhotoReplyForm
	template_name = "upload_photo_reply.html"

	def get_context_data(self, **kwargs):
		context = super(UploadPhotoReplyView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			try:
				context["authenticated"] = True
				context["photo"] = Photo.objects.get(pk=self.request.session["reply_photo_id"])
			except:
				context["authenticated"] = False
				context["photo"] = None
		return context

	def form_valid(self, form):
		f = form.save(commit=False)
		try:
			pk = self.request.session["reply_photo_id"]
			self.request.session["reply_photo_id"] = None
			self.request.session.modified = True
			target = Photo.objects.get(id=pk)
		except:
			return redirect("best_photo")
		user = self.request.user
		if user.userprofile.score < 15:
			context = {'score': '15'}
			return render(self.request, 'score_photo.html', context)
		else:
			#time_now = datetime.utcnow().replace(tzinfo=utc)
			time_now = timezone.now()
			try:
				photocooldown = PhotoCooldown.objects.filter(which_user=user).latest('time_of_uploading')
				difference = time_now - photocooldown.time_of_uploading 
				seconds = difference.total_seconds()
				if seconds < 60:
					context = {'time': round((60 - seconds),0)}
					return render(self.request, 'error_photo.html', context)
				else:
					photocooldown.time_of_uploading = time_now
					photocooldown.save()
			except:
				PhotoCooldown.objects.create(which_user=user, time_of_uploading=time_now)
			if f.image_file:
				image_file = clean_image_file(f.image_file)
				if image_file:
					f.image_file = image_file
				else:
					f.image_file = None
			else:
				f.image_file = None
			if f.image_file:
				if self.request.is_feature_phone:
					device = '1'
				elif self.request.is_phone:
					device = '2'
				elif self.request.is_tablet:
					device = '4'
				elif self.request.is_mobile:
					device = '5'
				else:
					device = '3'
				try:
					#photo being added to the head of a stream
					# photo_stream = PhotoStream.objects.filter(cover=target).latest('creation_time')
					photo = Photo.objects.create(image_file = f.image_file, owner=user, caption=f.caption, comment_count=0, device=device)
					####################################
					try:
						aggregate_object = TotalFanAndPhotos.objects.get(owner=user)
						aggregate_object.total_photos = aggregate_object.total_photos + 1
						aggregate_object.last_updated = datetime.utcnow()+timedelta(hours=5)
						aggregate_object.save()
					except:
						TotalFanAndPhotos.objects.create(owner=user, total_fans=0, total_photos=1, last_updated=datetime.utcnow()+timedelta(hours=5))
					####################################
					photo.which_stream.add(photo_stream)
					photo_stream.cover = photo
					photo_stream.photo_count = photo_stream.photo_count + 1
					photo_stream.show_time = photo.upload_time
					photo_stream.save()
					#photo.save()
				except:
					#photo added anywhere in the middle of the stream, i.e. new stream being made
					photo = Photo.objects.create(image_file = f.image_file, owner=user, caption=f.caption, comment_count=0, device=device)
					####################################
					try:
						aggregate_object = TotalFanAndPhotos.objects.get(owner=user)
						aggregate_object.total_photos = aggregate_object.total_photos + 1
						aggregate_object.last_updated = datetime.utcnow()+timedelta(hours=5)
						aggregate_object.save()
					except:
						TotalFanAndPhotos.objects.create(owner=user, total_fans=0, total_photos=1, last_updated=datetime.utcnow()+timedelta(hours=5))
					####################################
					tail_photos = Photo.objects.filter(which_stream=target.which_stream.latest('creation_time')).exclude(upload_time__gt=target.upload_time).order_by('upload_time')
					tail_photos_count = tail_photos.count()
					# stream = PhotoStream.objects.create(cover=photo, show_time=photo.upload_time, photo_count = (tail_photos_count + 1))
					photo.which_stream.add(stream)
					#gives you control of the 'through' model
					through_model = Photo.which_stream.through
					through_model.objects.bulk_create([
						through_model(photo_id=pk, photostream_id = stream.pk) for pk in tail_photos.values_list('pk', flat=True)
						])
				user.userprofile.score = user.userprofile.score - 10
				user.userprofile.save()
				return redirect("photo")
			else:
				context = {'photo': 'photo'}
				return render(self.request, 'big_photo.html', context)

def photostream_izzat(request, pk=None, *args, **kwargs):
	if pk:
		try:
			# stream_object_id = PhotoStream.objects.get(cover_id=pk).id
			return redirect("photo_izzat", stream_object_id)
		except:
			return redirect("best_photo")
	else:
		return redirect("best_photo")

class VideoScoreView(FormView):
	form_class = VideoScoreForm
	template_name = "video_score_breakdown.html"

	def get_context_data(self, **kwargs):
		context = super(VideoScoreView, self).get_context_data(**kwargs)
		key = self.kwargs["pk"]
		context["key"] = key
		if self.request.user.is_authenticated():
			context["authenticated"] = True
		else:
			context["authenticated"] = False
		video = Video.objects.get(id=key)
		context["video"] = video
		usernames_and_votes = get_video_votes(key)
		context["votes"] = usernames_and_votes
		if context["votes"]:
			context["content"] = True
			context["visible_score"] = video.visible_score 
		else:
			context["content"] = False
			context["visible_score"] = video.visible_score
		context["girls"] = FEMALES
		return context

class PhotoScoreView(FormView):
	form_class = PhotoScoreForm
	template_name = "photo_score_breakdown.html"

	def get_context_data(self, **kwargs):
		context = super(PhotoScoreView, self).get_context_data(**kwargs)
		key = self.kwargs["pk"]
		context["origin"] = self.kwargs["origin"]
		context["key"] = key
		if context["origin"] == '3':
			try:
				#if originating from user profile
				context["slug"] = self.kwargs["slug"]
			except:
				context["slug"] = self.request.user.username
		context["defender"] = False
		if self.request.user.is_authenticated():
			context["authenticated"] = True
		else:
			context["authenticated"] = False
		if in_defenders(self.request.user.id):
			context["defender"] = True
		cover_photo = Photo.objects.get(id=key)
		context["photo"] = cover_photo
		usernames_and_votes = get_photo_votes(key)
		context["votes"] = usernames_and_votes
		if context["votes"]:
			context["content"] = True
			context["visible_score"] = cover_photo.visible_score 
		else:
			context["content"] = False
			context["visible_score"] = cover_photo.visible_score
		context["girls"] = FEMALES
		return context

@ratelimit(rate='3/s')
def reply_to_photo(request, pk=None, ident=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# try:
		# 	deduction = 3 * -1
		# 	request.user.userprofile.score = request.user.userprofile.score + deduction
		# 	request.user.userprofile.save()
		# 	context = {'pk': 'pk'}
		# 	return render(request, 'penalty_photocomment.html', context)
		# except:
		# 	context = {'pk': 'pk'}
		# 	return render(request, 'penalty_photocomment.html', context)
		return redirect("missing_page")
	else:
		if pk.isdigit():
			request.session["photo_id"] = pk
			request.session["related_photostream_id"] = ident
			return redirect("reply_options")
		else:
			return redirect("profile", request.user.username )

class PhotoReplyView(FormView):
	form_class = PhotoReplyForm
	template_name = "photo_reply.html"

	def get_context_data(self, **kwargs):
		context = super(PhotoReplyView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			try:
				pk = self.request.session["photo_id"]
				if pk:
					context["photo"] = Photo.objects.get(id=pk)
					context["stream_related_id"] = self.request.session["related_photostream_id"]
					context["count"] = PhotoComment.objects.filter(which_photo= pk).count()
					context["comments"] = PhotoComment.objects.filter(which_photo= pk)
					context["authenticated"] = True
				else:
					context["photo"] = None
					context["authenticated"] = False
					context["comments"] = None
					context["count"] = None
			except:
				context["photo"] = None
				context["authenticated"] = False
				context["comments"] = None
				context["count"] = None
			return context

	def form_valid(self, form):
		try:
			pk = self.request.session["photo_id"]
			self.request.session["photo_id"] = None
			self.request.session.modified = True
			which_photo = Photo.objects.get(id=pk)
			if self.request.user_banned:
				return redirect("best_photo")
			else:
				if self.request.method == 'POST':
					option = self.request.POST.get("option")
					if option == 'Photo lagao':
						return redirect("upload_photo_reply_pk", pk)
					else:
						return redirect("comment_pk", pk)
				else:
					return redirect("best_photo")
		except:
			return redirect("best_photo")

@ratelimit(rate='3/s')
def comment_profile_pk(request, pk=None, user_id=None, from_photos=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# try:
		# 	deduction = 3 * -1
		# 	request.user.userprofile.score = request.user.userprofile.score + deduction
		# 	request.user.userprofile.save()
		# 	context = {'pk': 'pk'}
		# 	return render(request, 'penalty_commentpk.html', context)
		# except:
		# 	context = {'pk': 'pk'}
		# 	return render(request, 'penalty_commentpk.html', context)
		return redirect("missing_page")
	else:
		if pk and user_id and from_photos:
			request.session["photo_id"] = pk
			request.session["star_user_id"] = user_id
			return redirect("comment", pk=pk,origin=from_photos)
		else:
			return redirect("best_photo")

@ratelimit(rate='3/s')
def videocomment_pk(request, pk=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# try:
		# 	deduction = 3 * -1
		# 	request.user.userprofile.score = request.user.userprofile.score + deduction
		# 	request.user.userprofile.save()
		# 	context = {'pk': 'pk'}
		# 	return render(request, 'penalty_videocommentpk.html', context)
		# except:
		# 	context = {'pk': '10'}
		# 	return render(request, 'penalty_videocommentpk.html', context)
		return redirect("missing_page")
	else:
		if pk.isdigit():
			request.session["video_pk"] = pk
			return redirect("video_comment")
		else:
			return redirect("home")

class VideoCommentView(CreateView):
	model = VideoComment
	form_class = VideoCommentForm
	template_name = "video_comments.html"

	def get_context_data(self, **kwargs):
		context = super(VideoCommentView, self).get_context_data(**kwargs)
		context["verified"] = FEMALES
		on_fbs = self.request.META.get('HTTP_X_IORG_FBS',False)
		# try:
		# 	on_fbs = self.request.META.get('X-IORG-FBS')
		# except:
		# 	on_fbs = False
		if on_fbs:
			context["on_fbs"] = True
		else:
			context["on_fbs"] = False
		try:
			pk = self.request.session["video_pk"]
			video = Video.objects.select_related('owner').get(id=pk)
			context["video"] = video
			comms = VideoComment.objects.select_related('submitted_by__userprofile').filter(which_video_id=pk)
			context["count"] = comms.count()
			comments = comms.order_by('-id')[:25]
			context["comments"] = comments
		except:
			context["video"] = None
		return context

	def form_valid(self, form):
		if self.request.user.is_authenticated():
			f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
			user = self.request.user
			text = self.request.POST.get("text")
			try:
				pk = self.request.session["video_pk"]
				self.request.session["video_pk"] = None
				self.request.session.modified = True
				which_video = Video.objects.get(id=pk)
			except:
				user.userprofile.score = user.userprofile.score - 3
				user.userprofile.save()
				return redirect("profile", slug=user.username)
			if self.request.user_banned:
				return redirect("see_video")
			else:
				exists = VideoComment.objects.filter(which_video=which_video, submitted_by=user).exists()
				comments = which_video.comment_count + 1
				if self.request.is_feature_phone:
					device = '1'
				elif self.request.is_phone:
					device = '2'
				elif self.request.is_tablet:
					device = '4'
				elif self.request.is_mobile:
					device = '5'
				else:
					device = '3'
				videocomment = VideoComment.objects.create(submitted_by=user, which_video=which_video, text=text,device=device)
				time = videocomment.submitted_on
				timestring = time.isoformat()
				video_tasks.delay(self.request.user.id, pk, timestring, videocomment.id, comments, text, exists)
				try:
					return redirect("videocomment_pk", pk=pk)
				except:
					return redirect("profile", slug=user.username)
		else:
			context = {'pk': 'pk'}
			return render(self.request, 'auth_commentpk.html', context)

@ratelimit(rate='3/s')
def comment_chat_pk(request, pk=None, ident=None,*args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# try:
		# 	deduction = 3 * -1
		# 	request.user.userprofile.score = request.user.userprofile.score + deduction
		# 	request.user.userprofile.save()
		# 	context = {'pk': 'pk'}
		# 	return render(request, 'penalty_commentpk.html', context)
		# except:
		# 	context = {'pk': 'pk'}
		# 	return render(request, 'penalty_commentpk.html', context)
		return redirect("missing_page")
	else:
		try:
			request.session["first_time"] = True
			return redirect("comment_pk",pk,'6',ident)
		except:
			return redirect("best_photo")

@ratelimit(rate='3/s')
def comment_pk(request, pk=None, origin=None, ident=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# try:
		# 	deduction = 3 * -1
		# 	request.user.userprofile.score = request.user.userprofile.score + deduction
		# 	request.user.userprofile.save()
		# 	context = {'pk': 'pk'}
		# 	return render(request, 'penalty_commentpk.html', context)
		# except:
		# 	context = {'pk': '10'}
		# 	return render(request, 'penalty_commentpk.html', context)
		return redirect("missing_page")
	else:
		request.session["photo_id"] = pk
		if ident:
			request.session["user_ident"] = ident
		else:
			request.session["user_ident"] = None
		if origin:
			return redirect("comment", pk=pk,origin=origin)
		else:
			return redirect("comment", pk=pk)
	
class CommentView(CreateView):
	model = PhotoComment
	form_class = CommentForm
	template_name = "comments.html"

	def get_form_kwargs( self ):
		kwargs = super(CommentView,self).get_form_kwargs()
		kwargs['user_id'] = self.request.user.id
		kwargs['photo_id'] = self.kwargs['pk']
		return kwargs

	def get_context_data(self, **kwargs):
		context = super(CommentView, self).get_context_data(**kwargs)
		if self.request.is_feature_phone:
			context["feature_phone"] = True
		else:
			context["feature_phone"] = False
		pk = self.kwargs.get('pk',None)
		try:
			photo = Photo.objects.select_related('owner').get(id=pk)
		except Photo.DoesNotExist:
			context["authorized"] = False
			context["photo"] = None
			context["count"] = None
			return context
		secret_key = uuid.uuid4()
		set_text_input_key(self.request.user.id, pk, 'pht_comm', secret_key)
		context["sk"] = secret_key
		context["photo"] = photo
		comms = PhotoComment.objects.select_related('submitted_by__userprofile').filter(which_photo_id=pk)
		context["count"] = comms.count()
		comments = comms.order_by('-id')[:25]
		context["comments"] = comments
		context["thumbs"] = retrieve_single_thumbs(photo.owner.username)
		context["verified"] = FEMALES
		context["random"] = random.sample(xrange(1,188),15) #select 15 random emoticons out of 188
		context["authorized"] = True
		origin=self.kwargs.get("origin",None)
		if origin == '1':
			context["origin"] = '1'
			context["photo_id"] = pk
		elif origin == '2':
			context["origin"] = '2'
			context["photo_id"] = pk
		elif origin == '3':
			context["origin"] = '3'
			star_user_id = self.request.session.get("user_ident",None)
			try:
				username = User.objects.get(id=star_user_id).username
				context["username"] = username
			except User.DoesNotExist:
				context["origin"] = '1'
		elif origin == '5':
			context["origin"] = '5'
			context["photo_id"] = pk
		elif origin == '6':
			context["origin"] = '6'
			link_ident = self.request.session.get("user_ident",None) #mislabled - actually contains link_id
			if link_ident:
				#if originating from a specific link
				context["link_ident"] = link_ident
				self.request.session['target_id'] = link_ident
			else:
				#if originating from a notification
				self.request.session['target_id'] = None
			self.request.session.modified = True
		else:
			context["origin"] = '1'
		try:
			is_first = self.request.session["first_time"]
			self.request.session["first_time"] = False
			self.request.session.modified = True
			context["is_first"] = is_first
		except KeyError:
			context["is_first"] = False
		if self.request.user.is_authenticated():
			context["authenticated"] = True
			try:
				if origin == '4':
					#i.e. user originiated from unseen_activity
					context["origin"] = '4'
					star_user_id = self.request.session["user_ident"]
					context["slug_id"] = star_user_id
					username = User.objects.get(id=star_user_id).username
					context["username"] = username
				else:
					pass
			except:
				context["origin"] = '1'
			updated = update_notification(viewer_id=self.request.user.id, object_id=pk,object_type='0',seen=True,\
					updated_at=time.time(),single_notif=False, unseen_activity=True,priority='photo_tabsra',\
					bump_ua=False,no_comment=True)
			if comments:
				if updated:
					context["unseen"] = True
					try:
						#finding latest time user herself commented
						context["comment_time"] = max(comment.submitted_on for comment in comments if comment.submitted_by == self.request.user)
					except ValueError:
						context["comment_time"] = None #i.e. it's the first every comment
				else:
					context["unseen"] = False
					context["comment_time"] = None
			else:
				context["unseen"] = False
				context["comment_time"] = None
		else:
			context["authenticated"] = False
		return context


	def form_valid(self, form):
		if self.request.user.is_authenticated():
			user = self.request.user
			pk = self.kwargs.get('pk',None)
			photo_owner_id = self.request.POST.get("popk",None)
			banned_by, ban_time = is_already_banned(own_id=user.id,target_id=photo_owner_id, return_banner=True)
			if banned_by:
				self.request.session["banned_by"] = banned_by
				self.request.session["ban_time"] = ban_time
				self.request.session["where_from"] = 'best_photos'
				self.request.session.modified = True
				return redirect("ban_underway")
			elif self.request.user_banned:
				return render(self.request,'500.html',{}) #errorbanning
			f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
			text = f.text#self.request.POST.get("text")
			origin = self.request.POST.get("origin")
			star_user_id = None
			link_id = None
			try:
				# pk = self.request.session["photo_id"]
				# self.request.session["photo_id"] = None
				# self.request.session.modified = True
				which_photo = Photo.objects.get(id=pk)
				if which_photo.owner_id != int(photo_owner_id):
					self.request.session["where_from"] = 'best_photos'
					return redirect("ban_underway")
			except Photo.DoesNotExist:
				return redirect("best_photos")
			set_input_rate_and_history.delay(section='pht_comm',section_id=pk,text=text,user_id=user.id,time_now=time.time())
			if origin == '3' or origin == '4':
				try:
					star_user_id = self.request.session["user_ident"]
					self.request.session["user_ident"] = None
					self.request.session.modified = True
				except KeyError:
					star_user_id = None
			elif origin == '6':
				link_id = self.request.session["user_ident"]
				self.request.session["user_ident"] = None
				self.request.session["target_id"] = link_id	
				self.request.session.modified = True			
			exists = PhotoComment.objects.filter(which_photo=which_photo, submitted_by=user).exists()
			update_cc_in_home_photo(which_photo.id)
			if self.request.is_feature_phone:
				device = '1'
			elif self.request.is_phone:
				device = '2'
			elif self.request.is_tablet:
				device = '4'
			elif self.request.is_mobile:
				device = '5'
			else:
				device = '3'
			photocomment = PhotoComment.objects.create(submitted_by=user, which_photo=which_photo, text=text,device=device)
			comment_time = convert_to_epoch(photocomment.submitted_on)
			try:
				url = user.userprofile.avatar.url
			except ValueError:
				url = None
			citizen = self.request.mobile_verified
			add_photo_comment(photo_id=pk,photo_owner_id=photo_owner_id,latest_comm_text=text,latest_comm_writer_id=user.id,\
				latest_comm_av_url=url,latest_comm_writer_uname=user.username, exists=exists, citizen = citizen, time=comment_time)
			photo_tasks.delay(user.id, pk, comment_time, photocomment.id, which_photo.comment_count, text, \
				exists, user.username, url, citizen)
			if user.id != photo_owner_id:
				home_photo_tasks.delay(text=text, replier_id=user.id, time=comment_time, photo_owner_id=photo_owner_id,photo_id=pk)
			if pk and origin and link_id:
				return redirect("comment_pk",pk=pk,origin=origin, ident=link_id)
			elif pk and origin and star_user_id:
				return redirect("comment_pk",pk=pk,origin=origin, ident=star_user_id)
			elif pk and origin:
				return redirect("comment_pk",pk=pk,origin=origin)
			elif pk:
				#fires if user from chat
				return redirect("comment_pk", pk=pk)
			else:
				return redirect("best_photo")
		else:
			context = {'pk': 'pk'}
			return render(self.request, 'auth_commentpk.html', context)

@ratelimit(rate='3/s')
def see_special_photo_pk(request,pk=None,*args,**kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# try:
		# 	deduction = 3 * -1
		# 	request.user.userprofile.score = request.user.userprofile.score + deduction
		# 	request.user.userprofile.save()
		# 	context = {'pk': 'pk'}
		# 	return render(request, 'penalty_special.html', context)
		# except:
		# 	context = {'pk': '10'}
		# 	return render(request, 'penalty_special.html', context)
		return redirect("missing_page")
	else:
		if pk.isdigit():
			request.session["target_special_photo_id"] = pk
			return redirect("see_special_photo")
		else:
			return redirect("see_special_photo")

@ratelimit(rate='3/s')
def special_photo(request, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# try:
		# 	deduction = 3 * -1
		# 	request.user.userprofile.score = request.user.userprofile.score + deduction
		# 	request.user.userprofile.save()
		# 	context = {'pk': 'pk'}
		# 	return render(request, 'penalty_special.html', context)
		# except:
		# 	context = {'pk': '10'}
		# 	return render(request, 'penalty_special.html', context)
		return redirect("missing_page")
	else:
		if request.user.is_authenticated() and request.user.userprofile.score > 29:
			try:
				seen_special_photo_option = TutorialFlag.objects.get(user=request.user).seen_special_photo_option
				if seen_special_photo_option:
					request.session["ftue_special_photo_option"] = False
					return redirect("see_special_photo")
				else:
					request.session["ftue_special_photo_option"] = True
					return redirect("special_photo_tutorial")
			except:
				TutorialFlag.objects.create(user=request.user)
				request.session["ftue_special_photo_option"] = True
				return redirect("special_photo_tutorial")
		else:
			return redirect("see_special_photo")

class SpecialPhotoTutorialView(FormView):
	form_class = SpecialPhotoTutorialForm
	template_name = "special_photo_tutorial.html"

	def form_valid(self, form):
		if self.request.method == 'POST':
			try:
				choice = self.request.POST.get("choice")
				if choice == 'samajh gaya':
					flag = TutorialFlag.objects.filter(user=self.request.user).update(seen_special_photo_option=True)
					self.request.session["ftue_special_photo_option"] = None
					self.request.session.modified = True
					return redirect("see_special_photo")
				else:
					return redirect("best_photo")
			except:
				TutorialFlag.objects.filter(user=self.request.user).update(seen_special_photo_option=True)
				return redirect("see_special_photo")
		else:
			TutorialFlag.objects.filter(user=self.request.user).update(seen_special_photo_option=True)
			return redirect("see_special_photo")


class SpecialPhotoView(ListView):
	model = Photo
	template_name = "special_photos.html"
	paginate_by = 10 #i.e. 10 pages in total with a query-set of 200 objects

	def get_queryset(self):
		if self.request.is_feature_phone:
			queryset = Photo.objects.select_related('owner__userprofile', 'cover__latest_comment__submitted_by', 'second_latest_comment__submitted_by').filter(category='7').order_by('-id')[:200]
		else:
			queryset = Photo.objects.select_related('owner__userprofile', 'cover__latest_comment__submitted_by', 'second_latest_comment__submitted_by').filter(category='7').order_by('-id')[:200]
		return queryset

	def get_context_data(self, **kwargs):
		context = super(SpecialPhotoView, self).get_context_data(**kwargs)
		context["girls"] = FEMALES
		context["authenticated"] = False
		context["can_vote"] = False
		context["score"] = None
		if self.request.user.is_authenticated():
			context["authenticated"] = True
			user = self.request.user
			context["score"] = user.userprofile.score
			context["voted"] = []
			if not self.request.user_banned:
				if self.request.user.userprofile.score > 9:
					context["can_vote"] = True
				else:
					context["can_vote"] = False
				photos_in_page = [photo.id for photo in context["object_list"]]
				vote_cluster = PhotoVote.objects.filter(photo_id__in=photos_in_page)
				context["voted"] = vote_cluster.filter(voter=user).values_list('photo_id', flat=True)
				object_type, freshest_reply, is_link, is_photo, is_groupreply, is_salat = GetLatest(user)
				if not is_link and not is_photo and not is_groupreply and not is_salat:
					context["freshest_unseen_comment"] = []
					context["notification"] = 0
					context["parent"] = []
					context["parent_pk"] = 0
					context["first_time_user"] = False
					context["banned"] = False
					return context
				elif not freshest_reply:
					context["freshest_unseen_comment"] = []
					context["notification"] = 0
					context["parent"] = []
					context["parent_pk"] = 0
					context["first_time_user"] = False
					context["banned"] = False
					return context
				elif is_salat:
					cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
						'LOCATION': MEMLOC, 'TIMEOUT': 70,
					})
					salat_timings = cache_mem.get('salat_timings')
					salat_invite = freshest_reply
					context["type_of_object"] = '4'
					context["notification"] = 1
					context["first_time_user"] = False
					context["banned"] = False
					context["parent"] = salat_invite
					context["namaz"] = salat_timings['namaz'] 
					context["freshest_unseen_comment"] = 1				
				elif is_photo:
					if object_type == '1':
						#i.e. it's a photo a fan ought to see!
						photo = Photo.objects.get(id=freshest_reply)
						context["freshest_unseen_comment"] = None
						context["type_of_object"] = '1'
						context["notification"] = 1
						context["parent"] = photo
						context["parent_pk"] = freshest_reply
						context["first_time_user"] = False
						context["banned"] = False
					elif object_type == '0':
						context["freshest_unseen_comment"] = freshest_reply
						context["type_of_object"] = '0'
						context["notification"] = 1
						context["parent"] = freshest_reply.which_photo
						context["parent_pk"] = freshest_reply.which_photo_id
						# context["photostream_id"]=PhotoStream.objects.get(cover_id=context["parent_pk"]).id
						context["first_time_user"] = False
						context["banned"] = False
					else:
						context["freshest_unseen_comment"] = []
						context["notification"] = 0
						context["parent"] = []
						context["parent_pk"] = 0
						context["first_time_user"] = False
						context["banned"] = False
					return context
				elif is_link:
					context["type_of_object"] = '2'
					context["banned"] = False
					if freshest_reply:
						parent_link = freshest_reply.answer_to
						parent_link_writer = parent_link.submitter
						parent_link_writer_username = parent_link_writer.username
						WELCOME_MESSAGE1 = parent_link_writer_username+" welcum damadam pe! Kiya hal hai? Barfi khao aur mazay urao (barfi)"
						WELCOME_MESSAGE2 = parent_link_writer_username+" welcome! Kesey ho? Yeh zalim barfi try kar yar (barfi)"
						WELCOME_MESSAGE3 = parent_link_writer_username+" assalam-u-alaikum! Is barfi se mu meetha karo (barfi)"
						WELCOME_MESSAGE4 = parent_link_writer_username+" Damadam pe welcome! One plate laddu se life set (laddu)"
						WELCOME_MESSAGE5 = parent_link_writer_username+" kya haal he? Ye laddu aap ke liye (laddu)"
						WELCOME_MESSAGE6 = parent_link_writer_username+" welcum! Life set hei? Laddu khao, jaan banao (laddu)"
						WELCOME_MESSAGE7 = parent_link_writer_username+" welcomeee! Yar kya hal he? Jalebi khao aur ayashi karo (jalebi)"
						WELCOME_MESSAGE8 = parent_link_writer_username+" kaisey ho? Jalebi meri pasandida hai! Tumhari bhi? (jalebi)"
						WELCOME_MESSAGE9 = parent_link_writer_username+" salam! Is jalebi se mu meetha karo (jalebi)"
						WELCOME_MESSAGES = [WELCOME_MESSAGE1, WELCOME_MESSAGE2, WELCOME_MESSAGE3, WELCOME_MESSAGE4, WELCOME_MESSAGE5,\
						WELCOME_MESSAGE6, WELCOME_MESSAGE7, WELCOME_MESSAGE8, WELCOME_MESSAGE9]
					else:
						parent_link_writer = User()
						#parent_link.submitter = 0
						WELCOME_MESSAGES = []
					try:
						context["freshest_unseen_comment"] = freshest_reply
						context["notification"] = 1
						context["parent"] = parent_link
						context["parent_pk"] = parent_link.pk
						if user==parent_link_writer and any(freshest_reply.description in s for s in WELCOME_MESSAGES):
							context["first_time_user"] = True
						else:
							context["first_time_user"] = False
					except:
						context["freshest_unseen_comment"] = []
						context["notification"] = 0
						context["parent"] = []
						context["parent_pk"] = 0
						context["first_time_user"] = False
					return context
				elif is_groupreply:
					context["freshest_unseen_comment"] = []
					context["notification"] = 0
					context["type_of_object"] = '1'
					context["parent"] = []
					context["parent_pk"] = 0
					context["first_time_user"] = False
					context["banned"] = False
					return context
				else:
					context["freshest_unseen_comment"] = []
					context["notification"] = 0
					context["parent"] = []
					context["parent_pk"] = 0
					context["banned"] = False
					context["first_time_user"] = False
					return context
			else:
				context["notification"] = 0
				context["banned"] = True
				context["can_vote"] = False
				context["first_time_user"] = False
				context["type_of_object"] = None
				context["freshest_unseen_comment"] = []
				context["parent"] = []
				context["parent_pk"] = 0
				return context
		return context

	def get(self, request, *args, **kwargs):
		self.object_list = self.get_queryset()
		allow_empty = self.get_allow_empty()
		if not allow_empty:
			# When pagination is enabled and object_list is a queryset,
			# it's better to do a cheap query than to load the unpaginated
			# queryset in memory.
			if (self.get_paginate_by(self.object_list) is not None
				and hasattr(self.object_list, 'exists')):
				is_empty = not self.object_list.exists()
			else:
				is_empty = len(self.object_list) == 0
			if is_empty:
				raise Http404(_("Empty list and '%(class_name)s.allow_empty' is False.")
						% {'class_name': self.__class__.__name__})
		context = self.get_context_data(object_list=self.object_list)
		try:
			target_id = self.request.session["target_special_photo_id"]
			self.request.session["target_special_photo_id"] = None
			self.request.session.modified = True
		except:
			target_id = None
		if target_id:
			try:
				index = list(photo.id for photo in self.object_list).index(int(target_id))
			except:
				index = None
			if 0 <= index <= 9:
				addendum = '#section'+str(index+1)
			elif 10 <= index <= 19:
				addendum = '?page=2#section'+str(index+1-10)
			elif 20 <= index <= 29:
				addendum = '?page=3#section'+str(index+1-20)
			elif 30 <= index <= 39:
				addendum = '?page=4#section'+str(index+1-30)
			elif 40 <= index <= 49:
				addendum = '?page=5#section'+str(index+1-40)
			elif 50 <= index <= 59:
				addendum = '?page=6#section'+str(index+1-50)
			elif 60 <= index <= 69:
				addendum = '?page=7#section'+str(index+1-60)
			elif 70 <= index <= 79:
				addendum = '?page=8#section'+str(index+1-70)
			elif 80 <= index <= 89:
				addendum = '?page=9#section'+str(index+1-80)
			elif 90 <= index <= 99:
				addendum = '?page=10#section'+str(index+1-90)
			elif 100 <= index <= 109:
				addendum = '?page=11#section'+str(index+1-100)
			elif 110 <= index <= 119:
				addendum = '?page=12#section'+str(index+1-110)
			elif 120 <= index <= 129:
				addendum = '?page=13#section'+str(index+1-120)
			elif 130 <= index <= 139:
				addendum = '?page=14#section'+str(index+1-130)
			elif 140 <= index <= 149:
				addendum = '?page=15#section'+str(index+1-140)
			elif 150 <= index <= 159:
				addendum = '?page=16#section'+str(index+1-150)
			elif 160 <= index <= 169:
				addendum = '?page=17#section'+str(index+1-160)
			elif 170 <= index <= 179:
				addendum = '?page=18#section'+str(index+1-170)
			elif 180 <= index <= 189:
				addendum = '?page=19#section'+str(index+1-180)
			elif 190 <= index <= 199:
				addendum = '?page=20#section'+str(index+1-190)
			else:
				addendum = '#section0'		
			return HttpResponseRedirect(addendum)
		else:
			return self.render_to_response(context)

def non_fbs_vid(request, pk=None, *args, **kwargs):
	on_fbs = self.request.META.get('HTTP_X_IORG_FBS',False)
	return redirect("https://damadam.pk/"+"123")

class VideoView(ListView):
	model = Video
	paginate_by = 10
	template_name = "videos.html"

	def get_queryset(self):
		queryset = Video.objects.select_related('owner__userprofile', 'latest_comment__submitted_by', 'second_latest_comment__submitted_by').filter(id__in=all_videos()).order_by('-id')
		return queryset

	def get_context_data(self, **kwargs):
		context = super(VideoView, self).get_context_data(**kwargs)
		context["girls"] = FEMALES
		context["authenticated"] = False
		context["can_vote"] = False
		context["score"] = None
		on_fbs = self.request.META.get('HTTP_X_IORG_FBS',False)
		if on_fbs:
			context["on_fbs"] = True
		else:
			context["on_fbs"] = True
		if self.request.user.is_authenticated():
			context["authenticated"] = True
			user = self.request.user
			context["score"] = user.userprofile.score
			context["voted"] = []
			if not self.request.user_banned:
				if self.request.user.userprofile.score > 9:
					context["can_vote"] = True
				else:
					context["can_vote"] = False
				context["voted"] = voted_for_video(context["object_list"], user.username)
		return context

#########################Views for fresh photos#########################

@csrf_protect
@ratelimit(rate='3/s')
# @ratelimit(field='user_id',ip=False,rate='22/38s')
def photo_comment(request,pk=None,*args,**kwargs):
	if request.method == 'POST':
		was_limited = getattr(request, 'limits', False)
		if was_limited:
			return redirect("missing_page")
		link_id = request.POST.get("lid",None)
		user_id = request.user.id
		origin = request.POST.get("origin",None)
		photo_owner_id = request.POST.get("popk",None)
		banned_by, ban_time = is_already_banned(own_id=user_id,target_id=photo_owner_id, return_banner=True)
		if banned_by:
			request.session["banned_by"] = banned_by
			request.session["ban_time"] = ban_time
			if origin == '1':
				request.session["where_from"] = 'photos'
			elif origin == '2':
				request.session["where_from"] = 'best_photos'
			elif origin == '3':
				request.session["where_from"] = 'home'
			request.session.modified = True
			return redirect("ban_underway")
		# elif was_limited:
		# 	context = {'penalty':300}
		# 	UserProfile.objects.filter(user=request.user).update(score=F('score')-300) #punish the spammer
		# 	return render(request, 'penalty_photo_comment.html', context)
		else:
			form = PhotoCommentForm(data=request.POST,user_id=user_id,photo_id=pk)
			origin = request.POST.get("origin",None)
			lang = request.POST.get("lang",None)
			sort_by = request.POST.get("sort_by",None)
			# ipp = MAX_ITEMS_PER_PAGE if lang == 'urdu' else ITEMS_PER_PAGE
			if form.is_valid():
				photo = Photo.objects.filter(id=pk).values('owner','comment_count')[0]
				if photo['owner'] != int(photo_owner_id):
					request.session["where_from"] = 'best_photos'
					return redirect("ban_underway")
				description = form.cleaned_data.get("photo_comment")
				set_input_rate_and_history.delay(section='pht_comm',section_id=pk,text=description,user_id=user_id,time_now=time.time())
				if request.is_feature_phone:
					device = '1'
				elif request.is_phone:
					device = '2'
				elif request.is_tablet:
					device = '4'
				elif request.is_mobile:
					device = '5'
				else:
					device = '3'
				exists = PhotoComment.objects.filter(which_photo_id=pk, submitted_by=request.user).exists() #i.e. user commented before
				photocomment = PhotoComment.objects.create(submitted_by=request.user, which_photo_id=pk, text=description,device=device)
				update_cc_in_home_photo(pk)
				comment_time = convert_to_epoch(photocomment.submitted_on)
				try:
					url = request.user.userprofile.avatar.url
				except ValueError:
					url = None
				citizen = request.mobile_verified
				add_photo_comment(photo_id=pk,photo_owner_id=photo["owner"],latest_comm_text=description,latest_comm_writer_id=user_id,\
					latest_comm_av_url=url,latest_comm_writer_uname=request.user.username, exists=exists, citizen = citizen,time=comment_time)
				unseen_comment_tasks.delay(user_id, pk, comment_time, photocomment.id, photo["comment_count"], description, exists, \
					request.user.username, url, citizen)
				##############################################################################################
				##############################################################################################
				# if origin == '1':
				# 	log_organic_attention.delay(photo_id=pk,att_giver=user_id,photo_owner_id=photo_owner_id, action='photo_comm')
				##############################################################################################
				##############################################################################################
				if user_id != photo_owner_id:
					home_photo_tasks.delay(text=description, replier_id=user_id, time=comment_time, photo_owner_id=photo_owner_id,photo_id=pk, link_id=link_id)
				if origin == '3':
					request.session["target_id"] = link_id
					request.session.modified = True
					if lang == 'urdu' and sort_by == 'best':
						return redirect("home_loc_ur_best", lang)
					elif sort_by == 'best':
						return redirect("home_loc_best")
					elif lang == 'urdu':
						return redirect("home_loc_ur", lang)
					else:
						return redirect("home_loc")
				else:
					return return_to_photo(request,origin,pk,None,None)
			else:
				request.session["comment_form"] = form
				return return_to_photo(request,origin,pk,link_id if origin == '3' else None,None)
	else:
		return redirect("home")

def see_photo_pk(request,pk=None,*args,**kwargs):
	if request.user.is_authenticated():
		if pk:
			request.session["target_photo_id"] = pk
			return redirect("photo_loc")
		else:
			return redirect("best_photo")
	else:
		return redirect("register_login")

def unauth_photo_location_pk(request,pk=None,*args,**kwargs):
	if pk:
		photo_ids = all_photos()
		try:
			index = photo_ids.index(pk)
		except:
			index = 0
		page_num, addendum = get_addendum(index,PHOTOS_PER_PAGE)
		url = reverse_lazy("unauth_photo")+addendum
		page_obj = get_page_obj(page_num,photo_ids,PHOTOS_PER_PAGE)
		request.session['unauth_photos'] = retrieve_photo_posts(page_obj.object_list)
		request.session['unauth_photo_page'] = page_obj
		return redirect(url)
	else:
		return redirect("unauth_photo")

def photo_location(request,*args,**kwargs):
	photo_id = request.session.pop('target_photo_id',0)
	photo_ids = all_photos()
	if photo_id == 0:
		# there is no indexing to be done, just return to the top of the page
		page_num = request.GET.get('page', '1')
		page_obj = get_page_obj(page_num,photo_ids,PHOTOS_PER_PAGE)
		request.session['photos'] = retrieve_photo_posts(page_obj.object_list)
		request.session['photo_page'] = page_obj
		return redirect("photo")
	else:
		# have to return user to a specific anchor
		try:
			index = photo_ids.index(photo_id)
		except:
			index = 0
		page_num, addendum = get_addendum(index,PHOTOS_PER_PAGE)
		url = reverse_lazy("photo")+addendum
		page_obj = get_page_obj(page_num,photo_ids,PHOTOS_PER_PAGE)
		request.session['photos'] = retrieve_photo_posts(page_obj.object_list)
		request.session['photo_page'] = page_obj
		return redirect(url)

@cache_page(15)
@csrf_protect
def unauth_photos(request,*args,**kwargs):
	if request.user.is_authenticated():
		return redirect("photo")
	else:
		context = {}
		form = PhotosListForm()
		# newrelic.agent.add_custom_parameter("unauth_new photos", request.META.get('X-IORG-FBS-UIP',request.META.get('REMOTE_ADDR')))
		if 'unauth_photos' in request.session and 'unauth_photo_page' in request.session:
			if request.session['unauth_photos'] and request.session['unauth_photo_page']:
				# called when user has redirect from a photo comment
				context["object_list"] = request.session['unauth_photos']
				context["page"] = request.session['unauth_photo_page']
			else:
				photo_ids = all_photos()
				page_num = request.GET.get('page', '1')
				page_obj = get_page_obj(page_num,photo_ids,PHOTOS_PER_PAGE)
				context["page"] = page_obj
				context["object_list"] = retrieve_photo_posts(page_obj.object_list)
			del request.session['unauth_photos']
			del request.session['unauth_photo_page']
		else:
			photo_ids = all_photos()
			page_num = request.GET.get('page', '1')
			page_obj = get_page_obj(page_num,photo_ids,PHOTOS_PER_PAGE)
			context["page"] = page_obj
			context["object_list"] = retrieve_photo_posts(page_obj.object_list)
		new_id = request.session.get('new_id',None)
		if not new_id:
			new_id = get_temp_id()
			request.session['new_id'] = new_id
		# mp.track(new_id, 'on_photos')
		form = CreateNickNewForm()
		context["form"] = form
		return render(request,'unauth_photos.html',context)

def photo_list(request,*args, **kwargs):
	if request.user.is_authenticated():
		# newrelic.agent.add_custom_parameter("auth_new photos", request.META.get('X-IORG-FBS-UIP',request.META.get('REMOTE_ADDR')))
		if first_time_photo_uploader(request.user.id) and request.user.userprofile.score > UPLOAD_PHOTO_REQ:
			add_photo_uploader(request.user.id)
			return render(request, 'photo_uploader_tutorial.html', {})
		else:
			context = {}
			form = PhotosListForm()
			if 'photos' in request.session and 'photo_page' in request.session:
				if request.session['photos'] and request.session['photo_page']:
					context["page"] = request.session['photo_page']
					context["object_list"] = request.session['photos']
				else:
					photo_ids = all_photos()
					page_num = request.GET.get('page', '1')
					page_obj = get_page_obj(page_num,photo_ids,PHOTOS_PER_PAGE)
					context["page"] = page_obj
					context["object_list"] = retrieve_photo_posts(page_obj.object_list)
				del request.session['photo_page']
				del request.session['photos']
			else:
				photo_ids = all_photos()
				page_num = request.GET.get('page', '1')
				page_obj = get_page_obj(page_num,photo_ids,PHOTOS_PER_PAGE)
				context["page"] = page_obj
				context["object_list"] = retrieve_photo_posts(page_obj.object_list)
			user = request.user
			context["threshold"] = UPLOAD_PHOTO_REQ
			context["username"] = request.user.username
			context["score"] = user.userprofile.score
			context["voted"] = []
			context["csrf"] = csrf.get_token(request)
			context["girls"] = FEMALES
			context["mobile_verified"] = request.mobile_verified
			secret_key = uuid.uuid4()
			context["sk"] = secret_key
			set_text_input_key(user.id, '1', 'fresh_photos', secret_key)
			############################################# Home Rules #################################################
			context["home_rules"] = spammer_punishment_text(user.id)
			##########################################################################################################
			context["lang"] = None
			context["sort_by"] = None
			if request.is_feature_phone or request.is_phone or request.is_mobile:
				context["is_mob"] = True
			if "comment_form" in request.session:
				context["comment_form"] = request.session["comment_form"]
				request.session.pop("comment_form", None)
			else:
				context["comment_form"] = PhotoCommentForm()
			if request.user_banned:
				context["process_notification"] = False
			else:
				if context["score"] > 9:
					context["can_vote"] = True
				else:
					context["can_vote"] = False
				context["voted"] = voted_for_photo(context["object_list"],context["username"])
				photo_owners = set([photo['oi'] for photo in context["object_list"]])
				context["fanned"] = list(UserFan.objects.filter(star_id__in=photo_owners,fan=user).values_list('star_id',flat=True))
				cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
				'LOCATION': MEMLOC, 'TIMEOUT': 70,})
				context["salat_timings"] = cache_mem.get('salat_timings')
				if "notif_form" in request.session:
					context["notif_form"] = request.session["notif_form"]
					request.session.pop("notif_form", None)
				else:
					context["notif_form"] = UnseenActivityForm()
				context["process_notification"] = True

			return render(request,'photos.html',context)
	else:
		return redirect("unauth_home_new")

#########################Views for best photos#########################

def unauth_best_photo_location_pk(request,pk=None, *args,**kwargs):
	if pk:
		obj_list = all_best_photos()
		obj_list_keys = map(itemgetter(0), obj_list)
		try:
			index = obj_list_keys.index(pk)
		except:
			index = 0
		page_num, addendum = get_addendum(index,PHOTOS_PER_PAGE)
		url = reverse_lazy("unauth_best_photo")+addendum
		page_obj = get_page_obj(page_num,obj_list_keys,PHOTOS_PER_PAGE)
		request.session['unauth_best_photos'] = retrieve_photo_posts(page_obj.object_list)
		request.session['unauth_best_photo_page'] = page_obj
		return redirect(url)
	else:
		return redirect("unauth_best_photo")

def best_photo_location(request, *args, **kwargs):
	try:
		photo_id = request.session['target_best_photo_id']
		del request.session['target_best_photo_id']
	except:
		photo_id = 0
	obj_list = all_best_photos()
	obj_list_keys = map(itemgetter(0), obj_list)
	if photo_id == 0:
		# there is no index, just return to the top of the page
		page_num = request.GET.get('page', '1')
		page_obj = get_page_obj(page_num,obj_list_keys,PHOTOS_PER_PAGE)
		photos = retrieve_photo_posts(page_obj.object_list)
		request.session['best_photos'] = photos
		request.session['best_photo_page'] = page_obj
		request.session.modified = True
		# cache.set('best_photos'+str(page_num), photos, timeout=5*60)
		# cache.set('best_photos_page_obj'+str(page_num), page_obj, timeout=5*60)
		return redirect("best_photo")
	else:
		try:
			index = obj_list_keys.index(photo_id)
		except:
			index = 0
		page_num, addendum = get_addendum(index,PHOTOS_PER_PAGE)
		url = reverse_lazy("best_photo")+addendum
		page_obj = get_page_obj(page_num,obj_list_keys,PHOTOS_PER_PAGE)
		photos = retrieve_photo_posts(page_obj.object_list)
		request.session['best_photos'] = photos
		request.session['best_photo_page'] = page_obj
		request.session.modified = True
		# cache.set('best_photos'+str(page_num), photos, timeout=5*60)
		# cache.set('best_photos_page_obj'+str(page_num), page_obj, timeout=5*60)
		return redirect(url)

@cache_page(60)
@csrf_protect
def unauth_best_photos(request,*args,**kwargs):
	if request.user.is_authenticated():
		return redirect("best_photo")
	else:
		context = {}
		form = BestPhotosListForm()
		if 'unauth_best_photos' in request.session and 'unauth_best_photo_page' in request.session:
			if request.session['unauth_best_photos'] and request.session['unauth_best_photo_page']:
				# called when user has redirect from a photo comment
				context["object_list"] = request.session['unauth_best_photos']
				context["page"] = request.session['unauth_best_photo_page']
			else:
				obj_list = all_best_photos()
				obj_list_keys = map(itemgetter(0), obj_list)
				page_num = request.GET.get('page', '1')
				page_obj = get_page_obj(page_num,obj_list_keys,PHOTOS_PER_PAGE)
				context["page"] = page_obj
				context["object_list"] = retrieve_photo_posts(page_obj.object_list)
			del request.session['unauth_best_photos']
			del request.session['unauth_best_photo_page']
		else:
			obj_list = all_best_photos()
			obj_list_keys = map(itemgetter(0), obj_list)
			page_num = request.GET.get('page', '1')
			page_obj = get_page_obj(page_num,obj_list_keys,PHOTOS_PER_PAGE)
			context["page"] = page_obj
			context["object_list"] = retrieve_photo_posts(page_obj.object_list)
		form = CreateNickNewForm()
		context["form"] = form
		new_id = request.session.get('new_id',None)
		if not new_id:
			new_id = get_temp_id()
			request.session['new_id'] = new_id
		# mp.track(new_id, 'on_photos')
		return render(request,'unauth_best_photos.html',context)

def best_photos_list(request,*args,**kwargs):
	user_id = request.user.id
	if request.user.is_authenticated():
		if first_time_photo_uploader(user_id) and request.user.userprofile.score > UPLOAD_PHOTO_REQ:
			add_photo_uploader(user_id)
			return render(request, 'photo_uploader_tutorial.html', {})
		else:
			context = {}
			form = BestPhotosListForm()
			if 'best_photos' in request.session and 'best_photo_page' in request.session:
				if request.session['best_photos'] and request.session['best_photo_page']:
					# "called when user has voted or commented"
					context["object_list"] = request.session['best_photos']
					context["page"] = request.session['best_photo_page']
				else:
					# "doesn't do anything"
					obj_list = all_best_photos()
					obj_list_keys = map(itemgetter(0), obj_list)
					page_num = request.GET.get('page', '1')
					page_obj = get_page_obj(page_num,obj_list_keys,PHOTOS_PER_PAGE)
					# cache.set('best_photos_page_obj'+str(page_num), page_obj, timeout=5*60)
					context["page"] = page_obj
					context["object_list"] = retrieve_photo_posts(page_obj.object_list)
					# cache.set('best_photos'+str(page_num), context["object_list"], timeout=5*60)
				del request.session['best_photos']
				del request.session['best_photo_page']
			else:
				# "normal refresh or toggling between pages"
				page_num = request.GET.get('page', '1')
				obj_list = all_best_photos()
				obj_list_keys = map(itemgetter(0), obj_list)
				page_obj = get_page_obj(page_num,obj_list_keys,PHOTOS_PER_PAGE)
				context["page"] = page_obj
				context["object_list"] = retrieve_photo_posts(page_obj.object_list)
			user = request.user
			context["threshold"] = UPLOAD_PHOTO_REQ
			context["username"] = user.username
			context["newbie_flag"] = request.session.pop("newbie_flag",None)
			context["newbie_lang"] = request.session["newbie_lang"] if "newbie_lang" in request.session else None
			context["ident"] = user_id
			context["score"] = user.userprofile.score
			context["voted"] = []
			context["girls"] = FEMALES
			context["csrf"] = csrf.get_token(request)
			context["mobile_verified"] = request.mobile_verified
			secret_key = uuid.uuid4()
			context["sk"] = secret_key
			set_text_input_key(user_id, '1', 'best_photos', secret_key)
			############################################# Home Rules #################################################
			context["home_rules"] = spammer_punishment_text(context["ident"])
			##########################################################################################################
			context["lang"] = None
			context["sort_by"] = None
			if request.is_feature_phone or request.is_phone or request.is_mobile:
				context["is_mob"] = True
			if "comment_form" in request.session:
				context["comment_form"] = request.session["comment_form"]
				request.session.pop("comment_form", None)
			else:
				context["comment_form"] = PhotoCommentForm()
			if request.user_banned:
				context["process_notification"] = False
			else:
				if context["score"] > 9:
					context["can_vote"] = True
				else:
					context["can_vote"] = False
				context["voted"] = voted_for_photo(context["object_list"],context["username"])
				photo_owners = set([photo['oi'] for photo in context["object_list"]])
				context["fanned"] = list(UserFan.objects.filter(star_id__in=photo_owners,fan=user).values_list('star_id',flat=True))
				cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
				'LOCATION': MEMLOC, 'TIMEOUT': 70,})
				context["salat_timings"] = cache_mem.get('salat_timings')
				if "notif_form" in request.session:
					context["notif_form"] = request.session["notif_form"]
					request.session.pop("notif_form", None)
				else:
					context["notif_form"] = UnseenActivityForm()
				context["process_notification"] = True
			return render(request,'best_photos.html',context)
	else:
		return redirect("unauth_home_new")

def see_best_photo_pk(request,pk=None,*args,**kwargs):
	if pk:
		request.session["target_best_photo_id"] = pk
		return redirect("best_photo_loc")
	else:
		return redirect("best_photo")

##################################################################

class UploadVideoView(FormView):
	# model = Video
	form_class = UploadVideoForm
	template_name = "upload_video.html"

	def get_context_data(self, **kwargs):
		context = super(UploadVideoView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			videos = Video.objects.filter(id__in=get_recent_videos(self.request.user.id)).order_by('-id').values_list('vote_score', 'upload_time')
			number_of_videos = videos.count()
			forbidden, time_remaining = check_video_abuse(number_of_videos, videos)
			if forbidden:
				context["score"] = None
				context["forbidden"] = True
				context["time_remaining"] = time_remaining
			else:
				context["score"] = self.request.user.userprofile.score
				context["forbidden"] = False
				context["time_remaining"] = None
		return context

	def form_valid(self, form):
		if self.request.method == 'POST':
			status, seconds_to_go = video_uploaded_too_soon(self.request.user.id)
			if status:
				m, s = divmod(seconds_to_go, 60)
				if m and s:
					context = {"time_remaining":"%s minutes and %s seconds" % (int(m), int(s))}
				elif s:
					context= {"time_remaining": "%s seconds" % int(s)}
				else:
					context= {"time_remaining": 0}
				return render(self.request,'video_uploaded_too_soon.html',context)
			else:
				videos = Video.objects.filter(id__in=get_recent_videos(self.request.user.id)).order_by('-id').values_list('vote_score', 'upload_time')
				forbidden, time_remaining = check_video_abuse(videos.count(), videos)
				if forbidden:
					context = {'time_remaining':time_remaining}
					return render(self.request,'forbidden_video.html',context)
				caption = self.request.POST.get("caption")
				video = self.request.FILES['video_file']
				if self.request.is_feature_phone:
					device = '1'
				elif self.request.is_phone:
					device = '2'
				elif self.request.is_tablet:
					device = '4'
				elif self.request.is_mobile:
					device = '5'
				else:
					device = '3'
				video = Video.objects.create(owner=self.request.user, video_file=video, device=device, comment_count=0, caption=caption)
				video_upload_tasks.delay(video.video_file.name, video.id, self.request.user.id)
				context = {'pk':'pk'}
				return render(self.request,'video_upload.html',context)

##################################################################

def public_photo_upload_denied(request):
	"""
	Helper view for upload_public_photo
	"""
	which_msg = request.session.pop("public_photo_upload_denied",None)
	if which_msg == '1':
		return render(request,"dont_click_again_and_again.html",{'from_public_photos':True,'from_ecomm':False})
	elif which_msg == '2':
		return render(request,"score_photo.html",{})
	elif which_msg in ('3','4'):
		to_go = request.session.pop("public_photo_upload_denied_time_togo",None)
		return render(request, 'forbidden_photo.html', {'time_remaining': to_go})
	elif which_msg == '5':
		to_go = request.session.pop("public_photo_upload_denied_time_togo",None)
		return render(request, 'error_photo.html', {'time':to_go})
	elif which_msg == '6':
		return render(request,'big_photo_fbs.html',{'pk':'pk'})
	elif which_msg == '7':
		return render(request,'big_photo_regular.html',{'pk':'pk'})
	elif which_msg == '8':
		pk = request.session.pop("public_photo_upload_denied_photo_pk",None)
		if pk:
			try:
				photo = Photo.objects.get(id=int(pk))
				return render(request, 'duplicate_photo.html', {'photo': photo, 'females': FEMALES})
			except Photo.DoesNotExist:
				return render(request, 'big_photo.html', {'photo':'photo'})
		else:
			return redirect("missing_page")
	elif which_msg == '9':
		return render(request, 'big_photo.html', {'photo':'photo'})
	else:
		return redirect("missing_page")


@csrf_protect
def upload_public_photo(request,*args,**kwargs):
	if request.method == 'POST':
		user = request.user
		is_ajax = request.is_ajax()
		secret_key_from_form, secret_key_from_session = request.POST.get('sk','0'), get_and_delete_photo_upload_key(request.user.id)
		if str(secret_key_from_form) != str(secret_key_from_session):
			request.session["public_photo_upload_denied"] = '1'
			request.session.modified = True
			if is_ajax:
				return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
			else:
				return redirect('public_photo_upload_denied')
		elif user.userprofile.score < 3:#
			request.session["public_photo_upload_denied"] = '2'
			request.session.modified = True
			if is_ajax:
				return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
			else:
				return redirect('public_photo_upload_denied')
		elif request.user_banned:
			if is_ajax:
				return HttpResponse(json.dumps({'success':False,'message':reverse('missing_page')}),content_type='application/json',)
			else:
				return redirect("missing_page")
		else:
			banned, time_remaining = check_photo_upload_ban(user.id)
			if banned:
				if time_remaining == '-1':
					to_go = time_remaining
				else:
					to_go = timezone.now()+timedelta(seconds=time_remaining)
				request.session["public_photo_upload_denied_time_togo"] = to_go
				request.session["public_photo_upload_denied"] = '3'
				request.session.modified = True
				if is_ajax:
					return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
				else:
					return redirect('public_photo_upload_denied')
			else:
				number_of_photos = 0
				photos = []
				total_score = 0
				photo_ids = get_recent_photos(user.id)
				photos_qs = Photo.objects.filter(id__in=photo_ids).order_by('-id')#.annotate(unique_comment_count=Count('photocomment__submitted_by', distinct=True))
				for photo in photos_qs:
					total_score += photo.visible_score#((VOTE_WEIGHT*photo.vote_score) + photo.unique_comment_count)
					photos.append((photo.vote_score, photo.upload_time, photo.visible_score)) #list of dictionaries
					number_of_photos += 1
				forbidden, time_remaining = check_photo_abuse(number_of_photos, photos)
				if forbidden:
					request.session["public_photo_upload_denied_time_togo"] = time_remaining
					request.session["public_photo_upload_denied"] = '4'
					request.session.modified = True
					if is_ajax:
						return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
					else:
						return redirect('public_photo_upload_denied')			
			time_now = timezone.now()
			try:
				difference = time_now - photos[0][1]
				seconds = difference.total_seconds()
				if seconds < 120:
					request.session["public_photo_upload_denied_time_togo"] = int(120-seconds)
					request.session["public_photo_upload_denied"] = '5'
					request.session.modified = True
					if is_ajax:
						return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
					else:
						return redirect('public_photo_upload_denied')
			except (TypeError, IndexError, AttributeError):
				pass
			form = UploadPhotoForm(request.POST,request.FILES)
			if form.is_valid():
				image_file = request.FILES['image_file']
			else:
				request.session["public_photo_upload_form"] = form
				request.session.modified = True
				if is_ajax:
					return HttpResponse(json.dumps({'success':False,'message':reverse('upload_public_photo')}),content_type='application/json',)
				else:
					return redirect("upload_public_photo")
			if image_file:
				on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
				if on_fbs:
					if image_file.size > 200000:
						request.session["public_photo_upload_denied"] = '6'
						request.session.modified = True
						if is_ajax:
							return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
						else:
							return redirect('public_photo_upload_denied')
				else:
					if image_file.size > 10000000:
						request.session["public_photo_upload_denied"] = '7'
						request.session.modified = True
						if is_ajax:
							return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
						else:
							return redirect('public_photo_upload_denied')
				reoriented = request.POST.get('reoriented',None)
				resized = request.POST.get('resized',None)
				image_file_new, avghash, pk = clean_image_file_with_hash(image=image_file, already_resized=resized, already_reoriented=reoriented)#, caption=request.POST.get('caption',None))
				if isinstance(pk,float):
					request.session["public_photo_upload_denied"] = '8'
					request.session["public_photo_upload_denied_photo_pk"] = pk
					request.session.modified = True
					if is_ajax:
						return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
					else:
						return redirect('public_photo_upload_denied')
				else:
					image_file = image_file_new if image_file_new else None
			if not image_file:
				request.session["public_photo_upload_denied"] = '9'
				request.session.modified = True
				if is_ajax:
					return HttpResponse(json.dumps({'success':False,'message':reverse('public_photo_upload_denied')}),content_type='application/json',)
				else:
					return redirect('public_photo_upload_denied')
			else:
				if request.is_feature_phone:
					device = '1'
				elif request.is_phone:
					device = '2'
				elif request.is_tablet:
					device = '4'
				elif request.is_mobile:
					device = '5'
				else:
					device = '3'
				invisible_score = set_rank()
				caption = request.POST.get('caption',None)
				photo = Photo.objects.create(image_file = image_file, owner=user, caption=caption, comment_count=0, device=device, avg_hash=avghash, \
					invisible_score=invisible_score)
				photo_id = photo.id
				user_id = user.id
				time = photo.upload_time
				epochtime = convert_to_epoch(time)
				timestring = time.isoformat()
				banned = '1' if request.user_banned else '0'
				photo_upload_tasks.delay(banned, user_id,photo_id, timestring, device)
				insert_hash(photo_id, photo.avg_hash) #perceptual hash of the photo
				add_photo(photo_id) #adding into photo feed so that it shows up
				save_recent_photo(user_id, photo_id) #saving 5 recent ones
				try:
					owner_url = user.userprofile.avatar.url
				except ValueError:
					owner_url = None
				name = user.username
				add_photo_entry(photo_id=photo_id,owner_id=user_id,image_url=photo.image_file.url,upload_time=epochtime,\
					invisible_score=invisible_score,caption=caption,photo_owner_username=name,owner_av_url=owner_url,\
					device=device,from_fbs=on_fbs)
				create_object(object_id=photo_id, object_type='0', object_owner_avurl=owner_url,object_owner_id=user_id,\
					object_owner_name=name,object_desc=caption,photourl=photo.image_file.url,vote_score=0,res_count=0)
				# create_notification(viewer_id=user_id, object_id=photo_id, object_type='0',seen=True,updated_at=epochtime,\
				# 	unseen_activity=True)
				if number_of_photos:
					set_uploader_score(user_id, ((total_score*1.0)/number_of_photos)) #only from last 5 photos!
				bulk_create_notifications.delay(user_id, photo_id, epochtime,photo.image_file.url, name, caption)
				############################################
				############################################
				# log_pic_uploader_status(user_id, request.mobile_verified)
				############################################
				############################################
				if is_ajax:
					return HttpResponse(json.dumps({'success':True,'message':reverse('photo')}),content_type='application/json',)
				else:
					return redirect("photo")
	else:
		context = {}
		banned, time_remaining = check_photo_upload_ban(request.user.id)
		if banned:
			context["forbidden"] = True
			if time_remaining == '-1':
				to_go = time_remaining
			else:
				to_go = timezone.now()+timedelta(seconds=time_remaining)
			context["time_remaining"] = to_go
		else:
			photos = Photo.objects.filter(id__in=get_recent_photos(request.user.id)).order_by('-id').values_list('vote_score','upload_time','visible_score')
			number_of_photos = photos.count()
			forbidden, time_remaining = check_photo_abuse(number_of_photos, photos)
			if forbidden:
				context["forbidden"] = forbidden
				context["time_remaining"] = time_remaining
			else:
				bound_form = request.session.pop("public_photo_upload_form",None)
				context["form"] = bound_form if bound_form else UploadPhotoForm()
				secret_key = uuid.uuid4()
				context["sk"] = secret_key
				set_photo_upload_key(request.user.id, secret_key)
				post_big_photo_in_home = True
				if number_of_photos < 5: #must at least have posted 5 photos to have photo appear BIG in home
					post_big_photo_in_home = False
				else:
					for photo in photos:
						if photo[0] < 0: #can't post BIG photo in home if even 1 previous photo had negative score
							post_big_photo_in_home = False
				total_visible_score = sum(photo[2] for photo in photos)
				now = timezone.now()
				hotuser = HotUser.objects.filter(which_user=request.user).update(hot_score=total_visible_score, updated_at=now, allowed=post_big_photo_in_home)
				if hotuser:
					pass
				else:
					HotUser.objects.create(which_user=request.user, hot_score=total_visible_score, updated_at=now, allowed=post_big_photo_in_home)
				context["score"] = request.user.userprofile.score
				context["threshold"] = UPLOAD_PHOTO_REQ
		return render(request,"upload_public_photo.html",context)

##################################################################

class PicsChatUploadView(CreateView):
	model = ChatPic
	form_class = PicsChatUploadForm
	template_name = "pics_chat_upload.html"

	def form_valid(self, form): #this processes the form before it gets saved to the database
		f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
		#image = f.image
		if f.image:
			image_file = clean_image_file(f.image)
			if image_file:
				f.image = image_file
			else:
				f.image = None
		else: 
			f.image = None
		unique = uuid.uuid4()
		user = self.request.user
		if user.is_authenticated():
			if f.image:
				ChatPic.objects.create(image=f.image, owner=user, times_sent=0, unique=unique)
			else:
				context = {'unique': unique}
				return render(self.request, 'error_pic.html', context)
		else:
			if f.image:
				ChatPic.objects.create(image=f.image, owner_id=1, times_sent=0, unique=unique)
			else:
				context = {'unique': unique}
				return render(self.request, 'error_pic.html', context)
		return redirect("pic_expiry", slug=unique)

class PicExpiryView(FormView):
	form_class = PicExpiryForm
	template_name = "pic_expiry_form.html"

	def get_context_data(self, **kwargs):
		context = super(PicExpiryView, self).get_context_data(**kwargs)
		unique = self.kwargs["slug"]
		context["unique"] = unique
		if self.request.user.is_authenticated():
			context["is_authenticated"] = True
		else:
			context["is_authenticated"] = False
		return context

	def form_valid(self, form): #this processes the form before it gets saved to the database
		unique = self.request.POST.get("unique")
		decision = self.request.POST.get("decision")
		if decision == 'sirf aik bar' and valid_uuid(unique):
			num = 1
		elif decision == 'kayee bar' and valid_uuid(unique):
			num = 2
		else:
			return redirect("pic_expiry", slug=unique)
		return redirect("captionview", num=num, slug=unique)

class CaptionView(CreateView):
	model = ChatPicMessage
	form_class = CaptionForm
	template_name = "caption.html"

	def get_context_data(self, **kwargs):
		context = super(CaptionView, self).get_context_data(**kwargs)
		unique = self.kwargs["slug"]
		num = self.kwargs["num"]
		err = self.kwargs["err"]
		context["unique"] = unique
		context["num"] = num
		context["err"] = err
		return context

	def form_valid(self,form):
		if self.request.method == 'POST':
			f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
			user = self.request.user
			caption = f.caption
			unique = self.kwargs["slug"]
			num = self.kwargs["num"]
			if len(caption) > 149:
				return redirect("caption", num=num, slug=unique, err=1)
			which_pic = ChatPic.objects.get(unique=unique)
			if user.is_authenticated():
				message = ChatPicMessage.objects.create(which_pic=which_pic, sender=user, caption=caption, expiry_interval=num)
			else:
				message = ChatPicMessage.objects.create(which_pic=which_pic, sender_id=1, caption=caption, expiry_interval=num)
			return redirect("user_phonenumber", slug=unique, num=num, err=0, id=message.id)

class CaptionDecView(FormView):
	form_class = CaptionDecForm
	template_name = "caption_form.html"

	def get_context_data(self, **kwargs):
		context = super(CaptionDecView, self).get_context_data(**kwargs)
		unique = self.kwargs["slug"]
		num = self.kwargs["num"]
		context["unique"] = unique
		context["num"] = num
		return context

	def form_valid(self,form):
		unique = self.kwargs["slug"]
		num = self.kwargs["num"]
		dec = self.request.POST.get("dec")
		if dec == 'Haan':
			return redirect("caption", num=num, slug=unique, err=0)
		elif dec == 'Nahi':
			return redirect("user_phonenumber", slug=unique, num=num, err=0, id=0)		
		else:
			return redirect("captionview", num=num, slug=unique)

class UserPhoneNumberView(CreateView):
	model = ChatPicMessage
	form_class = UserPhoneNumberForm
	template_name = "get_user_phonenumber.html"

	# def get_initial(self):#initial is a keyword argument to a formfield that enables pre-filling in the formfield
	# 	"""
	# 	Returns the initial data to use for forms on this view.
	# 	"""
	# 	user = self.request.user
	# 	if user.is_authenticated():
	# 		try:
	# 			msg = ChatPicMessage.objects.filter(sender=user).latest('sending_time')
	# 			self.initial = {'what_number': msg.what_number} #initial needs to be passed a dictionary
	# 			return self.initial
	# 		except:
	# 			return self.initial
	# 	else:#i.e user is not authenticated
	# 		return self.initial
	# 	return self.initial

	def get_context_data(self, **kwargs):
		context = super(UserPhoneNumberView, self).get_context_data(**kwargs)
		unique = self.kwargs["slug"]
		ident = self.kwargs["id"]
		context["unique"] = unique
		num = self.kwargs["num"]
		context["decision"] = num
		context["id"] = ident
		err = self.kwargs["err"]
		context["err"] = err
		return context

	def form_valid(self, form): #this processes the form before it gets saved to the database
		f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
		num = f.what_number
		user = self.request.user
		unique = self.kwargs["slug"]
		ident = self.kwargs["id"]
		decision = self.kwargs["num"]
		if not num.isdigit():
			return redirect("user_phonenumber", slug=unique, num=decision, err=1, id=ident)		
		if not valid_uuid(unique):
			return redirect("user_phonenumber", slug=unique, num=decision, err=3, id=ident)
		if not valid_passcode(user=user, num=num):
			return redirect("user_phonenumber", slug=unique, num=decision, err=2, id=ident)
		if not (decision == '1' or '2'):
			return redirect("pic_expiry", slug=unique)
		which_image = ChatPic.objects.get(unique=unique)
		which_image.times_sent = which_image.times_sent + 1
		which_image.save()
		if int(ident):#i.e. it is not zero
			try:
				messageobject = ChatPicMessage.objects.get(pk=ident)
				messageobject.what_number = num
				messageobject.save()
			except:
				return redirect("user_phonenumber", slug=unique, num=decision, err=3, id=ident)
		else:#i.e. it is 0; no caption was set
			if user.is_authenticated():
				ChatPicMessage.objects.create(which_pic=which_image, sender=user, expiry_interval=decision, what_number=num)
			elif not user.is_authenticated():
				ChatPicMessage.objects.create(which_pic=which_image, sender_id=1, expiry_interval=decision, what_number=num)
			else:
				return redirect("user_phonenumber", slug=unique, num=decision, err=2, id=ident)
		on_fbs = self.request.META.get('HTTP_X_IORG_FBS',False)
		# try:
		# 	on_fbs = self.request.META.get('X-IORG-FBS')
		# except:
		# 	on_fbs = False
		if on_fbs:
				#definitely on a mobile browser, but can't redirect out now, so show the web address they are to send
				return redirect("user_SMS", fbs=1, num=num)
		else:#i.e. not on internet.org, now detect whether mobile browser or desktop browser
				return redirect("user_SMS", fbs=0, num=num)

	# def get_success_url(self): #which URL to go back once settings are saved?
	# 	try: 
	# 		on_fbs = self.request.META.get('X-IORG-FBS')
	# 	except:
	# 		on_fbs = False
	# 	if on_fbs:
	# 		return 
	# 		return redirect("home")#, pk= reply.answer_to.id)

class UserSMSView(FormView):
	form_class = UserSMSForm
	template_name = "user_sms.html"

	def get_context_data(self, **kwargs):
		context = super(UserSMSView, self).get_context_data(**kwargs)
		#send_sms = str(self.kwargs["sms"])
		num = str(self.kwargs["num"])
		fbs = str(self.kwargs["fbs"])
		if (fbs == '1' or '0') and num.isdigit():
			context["legit"] = True
			context["num"] = num
			context["fbs"] = fbs
			if self.request.is_feature_phone:
				context["device"] = '1'
			elif self.request.is_phone:
				context["device"] = '2'
			elif self.request.is_tablet:
				context["device"] = '4'
			elif self.request.is_mobile:
				context["device"] = '5'
			else:
				context["device"] = '3'
			user = self.request.user
			if user.is_authenticated():
				try:
					inbox = ChatInbox.objects.filter(owner=user).latest('id')
				except:
					inbox = ChatInbox.objects.create(owner=user)#.latest('id')
				addr = inbox.pin_code
				context["addr"] = addr
				#context["authenticated"] = True
			elif not user.is_authenticated():
				inbox = ChatInbox.objects.create(owner_id=1)
				addr = inbox.pin_code
				context["addr"] = addr
				#context["authenticated"] = False
			else:
				context["legit"] = False
				#context["dev"] = None
				context["num"] = None
				context["fbs"] = None
				context["addr"] = None
				#context["send_sms"] = None
				#context["authenticated"] = None
				#context["sentence"] = None								
		else:
			context["legit"] = False
			#context["dev"] = None
			context["num"] = None
			context["fbs"] = None
			context["addr"] = None
			context["device"] = '0'
			#context["send_sms"] = None
			#context["authenticated"] = None
			#context["sentence"] = None
		return context
				
class PhotoShareView(FormView):
	form_class = PhotoShareForm
	template_name = "photo_share_help.html"

	def get_context_data(self, **kwargs):
		context = super(PhotoShareView, self).get_context_data(**kwargs)
		try:
			loc = self.kwargs["loc"]
			context["loc"] = loc
			if loc == '3':
				username = self.kwargs["slug"]
				context["username"] = username
			else:
				username = None
		except:
			loc = '0'
			context["loc"] = loc
			username = None
		try:
			context["no_id"] = False
			pk = self.kwargs["pk"]
			context["ident"] = pk
			context["freebasics_url"] = "https://https-damadam-pk.0.freebasics.com/photo_detail/"+str(pk)
			context["regular_url"] = "https://damadam.pk/photo_detail/"+str(pk)
		except:
			context["no_id"] = True
		if self.request.user.is_authenticated():
			context["authenticated"] = True
		else:
			context["authenticated"] = False
		return context

class DeletePicView(FormView):
	form_class = DeletePicForm
	template_name = "delete_pic.html"	

	def get_context_data(self, **kwargs):
		context = super(DeletePicView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			unique = self.kwargs["slug"]
			context["unique"] = unique
		return context

	def form_valid(self, form): #this processes the form before it gets saved to the database
		if self.request.method == 'POST':
			unique = self.request.POST.get("ident")
			decision = self.request.POST.get("decision")
			if decision == 'Haan':
				pic = ChatPic.objects.get(unique=unique)
				if self.request.user == pic.owner:
					pic.is_visible = False
					pic.save()
				else:
					pass
			elif decision == 'Nahi':
				pass
			else:
				pass
			return redirect("auth_pics_display")
		else:
			return redirect("score_help")

class PicHelpView(FormView):
	form_class = PicHelpForm
	template_name = "pic_help.html"		

class PicPasswordView(NeverCacheMixin,FormView):
	form_class = PicPasswordForm
	template_name = "pic_password.html"

	def get_context_data(self, **kwargs):
		context = super(PicPasswordView, self).get_context_data(**kwargs)
		code = str(self.kwargs["code"])
		if code.isdigit():
			context["code"] = code
		else:
			context["code"] = None
		return context

	def form_valid(self, form): #this processes the form before it gets saved to the database
		mobile = self.request.POST.get("mobile_number")
		code = self.kwargs["code"]
		try:
			inbox = ChatInbox.objects.get(pin_code=code)
			user = inbox.owner #mhb11 is selected if unauthenticated user
			message = ChatPicMessage.objects.filter(what_number=mobile, sender=user).latest('sending_time')
			sender = message.sender
			caption = message.caption
			expiry_interval = message.expiry_interval
			pic = message.which_pic #the picture to be shown
			is_visible = pic.is_visible
		except:
			context = {'sender':None, 'refresh_now':False, 'exists':0, 'pic':2, 'max_time':0,'caption':None,}
			return render(self.request, 'pic.html', context)
		if message.seen:
			#i.e. the message was already seen
			if expiry_interval == '1':
				#the viewer has refreshed, so disappear the image FOREVER, but determine which error message to show
				#time_now = datetime.utcnow().replace(tzinfo=utc)
				time_now = timezone.now()
				viewing_time = message.viewing_time
				difference = time_now - viewing_time
				if difference.total_seconds() < 60 and is_visible:
					#pic:3 Ye photo dekh li gaye hai. 1 minute wali photo aik dafa se ziyada nahi dekhi jaa sakti. 
					context = {'sender':sender, 'refresh_now':True, 'exists':0, 'pic':3, 'max_times':0,'caption':None,}
				elif difference.total_seconds() < 60 and not is_visible:
					#pic:-1 Ye photo bhejnay waley ne mita di hai
					context = {'sender':sender, 'refresh_now':True, 'exists':0, 'pic':-1, 'max_time':0,'caption':None,}
				elif difference.total_seconds() > 60 and is_visible:
					#pic:0 Is photo ka waqt khatam ho gaya, <b>{{ max_time|naturaltime }}</b>
					context = {'sender':sender, 'refresh_now':True, 'exists':0, 'pic':0, 'max_time':viewing_time + timedelta(minutes = 1),'caption':None,}
				else:
					#pic:1 Is photo ka time khatam ho gaya, <b>{{ max_time|naturaltime }}</b>
					context = {'sender':sender, 'refresh_now':True, 'exists':0, 'pic':1, 'max_time':viewing_time + timedelta(minutes = 1),'caption':None,}
			elif expiry_interval == '2':
				#the user has refreshed, but it was a day-long image
				#time_now = datetime.utcnow().replace(tzinfo=utc)
				time_now = timezone.now()
				viewing_time = message.viewing_time
				difference = time_now - viewing_time
				if difference.total_seconds() < (60*60*24) and is_visible:
					context = {'sender':sender, 'refresh_now':False, 'exists':1, 'pic':pic, 'max_time':'kayee','caption':caption,}
				elif difference.total_seconds() < (60*60*24) and not is_visible:
					#pic:-1 Ye photo bhejnay waley ne mita di hai
					context = {'sender':sender, 'refresh_now':False, 'exists':0, 'pic':-1, 'max_time':0,'caption':None,}
				elif difference.total_seconds() > (60*60*24) and is_visible:
					#pic:0 Is photo ka waqt khatam ho gaya, <b>{{ max_time|naturaltime }}</b>
					context = {'sender':sender, 'refresh_now':False, 'exists':0, 'pic':0, 'max_time':viewing_time + timedelta(minutes = 1440),'caption':None,}
				else:
					#pic:1 Is photo ka time khatam ho gaya, <b>{{ max_time|naturaltime }}</b>
					context = {'sender':sender, 'refresh_now':False, 'exists':0, 'pic':1, 'max_time':viewing_time + timedelta(minutes = 1440),'caption':None,}
			else:# the expiry_interval was not set: ABORT
				#pic:2 Yahan dekney ke liye kuch nahi hai
				context = {'sender':sender, 'refresh_now':False, 'exists':0, 'pic':2, 'max_time':0,'caption':None,}
			return render(self.request, 'pic.html', context)
		else:
			#the message object is being opened for the first time
			if self.request.user.is_authenticated() and self.request.user == sender:
				#if the person opening it is the same person who sent the photo
				#time_now = datetime.utcnow().replace(tzinfo=utc)
				time_now = timezone.now
				context = {'sender':sender, 'refresh_now':True, 'exists':1, 'pic':pic, 'max_time':0,'caption':caption,}
			else:
				#set the seen flag of the message object
				message.seen = True
				#viewing_time = datetime.utcnow().replace(tzinfo=utc)
				viewing_time = timezone.now()
				message.viewing_time = viewing_time
				message.save()
				if expiry_interval == '1' and is_visible:
					context = {'sender':sender, 'refresh_now':True, 'exists':1, 'pic':pic, 'max_time':'aik','caption':caption,}
				elif expiry_interval == '1' and not is_visible:
					context = {'sender':sender, 'refresh_now':False, 'exists':0, 'pic':-1, 'max_time':0,'caption':None,}
				elif expiry_interval == '2' and is_visible:
					context = {'sender':sender, 'refresh_now':False, 'exists':1, 'pic':pic, 'max_time':'kayee','caption':caption,}
				elif expiry_interval == '2' and not is_visible:
					context = {'sender':sender, 'refresh_now':False, 'exists':0, 'pic':-1, 'max_time':0,'caption':None,}
				else:
					#Yahan dekhney ke liye kuch nahi hai
					context = {'sender':sender, 'refresh_now':False, 'exists':0, 'pic':2, 'max_time':0,'caption':None,}
			return render(self.request, 'pic.html', context)

class ChangeGroupRulesView(CreateView):
	model = Group
	form_class = ChangeGroupRulesForm
	template_name = "change_group_rules.html"

	def get_context_data(self, **kwargs):
		context = super(ChangeGroupRulesView, self).get_context_data(**kwargs)
		user = self.request.user
		context["unauthorized"] = False
		if user.is_authenticated():
			unique = self.request.session["public_uuid"]
			context["unique"] = unique
			group = Group.objects.get(unique=unique)
			context["group"] = group
			if group.private == '0':
				if not group.owner == user:
					context["unauthorized"] = True
				else:
					context["unauthorized"] = False
		return context

	def form_valid(self, form): #this processes the form before it gets saved to the database
		user = self.request.user
		if self.request.user_banned:
			return redirect("profile", slug=user.username)
		else:
			rules = self.request.POST.get("rules")
			unique = self.request.session["public_uuid"]
			group = Group.objects.get(unique=unique)
			if group.private == '0' and group.owner != user:
				return redirect("score_help")
			group.rules = rules
			group.save()
			Reply.objects.create(text=rules ,which_group=group ,writer=user ,category='5')
			return redirect("public_group", slug=unique)

class ChangePrivateGroupTopicView(CreateView):
	model = Group
	form_class = ChangePrivateGroupTopicForm
	template_name = "change_private_group_topic.html"

	def get_context_data(self, **kwargs):
		context = super(ChangePrivateGroupTopicView, self).get_context_data(**kwargs)
		user = self.request.user
		context["unauthorized"] = False
		if user.is_authenticated():
			# banned, ban_type, time_remaining, warned = private_group_posting_allowed(self.request.user.id)
			# banned = False
			unique = self.request.session.get("unique_id",None)
			if unique:# and not banned:	
				context["unique"] = unique
				group = Group.objects.get(unique=unique)
				context["group"] = group
				if group.private == '0' or group.private == '2':
					context["unauthorized"] = True
					context["group"] = None
					return context
			else:
				context["unauthorized"] = True
				context["group"] = None
				return context
		return context

	def form_valid(self, form):
		user = self.request.user
		if self.request.user_banned:
			return render(self.request,'500.html',{})
		else:
			# topic = self.request.POST.get("topic")
			topic = form.cleaned_data.get("topic")
			unique = self.request.session["unique_id"]
			group = Group.objects.get(unique=unique)
			if (group.private == '0' or group.private == '2') and group.owner != user:
				return redirect("score_help")
			group.topic = topic
			group.save()
			if self.request.is_feature_phone:
				device = '1'
			elif self.request.is_phone:
				device = '2'
			elif self.request.is_tablet:
				device = '4'
			elif self.request.is_mobile:
				device = '5'
			else:
				device = '3'
			Reply.objects.create(text=topic ,which_group=group , writer=user, category='4', device=device)
			self.request.session["unique_id"] = unique
			return redirect("private_group_reply")#, slug=unique)

class ChangeGroupTopicView(CreateView):
	model = Group
	form_class = ChangeGroupTopicForm
	template_name = "change_group_topic.html"

	def get_context_data(self, **kwargs):
		context = super(ChangeGroupTopicView, self).get_context_data(**kwargs)
		user = self.request.user
		context["unauthorized"] = False
		if user.is_authenticated():
			unique = self.request.session["public_uuid"]
			if unique:	
				context["unique"] = unique
				group = Group.objects.get(unique=unique)
				context["group"] = group
				if group.private == '0':
					if not group.owner == user:
						context["unauthorized"] = True
					else:
						context["unauthorized"] = False
			else:
				context["unauthorized"] = True
				return context
		return context

	def form_valid(self, form): #this processes the form before it gets saved to the database
		user = self.request.user
		if self.request.user_banned:
			return render(self.request,'500.html',{})
		else:
			# topic = self.request.POST.get("topic")
			topic = form.cleaned_data.get("topic")
			unique = self.request.session['public_uuid']
			group = Group.objects.get(unique=unique)
			if group.private == '0' and group.owner != user:
				return redirect("score_help")
			group.topic = topic
			group.save()
			Reply.objects.create(text=topic ,which_group=group , writer=user, category='4')
			return redirect("public_group", slug=unique)


def public_group_request_denied(request):
	which_msg = request.session.pop("public_group_request_denied",None)
	if which_msg == '1':
		return render(request,'big_photo_fbs.html',{'pk':'pk'})
	elif which_msg == '2':
		return render(request,'big_photo_regular.html',{'origin':'pub_grp'})
	elif which_msg == '3':
		return render(request, 'big_photo.html', {'photo':'pub_grp'})
	else:
		return redirect("missing_page")



class PublicGroupView(CreateView):
	model = Reply
	form_class = PublicGroupReplyForm
	template_name = "public_group_reply.html"

	@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
	def dispatch(self, request, *args, **kwargs):
		# Try to dispatch to the right method; if a method doesn't exist,
		# defer to the error handler. Also defer to the error handler if the
		# request method isn't on the approved list.
		if request.method.lower() in self.http_method_names:
			handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
		else:
			handler = self.http_method_not_allowed
		self.request = request
		self.args = args
		self.kwargs = kwargs
		return handler(request, *args, **kwargs)

	def get_form_kwargs(self):
		kwargs = super(PublicGroupView,self).get_form_kwargs()
		kwargs['user_id'] = self.request.user.id
		kwargs['is_mob_verified'] = self.request.mobile_verified
		return kwargs

	def get_context_data(self, **kwargs):
		context = super(PublicGroupView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			# pk = self.request.POST.get('gp',None)
			unique = self.request.session.get("public_uuid",None)
			try:
				# group = Group.objects.get(pk=pk)
				group = Group.objects.get(unique=unique)
				context["unique"] = unique
			except Group.DoesNotExist:
				context["switching"] = True
				context["group_banned"] = False
				return context
			if 'awami' in self.request.path and group.private == '0': 
				user_id, group_id = self.request.user.id, group.id
				secret_key = uuid.uuid4()
				context["sk"] = secret_key
				set_text_input_key(user_id, group_id, 'pub_grp', secret_key)
				context["form"] = self.request.session.pop("public_group_form") if "public_group_form" in self.request.session else \
				PublicGroupReplyForm()
				context["score"] = self.request.user.userprofile.score
				context["csrf"] = csrf.get_token(self.request)
				context["switching"] = False
				context["group"] = group
				if GroupBanList.objects.filter(which_user_id=user_id,which_group_id=group_id).exists():
					context["group_banned"]=True
					culprit_username = self.request.user.username
					if check_group_member(group_id, culprit_username):
						remove_group_member(group_id, culprit_username)
						remove_group_notification(user_id,group_id)
						remove_user_group(user_id, group_id)
					elif check_group_invite(user_id, group_id):
						remove_group_invite(user_id, group_id)
					return context#no need to process more
				public_group_attendance_tasks.delay(group_id=group_id, user_id=user_id)
				context["ensured"] = FEMALES
				context["mobile_verified"] = self.request.mobile_verified
				replies = Reply.objects.select_related('writer__userprofile').filter(which_group_id=group_id).exclude(category='1').order_by('-submitted_on')[:25]#get DB call
				time_now = timezone.now()
				updated_at = convert_to_epoch(time_now)
				save_user_presence(user_id,group_id,updated_at)
				pres_dict = get_latest_presence(group_id,set(reply.writer_id for reply in replies))
				context["replies"] = [(reply,reply.writer,pres_dict[reply.writer_id]) for reply in replies]
				context["unseen"] = False
				context["on_fbs"] = self.request.META.get('HTTP_X_IORG_FBS',False)
				if not self.request.user_banned:#do the following ONLY if user isn't hell-banned
					members = get_group_members(group_id)
					if self.request.user.username in members and context["replies"]:
						update_notification(viewer_id=self.request.user.id, object_id=group_id, object_type='3', seen=True, \
							updated_at=updated_at, single_notif=False, unseen_activity=True, priority='public_mehfil', \
							bump_ua=False) #just seeing means notification is updated, but not bumped up in ua:
			else:
				context["switching"] = True
				context["group_banned"] = False
		return context

	def form_invalid(self, form):
		"""
		If the form is invalid, re-render the context data with the
		data-filled form and errors.
		"""
		self.request.session["public_group_form"] = form
		self.request.session.modified = True
		if self.request.is_ajax():
			return HttpResponse(json.dumps({'success':False,'message':reverse('public_group')}),content_type='application/json',)
		else:
			return self.render_to_response(self.get_context_data(form=form))

	def form_valid(self, form): #this processes the public form before it gets saved to the database
		"""
		If the form is valid, redirect to the supplied URL.
		"""
		is_ajax = self.request.is_ajax()
		if self.request.user_banned:
			if is_ajax:
				return HttpResponse(json.dumps({'success':False,'message':reverse('missing_page')}),content_type='application/json',)
			else:
				return redirect("missing_page")
		user_id = self.request.user.id
		pk = self.request.POST.get('gp',None)
		try:
			which_group = Group.objects.get(id=pk)
		except Group.DoesNotExist:
			if is_ajax:
				return HttpResponse(json.dumps({'success':False,'message':reverse('group_page')}),content_type='application/json',)
			else:
				return redirect("group_page")
		if GroupBanList.objects.filter(which_user_id=user_id, which_group_id=which_group.id).exists():
			if is_ajax:
				return HttpResponse(json.dumps({'success':False,'message':reverse('group_page')}),content_type='application/json',)
			else:
				return redirect("group_page")
		else:
			if self.request.user.userprofile.score < -25:#
				HellBanList.objects.create(condemned=self.request.user)
				self.request.user.userprofile.score = random.randint(10,71)
				self.request.user.userprofile.save()
				if is_ajax:
					return HttpResponse(json.dumps({'success':False,'message':reverse('group_page')}),content_type='application/json',)
				else:
					return redirect("group_page")
			f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
			set_input_rate_and_history.delay(section='pub_grp',section_id=which_group.id,text=f.text,user_id=user_id,time_now=time.time())
			UserProfile.objects.filter(user_id=user_id).update(score=F('score')+PUBLIC_GROUP_MESSAGE)
			self.request.session["public_uuid"] = which_group.unique
			self.request.session.modified = True
			if f.image and which_group.pics_ki_ijazat == '1':
				on_fbs = self.request.META.get('HTTP_X_IORG_FBS',False)
				if on_fbs:
					if f.image.size > 200000:
						self.request.session["public_group_request_denied"] = '1'
						self.request.session.modified = True
						if is_ajax:
							return HttpResponse(json.dumps({'success':False,'message':reverse('public_group_request_denied')}),content_type='application/json',)
						else:
							return redirect("public_group_request_denied")
				else:
					if f.image.size > 10000000:
						self.request.session["public_group_request_denied"] = '2'
						self.request.session.modified = True
						if is_ajax:
							return HttpResponse(json.dumps({'success':False,'message':reverse('public_group_request_denied')}),content_type='application/json',)
						else:
							return redirect("public_group_request_denied")
				image_file = clean_image_file(f.image, already_reoriented=self.request.POST.get('reoriented',None),\
					already_resized=self.request.POST.get('resized',None))
				if image_file is False:
					self.request.session["public_group_request_denied"] = '3'
					self.request.session.modified = True
					if is_ajax:
						return HttpResponse(json.dumps({'success':False,'message':reverse('public_group_request_denied')}),content_type='application/json',)
					else:
						return redirect('public_group_request_denied')
				else:
					f.image = image_file
			else: 
				f.image = None
			if self.request.is_feature_phone:
				device = '1'
			elif self.request.is_phone:
				device = '2'
			elif self.request.is_tablet:
				device = '4'
			elif self.request.is_mobile:
				device = '5'
			else:
				device = '3'
			which_group_id = which_group.id
			reply = Reply.objects.create(writer_id=user_id, which_group=which_group, text=f.text, image=f.image, device=device)#
			add_group_member(which_group_id, self.request.user.username)
			remove_group_invite(user_id, which_group_id)
			add_user_group(user_id, which_group_id)
			reply_time = convert_to_epoch(reply.submitted_on)
			try:
				url=self.request.user.userprofile.avatar.url
			except ValueError:
				url=None
			try:
				image_url = reply.image.url
			except ValueError:
				image_url = None
			rank_public_groups.delay(group_id=which_group_id,writer_id=user_id)
			public_group_attendance_tasks.delay(group_id=which_group_id, user_id=user_id)
			group_notification_tasks.delay(group_id=which_group_id,sender_id=user_id,group_owner_id=which_group.owner.id,\
				topic=which_group.topic,reply_time=reply_time,poster_url=url,poster_username=self.request.user.username,\
				reply_text=f.text,priv=which_group.private,slug=which_group.unique,image_url=image_url,priority='public_mehfil',\
				from_unseen=False, reply_id=reply.id)
			if is_ajax:
				return HttpResponse(json.dumps({'success':False,'message':reverse('public_group')}),content_type='application/json',)
			else:
				return redirect("public_group")


@ratelimit(rate='3/s')
def public_group(request, slug=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if not slug:
		slug = request.session.get("public_uuid",None)
	else:
		request.session["public_uuid"] = slug
		request.session.modified = True
	if valid_uuid(slug):
		if was_limited:
			return redirect("missing_page")
		else:
			return redirect("public_group_reply")
	else:
		return redirect("group_page")



@ratelimit(rate='3/s')
def first_time_cricket_refresh(request, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# if request.user.is_authenticated():
		# 	deduction = 1 * -1
		# 	request.user.userprofile.score = request.user.userprofile.score + deduction
		# 	request.user.userprofile.save()
		# 	return render(request, 'cricket_refresh_penalty.html', {})
		# else:
		# 	return render(request, 'cricket_refresh_penalty.html', {})
		return redirect("missing_page")
	else:
		if first_time_refresher(request.user.id):
			add_refresher(request.user.id)
			return render(request, 'cricket_refresh.html', {})
		else:
			return redirect("cricket_comment")

@ratelimit(rate='3/s')
def first_time_unseen_refresh(request, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# if request.user.is_authenticated():
		# 	deduction = 1 * -1
		# 	request.user.userprofile.score = request.user.userprofile.score + deduction
		# 	request.user.userprofile.save()
		# 	context = {'unique': request.user.username}
		# 	return render(request, 'unseen_activity_refresh_penalty.html', context)
		# else:
		# 	context = {'unique': 'none'}
		# 	return render(request, 'unseen_activity_refresh_penalty.html', context)
		return redirect("missing_page")
	else:
		if first_time_refresher(request.user.id):
			add_refresher(request.user.id)
			context = {'unique': request.user.username}
			return render(request, 'unseen_activity_refresh.html', context)
		else:
			return redirect("unseen_activity", request.user.username)


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def first_time_public_refresh(request):
	if request.method == "POST":
		unique = request.POST.get('uid',None)
		if first_time_refresher(request.user.id):
			add_refresher(request.user.id)
			context = {'unique': unique}
			return render(request, 'public_mehfil_refresh.html', context)
		else:
			return redirect("public_group", unique)
	else:
		return redirect("public_group")


@ratelimit(rate='3/s')
def first_time_refresh(request, unique=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# if request.user.is_authenticated():
		# 	deduction = 1 * -1
		# 	request.user.userprofile.score = request.user.userprofile.score + deduction
		# 	request.user.userprofile.save()
		# 	context = {'unique': unique}
		# 	return render(request, 'mehfil_refresh_penalty.html', context)
		# else:
		# 	context = {'unique': 'none'}
		# 	return render(request, 'mehfil_refresh_penalty.html', context)
		return redirect("missing_page")
	else:
		if first_time_refresher(request.user.id):
			add_refresher(request.user.id)
			context = {'unique': unique}
			return render(request, 'mehfil_refresh.html', context)
		else:
			request.session["unique_id"] = unique
			return redirect("private_group_reply")#, slug=unique)

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@sensitive_post_parameters()
@csrf_protect
def priv_group(request,*args,**kwargs):
	if request.method == 'POST':
		slug = request.POST.get("private_uuid")
		if valid_uuid(slug):
			request.session["unique_id"] = slug
			return redirect("private_group_reply")
		else:
			return redirect("group_page")	
	else:
		return redirect("group_page")

class PrivateGroupView(CreateView): #get_queryset doesn't work in CreateView (it's a ListView thing!)
	model = Reply
	form_class = PrivateGroupReplyForm		
	template_name = "private_group_reply.html"

	@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
	def dispatch(self, request, *args, **kwargs):
		# Try to dispatch to the right method; if a method doesn't exist,
		# defer to the error handler. Also defer to the error handler if the
		# request method isn't on the approved list.
		if request.method.lower() in self.http_method_names:
			handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
		else:
			handler = self.http_method_not_allowed
		self.request = request
		self.args = args
		self.kwargs = kwargs
		return handler(request, *args, **kwargs)

	def get_form_kwargs( self ):
		kwargs = super(PrivateGroupView,self).get_form_kwargs()
		kwargs['user_id'] = self.request.user.id
		return kwargs

	def get_context_data(self, **kwargs):
		context = super(PrivateGroupView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			try:
				unique = self.request.session['unique_id']
			except:
				context["switching"] = True
				return context
			if unique:
				context["unique"] = unique
			else:
				context["switching"] = True
				return context
			try:
				group = Group.objects.get(unique=unique)#get DB call
			except:
				context["switching"] = True
				return context
			context["group"] = group
			if 'private' in self.request.path and group.private=='1':
				user_id = self.request.user.id
				group_id = group.id
				secret_key = uuid.uuid4()
				context["sk"] = secret_key
				set_text_input_key(user_id, group_id, 'prv_grp', secret_key)
				on_fbs = self.request.META.get('HTTP_X_IORG_FBS',False)
				context["score"] = self.request.user.userprofile.score
				context["csrf"] = csrf.get_token(self.request)
				context["switching"] = False
				context["ensured"] = FEMALES
				context["mobile_verified"] = self.request.mobile_verified
				replies = Reply.objects.select_related('writer__userprofile').defer('writer__userprofile__attractiveness',\
					'writer__userprofile__mobilenumber','writer__userprofile__previous_retort','writer__userprofile__age',\
					'writer__userprofile__gender','writer__userprofile__bio','writer__userprofile__streak','writer__userprofile__media_score',\
					'writer__userprofile__shadi_shuda','writer__userprofile__id','writer__is_superuser','writer__first_name','writer__last_name',\
					'writer__last_login','writer__email','writer__date_joined','writer__is_staff','writer__is_active','writer__password').\
				filter(which_group_id=group_id).order_by('-submitted_on')[:25]
				time_now = timezone.now()
				updated_at = convert_to_epoch(time_now)
				log_private_mehfil_session.delay(group_id, user_id)
				save_user_presence(user_id,group.id,updated_at)
				pres_dict = get_latest_presence(group_id,set(reply.writer_id for reply in replies))
				context["replies"] = [(reply,reply.writer,pres_dict[reply.writer_id]) for reply in replies]
				context["unseen"] = False
				if not self.request.user_banned:#do the following ONLY if user isn't hell-banned
					members = get_group_members(group_id)
					context["members"] = members #contains members' usernames
					if members and replies and self.request.user.username in members:
						# flip "unseen" notification here
						context["unseen"] = True #i.e. the user is a member and replies exist; the prospect of unseen replies exists
						update_notification(viewer_id=user_id, object_id=group_id, object_type='3', seen=True, \
							updated_at=updated_at, single_notif=False, unseen_activity=True, priority='priv_mehfil',
							bump_ua=False) #just seeing means notification is updated, but not bumped up in ua:
						try:
							#finding latest time user herself replied
							context["reply_time"] = max(reply.submitted_on for reply in replies if str(reply.writer) == str(self.request.user))
						except:
							context["reply_time"] = None #i.e. it's the first reply in the last 25 replies (i.e. all were unseen)
					else:
						context["reply_time"] = None
			else:
				context["switching"] = True
		return context

	def form_valid(self, form): #this processes the form before it gets saved to the database
		if self.request.user_banned:
			return render(self.request,'500.html',{})
		else:
			user_id = self.request.user.id
			if self.request.user.userprofile.score < -25:
				HellBanList.objects.create(condemned=self.request.user)
				self.request.user.userprofile.score = random.randint(10,71)
				self.request.user.userprofile.save()
				return redirect("group_page")
			pk = self.request.POST.get('gp',None)
			which_group = Group.objects.get(pk=pk)
			which_group_id, unique = pk, which_group.unique
			f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
			text = f.text #text of the reply
			UserProfile.objects.filter(user_id=user_id).update(score=F('score')+PRIVATE_GROUP_MESSAGE)
			if f.image:
				on_fbs = self.request.META.get('HTTP_X_IORG_FBS',False)
				if on_fbs:
					if f.image.size > 200000:
						context = {'pk':'pk'}
						return render(self.request,'big_photo_fbs.html',context)
					else:
						pass
				else:
					if f.image.size > 10000000:
						context = {'pk':'pk'}
						return render(self.request,'big_photo_regular.html',context)
					else:
						pass
				image_file = clean_image_file(f.image)
				if image_file is False:
					return render(self.request, 'big_photo.html', {'photo':'prv_grp'})
				else:
					f.image = image_file
			else: 
				f.image = None
			if self.request.is_feature_phone:
				device = '1'
			elif self.request.is_phone:
				device = '2'
			elif self.request.is_tablet:
				device = '4'
			elif self.request.is_mobile:
				device = '5'
			else:
				device = '3'
			set_input_rate_and_history.delay(section='prv_grp',section_id=which_group_id,text=text,user_id=user_id,time_now=time.time())
			reply = Reply.objects.create(writer=self.request.user, which_group=which_group, text=text, image=f.image, \
				device=device)
			add_group_member(which_group_id, self.request.user.username)
			remove_group_invite(user_id, which_group_id)
			add_user_group(user_id, which_group_id)
			reply_time = convert_to_epoch(reply.submitted_on)
			try:
				url=self.request.user.userprofile.avatar.url
			except ValueError:
				url=None
			try:
				image_url = reply.image.url
			except ValueError:
				image_url = None
			group_notification_tasks.delay(group_id=which_group_id,sender_id=user_id,group_owner_id=which_group.owner.id,\
				topic=which_group.topic,reply_time=reply_time,poster_url=url,poster_username=self.request.user.username,\
				reply_text=text,priv=which_group.private,slug=unique,image_url=image_url,priority='priv_mehfil',\
				from_unseen=False, reply_id=reply.id)
			self.request.session['unique_id'] = unique
			self.request.session.modified = True
			return redirect("private_group_reply")
				
	
@ratelimit(rate='3/s')
def welcome_pk(request, pk=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# if request.user.is_authenticated():
		# 	deduction = 1 * -10
		# 	request.user.userprofile.score = request.user.userprofile.score + deduction
		# 	request.user.userprofile.save()
		# 	context = {'unique': pk}
		# 	return render(request, 'penalty_welcome.html', context)
		# else:
		# 	context = {'unique': pk}
		# 	return render(request, 'penalty_welcome.html', context)
		return redirect("missing_page")
	else:
		if pk.isdigit():
			request.session["welcome_pk"] = pk
			return redirect("welcome")
		else:
			return redirect("group_help")

class WelcomeView(FormView):
	form_class = WelcomeForm
	template_name = "welcome.html"

	def get_context_data(self, **kwargs):
		context = super(WelcomeView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			try:
				target_user = User.objects.get(id=self.request.session["welcome_pk"])
				context["authenticated"] = True
				context["target_user"] = target_user
			except:
				context["authenticated"] = False
				context["target_user"] = []
		return context

class WelcomeMessageView(CreateView):
	model = Publicreply
	form_class = WelcomeMessageForm
	template_name = "welcome_message.html"

	def get_context_data(self, **kwargs):
		context = super(WelcomeMessageView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			try:
				pk = self.request.session["welcome_pk"]
				context["target_user"] = User.objects.get(id=pk)
				context["authorized"] = True
				context["option"] = self.kwargs["option"]
			except:
				context["authorized"] = False
				context["target_user"] = None
				context["option"] = None
		return context

def mehfilcomment_pk(request, pk=None, num=None, origin=None, slug=None, *args, **kwargs):
	if pk.isdigit() and num.isdigit():
		request.session['mehfilcomment_pk'] = pk
		request.session['mehfilphoto_pk'] = num
		if origin:
			request.session['mehfilfrom_photos'] = origin
		else:
			request.session['mehfilfrom_photos'] = None
		if slug:
			request.session['mehfil_slug'] = slug
		else:
			request.session['mehfil_slug'] = None
		return redirect("mehfilcomment_help")
	else:
		return redirect("score_help")

class MehfilCommentView(FormView):
	form_class = MehfilCommentForm
	template_name = "mehfilcomment_help.html"

	def get_context_data(self, **kwargs):
		context = super(MehfilCommentView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			try:
				target_id = self.request.session['mehfilcomment_pk']
				photo_id = self.request.session['mehfilphoto_pk']
				origin = self.request.session['mehfilfrom_photos']
				slug = self.request.session['mehfil_slug']
				context["target"] = User.objects.get(id=target_id)
				context["photo_id"] = photo_id
				context["origin"] = origin
			except:
				context["target"] = None
				context["photo_id"] = None
				context["origin"] = None
				return context
		return context

	def form_valid(self, form):
		if self.request.method == 'POST':
			user = self.request.user
			report = self.request.POST.get("decision")
			target_id = self.request.session['mehfilcomment_pk']
			photo_id = self.request.session['mehfilphoto_pk']
			origin = self.request.session['mehfilfrom_photos']
			slug = self.request.session['mehfil_slug']
			self.request.session['mehfilcomment_pk'] = None
			self.request.session['mehfilphoto_pk'] = None
			self.request.session['mehfilfrom_photos'] = None
			self.request.session.modified = True
			if report == 'Haan':
				if user.userprofile.score < 500:
					if photo_id is not None and origin is not None:
						context = {'pk': photo_id, 'origin':origin}
						return render(self.request, 'penalty_mehfil.html', context)
					else:
						return redirect("closed_group_help")
				else:
					target = User.objects.get(id=target_id)
					invitee = target.username
					topic = invitee+" se gupshup"
					unique = uuid.uuid4()
					try:
						group = Group.objects.create(topic=topic, rules='', owner=user, private='1', unique=unique)
						UserProfile.objects.filter(user=self.request.user).update(score=F('score')-500)
						reply_list = []
						seen_list = []
						reply = Reply.objects.create(text=invitee, category='1', which_group_id=group.id, writer=user)
						add_group_member(group.id, user.username)
						add_group_invite(target_id, group.id,reply.id)
						add_user_group(user.id, group.id)
						self.request.session["unique_id"] = unique
						self.request.session.modified = True
						return redirect("private_group_reply")#, slug=unique)
					except:
						if photo_id is not None:
							redirect("comment_pk", pk=photo_id)
						else:
							return redirect("profile",slug=self.request.user.username)
			else:
				if slug and origin and photo_id:
					return redirect("comment_pk", pk=photo_id, origin=origin, ident=slug)
				elif photo_id and origin:
					return redirect("comment_pk", pk=photo_id, origin=origin)
				else:
					return redirect("home")

@csrf_protect
@ratelimit(rate='3/s')
def unseen_group(request, pk=None, *args, **kwargs):
	was_limited = getattr(request,'limits',False)
	if was_limited:
		# UserProfile.objects.filter(user_id=user_id).update(score=F('score')-100)
		# return render(request, 'penalty_unseengroupreply.html', {'penalty':100,'uname':username})
		return redirect("missing_page")
	elif request.user_banned:
		return render(request,"500.html",{})
	username = request.user.username
	user_id = request.user.id
	grp = Group.objects.filter(id=pk).values('private','owner_id','topic','unique')[0]
	if not check_group_member(pk, username):
		return render(request, 'penalty_unseengroupreply.html', {'uname':username,'not_member':True})
	elif not request.mobile_verified and not grp["private"] == '1':
		return render(request, 'penalty_unseengroupreply.html', {'uname':username,'not_verified':True})
	else:
		if request.method == 'POST':
			origin, lang, sort_by = request.POST.get("origin",None), request.POST.get("lang",None), request.POST.get("sort_by",None)
			if grp["private"] == '1':
				form = UnseenActivityForm(request.POST,user_id=user_id,prv_grp_id=pk,pub_grp_id='',photo_id='',link_id='',per_grp_id='')
			else:
				form = UnseenActivityForm(request.POST,user_id=user_id,prv_grp_id='',pub_grp_id=pk,photo_id='',link_id='',per_grp_id='')
			if form.is_valid():
				desc1, desc2 = form.cleaned_data.get("public_group_reply"), form.cleaned_data.get("private_group_reply")
				description = desc1 if desc1 else desc2
				if request.is_feature_phone:
					device = '1'
				elif request.is_phone:
					device = '2'
				elif request.is_tablet:
					device = '4'
				elif request.is_mobile:
					device = '5'
				else:
					device = '3'
				groupreply = Reply.objects.create(writer_id=user_id, which_group_id=pk, text=description,device=device)#,image='')
				reply_time = convert_to_epoch(groupreply.submitted_on)
				try:
					url = request.user.userprofile.avatar.url
				except ValueError:
					url = None
				try:
					image_url = groupreply.image.url
				except ValueError:
					image_url = None
				if grp["private"] == '1':
					set_input_rate_and_history.delay(section='prv_grp',section_id=pk,text=description,user_id=user_id,time_now=time.time())
					priority='priv_mehfil'
					UserProfile.objects.filter(user_id=user_id).update(score=F('score')+PRIVATE_GROUP_MESSAGE)
				else:
					set_input_rate_and_history.delay(section='pub_grp',section_id=pk,text=description,user_id=user_id,time_now=time.time())
					priority='public_mehfil'
					UserProfile.objects.filter(user_id=user_id).update(score=F('score')+PUBLIC_GROUP_MESSAGE)
					rank_public_groups.delay(group_id=pk,writer_id=user_id)
					public_group_attendance_tasks.delay(group_id=pk, user_id=user_id)
				group_notification_tasks.delay(group_id=pk,sender_id=user_id, group_owner_id=grp["owner_id"],\
					topic=grp["topic"],reply_time=reply_time,poster_url=url, poster_username=username,\
					reply_text=description,priv=grp["private"], slug=grp["unique"],image_url=image_url,\
					priority=priority,from_unseen=True, reply_id=groupreply.id)
				if origin:
					if origin == '0':
						return redirect("photo")
					elif origin == '1':
						if lang == 'urdu' and sort_by == 'best':
							return redirect("ur_home_best", 'urdu')
						elif sort_by == 'best':
							return redirect("home_best")
						elif lang == 'urdu':
							return redirect("ur_home", 'urdu')
						else:
							return redirect("home")
					elif origin == '2':
						return redirect("best_photo")
					else:
						return redirect("unseen_activity", username)
				else:
					return redirect("unseen_activity", username)
			else:
				if origin:
					request.session["notif_form"] = form
					request.session.modified = True
					if origin == '0':
						return redirect("photo")
					elif origin == '1':
						if lang == 'urdu' and sort_by == 'best':
							return redirect("ur_home_best", 'urdu')
						elif sort_by == 'best':
							return redirect("home_best")
						elif lang == 'urdu':
							return redirect("ur_home", 'urdu')
						else:
							return redirect("home")
					elif origin == '2':
						return redirect("best_photo")
					else:
						return redirect("unseen_activity", username)
				else:
					notification = "np:"+str(user_id)+":3:"+str(pk)
					page_obj, oblist, forms, page_num, addendum = get_object_list_and_forms(request, notification)
					url = reverse_lazy("unseen_activity", args=[username])+addendum
					forms[pk] = form
					request.session["forms"] = forms
					request.session["oblist"] = oblist
					request.session["page_obj"] = page_obj
					request.session.modified = True
					return redirect(url)
		else:
			return redirect("unseen_activity", username)

#called when replying from unseen_activity
@csrf_protect
@ratelimit(rate='3/s')
def unseen_comment(request, pk=None, *args, **kwargs):
	"""
	Processes comment under photo from unseen activity
	"""
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# UserProfile.objects.filter(user_id=user_id).update(score=F('score')-100)
		# return render(request, 'penalty_unseen_comment.html', {'penalty':100,'uname':username})
		return redirect("missing_page")
	elif request.user_banned:
		return render(request,"500.html",{})
	username = request.user.username
	user_id = request.user.id
	if request.method == 'POST':
		photo_owner_id, origin = request.POST.get("popk",None), request.POST.get("origin",None)
		banned_by, ban_time = is_already_banned(own_id=user_id,target_id=photo_owner_id, return_banner=True)
		if banned_by:
			request.session["banned_by"] = banned_by
			request.session["ban_time"] = ban_time
			if origin == '1':
				request.session["where_from"] = 'home'
			elif origin == '0':
				request.session["where_from"] = 'photos'
			elif origin == '2':
				request.session["where_from"] = 'best_photos'
			else:
				request.session["where_from"] = 'matka'
			request.session["own_uname"] = username
			request.session.modified = True
			return redirect("ban_underway")
		lang, sort_by = request.POST.get("lang",None), request.POST.get("sort_by",None)
		form = UnseenActivityForm(request.POST,user_id=user_id,prv_grp_id='',pub_grp_id='',link_id='',photo_id=pk,per_grp_id='')
		if form.is_valid():
			photo_comment_count = Photo.objects.filter(id=pk).values_list('comment_count', flat=True)[0]
			description = form.cleaned_data.get("photo_comment")
			set_input_rate_and_history.delay(section='pht_comm',section_id=pk,text=description,user_id=user_id,time_now=time.time())
			if request.is_feature_phone:
				device = '1'
			elif request.is_phone:
				device = '2'
			elif request.is_tablet:
				device = '4'
			elif request.is_mobile:
				device = '5'
			else:
				device = '3'
			exists = PhotoComment.objects.filter(which_photo_id=pk, submitted_by=request.user).exists() #i.e. user commented before
			photocomment = PhotoComment.objects.create(submitted_by_id=user_id, which_photo_id=pk, text=description,device=device)
			# reset_best_photos_cache.delay(pk)
			update_cc_in_home_photo(pk)
			comment_time = convert_to_epoch(photocomment.submitted_on)
			try:
				url = request.user.userprofile.avatar.url
			except ValueError:
				url = None
			citizen = request.mobile_verified
			add_photo_comment(photo_id=pk,photo_owner_id=photo_owner_id,latest_comm_text=description,latest_comm_writer_id=user_id,\
				latest_comm_av_url=url,latest_comm_writer_uname=username, exists=exists, citizen = citizen,time=comment_time)
			unseen_comment_tasks.delay(user_id, pk, comment_time, photocomment.id, photo_comment_count, description, exists, \
				username, url, citizen)
			if user_id != photo_owner_id:
				home_photo_tasks.delay(text=description, replier_id=user_id, time=comment_time, photo_owner_id=photo_owner_id,photo_id=pk)
			if origin:
				if origin == '0':
					return redirect("photo")
				elif origin == '1':
					if lang == 'urdu' and sort_by == 'best':
						return redirect("ur_home_best", 'urdu')
					elif sort_by == 'best':
						return redirect("home_best")
					elif lang == 'urdu':
						return redirect("ur_home", 'urdu')
					else:
						return redirect("home")
				elif origin == '2':
					return redirect("best_photo")
				else:
					return redirect("best_photo")
			else:
				return redirect("unseen_activity", username)
		else:
			if origin:
				request.session["notif_form"] = form
				request.session.modified = True
				if origin == '0':
					return redirect("photo")
				elif origin == '1':
					if lang == 'urdu' and sort_by == 'best':
						return redirect("ur_home_best", 'urdu')
					elif sort_by == 'best':
						return redirect("home_best")
					elif lang == 'urdu':
						return redirect("ur_home", 'urdu')
					else:
						return redirect("home")
				elif origin == '2':
					return redirect("best_photo")
				else:
					return redirect("best_photo")
			else:
				notification = "np:"+str(request.user.id)+":0:"+str(pk)
				page_obj, oblist, forms, page_num, addendum = get_object_list_and_forms(request, notification)
				url = reverse_lazy("unseen_activity", args=[username])+addendum
				forms[pk] = form
				request.session["forms"] = forms
				request.session["oblist"] = oblist
				request.session["page_obj"] = page_obj
				request.session.modified = True
				return redirect(url)
	else:
		return redirect("unseen_activity", username)

#called when replying from unseen_activity
@csrf_protect
@ratelimit(rate='3/s')
def unseen_reply(request, pk=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# UserProfile.objects.filter(user_id=own_id).update(score=F('score')-100)
		# return render(request, 'penalty_publicreply.html', {'penalty':100,'uname':own_uname})
		return redirect("missing_page")
	elif request.user_banned:
		return render(request,"500.html",{})
	own_id = request.user.id
	own_uname = request.user.username
	if request.method == 'POST':
		link_writer_id, origin = request.POST.get("lwpk",None), request.POST.get("origin",None)
		banned_by, ban_time = is_already_banned(own_id=own_id,target_id=link_writer_id, return_banner=True)
		if banned_by:
			request.session["banned_by"] = banned_by
			request.session["ban_time"] = ban_time
			if origin == '1':
				request.session["where_from"] = 'home'
			elif origin == '0':
				request.session["where_from"] = 'photos'
			elif origin == '2':
				request.session["where_from"] = 'best_photos'
			else:
				request.session["where_from"] = 'matka'
			request.session["own_uname"] = own_uname
			request.session.modified = True
			return redirect("ban_underway")
		lang, sort_by = request.POST.get("lang",None), request.POST.get("sort_by",None)
		form = UnseenActivityForm(request.POST,user_id=own_id,prv_grp_id='',pub_grp_id='',link_id=pk,photo_id='',per_grp_id='')
		if form.is_valid():
			text = form.cleaned_data.get("home_comment")
			target = process_publicreply(request=request,link_id=pk,text=text,origin=origin if origin else 'from_unseen',\
				link_writer_id=link_writer_id)
			set_input_rate_and_history.delay(section='home_rep',section_id=pk,text=text,user_id=own_id,time_now=time.time())
			if target == ":":
				return redirect("ban_underway")
			elif origin:
				if origin == '0':
					return redirect("photo")
				elif origin == '1':
					if lang == 'urdu' and sort_by == 'best':
						return redirect("ur_home_best", 'urdu')
					elif sort_by == 'best':
						return redirect("home_best")
					elif lang == 'urdu':
						return redirect("ur_home", 'urdu')
					else:
						return redirect("home")
				elif origin == '2':
					return redirect("best_photo")
				else:
					return redirect("home")
			else:
				return redirect("unseen_activity", own_uname)
		else:
			if origin:
				request.session["notif_form"] = form
				request.session.modified = True
				if origin == '0':
					return redirect("photo")
				elif origin == '1':
					if lang == 'urdu' and sort_by == 'best':
						return redirect("ur_home_best", 'urdu')
					elif sort_by == 'best':
						return redirect("home_best")
					elif lang == 'urdu':
						return redirect("ur_home", 'urdu')
					else:
						return redirect("home")
				elif origin == '2':
					return redirect("best_photo")
				else:
					return redirect("home")
			else:
				notification = "np:"+str(own_id)+":2:"+str(pk)
				page_obj, oblist, forms, page_num, addendum = get_object_list_and_forms(request, notification)
				url = reverse_lazy("unseen_activity", args=[own_uname,])+addendum
				forms[pk] = form
				request.session["forms"] = forms
				request.session["oblist"] = oblist
				request.session["page_obj"] = page_obj
				request.session.modified = True
				return redirect(url)
	else:
		return redirect("unseen_activity", own_uname)

def get_object_list_and_forms(request, notif=None):
	notifications = retrieve_unseen_notifications(request.user.id)
	if notif:
		try:
			index = notifications.index(notif)
		except:
			index = 0
		page_num, addendum = get_addendum(index,ITEMS_PER_PAGE)
	else:
		addendum = '?page=1#section0'
		page_num = request.GET.get('page', '1')
	page_obj = get_page_obj(page_num, notifications, ITEMS_PER_PAGE)
	if page_obj.object_list:
		oblist = retrieve_unseen_activity(page_obj.object_list)
	else:
		oblist = []
	forms = {}
	for obj in oblist:
		forms[obj['oi']] = UnseenActivityForm()
	return page_obj, oblist, forms, page_num, addendum


# @ratelimit(rate='22/38s')
@ratelimit(rate='3/s')
def unseen_activity(request, slug=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# context = {'penalty':300}
		# UserProfile.objects.filter(user=request.user).update(score=F('score')-300) #punish the spammer
		# return render(request, 'penalty_matka.html', context)
		return redirect("missing_page")
	else:
		user_id = request.user.id
		if first_time_inbox_visitor(user_id):
			add_inbox(user_id)
			context={'username':request.user.username}
			return render(request, 'inbox_tutorial.html', context)
		else:
			if 'forms' in request.session and 'oblist' in request.session and 'page_obj' in request.session:
				if request.session['forms'] and request.session['oblist'] and request.session['page_obj']:
					page_obj = request.session["page_obj"]
					oblist = request.session["oblist"]
					forms = request.session["forms"]
				else:
					page_obj, oblist, forms, page_num, addendum = get_object_list_and_forms(request)
				del request.session["forms"]
				del request.session["oblist"]
				del request.session["page_obj"]
			else:
				page_obj, oblist, forms, page_num, addendum = get_object_list_and_forms(request)
			secret_key = uuid.uuid4()
			set_text_input_key(user_id, '1', 'home', secret_key)
			if oblist:
				last_visit_time = float(prev_unseen_activity_visit(user_id))-SEEN[False]
				context = {'object_list': oblist, 'verify':FEMALES, 'forms':forms, 'page':page_obj,'nickname':request.user.username,\
				'last_visit_time':last_visit_time,'sk':secret_key,'user_id':user_id}
				if request.is_feature_phone or request.is_phone or request.is_mobile:
					context["is_mob"] = True
				return render(request, 'user_unseen_activity.html', context)
			else:
				context = {'object_list': oblist, 'page':page_obj,'nickname':request.user.username,'sk':secret_key,'user_id':user_id}
				return render(request, 'user_unseen_activity.html', context)

def unseen_help(request,*args,**kwargs):
	context={'nickname':request.user.username}
	return render(request,'photo_for_fans_help.html',context)

def top_photo_help(request,*args,**kwargs):
	context={'rank':None}
	return render(request,'top_photo_help.html',context)

@csrf_protect
def unseen_fans(request,pk=None,*args, **kwargs):
	if request.method == 'POST':
		photo_url = request.POST.get("photo_url")
		fan_num = request.POST.get("fan_num")
		fan_list = request.POST.get("fan_list")
		fan_list = fan_list[1:-1] #removing '[' and ']' from the result
		fan_list = fan_list.split(", ") #tokenzing values from remaining string
		fan_list = User.objects.select_related('userprofile').filter(id__in=fan_list)
		context={'fan_list':fan_list,'photo_url':photo_url,'fan_num':fan_num,'nickname':request.user.username}
		return render(request,'which_fans.html',context)
	else:
		return redirect("unseen_activity",request.user.username)


def public_reply_view(request,*args,**kwargs):
	context, user_id = {}, request.user.id
	if request.method == "POST":
		from_refresh = request.POST.get("from_rfrsh",None)
		link_id = request.POST.get("lid",None)
		request.session["link_pk"] = link_id
		request.session.modified = True
		if from_refresh == '1' and first_time_refresher(user_id):
			add_refresher(user_id)
			return render(request, 'jawab_refresh.html', {'lid':link_id})
	else:
		link_id = request.session.pop("link_pk",None)
	if link_id:
		link = Link.objects.select_related('submitter__userprofile').get(id=link_id)
		form = request.session.pop("publicreply_form",None)
		secret_key = uuid.uuid4()
		set_text_input_key(user_id, link_id, 'home_rep', secret_key)
		context["sk"] = secret_key
		context["form"] = form if form else PublicreplyForm() 
		context["error"] = False
		context["authenticated"] = True
		score = request.user.userprofile.score
		context["score"] = score
		context["parent"] = link #the parent link
		context["parent_submitter_username"] = link.submitter.username 
		context["ensured"] = FEMALES
		context["feature_phone"] = True if request.is_feature_phone else False
		context["random"] = random.sample(xrange(1,188),15) #select 15 random emoticons out of 188
		replies = Publicreply.objects.select_related('submitted_by__userprofile','answer_to').\
		defer('answer_to__net_votes','answer_to__url','answer_to__cagtegory','answer_to__image_file','answer_to__rank_score','answer_to__is_visible',\
			'answer_to__device','answer_to__which_photostream','submitted_by__userprofile__media_score','submitted_by__userprofile__shadi_shuda',\
			'submitted_by__userprofile__age','submitted_by__userprofile__gender','submitted_by__userprofile__bio','submitted_by__userprofile__streak',\
			'submitted_by__userprofile__previous_retort','submitted_by__userprofile__attractiveness','submitted_by__userprofile__mobilenumber',\
			'category','device','seen','submitted_by__is_superuser','submitted_by__first_name','submitted_by__last_name','submitted_by__last_login',\
			'submitted_by__email','submitted_by__date_joined','submitted_by__is_staff','submitted_by__is_active','submitted_by__password').\
			filter(answer_to=link).order_by('-id')[:25]
		context["replies"] = replies
		if request.user_banned:
			context["unseen"] = False
			context["reply_time"] = None
		elif replies:
			updated = update_notification(viewer_id=user_id, object_id=link_id, object_type='2', seen=True, \
				updated_at=time.time(), single_notif=False, unseen_activity=True,priority='home_jawab',bump_ua=False)
			if updated:
				context["unseen"] = True
				try:
					# calculating the max 'own reply' time
					context["reply_time"] = max(reply.submitted_on for reply in replies if reply.submitted_by_id == user_id)
				except:
					context["reply_time"] = None
			else:
				context["unseen"] = False
				context["reply_time"] = None
		else:
			context["unseen"] = False
			context["reply_time"] = None
		return render(request,"reply.html",context)
	else:
		context["from_publicreply"] = True
		return render(request,"dont_click_again_and_again.html",context)


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
@ratelimit(rate='3/s')
# @ratelimit(field='user_id',ip=False,rate='22/38s')
def post_public_reply(request,*args,**kwargs):
	was_limited, context = getattr(request, 'limits', False), {}
	if was_limited:
		# context = {'penalty':300}
		# UserProfile.objects.filter(user=request.user).update(score=F('score')-300) #punish the spammer
		# return render(request, 'penalty_homejawab.html', context)
		return redirect("missing_page")
	elif request.user_banned:
		return render(request,'500.html',{})
	elif request.method == "POST":
		link_id = request.POST.get("link_id")
		link_writer_id = request.POST.get("lwpk")
		user_id = request.user.id
		banned_by, ban_time = is_already_banned(own_id=user_id,target_id=link_writer_id, return_banner=True)
		if banned_by:
			request.session["banned_by"] = banned_by
			request.session["ban_time"] = ban_time
			request.session["where_from"] = 'home'
			request.session.modified = True
			return redirect("ban_underway")
		else:
			##############################################################################################
			##############################################################################################
			# config_manager.get_obj().track('wrote_publicreply', user_id)
			##############################################################################################
			##############################################################################################
			form = PublicreplyForm(request.POST,user_id=user_id, link_id=link_id)
			if form.is_valid():
				text = form.cleaned_data["description"]
				set_input_rate_and_history.delay(section='home_rep',section_id=link_id,text=text,user_id=user_id,time_now=time.time())
				target = process_publicreply(request=request,link_id=link_id,text=text, link_writer_id=link_writer_id)
				if target == ":":
					return redirect("ban_underway")
				request.session["link_pk"] = link_id
				request.session.modified = True
			else:
				request.session["publicreply_form"] = form
				request.session["link_pk"] = link_id
				request.session.modified = True
			return redirect("publicreply_view")
	else:
		context["from_publicreply"] = True
		return render(request,"dont_click_again_and_again.html",context)


class UserActivityView(ListView):
	model = Link
	slug_field = "username"
	template_name = "user_activity.html"
	paginate_by = 20

	def get_queryset(self):
		username = self.kwargs['slug']
		try:
			user = User.objects.get(username=username)
			return Link.objects.select_related('submitter__userprofile').filter(submitter=user).order_by('-id')[:200] if username == self.request.user.username else Link.objects.select_related('submitter__userprofile').filter(submitter=user).order_by('-id')[:40]
		except:
			return []

	def get_context_data(self, **kwargs):
		context = super(UserActivityView, self).get_context_data(**kwargs)
		context["can_vote"] = False
		if self.request.user.is_authenticated():
			if self.request.user_banned:# and (self.request.user.username ==  self.kwargs['slug']):
				context["banned"] = True
			else:
				if self.request.user.userprofile.score > 9:
					context["can_vote"] = True
				context["verified"] = FEMALES
				context["ident"] = self.request.user.id
				context["username"] = self.kwargs['slug']
		return context

class UserSettingDetailView(DetailView):
	model = get_user_model()
	slug_field = "username"
	template_name = "user_detail.html"

	def get_object(self, queryset=None):
		user = super(UserSettingDetailView, self).get_object(queryset)
		UserSettings.objects.get_or_create(user=user)
		return user



class PhotoQataarHelpView(FormView):
	form_class = PhotoQataarHelpForm
	template_name = "photo_qataar.html"

	def get_context_data(self, **kwargs):
		context = super(PhotoQataarHelpView, self).get_context_data(**kwargs)
		context["key"] = self.kwargs["pk"]
		return context

class BaqiPhotosHelpView(FormView):
	form_class = BaqiPhotosHelpForm
	template_name = "baqi_photos_help.html"

	def get_context_data(self, **kwargs):
		context = super(BaqiPhotosHelpView, self).get_context_data(**kwargs)
		context["key"] = self.kwargs["pk"]
		return context


class UserProfileEditView(UpdateView):
	model = UserProfile
	form_class = UserProfileForm
	template_name = "edit_profile.html"

	def get_initial(self):#initial is a keyword argument to a formfield that enables pre-filling in the formfield
		"""
		Returns the initial data to use for forms on this view.
		"""
		return {'bio': 'Jb mein teen saal ka tha toh sr ke bl gir gaya tha. Tb se aisa hoon...'} #initial needs to be passed a dictionary

	def get_form_kwargs(self):
		"""
		Returns the keyword arguments for instantiating the form.
		"""
		kwargs = super(UserProfileEditView, self).get_form_kwargs()
		kwargs.update({'user': self.request.user})
		return kwargs

	def get_object(self, queryset=None):
		return UserProfile.objects.get_or_create(user=self.request.user)[0]

	def get_success_url(self):
		return reverse_lazy("profile", kwargs={'slug': self.request.user})


class UserSettingsEditView(UpdateView):
	model = UserSettings
	form_class = UserSettingsForm
	template_name = "edit_settings.html"

	def get_object(self, queryset=None): #loading the current state of settings
		return UserSettings.objects.get_or_create(user=self.request.user)[0]

	def get_success_url(self): #which URL to go back once settings are saved?
		return reverse_lazy("profile", kwargs={'slug': self.request.user})

@ratelimit(rate='3/s')
def link_create_pk(request, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		return redirect("missing_page")
	else:
		request.session["link_create_token"] = uuid.uuid4()
		return redirect("link_create")

class LinkCreateView(CreateView):
	model = Link
	form_class = LinkForm

	def get_form_kwargs( self ):
		kwargs = super(LinkCreateView,self).get_form_kwargs()
		kwargs['user_id'] = self.request.user.id
		return kwargs

	def get_context_data(self, **kwargs):
		context = super(LinkCreateView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			secret_key = uuid.uuid4()
			context["sk"] = secret_key
			set_text_input_key(self.request.user.id, '1', 'likho', secret_key)
			context["random"] = random.sample(xrange(1,188),15) #select 15 random emoticons out of 188		
			if self.request.is_feature_phone:
				context["feature_phone"] = True
			else:
				context["feature_phone"] = False
		return context

	# def form_invalid(self, form):
	# 	"""
	# 	If the form is invalid, re-render the context data with the
	# 	data-filled form and errors.
	# 	"""
	# 	description = self.request.POST.get("description",None)
	# 	description = 'specificity' if description == '' else description
	# 	error_string = str(dict(form.errors)["description"]).split('<li>')[1].split('</li>')[0]
	# 	log_erroneous_passwords(description,error_string)
	# 	return self.render_to_response(self.get_context_data(form=form))

	def form_valid(self, form): #this processes the form before it gets saved to the database
		token = self.request.session.get("link_create_token",None)
		self.request.session["link_create_token"] = None
		self.request.session.modified = True
		user = self.request.user
		user_id = user.id
		mobile_verified = self.request.mobile_verified
		if not mobile_verified:
			CSRF = csrf.get_token(self.request)
			temporarily_save_user_csrf(str(user_id), CSRF)
			return render(self.request, 'cant_write_on_home_without_verifying.html', {'csrf':CSRF})
		else:
			if valid_uuid(str(token)) and mobile_verified:
				f = form.save(commit=False) #getting form object, and telling database not to save (commit) it just yet
				set_input_rate_and_history.delay(section='home',section_id='1',text=f.description,user_id=user_id,time_now=time.time())
				f.rank_score = 10.1#round(0 * 0 + secs / 45000, 8)
				if user.userprofile.score < -25:
					if not HellBanList.objects.filter(condemned_id=user_id).exists(): #only insert user in hell-ban list if she isn't there already
						HellBanList.objects.create(condemned_id=user_id) #adding user to hell-ban list
						user.userprofile.score = random.randint(10,71)
						f.submitter = user
					else:
						f.submitter = user # ALWAYS set this ID to unregistered_bhoot
				else:
					f.submitter = user
					f.submitter.userprofile.score = f.submitter.userprofile.score + 1 #adding 1 point every time a user submits new content
				if self.request.is_feature_phone:
					f.device = '1'
				elif self.request.is_phone:
					f.device = '2'
				elif self.request.is_tablet:
					f.device = '4'
				elif self.request.is_mobile:
					f.device = '5'
				else:
					f.device = '3'
				try:
					av_url = user.userprofile.avatar.url
				except ValueError:
					av_url = None
				if is_urdu(text=f.description):
					category = '17'
				else:
					category = '1'
				f.cagtegory = category
				f.save()
				add_home_link(link_pk=f.id, categ=category, nick=user.username, av_url=av_url, desc=f.description, \
					scr=f.submitter.userprofile.score, cc=0, writer_pk=user_id, device=f.device, \
					by_pinkstar = (True if user.username in FEMALES else False))
				if self.request.user_banned:
					extras = add_unfiltered_post(f.id)
					if extras:
						queue_for_deletion.delay(extras)
				else:
					add_filtered_post(f.id, is_ur=True if category == '17' else False)
					extras = add_unfiltered_post(f.id)
					if extras:
						queue_for_deletion.delay(extras)
				f.submitter.userprofile.save()
				##############################################################################################
				##############################################################################################
				# config_manager.get_obj().track('wrote_onhome', user_id)
				##############################################################################################
				##############################################################################################
				return super(CreateView, self).form_valid(form) #saves the link automatically
			else:
				return redirect("home")

	def get_success_url(self): #which URL to go back once settings are saved?
		return reverse_lazy("home")


def del_public_group(request, pk=None, unique=None, private=None, *args, **kwargs):
	group = Group.objects.get(id=pk)
	member_ids = list(User.objects.filter(username__in=get_group_members(pk)).values_list('id',flat=True))
	if group.owner == request.user:
		remove_group_notification(user_id=request.user.id,group_id=pk)
		del_from_rankings(pk)
		del_attendance(pk)
		remove_group_object(pk)
		remove_all_group_members(pk)
		remove_latest_group_reply(pk)
		remove_group_for_all_members(pk,member_ids)
		GroupBanList.objects.filter(which_group_id=pk).delete()
		GroupCaptain.objects.filter(which_group_id=pk).delete()
		Group.objects.get(id=pk).delete()
		return redirect("group_page")
	else:
		context={'private':'0','unique':unique}
		return render(request,'penalty_groupbanned.html', context)


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def left_public_group(request, *args, **kwargs):
	if request.method == "POST":
		pk = request.POST.get("pk",None)
		inside_group = request.POST.get("igrp",None)
		unique = request.POST.get("slug",None)
		leaving_decision = request.POST.get("ldec",None)
		if leaving_decision == '1':
			username = request.user.username
			user_id = request.user.id
			if check_group_member(pk, username):
				remove_group_member(pk, username)
				remove_user_group(user_id, pk)
				remove_group_notification(user_id,pk)
			elif check_group_invite(user_id, pk):
				remove_group_invite(user_id, pk)
			else:
				pass
			return redirect("group_page")
		else:
			if inside_group == '1':
				return redirect("public_group", slug=unique)
			else:
				return redirect("group_page")
	return redirect("group_page")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def kick_pk(request, *args, **kwargs):
	if request.user_banned:
		return redirect("missing_page")
	elif request.method == "POST":
		kick_decision = request.POST.get("kdec",None)
		decision = request.POST.get("dec",None)
		slug = request.POST.get("slug",None)
		writer_id = request.POST.get("pk",None)
		if decision == 'rem':
			context = {}
			context["unique"] = slug
			group = Group.objects.get(unique=slug)
			context["unauthorized"] = False
			if group.private != '0':
				context["unauthorized"] = True
			context["owner"] = group.owner
			if group.owner != request.user:
				context["culprit"] = request.user
			else:
				if Reply.objects.filter(writer_id=writer_id,which_group=group).exists():
					culprit_username = User.objects.filter(id=writer_id).values_list('username',flat=True)[0]
					context["culprit_username"] = culprit_username
					context["pk"] = writer_id
				else:
					context["unauthorized"] = True
			return render(request,"kick.html",context)
		elif kick_decision == '1':
			if request.user.userprofile.score < -25:
				HellBanList.objects.create(condemned=request.user)
				request.user.userprofile.score = random.randint(10,71)
				request.user.userprofile.save()
				return redirect("group_page")
			else:
				try:
					group = Group.objects.get(unique=slug)
				except Group.DoesNotExist:
					return redirect("group_page")
				if group.private == '0':
					if group.owner != request.user:
						return redirect("public_group", slug=slug)
					elif writer_id == str(request.user.id):
						return redirect("public_group", slug=slug)
					else:
						group_id = group.id
						culprit_username = User.objects.filter(id=writer_id).values_list('username',flat=True)[0]
						is_member = check_group_member(group_id, culprit_username)
						recently_online_ids = get_attendance(group_id)
						if not is_member and writer_id not in recently_online_ids:
							return redirect("public_group", slug=slug)	
						if GroupBanList.objects.filter(which_user_id=writer_id, which_group_id=group_id).exists():# already kicked and banned
							return redirect("public_group", slug=slug)
						else:
							GroupBanList.objects.create(which_user_id=writer_id,which_group_id=group_id)#placing the person in ban list
							try:
								GroupCaptain.objects.get(which_user_id=writer_id, which_group_id=group_id).delete()
							except:
								pass
							if is_member:
								remove_group_member(group_id, culprit_username)
								remove_group_notification(writer_id,group_id)
								remove_user_group(writer_id, group_id)
								UserProfile.objects.filter(user_id=writer_id).update(score=F('score')-50) #punish the kickee
							elif check_group_invite(writer_id, group_id):
								remove_group_invite(writer_id, group_id)
							reply = Reply.objects.create(text=culprit_username, which_group_id=group_id, writer=request.user, category='2')
							return redirect("public_group", slug=slug)
				else:
					return redirect("group_page")			
		else:
			return redirect("public_group", slug=slug)
	else:
		return redirect("group_page")



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def groupreport_pk(request, *args, **kwargs):	
	if request.method == 'POST':
		pk = request.POST.get("pk",None)
		slug = request.POST.get("slug",None)
		decision = request.POST.get("dec",None)
		report_decision = request.POST.get("repdec",None)
		if decision == 'rep':
			context = {}
			try:
				context["unique"] = slug
				reply_id = pk
				group = Group.objects.get(unique=slug)
			except:
				context["captain"] = False
				context["unique"] = None
				context["reply"] = None
			if GroupCaptain.objects.filter(which_user=request.user, which_group=group).exists() and Reply.objects.filter(pk=pk, which_group=group).exists():
				context["captain"] = True
				context["reply_pk"] = pk
			else:
				context["captain"] = False
			return render(request,"group_report.html",context)
		elif report_decision == '1':
			try:
				group = Group.objects.get(unique=slug)
			except:
				return redirect("home")
			if group.private != '0' or request.user_banned:
				return redirect("missing_page")
			elif GroupBanList.objects.filter(which_user_id=request.user.id, which_group=group).exists():
				return redirect("group_page")
			elif request.user.userprofile.score < -25:
				HellBanList.objects.create(condemned=request.user)
				request.user.userprofile.score = random.randint(10,71)
				request.user.userprofile.save()
				return redirect("group_page")
			else:
				reply = get_object_or_404(Reply, pk=pk)
				if not GroupCaptain.objects.filter(which_user=request.user, which_group=group).exists() or reply.text == request.user.username \
				or reply.which_group_id != group.id:
					# not allowed
					pass
				elif reply.category == '3':
					# already hidden
					pass
				else: #i.e. the person requesting this is a group captain
					reply.category = '3'
					reply.text = request.user.username
					reply.writer.userprofile.score = reply.writer.userprofile.score - 5
					reply.writer.userprofile.save()
					reply.save()
				return redirect("public_group", slug=group.unique)
		else:
			return redirect("public_group", slug=slug)
	else:
		return redirect("home")



class ReportView(FormView):
	form_class = ReportForm

	def form_valid(self, form):
		if self.request.method == 'POST':
			if not self.request.user_banned:
				rprt = self.request.POST.get("report")
				if rprt == 'Haan':
					reply_id = self.request.POST.get("reply")
					link_id = self.request.POST.get("link")
					if Publicreply.objects.filter(pk=reply_id,answer_to=link_id, abuse=False).exists() and \
					Link.objects.filter(pk=link_id,submitter=self.request.user).exists():
						reply = get_object_or_404(Publicreply, pk=reply_id)
						reply.abuse = True
						reply.save()
						pk = reply.submitted_by_id
						UserProfile.objects.filter(user_id=pk).update(score=F('score')-3)
						self.request.session["report_pk"] = None
						self.request.session["linkreport_pk"] = None
						ident = self.request.user.id
						if pk != ident:
							document_publicreply_abuse(pk)
						self.request.session["link_pk"] = reply.answer_to.id
						self.request.session.modified = True
						return redirect("publicreply_view")
					else:
						UserProfile.objects.filter(user=self.request.user).update(score=F('score')-3)
						return redirect("home")
				else:
					link_id = self.request.POST.get("link")
					link = get_object_or_404(Link, pk=link_id)
					self.request.session["report_pk"] = None
					self.request.session["linkreport_pk"] = None
					self.request.session["link_pk"] = link.id
					self.request.session.modified = True
					return redirect("publicreply_view")
			else:
				return render(self.request,'500.html',{})

def welcome_reply(request,*args,**kwargs):
	if request.user_banned:
		return render(request,'500.html',{})
	else:
		if request.method == 'POST':
			user = request.user
			username = request.user.username
			try:
				pk = request.session["welcome_pk"]
				del request.session["welcome_pk"]
				target = User.objects.get(pk=pk)
			except:
				return redirect("profile", slug=username)
			current = User.objects.latest('id')
			num = current.id
			if (num-100) <= int(pk) <= (num+100):
				option = request.POST.get("opt")
				message = request.POST.get("msg")
				if request.is_feature_phone:
					device = '1'
				elif request.is_phone:
					device = '2'
				elif request.is_tablet:
					device = '4'
				elif request.is_mobile:
					device = '5'
				else:
					device = '3'
				request.user.userprofile.score = request.user.userprofile.score + 1
				request.user.userprofile.save()
				try:
					av_url = target.userprofile.avatar.url
				except:
					av_url = None
				if Link.objects.filter(submitter=target).exists():
					parent = Link.objects.filter(submitter=target).latest('id')
					parent.reply_count = parent.reply_count + 1
				else:
					num = random.randint(1,len(SALUTATIONS))
					parent = Link.objects.create(description=SALUTATIONS[num-1], submitter=target, reply_count=1, device=device)
					add_home_link(link_pk=parent.id, categ='1', nick=target.username, av_url=av_url, desc=SALUTATIONS[num-1], \
						scr=target.userprofile.score, cc=0, writer_pk=target.id, device=device, \
						by_pinkstar=(True if target.username in FEMALES else False))
					add_filtered_post(parent.id)
					extras = add_unfiltered_post(parent.id)
					if extras:
						queue_for_deletion.delay(extras)
				if option == '1' and message == 'Barfi khao aur mazay urao!':
					description = target.username+" welcum damadam pe! Kiya hal hai? Barfi khao aur mazay urao (barfi)"
					reply = Publicreply.objects.create(submitted_by=user, answer_to=parent, description=description, device=device)
				elif option == '1' and message == 'Yeh zalim barfi try kar yar!':
					description = target.username+" welcome! Kesey ho? Yeh zalim barfi try kar yar (barfi)"
					reply = Publicreply.objects.create(submitted_by=user, answer_to=parent, description=description, device=device)
				elif option == '1' and message == 'Is barfi se mu meetha karo!':
					description = target.username+" assalam-u-alaikum! Is barfi se mu meetha karo (barfi)"
					reply = Publicreply.objects.create(submitted_by=user, answer_to=parent, description=description, device=device)
				elif option == '2' and message == 'Aik plate laddu se life set!':
					description = target.username+" Damadam pe welcome! One plate laddu se life set (laddu)"
					reply = Publicreply.objects.create(submitted_by=user, answer_to=parent, description=description, device=device)
				elif option == '2' and message == 'Ye saray laddu aap ke liye!':
					description = target.username+" kya haal he? Ye laddu aap ke liye (laddu)"
					reply = Publicreply.objects.create(submitted_by=user, answer_to=parent, description=description, device=device)
				elif option == '2' and message == 'Laddu khao, jaan banao yar!':
					description = target.username+" welcum! Life set hei? Laddu khao, jaan banao (laddu)"
					reply = Publicreply.objects.create(submitted_by=user, answer_to=parent, description=description, device=device)
				elif option == '3' and message == 'Jalebi khao aur ayashi karo!':
					description = target.username+" welcomeee! Yar kya hal he? Jalebi khao aur ayashi karo (jalebi)"
					reply = Publicreply.objects.create(submitted_by=user, answer_to=parent, description=description, device=device)
				elif option == '3' and message == 'Jalebi meri pasandida hai!':
					description = target.username+" kaisey ho? Jalebi meri pasandida hai! Tumhari bhi? (jalebi)"
					reply = Publicreply.objects.create(submitted_by=user, answer_to=parent, description=description, device=device)
				elif option == '3' and message == 'Is jalebi se mu metha karo!':
					description = target.username+" salam! Is jalebi se mu meetha karo (jalebi)"
					reply = Publicreply.objects.create(submitted_by=user, answer_to=parent, description=description, device=device)
				else:
					return redirect("score_help")
				parent.latest_reply = reply
				parent.save()
				try:
					url = request.user.userprofile.avatar.url
				except ValueError:
					url = None
				time = convert_to_epoch(reply.submitted_on)
				amnt = update_comment_in_home_link(description,username,url,time,user.id,parent.id,(True if username in FEMALES else False))
				publicreply_notification_tasks.delay(link_id=parent.id,link_submitter_url=av_url,\
					sender_id=user.id,link_submitter_id=pk,link_submitter_username=target.username,\
					link_desc=parent.description,reply_time=time,reply_poster_url=url,\
					reply_poster_username=username,reply_desc=reply.description,is_welc=False,\
					reply_count=parent.reply_count,priority='home_jawab',from_unseen=False)
				return redirect("home")
			else:
				return render(request,'old_user.html',{'username':target.username})
		else:
			return render(request,'404.html',{})

def cross_group_notif(request,pk=None, uid=None,from_home=None, lang=None, sort_by=None, *args,**kwargs):
	update_notification(viewer_id=uid,object_id=pk, object_type='3',seen=True,unseen_activity=True, single_notif=False,\
		bump_ua=False)
	if from_home == '1':
		if lang == 'urdu' and sort_by == 'best':
			return redirect("ur_home_best", 'urdu')
		elif sort_by == 'best':
			return redirect("home_best")
		elif lang == 'urdu':
			return redirect("ur_home", 'urdu')
		else:
			return redirect("home")
	elif from_home == '2':
		return redirect("best_photo")
	# elif from_home == '5':
	# 	return redirect("see_special_photo")
	else:
		return redirect("photo")

def cross_comment_notif(request, pk=None, usr=None, from_home=None, object_type=None, lang=None, sort_by=None, *args, **kwargs):
	update_notification(viewer_id=usr, object_id=pk, object_type='0',seen=True, unseen_activity=True,\
		single_notif=False,bump_ua=False)
	if from_home == '1':
		if lang == 'urdu' and sort_by == 'best':
			return redirect("ur_home_best", 'urdu')
		elif sort_by == 'best':
			return redirect("home_best")
		elif lang == 'urdu':
			return redirect("ur_home", 'urdu')
		else:
			return redirect("home")
	elif from_home == '2':
		return redirect("best_photo")
	# elif from_home == '5':
	# 	return redirect("see_special_photo")
	else:
		return redirect("photo")

def cross_salat_notif(request, pk=None, user=None, from_home=None, lang=None, sort_by=None, *args, **kwargs):
	notif_name = "np:"+user+":"+pk.split(":",1)[1]
	hash_name = pk
	viewer_id = user
	delete_salat_notification(notif_name,hash_name,viewer_id)
	if from_home == '1':
		if lang == 'urdu' and sort_by == 'best':
			return redirect("ur_home_best", 'urdu')
		elif sort_by == 'best':
			return redirect("home_best")
		elif lang == 'urdu':
			return redirect("ur_home", 'urdu')
		else:
			return redirect("home")
	elif from_home == '2':
		return redirect("best_photo")
	# elif from_home == '5':
	# 	return redirect("see_special_photo")
	else:
		return redirect("photo")

def cross_notif(request, pk=None, user=None, from_home=None, lang=None, sort_by=None, *args, **kwargs):
	update_notification(viewer_id=user, object_id=pk, object_type='2',seen=True, unseen_activity=True,\
		single_notif=False, bump_ua=False)
	if from_home == '1':
		if lang == 'urdu' and sort_by == 'best':
			return redirect("ur_home_best", 'urdu')
		elif sort_by == 'best':
			return redirect("home_best")
		elif lang == 'urdu':
			return redirect("ur_home", 'urdu')
		else:
			return redirect("home")
	elif from_home == '2':
		return redirect("best_photo")
	# elif from_home == '5':
	# 	return redirect("see_special_photo")
	else:
		return redirect("photo")

@ratelimit(rate='3/s')
def video_vote(request, pk=None, val=None, usr=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# deduction = 3 * -1
		# request.user.userprofile.media_score = request.user.userprofile.media_score + deduction
		# request.user.userprofile.score = request.user.userprofile.score + deduction
		# request.user.userprofile.save()
		# context = {'unique': pk}
		# return render(request, 'penalty_videovote.html', context)
		return redirect("missing_page")
	else:
		video = Video.objects.get(id=pk)
		ident = video.owner.id
		if request.user.id == ident: #can't vote your own video
			context = {'unique': pk}
			return render(request, 'already_videovoted.html', context)
		else:
			added = add_vote_to_video(pk, request.user.username, val)
			if added:
				if int(val) > 0:
					vote_score_increase = 1
					visible_score_increase = 1
					media_score_increase = 1
					score_increase = 1
					video_vote_tasks.delay(pk, ident, vote_score_increase, visible_score_increase, media_score_increase, score_increase)
				else:
					vote_score_increase = -1
					visible_score_increase = -1
					media_score_increase = -1
					score_increase = -1
					video_vote_tasks.delay(pk, ident, vote_score_increase, visible_score_increase, media_score_increase, score_increase)
				return redirect("see_video")
			else:
				context = {'unique': pk}
				return render(request, 'already_videovoted.html', context)

def photostream_vote(request, pk=None, val=None, from_best=None, *args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		deduction = 3 * -1
		request.user.userprofile.media_score = request.user.userprofile.media_score + deduction
		request.user.userprofile.score = request.user.userprofile.score + deduction
		request.user.userprofile.save()
		context = {'unique': pk}
		return render(request, 'penalty_photovote.html', context)
	else:
		if pk.isdigit() and val.isdigit():
			if from_best == '5':
				ident = pk
				photo = Photo.objects.get(id=ident)
			else:
				# stream = PhotoStream.objects.get(id=pk)
				ident = stream.cover_id
				photo = Photo.objects.get(id=ident)
			if PhotoVote.objects.filter(voter=request.user, photo_id=ident).exists() or request.user == photo.owner:
				if from_best == '5':
					return redirect("see_photo_pk", ident)
				else:
					return redirect("see_photo_pk", ident)
			else:
				if val == '1':
						if request.user_banned:
							return redirect("score_help")
						else:
							PhotoVote.objects.create(voter=request.user, photo=photo, photo_owner=photo.owner, value=1)
							photo.visible_score = photo.visible_score + 1
							photo.vote_score = photo.vote_score + 1
							photo.owner.userprofile.media_score = photo.owner.userprofile.media_score + 1
							photo.owner.userprofile.score = photo.owner.userprofile.score + 1
							photo.owner.userprofile.save()
							photo.save()
				elif val == '0':
						if request.user_banned:
							return redirect("score_help")
						else:
							PhotoVote.objects.create(voter=request.user, photo=photo, photo_owner=photo.owner, value=-1)
							photo.visible_score = photo.visible_score - 1
							photo.vote_score = photo.vote_score -1
							photo.owner.userprofile.media_score = photo.owner.userprofile.media_score - 1
							photo.owner.userprofile.score = photo.owner.userprofile.score - 1
							photo.owner.userprofile.save()
							photo.save()
				else:
					if from_best == '1':
						request.session["target_best_photo_id"] = ident
						return redirect("best_photo_loc")
					elif from_best == '0':
						return redirect("see_photo_pk", ident)
					elif from_best == '5':
						return redirect("see_special_photo_pk", ident)
					else:
						request.session['target_id'] = int(from_best)
						return redirect("home_loc")
				if from_best == '1':
					request.session["target_best_photo_id"] = ident
					return redirect("best_photo_loc")
				elif from_best == '0':
					return redirect("see_photo_pk", ident)
				elif from_best == '5':
					return redirect("see_special_photo_pk", ident)
				else:
					request.session['target_id'] = int(from_best)
					return redirect("home_loc")
		else:
			if from_best == '1':
				request.session["target_best_photo_id"] = ident
				return redirect("best_photo_loc")
			elif from_best == '0':
				return redirect("see_photo_pk", ident)
			elif from_best == '5':
				return redirect("see_special_photo_pk", ident)
			else:
				request.session['target_id'] = int(from_best)
				return redirect("home_loc")

def salat_notification(request, pk=None, *args, **kwargs):
	now = datetime.utcnow()+timedelta(hours=5)
	epochtime = convert_to_epoch(now)
	cache_mem = get_cache('django.core.cache.backends.memcached.MemcachedCache', **{
		'LOCATION': MEMLOC, 'TIMEOUT': 70,
	})
	salat_timings = cache_mem.get('salat_timings')
	try:
		starting_time = datetime.combine(now.today(), salat_timings['current_namaz_start_time'])
	except:
		return redirect("salat_invite")
	if salat_timings['namaz'] =='Fajr':
		salat = '1'
	elif salat_timings['namaz'] =='Zuhr':
		salat = '2'
	elif salat_timings['namaz'] == 'Asr':
		salat = '3'
	elif salat_timings['namaz'] == 'Maghrib':
		salat = '4'
	elif salat_timings['namaz'] == 'Isha':
		salat = '5'
	else:
		return redirect("internal_salat_invite")
	try:
		latest_namaz = LatestSalat.objects.filter(salatee_id=pk).latest('when') #when did this person pray?
	except:
		#latest_namaz does not exist
		latest_namaz = None
	if pk.isdigit() and not SalatInvite.objects.filter(invitee_id=pk, which_salat=salat, sent_at__gte=starting_time).exists() and not AlreadyPrayed(latest_namaz,now):
		salat_object = SalatInvite.objects.create(inviter=request.user, invitee_id=pk, which_salat=salat, sent_at=now)
		salat_object_id = salat_object.id
		try:
			owner_url = request.user.userprofile.avatar.url
		except ValueError:
			owner_url = None
		create_object(object_id=salat_object_id,object_type='4',object_owner_name=request.user.username,\
			object_owner_avurl=owner_url,object_desc=salat_timings['namaz'], object_owner_id=request.user.id)
		create_notification(object_id=salat_object_id,object_type='4',viewer_id=pk,seen=False,updated_at=epochtime,\
			single_notif=True,priority='namaz_invite')
		viewer_salat_notifications(viewer_id=pk,object_id=salat_object_id, time=epochtime)
		return redirect("internal_salat_invite")
	else:
		user = User.objects.get(id=pk)
		context = {'invitee':user, 'namaz':salat_timings['namaz']}
		return render(request, 'salat_invite_error.html', context)

@ratelimit(rate='3/s')
def fan(request,*args,**kwargs):
	was_limited = getattr(request, 'limits', False)
	user_id = request.user.id
	if was_limited:
		# UserProfile.objects.filter(user_id=user_id).update(score=F('score')-50)
		# return redirect("best_photo")
		return redirect("missing_page")
	if request.method == "POST":
		origin, object_id, star_id = request.POST.get("org",None), request.POST.get("oid",None), request.POST.get("sid_btn",None)
		if int(user_id) == int(star_id):
			# penalize this user - she's trying to fan herself!
			UserProfile.objects.filter(user_id=user_id).update(score=F('score')-50)
			return render(request,'penalty_fan.html',{'unique':request.user.username})
		else:
			star = User.objects.get(id=star_id)
			star_username = star.username
			try:
				# allow unfanning even if never posted photo
				UserFan.objects.get(fan_id=user_id, star_id=star_id).delete()
				remove_from_photo_owner_activity(star_id, user_id)
			except:
				if never_posted_photo(user_id):
					# show "please first upload at least 1 photo" to be eligible for becomming a fan
					return render(request, 'fan_requirement.html', {'unique': request.user.username})
				else:
					#if not shown tutorial of what 'fan' is, show tutorial
					if first_time_fan(user_id):
						# show fan tutorial first, then do the rest
						add_fan(user_id) #adding fan tutorial flag
						context = {'star_id': star_id,'obj_id':object_id,'origin':origin,'name':star_username}
						return render(request, 'fan_tutorial.html', context)
					else:
						banned_by, ban_time = is_already_banned(own_id=user_id,target_id=star_id, return_banner=True)
						if banned_by:
							request.session["where_from"] = 'fan'
							request.session["banned_by_yourself"] = banned_by == str(user_id)
							request.session["target_username"] = star_username
							request.session["ban_time"] = ban_time
							request.session.modified = True
							return redirect("ban_underway") 
						UserFan.objects.create(fan_id=user_id,star_id=star_id,fanning_time=datetime.utcnow()+timedelta(hours=5))
						add_to_photo_owner_activity(star_id, user_id, new=True)
			"""
			origin codes:
				(un)fanned from starlist: '0'
				(un)fanned from starprofile: '1'
				(un)fanned from fresh photos: '2'
				(un)fanned from best photos: '3'
				(un)fanned from home: '4'
			"""
			if origin == '0':
				return redirect("star_list")
			elif origin == '1':
				return redirect("profile", star_username)
			elif origin == '2':
				request.session["target_photo_id"] = object_id
				request.session.modified = True
				return redirect("photo_loc")
			elif origin == '3':
				request.session["target_best_photo_id"] = object_id
				request.session.modified = True
				return redirect("best_photo_loc")
			elif origin == '4':
				request.session['target_id'] = object_id
				request.session.modified = True
				return redirect("home_loc")
			else:
				return redirect("home")
	else:
		return redirect("missing_page")

class SalatTutorialView(FormView):
	form_class = SalatTutorialForm
	template_name = "salat_tutorial.html"

	def form_valid(self, form):
		if self.request.method == 'POST':
			try:
				choice = self.request.POST.get("choice")
				TutorialFlag.objects.filter(user=self.request.user).update(seen_salat_option=True)
				return redirect("process_salat")
			except:
				TutorialFlag.objects.filter(user=self.request.user).update(seen_salat_option=True)
				return redirect("process_salat")
		else:
			TutorialFlag.objects.filter(user=self.request.user).update(seen_salat_option=True)
			return redirect("home")


def process_photo_vote(pk, ident, val, voter_id):
	if int(val) > 0:
		vote_score_increase = 1
		visible_score_increase = 1
		media_score_increase = 1
		score_increase = 1
		photo_vote_tasks.delay(pk, ident, vote_score_increase, visible_score_increase, media_score_increase, score_increase, voter_id)
	else:
		vote_score_increase = -1
		visible_score_increase = -1
		media_score_increase = -1
		score_increase = -1
		photo_vote_tasks.delay(pk, ident, vote_score_increase, visible_score_increase, media_score_increase, score_increase, voter_id)

@csrf_protect
def cast_photo_vote(request,*args,**kwargs):
	if request.method == 'POST':
		if request.user_banned:
			return redirect("missing_page")
		own_id = request.user.id
		mob_verified = request.mobile_verified
		if not mob_verified:
			CSRF = csrf.get_token(request)
			temporarily_save_user_csrf(str(own_id), CSRF)
			return render(request, 'cant_vote_without_verifying.html', {'csrf':CSRF})
		elif mob_verified:
			photo_id = request.POST.get("pid","")
			photo_owner_id = get_photo_owner(photo_id)
			if not photo_owner_id:
				photo_owner_id = Photo.objects.get(id=photo_id).owner.id
			if photo_id and photo_owner_id:
				own_username = request.user.username
				banned_from_voting,time_remaining = check_photo_vote_ban(own_id) #was this person banned by a defender?
				cool_down_time, can_vote = can_vote_on_photo(own_id) #defenders are exempt from timing out currently
				origin = request.POST.get("from","")
				if str(own_id) == photo_owner_id:
					# voted own photo - dismiss
					return render(request,'penalty_self_photo_vote.html')
				elif not can_vote:
					# needs to cool down
					context={'time_remaining':cool_down_time, 'origin':origin, 'pk':photo_id, 'slug':request.POST.get("oun",""),\
					'lid':request.POST.get("lid","")}
					return render(request, 'photovote_cooldown.html', context)
				elif banned_from_voting:
					# not allowed to vote - notify
					to_go = ('-1' if time_remaining == '-1' else timezone.now()+timedelta(seconds=time_remaining))
					context = {'time_remaining':to_go,'origin':origin, 'pk':photo_id, 'slug':request.POST.get("oun",""),\
					'lid':request.POST.get("lid","")}
					return render(request, 'photovote_disallowed.html', context)
				elif voted_for_single_photo(photo_id,own_username):
					# double voted photo - dismiss
					return render(request,'already_photovoted.html')
				else:
					#process the vote
					# reset_best_photos_cache.delay(photo_id)
					value = request.POST.get("photo_vote","")
					citizen = request.mobile_verified
					if value == '1':
						added = add_vote_to_photo(photo_id, own_username, 1,(True if own_username in FEMALES else False),citizen)
					elif value == '-1':
						added = add_vote_to_photo(photo_id, own_username, 0,(True if own_username in FEMALES else False),citizen)
					else:
						added = 0
					if added and citizen:
						# do not process vote if the user is not a 'citizen'
						process_photo_vote(photo_id, photo_owner_id, int(value), own_id)
					######################
					# if request.POST.get("from",None) == '1':
					# 	log_organic_attention.delay(photo_id=photo_id,att_giver=own_id,photo_owner_id=photo_owner_id, action='photo_vote',vote_value=value)
					######################
					#return the user to origin
					return return_to_photo(request,origin,photo_id,request.POST.get("lid",""),request.POST.get("oun",""))
			else:
				return render(request, 'penalty_suspicious.html', {})
		else:
			CSRF = csrf.get_token(request)
			temporarily_save_user_csrf(str(own_id), CSRF)
			return render(request, 'cant_vote_without_verifying.html', {'csrf':CSRF})
	else:
		return redirect("home")

@csrf_protect
def cast_vote(request,*args,**kwargs):
	if request.method == 'POST':
		if request.user_banned:
			return redirect("missing_page")
		own_id = request.user.id
		mob_verified = request.mobile_verified
		if not mob_verified:
			CSRF = csrf.get_token(request)
			temporarily_save_user_csrf(str(own_id), CSRF)
			return render(request, 'cant_vote_without_verifying.html', {'csrf':CSRF})
		elif mob_verified:
			link_id = request.POST.get("lid","")
			lang = request.POST.get("lang",None)
			sort_by = request.POST.get("sort_by",None)
			target_user_id = get_link_writer(link_id)#request.POST.get("oid","")
			if link_id and target_user_id:
				own_name = request.user.username
				if str(own_id) == target_user_id:
					#voting for own self
					return render(request, 'penalty_self_vote.html', {})
				elif voted_for_link(link_id,own_name):
					#already voted for link
					return render(request,'already_voted.html',{})
				else:
					#process the vote
					time_remaining, can_vote = can_vote_on_link(own_id)
					if not can_vote:
						request.session["target_id"] = link_id
						context = {'time_remaining':time_remaining}
						return render(request,'vote_cool_down.html',context)
					else:
						is_pinkstar = (True if own_name in FEMALES else False)
						value = request.POST.get("vote","")
						if value == '1':
							vote_tasks.delay(own_id, target_user_id,link_id,value)
							# username = u'سلمہ'
							add_vote_to_link(link_id, value, own_name,is_pinkstar)
						elif value == '-1':
							vote_tasks.delay(own_id, target_user_id,link_id,value)
							add_vote_to_link(link_id, value, own_name,is_pinkstar)
						##############################Cricket Voting###########################
						#######################################################################
						elif value == '4':
							vote_tasks.delay(own_id, target_user_id,link_id,'1')
							add_vote_to_link(link_id, value, own_name,is_pinkstar)
						elif value == '-4':
							vote_tasks.delay(own_id, target_user_id,link_id,'-1')
							add_vote_to_link(link_id, value, own_name,is_pinkstar)
						elif value == '5' and is_pinkstar:
							#is the user a verified female? If so, process the super cricket upvote
							vote_tasks.delay(own_id, target_user_id,link_id,'2')
							add_vote_to_link(link_id, value, own_name,is_pinkstar)
						elif value == '-5' and is_pinkstar:
							#is the user a verified female? If so, process the super cricket downvote
							vote_tasks.delay(own_id, target_user_id,link_id,'-2')
							add_vote_to_link(link_id, value, own_name,is_pinkstar)
						#######################################################################
						#######################################################################
						elif value == '2' and is_pinkstar:
							#is the user a verified female? If so, process the super upvote
							vote_tasks.delay(own_id, target_user_id,link_id,value)
							add_vote_to_link(link_id, value, own_name,is_pinkstar)
						elif value == '-2' and is_pinkstar:
							#is the user a verified female? If so, process the super downvote
							vote_tasks.delay(own_id, target_user_id,link_id,value)
							add_vote_to_link(link_id, value, own_name,is_pinkstar)
						else:
							pass
						origin = request.POST.get("from","")
						if origin == '1':
							#came from cricket_comments
							request.session["target_id"] = link_id
							request.session.modified = True
							return redirect("cric_loc")
						elif origin == '0':
							#came from home page
							request.session["target_id"] = link_id
							request.session.modified = True
							if lang == 'urdu' and sort_by == 'best':
								return redirect("home_loc_ur_best", lang)
							elif sort_by == 'best':
								return redirect("home_loc_best")
							elif lang == 'urdu':
								return redirect("home_loc_ur", lang)
							else:
								return redirect("home_loc")
						else:
							#came from somewhere else (error?)
							return redirect("home")
			else:
				return render(request, 'penalty_suspicious.html', {})
		else:
			CSRF = csrf.get_token(request)
			temporarily_save_user_csrf(str(own_id), CSRF)
			return render(request, 'cant_vote_without_verifying.html', {'csrf':CSRF})
	else:
		return redirect("home")

@csrf_protect
def hell_ban(request,*args,**kwargs):
	if request.method == "POST":
		ghost_ban = request.POST.get("ghost_ban","")
		if ghost_ban:
			counter = request.POST.get("counter","")
			username = request.POST.get("original_target_username","")
			if counter == '1':
				target = request.POST.get("target1","")
				if HellBanList.objects.filter(condemned_id=target).exists():
					HellBanList.objects.filter(condemned_id=target).delete()
					HellBanList.objects.create(condemned_id=target)
				else:
					HellBanList.objects.create(condemned_id=target)
				return redirect("profile",username)
			else:
				try:
					counter = int(counter)
					temp = 1
					target_ids = []
					while temp < (counter+1):
						target_id = request.POST.get("target"+str(temp),"")
						if target_id:
							target_ids.append(target_id)
						temp += 1
					if target_ids:
						hellbanned =[]
						HellBanList.objects.filter(condemned_id__in=target_ids).delete()
						for target_id in target_ids:
							hellbanned.append(HellBanList(condemned_id=target_id))
						HellBanList.objects.bulk_create(hellbanned)
						return redirect("profile",username)
					else:
						return redirect("profile",username)
				except:
					return redirect("home")
		else:
			target_username = request.POST.get("t_uname")
			target_id = request.POST.get("t_id")
			clone_ids = get_clones(target_id)
			own_id = request.user.id
			if clone_ids:
				if len(clone_ids) > 1:
					targets = User.objects.filter(id__in=clone_ids).values('id','username')
					hellbanned = list(HellBanList.objects.filter(condemned_id__in=clone_ids).values_list('condemned_id',flat=True))
					if hellbanned:
						for target in targets:
							if target['id'] in hellbanned:
								target['banned'] = True
							else:
								target['banned'] = False
					else:
						for target in targets:
							target['banned'] = False
					context = {'offline':False,'own_id':own_id,'targets':targets,'counter':len(clone_ids),'original_target_id':target_id,\
					'original_target_uname':target_username}
					return render(request,'hell_ban.html',context)
				elif len(clone_ids) == 1:
					if HellBanList.objects.filter(condemned_id=target_id).exists():
						targets = [{'id':target_id,'username':target_username,'banned':True}]
					else:
						targets = [{'id':target_id,'username':target_username,'banned':False}]
					context = {'offline':False,'counter':1,'original_target_id':target_id,'own_id':own_id,'targets':targets,\
					'original_target_uname':target_username}
					return render(request,'hell_ban.html',context)
				else:
					if HellBanList.objects.filter(condemned_id=target_id).exists():
						banned = True
					else:
						banned = False
					context={'offline':True,'original_target_id':target_id,'counter':1,'own_id':own_id,'banned':banned,\
					'original_target_uname':target_username}
					return render(request,'hell_ban.html',context)
			else:
				if HellBanList.objects.filter(condemned_id=target_id).exists():
					banned = True
				else:
					banned = False
				context={'offline':True,'original_target_id':target_id,'counter':1,'own_id':own_id,'banned':banned,\
				'original_target_uname':target_username}
				return render(request,'hell_ban.html',context)
	else:
		return render(request,"404.html",{})

@csrf_protect
def show_clones(request,*args,**kwargs):
	if request.method == "POST":
		target_username = request.POST.get("t_uname")
		target_id = request.POST.get("t_id")
		clone_ids = get_clones(target_id)
		if clone_ids:
			usernames = User.objects.filter(id__in=clone_ids).values_list('username',flat=True)
			context={'usernames':usernames,'original_target_id':target_id,'original_target_uname':target_username,\
			'own_id':request.user.id}
			return render(request,"show_clones.html",context)
		else:
			context={'usernames':None,'original_target_id':target_id,'original_target_uname':target_username,\
			'own_id':request.user.id}
			return render(request,"show_clones.html",context)
	else:
		return render(request,"404.html",{})

@csrf_protect
def kick_ban_user(request,*args,**kwargs):
	if request.method == "POST":
		kick_ban = request.POST.get("kick_ban","")
		if kick_ban:
			counter = request.POST.get("counter","")
			username = request.POST.get("original_target_username","")
			if counter == '1':
				target = request.POST.get("target1","")
				Session.objects.filter(user_id=target).delete()
				# BAN IP or USER_ID or BOTH?
				return redirect("profile",username)
			else:
				try:
					counter = int(counter)
					temp = 1
					target_ids = []
					while temp < (counter+1):
						target_id = request.POST.get("target"+str(temp),"")
						if target_id:
							target_ids.append(target_id)
						temp += 1
					Session.objects.filter(user_id__in=target_ids).delete()
					return redirect("profile",username)
				except:
					return redirect("home")
		else:
			target_username = request.POST.get("t_uname")
			target_id = request.POST.get("t_id")
			clone_ids = get_clones(target_id)
			if clone_ids:
				if len(clone_ids) > 1:
					targets = User.objects.filter(id__in=clone_ids).values('id','username')
					context={'offline':False,'targets':targets,'original_target_id':target_id,'original_target_uname':target_username,\
					'counter':len(clone_ids),'own_id':request.user.id}
					return render(request,'kick_ban_user.html',context)
				elif len(clone_ids) == 1:
					targets = [{'id':target_id,'username':target_username}]
					context={'offline':False,'targets':targets,'original_target_id':target_id,'original_target_uname':target_username,\
					'counter':1,'own_id':request.user.id}
					return render(request,'kick_ban_user.html',context)
				else:
					context={'offline':True,'original_target_uname':target_username,'original_target_id':target_id,'counter':1,\
					'own_id':request.user.id}
					return render(request,'kick_ban_user.html',context)
			else:
				context={'offline':True,'original_target_uname':target_username,'original_target_id':target_id,'counter':1,\
				'own_id':request.user.id}
				return render(request,'kick_ban_user.html',context)
	else:
		return render(request,"404.html",{})

@csrf_protect
def kick_user(request,*args,**kwargs):
	if request.method == "POST":
		kick = request.POST.get("kick","")
		if kick:
			counter = request.POST.get("counter","")
			username = request.POST.get("original_target_username","")
			if counter == '1':
				target = request.POST.get("target1","")
				Session.objects.filter(user_id=target).delete()
				return redirect("profile",username)
			else:
				try:
					counter = int(counter)
					temp = 1
					target_ids = []
					while temp < (counter+1):
						target_id = request.POST.get("target"+str(temp),"")
						if target_id:
							target_ids.append(target_id)
						temp += 1
					Session.objects.filter(user_id__in=target_ids).delete()
					return redirect("profile",username)
				except:
					return redirect("home")
		else:
			target_username = request.POST.get("t_uname")
			target_id = request.POST.get("t_id")
			clone_ids = get_clones(target_id)
			if clone_ids:
				if len(clone_ids) > 1:
					targets = User.objects.filter(id__in=clone_ids).values('id','username')
					context={'offline':False,'targets':targets,'original_target_id':target_id,'original_target_uname':target_username,\
					'counter':len(clone_ids),'own_id':request.user.id}
					return render(request,'kick_user.html',context)
				elif len(clone_ids) == 1:
					targets = [{'id':target_id,'username':target_username}]
					context={'offline':False,'targets':targets,'original_target_id':target_id,'original_target_uname':target_username,\
					'counter':1,'own_id':request.user.id}
					return render(request,'kick_user.html',context)
				else:
					context={'offline':True,'original_target_uname':target_username,'original_target_id':target_id,'counter':1,\
					'own_id':request.user.id}
					return render(request,'kick_user.html',context)
			else:
				context={'offline':True,'original_target_id':target_id,'counter':1,'own_id':request.user.id,\
				'original_target_uname':target_username}
				return render(request,'kick_user.html',context)
	else:
		return render(request,"404.html",{})

@csrf_protect
def cut_user_score(request,*args,**kwargs):
	if request.method == "POST":
		penalty = request.POST.get("penalty","")
		if penalty:
			target_username = request.POST.get("t_uname")
			target_id = request.POST.get("t_id")
			UserProfile.objects.filter(user_id=target_id).update(score=F('score')-int(penalty))
			return redirect("profile",target_username)
		else:
			target_username = request.POST.get("t_uname")
			target_id = request.POST.get("t_id")
			target_score = UserProfile.objects.get(user_id=target_id).score
			penalty1 = get_price(target_score)
			penalty2 = get_price(target_score)*2
			penalty3 = get_price(target_score)*3
			penalty4 = target_score
			context={'target_uname':target_username,'target_scr':target_score,'own_id':request.user.id,\
			'penalty1':penalty1,'penalty2':penalty2,'penalty3':penalty3,'penalty4':penalty4,'t_id':target_id}
			return render(request,'cut_user_score.html',context)
	else:
		return render(request,"404.html",{})

@csrf_protect	
def manage_user(request,*args,**kwargs):
	if request.method == "POST":
		manager_id = request.POST.get("m_id")
		if str(request.user.id) == manager_id:
			request.session["manager_id"] = manager_id
			target_id = request.POST.get("t_id")
			target = User.objects.get(id=target_id)
			context={'target_uname':target.username,'target_id':target_id}
			return render(request,"manage_user.html",context)
		else:
			return render(request,"404.html",{})	
	else:
		return render(request,"404.html",{})

@csrf_protect	
def manage_user_help(request,*args,**kwargs):
	if request.method == "POST":
		help_type = request.POST.get("htype")
		target_uname = request.POST.get("t_uname")
		target_id = request.POST.get("t_id")
		own_id = request.user.id
		context={'target_uname':target_uname,'target_id':target_id,'own_id':own_id,'authorized':True}
		if help_type == 'ctscr':
			return render(request,'cut_score.html',context)
		elif help_type == 'kout':
			return render(request,'kick_out.html',context)
		elif help_type == 'kban':
			return render(request,'kick_ban.html',context)
		elif help_type == 'ghban':
			return render(request,'ghost_ban.html',context)
		elif help_type == 'oclone':
			return render(request,'check_clones.html',context)
		else:
			return render(request,"404.html",{})	
	else:
		return render(request,"404.html",{})

def missing_page(request,*args,**kwargs):
	return render(request,'404.html',{})

# def LinkAutoCreate(user, content):   
# 	link = Link()
# 	#content = content.replace('#',' ') 
# 	link.description = content
# 	link.submitter = user
# 	#user.userprofile.score = user.userprofile.score + 5 #adding score for content creation
# 	epoch = datetime(1970, 1, 1).replace(tzinfo=None)
# 	unaware_submission = datetime.now().replace(tzinfo=None)
# 	td = unaware_submission - epoch 
# 	epoch_submission = td.days * 86400 + td.seconds + (float(td.microseconds) / 1000000) #number of seconds from epoch till date of submission
# 	secs = epoch_submission - 1432201843 #a recent date, coverted to epoch time
# 	link.rank_score = round(0 * 0 + secs / 45000, 8)
# 	link.with_votes = 0
# 	link.category = '1' '''
# 	try:
# 		urls1 = re.findall(urlmarker.URL_REGEX,link.description)
# 		if len(urls1)==0:
# 			pass
# 		elif len(urls1)==1:
# 			name, image = read_image(urls1[0])
# 			if image:
# 				image_io = StringIO.StringIO()
# 				image.save(image_io, format='JPEG')
# 				thumbnail = InMemoryUploadedFile(image_io, None, name, 'image/jpeg', image_io.len, None)
# 				link.image_file = thumbnail
# 		elif len(urls1)>=2:
# 			name, image = read_image(urls1[0])
# 			if image:
# 				image_io = StringIO.StringIO()
# 				image.save(image_io, format='JPEG')
# 				thumbnail = InMemoryUploadedFile(image_io, None, name, 'image/jpeg', image_io.len, None)
# 				link.image_file = thumbnail
# 			else:
# 				name, image = read_image(urls1[1])
# 				if image:
# 					image_io = StringIO.StringIO()
# 					image.save(image_io, format='JPEG')
# 					thumbnail = InMemoryUploadedFile(image_io, None, name, 'image/jpeg', image_io.len, None)
# 					link.image_file = thumbnail
# 		else:
# 			pass
# 	except Exception as e:
# 		print '%s (%s)' % (e.message, type(e))	
# 		pass			'''
# 	link.save()
# 	user.userprofile.previous_retort = content
# 	user.userprofile.save()

######################### Advertising #########################

@csrf_protect
def ad_feedback(request,*args,**kwargs):
	if request.method == 'POST':
		form = SearchAdFeedbackForm(request.POST)
		if form.is_valid():
			ad_campaign = form.cleaned_data['ad_campaign']
			results, feedback_count = get_ad_feedback(ad_campaign)
			# for feedback in results:
			# 	seconds_ago = time.time() - float(feedback['submitted_at'])
			# 	feedback['submitted_at'] = seconds_ago
			return render(request,'ad_feedback.html',{'form':form,'results':results,'feedback_count':feedback_count})
		else:
			return render(request,'ad_feedback.html',{'form':form,'feedback_count':0})
	else:
		form = SearchAdFeedbackForm()
		return render(request,'ad_feedback.html',{'form':form,'feedback_count':0})

def skin_doctor_price(request,*args,**kwargs):
	mp.track(request.user.id, 'Clicked Dr. Detail')
	return render(request,'skin_price.html',{})

def asan_doc(request,*args,**kwargs):
	if request.method == 'POST':
		form = AdFeedbackForm(request.POST)
		if form.is_valid():
			advertiser = 'Aasandoc'
			feedback = form.cleaned_data['feedback']
			username = request.user.username
			user_id = request.user.id
			time_now = timezone.now()
			submitted_at = convert_to_epoch(time_now)
			set_ad_feedback(advertiser,feedback,username,user_id,submitted_at)
			mp.track(request.user.id, 'Gave Aasandoc Feedback')
			return render(request,'ad_feedback_submitted.html',{'company':advertiser})
		else:
			return render(request,'asan_doc.html',{'form':form})
	else:
		form = AdFeedbackForm()
		mp.track(request.user.id, 'Clicked Aasandoc ad')
		return render(request,'asan_doc.html',{'form':form})


@csrf_protect
def skin_clinic(request,*args,**kwargs):
	if request.method == 'POST':
		form = AdFeedbackForm(request.POST)
		if form.is_valid():
			advertiser = 'SkinClub'
			feedback = form.cleaned_data['feedback']
			username = request.user.username
			user_id = request.user.id
			time_now = timezone.now()
			submitted_at = convert_to_epoch(time_now)
			set_ad_feedback(advertiser,feedback,username,user_id,submitted_at)
			mp.track(request.user.id, 'Gave Skin Ad Feedback')
			return render(request,'ad_feedback_submitted.html',{'company':advertiser})
		else:
			return render(request,'skin_package.html',{'form':form})
	else:
		form = AdFeedbackForm()
		mp.track(request.user.id, 'Clicked Skin Ad')
		return render(request,'skin_package.html',{'form':form})

@csrf_protect
def virgin_tees(request,*args,**kwargs):
	if request.method == 'POST':
		form = AdFeedbackForm(request.POST)
		if form.is_valid():
			advertiser = 'VirginTeez'
			feedback = form.cleaned_data['feedback']
			username = request.user.username
			user_id = request.user.id
			time_now = timezone.now()
			submitted_at = convert_to_epoch(time_now)
			set_ad_feedback(advertiser,feedback,username,user_id,submitted_at)
			mp.track(request.user.id, 'Gave VirginTeez Ad Feedback')
			return render(request,'ad_feedback_submitted.html',{'company':advertiser})
		else:
			return render(request,'virgin_tees_package.html',{'form':form})
	else:
		form = AdFeedbackForm()
		mp.track(request.user.id, 'Clicked VirginTeez Ad')
		return render(request,'virgin_tees_package.html',{'form':form})

@csrf_protect
def bykea(request,*args,**kwargs):
	if request.method == 'POST':
		form = AdFeedbackForm(request.POST)
		if form.is_valid():
			advertiser = 'Bykea'
			feedback = form.cleaned_data['feedback']
			username = request.user.username
			user_id = request.user.id
			time_now = timezone.now()
			submitted_at = convert_to_epoch(time_now)
			set_ad_feedback(advertiser,feedback,username,user_id,submitted_at)
			mp.track(request.user.id, 'Gave Bykea Ad Feedback')
			return render(request,'ad_feedback_submitted.html',{'company':advertiser})
		else:
			return render(request,'bykea_package.html',{'form':form})
	else:
		form = AdFeedbackForm()
		mp.track(request.user.id, 'Clicked Bykea Ad')
		return render(request,'bykea_package.html',{'form':form})

###############################################################

@ratelimit(rate='3/s')
def make_ad(request,*args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# context = {'unique': 'pk'}
		# return render(request, 'make_ad_error.html', context)
		return redirect("missing_page")
	else:
		request.session["ad_description_token"] = uuid.uuid4()
		return redirect("ad_description")

class AdDescriptionView(FormView):
	form_class = AdDescriptionForm
	template_name = "ad_description.html"

	def get_initial(self):#initial is a keyword argument to a formfield that enables pre-filling in the formfield
		"""
		Returns the initial data to use for forms on this view.
		"""
		user = self.request.user
		try:
			desc = self.request.session["ad_description"]
			self.initial = {'description': desc} #initial needs to be passed a dictionary
			return self.initial
		except:
			return self.initial

	def get_context_data(self, **kwargs):
		context = super(AdDescriptionView, self).get_context_data(**kwargs)
		if valid_uuid(str(self.request.session["ad_description_token"])):
			context["authentic"] = True
		else:
			context["authentic"] = False
		return context

	def form_valid(self, form):
		if self.request.method == 'POST':
			ad_description = self.request.POST.get("description")
			self.request.session["ad_description"] = ad_description
			self.request.session["ad_mobile_num_token"] = uuid.uuid4()
			return redirect("ad_mobile_num")
		else:
			return redirect("home")

class AdMobileNumView(FormView):
	form_class = AdMobileNumForm
	template_name = "ad_mobile_num.html"

	def get_initial(self):#initial is a keyword argument to a formfield that enables pre-filling in the formfield
		"""
		Returns the initial data to use for forms on this view.
		"""
		user = self.request.user
		try:
			num = self.request.session["ad_mobile_num"]
			self.initial = {'mobile_number': num} #initial needs to be passed a dictionary
			return self.initial
		except:
			return self.initial

	def get_context_data(self, **kwargs):
		context = super(AdMobileNumView, self).get_context_data(**kwargs)
		if valid_uuid(str(self.request.session["ad_mobile_num_token"])):
			context["authentic"] = True
		else:
			context["authentic"] = False
		return context

	def form_valid(self, form):
		if self.request.method == 'POST':
			mobile_number = self.request.POST.get("mobile_number")
			self.request.session["ad_mobile_num"] = mobile_number
			self.request.session["ad_call_pref_token"] = uuid.uuid4()
			return redirect("ad_call_pref")
		else:
			return redirect("home")

class AdCallPrefView(FormView):
	form_class = AdCallPrefForm
	template_name = "ad_call_pref.html"

	def get_context_data(self, **kwargs):
		context = super(AdCallPrefView, self).get_context_data(**kwargs)
		if valid_uuid(str(self.request.session["ad_call_pref_token"])):
			context["authentic"] = True
		else:
			context["authentic"] = False	
		return context

	def form_valid(self, form):
		if self.request.method == 'POST':
			call = self.request.POST.get("call",None)
			sms = self.request.POST.get("sms",None)
			callsms = self.request.POST.get("callsms",None)
			if call:
				self.request.session["ad_call_pref"] = '0'
			elif sms:
				self.request.session["ad_call_pref"] = '1'
			elif callsms:
				self.request.session["ad_call_pref"] = '2'
			else:
				return redirect("home")
			self.request.session["ad_title_yesno_token"] = uuid.uuid4()
			return redirect("ad_title_yesno")
		else:
			return redirect("home")

#'Yes' or 'No'
class AdTitleYesNoView(FormView):
	form_class = AdTitleYesNoForm
	template_name = "ad_title_yesno.html"

	def get_context_data(self, **kwargs):
		context = super(AdTitleYesNoView, self).get_context_data(**kwargs)
		if valid_uuid(str(self.request.session["ad_title_yesno_token"])):
			context["authentic"] = True
		else:
			context["authentic"] = False
		return context

	def form_valid(self, form):
		if self.request.method == 'POST':
			yes = self.request.POST.get("yes",None)
			no = self.request.POST.get("no",None)
			if yes:
				self.request.session["ad_title_token"] = uuid.uuid4()
				return redirect("ad_title")
			elif no:
				self.request.session["ad_image_yesno_token"] = uuid.uuid4()
				return redirect("ad_image_yesno")
			else:
				return redirect("home")
		else:
			return redirect("home")

class AdTitleView(FormView):
	form_class = AdTitleForm
	template_name = "ad_title.html"

	def get_initial(self):#initial is a keyword argument to a formfield that enables pre-filling in the formfield
		"""
		Returns the initial data to use for forms on this view.
		"""
		user = self.request.user
		try:
			title = self.request.session["ad_title"]
			self.initial = {'title': title} #initial needs to be passed a dictionary
			return self.initial
		except:
			return self.initial

	def get_context_data(self, **kwargs):
		context = super(AdTitleView, self).get_context_data(**kwargs)
		if valid_uuid(str(self.request.session["ad_title_token"])):
			context["authentic"] = True
		else:
			context["authentic"] = False
		return context

	def form_valid(self, form):
		if self.request.method == 'POST':
			title = self.request.POST.get("title")
			self.request.session["ad_title"] = title
			self.request.session["ad_image_yesno_token"] = uuid.uuid4()
			return redirect("ad_image_yesno")
		else:
			return redirect("home")

#'Yes' or 'No'
class AdImageYesNoView(FormView):
	form_class = AdImageYesNoForm
	template_name = "ad_image_yesno.html"

	def get_context_data(self, **kwargs):
		context = super(AdImageYesNoView, self).get_context_data(**kwargs)
		if valid_uuid(str(self.request.session["ad_image_yesno_token"])):
			context["authentic"] = True
		else:
			context["authentic"] = False
		return context

	def form_valid(self, form):
		if self.request.method == 'POST':
			yes = self.request.POST.get("yes",None)
			no = self.request.POST.get("no",None)
			if yes:
				self.request.session["ad_image_token"] = uuid.uuid4()
				return redirect("ad_image")
			elif no:
				self.request.session["ad_gender_token"] = uuid.uuid4()
				self.request.session["ad_image"] = None
				return redirect("ad_gender")
			else:
				return redirect("home")
		else:
			return redirect("home")

class AdImageView(CreateView):
	model = ChatPic
	form_class = AdImageForm
	template_name = "ad_image.html"

	def get_context_data(self, **kwargs):
		context = super(AdImageView, self).get_context_data(**kwargs)
		if valid_uuid(str(self.request.session["ad_image_token"])):
			context["authentic"] = True
		else:
			context["authentic"] = False
		return context

	def form_valid(self, form):
		f = form.save(commit=False)
		if f.image:
			on_fbs = self.request.META.get('HTTP_X_IORG_FBS',False)
			if on_fbs:
				if f.image.size > 200000:
					context = {'pk':'pk'}
					return render(self.request,'big_photo_fbs.html',context)
				else:
					pass
			else:
				if f.image.size > 10000000:
					context = {'pk':'pk'}
					return render(self.request,'big_photo_regular.html',context)
				else:
					pass
			image_file = clean_image_file(f.image)
			if image_file:
				f.image = image_file
			else:
				f.image = None
		if f.image:
			unique = uuid.uuid4()
			if self.request.user.is_authenticated():
				ad_image=ChatPic.objects.create(image=f.image, owner=self.request.user, times_sent=0, unique=unique)
			else:
				ad_image=ChatPic.objects.create(image=f.image, owner_id=1, times_sent=0, unique=unique)
			self.request.session["ad_image"] = ad_image.image.url
		else:
			self.request.session["ad_image"] = None
		self.request.session["ad_gender_token"] = uuid.uuid4()
		self.request.session.modified = True
		return redirect("ad_gender")

# class AdLinkURLView(FormView):
# 	form_class = AdLinkURLForm
# 	template_name = "ad_url.html"

# 	def get_context_data(self, **kwargs):
# 		context = super(AdLinkURLView, self).get_context_data(**kwargs)
# 		if valid_uuid(str(self.request.session["ad_link_url_token"])):
# 			context["authentic"] = True
# 		else:
# 			context["authentic"] = False
# 		return context

# 	def form_valid(self, form):

class AdGenderChoiceView(FormView):
	form_class = AdGenderChoiceForm
	template_name = "ad_gender.html"

	def get_context_data(self, **kwargs):
		context = super(AdGenderChoiceView, self).get_context_data(**kwargs)
		if valid_uuid(str(self.request.session["ad_gender_token"])):
			context["authentic"] = True
		else:
			context["authentic"] = False
		return context

	def form_valid(self, form):
		if self.request.method == 'POST':
			yes = self.request.POST.get("yes",None)
			no = self.request.POST.get("no",None)
			if yes:
				self.request.session["ad_gender"] = True
			elif no:
				self.request.session["ad_gender"] = False
			else:
				return redirect("home")
			self.request.session["ad_address_yesno_token"] = uuid.uuid4()
			return redirect("ad_address_yesno")
		else:
			return redirect("home")

#'Yes' or 'No'
class AdAddressYesNoView(FormView):
	form_class = AdAddressYesNoForm
	template_name = "ad_address_yesno.html"

	def get_context_data(self, **kwargs):
		context = super(AdAddressYesNoView, self).get_context_data(**kwargs)
		if valid_uuid(str(self.request.session["ad_address_yesno_token"])):
			context["authentic"] = True
		else:
			context["authentic"] = False
		return context

	def form_valid(self, form):
		if self.request.method == 'POST':
			yes = self.request.POST.get("yes",None)
			no = self.request.POST.get("no",None)
			if yes:
				self.request.session["ad_address_token"] = uuid.uuid4()
				return redirect("ad_address")
			elif no:
				self.request.session["ad_finalize_token"] = uuid.uuid4()
				return redirect("ad_finalize")
			else:
				return redirect("home")
		else:
			return redirect("home")

class AdAddressView(FormView):
	form_class = AdAddressForm
	template_name = "ad_address.html"

	def get_initial(self):#initial is a keyword argument to a formfield that enables pre-filling in the formfield
		"""
		Returns the initial data to use for forms on this view.
		"""
		user = self.request.user
		try:
			address = self.request.session["ad_address"]
			self.initial = {'address': address} #initial needs to be passed a dictionary
			return self.initial
		except:
			return self.initial

	def get_context_data(self, **kwargs):
		context = super(AdAddressView, self).get_context_data(**kwargs)
		if valid_uuid(str(self.request.session["ad_address_token"])):
			context["authentic"] = True
		else:
			context["authentic"] = False
		return context

	def form_valid(self, form):
		if self.request.method == 'POST':
			address = self.request.POST.get("address")
			self.request.session["ad_address"] = address
			self.request.session["ad_finalize"] = uuid.uuid4()
			return redirect("ad_finalize")
		else:
			return redirect("home")

@ratelimit(rate='3/s')
def ad_finalize(request,*args, **kwargs):
	was_limited = getattr(request, 'limits', False)
	if was_limited:
		# context = {'unique': 'pk'}
		# return render(request, 'make_ad_error.html', context)
		return redirect("missing_page")
	else:
		if valid_uuid(str(request.session["ad_finalize"])):
			description = request.session["ad_description"]
			# request.session["ad_description"] = None
			mobnum = request.session["ad_mobile_num"]
			# request.session["ad_mobile_num"] = None
			callpref = request.session["ad_call_pref"]
			# request.session["ad_call_pref"] = None
			title = request.session["ad_title"]
			# request.session["ad_title"] = None
			image = request.session["ad_image"]
			# request.session["ad_image"] = None
			address = request.session["ad_address"]
			# request.session["ad_address"] = None
			gender_based = request.session["ad_gender"]
			# request.session["ad_gender"] = None
			locations = ['0','1','2','3','4', '5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20']
			ad_url = 'http://www.damadam.pk/nick/ad/pin_code' # contains preview of advert that got submitted
			if request.user.is_authenticated():
				user_id = request.user.id
			else:
				user_id = None
			data = {"description":description, "phone_number":mobnum,
					"contact_preference":callpref, "title":title,
					"image_url":image,"address":address,
					"only_ladies":gender_based, "location":locations,
					"app_code":"1","user_id":user_id,"ad_url":ad_url}
			response = call_aasan_api(data,'create')
			return HttpResponse('Ad sent to aasanads')
		else:
			return redirect("home")
###############################################################

def suspend(request, ad_id, *args, **kwargs):
	suspend_ad(str(ad_id))
	return redirect("test_ad")

class TestAdsView(FormView):
	form_class = TestAdsForm
	template_name = "test_ads.html"

	def get_context_data(self, **kwargs):
		context = super(TestAdsView, self).get_context_data(**kwargs)
		user_loc = get_user_loc(self.request.user)
		ad,ad_id, clicks = get_ad(user_loc)
		if ad and ad_id:
			context["ad"] = ad
			context["ad_id"] = ad_id
			context["title"] = ad["ti"] 
			context["description"] = ad["ds"]
			context["clicks"] = clicks
		else:
			context["ad"] = None
			context["ad_id"] = None
			context["title"] = None
			context["description"] = None
		return context

class TestReportView(FormView):
	form_class = TestReportForm
	template_name = "test_report.html"

	def get_context_data(self, **kwargs):
		context = super(TestReportView, self).get_context_data(**kwargs)
		if self.request.user.is_authenticated():
			running,historical = get_user_ads(self.request.user.id)
		else:
			pass
		return context
		'''
		this only works for authenticated users. 
		'''

def click_ad(request, ad_id=None, *args,**kwargs):
	store_click(ad_id, get_user_loc(request.user))
	return redirect("test_ad")

###############################################################

@csrf_protect
def advertise_with_us(request,*args,**kwargs):
	if request.method == 'POST':
		form = AdvertiseWithUsForm(request.POST)
		if form.is_valid():
			name = form.cleaned_data.get("name")
			detail = form.cleaned_data.get("detail")
			mobile = form.cleaned_data.get("mobile")
			loc = form.cleaned_data.get("loc")
			submission_time = time.time()
			username = request.user.username if request.user.is_authenticated() else None
			save_advertiser(name, detail, mobile, loc, submission_time, username)
			return render(request,"thank_advertiser.html",{})
		else:
			return render(request,"advertise_with_us.html",{'form':form})
	else:
		form = AdvertiseWithUsForm()
		return render(request,"advertise_with_us.html",{'form':form})

@csrf_protect
def show_advertisers(request,*args,**kwargs):
	if request.method == 'POST':
		action = request.POST.get('action',None)
		export = None
		if action == 'Delete All':
			purge_advertisers()
		elif action == 'Export & Delete':
			export = export_advertisers()
		if export is not None:
			return render(request,"advertiser_export_status.html",{'export':export})
		else:
			return redirect("show_advertisers")
	else:
		list_ = get_advertisers()
		list_of_advertisers = []
		for elem in list_:
			list_of_advertisers.append(ast.literal_eval(elem))
		return render(request,"show_advertisers.html",{'advertisers':list_of_advertisers,\
			'num':len(list_of_advertisers)})

# Report run on 15/3/2018
#             relation             | total_size 
# ---------------------------------+------------
#  public.links_reply              | 14 GB
#  public.links_publicreply        | 8396 MB
#  public.links_photocomment       | 7377 MB
#  public.user_sessions_session    | 6689 MB
#  public.links_link               | 3769 MB
#  public.links_photo              | 1882 MB
#  public.links_photo_which_stream | 429 MB
#  public.links_photostream        | 408 MB
#  public.auth_user                | 294 MB
#  public.links_userprofile        | 239 MB
#  public.links_userfan            | 214 MB
#  public.links_salatinvite        | 152 MB
#  public.links_hotuser            | 43 MB
#  public.links_group              | 42 MB
#  public.links_totalfanandphotos  | 38 MB
#  public.links_salat              | 28 MB
#  public.links_tutorialflag       | 13 MB
#  public.links_cooldown           | 10112 kB
#  public.links_latestsalat        | 6208 kB
#  public.links_groupcaptain       | 6072 kB


# Report run on 18/3/2017
#              Table               |  Size   | External Size 
# ----------------------------------+---------+---------------
#  user_sessions_session            | 8583 MB | 6917 MB
#  links_publicreply                | 5999 MB | 3078 MB
#  links_photocomment               | 2920 MB | 1401 MB
#  links_photo                      | 2527 MB | 2202 MB
#  links_link                       | 1430 MB | 374 MB
#  links_reply                      | 880 MB  | 664 MB
#  links_photo_which_stream         | 237 MB  | 159 MB
#  links_photostream                | 226 MB  | 119 MB
#  links_userprofile                | 131 MB  | 54 MB
#  links_userfan                    | 105 MB  | 67 MB
#  auth_user                        | 99 MB   | 38 MB


# Report run on 15/3/2017
#               Table               |  Size   | External Size 
# ----------------------------------+---------+---------------
#  user_sessions_session            | 8578 MB | 6911 MB
#  links_publicreply                | 5918 MB | 3040 MB
#  links_photocomment               | 2877 MB | 1381 MB
#  links_photo                      | 2505 MB | 2180 MB
#  links_link                       | 1409 MB | 369 MB
#  links_reply                      | 875 MB  | 660 MB
#  links_salatinvite                | 439 MB  | 319 MB
#  links_photo_which_stream         | 234 MB  | 157 MB
#  links_photostream                | 223 MB  | 118 MB
#  links_userprofile                | 130 MB  | 54 MB
#  links_userfan                    | 105 MB  | 66 MB

# Report run on 4/3/2017
#               Table               |  Size   | External Size 
# ----------------------------------+---------+---------------
#  user_sessions_session            | 8578 MB | 6911 MB
#  links_publicreply                | 5636 MB | 2904 MB
#  links_photocomment               | 2717 MB | 1303 MB
#  links_photo                      | 2423 MB | 2098 MB
#  links_link                       | 1334 MB | 352 MB
#  links_reply                      | 873 MB  | 659 MB
#  links_vote                       | 579 MB  | 371 MB
#  links_salatinvite                | 429 MB  | 312 MB
#  links_groupseen                  | 394 MB  | 362 MB
#  links_photo_which_stream         | 225 MB  | 151 MB
#  links_photostream                | 214 MB  | 113 MB
#  links_userprofile                | 129 MB  | 53 MB
#  links_userfan                    | 101 MB  | 63 MB
#  auth_user                        | 96 MB   | 36 MB
#  links_totalfanandphotos          | 82 MB   | 73 MB
#  links_report                     | 82 MB   | 67 MB
#  links_photovote                  | 49 MB   | 49 MB


# Report run on 24/2/2017
#               Table               |  Size   | External Size 
# ----------------------------------+---------+---------------
#  user_sessions_session            | 8578 MB | 6911 MB
#  links_publicreply                | 5453 MB | 2817 MB
#  links_photocomment               | 2604 MB | 1249 MB
#  links_photo                      | 2366 MB | 2040 MB
#  links_link                       | 1277 MB | 338 MB
#  links_reply                      | 868 MB  | 655 MB
#  links_vote                       | 555 MB  | 356 MB
#  links_salatinvite                | 419 MB  | 305 MB
#  links_groupseen                  | 394 MB  | 362 MB
#  links_photo_which_stream         | 218 MB  | 146 MB
#  links_photostream                | 208 MB  | 110 MB
#  links_userprofile                | 129 MB  | 52 MB


# Report run on 12/11/2016
#               Table               |  Size   | External Size 
# ----------------------------------+---------+---------------
#  user_sessions_session            | 8214 MB | 6464 MB
#  links_publicreply                | 3666 MB | 1923 MB
#  links_photoobjectsubscription    | 2627 MB | 2251 MB
#  links_photo                      | 1822 MB | 1497 MB
#  links_grouptraffic               | 1756 MB | 1724 MB
#  links_photocomment               | 1569 MB | 749 MB
#  links_link                       | 795 MB  | 216 MB
#  links_reply                      | 544 MB  | 413 MB
#  links_groupseen                  | 454 MB  | 362 MB
#  links_vote                       | 363 MB  | 235 MB
#  links_seen                       | 351 MB  | 351 MB
#  links_salatinvite                | 314 MB  | 228 MB
#  links_groupinvite                | 164 MB  | 125 MB
#  links_photo_which_stream         | 147 MB  | 99 MB
#  links_photostream                | 140 MB  | 74 MB
#  links_userprofile                | 119 MB  | 43 MB

###################################################

# Setting up new redis instance

# sudo cp redis.conf /etc/redis/redis-2.conf OR sudo cp redis-2.conf /etc/redis/redis-3.conf
# 	Inside the conf:
# pidfile /var/run/redis/redis2-server.pid
# logfile /var/log/redis/redis2-server.log
# dir /var/lib/redis2
# port 0
# unixsocket /var/run/redis/redis2.sock
# unixsocketperm 775
# set a policy for BG save (e.g. save 3600 1)
#	Outside the conf:
#sudo mkdir /var/lib/redis2
#sudo chown -R redis:redis /var/lib/redis2
#	Create a copy of redis-server file at /etc/init.d (sudo cp redis-server /etc/init.d/redis2-server OR sudo cp redis2-server /etc/init.d/redis3-server)
# change DAEMON_ARGS, NAME, DESC, and PIDFILE
# exit file and do:
# sudo chmod 755 redis2-server
# sudo update-rc.d redis2-server defaults
# sudo /etc/init.d/redis2-server start
# TO CONNECT TO REDIS CLI:
# sudo redis-cli -s /var/run/redis/redis2.sock
# then make an entry in location.py for REDLOC[next_value]
# ensure redis[next_value].py refers to this new REDLOC, and also its CONNECTION_POOL

###################################################

# def test_functional_redis_server(request,*args,**kwargs):
# 	payload = "This is test payload".split()
# 	result = set_test_payload(payload)
# 	return render(request,"redis_successfuly.html",{'result':result})

# Example test function to be used within redis[new].py:

# POOL = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=REDLOC3, db=0)

# def set_test_payload(payload_list):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	try:
# 		return my_server.lpush(my_server,payload_list)
# 	except:
# 		return None