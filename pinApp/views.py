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

                    # Fetch the personal_name from the Users table
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT personal_name
                            FROM "User"
                            WHERE uname = %s
                            """,
                            [username]
                        )
                        result = cursor.fetchone()

                    if result:
                        request.session['username'] = username
                        request.session['personal_name'] = personal_name = result[0]
                        print(f"Personal name found: {personal_name}")
                    else:
                        print("Personal name search failed")
                        personal_name = None
                    return render(request, 'dashboard.html', {'personal_name': personal_name})
                else:
                    print("User failed to be found")
                    messages.error(request, "Invalid username or password.")
                    return render(request, 'login.html')
        except Exception as e:
                print("Login error:", str(e))
                messages.error(request, "Something unexpected happended!")
    
    return render(request, 'login.html')

def dashboard_view(request):
    if 'username' not in request.session:
        return redirect('login')
    
    username = request.session['username']
    context = {}

    try:
        # Fetch the personal_name from the Users table
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT personal_name, email, created_at
                FROM "User"
                WHERE uname = %s
                """,
                [username]
            )
            result = cursor.fetchone()

        if result:
            context["personal_name"] = result[0]
            context["email"] = result[1]
            context["join_date"] = result[2]
        else:
            print("Personal name search failed")
            personal_name = None
        
        # Get user's boards
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT bid, name, comment_perms, created_at 
                FROM board 
                WHERE uname = %s 
                ORDER BY created_at DESC
                LIMIT 8
            """, [username])
            columns = [col[0] for col in cursor.description]
            boards = [dict(zip(columns, row)) for row in cursor.fetchall()]
        context['boards'] = boards
        print("Raw DB results: ", boards)

    except Exception as e:
        messages.error(request, f"Error loading dashboard: {str(e)}")

    return render(request, 'dashboard.html', context)

def create_board_view(request):
    if 'username' not in request.session:
        return redirect('login')
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        comment_perms = request.POST.get('comment_perms', 'public')
        username = request.session['username']
        
        # Validation
        errors = []
        if not name:
            errors.append('Board name is required')
        if comment_perms not in ['public', 'friends']:
            errors.append('Invalid comment permissions')
            
        if errors:
            return render(request, 'board_create.html', {'error': ' '.join(errors)})
        
        try:
            with connection.cursor() as cursor:
                # Insert new board
                cursor.execute("""
                    INSERT INTO Board (uname, name, comment_perms)
                    VALUES (%s, %s, %s)
                    RETURNING bid
                """, [username, name, comment_perms])                
                # bid = cursor.fetchone()[0]
                
            messages.success(request, 'Board created successfully!')
            return redirect('dashboard')
            
        except Exception as e:
            # Handle database errors
            print("Board Create error:", str(e))
            return render(request, 'board_create.html', {'error': f'Error creating board: {str(e)}'})
    
    # GET request - show empty form
    return render(request, 'board_create.html')