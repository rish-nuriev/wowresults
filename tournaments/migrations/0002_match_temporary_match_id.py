# Generated by Django 5.0.1 on 2025-01-08 16:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='temporary_match_id',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Поле для хранения временного ID от АПИ'),
        ),
    ]
