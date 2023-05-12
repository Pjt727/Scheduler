# Generated by Django 4.1.4 on 2023-05-07 23:57

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('authentication', '0002_initial'),
        ('request', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RequestBundle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50)),
                ('reason', models.CharField(blank=True, default=None, max_length=1024, null=True)),
                ('is_closed', models.BooleanField(blank=True, default=False)),
                ('approver', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='my_approve_request_bundles', to='authentication.professor')),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='my_request_bundles', to='authentication.professor')),
            ],
        ),
        migrations.CreateModel(
            name='RequestMessageGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_bundle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='request_message_groups', to='request.requestbundle')),
            ],
        ),
        migrations.CreateModel(
            name='RequestMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(blank=True, default=django.utils.timezone.now)),
                ('message', models.CharField(blank=True, default=None, max_length=1024, null=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='author_request_messages', to='authentication.professor')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='request_messages', to='request.requestmessagegroup')),
            ],
            options={
                'ordering': ['date'],
            },
        ),
        migrations.CreateModel(
            name='RequestItemGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_bundle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='request_item_groups', to='request.requestbundle')),
            ],
        ),
        migrations.CreateModel(
            name='RequestItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('not_requested', 'Not requested'), ('requested', 'Requested'), ('changed', 'Changed'), ('approved', 'Approved'), ('denied', 'Denied'), ('cancelled', 'Cancelled'), ('deleted', 'Deleted')], default='not_requested', max_length=20, null=True)),
                ('date', models.DateField(blank=True, default=django.utils.timezone.now)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='request_items', to='request.requestitemgroup')),
                ('request_message', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='request_items', to='request.requestmessage')),
            ],
        ),
    ]