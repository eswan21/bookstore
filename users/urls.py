from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.log_in, name="login" ),
    path("logout/", views.log_out, name="logout"),
    path("quick_register/", views.quick_register, name="quick_register"),
    path("forgot_password/", views.forgot_password, name="forgot_password"),
    path("verify_code/", views.verify_code, name="verify_code"),
    path("reset_password/", views.reset_password, name="reset_password"),
]



# crud

# create (GET new/POST create)
# /books/new, /books

# read (GET index/GET show)
# /books, /books/1

# update (GET edit/PUT update)
# /books/1/edit, /books/1

# DELETE destroy
# /books/1

# почитать про POST/GET разницу? тело запроса что такое
# - create all base models (relations, migrations)
# - base template (template inheritance?)
# - migrate existing pages (use it)
# - create user, auth/registration process




