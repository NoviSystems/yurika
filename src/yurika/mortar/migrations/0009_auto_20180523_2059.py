# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-05-23 20:59
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mortar', '0008_crawleraccount'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='crawler',
            options={'ordering': ['pk']},
        ),
    ]