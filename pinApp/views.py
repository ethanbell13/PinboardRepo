from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.messages import get_messages
from django.db import connection

def home_view(request):
    return render(request, 'home.html')

def register_view(request):
    print("Beginning\n")
    if request.method == 'POST':
        userNameIn = request.POST.get('username')
        emailIn = request.POST.get('email')
        personalNameIn = request.POST.get('personal_name')
        password1In = request.POST.get('password1')
        password2In = request.POST.get('password2')
        if password1In != password2In:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')
        cursor = connection.cursor()
        print("Before try statement\n")
        try:
            cursor.execute(
                """
                select 1
                from \"User\"
                where uname = %s
                limit 1
                """,
                [userNameIn]
            )
            if cursor.fetchone():
                messages.error(request, "That username is not available.")
                return render(request, 'register.html')
            print("After unique username check\n")
            cursor.execute(
                """
                select 1
                from \"User\"
                where email = %s
                limit 1;
                """,
                [emailIn]
            )
            if cursor.fetchone():
                messages.error(request, "There is already an account with that email.")
                return render(request, 'register.html')
            print("after unique email check")
            print("Before insert statment\n")
            cursor.execute(
                    """
                    insert into \"User\"(uname, personal_name, passwd, email)
                    values(%s, %s, %s, %s)
                    returning uname
                    """,
                    [userNameIn, personalNameIn, password1In, emailIn]
            )
            user_row = cursor.fetchone()
            print("Inserted:", user_row)
            messages.success(request, "Account created successfully!")
            return redirect('login')
        except Exception as e:
                print("Registration error:", str(e))
                messages.error(request, "Something unexpected happended!")
        finally:
             cursor.close()
    return render(request, 'register.html')

def logout_view(request):
    request.session.flush()  # Clear all session data
    storage = get_messages(request)
    for _ in storage:
        pass  # this is enough to clear the message queue
    return redirect('home')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        print("Before credentials check")
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1
                    FROM "User"
                    WHERE uname = %s
                    AND passwd = %s
                    LIMIT 1
                    """,
                    [username, password]
                )
                if cursor.fetchone():
                    # credentials OK
                    print("User successfully found")
                    request.session['username'] = username
                    messages.success(request, f"Welcome back, {username}!")
                    return render(request, 'dashboard.html')
                else:
                    print("User failed to be found")
                    messages.error(request, "Invalid username or password.")
                    return render(request, 'login.html')
        except Exception as e:
                print("Registration error:", str(e))
                messages.error(request, "Something unexpected happended!")
    
    return render(request, 'login.html')

def dashboard_view(request):
    if 'username' not in request.session:
        return redirect('login')
    return render(request, 'dashboard.html', {'username': request.session['username']})

