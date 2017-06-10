# coding=utf-8
import redis, time, random
from location import REDLOC4

'''
##########Redis Namespace##########

"historical_calcs"
latest_user_ip = "lip:"+str(user_id)
logged_users = "logged_users"
sorted_set = "online_users"
user_ban = "ub:"+str(user_id)
user_times = "user_times:"+str(user_id)

###########
'''

POOL = redis.ConnectionPool(connection_class=redis.UnixDomainSocketConnection, path=REDLOC4, db=0)

TEN_MINS = 10*60
FIVE_MINS = 5*60

#######################Test Function######################

# def set_test_payload(payload_list):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	try:
# 		return my_server.lpush("my_test",payload_list)
# 	except:
# 		return None

#####################Retention Logger#####################
def log_retention(server_instance, user_id):
	time_now = time.time()
	if server_instance.exists("user_times:"+user_id):
		if time_now - float(server_instance.lrange("user_times:"+user_id,0,0)[0]) > TEN_MINS:
			server_instance.lpush("user_times:"+user_id,time_now)
			server_instance.sadd("logged_users",user_id)
	else:
		# contains a user's times of browsing Damadam
		server_instance.lpush("user_times:"+user_id,time_now)
		# contains all user_ids that have ever been logged
		server_instance.sadd("logged_users",user_id)

def retrieve_retention_ids():
	my_server = redis.Redis(connection_pool=POOL)
	return my_server.smembers("logged_users")

def retrieve_retention_data(user_ids):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	for id_ in user_ids:
		pipeline1.lrange("user_times:"+id_,0,-1)
	result1 = pipeline1.execute()
	user_times = []
	counter = 0
	for id_ in user_ids:
		user_times.append((id_,result1[counter]))
		counter += 1
	return user_times

# def reduce_retention_data():
	"""
	to delete, get ids of really old "last_active"
	dates from session table in DB (to ensure it's 
	an old user). Then delete those "user_times"+str(user_id)
	"""

#######################Whose Online#######################

#expires online_users from tasks.py
def expire_online_users():
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "online_users"
	my_server.zremrangebyscore(sorted_set,'-inf','('+str(time.time()-TEN_MINS))

#invoked from WhoseOnline.py middleware
def set_online_users(user_id,user_ip):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "online_users"
	user_id = str(user_id)
	latest_user_ip = "lip:"+user_id #latest ip of user with 'user_id'
	my_server.zadd(sorted_set,user_id+":"+str(user_ip),time.time())
	my_server.set(latest_user_ip,user_ip)
	my_server.expire(latest_user_ip,FIVE_MINS)
	############ logging user retention ############
	# if random.random() < 0.45:
	# 	log_retention(my_server,user_id)

# invoked by tasks.py to show whoever is online in OnlineKon
def get_recent_online():
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "online_users"
	ten_mins_ago = time.time() - TEN_MINS
	online_users = my_server.zrangebyscore(sorted_set,ten_mins_ago,'+inf')
	online_ids = []
	for user in online_users:
		online_ids.append(user.split(":",1)[0])
	return online_ids

# invoked in views.py to show possible clones of users
def get_clones(user_id):
	my_server = redis.Redis(connection_pool=POOL)
	sorted_set = "online_users"
	latest_user_ip = "lip:"+str(user_id) #latest ip of user with 'user_id'
	user_ip = my_server.get(latest_user_ip)
	if user_ip:
		clones = []
		five_mins_ago = time.time() - FIVE_MINS
		online_users = my_server.zrangebyscore(sorted_set,five_mins_ago,'+inf')
		for user in online_users:
			if user_ip == user.split(":",1)[1]:
				clones.append(user.split(":",1)[0])
		return clones
	else:
		return None

# def set_site_ban(user_id):
# 	my_server = redis.Redis(connection_pool=POOL)
# 	user_ban = "ub:"+str(user_id) # banning user's ip from logging into website
# 	my_server.set(user_ban,1)
# 	my_server.expire(user_ban,ONE_HOUR)

#########################################################

#calculating installment amount for mobile devices
def get_historical_calcs(base_price=None, time_period_in_months=None, monthly_installment=None, ending_value=None):
	my_server = redis.Redis(connection_pool=POOL)
	pipeline1 = my_server.pipeline()
	if base_price is None:
		id_ = my_server.get("historical_calcs")
		if id_ is not None:
			for x in range(1,(int(id_)+1)):
				pipeline1.hgetall("cd:"+str(x))
			return pipeline1.execute()
		else:
			return None
	else:
		id_ = my_server.incr("historical_calcs")
		calc_details = "cd:"+str(id_)
		mapping = {'id':id_,'bp':base_price,'tpim':time_period_in_months,'mi':monthly_installment,'ev':ending_value, 't':time.time()}
		my_server.hmset(calc_details,mapping)
		for x in range(1,(id_+1)):
			pipeline1.hgetall("cd:"+str(x))
		return pipeline1.execute()
