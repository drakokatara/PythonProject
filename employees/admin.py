from django.contrib import admin
from .models import Employee, Attendance

# ── Κεντρικές Ρυθμίσεις Branding ──
admin.site.site_header = "PCS Attendance Dashboard"
admin.site.site_title = "PCS Portal"
admin.site.index_title = "Διαχείριση Προσωπικού & Παρουσιών"

# ── Inline Διαχείριση ──
# Επιτρέπει την προσθήκη παρουσιών απευθείας μέσα στην καρτέλα του υπαλλήλου
class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 1
    fields = ('date', 'work_type')
    show_change_link = True

# ── Employee Admin ──
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'date_joined', 'initial_debt')
    search_fields = ('full_name', 'email')
    list_filter = ('date_joined',)
    inlines = [AttendanceInline]
    list_per_page = 20
    ordering = ('full_name',)

    # Επιβολή του CSS
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }

# ── Attendance Admin ──
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'work_type')
    list_filter = ('work_type', 'date', 'employee')
    search_fields = ('employee__full_name',)
    date_hierarchy = 'date' # Μπάρα ημερομηνιών στο πάνω μέρος

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }