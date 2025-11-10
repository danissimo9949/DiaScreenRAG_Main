from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .forms import SupportTicketForm


@login_required
def create_ticket(request):
    if request.method != "POST":
        return redirect(request.META.get("HTTP_REFERER", "/"))

    form = SupportTicketForm(request.POST)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"

    if form.is_valid():
        ticket = form.save(commit=False)
        ticket.user = request.user
        ticket.save()
        messages.success(request, "Звернення передано в технічну підтримку.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{form.fields[field].label or field}: {error}")

    return redirect(next_url)


