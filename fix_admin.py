from core.models import CustomUser

admin = CustomUser.objects.get(username='admin')
print("User Type:", admin.user_type)

admin.user_type = 'admin'
admin.save()
print("Fixed! user_type is now:", admin.user_type)
