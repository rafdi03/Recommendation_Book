from django.contrib import admin
from django.urls import path
from book_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.input_page, name='input_page'),
]
