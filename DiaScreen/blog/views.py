from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from typing import Any
from django.views import generic
from user_auth.mixins import AdminRoleMixin
from .models import Article
from .forms import ArticleCreationForm


class InformationPanel(generic.ListView, AdminRoleMixin):
    model = Article
    template_name = 'info_panel.html'
    context_object_name = 'article_list'
    paginate_by = 9
    
    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        context['article_creation_form'] = ArticleCreationForm()
        context['is_admin'] = self.get_admin_role(self.request)
        return context
    
    def post(self, request, *args, **kwargs):
        article_form = ArticleCreationForm(request.POST, request.FILES)
        if article_form.is_valid():
            article_form.save()
            return redirect('information')
        return redirect('information')


class ArticleDetails(generic.DetailView, AdminRoleMixin):
    model = Article
    template_name = 'article_detail.html'
    context_object_name = 'article'

    def split_text(self):
        article = self.get_object()
        paragraphs = article.article_text.split('\n')
        return paragraphs

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        context['article_form'] = ArticleCreationForm(instance=self.get_object())
        context['paragraphs'] = self.split_text()
        context['is_admin'] = self.get_admin_role(self.request)
        return context


@require_POST
def delete_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    article.delete()
    return redirect('information')


def edit_article(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    if request.method == 'POST':
        article_form = ArticleCreationForm(request.POST, request.FILES, instance=article)
        if article_form.is_valid():
            article_form.save()
            return redirect('article_detail', pk=article_id)
    else:
        article_form = ArticleCreationForm(instance=article)
