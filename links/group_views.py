# for starters, only create private mehfil
import ujson as json
import uuid, random, time
from datetime import datetime
from collections import defaultdict
from django.middleware import csrf
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import cache_control
from django.core.urlresolvers import reverse_lazy, reverse
from redis1 import check_photo_upload_ban
from redis3 import tutorial_unseen, get_user_verified_number
from redis2 import update_notification, skip_private_chat_notif
from redis4 import set_photo_upload_key, get_and_delete_photo_upload_key, retrieve_bulk_unames, retrieve_bulk_avurls, avg_num_of_chats_per_type,\
avg_num_of_switchovers_per_type, avg_sessions_per_type, get_cached_photo_dim, cache_photo_dim, retrieve_uname, retrieve_user_id, retrieve_photo_data,\
retrieve_fresh_photo_shares_or_cached_data
from redis5 import personal_group_invite_status, process_invite_sending, interactive_invite_privacy_settings, personal_group_sms_invite_allwd, \
delete_or_hide_chat_from_personal_group, personal_group_already_exists, add_content_to_personal_group, retrieve_content_from_personal_group, \
sanitize_personal_group_invites, delete_all_user_chats_from_personal_group, check_single_chat_current_status, get_personal_group_anon_state, \
set_personal_group_anon_state, create_personal_group, toggle_personal_group_photo_settings, get_personal_group_photo_rec_settings, ignore_invite,\
personal_group_image_transfer_not_permitted, set_personal_group_photo_permission, personal_group_photo_xfer_invite_allwd, get_user_sms_setting,\
retrieve_all_personal_group_images, delete_or_hide_photo_from_settings, enable_personal_group_sms_rec, set_personal_group_target_id_and_csrf, \
disable_personal_group_sms_rec, sms_sending_locked, lock_sms_sending, return_invite_list, set_sms_notif_from_chat, retrieve_user_group_list_contents,\
suspend_personal_group, save_personal_group_content, retrieve_personal_group_saved_content, get_cached_personal_group_data, reset_all_group_chat, \
delete_single_personal_group_saved_content, delete_all_personal_group_saved_content, is_save_permission_granted_by_target, own_save_permission_status,\
toggle_save_permission, exit_already_triggered, purge_all_saved_chat_of_user,unsuspend_personal_group, can_change_number, get_target_username,\
get_single_user_credentials, get_user_credentials, get_user_friend_list, get_rate_limit_in_personal_group_sharing, can_share_photo#, exited_personal_group_hard_deletion
from tasks import personal_group_trimming_task, add_image_to_personal_group_storage, queue_personal_group_invitational_sms, private_chat_tasks, \
cache_personal_group, update_notif_object_anon, update_notif_object_del, update_notif_object_hide, private_chat_seen, photo_sharing_metrics_and_rate_limit,\
cache_photo_shares
from page_controls import PERSONAL_GROUP_IMGS_PER_PAGE, PERSONAL_GROUP_MAX_SMS_SIZE, PERSONAL_GROUP_SMS_LOCK_TTL, PERSONAL_GROUP_OWN_BG, PRIV_CHAT_EMOTEXT, \
PERSONAL_GROUP_THEIR_BG, PERSONAL_GROUP_OWN_BORDER, PERSONAL_GROUP_THEIR_BORDER, OBJS_PER_PAGE_IN_USER_GROUP_LIST, OBJS_PER_PAGE_IN_USER_GROUP_INVITE_LIST, \
PRIV_CHAT_NOTIF, PHOTO_SHARING_FRIEND_LIMIT
from group_forms import PersonalGroupPostForm, PersonalGroupSMSForm, PersonalGroupReplyPostForm, PersonalGroupSharedPhotoCaptionForm
from score import PERSONAL_GROUP_ERR, THUMB_HEIGHT, PERSONAL_GROUP_DEFAULT_SMS_TXT
from image_processing import process_personal_group_image
from views import get_page_obj, get_object_list_and_forms
from imagestorage import upload_image_to_s3
from forms import UnseenActivityForm
from models import Photo

ONE_DAY = 60*60*24
ONE_WEEK = 7*60*60*24

# def deletion_test(request):
# 	"""
# 	"""
# 	exited_personal_group_hard_deletion(['5','6'])

#######################################################################################################################
########################################### Personal Group Helper Functions ###########################################
#######################################################################################################################


def get_uname_and_avurl(target_id, their_anon_status):
	"""
	Retrieves target_id's username and avatar_url
	"""
	target_id = str(target_id)
	if their_anon_status:
		return get_target_username(target_id), None
	else:
		return get_single_user_credentials(target_id,as_list=False)

def retrieve_user_env(user_agent, fbs):
	"""
	Checks whether environment can support JS

	Opera mini (extreme mode) and free basics do not support JS
	"""
	if fbs:
		return False#, True
	elif user_agent:
		if 'Presto' in user_agent and 'Opera Mini' in user_agent:
			return False#, False
		else:
			return True#, False
	else:
		return True#, False


def sms_lock_time_remaining(time_of_lock):
	"""
	Calculates wait time till SMS lock expiry
	"""
	return PERSONAL_GROUP_SMS_LOCK_TTL - (time.time() - time_of_lock)


def create_sms_text(target_username, concat_text, incl_uname=True):
	"""
	Creates an sms text of the right size
	"""
	if incl_uname:
		full_text = target_username[:16]+concat_text
	else:
		full_text = concat_text
	return full_text[:PERSONAL_GROUP_MAX_SMS_SIZE]


def personal_group_sanitization(obj_count, obj_ceiling, group_id):
	"""
	Determines whether to call personal_group trimming task
	"""
	if obj_count > obj_ceiling and random.random() < 0.66:
		personal_group_trimming_task.delay(group_id, obj_count)


def return_to_source(origin,parent_object_id,target_username):
	"""
	Redirect to a certain location
	"""
	if origin in ('home','home_reply'):
		if parent_object_id:
			return redirect("home_loc_pk",pk=parent_object_id)
		else:
			return redirect("home")
	elif origin == 'history':
		if target_username:
			return redirect("user_activity",slug=target_username)
		else:
			return redirect("home")
	elif origin == 'public':
		if parent_object_id:
			return redirect("public_group",slug=parent_object_id)
		else:
			return redirect("home")
	elif origin == 'search':
		return redirect("search_username")
	elif origin == 'profile':
		if parent_object_id:
			return redirect("user_profile",slug=parent_object_id)
		else:
			return redirect("home")	
	elif origin == 'profile_photos':
		if parent_object_id:
			return redirect("profile",slug=parent_object_id)
		else:
			return redirect("home")	
	elif origin == 'best_photos':
		if parent_object_id:
			return redirect("best_photo_loc_pk", parent_object_id)
		else:
			return redirect("home")
	elif origin == 'photo_comments':
		if parent_object_id:
			return redirect("comment", parent_object_id)
		else:
			return redirect("home")
	elif origin == 'fresh_photos':
		if parent_object_id:
			return redirect("see_photo_pk", parent_object_id)
		else:
			return redirect("photo")
	else:
		return redirect("home")


def construct_personal_group_data(content_list_of_dictionaries, own_id, own_uname, their_uname, own_avurl, their_avurl):
	"""
	Preps raw personal group data for display

	Helper function for enter_personal_group()
	"""
	for dictionary in content_list_of_dictionaries:
		is_own_blob = True if dictionary['id'] == str(own_id) else False 
		which_blob = dictionary.get("which_blob",None) # identifies 'nor' (normal), 'res' (response), 'action', 'notif' (notification) blobs
		if is_own_blob:
			dictionary["username"] = own_uname
			dictionary["av_url"] = own_avurl
		else:
			dictionary["username"] = their_uname
			dictionary["av_url"] = their_avurl
		if which_blob == 'res':
			dictionary["res_time"] = float(dictionary["res_time"])
			if is_own_blob:
				dictionary["t_username"] = their_uname 
				dictionary["t_av_url"] = their_avurl
			else:
				dictionary["t_username"] = own_uname
				dictionary["t_av_url"] = own_avurl
		elif which_blob in ('action','notif'):
			if is_own_blob:
				dictionary["t_username"] = their_uname 
				dictionary["t_av_url"] = their_avurl
			else:
				dictionary["t_username"] = own_uname
				dictionary["t_av_url"] = own_avurl
		else:
			"""
			Degree of completeness (of retrieved metadata):

			'0': no metadata retrieved
			'1': just image retrieved
			'2': just title retrieved
			'3': just desc retrieved
			'4': just img and img_dim retrieved
			'5': just desc and img retrieved
			'6': just title and img retrieved
			'7': just desc and title retrieved
			'8': just title, img and img_dim retrieved
			'9': just desc, img and img_dim retrieved
			'10': just desc, title and img retrieved
			'11': desc, title, img and img_dim retrieved
			"""
			normal_chat = []
			for i in range(1,int(dictionary["idx"])+1):
				idx = str(i)
				doc = 'doc'+idx
				has_url_meta = doc in dictionary
				if has_url_meta and dictionary['type'+idx] == 'text':
					meta_complete = dictionary[doc]
					# add meta_complete in every 5th index (i.e. tup.5)
					# add meta_data in this order: url, desc, title, img, img_hw_ratio, 'yt' - youtube (add empty index in case data doesn't exist - useful in personal_group.html)
					if meta_complete == '1':
						# just image retrieved
						normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx]),'1',\
							dictionary['url'+idx],'','',dictionary['url_img'+idx],'',dictionary['yt'+idx]))
					elif meta_complete == '2':
						# just title retrieved
						normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx]),'2',\
							dictionary['url'+idx],'',dictionary['url_title'+idx],'','',dictionary['yt'+idx]))
					elif meta_complete == '3':
						# just desc retrieved
						normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx]),'3',\
							dictionary['url'+idx], dictionary['url_desc'+idx],'','','',dictionary['yt'+idx]))
					elif meta_complete == '4':
						# img and img_dim
						normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx]),'4',\
							dictionary['url'+idx],'','',dictionary['url_img'+idx],dictionary['url_hw_ratio'+idx],dictionary['yt'+idx]))
					elif meta_complete == '5':
						# desc and img
						normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx]),'5',\
							dictionary['url'+idx], dictionary['url_desc'+idx],'',dictionary['url_img'+idx],'',dictionary['yt'+idx]))
					elif meta_complete == '6':
						# title and img
						normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx]),'6',\
							dictionary['url'+idx],'',dictionary['url_title'+idx],dictionary['url_img'+idx],'',dictionary['yt'+idx]))
					elif meta_complete == '7':
						# desc and title
						normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx]),'7',\
							dictionary['url'+idx],dictionary['url_desc'+idx],dictionary['url_title'+idx],'','',dictionary['yt'+idx]))
					elif meta_complete == '8':
						# title, img and img_dim
						normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx]),'8',\
							dictionary['url'+idx],'',dictionary['url_title'+idx],dictionary['url_img'+idx],dictionary['url_hw_ratio'+idx],\
							dictionary['yt'+idx]))
					elif meta_complete == '9':
						# desc, img and img_dim
						normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx]),'9',\
							dictionary['url'+idx],dictionary['url_desc'+idx],'',dictionary['url_img'+idx],dictionary['url_hw_ratio'+idx],\
							dictionary['yt'+idx]))
					elif meta_complete == '10':
						# desc, title and img
						normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx]),'10',\
							dictionary['url'+idx],dictionary['url_desc'+idx],dictionary['url_title'+idx],dictionary['url_img'+idx],'',\
							dictionary['yt'+idx]))
					elif meta_complete == '11':
						# desc, title, img and img_dim
						normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx]),'11',\
							dictionary['url'+idx],dictionary['url_desc'+idx],dictionary['url_title'+idx],dictionary['url_img'+idx],\
							dictionary['url_hw_ratio'+idx],dictionary['yt'+idx]))
					else:
						# no meaningful metadata
						normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx])))
				elif has_url_meta and dictionary['type'+idx] == 'img':
					meta_complete = dictionary[doc]
					# add meta_complete in each 11th index (i.e. tup.11)
					# add meta_data in this order: url, desc, title, img, img_hw_ratio, 'yt' - youtube (add empty index in case data doesn't exist - useful in personal_group.html)
					if meta_complete == '1':
						# just image retrieved
						normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
							dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
							dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx],'1',dictionary['url'+idx],'','',dictionary['url_img'+idx],'',\
							dictionary['yt'+idx]))
					elif meta_complete == '2':
						# just title retrieved
						normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
							dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
							dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx],'2',dictionary['url'+idx],'',dictionary['url_title'+idx],'','',\
							dictionary['yt'+idx]))
					elif meta_complete == '3':
						# just desc retrieved
						normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
							dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
							dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx],'3',dictionary['url'+idx],dictionary['url_desc'+idx],'','','',\
							dictionary['yt'+idx]))
					elif meta_complete == '4':
						# img and img_dim
						normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
							dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
							dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx],'4',dictionary['url'+idx],'','',dictionary['url_img'+idx],\
							dictionary['url_hw_ratio'+idx],dictionary['yt'+idx]))
					elif meta_complete == '5':
						# desc and img
						normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
							dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
							dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx],'5',dictionary['url'+idx],dictionary['url_desc'+idx],'',\
							dictionary['url_img'+idx],'',dictionary['yt'+idx]))
					elif meta_complete == '6':
						# title and img
						normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
							dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
							dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx],'6',dictionary['url'+idx],'',dictionary['url_title'+idx],\
							dictionary['url_img'+idx],'',dictionary['yt'+idx]))
					elif meta_complete == '7':
						# desc and title
						normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
							dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
							dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx],'7',dictionary['url'+idx],dictionary['url_desc'+idx],\
							dictionary['url_title'+idx],'','',dictionary['yt'+idx]))
					elif meta_complete == '8':
						# title, img and img_dim
						normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
							dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
							dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx],'8',dictionary['url'+idx],'',dictionary['url_title'+idx],\
							dictionary['url_img'+idx],dictionary['url_hw_ratio'+idx],dictionary['yt'+idx]))
					elif meta_complete == '9':
						# desc, img and img_dim
						normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
							dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
							dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx],'9',dictionary['url'+idx],dictionary['url_desc'+idx],'',\
							dictionary['url_img'+idx],dictionary['url_hw_ratio'+idx],dictionary['yt'+idx]))
					elif meta_complete == '10':
						# desc, title and img
						normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
							dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
							dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx],'10',dictionary['url'+idx],dictionary['url_desc'+idx],\
							dictionary['url_title'+idx],dictionary['url_img'+idx],'',dictionary['yt'+idx]))
					elif meta_complete == '11':
						# desc, title, img and img_dim
						normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
							dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
							dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx],'11',dictionary['url'+idx],dictionary['url_desc'+idx],\
							dictionary['url_title'+idx],dictionary['url_img'+idx],dictionary['url_hw_ratio'+idx],dictionary['yt'+idx]))
					else:
						# no meaningful metadata
						normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
							dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
							dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx]))
				elif dictionary['type'+idx] == 'text':
					normal_chat.append((dictionary['status'+idx], idx, 'text', dictionary['text'+idx], float(dictionary['time'+idx])))
				elif dictionary['type'+idx] == 'img':
					normal_chat.append((dictionary['status'+idx], idx, 'img', dictionary['img'+idx], float(dictionary['time'+idx]), \
						dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
						dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx]))
				elif dictionary['type'+idx] == 'shared_img':
					normal_chat.append((dictionary['status'+idx], idx, 'shared_img', dictionary['shared_img'+idx], float(dictionary['time'+idx]), \
						dictionary['img_s_caption'+idx],dictionary['img_caption'+idx],dictionary['hidden'+idx],dictionary['img_width'+idx],\
						dictionary['img_hw_ratio'+idx],dictionary['img_id'+idx],dictionary['owner_uname'+idx].decode('utf-8')))
				else:
					# append nothing - this case shouldn't arise
					pass
			dictionary["iterator"] = normal_chat
	return content_list_of_dictionaries


####################################################################################################################
########################################### Personal Group Functionality ###########################################
####################################################################################################################


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def enter_personal_group(request):
	"""
	Render personal group
	"""
	own_id = request.user.id
	if request.method == "POST":
		target_id = request.POST.get("tid")
		group_id, exists = personal_group_already_exists(own_id, target_id)
		if exists:
			request.session["personal_group_tid_key"] = target_id
			request.session["personal_group_gid_key:"+target_id] = group_id#checked
			request.session.modified = True
	else:
		target_id = request.session.get("personal_group_tid_key",None)
		try:
			group_id = request.session.get("personal_group_gid_key:"+target_id,None)
		except TypeError:
			group_id = None
		if group_id:
			exists = True
		else:
			group_id, exists = personal_group_already_exists(own_id, target_id)
	if exists:
		personal_group_form_error = request.session.pop("personal_group_form_error",None)
		secret_key, own_refresh_time = uuid.uuid4(), time.time()
		set_photo_upload_key(user_id=own_id, group_id=group_id, secret_key=secret_key)
		content_list_of_dictionaries = get_cached_personal_group_data(group_id)
		if content_list_of_dictionaries:
			# populate data from cached json object
			content_list_of_dictionaries = json.loads(content_list_of_dictionaries)
			prev_seen_time, own_anon_status, their_anon_status, auto_del_called, their_last_seen_time, is_suspended, t_nick = \
			retrieve_content_from_personal_group(group_id, own_id, target_id, own_refresh_time, chat_data=False)
		else:
			# reconstruct data and cache it
			prev_seen_time, own_anon_status, their_anon_status, auto_del_called, their_last_seen_time, is_suspended, content_list_of_dictionaries, \
			own_cred, their_cred = retrieve_content_from_personal_group(group_id, own_id, target_id, own_refresh_time)
			own_uname, own_avurl, their_uname, their_avurl = own_cred[0], own_cred[1], their_cred[0], their_cred[1]
			content_list_of_dictionaries = construct_personal_group_data(content_list_of_dictionaries, own_id, own_uname, their_uname, own_avurl, \
				their_avurl)
			cache_personal_group.delay(json.dumps(content_list_of_dictionaries, ensure_ascii=False),group_id)#ensure_ascii used to get rid of error 'Unpaired high surrogate when decoding 'string'
			t_nick = their_uname
		t_nick = t_nick[:1].upper() if their_anon_status == '1' else t_nick
		their_nick = False if their_anon_status == '1' else True
		own_nick = False if own_anon_status == '1' else True
		not_empty = True if content_list_of_dictionaries else False
		if their_last_seen_time == '-1':
			last_seen_time_diff = None
		else:
			try:
				last_seen_time_diff = time.time() - float(their_last_seen_time)
			except TypeError:
				last_seen_time_diff = None
		private_chat_seen.delay(own_id, group_id, own_refresh_time) # to ensure outstanding notifications are 'seen'
		no_permit = request.session.pop("personal_group_image_xfer_no_permit",None)
		no_sms = request.session.pop("personal_group_sms_no_permit",None)
		no_save_chat = request.session.pop("personal_group_save_chat_no_permit",None)
		is_js_env = retrieve_user_env(user_agent=request.META.get('HTTP_USER_AGENT',None), fbs=request.META.get('HTTP_X_IORG_FBS',False))
		return render(request,"personal_group/main/personal_group.html",{'form_errors':personal_group_form_error,'personal_group_form':PersonalGroupPostForm(),\
			'tid':target_id,'content':content_list_of_dictionaries, 'own_id':own_id, 'last_seen_time':prev_seen_time,'sk':secret_key,'no_sms':no_sms,\
			'own_nick':own_nick,'their_nick':their_nick, 'no_permit':no_permit,'t_nick':t_nick,'autodel':auto_del_called,'thumb_height':THUMB_HEIGHT,\
			'not_empty':not_empty,'their_last_seen_time':their_last_seen_time,'last_seen_time_diff':last_seen_time_diff,'no_save_chat':no_save_chat,\
			'is_suspended':is_suspended,'group_id':group_id,'personal_group_rep_form':PersonalGroupReplyPostForm(),'is_js_env':is_js_env})
	else:
		return redirect("missing_page")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def post_to_personal_group(request, *args, **kwargs):
	"""
	Submit a text post, image post or a direct response
	"""
	if request.method == 'POST':
		own_id, target_id = request.user.id, request.POST.get('tid',None)
		request.session["personal_group_tid_key"] = target_id
		group_id, exists = personal_group_already_exists(own_id, target_id)
		if exists:
			request.session["personal_group_gid_key:"+target_id] = group_id
			is_ajax = request.is_ajax()
			sk_form, sk_redis = str(request.POST.get('sk','0')), get_and_delete_photo_upload_key(user_id=own_id, group_id=group_id)
			if sk_form != sk_redis:
				request.session["personal_group_form_error"] = PERSONAL_GROUP_ERR['mismatch']
				request.session.modified = True
				if is_ajax:
					return HttpResponse(json.dumps({'success':False,'message':reverse('enter_personal_group')}),content_type='application/json',)
				else:
					return redirect("enter_personal_group")
			else:
				is_direct_response = request.POST.get('dr',None)
				on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
				form = PersonalGroupPostForm(request.POST,request.FILES,on_fbs = on_fbs)
				if form.is_valid():
					image_file = request.FILES.get('image')
					reply = form.cleaned_data.get("reply")
					if (image_file and reply) or image_file:
						if personal_group_image_transfer_not_permitted(target_id, group_id):
							request.session["personal_group_image_xfer_no_permit"] = True
							if personal_group_photo_xfer_invite_allwd(target_id, group_id):
								#'1' signifies photo permission notification
								add_content_to_personal_group(content='1', type_='notif', writer_id=own_id, group_id=group_id)
								private_chat_tasks.delay(own_id=own_id,target_id=target_id,group_id=group_id,posting_time=time.time(),text=PRIV_CHAT_NOTIF['1'],\
									txt_type='notif',own_anon='',target_anon='',blob_id='', idx='', img_url='',own_uname='',own_avurl='',deleted='undel',\
									hidden='no')
						else:
							reoriented = request.POST.get('reoriented',None)
							resized = request.POST.get('resized',None)
							quality = None if on_fbs else True
							image_to_upload, img_width, img_height = process_personal_group_image(image=image_file, quality=quality, already_resized=resized, \
								already_reoriented=reoriented)
							if not image_to_upload and img_height == 'too_high':
								request.session["personal_group_form_error"] = PERSONAL_GROUP_ERR['too_high']
								request.session.modified = True
								if is_ajax:
									return HttpResponse(json.dumps({'success':False,'message':reverse('enter_personal_group')}),content_type='application/json',)
								else:
									return redirect("enter_personal_group")
							else:
								uploaded_image_loc = upload_image_to_s3(image_to_upload)
								content = {'img_url':uploaded_image_loc, 'img_width':img_width, 'img_height':img_height, 'img_caption':reply}
								if is_direct_response:
									target_content_type = request.POST.get('tt',None)
									target_blob_id = request.POST.get('bid',None)
									target_index = request.POST.get('idx',None)
									if target_index and target_blob_id and target_content_type:
										# add as a 'response' blob
										res_blob,type_ = {'target_blob_id':target_blob_id,'target_index':target_index,'target_content_type':target_content_type},\
										'img_res'
										obj_count, obj_ceiling, gid, bid, idx, img_id, img_wid, hw_ratio = add_content_to_personal_group(content=content, \
											type_=type_, writer_id=own_id, group_id=group_id, res_blob=res_blob)
										add_image_to_personal_group_storage.delay(uploaded_image_loc, img_id, img_wid, hw_ratio, quality, bid, idx, own_id, \
											gid)
									else:
										# add normally to existing blobs
										type_='img'
										obj_count, obj_ceiling, gid, bid, idx, img_id, img_wid, hw_ratio = add_content_to_personal_group(content=content, \
											type_=type_, writer_id=own_id, group_id=group_id)
										add_image_to_personal_group_storage.delay(uploaded_image_loc, img_id, img_wid, hw_ratio, quality, bid, idx, own_id, gid)
								else:
									# add normally to existing blobs
									type_='img'
									obj_count, obj_ceiling, gid, bid, idx, img_id, img_wid, hw_ratio = add_content_to_personal_group(content=content, \
										type_=type_, writer_id=own_id, group_id=group_id)
									add_image_to_personal_group_storage.delay(uploaded_image_loc, img_id, img_wid, hw_ratio, quality, bid, idx, own_id, gid)
								private_chat_tasks.delay(own_id=own_id,target_id=target_id,group_id=group_id,posting_time=time.time(),text=reply,txt_type=type_,\
									own_anon='',target_anon='',blob_id=bid, idx=idx, img_url=uploaded_image_loc,own_uname='',own_avurl='',deleted='undel',\
									hidden='no',successful=True if bid else False)
								personal_group_sanitization(obj_count, obj_ceiling, gid)
					elif reply:
						if is_direct_response:
							target_content_type = request.POST.get('tt',None)
							target_blob_id = request.POST.get('bid',None)
							target_index = request.POST.get('idx',None)
							if target_blob_id and target_index and target_content_type:
								# add as a 'response' blob
								res_blob,type_ = {'target_blob_id':target_blob_id,'target_index':target_index,'target_content_type':target_content_type},'text_res'
								obj_count, obj_ceiling, gid, bid, idx, img_id, img_wid, hw_ratio = add_content_to_personal_group(content=reply, \
									type_=type_, writer_id=own_id, group_id=group_id, res_blob=res_blob)
							else:
								# add normally to existing blobs
								type_='text'
								obj_count, obj_ceiling, gid, bid, idx, img_id, img_wid, hw_ratio = add_content_to_personal_group(content=reply, type_=type_, \
									writer_id=own_id, group_id=group_id)
						else:
							type_='text'
							obj_count, obj_ceiling, gid, bid, idx, img_id, img_wid, hw_ratio = add_content_to_personal_group(content=reply, type_=type_, \
								writer_id=own_id, group_id=group_id)
						private_chat_tasks.delay(own_id=own_id,target_id=target_id,group_id=group_id,posting_time=time.time(),text=reply,txt_type=type_,\
							own_anon='',target_anon='',blob_id=bid, idx=idx, img_url='',own_uname='',own_avurl='',deleted='undel',hidden='no',\
							successful=True if bid else False)
						personal_group_sanitization(obj_count, obj_ceiling, gid)
					else:
						pass
					request.session.modified = True
					if is_ajax:
						return HttpResponse(json.dumps({'success':True,'message':reverse('enter_personal_group')}),content_type='application/json',)
					else:
						return redirect("enter_personal_group")
				else:
					if is_direct_response:
						request.session.modified = True
						if is_ajax:
							# should NEVER fire, since JS/AJAX-powered direct_response is handled by "post_js_reply_to_personal_group"
							return HttpResponse(json.dumps({'success':False,'message':reverse('enter_personal_group')}),content_type='application/json',)
						else:
							content = request.POST.get('ct',None)
							content_type = request.POST.get('tt',None)
							blob_id = request.POST.get('bid',None)
							index = request.POST.get('idx',None)
							if not (content_type and blob_id and index):
								return redirect("enter_personal_group")
							else:
								s_caption = request.POST.get("scp",None)
								caption = request.POST.get("cp",None)
								t_time = request.POST.get("t",None)
								their_nick = request.POST.get("tn",None)
								t_av_url = request.POST.get("tau",None)
								t_uname = request.POST.get("tun",None)
								secret_key = uuid.uuid4()
								set_photo_upload_key(user_id=own_id, group_id=group_id, secret_key=secret_key)
								return render(request,"personal_group/direct_response/personal_group_direct_response.html",\
									{'tun':t_uname,'tau':t_av_url,'tt':content_type,'ct':content,'caption':caption,'idx':index,\
									's_caption':s_caption,'time':t_time,'sk':secret_key,'personal_group_form':form,'bid':blob_id,\
									'tid':target_id,'their_nick':True if their_nick == 'True' else False})
					else:
						try:
							request.session["personal_group_form_error"] = form.errors.as_text().split("*")[2]
						except IndexError:
							# form was invalid, but we couldn't parse the error string so return a generic error
							request.session["personal_group_form_error"] = PERSONAL_GROUP_ERR['generic']
						request.session.modified = True
						if is_ajax:
							return HttpResponse(json.dumps({'success':False,'message':reverse('enter_personal_group')}),content_type='application/json',)
						else:
							return redirect("enter_personal_group")
		else:
			return redirect("missing_page")
	else:
		return redirect("enter_personal_group")



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def delete_post_from_personal_group(request):
	"""
	Delete/undelete single chat post from personal group
	"""
	if request.method == "POST":
		own_id = request.user.id
		decision = request.POST.get('dec',None)
		undelete = request.POST.get('un',None)
		target_blob_id = request.POST.get("bid", None)
		target_index = request.POST.get("idx", None)
		target_id = request.POST.get("tid", None)
		group_id, exists = personal_group_already_exists(own_id, target_id)
		if exists:
			if decision == '1':
				action = 'undel' if undelete == '1' else 'del'
				deleted, ttl = delete_or_hide_chat_from_personal_group(blob_id=target_blob_id, idx=target_index, own_id=own_id, group_id=group_id, \
					img_id=None, action=action)#img_id is used in 'hiding', not needed here
				if deleted:
					update_notif_object_del.delay(action=action,blob_id=target_blob_id,idx=target_index,group_id=group_id)
				elif ttl and not deleted:
					return render(request,"personal_group/deletion/personal_group_cant_delete_chat.html",{'ttl':ttl,'un':undelete,\
						'one_post':True,'tid':target_id})
			request.session["personal_group_tid_key"] = target_id
			request.session["personal_group_gid_key:"+target_id] = group_id#checked
			request.session.modified = True
			return redirect("enter_personal_group")
		else:
			return redirect("personal_group_user_listing")
	else:
		return redirect("enter_personal_group")



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_own_chat_buttons(request):
	"""
	Handling user controls in own chat
	"""
	if request.method == "POST":
		own_id = request.user.id
		decision = request.POST.get("dec",None)
		if decision == '1':
			# own chat deletion
			payload = request.POST.get('pl',None)
			content = request.POST.get('pl_ct',None)
			image_caption = request.POST.get('imc',None)
			original_poster = request.POST.get('op',None)
			payload = payload.split(":")
			try:
				blob_id, index, username, tt, posting_time, av_url, is_res, target_id, own_nick, their_nick, img_width = payload[0], \
				payload[1], payload[2], payload[3], payload[4], payload[5], payload[6], payload[7], payload[8], payload[9], payload[10]
			except IndexError:
				return redirect("enter_personal_group")
			group_id, exists = personal_group_already_exists(own_id, target_id)
			if exists:	
				context = {'tt':tt, 'usr':username, 'ct':content, 'aurl':av_url, 't':posting_time, 'imc':image_caption, 'is_res':is_res,'idx':index,\
				'delete_single_chat':True,'own_nick':own_nick,'their_nick':their_nick,'img_width':img_width,'tid':target_id,'bid':blob_id,\
				'original_poster':original_poster}
				if is_res == 'res':
					target_content = request.POST.get('rpl_ct',None)
					direct_response_payload = request.POST.get('rpl',None)
					direct_response_payload = direct_response_payload.split(":")
					try:
						target_username, target_av_url, target_content_type, target_posting_time, target_status = direct_response_payload[0], \
						direct_response_payload[1], direct_response_payload[2], direct_response_payload[3], direct_response_payload[4]
					except IndexError:
						request.session["personal_group_tid_key"] = target_id
						request.session["personal_group_gid_key:"+target_id] = group_id
						request.session.modified = True
						return redirect("enter_personal_group")	
					context["t_ic"],context["t_isc"] = request.POST.get('t_ic',None),request.POST.get('t_isc',None)
					context["t_usr"],context["t_aurl"],context["t_tt"],context["t_t"],context["t_ct"],context["t_st"] = target_username, \
					target_av_url, target_content_type, target_posting_time,target_content,target_status
				post_status = check_single_chat_current_status(blob_id=blob_id, idx=index, own_id=own_id, group_id=group_id)
				if post_status == 'del':
					context["undelete"] = True
					return render(request,"personal_group/deletion/personal_group_chat_deletion.html",context)
				elif post_status == 'undel':
					return render(request,"personal_group/deletion/personal_group_chat_deletion.html",context)
				else:
					# if item doesn't exist any more (e.g. was mass deleted)
					request.session["personal_group_tid_key"] = target_id
					request.session["personal_group_gid_key:"+target_id] = group_id
					request.session.modified = True
					return redirect("enter_personal_group")
			else:
				return redirect("missing_page")
		elif decision == '2':
			# own chat saving
			payload = request.POST.get('pl',None)
			content = request.POST.get('pl_ct',None)
			image_caption = request.POST.get('imc',None)
			payload = payload.split(":")
			try:
				blob_id, index, username, tt, posting_time, av_url, is_res, target_id, own_nick, their_nick, img_width, target_username, \
				target_av_url, target_content_type, target_posting_time, target_status = payload[0], payload[1], payload[2], payload[3], \
				payload[4], payload[5], payload[6], payload[7], payload[8], payload[9], payload[10], None, None, None, None, None
			except IndexError:
				return redirect("enter_personal_group")
			if is_res == 'res':
				direct_response_payload = request.POST.get('rpl',None)
				direct_response_payload = direct_response_payload.split(":")
				try:
					target_username, target_av_url, target_content_type, target_posting_time, target_status = direct_response_payload[0], \
					direct_response_payload[1], direct_response_payload[2], direct_response_payload[3], direct_response_payload[4]
				except IndexError:
					return redirect("enter_personal_group")	
			if own_nick == 'False':
				own_anon = True
				own_nick = False
			else:
				own_anon = False
				own_nick = True
			if their_nick == 'False':
				their_anon = True
				their_nick = False
			else:
				their_anon = False
				their_nick = True
			return render(request,"personal_group/saved_posts/personal_group_chat_saving.html",{'own_chat':True,'bgclass':PERSONAL_GROUP_OWN_BG,\
				'text_align':'text-align:right;','corner_class':'tr_cnr','their_bgclass':PERSONAL_GROUP_THEIR_BG,'own_anon':own_anon,'bid':blob_id,\
				'own_nick':own_nick,'css_shadow':'sh-r','their_text_align':'text-align:left','their_corner_class':'tl_cnr','their_tgt_anon':their_anon,\
				'their_tgt_nick':their_nick,'their_css_shadow':'sh-l','shadow_base_color':'#00E699','usr':username,'aurl':av_url,'idx':index,'ct':content,\
				'tt':tt,'img_width':img_width,'time':posting_time,'img_cap':image_caption,'t_usr':target_username,'is_res':is_res,'tid':target_id,\
				't_aurl':target_av_url,'t_st':target_status,'t_tt':target_content_type,'t_time':target_posting_time,'t_ct':request.POST.get('rpl_ct',None),\
				't_img_cap':request.POST.get('t_isc',None),'bclass':PERSONAL_GROUP_OWN_BORDER,'their_bclass':PERSONAL_GROUP_THEIR_BORDER,\
				'original_poster':request.POST.get('op',None)})
		else:
			return redirect("enter_personal_group")
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_their_chat_buttons(request):
	"""
	Handling user controls in 'their' chat
	"""
	if request.method == "POST":
		decision = request.POST.get('dec',None)
		if decision == '1':
			# direct_response
			payload = request.POST.get('pl',None)
			payload = payload.split(":")
			try:
				bid, usr, idx, time, tt, tid, img_width, their_nick, own_nick, is_res, av_url, own_id = payload[0], payload[1], payload[2], payload[3], \
				payload[4], payload[5], payload[6], payload[7], payload[8], payload[9], payload[10], request.user.id
			except IndexError:
				return redirect("enter_personal_group")
			group_id, exists = personal_group_already_exists(own_id, tid)
			if exists:
				ct, secret_key = request.POST.get('pl_ct',None), uuid.uuid4()
				set_photo_upload_key(user_id=own_id, group_id=group_id, secret_key=secret_key)
				return render(request,"personal_group/direct_response/personal_group_direct_response.html",{'tun':usr,'tau':av_url,\
					'tt':tt,'ct':ct,'caption':request.POST.get('cp',None),'s_caption':request.POST.get('scp',None),'time':time, \
					'sk':secret_key,'tid':tid,'ct':ct,'personal_group_form':PersonalGroupPostForm(),'bid':bid,'idx':idx,'tt':tt,\
					'their_nick':True if their_nick == 'True' else False})
			else:
				return redirect("missing_page")	
		elif decision == '2':
			# save their post, generalize all if clauses
			payload = request.POST.get('pl',None)
			payload = payload.split(":")
			try:
				bid, usr, idx, time, tt, tid, img_width, their_nick, own_nick, is_res, av_url, t_usr, t_st, t_tt, t_time, t_aurl = payload[0], \
				payload[1], payload[2], payload[3], payload[4], payload[5], payload[6], payload[7], payload[8], payload[9], payload[10], None, \
				None, None, None, None
			except IndexError:
				return redirect("enter_personal_group")
			if not is_save_permission_granted_by_target(request.user.id,tid):
				request.session["personal_group_save_chat_no_permit"] = True
				request.session["personal_group_tid_key"] = tid
				request.session.modified = True
				return redirect("enter_personal_group")
			else:
				target_payload = request.POST.get('t_pl',None)
				if target_payload:
					target_payload = target_payload.split(":")
					try:
						t_usr, t_st, t_tt, t_time, t_aurl = target_payload[0], target_payload[1], target_payload[2], target_payload[3], target_payload[4]
					except IndexError:
						return redirect("enter_personal_group")
				if their_nick == 'True':
					their_anon = False
					their_nick = True
				else:
					their_anon = True
					their_nick = False
				if own_nick == 'True':
					own_anon = False
					own_nick = True
				else:
					own_anon = True
					own_nick = False
				return render(request,"personal_group/saved_posts/personal_group_chat_saving.html",{'their_chat':True,'bgclass':PERSONAL_GROUP_THEIR_BG,\
					'text_align':'','corner_class':'tl_cnr','their_nick':their_nick,'their_bgclass':PERSONAL_GROUP_OWN_BG,'bclass':PERSONAL_GROUP_THEIR_BORDER,\
					'their_anon':their_anon,'bid':bid,'css_shadow':'sh-l','their_text_align':'text-align:right','their_corner_class':'tr_cnr','own_tgt_anon':own_anon,\
					'own_tgt_nick':own_nick,'their_css_shadow':'sh-r','shadow_base_color':'#68D0FD','usr':usr,'aurl':av_url,'tt':tt,'t_time':t_time,'t_usr':t_usr,\
					'ct':request.POST.get('pl_ct',None),'idx':idx,'img_cap':request.POST.get('cp',None),'img_width':img_width,'time':time,'is_res':is_res,'tid':tid,\
					't_st':t_st,'t_tt':t_tt,'t_ct':request.POST.get('t_pl_ct',None),'t_img_cap':request.POST.get('t_scp',None),'their_bclass':PERSONAL_GROUP_OWN_BORDER,\
					't_aurl':t_aurl,'original_poster':request.POST.get('op',None)})
		elif decision == '3':
			# hide/unhide
			payload = request.POST.get('pl',None)
			content = request.POST.get('pl_ct',None)
			hide_action = 'hide' if request.POST.get('hval',None) == 'True' else 'unhide'
			payload = payload.split(":")
			return render(request,"personal_group/photos/personal_group_hide_photo.html",{'action':hide_action,'img_url':content,'bid':payload[0],'idx':payload[2],\
				'tid':payload[5],'iid':request.POST.get('iid',None)})
		else:
			return redirect("enter_personal_group")
	else:
		return redirect("enter_personal_group")		


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def save_post_in_personal_group(request):
	"""
	Processes post saving in personal group
	"""
	if request.method == "POST":
		decision = request.POST.get('dec',None)
		target_id = request.POST.get("tid",None)
		if decision == '0':
			request.session["personal_group_tid_key"] = target_id
			return redirect("enter_personal_group")
		else:
			own_id = request.user.id
			own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, target_id)
			if their_anon_status is None:
				return redirect("personal_group_user_listing")
			else:
				blob_id = request.POST.get("bid",None)
				index = request.POST.get("idx",None)
				is_saved, msg, ttl = save_personal_group_content(own_id, target_id, group_id, blob_id, index)
				their_uname, their_avurl = get_uname_and_avurl(target_id,their_anon_status)
				return render(request,"personal_group/saved_posts/personal_group_saved_posts.html",{'name':their_uname,'own_id':own_id,'ttl':ttl,\
				'all_saved_posts':retrieve_personal_group_saved_content(own_id,target_id,group_id),'bgclass':PERSONAL_GROUP_OWN_BG,'save_status':is_saved,\
				'their_bgclass':PERSONAL_GROUP_THEIR_BG,'own_anon':own_anon_status,'their_anon':their_anon_status,'tid':target_id,'msg':msg,\
				'avatar':their_avurl,'saved':True,'curr_perm':own_save_permission_status(own_id,group_id),'bclass':PERSONAL_GROUP_OWN_BORDER,\
				'their_bclass':PERSONAL_GROUP_THEIR_BORDER})
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def show_all_saved_posts_in_personal_group(request):
	"""
	Shows list of all saved posts in a personal group
	"""
	if request.method == "POST":
		own_id, target_id = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, target_id)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			their_uname, their_avurl = get_uname_and_avurl(target_id,their_anon_status)
			return render(request,"personal_group/saved_posts/personal_group_saved_posts.html",{'own_id':own_id,'name':their_uname,'avatar':their_avurl,\
				'all_saved_posts':retrieve_personal_group_saved_content(own_id,target_id,group_id),'bgclass':PERSONAL_GROUP_OWN_BG,'their_anon':their_anon_status,\
				'their_bgclass':PERSONAL_GROUP_THEIR_BG,'own_anon':own_anon_status,'curr_perm':own_save_permission_status(own_id,group_id),'tid':target_id,\
				'bclass':PERSONAL_GROUP_OWN_BORDER,'their_bclass':PERSONAL_GROUP_THEIR_BORDER})
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_delete_saved_post(request):
	"""
	Delete single (or all) saved post(s) from personal group
	"""
	if request.method == "POST":
		own_id, target_id = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, target_id)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			delete_all = request.POST.get("dall",None)
			saved_blob_id = request.POST.get("bid",None)
			deleted, deleted_everything = None, None
			if delete_all == '1':
				if request.POST.get('dec',None) == '1':
					deleted_everything = delete_all_personal_group_saved_content(own_id, group_id)
				else:
					request.session["personal_group_tid_key"] = target_id
					request.session["personal_group_gid_key:"+target_id] = group_id
					request.session.modified = True
					return redirect("enter_personal_group")
			elif saved_blob_id:
				deleted = delete_single_personal_group_saved_content(own_id, group_id, saved_blob_id)
			else:
				pass
			their_uname, their_avurl = get_uname_and_avurl(target_id,their_anon_status)
			return render(request,"personal_group/saved_posts/personal_group_saved_posts.html",{'their_anon':their_anon_status,\
				'all_saved_posts':retrieve_personal_group_saved_content(own_id,target_id,group_id),'bgclass':PERSONAL_GROUP_OWN_BG,'own_id':own_id,\
				'their_bgclass':PERSONAL_GROUP_THEIR_BG,'own_anon':own_anon_status,'name':their_uname,'tid':target_id,'avatar':their_avurl,\
				'deleted_everything':True if deleted_everything else False,'curr_perm':own_save_permission_status(own_id,group_id),\
				'bclass':PERSONAL_GROUP_OWN_BORDER,'their_bclass':PERSONAL_GROUP_THEIR_BORDER,'deleted':True if deleted else False})
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_grant_chat_saving_perm(request):
	"""
	Allow other user to save own chat in personal group
	"""
	if request.method == "POST":
		own_id, target_id = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, target_id)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			decision = request.POST.get("dec",None)
			final_decision = request.POST.get("fdec",None)
			if final_decision == '1':
				perm_set = toggle_save_permission(own_id, group_id)
				if perm_set in ('1','0'):
					their_uname, their_avurl = get_uname_and_avurl(target_id,their_anon_status)
					return render(request,"personal_group/saved_posts/personal_group_saved_posts.html",{'own_id':own_id,'avatar':their_avurl,\
					'all_saved_posts':retrieve_personal_group_saved_content(own_id,target_id,group_id),'bgclass':PERSONAL_GROUP_OWN_BG,'new_save_perm':True,\
					'their_bgclass':PERSONAL_GROUP_THEIR_BG,'own_anon':own_anon_status,'their_anon':their_anon_status,'tid':target_id,'new_perm':perm_set,\
					'name':their_uname,'curr_perm':perm_set,'bclass':PERSONAL_GROUP_OWN_BORDER,'their_bclass':PERSONAL_GROUP_THEIR_BORDER})
				else:
					request.session["personal_group_tid_key"] = target_id
					request.session["personal_group_gid_key:"+target_id] = group_id
					request.session.modified = True
					return redirect("enter_personal_group")
			elif final_decision == 'Cancel':
				their_uname, their_avurl = get_uname_and_avurl(target_id,their_anon_status)
				return render(request,"personal_group/saved_posts/personal_group_saved_posts.html",{'own_id':own_id,'avatar':their_avurl,'tid':target_id,\
				'all_saved_posts':retrieve_personal_group_saved_content(own_id,target_id,group_id),'bgclass':PERSONAL_GROUP_OWN_BG,'their_anon':their_anon_status,\
				'their_bgclass':PERSONAL_GROUP_THEIR_BG,'own_anon':own_anon_status,'curr_perm':request.POST.get("cp",None),'name':their_uname,\
				'bclass':PERSONAL_GROUP_OWN_BORDER,'their_bclass':PERSONAL_GROUP_THEIR_BORDER})
			elif decision == '1':
				current_permission = request.POST.get("cp",None)
				their_uname, their_avurl = get_uname_and_avurl(target_id,their_anon_status)
				if current_permission == '0' and tutorial_unseen(user_id=own_id, which_tut='2', renew_lease=True):
					return render(request,"personal_group/saved_posts/grant_save_permission_warning.html",{'their_anon':their_anon_status,\
						'avatar':their_avurl,'name':their_uname,'tid':target_id,'cp':current_permission})
				perm_set = toggle_save_permission(own_id, group_id)
				if perm_set in ('1','0'):
					their_uname, their_avurl = get_uname_and_avurl(target_id,their_anon_status)
					return render(request,"personal_group/saved_posts/personal_group_saved_posts.html",{'own_id':own_id,'name':their_uname,\
					'all_saved_posts':retrieve_personal_group_saved_content(own_id,target_id,group_id),'bgclass':PERSONAL_GROUP_OWN_BG,'new_save_perm':True,\
					'their_bgclass':PERSONAL_GROUP_THEIR_BG,'own_anon':own_anon_status,'their_anon':their_anon_status,'tid':target_id,'new_perm':perm_set,\
					'avatar':their_avurl,'curr_perm':perm_set,'bclass':PERSONAL_GROUP_OWN_BORDER,'their_bclass':PERSONAL_GROUP_THEIR_BORDER})
				else:
					request.session['personal_group_tid_key'] = target_id
					request.session["personal_group_gid_key:"+target_id] = group_id
					request.session.modified = True
					return redirect("enter_personal_group")
			else:
				request.session['personal_group_tid_key'] = target_id
				request.session["personal_group_gid_key:"+target_id] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")
	else:
		return redirect("enter_personal_group")

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def hide_photo_from_personal_group_chat(request):
	"""
	Hiding/unhiding photo from chat
	"""
	if request.method == 'POST':
		decision = request.POST.get('dec',None)
		target_id = request.POST.get('tid',None)
		if decision == '0':
			request.session['personal_group_tid_key'] = target_id
			request.session.modified = True
			return redirect("enter_personal_group")
		else:
			own_id = request.user.id
			group_id, exists = personal_group_already_exists(own_id, target_id)
			if exists:
				blob_id = request.POST.get("bid",None)
				idx = request.POST.get('idx',None)
				img_id = request.POST.get("iid",None)
				request.session['personal_group_tid_key'] = target_id
				request.session["personal_group_gid_key:"+target_id] = group_id
				request.session.modified = True
				if not (blob_id and idx and img_id):
					return redirect("enter_personal_group")
				else:
					action = request.POST.get('act',None)#values are either 'hide' or 'unhide' (i.e. 'hide' if request.POST.get('hval',None) == 'True' else 'unhide')
					hidden, ttl = delete_or_hide_chat_from_personal_group(blob_id, idx, own_id, group_id, img_id, action=action)
					if hidden:
						update_notif_object_hide.delay(action=action,blob_id=blob_id,idx=idx,group_id=group_id)
					elif ttl and not hidden:
						return render(request,"personal_group/deletion/personal_group_cant_delete_chat.html",{'ttl':ttl,'act':action,\
							'one_photo':True,'tid':target_id})
					return redirect("enter_personal_group")
			else:
				return redirect("personal_group_user_listing")
	else:
		return redirect("personal_group_user_listing")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def post_chat_action_in_personal_group(request):
	"""
	Render chat actions in personal groups
	"""
	if request.method == "POST":
		own_id, target_id = request.user.id, request.POST.get('tid',None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, target_id)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			option = request.POST.get('opt',None)
			if option == '6':
				their_uname, their_avurl = get_uname_and_avurl(target_id,their_anon_status)
				return render(request,"personal_group/general_settings/personal_group_all_settings.html",{'their_anon':their_anon_status,\
					'avatar':their_avurl,'name':their_uname,'own_anon':own_anon_status,'tid':target_id})
			elif option in ('1','2','3','4','5'):
				obj_count, obj_ceiling, gid, bid, idx, img_id, img_wid, hw_ratio = add_content_to_personal_group(content=option, type_='action', \
					writer_id=own_id, group_id=group_id)
				private_chat_tasks.delay(own_id=own_id,target_id=target_id,group_id=group_id,posting_time=time.time(),text=PRIV_CHAT_EMOTEXT[option],\
					txt_type='action',own_anon='1' if own_anon_status else '0',target_anon='1' if their_anon_status else '0',blob_id=bid, idx=idx, \
					img_url='',own_uname='',own_avurl='',deleted='undel',hidden='no',successful=True if bid else False)
				personal_group_sanitization(obj_count, obj_ceiling, gid)
			else:
				pass
			request.session['personal_group_tid_key'] = target_id
			request.session["personal_group_gid_key:"+target_id] = group_id
			request.session.modified = True
			return redirect("enter_personal_group")		
	else:		
		return redirect("enter_personal_group")


def kick_from_group(request):
	"""
	Kick user from group without banning them.

	This is essentially a warning shot
	"""
	return render(request,"404.html",{})

def ban_from_group(request):
	"""
	Remove user from group till set passage of time.
	"""
	return render(request,"404.html",{})

def set_group_theme(request):
	"""
	Use to change group's wallpapers, etc.
	"""
	return render(request,"404.html",{})


def get_group_theme(request):
	"""
	Use to get group's theme.
	"""
	return render(request,"404.html",{})



def set_group_type(request):
	"""
	This sets group type (e.g. public, private)
	"""
	return render(request,"404.html",{})

def set_user_perms_for_group(request):
	"""
	This sets group permissions for a user (e.g. is the user an officer)

	"""
	return render(request,"404.html",{})

def get_user_perms_for_group(request):
	"""
	Get group permissions for a user
	"""
	return render(request,"404.html",{})


def x_per_grp_notif(request, gid, fid, from_home):
	"""
	Used to skip personal group notification
	"""
	own_id = request.user.id
	group_id, exists = personal_group_already_exists(own_id, fid)
	if exists and group_id == str(gid):
		skip_private_chat_notif(own_id, group_id,curr_time=time.time(),seen=True)
	if from_home == '1':
		return redirect("home")
	elif from_home == '2':
		return redirect("best_photo")
	else:
		return redirect("photo")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def unseen_per_grp(request, gid, fid):
	"""
	Processes reply given in personal group straight from a notification
	"""
	if request.method == "POST":
		own_id = request.user.id
		own_uname = get_target_username(str(own_id))
		group_id, exists = personal_group_already_exists(own_id, fid)
		if exists and group_id == str(gid):
			origin, lang, sort_by = request.POST.get("origin",None), request.POST.get("lang",None), request.POST.get("sort_by",None)
			form = UnseenActivityForm(request.POST,user_id=own_id, prv_grp_id='',pub_grp_id='',photo_id='',link_id='',per_grp_id=group_id)
			if form.is_valid():
				text, type_ = form.cleaned_data.get("personal_group_reply"), 'text'
				obj_count, obj_ceiling, gid, bid, idx, img_id, img_wid, hw_ratio = add_content_to_personal_group(content=text, type_=type_, \
					writer_id=own_id, group_id=group_id)
				private_chat_tasks.delay(own_id=own_id,target_id=fid,group_id=group_id,posting_time=time.time(),text=text,txt_type=type_,\
					own_anon='',target_anon='',blob_id=bid, idx=idx, img_url='',own_uname=own_uname,own_avurl='',deleted='undel',hidden='no',\
					successful=True if bid else False, from_unseen=True)
				personal_group_sanitization(obj_count, obj_ceiling, gid)
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
						return redirect("unseen_activity", own_uname)
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
						return redirect("unseen_activity", own_uname)
				else:
					notification = "np:"+str(own_id)+":5:"+group_id
					page_obj, oblist, forms, page_num, addendum = get_object_list_and_forms(request, notification)
					url = reverse_lazy("unseen_activity", args=[own_uname])+addendum
					forms[group_id] = form
					request.session["forms"] = forms
					request.session["oblist"] = oblist
					request.session["page_obj"] = page_obj
					request.session.modified = True
					return redirect(url)
		else:
			return redirect("unseen_activity", own_uname)
	else:
		return redirect("home")


###########################################################################################################
######################################### Personal Group Settings #########################################
###########################################################################################################

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_reentry(request):
	"""
	Reentering personal group after exiting it
	"""
	if request.method == "POST":
		own_id, tid = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, tid)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			exit_by_self, exit_by_them, sus_time = exit_already_triggered(own_id, tid, group_id, sus_time=True)
			if exit_by_self:
				# revert the group
				try:
					time_diff = time.time() - float(sus_time)
				except TypeError:
					time_diff = None
				if not time_diff:
					# no time stamp was returned - something is wrong
					their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
					return redirect(request,"personal_group/exit_settings/personal_group_exit_settings.html",{'their_anon':their_anon_status,\
					'avatar':their_avurl,'name':their_uname,'reentry_denied':True,'tid':tid})
				elif time_diff < ONE_DAY:
					# cant return yet - it's too soon
					their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
					return render(request,"personal_group/exit_settings/personal_group_exit_settings.html",{'reentry_too_soon':True,\
						'avatar':their_avurl,'name':their_uname,'their_anon':their_anon_status,'tid':tid,'time_remaining':ONE_DAY-time_diff})
				else:
					# re-enter normally, i.e. unsuspend group
					unsuspend_personal_group(own_id, tid, group_id)
					reset_all_group_chat(group_id) #permanently resetting group chat
					private_chat_tasks.delay(own_id=own_id,target_id=tid,group_id=group_id,posting_time=time.time(),text='reentry',txt_type='reentry',\
						own_anon='1' if own_anon_status else '0',target_anon='1' if their_anon_status else '0',blob_id='', idx='', img_url='',own_uname='',\
						own_avurl='',deleted='undel',hidden='no')
					request.session['personal_group_tid_key'] = tid
					request.session["personal_group_gid_key:"+tid] = group_id
					request.session.modified = True
					return redirect("enter_personal_group")
			elif exit_by_them:
				# user doesn't have the privilege to do this
				their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
				return redirect(request,"personal_group/exit_settings/personal_group_exit_settings.html",{'their_anon':their_anon_status,\
					'avatar':their_avurl,'name':their_uname,'reentry_denied':True,'tid':tid})
			else:
				request.session['personal_group_tid_key'] = tid
				request.session["personal_group_gid_key:"+tid] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_exit_settings(request):
	"""
	Exiting personal group
	"""
	if request.method == "POST":
		own_id, tid = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, tid)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			exit_by_self, exit_by_them = exit_already_triggered(own_id, tid, group_id)
			their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
			if exit_by_self or exit_by_them:
				return render(request,"personal_group/exit_settings/personal_group_exit_settings.html",{'their_anon':their_anon_status,\
					'you_already_exited':True if exit_by_self else False,'they_already_exited':True if exit_by_them else False,\
					'name':their_uname,'tid':tid,'avatar':their_avurl})
			else:
				exit_decision = request.POST.get('edec',None)
				if exit_decision == '1':
					successful, rate_limited = suspend_personal_group(suspended_by_id=own_id, their_id=tid, group_id=group_id)
					if rate_limited:
						their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
						return render(request,"personal_group/exit_settings/personal_group_exit_settings.html",{'time_to_suspend':rate_limited,\
							'avatar':their_avurl,'name':their_uname,'their_anon':their_anon_status,'tid':tid})
					elif successful == True:
						purge_all_saved_chat_of_user(own_id, tid, group_id)
						delete_all_user_chats_from_personal_group(own_id, group_id) #hides all user chat - not permanent deletion
						private_chat_tasks.delay(own_id=own_id,target_id=tid,group_id=group_id,posting_time=time.time(),text='exit',txt_type='exited',\
							own_anon='1' if own_anon_status else '0',target_anon='1' if their_anon_status else '0',blob_id='', idx='', img_url='',own_uname='',\
							own_avurl='',deleted='undel',hidden='no')
						their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
						return render(request,"personal_group/exit_settings/personal_group_exit_settings.html",{'were_sorry':True,\
							'avatar':their_avurl,'name':their_uname,'their_anon':their_anon_status,'tid':tid})
					elif successful == None:
						#you have already suspended it
						their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
						return render(request,"personal_group/exit_settings/personal_group_exit_settings.html",{'you_already_exited':True,\
							'avatar':their_avurl,'name':their_uname,'their_anon':their_anon_status,'tid':tid})
					elif successful == False:
						# you can't suspend it because the other person has suspended it
						request.session["personal_group_tid_key"] = tid
						request.session["personal_group_gid_key:"+tid] = group_id
						request.session.modified = True
						return redirect("enter_personal_group") 
					else:
						return redirect("missing_page")
				elif exit_decision == 'Cancel':
					request.session["personal_group_tid_key"] = tid
					request.session["personal_group_gid_key:"+tid] = group_id
					request.session.modified = True
					return redirect("enter_personal_group")
				else:
					their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
					return render(request,"personal_group/exit_settings/personal_group_exit_settings.html",{'name':their_uname,'tid':tid,\
						'avatar':their_avurl,'their_anon':their_anon_status})
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def delete_or_hide_photo_from_photo_settings(request):
	"""
	Delete/undelete a photo from settings
	"""
	if request.method == "POST":
		decision = request.POST.get('dec',None)
		image_data = request.POST.get('imgd',None)
		target_id = request.POST.get('tid',None)
		if decision is None:
			image_url = request.POST.get('phturl',None)
			photo_action = request.POST.get('actpht',None)
			if photo_action == '1':
				action = 'del'
			elif photo_action == '2':
				action = 'undel'
			elif photo_action == '3':
				action = 'hide'
			elif photo_action == '4':
				action = 'unhide'
			return render(request,"personal_group/photos/photo_settings/delete_photo_from_settings.html",\
				{'action':action,'img_url':image_url,'imgd':image_data,'tid':target_id})
		elif decision == '1':
			own_id = request.user.id
			group_id, exists = personal_group_already_exists(own_id, target_id)
			if exists:
				try:
					image_data = image_data.split(":")
					blob_id, idx, img_id = image_data[0],image_data[1],image_data[2]
				except (AttributeError,IndexError):
					pass
				action = request.POST.get('act',None)
				deleted, ttl = delete_or_hide_photo_from_settings(own_id, group_id, blob_id, idx, img_id, action=action)
				if deleted:
					if action in ('del','undel'):
						update_notif_object_del.delay(action=action,blob_id=blob_id,idx=idx,group_id=group_id)
					elif action in ('hide','unhide'):
						update_notif_object_hide.delay(action,blob_id,idx,group_id)
				elif not deleted and ttl:
					return render(request,"personal_group/deletion/personal_group_cant_delete_chat.html",{'ttl':ttl,'act':action,\
						'one_photo':True,'tid':target_id})
				request.session["personal_group_tid_key"] = target_id
				request.session["personal_group_gid_key:"+target_id] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")
			else:
				return redirect("personal_group_user_listing")
		elif decision == '0':
			request.session["personal_group_tid_key"] = target_id
			request.session.modified = True
			return redirect("enter_personal_group")
		else:
			return redirect("personal_group_user_listing")
	else:
		return redirect("enter_personal_group")		


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def delete_all_posts_from_personal_group(request):
	"""
	Used to cleanse/uncleanse personal group of all chat written in it. 
	"""
	if request.method == "POST":
		own_id, tid = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, tid)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			decision = request.POST.get('dec',None)
			if decision is None:
				their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
				return render(request,'personal_group/deletion/deletion_settings/wipe_personal_group_chat.html',\
					{'their_anon':their_anon_status,'name':their_uname,'avatar':their_avurl,'tid':tid})
			elif decision == '1':
				undelete = request.POST.get('un',None)
				deleted, ttl = delete_all_user_chats_from_personal_group(own_id=own_id, group_id=group_id, undelete=undelete)
				if deleted:
					update_notif_object_del.delay(group_id, bulk_deletion=True)
				elif not deleted and ttl:
					return render(request,"personal_group/deletion/personal_group_cant_delete_chat.html",{'ttl':ttl,'un':undelete,\
						'all_chat':True,'tid':tid})
				request.session["personal_group_tid_key"] = tid
				request.session["personal_group_gid_key:"+tid] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")
			else:
				request.session["personal_group_tid_key"] = tid
				request.session["personal_group_gid_key:"+tid] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def anonymize_user_in_personal_group(request):
	"""
	Used to anonymize/unanonymize nicknames in personal group
	"""
	if request.method == "POST":
		own_id, tid = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, tid)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			decision =	request.POST.get('anon_dec',None)
			if decision is None:
				their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
				return render(request,"personal_group/anon_settings/personal_group_anonymize.html",{'their_anon':their_anon_status,'avatar':their_avurl,\
					'own_anon':own_anon_status,'name':their_uname,'tid':tid})
			elif decision == '1':
				their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
				new_value = set_personal_group_anon_state(own_id, tid)
				if new_value:
					update_notif_object_anon.delay(value=new_value,which_user=own_id,which_group=group_id)
					return render(request,"personal_group/anon_settings/personal_group_anonymize.html",{'their_anon':their_anon_status,\
						'own_anon':False if new_value == '0' else True,'name':their_uname,'avatar':their_avurl,'new_anon_value':new_value,\
						'own_name':get_target_username(str(own_id)) if new_value == '1' else None,'tid':tid})
				else:
					return redirect("personal_group_user_listing")
			else:
				request.session["personal_group_tid_key"] = tid
				request.session["personal_group_gid_key:"+tid] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_photo_settings(request):
	"""
	Set photo settings for personal group
	"""
	if request.method == 'POST':
		new_phrec_value, new_phdel_value = None, None
		own_id, tid = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, tid)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			photo_setting = request.POST.get("phts",None)
			if photo_setting == '1':
				# photo reception permissions
				decision = request.POST.get("pht_dec",None)
				if decision == '1':
					new_phrec_value, ttl, garbage = toggle_personal_group_photo_settings(own_id=own_id,target_id=tid,setting_type=photo_setting, group_id=group_id)
				else:
					request.session["personal_group_tid_key"] = tid
					request.session["personal_group_gid_key:"+tid] = group_id
					request.session.modified = True
					return redirect("enter_personal_group")	
			elif photo_setting == '2':
				# photo mass-deletion setting
				decision = request.POST.get("pht_dec",None)
				if decision == '1':
					new_phdel_value, ttl, undelete = toggle_personal_group_photo_settings(own_id=own_id,target_id=tid,setting_type=photo_setting, group_id=group_id)
					if new_phdel_value == '1':
						update_notif_object_del.delay(group_id=group_id,bulk_deletion=True)
					elif new_phdel_value is None and ttl is not None:
						return render(request,"personal_group/deletion/personal_group_cant_delete_chat.html",{'ttl':ttl,'un':undelete,'all_photos':True,\
							'tid':tid})
				else:
					request.session["personal_group_tid_key"] = tid
					request.session["personal_group_gid_key:"+tid] = group_id
					request.session.modified = True
					return redirect("enter_personal_group")
			elif photo_setting == '3':
				# photo mass-restoration setting
				decision = request.POST.get("pht_dec",None)
				if decision == '1':
					new_phdel_value, ttl, undelete = toggle_personal_group_photo_settings(own_id=own_id,target_id=tid,setting_type=photo_setting, group_id=group_id)
					if new_phdel_value == '0':
						update_notif_object_del.delay(group_id=group_id,bulk_deletion=True)
					elif new_phdel_value is None and ttl is not None:
						return render(request,"personal_group/deletion/personal_group_cant_delete_chat.html",{'ttl':ttl,'un':undelete,'all_photos':True,\
							'tid':tid})
				else:
					request.session["personal_group_tid_key"] = tid
					request.session["personal_group_gid_key:"+tid] = group_id
					request.session.modified = True
					return redirect("enter_personal_group")
			else:
				pass
			pht_rec_perms = get_personal_group_photo_rec_settings(own_id, tid)
			if pht_rec_perms:
				their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
				photos = retrieve_all_personal_group_images(group_id)
				context = {'phrec':pht_rec_perms,'new_phrec_value':new_phrec_value,'their_anon':their_anon_status,'tid':tid,'name':their_uname,\
				'avatar':their_avurl,'photos':photos,'new_phdel_value':new_phdel_value,'num_phts':len(photos)}
				return render(request,"personal_group/photos/photo_settings/personal_group_photo_sharing.html",context)
			else:
				return redirect("personal_group_user_listing")
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def set_personal_group_photo_sharing_perm_from_chat(request):
	"""
	Directly sets photo sharing permissions from private chat
	"""
	if request.method == 'POST':
		own_id, target_id = request.user.id, request.POST.get('tid',None)
		group_id, exists = personal_group_already_exists(own_id,target_id)
		if exists is False:
			return redirect("personal_group_user_listing")
		else:
			decision, blob_id = request.POST.get('dec',None), request.POST.get('bid',None)
			if decision == '1':
				set_personal_group_photo_permission(own_id, group_id, blob_id, allow=True, resolve_notif=True)
			else:
				set_personal_group_photo_permission(own_id, group_id, blob_id, allow=False, resolve_notif=True)
			request.session["personal_group_tid_key"] = target_id
			request.session["personal_group_gid_key:"+target_id] = group_id
			request.session.modified = True
			return redirect("enter_personal_group")
	else:
		return redirect("enter_personal_group")	



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_send_sms(request):
	"""
	Processes SMS sending for private groups
	"""
	if request.method == "POST":
		own_id, tid = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, tid)
		smsrec = None
		if their_anon_status is None:
			return redirect("missing_page")
		else:
			sms_decision = request.POST.get("sdec",None)
			if sms_decision == '1':
				allwd, sms_text, mob_idx = get_user_sms_setting(tid, group_id, with_cred=True)
				if allwd:
					time_of_lock = sms_sending_locked(own_id,tid)
					if time_of_lock:
						their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
						# sms sending is rate limited
						secs_remaining = sms_lock_time_remaining(float(time_of_lock))
						return render(request,"personal_group/sms_settings/personal_group_cant_send_sms.html",{'time_remaining':secs_remaining,\
							'avatar':their_avurl,'tid':tid,'their_anon':their_anon_status,'name':their_uname})
					else:
						mobnums = get_user_verified_number(tid,country_code=True)
						try:
							target_number = mobnums[int(mob_idx)]
						except (ValueError,IndexError,TypeError):
							target_number = mobnums[0]
						queue_personal_group_invitational_sms.delay(mobile_number=target_number,sms_text=sms_text,own_id=own_id,target_id=tid, \
							sending_time=time.time())
						lock_sms_sending(own_id,tid)
						smsrec, sms_text, mob_idx = get_user_sms_setting(own_id, group_id, with_cred=True)
						their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
						return render(request,"personal_group/sms_settings/personal_group_sms_settings.html",{'their_anon':their_anon_status,'tid':tid,\
							'avatar':their_avurl,'name':their_uname,'smsrec':smsrec,'sms_text':sms_text,'sms_sent':True,'is_verified':request.mobile_verified})
				else:
					# get permission from tid, creating a notification (if allowed)
					send_invite_notif = personal_group_sms_invite_allwd(tid, group_id)
					if send_invite_notif:
						#'2' signifies sms permission notification
						add_content_to_personal_group(content='2', type_='notif', writer_id=own_id, group_id=group_id)
						private_chat_tasks.delay(own_id=own_id,target_id=tid,group_id=group_id,posting_time=time.time(),text=PRIV_CHAT_NOTIF['2'],\
							txt_type='notif',own_anon='1' if own_anon_status else '0',target_anon='1' if their_anon_status else '0',blob_id='', idx='', \
							img_url='',own_uname='',own_avurl='',deleted='undel',hidden='no')
					request.session["personal_group_sms_no_permit"] = True
					request.session["personal_group_tid_key"] = tid
					request.session["personal_group_gid_key:"+tid] = group_id
					request.session.modified = True
					return redirect("enter_personal_group")
			else:
				request.session["personal_group_tid_key"] = tid
				request.session["personal_group_gid_key:"+tid] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_sms_text_form(request):
	"""
	Renders form for personalized SMS
	"""
	if request.method == "POST":
		own_id, tid = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, tid)
		smsrec = None
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			sms_decision = request.POST.get("sdec",None)
			if sms_decision == '1':
				their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
				context={'avatar':their_avurl,'name':their_uname,'custom_text':True, 'form':PersonalGroupSMSForm(),'their_anon':their_anon_status,'tid':tid}
				return render(request,"personal_group/sms_settings/personal_group_sms_text.html",context)
			else:
				request.session["personal_group_tid_key"] = tid
				request.session["personal_group_gid_key:"+tid] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")		
	else:
		return redirect("enter_personal_group")



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_sms_settings(request):
	"""
	Set sms settings page for personal groups
	"""
	if request.method == 'POST':
		sms_setting = request.POST.get('ss',None)
		own_id, tid = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, tid)
		mobunver_rec, new_smsrec = None, None
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			smsrec, sms_text, mob_idx = get_user_sms_setting(own_id, group_id, with_cred=True)
			their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
			return render(request,"personal_group/sms_settings/personal_group_sms_settings.html",{'their_anon':their_anon_status,\
				'avatar':their_avurl,'name':their_uname,'smsrec':smsrec, 'new_smsrec':new_smsrec,'sms_text':sms_text,'tid':tid,\
				'fresh_visit':tutorial_unseen(user_id=own_id, which_tut='1', renew_lease=True),'is_verified':request.mobile_verified})
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_customize_sms_text(request):
	"""
	Processes customized SMS text for personal groups
	"""
	if request.method == "POST":
		own_id, tid = request.user.id, request.POST.get('tid',None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, tid)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			final_decision = request.POST.get('fdec',None)
			if final_decision == '1':
				form = PersonalGroupSMSForm(request.POST)
				if form.is_valid():
					sms = form.cleaned_data.get("sms")
					mobnums = get_user_verified_number(own_id)
					which_num = request.session.get('personal_group_target_mobnum_idx',None)
					try:
						target_number = mobnums[int(which_num)]
					except (ValueError,IndexError,TypeError):
						target_number = mobnums[0]
					enable_personal_group_sms_rec(own_id=own_id, group_id=group_id, target_num_idx=which_num, sms_text=create_sms_text('', sms, incl_uname=False))
					from_chat = request.POST.get('fch',None)
					if from_chat is None:
						smsrec, sms_text, mob_idx = get_user_sms_setting(own_id, group_id, with_cred=True)
						their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
						return render(request,"personal_group/sms_settings/personal_group_sms_settings.html",{'their_anon':their_anon_status,'tid':tid,\
						'avatar':their_avurl,'name':their_uname,'smsrec':smsrec,'sms_text':sms_text, 'new_smsrec':'1','is_verified':request.mobile_verified})
					else:
						request.session["personal_group_tid_key"] = tid
						request.session["personal_group_gid_key:"+tid] = group_id
						request.session.modified = True
						return redirect("enter_personal_group")
				else:
					their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
					context={'avatar':their_avurl,'name':their_uname,'custom_text':True,'their_anon':their_anon_status,'form':form,'tid':tid}
					return render(request,"personal_group/sms_settings/personal_group_sms_text.html",context)
			elif final_decision == 'Cancel':
				request.session["personal_group_tid_key"] = tid
				request.session["personal_group_gid_key:"+tid] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")
	else:
		return redirect("enter_personal_group")



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_sms_text(request):
	"""
	Turn on SMS perms, or redirect to 'customize sms' screen
	"""
	if request.method == "POST":
		own_id, tid = request.user.id, request.POST.get('tid',None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, tid)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			decision = request.POST.get('dec',None)
			request.session["personal_group_tid_key"] = tid
			request.session["personal_group_gid_key:"+tid] = group_id
			request.session.modified = True
			their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
			if decision == 'ok':
				mobnums = get_user_verified_number(own_id)
				which_num = request.session.get('personal_group_target_mobnum_idx',None)
				try:
					target_number = mobnums[int(which_num)]
				except (ValueError,IndexError,TypeError):
					target_number = mobnums[0]
				enable_personal_group_sms_rec(own_id=own_id, group_id=group_id, target_num_idx=which_num, \
					sms_text=create_sms_text(their_uname, PERSONAL_GROUP_DEFAULT_SMS_TXT))
				from_chat = request.POST.get("fch",None)
				if from_chat is None:
					smsrec, sms_text, mob_idx = get_user_sms_setting(own_id, group_id, with_cred=True)
					return render(request,"personal_group/sms_settings/personal_group_sms_settings.html",{'their_anon':their_anon_status,'tid':tid,\
					'avatar':their_avurl,'name':their_uname,'smsrec':smsrec,'sms_text':sms_text, 'new_smsrec':'1','is_verified':request.mobile_verified})
				else:
					return redirect("enter_personal_group")
			elif decision == 'chg':
				context={'avatar':their_avurl,'name':their_uname,'custom_text':True, 'form':PersonalGroupSMSForm(),'their_anon':their_anon_status,'tid':tid}
				return render(request,"personal_group/sms_settings/personal_group_sms_text.html",context)
			else:
				return redirect("enter_personal_group")		
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_receive_sms(request):
	"""
	"""
	if request.method == 'POST':
		own_id, tid = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, tid)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			sms_decision = request.POST.get("sdec",None)
			number_decision = request.POST.get("numdec",None)
			request.session["personal_group_tid_key"] = tid
			request.session["personal_group_gid_key:"+tid] = group_id
			request.session.modified = True
			if number_decision == '1':
				which_num = request.POST.get("mob",None)
				their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
				if which_num == 'new':
					CSRF = csrf.get_token(request)
					set_personal_group_target_id_and_csrf(own_id, tid, CSRF)
					return render(request,"personal_group/sms_settings/personal_group_new_mobile_number.html",{'csrf':CSRF,'tid':tid,\
						'avatar':their_avurl,'name':their_uname,'their_anon':their_anon_status})
				else:
					mobnums = get_user_verified_number(own_id)
					try:
						target_number = mobnums[int(which_num)]
					except (ValueError,IndexError,TypeError):
						target_number = mobnums[0]
					request.session["personal_group_target_mobnum_idx"] = which_num
					request.session.modified = True
					return render(request,"personal_group/sms_settings/personal_group_sms_text.html",{'their_anon':their_anon_status,\
						'avatar':their_avurl,'name':their_uname,'default_text':PERSONAL_GROUP_DEFAULT_SMS_TXT,'tid':tid})
			elif sms_decision == '1':
				sms_rec, sms_text, mob_idx = get_user_sms_setting(own_id, group_id, with_cred=True)
				their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
				if sms_rec:
					disable_personal_group_sms_rec(own_id=own_id, group_id=group_id)
					return render(request,"personal_group/sms_settings/personal_group_sms_settings.html",{'their_anon':their_anon_status,'tid':tid,\
					'avatar':their_avurl,'name':their_uname,'smsrec':False, 'new_smsrec':'0','is_verified':request.mobile_verified})
				else:
					already_verified = request.mobile_verified
					if already_verified:
						num_chg_allwd = can_change_number(own_id)
						mobnums = get_user_verified_number(own_id)
						how_many_nums = len(mobnums)
						if how_many_nums == 1 and not num_chg_allwd:
							context={'single_statement':True, 'name':their_uname,'mobnums':mobnums,'their_anon':their_anon_status,'tid':tid,\
							'avatar':their_avurl}
						else:
							context={'name':their_uname,'change_num':num_chg_allwd,'mobnums':mobnums,'their_anon':their_anon_status,'tid':tid,\
							'avatar':their_avurl}
						return render(request,"personal_group/sms_settings/personal_group_mobile_number_selection.html",context)
					else:
						CSRF = csrf.get_token(request)
						set_personal_group_target_id_and_csrf(own_id, tid, CSRF)
						mobunver_rec = '1'
						return render(request,"personal_group/sms_settings/personal_group_sms_settings.html",{'their_anon':their_anon_status,\
							'tid':tid,'name':their_uname,'smsrec':sms_rec, 'mobunver_rec':mobunver_rec,'csrf':CSRF,'sms_text':sms_text,\
							'avatar':their_avurl,'is_verified':request.mobile_verified})
			else:
				return redirect("enter_personal_group")		
	else:
		return redirect("enter_personal_group")


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def personal_group_receive_sms_from_chat(request):
	"""
	Accepting or rejecting sms invite from chat
	"""
	if request.method == "POST":
		own_id, tid = request.user.id, request.POST.get("tid",None)
		own_anon_status, their_anon_status, group_id = get_personal_group_anon_state(own_id, tid)
		if their_anon_status is None:
			return redirect("personal_group_user_listing")
		else:
			sms_decision = request.POST.get("sdec",None)
			number_decision = request.POST.get("numdec",None)
			if number_decision == '1':
				which_num = request.POST.get("mob",None)
				their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
				if which_num == 'new':
					CSRF = csrf.get_token(request)
					set_personal_group_target_id_and_csrf(own_id, tid, CSRF)
					return render(request,"personal_group/sms_settings/personal_group_new_mobile_number.html",{'csrf':CSRF,'tid':tid,\
						'avatar':their_avurl,'name':their_uname,'their_anon':their_anon_status})
				else:
					mobnums = get_user_verified_number(own_id)
					try:
						target_number = mobnums[int(which_num)]
					except (ValueError,IndexError,TypeError):
						target_number = mobnums[0]
					request.session["personal_group_target_mobnum_idx"] = which_num
					request.session.modified = True
					return render(request,"personal_group/sms_settings/personal_group_sms_text.html",{'their_anon':their_anon_status,\
						'avatar':their_avurl,'name':their_uname,'default_text':PERSONAL_GROUP_DEFAULT_SMS_TXT,'tid':tid,'from_chat':'1'})
			elif sms_decision == '1':
				bid = request.POST.get("bid",None)
				set_sms_notif_from_chat(group_id, tid, bid)
				already_verified = request.mobile_verified
				their_uname, their_avurl = get_uname_and_avurl(tid,their_anon_status)
				if already_verified:
					num_chg_allwd = can_change_number(own_id)
					mobnums = get_user_verified_number(own_id)
					how_many_nums = len(mobnums)
					if how_many_nums == 1 and not num_chg_allwd:
						context={'single_statement':True, 'name':their_uname,'mobnums':mobnums,'their_anon':their_anon_status,'from_chat':True,\
						'avatar':their_avurl,'tid':tid}
					else:
						context={'name':their_uname,'change_num':num_chg_allwd,'mobnums':mobnums,'their_anon':their_anon_status,'from_chat':True,\
						'avatar':their_avurl,'tid':tid}
					return render(request,"personal_group/sms_settings/personal_group_mobile_number_selection.html",context)
				else:
					CSRF = csrf.get_token(request)
					set_personal_group_target_id_and_csrf(own_id, tid, CSRF)
					return render(request,"personal_group/sms_settings/personal_group_new_mobile_number.html",{'their_anon':their_anon_status,\
					'avatar':their_avurl,'tid':tid,'name':their_uname,'csrf':CSRF,'from_chat':True})
			elif sms_decision == '0':
				bid = request.POST.get("bid",None)
				set_sms_notif_from_chat(group_id, tid, bid)
				request.session["personal_group_tid_key"] = tid
				request.session["personal_group_gid_key:"+tid] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")
			else:
				request.session["personal_group_tid_key"] = tid
				request.session["personal_group_gid_key:"+tid] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")
	else:
		return redirect("enter_personal_group")		



#######################################################################################################################
######################################### Personal Group Invite Functionality #########################################
#######################################################################################################################


def show_personal_group_invite_list(request):
	"""
	Displays list of all outstanding invites
	"""
	invite_accepted = request.session.pop("personal_group_invite_accepted",None)
	t_username = request.session.pop("personal_group_invite_accepted_username",None)
	t_av_url = request.session.pop("personal_group_invite_accepted_av_url",None)
	is_anon = request.session.pop("personal_group_invite_accepted_is_anon",None)
	tid = request.session.pop("personal_group_tid_key",None)
	invites, user_id, page_num = [], request.user.id, request.GET.get('page', '1')
	start_index, end_index = get_indices(page_num, OBJS_PER_PAGE_IN_USER_GROUP_INVITE_LIST)
	invite_list, time_gap, total_invites = return_invite_list(user_id, start_index, end_index)
	page_list = get_overall_page_list(total_invites, OBJS_PER_PAGE_IN_USER_GROUP_INVITE_LIST)
	for invite, expiry_time in invite_list:
		invite_tokens = invite.split(":")
		creation_time = expiry_time - time_gap
		invites.append((invite_tokens[0],invite_tokens[1].decode('utf-8'),invite_tokens[2],invite_tokens[3].decode('utf-8'),creation_time))
	return render(request,"personal_group/invites/personal_group_invite_list.html",{'invites':invites,'own_id':str(user_id),'invite_accepted':invite_accepted,\
		't_username':t_username,'tid':tid,'t_av_url':t_av_url,'is_anon':is_anon,'current_page':page_num,'pages':page_list,'num_pages':len(page_list)})

	
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def render_personal_group_invite(request):
	"""
	Renders private chat invite page
	"""
	if request.method == "POST":
		own_id, target_id = request.user.id, request.POST.get('tid',None)
		if own_id == target_id:
			return render(request,"personal_group/invites/personal_group_status.html",{'own_invite':True})
		else:
			parent_object_id, object_type, origin = request.POST.get('poid',None), request.POST.get('ot',None), request.POST.get('org',None)
			group_id, already_exists = personal_group_already_exists(own_id, target_id)
			if already_exists:
				request.session["personal_group_tid_key"] = target_id
				request.session["personal_group_gid_key:"+target_id] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")
			else:
				target_username, target_av_url = get_single_user_credentials(target_id,as_list=False)
				state, invite_sending_time, recently_declined = personal_group_invite_status(own_id, get_target_username(str(own_id)), \
					target_id, target_username)
				if state in ('0','1'):
					context = {'already_invited':True, 'target_av_url':target_av_url, 'tun':target_username,'it':invite_sending_time,\
					'poid':parent_object_id, 'org':origin}
					return render(request,"personal_group/invites/personal_group_status.html",context)
				elif state in ('2','3'):
					context ={'show_invite':True,'recently_declined':True if recently_declined else False,'target_av_url':target_av_url,\
					'tun':target_username,'it':invite_sending_time,'poid':parent_object_id,'org':origin,'is_anon':True if state == '3' else False}
					request.session["personal_group_invitation_sent_by_username"] = target_username
					request.session["personal_group_invitation_sent_by_id"] = target_id
					request.session["personal_group_invitation_sent_by_anon"] = True if state == '3' else False
					request.session.modified = True
					return render(request,"personal_group/invites/personal_group_status.html",context)
				else:
					request.session["personal_group_invite_target_username"], request.session["personal_group_invite_parent_object_id"], \
					request.session["personal_group_invite_object_type"], request.session["personal_group_invite_origin"], \
					request.session["personal_group_invite_target_id"], request.session["personal_group_invite_target_av_url"] = \
					target_username, parent_object_id, object_type, origin, target_id, target_av_url
					request.session.modified = True
					return render(request,"personal_group/invites/personal_group_status.html",{'invited':True,'tun':target_username,'target_av_url':\
						target_av_url,'org':origin,'poid':parent_object_id})
	return redirect("show_personal_group_invite_list")




@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def accept_personal_group_invite(request):
	"""
	Accept personal group invite and create group
	"""
	if request.method == "POST":
		if request.user_banned:
			return render(request,'500.html',{}) #errorbanning
		decision = request.POST.get("dec",None)
		if decision == '1':
			own_id, target_id = request.user.id, request.session.get("personal_group_invitation_sent_by_id",None)
			int_tid = int(target_id)
			username_dictionary = retrieve_bulk_unames([own_id,target_id],decode=True)
			own_username = username_dictionary[own_id]
			target_username = username_dictionary[int_tid]
			is_target_anon = request.session.get("personal_group_invitation_sent_by_anon",None)
			sanitize_personal_group_invites(own_id, own_username, target_id, target_username)
			own_anon, target_anon = '0','1' if is_target_anon == True else '0'
			group_id, already_existed = create_personal_group(own_id, target_id, own_anon=own_anon, target_anon=target_anon)
			if not already_existed:
				private_chat_tasks.delay(own_id=own_id,target_id=target_id,group_id=group_id,posting_time=time.time(),text='created',txt_type='creation',\
					own_anon=own_anon,target_anon=target_anon,blob_id='', idx='', img_url='',own_uname=own_username,own_avurl='',deleted='undel',hidden='no')
			request.session["personal_group_tid_key"] = target_id
			request.session["personal_group_gid_key:"+target_id] = group_id
			request.session.modified = True
			return redirect("enter_personal_group")
		else:
			origin, poid, target_username = request.POST.get('org',None), request.POST.get('poid',None), request.POST.get('nickname',None)
			if origin == 'publicreply':
				if poid:
					request.session["link_pk"] = poid
					request.session.modified = True
					return redirect("publicreply_view")
				else:
					return redirect("home")
			else:
				return return_to_source(origin,poid,target_username)
	else:
		return redirect("home")



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def send_personal_group_invite(request):
	"""
	Forward to privacy setting of invite, don't send invite yet
	"""
	if request.method == "POST":
		invite_decision = request.POST.get('invite_dec',None)
		if invite_decision == '1':
			context = {'set_privacy':True,'target_av_url':request.session.get("personal_group_invite_target_av_url",None),\
			'tun':request.session.get("personal_group_invite_target_username",None)}
			return render(request,"personal_group/invites/personal_group_status.html",context)
		else:
			origin, poid, target_username = request.POST.get('org',None), request.POST.get('poid',None), request.POST.get('nickname',None)
			if origin == 'publicreply':
				if poid:
					request.session["link_pk"] = poid
					request.session.modified = True
					return redirect("publicreply_view")
				else:
					return redirect("home")
			else:
				return return_to_source(origin,poid,target_username)
	else:
		return redirect("home")



@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def change_personal_group_invite_privacy(request):
	"""
	Set privacy level of invite and send the invite
	"""
	if request.method == "POST":
		own_id = request.user.id
		target_id = request.session.get("personal_group_invite_target_id",None)
		group_id, already_exists = personal_group_already_exists(own_id, target_id)
		if already_exists:
			request.session["personal_group_tid_key"] = target_id
			request.session["personal_group_gid_key:"+target_id] = group_id
			request.session.modified = True
			return redirect("enter_personal_group")
		else:
			if request.user_banned:
				return render(request,'500.html',{}) #errorbanning
			decision = request.POST.get("dec",None)
			own_username, target_username = get_target_username(str(own_id)),request.session.get("personal_group_invite_target_username",None)
			state, invite_sending_time, recently_declined = personal_group_invite_status(own_id, own_username, target_id, target_username)
			if state in ('2','3'):
				# they already invited me, so accept the invite instead of inviting them back
				sanitize_personal_group_invites(own_id, own_username, target_id, target_username)
				avatars = retrieve_bulk_avurls([own_id, target_id])
				own_av_url = avatars[own_id]
				target_av_url = avatars[int(target_id)]
				own_anon, target_anon = '1' if decision == '0' else '0', '1' if state == '3' else '0'
				group_id, already_existed = create_personal_group(own_id, target_id, own_anon=own_anon, target_anon=target_anon)
				if not already_existed:
					private_chat_tasks.delay(own_id=own_id,target_id=target_id,group_id=group_id,posting_time=time.time(),text='created',txt_type='creation',\
						own_anon=own_anon,target_anon=target_anon,blob_id='', idx='', img_url='',own_uname=own_username,own_avurl='',deleted='undel',hidden='no')
				request.session["personal_group_tid_key"] = target_id
				request.session["personal_group_gid_key:"+target_id] = group_id
				request.session.modified = True
				return redirect("enter_personal_group")
			else:
				# proceed with the invite
				parent_object_id = request.session.get("personal_group_invite_parent_object_id",None)
				origin = request.session.get("personal_group_invite_origin",None)
				target_av_url = request.session.get("personal_group_invite_target_av_url",None)
				object_type = request.session.get("personal_group_invite_object_type",None)
				context = {'tun':target_username,'tid':target_id,'poid':parent_object_id,'org':origin,'ot':object_type,'target_av_url':target_av_url}
				sent, cooloff_time = process_invite_sending(own_id, own_username, target_id, target_username)
				if sent is False:
					context = {'rate_limited':True,'time_remaining':cooloff_time,'org':origin,'poid':parent_object_id,'tun':target_username}
					return render(request,"personal_group/invites/personal_group_status.html",context)
				else:
					if decision == '0':
						interactive_invite_privacy_settings(own_id, own_username, target_id, target_username, visible=decision)
						if tutorial_unseen(user_id=own_id, which_tut='0', renew_lease=True):
							context["personal_group_invite_privacy"] = True
							context["oun"] = own_username
							return render(request,"helpful_instructions.html",context)
					return redirect("show_personal_group_invite_list")
	else:
		return redirect("home")

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def process_personal_group_invite(request):
	"""
	Accept or decline invite directly from invite lists
	"""
	if request.method == "POST":
		own_id, target_id = request.user.id, request.POST.get("tid",None)
		int_tid = int(target_id)
		own_cred, their_cred = get_user_credentials(str(own_id), target_id)
		own_username, own_av_url, target_username, target_av_url = own_cred[0], own_cred[1], their_cred[0], their_cred[1]
		state, invite_sending_time, recently_declined = personal_group_invite_status(own_id, own_username, target_id, target_username)
		if state in ('2','3'):
			if request.POST.get("sel",None) == '1':
				if request.user_banned:
					return render(request,'500.html',{}) #errorbanning
				sanitize_personal_group_invites(own_id, own_username, target_id, target_username)
				own_anon, target_anon = '0', '1' if state == '3' else '0'
				group_id, already_existed = create_personal_group(own_id, target_id, own_anon=own_anon, target_anon=target_anon)
				if not already_existed:
					private_chat_tasks.delay(own_id=own_id,target_id=target_id,group_id=group_id,posting_time=time.time(),text='created',txt_type='creation',\
						own_anon=own_anon,target_anon=target_anon,blob_id='', idx='', img_url='',own_uname=own_username,own_avurl=own_av_url,deleted='undel',\
						hidden='no')
				request.session["personal_group_invite_accepted"] = True
				request.session["personal_group_invite_accepted_is_anon"] = True if state == '3' else False
				request.session["personal_group_invite_accepted_username"] = target_username
				request.session["personal_group_invite_accepted_av_url"] = target_av_url
				request.session["personal_group_tid_key"] = target_id
				request.session["personal_group_gid_key:"+target_id] = group_id
				request.session.modified = True
			else:
				ignore_invite(own_id, own_username, target_id, target_username)
	return redirect("show_personal_group_invite_list")


######################################## Personal Group JS Helper Functions ########################################

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def post_js_reply_to_personal_group(request):
	"""
	Processes reply posted via JS-created HTML widget inside chat

	This function is only invoked in JS-enabled devices
	"""
	if request.method == "POST":
		target_content_type, target_blob_id, target_index, target_id, sk_form = request.POST.get('tt',None), request.POST.get('bid',None),\
		request.POST.get('idx',None), request.POST.get('tid',None), request.POST.get('sk',None)
		# try:
		# 	payload = payload.split(":")
		# 	target_content_type, target_blob_id, target_index, target_id, sk_form = payload[2], payload[4], payload[3], payload[1], payload[0]
		# except (IndexError,TypeError):
		# 	return redirect("enter_personal_group")
		if target_index and target_blob_id and target_content_type:
			own_id = request.user.id
			request.session["personal_group_tid_key"] = target_id
			group_id, exists = personal_group_already_exists(own_id, target_id)
			if exists:
				request.session["personal_group_gid_key:"+target_id] = group_id
				is_ajax = request.is_ajax()
				sk_redis = get_and_delete_photo_upload_key(user_id=own_id, group_id=group_id)
				if sk_form != sk_redis:
					request.session["personal_group_form_error"] = PERSONAL_GROUP_ERR['mismatch']
					request.session.modified = True
					if is_ajax:
						return HttpResponse(json.dumps({'success':False,'message':reverse('enter_personal_group')}),content_type='application/json',)
					else:
						return redirect("enter_personal_group")
				else:
					on_fbs = request.META.get('HTTP_X_IORG_FBS',False)
					form = PersonalGroupReplyPostForm(request.POST,request.FILES,on_fbs = on_fbs)
					if form.is_valid():
						image_file = request.FILES.get('rep_image')
						reply = form.cleaned_data.get("rep_reply")
						if (image_file and reply) or image_file:
							if personal_group_image_transfer_not_permitted(target_id, group_id):
								request.session["personal_group_image_xfer_no_permit"] = True
								if personal_group_photo_xfer_invite_allwd(target_id, group_id):
									#'1' signifies photo permission notification
									add_content_to_personal_group(content='1', type_='notif', writer_id=own_id, group_id=group_id)
									private_chat_tasks.delay(own_id=own_id,target_id=target_id,group_id=group_id,posting_time=time.time(),text=PRIV_CHAT_NOTIF['1'],\
										txt_type='notif',own_anon='',target_anon='',blob_id='', idx='', img_url='',own_uname='',own_avurl='',deleted='undel',\
										hidden='no')
							else:
								reoriented = request.POST.get('reoriented',None)
								resized = request.POST.get('resized',None)
								quality = None if on_fbs else True
								image_to_upload, img_width, img_height = process_personal_group_image(image=image_file, quality=quality, already_resized=resized, \
									already_reoriented=reoriented)
								if not image_to_upload and img_height == 'too_high':
									request.session["personal_group_form_error"] = PERSONAL_GROUP_ERR['too_high']
									request.session.modified = True
									if is_ajax:
										return HttpResponse(json.dumps({'success':False,'message':reverse('enter_personal_group')}),content_type='application/json',)
									else:
										return redirect("enter_personal_group")
								else:
									uploaded_image_loc = upload_image_to_s3(image_to_upload)
									content = {'img_url':uploaded_image_loc, 'img_width':img_width, 'img_height':img_height, 'img_caption':reply}
									# add as a 'response' blob
									res_blob = {'target_blob_id':target_blob_id,'target_index':target_index,'target_content_type':target_content_type}
									obj_count, obj_ceiling, gid, bid, idx, img_id, img_wid, hw_ratio = add_content_to_personal_group(content=content, \
										type_='img_res', writer_id=own_id, group_id=group_id, res_blob=res_blob)
									private_chat_tasks.delay(own_id=own_id,target_id=target_id,group_id=group_id,posting_time=time.time(),text=reply,\
										txt_type='img_res',own_anon='',target_anon='',blob_id=bid, idx=idx, img_url=uploaded_image_loc,own_uname='',\
										own_avurl='',deleted='undel',hidden='no',successful=True if bid else False)
									add_image_to_personal_group_storage.delay(uploaded_image_loc, img_id, img_wid, hw_ratio, quality, bid, idx, own_id, gid)
									personal_group_sanitization(obj_count, obj_ceiling, gid)
						elif reply:
							# add as a 'response' blob
							res_blob = {'target_blob_id':target_blob_id,'target_index':target_index,'target_content_type':target_content_type}
							obj_count, obj_ceiling, gid, bid, idx, img_id, img_wid, hw_ratio = add_content_to_personal_group(content=reply, \
								type_='text_res', writer_id=own_id, group_id=group_id, res_blob=res_blob)
							private_chat_tasks.delay(own_id=own_id,target_id=target_id,group_id=group_id,posting_time=time.time(),text=reply,\
								txt_type='text_res',own_anon='',target_anon='',blob_id=bid, idx=idx, img_url='',own_uname='',own_avurl='',\
								deleted='undel',hidden='no',successful=True if bid else False)
							personal_group_sanitization(obj_count, obj_ceiling, gid)
						else:
							pass
						request.session.modified = True
						if is_ajax:
							return HttpResponse(json.dumps({'success':True,'message':reverse('enter_personal_group')}),content_type='application/json',)
						else:
							return redirect("enter_personal_group")
					else:
						try:
							request.session["personal_group_form_error"] = form.errors.as_text().split("*")[2]
						except IndexError:
							request.session["personal_group_form_error"] = PERSONAL_GROUP_ERR['generic']
						request.session.modified = True
						if is_ajax:
							return HttpResponse(json.dumps({'success':False,'message':reverse('enter_personal_group')}),content_type='application/json',)
						else:
							return redirect("enter_personal_group")
			else:
				return redirect("personal_group_user_listing")
		else:
			return redirect("enter_personal_group")
	else:
		return redirect("enter_personal_group")

######################################## Personal Group Listing and Pagination ########################################

def get_indices(page_number, obj_allotment):
	"""
	When fed a page_number, returns a start_index and end_index
	"""
	try:
		page_number = int(page_number)
	except (ValueError,TypeError):
		return 0,obj_allotment-1
	objs_per_page = obj_allotment
	index_ceiling = objs_per_page * page_number
	return (index_ceiling)-objs_per_page,index_ceiling-1
	
def get_overall_page_list(num_of_items, objs_per_page):
	"""
	Returns list of all pages containing groups that a user has
	"""
	page_list = []
	try:
		remainder = (num_of_items % objs_per_page)
	except ZeroDivisionError:
		return page_list
	if remainder:
		num_of_pages = int(num_of_items / objs_per_page)+1
	else:
		num_of_pages = int(num_of_items / objs_per_page)
	for page_num in xrange(num_of_pages):
		page_list.append(str(page_num+1))
	return page_list


def personal_group_user_listing(request):
	"""
	List down personal groups of a given user
	"""
	own_id, page_num = request.user.id, request.GET.get('page', '1')
	start_index, end_index = get_indices(page_num, OBJS_PER_PAGE_IN_USER_GROUP_LIST)
	payload, total_grps = retrieve_user_group_list_contents(own_id,start_index,end_index)
	page_list = get_overall_page_list(total_grps, OBJS_PER_PAGE_IN_USER_GROUP_LIST)
	return render(request,"personal_group/group_listing/user_group_list.html",{'payload':payload,'pages':page_list,'num_pages':len(page_list),\
		'current_page':page_num,'current_time':time.time(),'own_id':str(request.user.id),'items_in_curr_page':len(payload)})

####################################################################################################################
#################################################### Help Page #####################################################
####################################################################################################################


@csrf_protect
def personal_group_help1(request):
	"""
	Renders private chat help page
	"""
	if request.method == 'POST':
		tid = request.POST.get('tid',None)
		return render(request,"personal_group/help/personal_group_help1.html",{'tid':tid})
	else:
		return render(request,"personal_group/help/personal_group_help1.html",{})


@csrf_protect
def personal_group_help2(request):
	"""
	Renders private chat help page
	"""
	if request.method == 'POST':
		tid = request.POST.get('tid',None)
		return render(request,"personal_group/help/personal_group_help2.html",{'tid':tid})
	else:
		return render(request,"personal_group/help/personal_group_help2.html",{})


@csrf_protect
def personal_group_help3(request):
	"""
	Renders private chat help page
	"""
	if request.method == 'POST':
		tid = request.POST.get('tid',None)
		return render(request,"personal_group/help/personal_group_help3.html",{'tid':tid})
	else:
		return render(request,"personal_group/help/personal_group_help3.html",{})


@csrf_protect
def personal_group_help4(request):
	"""
	Renders private chat help page 
	"""
	if request.method == 'POST':
		tid = request.POST.get('tid',None)
		return render(request,"personal_group/help/personal_group_help4.html",{'tid':tid})
	else:
		return render(request,"personal_group/help/personal_group_help4.html",{})

	
def private_chat_help_ad(request):
	"""
	"""
	return render(request,"personal_group/help/private_chat_help_ad.html",{})	


#####################################################################################################################
######################################### Sharing Photos in Personal Groups #########################################
#####################################################################################################################

def show_shared_photo_metrics(request,nick):
	"""
	Shows shared photos metrics to users
	"""
	their_id = retrieve_user_id(nick)
	if their_id:
		own_id = str(request.user.id) if request.user.is_authenticated() else None
		photo_content, is_cached = retrieve_fresh_photo_shares_or_cached_data(their_id)
		if is_cached:
			final_photo_data = photo_content
		else:
			epoch_time_one_week_ago = time.time()-ONE_WEEK
			#############################
			last_week_shared_by_others = defaultdict(int)
			for content in photo_content:
				data = content.split(":")
				photo_id, num_shares, sharer_id, sharing_time = data[0], data[1], data[2], data[3]
				if float(sharing_time) > epoch_time_one_week_ago:
					if sharer_id != their_id:
						last_week_shared_by_others[photo_id] += int(num_shares)
			photos = sorted(last_week_shared_by_others.iteritems(),key=lambda (k,v):v,reverse=True)
			photo_ids = [i[0] for i in photos][0:5]
			photo_data = retrieve_photo_data(photo_ids, their_id)
			final_photo_data = []
			for photo_id in photo_ids:
				photo_data[photo_id]['num_shares'] = last_week_shared_by_others[photo_id]
				final_photo_data.append(photo_data[photo_id])
			cache_photo_shares.delay(json.dumps(final_photo_data), their_id)
		if own_id and tutorial_unseen(user_id=own_id, which_tut='4', renew_lease=True):
			first_time = True
		else:
			first_time = False
		return render(request,"personal_group/sharing/photo_sharing_metrics.html",{'final_photo_data':final_photo_data,'num_photos':len(final_photo_data),\
			'own_profile': their_id == own_id,'username':nick,'photo_owner_id':their_id,'first_time':first_time})
	else:
		return redirect('profile',nick)


def cant_share_photo(request, ttl=None,*args, **kwargs):
	"""
	Shows failure message if photo can't be shared due to photo owner being banned
	"""
	if ttl:
		try:
			ttl = int(ttl)
		except ValueError:
			ttl = None
	photo_id = request.session.get("personal_group_shared_photo_id",None)
	origin = request.session.get("personal_group_shared_photo_origin",None)
	photo_url = request.session.get("personal_group_shared_photo_url",None)
	photo_caption = request.session.get("personal_group_shared_photo_caption",None)
	photo_owner_username = request.session.get("personal_group_shared_photo_owner_username",None)
	return render(request,"personal_group/sharing/photo_not_shared.html",{'photo_caption':photo_caption,'photo_id':photo_id,'photo_url':photo_url,\
		'photo_owner_username':photo_owner_username,'origin':origin,'ttl':ttl})


def photo_shared(request):
	"""
	Shows success message after photo is shared in personal group(s)
	"""
	photo_id = request.session.get("personal_group_shared_photo_id",None)
	origin = request.session.get("personal_group_shared_photo_origin",None)
	photo_url = request.session.get("personal_group_shared_photo_url",None)
	photo_caption = request.session.get("personal_group_shared_photo_caption",None)
	allwd_friends = request.session.get("personal_group_shared_photo_allwd_friends",None)
	disallwd_friends = request.session.get("personal_group_shared_photo_disallwd_friends",None)
	photo_owner_username = request.session.get("personal_group_shared_photo_owner_username",None)
	return render(request,"personal_group/sharing/photo_shared.html",{'allwd_friends':allwd_friends,'disallwd_friends':disallwd_friends,\
		'own_uname':retrieve_uname(request.user.id,decode=True),'origin':origin,'photo_caption':photo_caption,'num_sent':len(allwd_friends),\
		'num_unsent':len(disallwd_friends),'photo_url':photo_url,'photo_id':photo_id,'photo_owner_username':photo_owner_username})


def post_shared_photo_to_personal_groups(group_ids,photo_url,photo_caption,photo_id,photo_owner_username,own_id, photo_owner_id):
	"""
	Post a shared image post to list of personal groups
	"""
	photo_allwd, photo_disallwd, legit_groups, nonlegit_groups = can_share_photo(group_ids,own_id)
	if photo_allwd:
		img_height, img_width = get_cached_photo_dim(photo_id)
		if not img_height:
			img_obj = Photo.objects.get(id=photo_id) # reaffirm url at this point too
			img_height, img_width = img_obj.image_file.height, img_obj.image_file.width
			cache_photo_dim(photo_id,img_height,img_width)
		sharing_time = time.time()
		for group_id in photo_allwd:
			# send the photo!
			content, type_ = {'img_url':photo_url, 'img_width':img_width, 'img_height':img_height, 'owner_uname':photo_owner_username, \
			'img_caption':photo_caption,'owner_id':photo_owner_id,'pid':photo_id},'shared_img'
			obj_count, obj_ceiling, gid, bid, idx, img_id, img_wid, hw_ratio = add_content_to_personal_group(content=content, type_=type_,\
				writer_id=own_id, group_id=group_id)
			# image 'quality' shows the "low quality - uploaded via fbs" msg. We can omit it for this case, hence setting it to 'True'
			quality = True
			add_image_to_personal_group_storage.delay(photo_url, img_id, img_wid, hw_ratio, quality, bid, idx, own_id, gid, True, photo_owner_username)#set_personal_group_image_storage()
			# 'text' is photo_caption in this case
			private_chat_tasks.delay(own_id=own_id,target_id=legit_groups[group_id],group_id=group_id,posting_time=sharing_time,text=photo_caption,\
				txt_type=type_,own_anon='',target_anon='',blob_id=bid, idx=idx, img_url=photo_url,own_uname='',own_avurl='',deleted='undel',\
				hidden='no',successful=True if bid else False,sharing=True)
			personal_group_sanitization(obj_count, obj_ceiling, gid)
		photo_sharing_metrics_and_rate_limit.delay(own_id, photo_id, photo_owner_id, len(photo_allwd),sharing_time, photo_allwd)
	else:
		pass
	return photo_allwd, photo_disallwd


@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@csrf_protect
def share_photo_in_personal_group(request):
	"""
	Allows sharing any Damadam photo in a personal group

	Permission to share photo must have been granted for this to work
	"""
	if request.method == "POST":
		user_id = request.user.id
		decision_made = request.POST.get("dm",None)
		new_title = request.POST.get("nt",None)
		if new_title:
			# before processing, ensure this user's all photos aren't banned:
			photo_owner_id = request.session.get("personal_group_shared_photo_owner_id",None)
			banned, time_remaining = check_photo_upload_ban(photo_owner_id)
			if banned:
				return redirect("cant_share_photo")
			elif not banned:
				photo_caption = request.session.get("personal_group_shared_photo_caption",None)
				photo_url = request.session.get("personal_group_shared_photo_url",None)
				if request.POST.get('dec',None) == '1':
					form = PersonalGroupSharedPhotoCaptionForm(request.POST)
					if form.is_valid():
						# change photo caption
						photo_owner_username = request.session.get("personal_group_shared_photo_owner_username",None)
						group_ids = request.session.get("personal_group_shared_photo_group_ids",None)
						photo_id = request.session.get("personal_group_shared_photo_id",None)
						new_photo_caption = form.cleaned_data.get("text")
						is_limited, cooloff_time = get_rate_limit_in_personal_group_sharing(user_id)
						if is_limited:
							return redirect("cant_share_photo",cooloff_time)
						elif not is_limited:
							allwd_grps, disallwd_grps = post_shared_photo_to_personal_groups(group_ids,photo_url,new_photo_caption,photo_id,\
								photo_owner_username,user_id, photo_owner_id)
							targeted_friends = request.session.get("personal_group_shared_photo_group_contents",None)
							allwd_friends, disallwd_friends = [], []
							for group_id in allwd_grps:
								allwd_friends.append(targeted_friends[group_id])
							for group_id in disallwd_grps:
								disallwd_friends.append(targeted_friends[group_id])
							request.session["personal_group_shared_photo_caption"] = new_photo_caption
							request.session["personal_group_shared_photo_allwd_friends"] = allwd_friends
							request.session["personal_group_shared_photo_disallwd_friends"] = disallwd_friends
							request.session.modified = True
							return redirect("photo_shared")
						else:
							return redirect("cant_share_photo",cooloff_time)
					else:
						# validation error when trying to change photo caption
						context = {'photo_url':photo_url,'edit_caption':True,'photo_caption':photo_caption,'form':form}
						return render(request,"personal_group/sharing/share_photo_in_personal_group.html",context)
				else:
					# user pressed 'skip' - i.e. no change in photo caption
					photo_owner_username = request.session.get("personal_group_shared_photo_owner_username",None)
					group_ids = request.session.get("personal_group_shared_photo_group_ids",None)
					photo_id = request.session.get("personal_group_shared_photo_id",None)
					is_limited, cooloff_time = get_rate_limit_in_personal_group_sharing(user_id)
					if is_limited:
						return redirect("cant_share_photo",cooloff_time)
					elif not is_limited:
						allwd_grps, disallwd_grps = post_shared_photo_to_personal_groups(group_ids,photo_url,photo_caption,photo_id,\
							photo_owner_username,user_id, photo_owner_id)
						targeted_friends = request.session.get("personal_group_shared_photo_group_contents",None)
						allwd_friends, disallwd_friends = [], []
						for group_id in allwd_grps:
							allwd_friends.append(targeted_friends[group_id])
						for group_id in disallwd_grps:
							disallwd_friends.append(targeted_friends[group_id])
						request.session["personal_group_shared_photo_allwd_friends"] = allwd_friends
						request.session["personal_group_shared_photo_disallwd_friends"] = disallwd_friends
						request.session.modified = True
						return redirect("photo_shared")
					else:
						return redirect("cant_share_photo",cooloff_time)
			else:
				return redirect("cant_share_photo")
		elif decision_made:
			groups = request.POST.getlist('gid',None)# contains group_ids in list format
			photo_url = request.session.get("personal_group_shared_photo_url",None)
			photo_caption = request.session.get("personal_group_shared_photo_caption",None)
			if groups:
				if len(groups) > PHOTO_SHARING_FRIEND_LIMIT:
					# return to select friends screen, alongwith message asking user to select lesser friends
					context = {'must_select_less':True,'limit':PHOTO_SHARING_FRIEND_LIMIT,'photo_url':photo_url,'photo_caption':photo_caption}
					group_and_friend = get_user_friend_list(user_id)
					if not group_and_friend:
						context["no_friends"] = True
					else:
						context["friend_data"] = group_and_friend
					return render(request,"personal_group/sharing/share_photo_in_personal_group.html",context)
				else:
					group_ids, group_contents = [], {}
					for group in groups:
						data = group.split(":",4)
						group_id = data[0]
						group_ids.append(group_id)
						group_contents[group_id] = {'friend_uname':data[4],'friend_avurl':data[2],'friend_id':data[3],'is_anon':data[1]}
					request.session["personal_group_shared_photo_group_ids"] = group_ids
					request.session["personal_group_shared_photo_group_contents"] = group_contents
					request.session.modified = True
					context = {'photo_url':photo_url,'edit_caption':True,'photo_caption':photo_caption,'form':PersonalGroupSharedPhotoCaptionForm()}
					return render(request,"personal_group/sharing/share_photo_in_personal_group.html",context)
			else:
				# return to select friends screen, alongwith message asking user to at least select 1 friend
				context = {'must_select_one':True,'photo_url':photo_url,'photo_caption':photo_caption}
				group_and_friend = get_user_friend_list(user_id)
				if not group_and_friend:
					context["no_friends"] = True
				else:
					context["friend_data"] = group_and_friend
				return render(request,"personal_group/sharing/share_photo_in_personal_group.html",context)
		else:
			payload = request.POST.get("pl").split(":",4)#maxsplit set to 4 to ensure caption containing ':' is not split
			owner_username, photo_id, origin, owner_id, photo_caption = payload[0], payload[1], payload[2], payload[3], payload[4]
			photo_url = request.POST.get("purl")
			request.session["personal_group_shared_photo_id"] = photo_id
			request.session["personal_group_shared_photo_url"] = photo_url
			request.session["personal_group_shared_photo_origin"] = origin
			request.session["personal_group_shared_photo_owner_id"] = owner_id
			request.session["personal_group_shared_photo_caption"] = photo_caption
			request.session["personal_group_shared_photo_owner_username"] = owner_username
			request.session.modified = True
			context = {'photo_url':photo_url,'photo_caption':photo_caption,'limit':PHOTO_SHARING_FRIEND_LIMIT,'origin':origin,'photo_id':photo_id,\
			'owner_username':owner_username}
			if tutorial_unseen(user_id=user_id, which_tut='3', renew_lease=True):
				context["show_first_time_tutorial"] = True
			group_and_friend = get_user_friend_list(user_id)
			if not group_and_friend:
				context["no_friends"] = True
			else:
				context["friend_data"] = group_and_friend
				context["num_friends"] = len(group_and_friend)
			return render(request,"personal_group/sharing/share_photo_in_personal_group.html",context)
	else:
		return redirect("missing_page")



#####################################################################################################################
################################################### Metrics Page ####################################################
#####################################################################################################################


def personal_group_metrics(request):
	"""
	Displays metrics related to personal groups

	1) How many personal groups are created each day, and how many are exited
	2) What are avg number of chats produced per type of chat?
	3) What are avg number of switchovers produced per type of chat?
	"""
	total_pms, median_pm_idx, median_pm_tuple, aggregate_pm_chats, avg_chat_per_pm, total_pgs, median_pg_idx, median_pg_tuple, aggregate_pg_chats, \
	avg_chat_per_pg, pms_with_sws, pgs_with_sws = avg_num_of_chats_per_type()
	
	total_pms_sw, median_pm_sw_idx, median_pm_sw_tuple, aggregate_pm_sws, avg_sw_per_pm, total_pgs_sw, median_pg_sw_idx, median_pg_sw_tuple, \
	aggregate_pg_sws, avg_sw_per_pg = avg_num_of_switchovers_per_type()

	total_pgs_sess, total_pms_sess, med_sess_per_user_per_pg, med_sess_per_user_per_pm, avg_sess_per_user_per_pg, avg_sess_per_user_per_pm, \
	avg_users_per_pm, med_users_per_pm, avg_users_per_pg, med_users_per_pg, avg_sess_per_user_per_two_user_pm, med_sess_per_user_per_two_user_pm,\
	total_two_user_pms, avg_users_per_two_user_pm, med_users_per_two_user_pm = avg_sessions_per_type()

	return render(request,"personal_group/metrics/personal_group_metrics.html",{'total_pms':total_pms,'agg_pm_chats':aggregate_pm_chats,\
		'avg_pm_chats':avg_chat_per_pm,'total_pgs':total_pgs,'agg_pg_chats':aggregate_pg_chats,'avg_pg_chats':avg_chat_per_pg,\
		'med_pm_idx':median_pm_idx,'med_pg_idx':median_pg_idx,'med_pm_tup':median_pm_tuple,'med_pg_tup':median_pg_tuple,\
		'total_pms_sw':total_pms_sw,'agg_pm_sws':aggregate_pm_sws,'avg_pm_sws':avg_sw_per_pm,'total_pgs_sw':total_pgs_sw,\
		'agg_pg_sws':aggregate_pg_sws,'avg_pg_sws':avg_sw_per_pg,'med_pm_idx_sw':median_pm_sw_idx,'med_pg_idx_sw':median_pg_sw_idx,\
		'med_pm_tup_sw':median_pm_sw_tuple,'med_pg_tup_sw':median_pg_sw_tuple,'avg_sess_per_user_per_pg':avg_sess_per_user_per_pg,\
		'avg_sess_per_user_per_pm':avg_sess_per_user_per_pm,'med_sess_per_user_per_pg':med_sess_per_user_per_pg,\
		'med_sess_per_user_per_pm':med_sess_per_user_per_pm,'pgs_sampled_sess':total_pgs_sess,'pms_sampled_sess':total_pms_sess,\
		'avg_users_per_pm':avg_users_per_pm, 'med_users_per_pm':med_users_per_pm,'avg_users_per_pg':avg_users_per_pg,\
		'med_users_per_pg':med_users_per_pg,'pms_with_sws':pms_with_sws,'pgs_with_sws':pgs_with_sws,'total_two_user_pms':total_two_user_pms,\
		'avg_sess_per_user_per_two_user_pm':avg_sess_per_user_per_two_user_pm,'med_sess_per_user_per_two_user_pm':med_sess_per_user_per_two_user_pm,\
		'avg_users_per_two_user_pm':avg_users_per_two_user_pm, 'med_users_per_two_user_pm':med_users_per_two_user_pm})