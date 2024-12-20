# Generated by Django 5.0.1 on 2024-10-04 15:01

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(db_index=True, max_length=255, verbose_name='Страна')),
                ('slug', models.SlugField(max_length=255, unique=True)),
            ],
            options={
                'verbose_name': 'Страна',
                'verbose_name_plural': 'Страны',
            },
        ),
        migrations.CreateModel(
            name='Stage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Стадия турнира')),
                ('title_api_football', models.CharField(max_length=255, verbose_name='Стадия турнира на API Football')),
            ],
            options={
                'verbose_name': 'Стадия турнира',
                'verbose_name_plural': 'Стадии турнира',
            },
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(db_index=True, max_length=255, verbose_name='Название')),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('city', models.CharField(max_length=255, verbose_name='Город')),
                ('id_api_football', models.BigIntegerField(db_index=True, default=0, verbose_name='ID на API Football')),
                ('is_moderated', models.BooleanField(default=True, verbose_name='Проверка пройдена')),
                ('logo', models.ImageField(null=True, upload_to='images/teams/')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='teams', to='tournaments.country', verbose_name='Страна')),
            ],
            options={
                'verbose_name': 'Команда',
                'verbose_name_plural': 'Команды',
                'ordering': ['title'],
            },
        ),
        migrations.CreateModel(
            name='Tournament',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(db_index=True, max_length=255, verbose_name='Турнир')),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('season', models.CharField(max_length=100, verbose_name='Сезон')),
                ('league_api_football', models.BigIntegerField(db_index=True, default=0, verbose_name='Лига на API Football')),
                ('season_api_football', models.CharField(default=0, max_length=100, verbose_name='Сезон на API Football')),
                ('description', models.TextField(blank=True, verbose_name='Описание турнира')),
                ('current', models.BooleanField(default=False, verbose_name='Действующий')),
                ('is_regular', models.BooleanField(default=False, verbose_name='Регулярный чемпионат')),
                ('tours_count', models.IntegerField(blank=True, default=0, verbose_name='Количество туров')),
                ('points_per_win', models.IntegerField(default=3, verbose_name='Очков за победу')),
                ('points_per_draw', models.IntegerField(default=1, verbose_name='Очков за ничью')),
                ('order', models.IntegerField(db_index=True, default=1, verbose_name='Порядок')),
                ('logo', models.ImageField(null=True, upload_to='images/tournaments/')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tournaments', to='tournaments.country', verbose_name='Страна')),
            ],
            options={
                'verbose_name': 'Турнир',
                'verbose_name_plural': 'Турниры',
                'ordering': ['order', '-season'],
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Событие')),
                ('description', models.TextField(blank=True, verbose_name='Описание события')),
                ('operation', models.CharField(choices=[('A', 'Добавить'), ('R', 'Отнять'), ('N', 'Не менять')], default='N', max_length=1, verbose_name='Операция')),
                ('value', models.IntegerField(default=0)),
                ('tour', models.IntegerField(default=0)),
                ('team', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='events', to='tournaments.team', verbose_name='Команда')),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='tournaments.tournament', verbose_name='Турнир')),
            ],
            options={
                'verbose_name': 'Событие',
                'verbose_name_plural': 'События',
            },
        ),
        migrations.CreateModel(
            name='ApiFootballID',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('api_football_id', models.PositiveIntegerField(null=True)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
            options={
                'verbose_name': 'Соответствия APIFootball',
                'verbose_name_plural': 'Соответствие APIFootball',
                'indexes': [models.Index(fields=['content_type', 'object_id'], name='tournaments_content_b2f88e_idx')],
                'unique_together': {('content_type', 'object_id', 'api_football_id')},
            },
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('group', models.CharField(blank=True, max_length=2, null=True, verbose_name='Группа')),
                ('tour', models.IntegerField(blank=True, default=0, null=True, verbose_name='Тур')),
                ('date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Дата и время')),
                ('at_home', models.BooleanField(default=True)),
                ('result', models.CharField(choices=[('W', 'Победа'), ('D', 'Ничья'), ('L', 'Поражение')], default='W', max_length=1, null=True, verbose_name='Результат')),
                ('status', models.CharField(choices=[('NS', 'Не начался'), ('FT', 'Завершен'), ('1H', 'Идет первый тайм'), ('HT', 'Перерыв'), ('2H', 'Идет второй тайм'), ('CANC', 'Отменен'), ('PEN', 'Серия пенальти'), ('TBD', 'Точная дата не известна'), ('PST', 'Отложен')], default='NS', max_length=5, verbose_name='Статус матча')),
                ('points_received', models.IntegerField(default=0, verbose_name='Очков получено')),
                ('goals_scored', models.IntegerField(default=0, null=True, verbose_name='Голов забито')),
                ('goals_conceded', models.IntegerField(default=0, null=True, verbose_name='Голов пропущено')),
                ('video', models.CharField(blank=True, max_length=255, null=True, verbose_name='Видео')),
                ('opposite_match', models.BigIntegerField(default=0, verbose_name='Сопряженный матч')),
                ('score', models.JSONField(default=dict)),
                ('goals_stats', models.JSONField(null=True)),
                ('is_moderated', models.BooleanField(default=True, verbose_name='Проверка пройдена')),
                ('stage', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to='tournaments.stage', verbose_name='Стадия турнира')),
                ('main_team', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='matches', to='tournaments.team', verbose_name='Команда')),
                ('opponent', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='tournaments.team', verbose_name='Соперник')),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='matches', to='tournaments.tournament', verbose_name='Турнир')),
            ],
            options={
                'verbose_name': 'Матч',
                'verbose_name_plural': 'Матчи',
                'unique_together': {('main_team', 'opponent', 'date')},
            },
        ),
    ]
