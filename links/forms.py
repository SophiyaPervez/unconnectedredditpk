# coding=utf-8
from django import forms
from django.forms import Textarea
from tasks import log_gibberish_writer, invalidate_avatar_url
from redis4 import retrieve_previous_msgs,many_short_messages, log_short_message, is_limited, get_and_delete_text_input_key, get_aurl
from .models import UserProfile, TutorialFlag, ChatInbox, PhotoStream, PhotoComment, ChatPicMessage, Photo, Link, Vote, \
ChatPic, UserSettings, Publicreply, Group, GroupInvite, Reply, GroupTraffic, GroupCaptain, VideoComment
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.core import validators
from django.core.files.images import get_image_dimensions
from django.utils.translation import ugettext, ugettext_lazy as _
from image_processing import compute_avg_hash, reorient_image, make_thumbnail
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
import re, time, random
from user_sessions.models import Session
import unicodedata

########################################### Utilities #######################################

def repetition_found(section,section_id,user_id, target_text):
	msgs_list = retrieve_previous_msgs(section=section, section_id=section_id,user_id=user_id)
	if msgs_list:
		if target_text in [x.decode('utf-8') for x in msgs_list[1:]]:
			return True
		else:
			return False
	else:
		return False


def uniform_string(text,n=8):
	text = text.lower()
	for i, c in enumerate(text):
		if text[i:i+n] == c * n:
			return text[i:i+n]
	return False

def getip(request):
	ip = request.META.get('X-IORG-FBS-UIP',
		request.META.get('REMOTE_ADDR')
	)
	return ip

def clear_zalgo_text(text):
	return ''.join((c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn'))

def human_readable_time(future_time_in_seconds):
	try:
		m, s = divmod(future_time_in_seconds, 60)
		h, m = divmod(m, 60)
		d, h = divmod(h, 24)
		mo, d = divmod(d, 30)
		if mo:
			mo = int(mo)
			if mo == 1:
				return "1 month"
			else:
				return "%s months" % mo
		elif d:
			d = int(d)
			if d == 1:
				return "1 day"
			else:
				return "%s days" % d
		elif h:
			h = int(h)
			if h == 1:
				return "1 hour"
			else:
				return "%s hours" % h
		elif m:
			m = int(m)
			if m == 1:
				return "1 min"
			else:
				return "%s mins" % m
		elif s:
			s = int(s)
			if s == 1:
				return "1 sec"
			else:
				return "%s secs" % s
		else:
			return "kuch waqt"
	except (NameError,TypeError):
		return "kuch waqt"

################################################################################################


class UserProfileForm(forms.ModelForm): #this controls the userprofile edit form
	MardAurat = (
		('1','Girl'),
		('0','Boy'),
		)
	MaritalStatus = (
		('1','Yes'),
		('0','No'),
		)
	RATING = (
		('0','Ek dum kadak'),
		('1','Fifty fifty'),
		('2','Shakal pe mat ja'),
	)
	avatar = forms.ImageField(label='Photo Lagao', help_text='less than 1 mb', required=False)
	gender = forms.TypedChoiceField(choices=MardAurat, widget=forms.RadioSelect, coerce=int)
	shadi_shuda = forms.TypedChoiceField(choices=MaritalStatus, widget=forms.RadioSelect, coerce=int)
	attractiveness = forms.TypedChoiceField(choices=RATING, widget=forms.RadioSelect, coerce=int)
	bio = forms.CharField(widget=forms.Textarea(attrs={'cols':40,'rows':3,'style':'max-width:98%;'}))
	mobilenumber = forms.CharField(widget=forms.Textarea(attrs={'cols':30,'rows':1,'style':'max-width:80%;'}))
	age = forms.CharField(widget=forms.Textarea(attrs={'cols':10,'rows':1,'style':'max-width:50%;'}))
	class Meta:
		model = UserProfile
		exclude = ('user','previous_retort') #so user and previous_retort doesn't show, but the extended attributes of bio and mobile number do show
		fields=('avatar', 'mobilenumber', 'bio', 'gender', 'age', 'shadi_shuda', 'attractiveness')

	def __init__(self, *args, **kwargs):
		# you take the user out of kwargs and store it as a class attribute
		self.user = kwargs.pop('user', None)
		super(UserProfileForm, self).__init__(*args, **kwargs)
		self.fields['avatar'].widget.attrs['style'] = 'width:95%;'
		# self.fields['avatar'].widget.attrs['accept'] = 'image/*'

	def clean_avatar(self):
		image=self.cleaned_data.get("avatar")
		try:
			if image.name in self.user.userprofile.avatar.url:
				#print "no need to re-submit image"
				return image
		except (AttributeError, ValueError):
			pass
		if image or image is False:	
			user_id = self.user.id
			ttl = get_aurl(user_id)
			if ttl > 1:
				raise forms.ValidationError('Ap profile photo change kar sakien ge %s secs baad' % ttl)
			invalidate_avatar_url.delay(user_id, set_rate_limit=True)
			if image:
				try:
					if image.size > 1000000:
						return 0
				except:
					pass
				image = Image.open(image)
				image = make_thumbnail(image,None)
				return image
			else:
				return 0
		else:
			return None

	def clean_bio(self):
		bio = self.cleaned_data.get("bio")
		bio = bio.strip()
		bio = clear_zalgo_text(bio)
		return bio

	def clean_age(self):
		age = self.cleaned_data.get("age")
		if len(age) > 2:
			raise forms.ValidationError('Age sahi likhein')
		return age

class UserSettingsForm(forms.ModelForm):
	ScoreVisible = (
		('0','No'),
		('1','Yes'),
		)
	score_setting = forms.TypedChoiceField(choices=ScoreVisible, widget=forms.RadioSelect, coerce=int)
	class Meta:
		model = UserSettings
		exclude = ('user', 'setting2', 'setting3', 'setting4', 'setting5')
		fields = ('score_setting',)

class CricketCommentForm(forms.Form): #a 'Form' version of the LinkForm modelform
	description = forms.CharField(widget=forms.Textarea(attrs={'cols':40,'rows':3,'style':'width:98%;',\
		'class': 'cxl','autocomplete': 'off','autocapitalize':'off','spellcheck':'false'}))
	sk = forms.CharField(required=False)

	class Meta:
		fields = ("description",)

	def __init__(self,*args,**kwargs):
		self.user_id = kwargs.pop('user_id',None)
		super(CricketCommentForm, self).__init__(*args, **kwargs)
		self.fields['description'].widget.attrs['style'] = 'width:95%;height:50px;border-radius:10px;border: 1px #E0E0E0 solid; background-color:#FAFAFA;padding:5px;'

	def clean(self):
		data = self.cleaned_data
		user_id, description, section_id, section, secret_key_from_form = self.user_id, data.get("description"), '1', 'home', data.get("sk")
		description = description.strip() if description else None
		if not description:
			raise forms.ValidationError('tip: likhna zaruri hai')
		secret_key_from_session = get_and_delete_text_input_key(user_id,'1','home')
		if secret_key_from_form != secret_key_from_session:
			raise forms.ValidationError('tip: sirf aik dafa button dabain')
		if repetition_found(section=section,section_id=section_id,user_id=user_id, target_text=description):
			raise forms.ValidationError('tip: milti julti baatien nah likho, kuch new likho')
		else:
			rate_limited, reason = is_limited(user_id,section='home',with_reason=True)
			if rate_limited > 0:
				raise forms.ValidationError('Ap yahan likhne se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
			else:
				desc_len = len(description)
				# if desc_len < 2:
				# 	raise forms.ValidationError('tip: itna choti baat nahi likh sakte')
				if desc_len < 6:
					if many_short_messages(user_id,section,section_id):
						raise forms.ValidationError('tip: har thori deir baad yahan choti baat nah likhein')
					else:
						log_short_message(user_id,section,section_id)
				elif desc_len > 500:
					raise forms.ValidationError('tip: itna barri baat nahi likh sakte')
				# description = clear_zalgo_text(description)
				# uni_str = uniform_string(description)
				# if uni_str:
				# 	if uni_str.isspace():
				# 		raise forms.ValidationError('tip: ziyada spaces daal di hain')
				# 	else:
				# 		raise forms.ValidationError('tip: "%s" ki terhan bar bar ek hi harf nah likho' % uni_str)
				return data


class LinkForm(forms.ModelForm):#this controls the link edit form
	description = forms.CharField(label='Likho:', widget=forms.Textarea(attrs={'cols':40,'rows':3,'style':'width:98%;',\
		'class': 'cxl','autofocus': 'autofocus','autocomplete': 'off','autocapitalize':'off','spellcheck':'false'}),\
	error_messages={'required': 'Pehlay kuch likhein, phir OK dabain'})
	sk = forms.CharField(required=False)

	class Meta:
		model = Link
		exclude = ("submitter", "rank_score", "cagtegory",)
		fields = ("image_file", "description",)

	def __init__(self,*args,**kwargs):
		self.user_id = kwargs.pop('user_id',None)
		super(LinkForm, self).__init__(*args,**kwargs)
		self.fields['description'].widget.attrs['style'] = 'width:95%;height:50px;border-radius:10px;border: 1px #E0E0E0 solid; background-color:#FAFAFA;padding:5px;'

	def clean(self):
		data = self.cleaned_data
		description, user_id, section_id, section, secret_key_from_form = data.get("description"), self.user_id, '1', 'home', data.get("sk")
		secret_key_from_session = get_and_delete_text_input_key(user_id,'1','likho')
		description = description.strip() if description else None
		if not description:
			raise forms.ValidationError('tip: likhna zaruri hai')
		elif secret_key_from_form != secret_key_from_session:
			raise forms.ValidationError('tip: sirf aik dafa button dabain')
		elif repetition_found(section=section,section_id=section_id,user_id=user_id, target_text=description):
			raise forms.ValidationError('tip: milti julti baatien nah likho, kuch new likho')
		else:
			rate_limited, reason = is_limited(user_id,section='home',with_reason=True)
			if rate_limited > 0:
				raise forms.ValidationError('Ap home pe likhne se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
			else:
				len_ = len(description)
				if len_ < 2:
					raise forms.ValidationError('tip: itni choti baat nahi likh sakte')
				elif len_ < 6:
					if many_short_messages(user_id,section,section_id):
						raise forms.ValidationError('tip: har thori deir baad yahan choti baat nah likhein')
					else:
						log_short_message(user_id,section,section_id)
				elif len_ > 500:
					raise forms.ValidationError('tip: itni barri baat nahi likh sakte')
				# description = clear_zalgo_text(description)
				# uni_str = uniform_string(description)
				# if uni_str:
				# 	if uni_str.isspace():
				# 		raise forms.ValidationError('tip: ziyada spaces daal di hain')
				# 	else:
				# 		raise forms.ValidationError('"%s" is terhan bar bar ek hi harf nah likho' % uni_str)
				log_gibberish_writer.delay(user_id,description,len_) # flags the user_id in case the text turned out to be gibberish
				return data

class PublicGroupReplyForm(forms.ModelForm):
	text = forms.CharField(required=False,widget=forms.Textarea(attrs={'cols':40,'rows':3,'autofocus': 'autofocus',\
		'class': 'cxl','autocomplete': 'off','autocapitalize':'off','spellcheck':'false'}),error_messages={'required': 'tip: likhna zaruri hai'})
	image = forms.ImageField(required=False,error_messages={'invalid_image': 'tip: photo sahi nahi hai'})
	sk = forms.CharField(required=False)
	gp = forms.IntegerField()

	class Meta:
		model = Reply
		exclude = ("submitted_on","which_group","writer","abuse")
		fields = ("image", "text")

	def __init__(self,*args,**kwargs):
		self.user_id = kwargs.pop('user_id',None)
		self.is_mob_verified = kwargs.pop('is_mob_verified',None)
		super(PublicGroupReplyForm, self).__init__(*args,**kwargs)
		# self.fields['image'].widget.attrs['accept'] = 'image/*'
		self.fields['image'].widget.attrs['id'] = 'pub_grp_browse_image_btn'
		self.fields['text'].widget.attrs['id'] = 'pub_grp_text_field'
		self.fields['text'].widget.attrs['style'] = 'width:99%;height:50px;border-radius:10px;border: 1px #E0E0E0 solid; background-color:#FAFAFA;padding:5px;'

	def clean(self):
		data = self.cleaned_data
		text, user_id, section_id, section, image, secret_key_from_form = data.get("text"), self.user_id, data.get("gp"), 'pub_grp', \
		data.get('image'), data.get('sk')
		secret_key_from_session = get_and_delete_text_input_key(self.user_id,section_id,'pub_grp')
		text = text.strip() if text else text # make function sophisticated https://stackoverflow.com/questions/1546226/simple-way-to-remove-multiple-spaces-in-a-string
		if secret_key_from_form != secret_key_from_session:
			raise forms.ValidationError('tip: sirf aik dafa button dabain')
		elif not text:
			if image:
				rate_limited, reason = is_limited(user_id,section='pub_grp',with_reason=True)
				if rate_limited > 0:
					raise forms.ValidationError('Ap open mehfils mein likhne se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
				elif not self.is_mob_verified:
					raise forms.ValidationError('tip: yahan foto laganey ke liye apna mobile number verify karwain')
				else:
					data["text"] = random.choice(["... ... ...",".. .. ..","... .. ...",".. ... ..","... ... ..",".. ... ...",". ... .",\
						". . . . .",".. .. .. ..",".... . ....","... .... ..."]) # for aesthetic reasons
					return data
			else:
				raise forms.ValidationError('tip: likhna zaruri hai')
		else:
			if repetition_found(section=section,section_id=section_id,user_id=user_id, target_text=text):
				raise forms.ValidationError('tip: milti julti baatien nah likho, kuch new likho')
			else:
				rate_limited, reason = is_limited(user_id,section='pub_grp',with_reason=True)
				if rate_limited > 0:
					raise forms.ValidationError('Ap open mehfils mein likhne se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
				else:
					text_len = len(text)
					# if text_len < 1:
					# 	raise forms.ValidationError('tip: likhna zaruri hai')
					# elif text_len < 2:
					# 	raise forms.ValidationError('tip: itni choti baat nahi likh sakte')
					if text_len < 6:
						if many_short_messages(user_id,section,section_id):
							raise forms.ValidationError('tip: har thori deir baad yahan choti baat nah likhein')
						else:
							log_short_message(user_id,section,section_id)
					elif text_len > 500:
						raise forms.ValidationError('tip: itni barri baat nahi likh sakte')
					if not self.is_mob_verified:
						raise forms.ValidationError('tip: yahan likhne ke liye apna mobile number verify karwain')
					# text = clear_zalgo_text(text)
					# uni_str = uniform_string(text)
					# if uni_str:
					# 	if uni_str.isspace():
					# 		raise forms.ValidationError('tip: ziyada spaces daal di hain')
					# 	else:
					# 		raise forms.ValidationError('tip: "%s" ki terhan bar bar ek hi harf nah likhein' % uni_str)
					data["text"] = text
					return data
		
class OutsiderGroupForm(forms.ModelForm):
	text = forms.CharField(label='Likho:',widget=forms.Textarea(attrs={'cols':40,'rows':3}))
	class Meta:
		model = Reply
		exclude = ("submitted_on","which_group","writer","abuse")
		fields = ("image", "text")

class PrivateGroupReplyForm(forms.ModelForm):
	text = forms.CharField(required=False,widget=forms.Textarea(attrs={'cols':40,'rows':3,'autofocus': 'autofocus','class': 'cxl',\
		'autocomplete': 'off','autocapitalize':'off','spellcheck':'false'}),error_messages={'required': 'tip: likhna zaruri hai'})
	image = forms.ImageField(required=False,error_messages={'invalid_image': 'tip: photo sahi nahi hai'})
	sk = forms.CharField(required=False)
	gp = forms.IntegerField()
	
	class Meta:
		model = Reply
		exclude = ("submitted_on","which_group","writer","abuse")
		fields = ("image", "text")

	def __init__(self,*args,**kwargs):
		self.user_id = kwargs.pop('user_id',None)
		super(PrivateGroupReplyForm, self).__init__(*args,**kwargs)
		self.fields['text'].widget.attrs['style'] = 'width:99%;height:50px;border-radius:10px;border: 1px #E0E0E0 solid; background-color:#FAFAFA;padding:5px;'

	def clean(self):
		data = self.cleaned_data
		text, user_id, section_id, section, image, secret_key_from_form = data.get("text"), self.user_id, data.get("gp"), 'prv_grp', \
		data.get("image"), data.get("sk")
		secret_key_from_session = get_and_delete_text_input_key(self.user_id,section_id,'prv_grp')
		text = text.strip() if text else text
		if not text:
			if image:
				rate_limited, reason = is_limited(user_id,section='prv_grp',with_reason=True)
				if rate_limited > 0:
					raise forms.ValidationError('Ap private mehfils mein likhne se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
				else:
					data["text"] = random.choice(["... ... ...",".. .. ..","... .. ...",".. ... ..","... ... ..",".. ... ...",". ... .",\
						". . . . .",".. .. .. ..",".... . ....","... .... ..."]) # for aesthetic reasons
					return data
			else:
				raise forms.ValidationError('tip: likhna zaruri hai')
		elif secret_key_from_form != secret_key_from_session:
			raise forms.ValidationError('tip: sirf aik dafa button dabain')
		else:
			if repetition_found(section=section,section_id=section_id,user_id=user_id, target_text=text):
				raise forms.ValidationError('tip: milti julti baatien nah likho, kuch new likho')
			else:
				rate_limited, reason = is_limited(user_id,section='prv_grp',with_reason=True)
				if rate_limited > 0:
					raise forms.ValidationError('Ap private mehfils mein likhne se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
				else:
					text_len = len(text)
					if text_len < 1:
						raise forms.ValidationError('tip: likhna zaruri hai')
					# elif text_len < 2:
					# 	raise forms.ValidationError('tip: itni choti baat nahi likh sakte')
					if text_len < 6:
						if many_short_messages(user_id,section,section_id):
							raise forms.ValidationError('tip: har thori deir baad yahan choti baat nah likhein')
						else:
							log_short_message(user_id,section,section_id)
					elif text_len > 500:
						raise forms.ValidationError('tip: itni barri baat nahi likh sakte')
					# text = clear_zalgo_text(text)
					# uni_str = uniform_string(text)
					# if uni_str:
					# 	if uni_str.isspace():
					# 		raise forms.ValidationError('tip: ziyada spaces daal di hain')
					# 	else:
					# 		raise forms.ValidationError('tip: "%s" ki terhan bar bar ek hi harf nah likho' % uni_str)
					data["text"] = text
					return data


class WelcomeMessageForm(forms.ModelForm):
	description = forms.CharField(widget=forms.Textarea(attrs={'cols':40,'rows':3}))

	class Meta:
		model = Publicreply
		exclude = ("submitted_by","answer_to","seen","category","abuse","submitted_on")
		fields = ("description",)

class CommentForm(forms.ModelForm):
	text = forms.CharField(widget=forms.Textarea(attrs={'cols':30,'rows':2,'style':'width:98%;','class': 'cxl','autofocus': 'autofocus',\
		'autocomplete': 'off','autocapitalize':'off','spellcheck':'false'}))
	sk = forms.CharField(required=False)

	class Meta:
		model = PhotoComment
		exclude = ("which_video", "device", "submitted_by", "submitted_on",)
		fields = ("text",)

	def __init__(self,*args,**kwargs):
		self.user_id = kwargs.pop('user_id',None)
		self.photo_id = kwargs.pop('photo_id',None)
		super(CommentForm, self).__init__(*args,**kwargs)
		self.fields['text'].widget.attrs['style'] = 'width:99%;height:50px;border-radius:10px;border: 1px #E0E0E0 solid; background-color:#FAFAFA;padding:5px;'

	def clean(self):
		data = self.cleaned_data
		text, user_id, photo_id, section, secret_key_from_form = data.get("text"), self.user_id, self.photo_id, 'pht_comm', data.get("sk")
		secret_key_from_session = get_and_delete_text_input_key(self.user_id,self.photo_id,'pht_comm')
		if secret_key_from_form != secret_key_from_session:
			raise forms.ValidationError('tip: sirf aik dafa button dabain')
		text = text.strip() if text else text
		if not text:
			raise forms.ValidationError('tip: likhna zaruri hai')
		elif repetition_found(section=section,section_id=photo_id,user_id=user_id, target_text=text):
			raise forms.ValidationError('tip: milti julti baatien nah likho, kuch new likho')
		else:
			rate_limited, reason = is_limited(user_id,section='pht_comm',with_reason=True)
			if rate_limited > 0:
				raise forms.ValidationError('Ap photos pe comment karney se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
			else:
				text_len = len(text)
				# if text_len < 2:
				# 	raise forms.ValidationError('tip: tabsre mein itna chota lafz nahi likh sakte')
				if text_len < 6:
					if many_short_messages(user_id,section,photo_id):
						raise forms.ValidationError('tip: har thori deir baad yahan choti baat nah likhein')
					else:
						log_short_message(user_id,section,photo_id)
				elif text_len > 250:
					raise forms.ValidationError('tip: inta bara tabsra nahi likh sakte')
				# text = clear_zalgo_text(text)
				# uni_str = uniform_string(text)
				# if uni_str:
				# 	if uni_str.isspace():
				# 		raise forms.ValidationError('tip: ziyada spaces daal di hain')
				# 	else:
				# 		raise forms.ValidationError('tip: "%s" ki terhan bar bar ek hi harf nah likho' % uni_str)
				return data

class VideoCommentForm(forms.ModelForm):
	text = forms.CharField(widget=forms.Textarea(attrs={'cols':30,'rows':2,'style':'width:98%;'}))
	class Meta:
		model = VideoComment
		exclude = ("which_photo", "device", "submitted_by", "submitted_on",)
		fields = ("text",)

class PublicreplyForm(forms.ModelForm):
	description = forms.CharField(label='Jawab:', widget=forms.Textarea(attrs={'cols':30,'rows':2,'style':'width:98%;',\
		'class': 'cxl','autofocus': 'autofocus','autocomplete': 'off','autocapitalize':'off','spellcheck':'false'}), \
	error_messages={'required': 'Pehlay jawab likhein, phir OK dabain'})
	sk = forms.CharField(required=False)

	class Meta:
		model = Publicreply
		exclude = ("submitted_by","answer_to","seen","category","abuse","submitted_on")
		fields = ("description",)

	def __init__(self,*args,**kwargs):
		self.user_id = kwargs.pop('user_id',None)
		self.link_id = kwargs.pop('link_id',None)
		super(PublicreplyForm, self).__init__(*args,**kwargs)
		self.fields['description'].widget.attrs['style'] = 'width:99%;height:50px;border-radius:10px;border: 1px #E0E0E0 solid; background-color:#FAFAFA;padding:5px;'

	def clean_sk(self):															
		secret_key_from_form, secret_key_from_session = self.cleaned_data.get("sk"), get_and_delete_text_input_key(self.user_id,self.link_id,'home_rep')
		if secret_key_from_form != secret_key_from_session:
			raise forms.ValidationError('tip: sirf aik dafa button dabain')
		return secret_key_from_form

	def clean_description(self):
		description, user_id, section_id, section = self.cleaned_data.get("description"), self.user_id, self.link_id, 'home_rep'
		description = description.strip() if description else None
		if not description:
			raise forms.ValidationError('tip: likhna zaruri hai')
		elif repetition_found(section=section,section_id=section_id,user_id=user_id, target_text=description):
			raise forms.ValidationError('tip: milte julte jawab nah likho, kuch new likho')
		else:
			rate_limited, reason = is_limited(user_id,section='home_rep',with_reason=True)
			if rate_limited > 0:
				raise forms.ValidationError('Ap jawab dene se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
			else:
				desc_len = len(description)
				# if desc_len < 2:
				# 	raise forms.ValidationError('tip: itna chota jawab nahi likh sakte')
				if desc_len < 6:
					if many_short_messages(user_id,section,section_id):
						raise forms.ValidationError('tip: har thori deir baad yahan choti baat nah likhein')
					else:
						log_short_message(user_id,section,section_id)
				elif desc_len > 250:
					raise forms.ValidationError('tip: inta bara jawab nahi likh sakte')
				# description = clear_zalgo_text(description)
				# uni_str = uniform_string(description)
				# if uni_str:
				# 	if uni_str.isspace():
				# 		raise forms.ValidationError('tip: ziyada spaces daal di hain')
				# 	else:
				# 		raise forms.ValidationError('tip: "%s" ki terhan bar bar ek hi harf nah likho' % uni_str)
				return description


class PublicreplyMiniForm(PublicreplyForm):
	description = forms.CharField(max_length=250, error_messages={'required': 'Pehlay yahan jawab likhein, phir "Jawab do" dabain'})
	sk = forms.CharField(required=False)

	def __init__(self,*args,**kwargs):
		super(PublicreplyMiniForm, self).__init__(*args,**kwargs)
		self.fields['description'].widget.attrs['class'] = 'box-with-button-right cdt ml'
		self.fields['description'].widget.attrs['style'] = 'border: 1px solid lightgrey; border-radius:20px; line-height:30px;'
		self.fields['description'].widget.attrs['autocomplete'] = 'off'											

	def clean_sk(self):
		secret_key_from_form, secret_key_from_session = self.cleaned_data.get("sk"), get_and_delete_text_input_key(self.user_id, '1', 'home')
		if secret_key_from_form != secret_key_from_session:
			raise forms.ValidationError('tip: sirf aik dafa button dabain')
		return secret_key_from_form

class SearchNicknameForm(forms.Form):
	nickname = forms.CharField(max_length=71)

	def __init__(self, *args, **kwargs):
		super(SearchNicknameForm, self).__init__(*args, **kwargs)
		self.fields['nickname'].widget.attrs['style'] = \
		'max-width:90%;width:500px;background-color:#F8F8F8;border: 1px solid #179b36;border-radius:5px;padding: 6px 6px 6px 0;text-indent: 6px;color: #179b36;'
		self.fields['nickname'].widget.attrs['class'] = 'cxl'
		# self.fields['nickname'].widget.attrs['autofocus'] = 'autofocus'
		self.fields['nickname'].widget.attrs['autocomplete'] = 'off'

	def clean_nickname(self):
		nickname = self.cleaned_data.get("nickname")
		nickname = nickname.strip()
		if len(nickname) > 70:
			raise forms.ValidationError('tip: inta bara nickname nahi likh sakte')
		# nickname = clear_zalgo_text(nickname)
		return nickname

class CaptionDecForm(forms.Form):
	class Meta:
		pass

class PhotostreamForm(forms.Form):
	class Meta:
		pass

class CaptionForm(forms.ModelForm):
	caption = forms.CharField(max_length=150)
	class Meta:
		model = ChatPicMessage
		exclude = ("which_pic","viewing_time","sending_time","expiry_interval","what_number","seen")
		fields = ("caption",)

class UserPhoneNumberForm(forms.ModelForm):
	what_number = forms.CharField(label='Mobile number:', max_length=50)
	class Meta:
		model = ChatPicMessage
		exclude = ("which_pic","viewing_time","sending_time","expiry_interval","caption","seen")
		fields = ("what_number",)

class UserSMSForm(forms.Form):
	class Meta:
		pass

class AdImageForm(forms.ModelForm):
	image = forms.ImageField(label='Upload', error_messages={'required': 'Photo ka intekhab sahi nahi hua'})
	class Meta:
		model = ChatPic
		exclude = ("sender","sending_time", "sms_created", "expiry_interval")
		fields = ("image",)

	def __init__(self, *args, **kwargs):
		super(AdImageForm, self).__init__(*args, **kwargs)
		self.fields['image'].widget.attrs['style'] = 'width:95%;'

class AdImageYesNoForm(forms.Form):
	class Meta:
		pass

class AdAddressYesNoForm(forms.Form):
	class Meta:
		pass

class AdCallPrefForm(forms.Form):
	class Meta:
		pass

class AdGenderChoiceForm(forms.Form):
	class Meta:
		pass

class AdTitleYesNoForm(forms.Form):
	class Meta:
		pass

class AdAddressForm(forms.Form):
	address = forms.CharField(max_length=250)
	class Meta:
		fields = ("address",)

class AdTitleForm(forms.Form):
	title = forms.CharField(max_length=250)
	class Meta:
		fields = ("title",)

class TestAdsForm(forms.Form):
	class Meta:
		pass

class TestReportForm(forms.Form):
	class Meta:
		pass

class AdMobileNumForm(forms.Form):
	mobile_number = forms.CharField(max_length=20)
	class Meta:
		fields = ("mobile_number",)

class AdDescriptionForm(forms.Form):
	description = forms.CharField(max_length=250)
	class Meta:
		fields = ("description",)

class ReportFeedbackForm(forms.Form):
	description = forms.CharField(max_length=250)
	class Meta:
		fields = ("description",)

class PhotoCommentForm(forms.Form):
	photo_comment = forms.CharField(max_length=250, error_messages={'required': 'Pehlay yahan kuch likhein, phir "tabsra kro" button dabain'})
	sk = forms.CharField(required=False)
	origin = forms.CharField(required=False)

	class Meta:
		fields = ("photo_comment",)

	def __init__(self,*args,**kwargs):
		self.user_id = kwargs.pop('user_id',None)
		self.photo_id = kwargs.pop('photo_id',None)
		super(PhotoCommentForm, self).__init__(*args, **kwargs)
		self.fields['photo_comment'].widget.attrs['class'] = 'box-with-button-right cdo'
		self.fields['photo_comment'].widget.attrs['style'] = 'border: 1px solid lightgrey; border-radius:20px;'
		self.fields['photo_comment'].widget.attrs['autocomplete'] = 'off'

	def clean(self):
		data = self.cleaned_data
		comment, user_id, photo_id, section, secret_key_from_form, origin = data.get("photo_comment"), self.user_id, self.photo_id, \
		'pht_comm', data.get("sk"), data.get("origin")
		if origin == '1':
			org = 'fresh_photos'
		elif origin == '3':
			org = 'home'
		else:
			org = 'best_photos'
		secret_key_from_session = get_and_delete_text_input_key(user_id,'1',org)
		if secret_key_from_form != secret_key_from_session:
			raise forms.ValidationError('tip: sirf aik dafa button dabain')
		comment = comment.strip() if comment else comment
		if not comment:
			raise forms.ValidationError('tip: likhna zaruri hai')
		elif repetition_found(section=section,section_id=photo_id,user_id=user_id, target_text=comment):
			raise forms.ValidationError('tip: milti julti baatien nah likho, kuch new likho')
		else:
			rate_limited, reason = is_limited(user_id,section='pht_comm',with_reason=True)
			if rate_limited > 0:
				raise forms.ValidationError('Ap photos pe comment karney se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
			else:
				comm_len = len(comment)
				# if comm_len < 2:
				# 	raise forms.ValidationError('tip: itna chota lafz nahi likh sakte')
				if comm_len < 6:
					if many_short_messages(user_id,section,photo_id):
						raise forms.ValidationError('tip: har thori deir baad yahan choti baat nah likhein')
					else:
						log_short_message(user_id,section,photo_id)
				elif comm_len > 250:
					raise forms.ValidationError('tip: inti barri baat nahi likh sakte')
				# comment = clear_zalgo_text(comment)
				# uni_str = uniform_string(comment)
				# if uni_str:
				# 	if uni_str.isspace():
				# 		raise forms.ValidationError('tip: ziyada spaces daal di hain')
				# 	else:
				# 		raise forms.ValidationError('tip: "%s" ki terhan bar bar ek hi harf nah likho' % uni_str)
				return data


class UnseenActivityForm(forms.Form):
	home_comment = forms.CharField(required=False, max_length=250, error_messages={'required': 'Pehlay yahan jawab likhein, phir "jawab do" button dabain'})
	photo_comment = forms.CharField(required=False, max_length=250, error_messages={'required': 'Pehlay yahan kuch likhein, phir "tabsra kro" button dabain'})
	public_group_reply = forms.CharField(required=False, max_length=500, error_messages={'required': 'Pehlay yahan jawab likhein, phir "jawab do" button dabain'})
	private_group_reply = forms.CharField(required=False, max_length=500, error_messages={'required': 'Pehlay yahan jawab likhein, phir "jawab do" button dabain'})
	personal_group_reply = forms.CharField(required=False, max_length=500, error_messages={'required': 'Pehlay yahan jawab likhein, phir "jawab do" button dabain'})
	sk = forms.CharField(required=False)
	origin = forms.CharField(required=False)

	class Meta:
		fields = ("home_comment", "photo_comment", "public_group_reply", "private_group_reply", "personal_group_reply")

	def __init__(self,*args,**kwargs):
		self.user_id = kwargs.pop('user_id',None)
		self.link_id = kwargs.pop('link_id',None)
		self.photo_id = kwargs.pop('photo_id',None)
		self.pub_grp_id = kwargs.pop('pub_grp_id',None)
		self.prv_grp_id = kwargs.pop('prv_grp_id',None)
		self.per_grp_id = kwargs.pop('per_grp_id',None)
		super(UnseenActivityForm, self).__init__(*args, **kwargs)
		self.fields['public_group_reply'].widget.attrs['class'] = 'box-with-button-right cp'
		self.fields['public_group_reply'].widget.attrs['style'] = 'border: 1px solid #765989'
		self.fields['public_group_reply'].widget.attrs['autocomplete'] = 'off'
		self.fields['public_group_reply'].widget.attrs['autocapitalize'] = 'off'
		self.fields['public_group_reply'].widget.attrs['spellcheck'] = 'false'

		self.fields['private_group_reply'].widget.attrs['class'] = 'box-with-button-right cdg'
		self.fields['private_group_reply'].widget.attrs['style'] = 'border: 1px solid #00c853'
		self.fields['private_group_reply'].widget.attrs['autocomplete'] = 'off'
		self.fields['private_group_reply'].widget.attrs['autocapitalize'] = 'off'
		self.fields['private_group_reply'].widget.attrs['spellcheck'] = 'false'

		self.fields['home_comment'].widget.attrs['class'] = 'box-with-button-right cdt'
		self.fields['home_comment'].widget.attrs['style'] = 'border: 1px solid #229ec3'
		self.fields['home_comment'].widget.attrs['autocomplete'] = 'off'
		self.fields['home_comment'].widget.attrs['autocapitalize'] = 'off'
		self.fields['home_comment'].widget.attrs['spellcheck'] = 'false'

		self.fields['photo_comment'].widget.attrs['class'] = 'box-with-button-right cdo'
		self.fields['photo_comment'].widget.attrs['style'] = 'border: 1px solid #ff9933'
		self.fields['photo_comment'].widget.attrs['autocomplete'] = 'off'
		self.fields['photo_comment'].widget.attrs['autocapitalize'] = 'off'
		self.fields['photo_comment'].widget.attrs['spellcheck'] = 'false'

		self.fields['personal_group_reply'].widget.attrs['class'] = 'box-with-button-right'
		self.fields['personal_group_reply'].widget.attrs['style'] = 'color:#306654;border: 1px solid #306654'
		self.fields['personal_group_reply'].widget.attrs['autocomplete'] = 'off'
		self.fields['personal_group_reply'].widget.attrs['autocapitalize'] = 'off'
		self.fields['personal_group_reply'].widget.attrs['spellcheck'] = 'false'


	def clean(self):
		data, user_id = self.cleaned_data, self.user_id
		origin, secret_key_from_form = data.get("origin"), data.get("sk")
		if origin == '0':
			org = 'fresh_photos'
		elif origin == '1':
			org = 'home'
		elif origin == '2':
			org = 'best_photos'
		else:
			org = 'home'
		secret_key_from_session = get_and_delete_text_input_key(user_id,'1',org)
		if secret_key_from_form != secret_key_from_session:
			raise forms.ValidationError('tip: sirf aik dafa button dabain')
		else:
			link_id, photo_id, pub_grp_id, prv_grp_id, per_grp_id = self.link_id, self.photo_id, self.pub_grp_id, self.prv_grp_id, self.per_grp_id
			if link_id:
				section, payload, obj_id = 'home_rep', data.get("home_comment"), link_id
				payload = payload.strip() if payload else None
				if not payload:
					raise forms.ValidationError('tip: likhna zaruri hai')
				elif repetition_found(section=section,section_id=obj_id,user_id=user_id, target_text=payload):
					raise forms.ValidationError('tip: aik hi baat bar bar nah likhein')
				rate_limited, reason = is_limited(user_id,section=section,with_reason=True)
				if rate_limited > 0:
					raise forms.ValidationError('Ap jawab dene se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
				else:
					len_payload = len(payload)
					if len_payload < 6:
						if many_short_messages(user_id,section,obj_id):
							raise forms.ValidationError('tip: har thori deir baad yahan choti baat nah likhein')
						else:
							log_short_message(user_id,section,obj_id)
					elif len_payload > 250:
						raise forms.ValidationError('tip: inti barri baat nahi likh sakte')
					return data
			elif photo_id:
				section, payload, obj_id = 'pht_comm', data.get("photo_comment"), photo_id
				payload = payload.strip() if payload else None
				if not payload:
					raise forms.ValidationError('tip: likhna zaruri hai')
				elif repetition_found(section=section,section_id=obj_id,user_id=user_id, target_text=payload):
					raise forms.ValidationError('tip: aik hi baat bar bar nah likhein')
				rate_limited, reason = is_limited(user_id,section=section,with_reason=True)
				if rate_limited > 0:
					raise forms.ValidationError('Ap photo pe comment karney se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
				else:
					len_payload = len(payload)
					if len_payload < 6:
						if many_short_messages(user_id,section,obj_id):
							raise forms.ValidationError('tip: har thori deir baad yahan choti baat nah likhein')
						else:
							log_short_message(user_id,section,obj_id)
					elif len_payload > 250:
						raise forms.ValidationError('tip: inti barri baat nahi likh sakte')
					return data
			elif pub_grp_id:
				section, payload, obj_id= 'pub_grp', data.get("public_group_reply"), pub_grp_id
				payload = payload.strip() if payload else None
				if not payload:
					raise forms.ValidationError('tip: likhna zaruri hai')
				elif repetition_found(section=section,section_id=obj_id,user_id=user_id, target_text=payload):
					raise forms.ValidationError('tip: milti julti baatien nah likho, kuch new likho')
				rate_limited, reason = is_limited(user_id,section=section,with_reason=True)
				if rate_limited > 0:
					raise forms.ValidationError('Ap open mehfils mein likhne se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
				else:
					len_payload = len(payload)
					if len_payload < 6:
						if many_short_messages(user_id,section,obj_id):
							raise forms.ValidationError('tip: har thori deir baad yahan choti baat nah likhein')
						else:
							log_short_message(user_id,section,obj_id)
					elif len_payload > 500:
						raise forms.ValidationError('tip: inti barri baat nahi likh sakte')
					return data
			elif prv_grp_id:
				section, payload, obj_id = 'prv_grp', data.get("private_group_reply"), prv_grp_id
				payload = payload.strip() if payload else None
				if not payload:
					raise forms.ValidationError('tip: likhna zaruri hai')
				elif repetition_found(section=section,section_id=obj_id,user_id=user_id, target_text=payload):
					raise forms.ValidationError('tip: aik hi baat bar bar nah likhein')
				rate_limited, reason = is_limited(user_id,section='prv_grp',with_reason=True)
				if rate_limited > 0:
					raise forms.ValidationError('Ap private mehfils mein likhne se {0} tak banned ho. Reason: {1}'.format(human_readable_time(rate_limited),reason))
				else:
					len_payload = len(payload)
					if len_payload < 6:
						if many_short_messages(user_id,section,obj_id):
							raise forms.ValidationError('tip: har thori deir baad yahan choti baat nah likhein')
						else:
							log_short_message(user_id,section,obj_id)
					elif len_payload > 500:
						raise forms.ValidationError('tip: inti barri baat nahi likh sakte')
					return data
			elif per_grp_id:
				payload = data.get("personal_group_reply")
				payload = payload.strip() if payload else None
				if not payload:
					raise forms.ValidationError('tip: likhna zaruri hai')
				# No need to check for repetition, length or rate limit
				return data
			else:
				pass
			return data



class PhotoTimeForm(forms.Form):
	class Meta:
		pass

class ClosedGroupCreateForm(forms.ModelForm):
	class Meta:
		model = Group
		exclude = ("owner","created_at", "members", "cagtegory","private", "rules", "pics_ki_ijazat")
		fields = ("topic",)

	def __init__(self, *args, **kwargs):
		super(ClosedGroupCreateForm, self).__init__(*args, **kwargs)
		self.fields['topic'].widget.attrs['style'] = 'width:95%;'

class OpenGroupCreateForm(forms.ModelForm):
	PicNoPic = (
		('1','Haan'),
		('0','Nahi'),
		)
	pics_ki_ijazat = forms.TypedChoiceField(choices=PicNoPic, widget=forms.RadioSelect, coerce=int)
	class Meta:
		model = Group
		exclude = ("owner","created_at", "members", "cagtegory","private")
		fields = ("topic", "rules", "pics_ki_ijazat")

	def __init__(self, *args, **kwargs):
		self.is_mob_verified = kwargs.pop('verified',None)
		super(OpenGroupCreateForm, self).__init__(*args, **kwargs)
		self.fields['topic'].widget.attrs['style'] = 'width:95%;'
		self.fields['rules'].widget.attrs['style'] = 'width:95%;'

	def clean_topic(self):
		data, is_mob_verified = self.cleaned_data.get("topic"), self.is_mob_verified
		if not is_mob_verified:
			raise forms.ValidationError('Mobile number verify kiye beghair mehfil nahi ban sakti')
		return data


class ChangeOutsideGroupTopicForm(forms.ModelForm):
	topic = forms.CharField(label='Neya Topic:', widget=forms.Textarea(attrs={'cols':30,'rows':2,'style':'width:98%;'}))
	class Meta:
		model = Group
		fields = ("topic",)

class ChangePrivateGroupTopicForm(forms.ModelForm):
	topic = forms.CharField(label='New Topic:', widget=forms.Textarea(attrs={'cols':30,'rows':2,'style':'width:98%;'}))
	class Meta:
		model = Group
		fields = ("topic",)

	def clean_topic(self):
		topic = self.cleaned_data.get("topic")
		topic = topic.strip()
		# topic = clear_zalgo_text(topic)
		if not topic:
			raise forms.ValidationError('Topic rakhna zaruri hai')
		elif topic < 1:
			raise forms.ValidationError('Topic rakhna zaruri hai')
		return topic

class ChangeGroupTopicForm(forms.ModelForm):
	topic = forms.CharField(label='Neya Topic:', widget=forms.Textarea(attrs={'cols':30,'rows':2,'style':'width:98%;'}))
	class Meta:
		model = Group
		fields = ("topic",)

	def clean_topic(self):
		topic = self.cleaned_data.get("topic")
		topic = topic.strip()
		# topic = clear_zalgo_text(topic)
		if not topic:
			raise forms.ValidationError('Topic rakhna zaruri hai')
		elif topic < 1:
			raise forms.ValidationError('Topic rakhna zaruri hai')
		return topic


class UploadPhotoReplyForm(forms.ModelForm):
	image_file = forms.ImageField(error_messages={'required': 'Photo ka intekhab doobara karo'})
	caption = forms.CharField(widget=forms.Textarea(attrs={'cols':20,'rows':2,'style':'width:98%;'}), error_messages={'required': 'Photo ke bary mien likhna zaroori hai'})
	class Meta:
		model = Photo
		exclude = ("owner", "children", "child_count", "upload_time", "comment_count", "category", "device", "latest_comment", "second_latest_comment", "is_visible", "visible_score", "invisible_score",)
		fields = ("image_file", "caption",)

	def __init__(self, *args, **kwargs):
		super(UploadPhotoReplyForm, self).__init__(*args, **kwargs)
		self.fields['image_file'].widget.attrs['style'] = 'width:95%;'

class UploadPhotoForm(forms.ModelForm):
	image_file = forms.ImageField(label='Upload', error_messages={'required': 'Photo ka intekhab sahi nahi hua'})
	caption = forms.CharField(widget=forms.Textarea(attrs={'cols':20,'rows':2,'style':'width:98%;'}), error_messages={'required': 'Photo ke barey mien likhna zaroori hai'})
	class Meta:
		model = Photo
		exclude = ("owner", "children", "child_count", "upload_time", "comment_count", "category", "device", "latest_comment", "second_latest_comment", "is_visible", "visible_score", "invisible_score",)
		fields = ("image_file","caption",)

	def __init__(self, *args, **kwargs):
		super(UploadPhotoForm, self).__init__(*args, **kwargs)
		self.fields['caption'].widget.attrs['style'] = 'width:99%;height:50px;border-radius:10px;border: 1px #E0E0E0 solid; background-color:#FAFAFA;padding:5px;'
		self.fields['caption'].widget.attrs['id'] = 'pub_img_caption_field'
		self.fields['image_file'].widget.attrs['style'] = 'width:95%;'
		# self.fields["image_file"].widget.attrs['class'] = 'p'
		self.fields['image_file'].widget.attrs['id'] = 'browse_pub_img_btn'
		# self.fields['image_file'].widget.attrs['accept'] = 'image/*'

class UploadVideoForm(forms.Form):
	video_file = forms.FileField()
	caption = forms.CharField(widget=forms.Textarea(attrs={'cols':20,'rows':2,'style':'width:98%;'}), error_messages={'required': 'Video ke bary mien likhna zaroori hai'})
	class Meta:
		fields = ("video_file", "caption",)

class PicsChatUploadForm(forms.ModelForm):
	image = forms.ImageField(label='Upload')
	#image.widget.attrs["value"] ='Upload'
	#image.widget.attrs["type"] ='image'
	class Meta:
		model = ChatPic
		exclude = ("sender","sending_time", "sms_created", "expiry_interval")
		fields = ("image",)

	def __init__(self, *args, **kwargs):
		super(PicsChatUploadForm, self).__init__(*args, **kwargs)
		self.fields['image'].widget.attrs['style'] = 'width:95%;'
		# self.fields['image'].widget.attrs['accept'] = 'image/*'

class ChangeGroupRulesForm(forms.ModelForm):
	rules = forms.CharField(label='Neya Qanoon:', widget=forms.Textarea(attrs={'cols':40,'rows':3,'style':'width:98%;'}))
	class Meta:
		model = Group
		fields = ("rules",)

class PhotoReportForm(forms.Form):
	description = forms.CharField(widget=forms.Textarea(attrs=\
		{'style':'max-width:90%;background-color:#F8F8F8;border: 1px solid red;border-radius:5px;color: #404040;'}),\
		validators=[validators.RegexValidator(regex="^[A-Za-z0-9._~()'!*:@, ;+?-]*$")],error_messages={'invalid': _("(tip: sirf english harf, number ya @ _ . + - likh sakte ho)"),\
		'required':_("(tip: report ko khali nahi chore sakte)")})
	class Meta:
		fields = ("description",)

	def __init__(self, *args, **kwargs):
		super(PhotoReportForm, self).__init__(*args, **kwargs)
		self.fields['description'].widget.attrs['class'] = 'cxl'
		self.fields['description'].widget.attrs['autofocus'] = 'autofocus'

	def clean_description(self):
		description = self.cleaned_data.get("description")
		description = description.strip()
		if len(description) < 5:
			raise forms.ValidationError('(tip: itni choti report nahi likh sakte)')
		elif len(description) > 250:
			raise forms.ValidationError('(tip: inti barri report nahi likh sakte)')
		# description = clear_zalgo_text(description)
		return description

class HomeLinkListForm(forms.Form):
	reply = forms.CharField(max_length=250)

	class Meta:
		fields = ("reply",)

	def __init__(self, *args, **kwargs):
		super(HomeLinkListForm, self).__init__(*args, **kwargs)
		self.fields['reply'].widget.attrs['style'] = \
		'background-color:#F8F8F8;width:1400px;max-width:90%;border: 1px solid #1f8cad;border-radius:5px;padding: 6px 6px 6px 0;text-indent: 6px;color: #1f8cad;'

class BestPhotosListForm(forms.Form):
	class Meta:
		pass

class PhotosListForm(forms.Form):
	class Meta:
		pass

class FacesPagesForm(forms.Form):
	class Meta:
		pass

class CrossNotifForm(forms.Form):
	class Meta:
		pass
		#model = Link

class PhotoShareForm(forms.Form):
	class Meta:
		pass

class InternalSalatInviteForm(forms.Form):
	class Meta:
		pass

class ExternalSalatInviteForm(forms.Form):
	class Meta:
		pass

class PhotoReplyForm(forms.Form):
	class Meta:
		pass

class PhotoJawabForm(forms.Form):
	class Meta:
		pass

class PicPasswordForm(forms.Form):
	mobile_number = forms.CharField(max_length=50)
	class meta:
		fields = ("mobile_number",)

	def __init__(self, *args, **kwargs):
		super(PicPasswordForm, self).__init__(*args, **kwargs)
		self.fields['mobile_number'].widget.attrs['style'] = 'width:95%;'

class SalatTutorialForm(forms.Form):
	class Meta:
		pass

class DirectMessageForm(forms.Form):
	class Meta:
		pass

class SalatInviteForm(forms.Form):
	class Meta:
		pass

class ChainPhotoTutorialForm(forms.Form):
	class Meta:
		pass

class VideoScoreForm(forms.Form):
	class Meta:
		pass

class PhotoScoreForm(forms.Form):
	class Meta:
		pass

class BaqiPhotosHelpForm(forms.Form):
	class Meta:
		pass

class PhotoQataarHelpForm(forms.Form):
	class Meta:
		pass

class ContactForm(forms.Form):
	class Meta:
		pass

class AboutForm(forms.Form):
	class Meta:
		pass

class PrivacyPolicyForm(forms.Form):
	class Meta:
		pass

class PhotoHelpForm(forms.Form):
	class Meta:
		pass

class DeletePicForm(forms.Form):
	class Meta:
		pass

class PicHelpForm(forms.Form):
	class Meta:
		pass

class DirectMessageCreateForm(forms.Form):
	class Meta:
		model = Group

class PicExpiryForm(forms.Form):
	class Meta:
		pass

class InvitePrivateForm(forms.Form):
	class Meta:
		model = Session

class InviteForm(forms.Form): # doesn't work if one uses Model form
	class Meta:
		model = Session

class VerifiedForm(forms.Form):
	class Meta:
		model = User

class TopPhotoForm(forms.Form):
	class Meta:
		model = User

class TopForm(forms.Form):
	class Meta:
		model = User

class OwnerGroupOnlineKonForm(forms.ModelForm):
	class Meta:
		model = GroupTraffic

class GroupOnlineKonForm(forms.ModelForm):
	class Meta:
		model = GroupTraffic

class DeviceHelpForm(forms.Form):
	class Meta:
		pass

class ReportcommentForm(forms.Form):
	class Meta:
		pass

class MehfilCommentForm(forms.Form):
	class Meta:
		pass

class WelcomeForm(forms.Form):
	class Meta:
		pass

class GroupPageForm(forms.Form):
	class Meta:
		model = Reply

class AppointCaptainForm(forms.Form): #doesn't work as forms.ModelForm
	class Meta:
		pass

class GroupListForm(forms.Form):
	class Meta:
		pass

class OpenGroupHelpForm(forms.Form):
	class Meta:
		pass

class ClosedGroupHelpForm(forms.Form):
	class Meta:
		pass

class GroupTypeForm(forms.Form):
	class Meta:
		pass

class DownvoteForm(forms.Form):
	class Meta:
		pass

class UpvoteForm(forms.Form):
	class Meta:
		pass

class LogoutHelpForm(forms.Form):
	class Meta:
		pass

class FacesHelpForm(forms.Form):
	class Meta:
		pass

class EmoticonsHelpForm(forms.Form):
	class Meta:
		pass

class ReportreplyForm(forms.Form):
	class Meta:
		pass

class LogoutReconfirmForm(forms.Form):
	class Meta:
		pass

class LogoutPenaltyForm(forms.Form):
	class Meta:
		pass

class ReinvitePrivateForm(forms.Form):
	class Meta:
		pass

class ReportNicknameForm(forms.Form):
	class Meta:
		pass

class SpecialPhotoTutorialForm(forms.Form):
	class Meta:
		pass

class ReinviteForm(forms.Form):
	class Meta:
		pass

# class KickForm(forms.Form):
# 	class Meta:
# 		pass

class MehfilForm(forms.Form):
	class Meta:
		pass

# class GroupReportForm(forms.Form):
# 	class Meta:
# 		model = Reply

class MehfildecisionForm(forms.Form):
	class Meta:
		pass

class ReportForm(forms.Form):
	class Meta:
		model = Publicreply

class ScoreHelpForm(forms.Form):
	class Meta:
		pass

class RegisterLoginForm(forms.Form):
	class Meta:
		pass

class ReauthForm(forms.Form):
	password = forms.CharField(widget=forms.TextInput(attrs={'placeholder':''}))
	class Meta:
		fields = ("password",)

	def __init__(self,*args,**kwargs):
		self.request = kwargs.pop('request',None)
		super(ReauthForm, self).__init__(*args,**kwargs)
		self.fields['password'].widget.attrs['style'] = 'max-width:95%;'

	def clean_password(self):
		entered_password = self.cleaned_data["password"]
		real_password = self.request.user.password
		if check_password(password=entered_password,encoded=real_password):
			return entered_password
		else:
			raise forms.ValidationError('Password theek nahi, phir se likho')


class ResetPasswordForm(forms.Form):
	password = forms.CharField(widget=forms.PasswordInput)
	class Meta:
		fields = ('password',)

	def __init__(self,*args,**kwargs):
		self.request = kwargs.pop('request',None)
		super(ResetPasswordForm, self).__init__(*args,**kwargs)
		self.fields['password'].widget.attrs['style'] = 'max-width:95%;'

	def clean_password(self):
		password = self.cleaned_data["password"]
		password = password.strip()
		old_password = self.request.user.password
		lower_pass = password.lower()
		nickname = self.request.user.username
		lower_nick = nickname.lower()
		if check_password(password,old_password):
			raise ValidationError('New password purane password se mukhtalif rakhein')
		if len(password) < 6:
			raise ValidationError('Kam se kam 6 harf likhna zaruri hain!')
		elif lower_pass in '1234567890':
			raise ValidationError('"%s" ko boojhna aasan hai, kuch aur likhein'  % lower_pass)
		elif lower_pass == lower_pass[0]*len(lower_pass): #checks if it's a string made of a single character
			raise ValidationError('"%s" ko boojhna aasan hai, kuch aur likhein'  % lower_pass)
		elif lower_nick in lower_pass:
			raise ValidationError('"%s" nahi likh sakte kiyunke nickname mein hai' % nickname)
		elif 'damadam' in lower_pass:
			raise ValidationError('"damadam" ko boojhna aasan hai, kuch aur likhein')
		elif 'qwerty' in lower_pass:
			raise ValidationError('"qwerty" ko boojhna aasan hai, kuch aur likhein')
		return password


	def save(self, commit=True):
		user = self.request.user
		password = self.cleaned_data["password"]
		user.set_password(password)
		if commit:
			user.save()
		return user

class LoginWalkthroughForm(forms.Form):
	class Meta:
		pass

class VoteOrProfForm(forms.Form):
	class Meta:
		pass

class SmsReinviteForm(forms.Form):
	class Meta:
		pass

class SmsInviteForm(forms.Form):
	class Meta:
		pass

class HistoryHelpForm(forms.Form):
	class Meta:
		pass

class WhoseOnlineForm(forms.Form):
	class Meta:
		pass

class GroupHelpForm(forms.Form):
	class Meta:
		pass

class HelpForm(forms.Form):
	class Meta:
		pass

class RegisterHelpForm(forms.Form):
	class Meta:
		pass

class VerifyHelpForm(forms.Form):
	class Meta:
		pass

class SearchAdFeedbackForm(forms.Form):
	ad_campaign = forms.CharField(max_length=100)

	def __init__(self, *args, **kwargs):
		super(SearchAdFeedbackForm, self).__init__(*args, **kwargs)
		self.fields['ad_campaign'].widget.attrs['style'] = \
		'max-width:90%;width:500px;background-color:#F8F8F8;border: 1px solid #179b36;border-radius:5px;padding: 6px 6px 6px 0;text-indent: 6px;color: #179b36;'
		self.fields['ad_campaign'].widget.attrs['class'] = 'cxl'
		self.fields['ad_campaign'].widget.attrs['autofocus'] = 'autofocus'

	def clean_ad_campaign(self):
		ad_campaign = self.cleaned_data.get("ad_campaign")
		ad_campaign = ad_campaign.strip()
		if len(ad_campaign) > 100:
			raise forms.ValidationError('tip: inta bara name nahi likh sakte')
		ad_campaign = clear_zalgo_text(ad_campaign)
		return ad_campaign

class AdFeedbackForm(forms.Form):
	feedback = forms.CharField(widget=forms.Textarea(attrs=\
		{'cols':40,'rows':3,'style':'max-width:90%;background-color:#F8F8F8;border: 1px solid green;border-radius:5px;color: #404040;'}),\
		validators=[validators.RegexValidator(regex="^[A-Za-z0-9._~()'!*:@, ;+?-]*$")],error_messages={'invalid': _("(tip: sirf english harf, number ya @ _ . + - likh sakte ho)"),\
		'required':_("(tip: isko khali nahi chore sakte)")})
	class Meta:
		fields = ("feedback",)

	def __init__(self, *args, **kwargs):
		super(AdFeedbackForm, self).__init__(*args, **kwargs)
		self.fields['feedback'].widget.attrs['class'] = 'cxl'
		self.fields['feedback'].widget.attrs['autocomplete'] = 'off'

	def clean_feedback(self):
		feedback = self.cleaned_data.get("feedback")
		feedback = feedback.strip()
		if len(feedback) < 5:
			raise forms.ValidationError('(tip: is se ziyada likho)')
		elif len(feedback) > 250:
			raise forms.ValidationError('(tip: buhut ziyada likh diya hai. Chota karo)')
		feedback = clear_zalgo_text(feedback)
		return feedback
