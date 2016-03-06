from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required as auth
from django.contrib import admin
from django.views.decorators.cache import cache_page
from links.models import UserProfile
from links.views import cross_notif, vote, vote_on_vote
from django.views.generic.base import TemplateView
from links.views import LinkListView, TopView, PicHelpView, VoteOrProfileView, EmoticonsHelpView, UserSMSView, LogoutHelpView, DeletePicView, AuthPicsDisplayView, PicView, UserPhoneNumberView, PicExpiryView, PicsChatUploadView, VerifiedView, GroupHelpView, WelcomeView, WelcomeReplyView, WelcomeMessageView, NotifHelpView, MehfilView, LogoutReconfirmView, LogoutPenaltyView, GroupReportView, OwnerGroupOnlineKonView, AppointCaptainView, KickView, SmsReinviteView, OutsideMessageRecreateView, OutsiderGroupView, SmsInviteView, OutsideMessageCreateView, OutsideMessageView, DirectMessageCreateView, DirectMessageView, ClosedInviteTypeView, PrivateGroupView, PublicGroupView, OpenInviteTypeView, ReinviteView, LoginWalkthroughView, RegisterWalkthroughView, RegisterLoginView, ChangeGroupRulesView, ClosedGroupHelpView, ChangeGroupTopicView, GroupOnlineKonView, GroupListView, OpenGroupHelpView, GroupTypeView, GroupPageView, ClosedGroupCreateView, OpenGroupCreateView, InviteUsersToGroupView, OnlineKonView, UserProfileDetailView, UserProfileEditView, LinkCreateView, LinkDetailView, LinkUpdateView, LinkDeleteView, ScoreHelpView, UserSettingsEditView, HelpView, UnseenActivityView, WhoseOnlineView, RegisterHelpView, VerifyHelpView, PublicreplyView, ReportreplyView, UserActivityView, ReportView, HistoryHelpView#, UpvoteView, DownvoteView, MehfildecisionView CrossNotifView,


admin.autodiscover()

urlpatterns = patterns('',
	url(r'^admin/', include(admin.site.urls)),
	url(r'^$', LinkListView.as_view(), name='home'),
	url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}, name="login"),
	url(r'^logout/$', 'django.contrib.auth.views.logout_then_login', name="logout"),
	url(r'^logout_penalty/$', LogoutPenaltyView.as_view(), name='logout_penalty'),
	url(r'^logout_reconfirm/$', LogoutReconfirmView.as_view(), name='logout_reconfirm'),
	url(r'^logout_help/$', LogoutHelpView.as_view(), name='logout_help'),
	url(r'', include('user_sessions.urls', 'user_sessions')),
	#url(r'^register/$', MyRegistrationView.as_view(), name='registration_register'),
	#url(r'^register/closed/$', TemplateView.as_view(template_name='registration/registration_closed.html'),
	#                      name='registration_disallowed'),
	#(r'', include('registration.auth_urls')),
	url(r'^users/(?P<slug>[\w.@+-]+)/$', UserProfileDetailView.as_view(), name='profile'),#r'^[\w.@+-]+$'
	url(r'^vote_or_user/(?P<pk>\d+)/(?P<id>\d+)/(?P<num>\d+)/$', auth(VoteOrProfileView.as_view()), name='vote_or_profile'),#r'^[\w.@+-]+$'
	url(r'^edit_settings/$', auth(UserSettingsEditView.as_view()), name='edit_settings'),
	url(r'^edit_profile/$', auth(UserProfileEditView.as_view()), name='edit_profile'),
	url(r'^accounts/', include('registration.backends.simple.urls')),
	url(r'^closed_group/help/outside/$', auth(OutsideMessageView.as_view()), name='outside_message_help'),
	url(r'^closed_group/help/(?P<pk>\d+)/$', auth(DirectMessageView.as_view()), name='direct_message_help'),
	url(r'^mehfil/help/(?P<pk>\d+)/(?P<slug>[\w.@+-]+)/$', auth(MehfilView.as_view()), name='mehfil_help'),
	#url(r'^mehfil/help/(?P<pk>\d+)/$', auth(MehfildecisionView.as_view()), name='mehfil_decision'),
	url(r'^closed_group/create/(?P<pk>\d+)/$', auth(DirectMessageCreateView.as_view()), name='direct_message_create'),
	url(r'^closed_group/create/outside/$', auth(OutsideMessageCreateView.as_view()), name='outside_message_create'),
	url(r'^closed_group/recreate/outside/(?P<slug>[\w.@+-]+)/$', auth(OutsideMessageRecreateView.as_view()), name='outside_message_recreate'),
	url(r'^online_kon/$', auth(OnlineKonView.as_view()), name='online_kon'),
	url(r'^top/$', auth(TopView.as_view()), name='top'),
	url(r'^verified/$', auth(VerifiedView.as_view()), name='verified'),
	url(r'^users/(?P<slug>[\w.@+-]+)/activity/$', auth(UserActivityView.as_view()), name='user_activity'),
	url(r'^users/(?P<slug>[\w.@+-]+)/unseen/$', auth(UnseenActivityView.as_view()), name='unseen_activity'),
	#url(r'^users/(?P<slug>[\w.@+-]+)/message/$', auth(MessageActivityView.as_view()), name='message_activity'),
	url(r'^link/create/$', auth(LinkCreateView.as_view()), name='link_create'),
	url(r'^welcome/(?P<pk>\d+)/$', auth(WelcomeView.as_view()), name='welcome'),
	url(r'^welcome_reply/(?P<pk>\d+)/$', auth(WelcomeReplyView.as_view()), name='welcome_reply'),
	url(r'^welcome/(?P<pk>\d+)/(?P<option>\d+)/$', auth(WelcomeMessageView.as_view()), name='welcome_message'),
	url(r'^open_group/help/$', auth(OpenGroupHelpView.as_view()), name='open_group_help'),
	url(r'^closed_group/help/$', auth(ClosedGroupHelpView.as_view()), name='closed_group_help'),
	url(r'^open_group/create/$', auth(OpenGroupCreateView.as_view()), name='open_group_create'),
	url(r'^closed_group/create/$', auth(ClosedGroupCreateView.as_view()), name='closed_group_create'),
	url(r'^group/invite/(?P<slug>[\w.@+-]+)/$', auth(InviteUsersToGroupView.as_view()), name='invite'),
	url(r'^group/invite/(?P<slug>[\w.@+-]+)/(?P<num>[\w.@+-]+)/(?P<name>[\w.@+-]+)/$', auth(SmsInviteView.as_view()), name='sms_invite'),
	url(r'^group/invite/(?P<slug>[\w.@+-]+)/(?P<num>[\w.@+-]+)/$', auth(SmsReinviteView.as_view()), name='sms_reinvite'),
	url(r'^group/open_invite_type/(?P<slug>[\w.@+-]+)/$', auth(OpenInviteTypeView.as_view()), name='open_invite_type'),
	url(r'^group/closed_invite_type/(?P<slug>[\w.@+-]+)/$', auth(ClosedInviteTypeView.as_view()), name='closed_invite_type'),
	url(r'^link/(?P<pk>\d+)/$', LinkDetailView.as_view(), name='link_detail'),
	url(r'^score/$', auth(ScoreHelpView.as_view()), name='score_help'),
	url(r'^reinvite/(?P<slug>[\w.@+-]+)/$', auth(ReinviteView.as_view()), name='reinvite_help'),
	url(r'^history/$', auth(HistoryHelpView.as_view()), name='history_help'),
	url(r'^notif_help/(?P<pk>\d+)/$', auth(NotifHelpView.as_view()), name='notif_help'),
	url(r'^cross_notif/(?P<pk>\d+)/(?P<ident>\d+)/(?P<user>\d+)/$', cross_notif, name='x_notif'),
	url(r'^help/$', HelpView.as_view(), name='help'),
	url(r'^register_help/$', RegisterHelpView.as_view(), name='register_help'),
	url(r'^register_login/$', RegisterLoginView.as_view(), name='register_login'),
	url(r'^login_walkthrough/$', LoginWalkthroughView.as_view(), name='login_walkthrough'),
	url(r'^register_walkthrough/$', RegisterWalkthroughView.as_view(), name='register_walkthrough'),
	url(r'^verify_help/$', VerifyHelpView.as_view(), name='verify_help'),
	url(r'^group_help/$', GroupHelpView.as_view(), name='group_help'),
	url(r'^emoticons_help/$', EmoticonsHelpView.as_view(), name='emoticons_help'),
	url(r'^link/update/(?P<pk>\d+)/$', auth(LinkUpdateView.as_view()), name='link_update'),
	url(r'^link/delete/(?P<pk>\d+)/$', auth(LinkDeleteView.as_view()), name='link_delete'),
	url(r'^pic_expiry/(?P<slug>[\w.@+-]+)/$', PicExpiryView.as_view(), name='pic_expiry'),
	url(r'^delete_pic/(?P<slug>[\w.@+-]+)/$', DeletePicView.as_view(), name='delete_pic'),
	url(r'^pic_upload/$', PicsChatUploadView.as_view(), name='pic_upload'),
	url(r'^p/(?P<pk>\d+)/(?P<slug>[\w.@+-]+)/$', PicView.as_view(), name='pic_view'),
	url(r'^user_SMS/(?P<slug>[\w.@+-]+)/(?P<num>\d+)/$', UserSMSView.as_view(), name='user_SMS'),
	url(r'^p/$', PicHelpView.as_view(), name='pic_help'),
	url(r'^user_phonenumber/(?P<slug>[\w.@+-]+)/(?P<num>\d+)/$', UserPhoneNumberView.as_view(), name='user_phonenumber'),
	#url(r'^send_pic_sms/(?P<slug>[\w.@+-]+)/(?P<num>\d+)/$', SendPicSMSView.as_view(), name='send_pic_sms'),
	url(r'^auth_pics_display/$', auth(AuthPicsDisplayView.as_view()), name='auth_pics_display'),
	url(r'^comments/', include('django.contrib.comments.urls')),
	url(r'^vote_on_vote/(?P<vote_id>\d+)/(?P<target_id>\d+)/(?P<link_submitter_id>\d+)/(?P<val>\d+)/$', auth(vote_on_vote), name='vote_on_vote'),
	url(r'^vote/(?P<pk>\d+)/(?P<usr>\d+)/(?P<loc>\d+)/(?P<val>\d+)/$', auth(vote), name='vote'),
	# url(r'^upvote/$', UpvoteView.as_view(), name='confirm_upvote'),
	# url(r'^downvote/$', DownvoteView.as_view(), name='confirm_downvote'),
	url(r'^link/(?P<pk>\d+)/reply/$', auth(PublicreplyView.as_view()), name='reply'),
	url(r'^mehfil/(?P<slug>[\w.@+-]+)/public/$', auth(PublicGroupView.as_view()), name='public_group_reply'),
	url(r'^mehfil/(?P<slug>[\w.@+-]+)/private/$', auth(PrivateGroupView.as_view()), name='private_group_reply'),
	url(r'^mehfil/(?P<slug>[\w.@+-]+)/outsider/$', OutsiderGroupView.as_view(), name='outsider_group_reply'),####
	url(r'^group/(?P<slug>[\w.@+-]+)/change_topic/$', auth(ChangeGroupTopicView.as_view()), name='change_topic'),
	url(r'^group/(?P<slug>[\w.@+-]+)/change_rules/$', auth(ChangeGroupRulesView.as_view()), name='change_rules'),
	url(r'^group/(?P<slug>[\w.@+-]+)/online_kon/$', auth(GroupOnlineKonView.as_view()), name='group_online_kon'),
	url(r'^group/(?P<slug>[\w.@+-]+)/owner_online_kon/$', auth(OwnerGroupOnlineKonView.as_view()), name='owner_group_online_kon'),
	url(r'^group/$', auth(GroupPageView.as_view()), name='group_page'),
	url(r'^group_list/$', auth(GroupListView.as_view()), name='group_list'),
	url(r'^group_type/$', auth(GroupTypeView.as_view()), name='group_type'),
	url(r'^report/(?P<pk>\d+)/$', auth(ReportreplyView.as_view()), name='reportreply'),
	url(r'^appoint/(?P<pk>\d+)/(?P<slug>[\w.@+-]+)/(?P<app>\d+)/$', auth(AppointCaptainView.as_view()), name='appoint'),
	url(r'^report/$', auth(ReportView.as_view()), name="report"),
	url(r'^groupreport/(?P<slug>[\w.@+-]+)/(?P<pk>\d+)/$', auth(GroupReportView.as_view()), name="group_report"),
	url(r'^kick/(?P<pk>\d+)/(?P<slug>[\w.@+-]+)/(?P<id>\d+)/$', auth(KickView.as_view()), name='kick'),
	#url(r'^kick/$', auth(KickView.as_view()), name='kick'),
)