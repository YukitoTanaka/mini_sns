from django.contrib import admin
from django.urls import path,include
# import hello.views as hello
# helloのことはhelloのurlsでやってね！

urlpatterns = [
    path('admin/', admin.site.urls),
    path('hello/', include('hello.urls')),
    path('mini_sns/',include('mini_sns.urls')),
]
