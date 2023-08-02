# Generated by Django 4.1.4 on 2023-07-29 14:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('claim', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UpdateMeetingRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('day', models.CharField(choices=[('MO', 'Monday'), ('TU', 'Tuesday'), ('WE', 'Wednesday'), ('TH', 'Thursday'), ('FR', 'Friday')], max_length=2)),
                ('building', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='change_requests', to='claim.building')),
                ('original', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='change_requests', to='claim.meeting')),
                ('room', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='change_requests', to='claim.room')),
            ],
        ),
        migrations.CreateModel(
            name='UpdateMeetingMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('requested', 'Requested'), ('accepted', 'Accepted'), ('revised_accepted', 'Revised and Accepted'), ('denied', 'Denied')], max_length=20)),
                ('old_start_time', models.TimeField()),
                ('old_end_time', models.TimeField()),
                ('old_day', models.CharField(choices=[('MO', 'Monday'), ('TU', 'Tuesday'), ('WE', 'Wednesday'), ('TH', 'Thursday'), ('FR', 'Friday')], max_length=2)),
                ('new_start_time', models.TimeField()),
                ('new_end_time', models.TimeField()),
                ('new_day', models.CharField(choices=[('MO', 'Monday'), ('TU', 'Tuesday'), ('WE', 'Wednesday'), ('TH', 'Thursday'), ('FR', 'Friday')], max_length=2)),
                ('course', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages', to='claim.building')),
                ('new_building', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages_of_old', to='claim.building')),
                ('new_room', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages_of_old', to='claim.room')),
                ('old_building', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages_of_new', to='claim.building')),
                ('old_room', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages_of_new', to='claim.room')),
                ('request', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messages', to='request.updatemeetingrequest')),
            ],
        ),
    ]
