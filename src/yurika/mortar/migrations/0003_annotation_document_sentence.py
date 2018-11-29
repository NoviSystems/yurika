# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-05-03 20:00
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mortar', '0002_sentencetokenizer'),
    ]

    operations = [
        migrations.CreateModel(
            name='Annotation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.TextField(help_text='Elasticsearch query JSON.')),
                ('crawler', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mortar.Crawler')),
            ],
            options={
                'ordering': ['pk'],
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('elastic_id', models.TextField()),
                ('url', models.URLField(max_length=2083)),
                ('timestamp', models.DateTimeField()),
                ('text', models.TextField()),
                ('annotation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mortar.Annotation')),
            ],
        ),
        migrations.CreateModel(
            name='Sentence',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('elastic_id', models.TextField()),
                ('text', models.TextField()),
                ('annotation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mortar.Annotation')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mortar.Document')),
            ],
        ),
    ]
