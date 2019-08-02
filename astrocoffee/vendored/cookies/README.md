This directory contains the Python `http.cookies` module from the master branch
at:

https://github.com/python/cpython/blob/master/Lib/http/cookies.py

The purpose of vendoring this module is to use the samesite cookie attribute in
our tornado BaseHandler. This attribute isn't supported yet, but will be
supported in Python 3.8. A permalink to the actual change in the file is below:

https://github.com/python/cpython/blob/b2984ab9a7c458f8b7ed8978c0c95b109116895d/Lib/http/cookies.py#L283

Prompted by this article:

https://blog.twitter.com/engineering/en_us/topics/insights/2018/twitter_silhouette.html
