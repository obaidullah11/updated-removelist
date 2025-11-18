"""
URL patterns for task management endpoints.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Task endpoints
    path('', views.get_tasks, name='get_tasks'),
    path('create/', views.create_task, name='create_task'),
    path('<uuid:task_id>/', views.get_task, name='get_task'),
    path('<uuid:task_id>/update/', views.update_task, name='update_task'),
    path('<uuid:task_id>/delete/', views.delete_task, name='delete_task'),
    path('from-template/', views.create_task_from_template, name='create_task_from_template'),
    
    # Task timer endpoints
    path('timers/', views.get_task_timers, name='get_task_timers'),
    path('timers/start/', views.start_task_timer, name='start_task_timer'),
    path('timers/<uuid:timer_id>/stop/', views.stop_task_timer, name='stop_task_timer'),
    path('timers/active/', views.get_active_timer, name='get_active_timer'),
    
    # Task template endpoints
    path('templates/', views.get_task_templates, name='get_task_templates'),
    path('templates/<uuid:template_id>/', views.get_task_template, name='get_task_template'),
]

