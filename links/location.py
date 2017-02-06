#Contains locations of memcached/redis in various OSes.
import os
ON_MAC = os.environ.get('ON_MAC')

if ON_MAC == '1':
	MEMLOC = 'unix:/usr/local/var/run/memcached/memcached.sock'
	REDLOC1 = '/usr/local/var/run/redis/redis.sock'
	REDLOC2 = '/usr/local/var/run/redis/redis2.sock' 
else:
	MEMLOC = 'unix:/var/run/memcached/memcached.sock'
	REDLOC1 = '/var/run/redis/redis.sock'
	REDLOC2 = '/var/run/redis/redis2.sock' 