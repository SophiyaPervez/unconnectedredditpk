from twilio.rest import Client
from unconnectedreddit.twilio_settings import ACCNT_SID, AT, SERV_SID
from datetime import datetime

client = Client(ACCNT_SID, AT)
service = client.notify.services(SERV_SID) # using twilio 6.4.3a 'alpha' library. This is experimental, and must be updated by September 2017 at least.


def process_sms(target_number,ad_id,status=None, buyer_number=None, item_name=None):
	if status == 'unique_click_plus_expiry':
		body = "Damadam pe apke ad se {0} ne apka mobile number lia. Ab apka ad khatam ho gaya hai. Damadam pe apna ad dubara laga lein".format(buyer_number)
	elif status == 'unique_click':
		body = "Damadam pe apke ad se {0} ne apka mobile number lia. Doston ko apna ad dikhaney ke liye ye link dein: https://damadam.pk/ad/{1}/".format(buyer_number,ad_id)
	elif status == 'approved':
		body = "Apka ad Damadam pe lag gaya. Hum ne apko aik aur SMS bheji hai. Isko apney all friends ko forward kar dein. Us SMS mein apke ad ki tafseel hai"#Doston ko ye link de ke ad dikhain: https://damadam.pk/ad/{0}/".format(ad_id)
	elif status == 'forward' and item_name:
		body = "Mein {0} baich raha hoon. Aap ne ya apke dost ne kharidna hai? Tafseel yahan hai http://damadam.pk/ad/{1}/".format(item_name, ad_id)
	message = client.messages.create(to=target_number, from_="+18328955063",body=body)
	

def process_buyer_sms(target_number,order_id,order_data, buyer_number=None):
	if order_data and order_id:
		body = order_data
	message = client.messages.create(to=target_number, from_="+18328955063",body=body)



def send_personal_group_sms(mobile_number, sms_text):
	"""
	Send SMS to personal group user, inviting them online
	"""
	message = client.messages.create(to=mobile_number, from_="+18328955063",body=sms_text)


# def process_bulk_sms(target_number_list, ad_ids=None, status=None, buyer_number_list=None):
# 	for target_number in target_number_list:
# 		body = "Damadam pe apka muft ad khatam ho gaya hai. Neya ad laganey ke liye yahan ao: https://damadam.pk/kuch_baicho/"
# 		message = client.messages.create(to=target_number, from_="+18328955063",body=body)



def bind_user_to_twilio_notify_service(user_id,phone_number):
	"""
	Twilio bindings are helpful in sending bulk SMSes
	"""
	binding = service.bindings.create(
		identity=user_id,
		binding_type='sms',
		address=phone_number,
	)

def send_expiry_sms_in_bulk(user_ids):
	service.notifications.create(identity=user_ids,
                             body="Damadam pe apka muft ad khatam ho gaya hai. Neya ad laganey ke liye yahan ao: https://damadam.pk/kuch_baicho/")


# def get_all_bindings_to_date():
# 	bindings = service.bindings .list(
# 	        tag="sms",
# 	        start_date=datetime.strptime("2017-01-30", "%Y-%m-%d")
# 	    )
# 	for binding in bindings:
# 	    print(binding.sid)