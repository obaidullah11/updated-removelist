"""
URL patterns for move management endpoints.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_move, name='create_move'),
    path('get/<uuid:move_id>/', views.get_move, name='get_move'),
    path('user-moves/', views.user_moves, name='user_moves'),
    path('update/<uuid:move_id>/', views.update_move, name='update_move'),
    path('delete/<uuid:move_id>/', views.delete_move, name='delete_move'),
    
    # Collaborator management
    path('collaborators/invite/', views.invite_collaborator, name='invite_collaborator'),
    path('collaborators/accept/', views.accept_invitation, name='accept_invitation'),
    path('collaborators/invitation/<str:invitation_token>/', views.get_invitation_details, name='get_invitation_details'),
    path('collaborators/my-moves/', views.get_collaborator_moves, name='get_collaborator_moves'),
    path('collaborators/<uuid:move_id>/', views.get_collaborators, name='get_collaborators'),
    path('collaborators/remove/<uuid:collaborator_id>/', views.remove_collaborator, name='remove_collaborator'),
    
    # Task assignments
    path('tasks/assign/', views.assign_task, name='assign_task'),
    path('tasks/assignments/<uuid:move_id>/', views.get_task_assignments, name='get_task_assignments'),
    
    # AI-powered moving checklist generation
    path('generate-checklist/<uuid:move_id>/', views.generate_moving_checklist, name='generate_moving_checklist'),
    path('convert-checklist-to-tasks/<uuid:move_id>/', views.convert_checklist_to_tasks, name='convert_checklist_to_tasks'),

    # Expense management
    path('expenses/<uuid:move_id>/', views.get_move_expenses, name='get_move_expenses'),
    path('expenses/create/', views.create_move_expense, name='create_move_expense'),
    path('expenses/<uuid:expense_id>/update/', views.update_move_expense, name='update_move_expense'),
    path('expenses/<uuid:expense_id>/delete/', views.delete_move_expense, name='delete_move_expense'),
]
