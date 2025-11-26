from datetime import datetime
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import json
import requests

from .utils import call_rag_api_with_retry

logger = logging.getLogger(__name__)

MAX_PERSONAL_CONTEXT_LENGTH = getattr(settings, 'MAX_PERSONAL_CONTEXT_LENGTH', 2000)

from card.models import (
    GlucoseMeasurement,
    InsulineDoseMeasurement,
    GlycemicProfileMeasurement,
    PhysicalActivityMeasurement,
    FoodMeasurement,
    AnthropometricMeasurement,
)
from support.forms import SupportTicketForm

from .models import AISession, AIMessage


def build_personal_context(user):
    patient = getattr(user, 'profile', None)
    if patient is None:
        return "Пацієнт ще не створив профіль. Персональні дані недоступні."

    parts = []
    full_name = user.get_full_name() or user.username
    parts.append(f"Пацієнт: {full_name}")

    if patient.age is not None:
        parts.append(f"Вік: {patient.age} років")
    if patient.sex:
        parts.append(f"Стать: {'Чоловік' if patient.sex == 'male' else 'Жінка'}")
    if patient.diabetes_type:
        parts.append(f"Тип діабету: {patient.get_diabetes_type_display()}")
    if patient.target_glucose_min is not None and patient.target_glucose_max is not None:
        parts.append(
            f"Цільовий діапазон глюкози: {float(patient.target_glucose_min):.1f} – {float(patient.target_glucose_max):.1f} ммоль/л"
        )
    if patient.height:
        parts.append(f"Зріст: {patient.height} м")
    if patient.weight:
        parts.append(f"Вага: {patient.weight} кг")
    if patient.bmi:
        parts.append(f"ІМТ: {patient.bmi:.1f}")

    latest_glucose = (
        GlucoseMeasurement.objects.filter(patient=patient)
        .order_by('-date_of_measurement', '-time_of_measurement')
        .first()
    )
    latest_insuline = (
        InsulineDoseMeasurement.objects.filter(patient=patient)
        .order_by('-date_of_measurement', '-time')
        .first()
    )
    latest_glycemic = (
        GlycemicProfileMeasurement.objects.filter(patient=patient)
        .order_by('-measurement_date', '-measurement_time')
        .first()
    )
    latest_activity = (
        PhysicalActivityMeasurement.objects.filter(patient=patient)
        .order_by('-date_of_measurement', '-time_of_activity')
        .first()
    )
    latest_food = (
        FoodMeasurement.objects.filter(patient=patient)
        .order_by('-date_of_measurement', '-time_of_eating')
        .first()
    )
    latest_anthropometry = (
        AnthropometricMeasurement.objects.filter(patient=patient)
        .order_by('-measurement_date', '-measurement_time')
        .first()
    )

    def format_datetime(date_obj, time_obj):
        if date_obj and time_obj:
            return f"{date_obj.strftime('%d.%m.%Y')} {time_obj.strftime('%H:%M')}"
        if date_obj:
            return date_obj.strftime('%d.%m.%Y')
        return ''

    if latest_glucose:
        parts.append(
            f"Останній замір глюкози: {latest_glucose.glucose} ммоль/л ({format_datetime(latest_glucose.date_of_measurement, latest_glucose.time_of_measurement)})"
        )
    if latest_insuline:
        parts.append(
            f"Остання інʼєкція інсуліну: {latest_insuline.insuline_dose} ОД, категорія {latest_insuline.category} ({format_datetime(latest_insuline.date_of_measurement, latest_insuline.time)})"
        )
    if latest_glycemic:
        parts.append(
            f"Останній глікемічний профіль: середня глюкоза {latest_glycemic.average_glucose} ммоль/л, HbA1c {latest_glycemic.hba1c}% ({format_datetime(latest_glycemic.measurement_date, latest_glycemic.measurement_time)})"
        )
    if latest_activity:
        parts.append(
            f"Остання активність: {latest_activity.type_of_activity.name} ({format_datetime(latest_activity.date_of_measurement, latest_activity.time_of_activity)})"
        )
    if latest_food:
        parts.append(
            f"Останній прийом їжі: {latest_food.category} ({format_datetime(latest_food.date_of_measurement, latest_food.time_of_eating)})"
        )
    if latest_anthropometry:
        parts.append(
            f"Остання антропометрія: вага {latest_anthropometry.weight} кг, ІМТ {latest_anthropometry.bmi} ({format_datetime(latest_anthropometry.measurement_date, latest_anthropometry.measurement_time)})"
        )

    if not parts:
        return "Персональні дані пацієнта не заповнені."
    
    context = "\n".join(parts)
    
    if len(context) > MAX_PERSONAL_CONTEXT_LENGTH:
        logger.warning(
            f"Personal context for user {user.id} exceeded limit "
            f"({len(context)} > {MAX_PERSONAL_CONTEXT_LENGTH} chars). Truncating."
        )
        lines = context.split('\n')
        truncated_lines = []
        current_length = 0
        
        for line in reversed(lines):
            line_length = len(line) + 1
            if current_length + line_length > MAX_PERSONAL_CONTEXT_LENGTH:
                break
            truncated_lines.insert(0, line)
            current_length += line_length
        
        context = "\n".join(truncated_lines)
        if len(context) < 50:
            context = "\n".join(lines[:5])
            logger.warning(f"Context too short after truncation, using first 5 lines")
    
    return context


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
                'personal_context_used': bool((msg.metadata or {}).get('personal_context_used')),
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
        use_personal_context = bool(data.get('use_personal_context'))
        
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
        user_message.metadata = {'personal_context_used': use_personal_context}
        user_message.save(update_fields=['metadata'])
        
        ai_message = AIMessage.objects.create(
            session=session,
            sender='assistant',
            message_text='',
            status='pending'
        )

        rag_url = getattr(settings, 'RAG_API_URL', 'http://127.0.0.1:8001/get-response')
        rag_personal_url = getattr(
            settings,
            'RAG_PERSONAL_API_URL',
            f"{rag_url.rstrip('/')}/personalized"
        )
        personal_context = build_personal_context(request.user) if use_personal_context else None
        mode = 'personalized' if personal_context else 'standard'

        max_retries = getattr(settings, 'RAG_API_RETRY_MAX_ATTEMPTS', 3)
        backoff_factor = getattr(settings, 'RAG_API_RETRY_BACKOFF_FACTOR', 0.5)
        timeout = getattr(settings, 'RAG_API_TIMEOUT', 60)

        try:
            if personal_context:
                response, error = call_rag_api_with_retry(
                    rag_personal_url,
                    method='POST',
                    max_retries=max_retries,
                    backoff_factor=backoff_factor,
                    timeout=timeout,
                    json={
                        'question': message_text,
                        'context': personal_context,
                        'mode': mode,
                    }
                )
            else:
                response, error = call_rag_api_with_retry(
                    rag_url,
                    method='GET',
                    max_retries=max_retries,
                    backoff_factor=backoff_factor,
                    timeout=timeout,
                    params={
                        'question': message_text,
                        'mode': mode,
                    }
                )
            
            if error or response is None:
                raise error or requests.RequestException("RAG API request failed after retries")
            
            if response.status_code >= 400:
                response.raise_for_status()
            
            data = response.json()
            answer_text = (data.get('answer') or '').strip()
            sources = data.get('sources') or []
            metadata = data.get('metadata') or {}

            if not answer_text:
                answer_text = 'Вибачте, сервіс не надав відповіді.'

            metadata['personal_context_used'] = use_personal_context
            if personal_context:
                metadata['personal_context'] = personal_context
            metadata.setdefault('mode', mode)
            metadata['session_id'] = session.session_id

            ai_message.message_text = answer_text
            ai_message.status = 'completed'
            ai_message.sources = sources
            ai_message.metadata = metadata
            ai_message.response_time_ms = metadata.get('response_time_ms')
            ai_message.save(update_fields=['message_text', 'status', 'sources', 'metadata', 'response_time_ms'])
            
        except requests.Timeout as exc:
            logger.error(f"RAG API timeout after {max_retries + 1} attempts: {exc}")
            ai_message.message_text = (
                'Сервіс зараз перевантажений або не відповідає. '
                'Спробуйте перефразувати питання або зверніться пізніше.'
            )
            ai_message.status = 'error'
            ai_message.error_message = f'Timeout after {max_retries + 1} attempts'
            ai_message.metadata = {
                'personal_context_used': use_personal_context,
                'personal_context': personal_context,
                'mode': mode,
                'session_id': session.session_id,
                'error_type': 'timeout',
            }
            ai_message.save(update_fields=['message_text', 'status', 'error_message', 'metadata'])
            
        except requests.ConnectionError as exc:
            logger.error(f"RAG API connection error after {max_retries + 1} attempts: {exc}")
            ai_message.message_text = (
                'Не вдалося підключитися до сервісу. '
                'Перевірте інтернет-з\'єднання або спробуйте пізніше.'
            )
            ai_message.status = 'error'
            ai_message.error_message = f'Connection error after {max_retries + 1} attempts'
            ai_message.metadata = {
                'personal_context_used': use_personal_context,
                'personal_context': personal_context,
                'mode': mode,
                'session_id': session.session_id,
                'error_type': 'connection',
            }
            ai_message.save(update_fields=['message_text', 'status', 'error_message', 'metadata'])
            
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response else None
            logger.error(f"RAG API HTTP error (status {status_code}): {exc}")
            
            if status_code == 429:
                ai_message.message_text = (
                    'Занадто багато запитів. Зачекайте хвилину перед наступним питанням.'
                )
            else:
                ai_message.message_text = 'Помилка сервера. Спробуйте пізніше.'
            
            ai_message.status = 'error'
            ai_message.error_message = f'HTTP {status_code}: {str(exc)}'
            ai_message.metadata = {
                'personal_context_used': use_personal_context,
                'personal_context': personal_context,
                'mode': mode,
                'session_id': session.session_id,
                'error_type': 'http',
                'http_status': status_code,
            }
            ai_message.save(update_fields=['message_text', 'status', 'error_message', 'metadata'])
            
        except (requests.RequestException, ValueError) as exc:
            logger.error(f"RAG API request error: {exc}")
            ai_message.message_text = 'Вибачте, зараз я не можу відповісти. Спробуйте трохи пізніше.'
            ai_message.status = 'error'
            ai_message.error_message = str(exc)
            ai_message.metadata = {
                'personal_context_used': use_personal_context,
                'personal_context': personal_context,
                'mode': mode,
                'session_id': session.session_id,
                'error_type': 'unknown',
            }
            ai_message.save(update_fields=['message_text', 'status', 'error_message', 'metadata'])

        ai_message.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'session_id': session.session_id,
            'user_message': {
                'message_id': user_message.message_id,
                'sender': 'user',
                'message_text': user_message.message_text,
                'created_at': user_message.created_at.strftime('%H:%M'),
                'personal_context_used': use_personal_context,
            },
            'assistant_message': {
                'message_id': ai_message.message_id,
                'sender': 'assistant',
                'message_text': ai_message.message_text,
                'created_at': ai_message.created_at.strftime('%H:%M'),
                'status': ai_message.status,
                'error_message': ai_message.error_message or '',
                'personal_context_used': use_personal_context,
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
