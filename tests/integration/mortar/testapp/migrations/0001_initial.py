# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-04-10 12:50
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('mortar', '0002_auto_20180410_1250'),
    ]

    operations = [
        migrations.CreateModel(
            name='Abort',
            fields=[
                ('task_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='mortar.Task')),
            ],
            bases=('mortar.task',),
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('downcast', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='Fail',
            fields=[
                ('task_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='mortar.Task')),
            ],
            bases=('mortar.task',),
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('downcast', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='Finish',
            fields=[
                ('task_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='mortar.Task')),
                ('flag', models.BooleanField(default=False)),
            ],
            bases=('mortar.task',),
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('downcast', django.db.models.manager.Manager()),
            ],
        ),
    ]