from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Event, Stage, DynamicAttribute, EventAttributeValue, Registration, Feedback, Result


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Role Info", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Role Info", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")

admin.site.register(Event)
admin.site.register(Stage)
admin.site.register(DynamicAttribute)
admin.site.register(EventAttributeValue)
admin.site.register(Registration)
admin.site.register(Feedback)
admin.site.register(Result)
