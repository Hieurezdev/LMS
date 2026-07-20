from django.db import migrations


def assign_one_teacher_per_classroom(apps, schema_editor):
    ClassRoom = apps.get_model('lms_manager', 'ClassRoom')
    Enrollment = apps.get_model('lms_manager', 'Enrollment')

    for classroom in ClassRoom.objects.all():
        teacher = classroom.teachers.order_by('id').first()
        if not teacher:
            continue
        classroom.teachers.set([teacher])
        subject = teacher.subjects.order_by('id').first()
        if not subject:
            continue
        Enrollment.objects.filter(student__classroom_id=classroom.id).exclude(teacher_id=teacher.id).delete()
        for student in classroom.students.all():
            Enrollment.objects.get_or_create(
                student_id=student.id,
                subject_id=subject.id,
                defaults={'teacher_id': teacher.id},
            )


class Migration(migrations.Migration):

    dependencies = [
        ('lms_manager', '0013_paymentbatch'),
    ]

    operations = [
        migrations.RunPython(assign_one_teacher_per_classroom, migrations.RunPython.noop),
    ]
