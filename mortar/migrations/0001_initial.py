# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-10-09 18:55
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Annotation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('category', models.CharField(choices=[('S', 'Sentence'), ('P', 'Paragraph'), ('D', 'Document')], max_length=1)),
            ],
        ),
        migrations.CreateModel(
            name='Crawler',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('category', models.CharField(choices=[('txt', 'File System Crawler'), ('web', 'Web Crawler')], max_length=3)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('Running', 'Running'), ('Finished', 'Finished'), ('Stopped', 'Stopped')], max_length=15)),
                ('process_id', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Dictionary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('filepath', models.FilePathField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Dictionaries',
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField()),
                ('crawled_at', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='ElasticIndex',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('regex', models.CharField(blank=True, max_length=255, null=True)),
                ('lft', models.PositiveIntegerField(db_index=True, editable=False)),
                ('rght', models.PositiveIntegerField(db_index=True, editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, editable=False)),
                ('level', models.PositiveIntegerField(db_index=True, editable=False)),
                ('dictionary', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='nodes', to='mortar.Dictionary')),
                ('parent', mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='mortar.Node')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Query',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=50)),
                ('string', models.TextField(blank=True)),
                ('elastic_json', models.TextField(blank=True)),
            ],
            options={
                'verbose_name_plural': 'Queries',
            },
        ),
        migrations.CreateModel(
            name='QueryPart',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('op', models.CharField(choices=[('+', 'AND'), ('|', 'OR')], max_length=1)),
                ('name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Seed',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'verbose_name': 'Seed',
            },
        ),
        migrations.CreateModel(
            name='Tree',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('slug', models.SlugField(unique=True)),
                ('doc_dest_index', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='doc_dests', to='mortar.ElasticIndex')),
                ('doc_source_index', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='doc_sources', to='mortar.ElasticIndex')),
            ],
        ),
        migrations.CreateModel(
            name='Word',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('dictionary', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='words', to='mortar.Dictionary')),
            ],
        ),
        migrations.CreateModel(
            name='DictionaryPart',
            fields=[
                ('querypart_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='mortar.QueryPart')),
                ('dictionary', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='query_parts', to='mortar.Dictionary')),
            ],
            bases=('mortar.querypart',),
        ),
        migrations.CreateModel(
            name='FileSeed',
            fields=[
                ('seed_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='mortar.Seed')),
                ('path', models.FilePathField()),
            ],
            bases=('mortar.seed',),
        ),
        migrations.CreateModel(
            name='PartOfSpeechPart',
            fields=[
                ('querypart_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='mortar.QueryPart')),
                ('part_of_speech', models.CharField(choices=[('CC', 'Coordinating Conjunction'), ('CD', 'Cardinal Number'), ('DT', 'Determiner'), ('EX', 'Existential there'), ('FW', 'Foreign Word'), ('IN', 'Preposition of subordinating conjunction'), ('JJ', 'Adjective'), ('JJR', 'Adjective, comparitive'), ('JJS', 'Adjective, superlative'), ('LS', 'List item marker'), ('MD', 'Modal'), ('NN', 'Noun, singular or mass'), ('NNS', 'Noun, plural'), ('NNP', 'Proper Noun, singular'), ('NNPS', 'Proper Noun, plural'), ('PDT', 'Predeterminer'), ('POS', 'Possessive ending'), ('PRP', 'Personal pronoun'), ('PRP$', 'Possessive pronoun'), ('RB', 'Adverb'), ('RBR', 'Adverb, comparative'), ('RBS', 'Adverb, superlative'), ('RP', 'Particle'), ('SYM', 'Symbol'), ('TO', 'to'), ('UH', 'Interjection'), ('VB', 'Verb, base form'), ('VBD', 'Verb, past tense'), ('VBG', 'Verb, gerund or present participle'), ('VBN', 'Verb, past participle'), ('VBP', 'Verb, non-3rd person singular present'), ('VBZ', 'Verb 3rd person singular present'), ('WDT', 'Wh-determiner'), ('WP', 'Wh-pronoun'), ('WP$', 'Possessive wh-pronoun'), ('WRB', 'Wh-adverb')], max_length=4)),
            ],
            bases=('mortar.querypart',),
        ),
        migrations.CreateModel(
            name='RegexPart',
            fields=[
                ('querypart_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='mortar.QueryPart')),
            ],
            bases=('mortar.querypart',),
        ),
        migrations.CreateModel(
            name='SubQueryPart',
            fields=[
                ('querypart_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='mortar.QueryPart')),
                ('subquery', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='query_parts', to='mortar.Query')),
            ],
            bases=('mortar.querypart',),
        ),
        migrations.CreateModel(
            name='URLSeed',
            fields=[
                ('seed_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='mortar.Seed')),
                ('url', models.URLField()),
            ],
            bases=('mortar.seed',),
        ),
        migrations.AddField(
            model_name='querypart',
            name='query',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parts', to='mortar.Query'),
        ),
        migrations.AddField(
            model_name='node',
            name='tree_link',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nodes', to='mortar.Tree'),
        ),
        migrations.AddField(
            model_name='document',
            name='index',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='mortar.ElasticIndex'),
        ),
        migrations.AddField(
            model_name='document',
            name='tree',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='mortar.Tree'),
        ),
        migrations.AddField(
            model_name='crawler',
            name='index',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='crawlers', to='mortar.ElasticIndex'),
        ),
        migrations.AddField(
            model_name='crawler',
            name='seed_list',
            field=models.ManyToManyField(blank=True, related_name='crawlers', to='mortar.Seed'),
        ),
        migrations.AddField(
            model_name='annotation',
            name='document',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='annotations', to='mortar.Document'),
        ),
        migrations.AddField(
            model_name='annotation',
            name='query',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='annotations', to='mortar.Query'),
        ),
        migrations.AddField(
            model_name='annotation',
            name='tree',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='annotations', to='mortar.Tree'),
        ),
        migrations.AddField(
            model_name='regexpart',
            name='regex',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='query_parts', to='mortar.Node'),
        ),
    ]
