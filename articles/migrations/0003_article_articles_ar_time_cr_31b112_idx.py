# Generated by Django 5.0.1 on 2025-03-03 13:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0002_comment_article_articles_ar_time_cr_31b112_idx_and_more'),
        ('tournaments', '0003_team_temporary_team_id_alter_match_status'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='article',
            index=models.Index(fields=['-time_create'], name='articles_ar_time_cr_31b112_idx'),
        ),
    ]
