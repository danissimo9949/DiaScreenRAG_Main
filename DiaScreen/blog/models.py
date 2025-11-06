from django.db import models

# Create your models here.
class Article(models.Model):
    article_name = models.CharField(max_length=500, blank=False, null=False, unique=True)
    article_short_name = models.CharField(max_length=50, blank=True, null=True, unique=True)
    article_author = models.CharField(max_length=255, blank=True, null=True)
    article_description = models.CharField(max_length=500, blank=True, null=True)
    article_img = models.ImageField(upload_to='articles-img/')
    article_text = models.TextField(max_length=6000, blank=False, null=False)
    date_of_creation = models.DateField(auto_now_add=True, db_index=True)
    
    def get_image_url(self):
        return self.article_img.url if self.article_img else None

    def __str__(self):
        return self.article_name
    
    class Meta:
        verbose_name = 'Article'
        verbose_name_plural = 'Articles'
        ordering = ['-date_of_creation']