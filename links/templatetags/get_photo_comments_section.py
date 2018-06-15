from django import template
from links.redis1 import get_raw_comments

register = template.Library()

@register.inclusion_tag(file_name='photo_comments_section.html')
def photo_comments_section(raw_comments, static_url, self_user_id, origin=None, score=None):
	# if originates from home ('3'), raw_comments contains photo_id in that case
	if origin == '3':
		raw_comments = get_raw_comments(raw_comments)
	if raw_comments:
		comments = []
		raw_comment_set = filter(None,raw_comments.split('#el#'))
		counter = 0
		for raw_comment in reversed(raw_comment_set):
			if raw_comment[0] != '#':# exception handling
				components = raw_comment.split("#",5)
				comment = {}
				comment["writer_av_url"], comment["writer_uname"], comment["epoch_time"], comment["commenter_id"], comment["photo_id"],comment["text"] = \
				components[0], components[1], float(components[2]), components[3], components[4], components[5]
				comments.append(comment)
			counter += 1
			if counter > 5:
				# this ensure only 6 comments can show up on the photo page (at max)
				break
		return {'comments':comments, 'static_url':static_url,'self_user_id':self_user_id,'score':score,'origin':origin}