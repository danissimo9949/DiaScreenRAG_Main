from django.urls import path
from .views import (
    render_chat_ai,
    send_message,
    get_session_messages,
    create_session,
    get_sessions,
    delete_session
)

urlpatterns = [
    path('', render_chat_ai, name='chat'),
    path('api/send-message/', send_message, name='send_message'),
    path('api/sessions/<int:session_id>/messages/', get_session_messages, name='get_messages'),
    path('api/create-session/', create_session, name='create_session'),
    path('api/sessions/', get_sessions, name='get_sessions'),
    path('api/sessions/<int:session_id>/delete/', delete_session, name='delete_session'),
]
