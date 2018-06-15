from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib.auth.decorators import login_required as auth    
from links.group_views import render_personal_group_invite, change_personal_group_invite_privacy, show_personal_group_invite_list, \
process_personal_group_invite, personal_group_sms_text, post_to_personal_group, personal_group_sms_settings, personal_group_own_chat_buttons, \
delete_post_from_personal_group, post_chat_action_in_personal_group, delete_all_posts_from_personal_group, save_post_in_personal_group,\
anonymize_user_in_personal_group, accept_personal_group_invite, send_personal_group_invite, personal_group_grant_chat_saving_perm, \
set_personal_group_photo_sharing_perm_from_chat, delete_or_hide_photo_from_photo_settings, hide_photo_from_personal_group_chat, private_chat_help_ad,\
personal_group_receive_sms, personal_group_customize_sms_text, personal_group_receive_sms_from_chat, enter_personal_group,personal_group_help1,\
personal_group_send_sms, personal_group_sms_text_form, personal_group_exit_settings, personal_group_their_chat_buttons, personal_group_reentry,\
show_all_saved_posts_in_personal_group, retrieve_personal_group_saved_content,personal_group_delete_saved_post, personal_group_photo_settings,\
post_js_reply_to_personal_group, personal_group_user_listing, unseen_per_grp, x_per_grp_notif, personal_group_metrics, share_photo_in_personal_group,\
photo_shared, cant_share_photo, personal_group_help2, personal_group_help3, personal_group_help4, show_shared_photo_metrics#, deletion_test
from links.number_verification import verify_personal_group_user

admin.autodiscover()

urlpatterns = patterns('',
	# url(r'^deletion_test/$', auth(deletion_test), name='deletion_test'),
	############################## Personal Groups ###############################
	url(r'^private_chat/$', auth(enter_personal_group), name='enter_personal_group'),
	url(r'^pcp/$', auth(post_to_personal_group), name='post_to_personal_group'),
	url(r'^pcpr/$', auth(post_js_reply_to_personal_group), name='post_js_reply_to_personal_group'),
	url(r'^pctb/$', auth(personal_group_their_chat_buttons), name='personal_group_their_chat_buttons'),
	url(r'^pcasp/$', auth(show_all_saved_posts_in_personal_group), name='show_all_saved_posts_in_personal_group'),
	url(r'^pcsp/$', auth(save_post_in_personal_group), name='save_post_in_personal_group'),
	url(r'^pcr/$', auth(delete_post_from_personal_group), name='delete_post_from_personal_group'),
	url(r'^pchf/$', auth(hide_photo_from_personal_group_chat), name='hide_photo_from_personal_group_chat'),
	url(r'^pca/$', auth(post_chat_action_in_personal_group), name='post_chat_action_in_personal_group'),
	url(r'^pcrd/$', auth(personal_group_own_chat_buttons), name='personal_group_own_chat_buttons'),
	########################## Personal Group Settings ###########################
	url(r'^pcsvp/$', auth(personal_group_grant_chat_saving_perm), name='personal_group_grant_chat_saving_perm'),
	url(r'^pcdsv/$', auth(personal_group_delete_saved_post), name='personal_group_delete_saved_post'),
	url(r'^pcsv/$', auth(retrieve_personal_group_saved_content), name='retrieve_personal_group_saved_content'),
	url(r'^pce/$', auth(personal_group_exit_settings), name='personal_group_exit_settings'),
	url(r'^pcre/$', auth(personal_group_reentry), name='personal_group_reentry'),
	url(r'^pcra/$', auth(delete_all_posts_from_personal_group), name='delete_all_posts_from_personal_group'),
	url(r'^pcfd/$', auth(delete_or_hide_photo_from_photo_settings), name='delete_or_hide_photo_from_photo_settings'),
	url(r'^pcf/$', auth(personal_group_photo_settings), name='personal_group_photo_settings'),
	url(r'^pcs/$', auth(personal_group_sms_settings), name='personal_group_sms_settings'),
	url(r'^pcss/$',personal_group_send_sms, name="personal_group_send_sms"),
	url(r'^pcssf/$',personal_group_sms_text_form, name="personal_group_sms_text_form"),
	url(r'^pcfc/$', auth(set_personal_group_photo_sharing_perm_from_chat), name='set_personal_group_photo_sharing_perm_from_chat'),
	url(r'^pcz/$', auth(anonymize_user_in_personal_group), name='anonymize_user_in_personal_group'),
	########################### Verify Mobile Number #############################
	url(r'^vpg/$',verify_personal_group_user, name="verify_personal_group_user"),
	url(r'^pcrs/$',personal_group_receive_sms, name="personal_group_receive_sms"),
	url(r'^pcsms/$',personal_group_sms_text, name="personal_group_sms_text"),
	url(r'^pccs/$',personal_group_customize_sms_text, name="personal_group_customize_sms_text"),
	url(r'^pcrsc/$',personal_group_receive_sms_from_chat, name="personal_group_receive_sms_from_chat"),
	########################### Personal Group Invites ###########################
	url(r'^invite_priv_chat/$', auth(render_personal_group_invite), name='render_personal_group_invite'),
	url(r'^send_priv_chat_invite/$', auth(send_personal_group_invite), name='send_personal_group_invite'),
	url(r'^accept_priv_chat_invite/$', auth(accept_personal_group_invite), name='accept_personal_group_invite'),
	url(r'^acc_priv_chat_invite/$', auth(process_personal_group_invite), name='process_personal_group_invite'),
	url(r'^priv_chat_invite_privacy/$', auth(change_personal_group_invite_privacy), name='change_personal_group_invite_privacy'),
	############################## Personal Group Listing ###############################
	url(r'^priv_chat_invite_list/$', auth(show_personal_group_invite_list), name='show_personal_group_invite_list'),
	url(r'^priv_chat_list/$', auth(personal_group_user_listing), name='personal_group_user_listing'),
	############################## Personal Group Notifications ###############################
	url(r'^unpergrp/(?P<gid>\d+)/(?P<fid>\d+)/$', auth(unseen_per_grp), name='unseen_per_grp'),
	url(r'^xpergrp/(?P<gid>\d+)/(?P<fid>\d+)/(?P<from_home>\d+)/$', auth(x_per_grp_notif), name='x_per_grp_notif'),
	############################## Personal Group Notifications ###############################
	url(r'^private_chat_ad/$', auth(private_chat_help_ad), name='private_chat_help_ad'),
	############################ Personal Group Metrics Reporting #############################
	url(r'^personal_group_metrics/$', auth(personal_group_metrics), name='personal_group_metrics'),
	############################ Personal Group Metrics Reporting #############################
	url(r'^pcsf/$', auth(share_photo_in_personal_group), name='share_photo_in_personal_group'),
	url(r'^pccsf/$', auth(cant_share_photo), name='cant_share_photo'),
	url(r'^pccsf/(?P<ttl>\d+)/$', auth(cant_share_photo), name='cant_share_photo'),
	url(r'^pcfs/$', auth(photo_shared), name='photo_shared'),
	################################ Personal Group Help Pages #################################
	url(r'^private_chat_help_page1/$', auth(personal_group_help1), name='personal_group_help1'),
	url(r'^private_chat_help_page2/$', auth(personal_group_help2), name='personal_group_help2'),
	url(r'^private_chat_help_page3/$', auth(personal_group_help3), name='personal_group_help3'),
	url(r'^private_chat_help_page4/$', auth(personal_group_help4), name='personal_group_help4'),
	############################## Personal Group Shared Photos ###############################
	url(r'^shared_photos/(?P<nick>[\w.@+-]+)/$', show_shared_photo_metrics, name='show_shared_photo_metrics'),
)