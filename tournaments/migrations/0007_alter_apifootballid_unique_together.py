# Generated by Django 5.0.1 on 2024-08-26 17:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('tournaments', '0006_apifootballid'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='apifootballid',
            unique_together={('content_type', 'object_id', 'api_football_id')},
        ),
    ]