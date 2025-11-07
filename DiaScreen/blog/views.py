from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from typing import Any
from django.views import generic
from user_auth.mixins import AdminRoleMixin
from django.core.exceptions import PermissionDenied
from .models import Article
from .forms import ArticleCreationForm


class InformationPanel(generic.ListView, AdminRoleMixin):
    model = Article
    template_name = 'blog/info_panel.html'
    context_object_name = 'article_list'
    paginate_by = 9
    
    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.get_admin_role(self.request)
        if context['is_admin']:
            context['article_creation_form'] = ArticleCreationForm()
        return context
    
    def post(self, request, *args, **kwargs):
        
        if not self.get_admin_role(request):
            raise PermissionDenied("Тільки адміністратори можуть створювати статті")
        
        article_form = ArticleCreationForm(request.POST, request.FILES)
        if article_form.is_valid():
            article_form.save()
            return redirect('information')
        else:
            messages.error(request, 'Помилка при створенні статті. Перевірте форму.')
            context = self.get_context_data(**kwargs)
            context['article_creation_form'] = article_form
            context['form_errors'] = True
            return render(request, self.template_name, context)


class ArticleDetails(generic.DetailView, AdminRoleMixin):
    model = Article
    template_name = 'blog/article_detail.html'
    context_object_name = 'article'

    def split_text(self):
        article = self.get_object()
        paragraphs = article.article_text.split('\n')
        return paragraphs

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        context['is_admin'] = self.get_admin_role(self.request)
        context['paragraphs'] = self.split_text()
        if context['is_admin']:
            context['article_form'] = ArticleCreationForm(instance=self.get_object())
        return context


@require_POST
def delete_article(request, article_id):
    user = request.user
    is_admin = user.groups.filter(name='Administrators').exists()
    if not is_admin:
        raise PermissionDenied("Тільки адміністратори можуть видаляти статті")
    
    article = get_object_or_404(Article, id=article_id)
    article.delete()
    messages.success(request, 'Статтю успішно видалено!')
    return redirect('information')


def edit_article(request, article_id):
    user = request.user
    is_admin = user.groups.filter(name='Administrators').exists()
    if not is_admin:
        raise PermissionDenied("Тільки адміністратори можуть редагувати статті")
    
    article = get_object_or_404(Article, id=article_id)
    if request.method == 'POST':
        article_form = ArticleCreationForm(request.POST, request.FILES, instance=article)
        if article_form.is_valid():
            article_form.save()
            messages.success(request, 'Статтю успішно оновлено!')
            return redirect('article_detail', pk=article_id)
        else:
            messages.error(request, 'Помилка при оновленні статті. Перевірте форму.')
            return render(request, 'blog/edit_article.html', {
                'article_form': article_form,
                'article': article,
                'is_admin': is_admin
            })
    else:
        article_form = ArticleCreationForm(instance=article)
    
    return render(request, 'blog/edit_article.html', {
        'article_form': article_form,
        'article': article,
        'is_admin': is_admin
    })
