from django.urls import path
from .views import InformationPanel, ArticleDetails, delete_article, edit_article

urlpatterns = [
    path('', InformationPanel.as_view(), name='information'),
    path('article/<int:pk>', ArticleDetails.as_view(), name='article_detail'),
    path('delete-article/<int:article_id>', delete_article, name='delete_article'),
    path('edit-article/<int:article_id>/', edit_article, name='edit_article'),
]
