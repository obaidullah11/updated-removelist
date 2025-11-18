"""
Admin configuration for task management.
"""
from django.contrib import admin
from .models import Task, TaskTimer, TaskTemplate


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'move', 'category', 'location', 'priority', 'completed', 'assigned_to', 'created_at']
    list_filter = ['category', 'location', 'priority', 'completed', 'is_external']
    search_fields = ['title', 'description', 'move__user__email']
    readonly_fields = ['id', 'time_spent', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(TaskTimer)
class TaskTimerAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'start_time', 'end_time', 'duration', 'created_at']
    list_filter = ['start_time', 'end_time']
    search_fields = ['task__title', 'user__email']
    readonly_fields = ['id', 'duration', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'location', 'priority', 'is_external', 'is_active']
    list_filter = ['category', 'location', 'priority', 'is_external', 'is_active']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['category', 'priority', 'title']

