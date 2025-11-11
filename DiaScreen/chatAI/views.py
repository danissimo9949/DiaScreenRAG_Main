from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings
import json
import requests

from .models import AISession, AIMessage
from support.forms import SupportTicketForm


@login_required
def render_chat_ai(request):
    sessions = AISession.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-updated_at')[:20]

    initial_session_id = sessions[0].session_id if sessions else None

    context = {
        'sessions': sessions,
        'support_ticket_form': SupportTicketForm(
            initial={'page_context': 'chat'}
        ),
        'initial_session_id': initial_session_id,
    }
    return render(request, 'chatAI/chat.html', context)


@login_required
@require_http_methods(["GET"])
def get_session_messages(request, session_id):
    """Получить все сообщения конкретной сессии"""
    try:
        session = AISession.objects.get(pk=session_id, user=request.user)
        messages = session.messages.all().order_by('created_at')
        
        messages_data = [
            {
                'message_id': msg.message_id,
                'sender': msg.sender,
                'message_text': msg.message_text,
                'created_at': msg.created_at.strftime('%H:%M'),
                'status': msg.status,
            }
            for msg in messages
        ]
        
        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'session': {
                'session_id': session.session_id,
                'summary': session.summary or 'Новий діалог',
                'created_at': session.created_at.strftime('%d.%m.%Y %H:%M'),
            }
        })
    except AISession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Сесію не знайдено'}, status=404)


@login_required
@require_http_methods(["POST"])
def send_message(request):
    """Отправить сообщение от пользователя"""
    try:
        data = json.loads(request.body)
        message_text = data.get('message', '').strip()
        session_id = data.get('session_id', None)
        
        if not message_text:
            return JsonResponse({'success': False, 'error': 'Повідомлення не може бути порожнім'}, status=400)
        
        if session_id:
            try:
                session = AISession.objects.get(pk=session_id, user=request.user)
            except AISession.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Сесію не знайдено'}, status=404)
        else:
            session = AISession.objects.create(
                user=request.user,
                summary=message_text[:200]
            )
        
        default_summaries = {'новий діалог', 'новий чат', 'new chat', 'new dialog'}
        current_summary = (session.summary or '').strip()
        if not current_summary or current_summary.lower() in default_summaries:
            session.summary = message_text[:200]
            session.save(update_fields=['summary'])

        user_message = AIMessage.objects.create(
            session=session,
            sender='user',
            message_text=message_text,
            status='completed'
        )
        
        ai_message = AIMessage.objects.create(
            session=session,
            sender='assistant',
            message_text='',
            status='pending'
        )

        rag_url = getattr(settings, 'RAG_API_URL', 'http://127.0.0.1:8001/get-response')

        try:
            response = requests.get(
                rag_url,
                params={'question': message_text},
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            answer_text = (data.get('answer') or '').strip()
            sources = data.get('sources') or []
            metadata = data.get('metadata') or {}

            if not answer_text:
                answer_text = 'Вибачте, сервіс не надав відповіді.'

            ai_message.message_text = answer_text
            ai_message.status = 'completed'
            ai_message.sources = sources
            ai_message.metadata = metadata
            ai_message.response_time_ms = metadata.get('response_time_ms')
            ai_message.save(update_fields=['message_text', 'status', 'sources', 'metadata', 'response_time_ms'])
        except (requests.RequestException, ValueError) as exc:
            ai_message.message_text = 'Вибачте, зараз я не можу відповісти. Спробуйте трохи пізніше.'
            ai_message.status = 'error'
            ai_message.error_message = str(exc)
            ai_message.save(update_fields=['message_text', 'status', 'error_message'])

        ai_message.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'session_id': session.session_id,
            'user_message': {
                'message_id': user_message.message_id,
                'sender': 'user',
                'message_text': user_message.message_text,
                'created_at': user_message.created_at.strftime('%H:%M'),
            },
            'assistant_message': {
                'message_id': ai_message.message_id,
                'sender': 'assistant',
                'message_text': ai_message.message_text,
                'created_at': ai_message.created_at.strftime('%H:%M'),
                'status': ai_message.status,
                'error_message': ai_message.error_message or '',
            },
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def create_session(request):
    """Создать новую сессию"""
    try:
        raw_body = request.body.decode('utf-8').strip()
        try:
            data = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            data = {}
        summary = data.get('summary') or 'Новий діалог'
    
        session = AISession.objects.create(
            user=request.user,
            summary=summary
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.session_id,
            'created_at': session.created_at.strftime('%d.%m.%Y %H:%M')
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_sessions(request):
    """Получить список всех сессий пользователя"""
    sessions = AISession.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-updated_at')[:20]
    
    sessions_data = [
        {
            'session_id': session.session_id,
            'summary': session.summary or 'Новий діалог',
            'created_at': session.created_at.strftime('%d.%m.%Y %H:%M'),
            'updated_at': session.updated_at.strftime('%d.%m.%Y %H:%M'),
            'message_count': session.get_message_count(),
        }
        for session in sessions
    ]
    
    return JsonResponse({
        'success': True,
        'sessions': sessions_data
    })


@login_required
@require_http_methods(["DELETE", "POST"])
def delete_session(request, session_id):
    """Удалить сессию (пометить как неактивную)"""
    try:
        session = AISession.objects.get(pk=session_id, user=request.user)
        
        # Помечаем сессию как неактивную вместо физического удаления
        session.is_active = False
        session.save(update_fields=['is_active'])
        
        return JsonResponse({
            'success': True,
            'message': 'Сесію успішно видалено'
        })
    except AISession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Сесію не знайдено'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
