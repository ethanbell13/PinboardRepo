from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.messages import get_messages
from django.db import connection
from django.db import transaction
import base64

def home_view(request):
    if 'username' in request.session:
        return redirect('dashboard')
    
    return render(request, 'home.html')

def register_view(request):
    if 'username' in request.session:
        return redirect('dashboard')
    
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
    if 'username' in request.session:
        return redirect('dashboard')
    
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
                    return redirect('dashboard')
                else:
                    print("User failed to be found")
                    messages.error(request, "Invalid username or password.")
                    return render(request, 'login.html')
        except Exception as e:
                print("Login error:", str(e))
                messages.error(request, "Something unexpected happended!")
    
    return render(request, 'login.html')

def edit_profile_view(request):
    if 'username' not in request.session:
        return redirect('login')
    
    username = request.session['username']
    context = {}
    
    try:
        with connection.cursor() as cursor:
            # Get current user data
            cursor.execute("""
                SELECT personal_name, passwd 
                FROM "User" 
                WHERE uname = %s
            """, [username])
            user_data = cursor.fetchone()
            
            if not user_data:
                messages.error(request, "User not found")
                return redirect('dashboard')
            
            context['user'] = {
                'personal_name': user_data[0],
            }
            
            if request.method == 'POST':
                personal_name = request.POST.get('personal_name', '').strip()
                current_password = request.POST.get('current_password', '')
                new_password = request.POST.get('new_password', '')
                confirm_password = request.POST.get('confirm_password', '')
                
                errors = []
                updates = []
                params = []
                
                # Validate personal name
                if not personal_name:
                    errors.append("Display name is required")
                else:
                    updates.append("personal_name = %s")
                    params.append(personal_name)
                
                # Password change logic
                if current_password or new_password or confirm_password:
                    # Verify all password fields are filled
                    if not all([current_password, new_password, confirm_password]):
                        errors.append("All password fields are required for password change")
                    else:
                        # Verify current password
                        stored_password = user_data[1]
                        # WARNING: In practice, use proper password hashing comparison!
                        if current_password != stored_password:
                            errors.append("Current password is incorrect")
                        elif new_password != confirm_password:
                            errors.append("New passwords do not match")
                        else:
                            # In practice: Use proper password hashing here!
                            updates.append("passwd = %s")
                            params.append(new_password)  # Store properly hashed password
                
                if errors:
                    return render(request, 'edit_profile.html', {
                        'error': ' '.join(errors),
                        'user': {'personal_name': personal_name}
                    })
                
                # Build update query
                if updates:
                    query = """
                        UPDATE "User" 
                        SET {}
                        WHERE uname = %s
                    """.format(", ".join(updates))
                    
                    params.append(username)
                    
                    cursor.execute(query, params)
                    messages.success(request, "Profile updated successfully")
                    return redirect('dashboard')
                
    except Exception as e:
        messages.error(request, f"Error updating profile: {str(e)}")
    
    return render(request, 'edit_profile.html', context)

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
            context["personal_name"] = None
            context["email"] = None 
            context["join_date"] = None
        
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
            return render(request, 'create_board.html', {'error': ' '.join(errors)})
        
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
            return render(request, 'create_board.html', {'error': f'Error creating board: {str(e)}'})
    
    # GET request - show empty form
    return render(request, 'create_board.html')

def process_tags(tags_str, picid):
    """Helper function to handle tag insertion and relationships"""
    tags = [tag.strip().lower() for tag in tags_str.split(',') if tag.strip()]
    with connection.cursor() as cursor:
        for tag in tags:
            # Insert tag if not exists
            cursor.execute("""
                INSERT INTO Tag (tname) 
                VALUES (%s)
                ON CONFLICT (tname) DO NOTHING
            """, [tag])
            
            # Create picture-tag relationship
            cursor.execute("""
                INSERT INTO PictureTag (picid, tname)
                VALUES (%s, %s)
                ON CONFLICT (picid, tname) DO NOTHING
            """, [picid, tag])

def edit_board_view(request, bid):
    if 'username' not in request.session:
        return redirect('login')
    
    username = request.session['username']
    context = {}
    
    try:
        with connection.cursor() as cursor:
            # Verify board ownership
            cursor.execute("""
                SELECT bid, name, comment_perms, created_at 
                FROM board 
                WHERE bid = %s AND uname = %s
            """, [bid, username])
            
            board_data = cursor.fetchone()
            if not board_data:
                messages.error(request, "Board not found or access denied")
                return redirect('dashboard')
            
            # Convert board data to dict
            columns = [col[0] for col in cursor.description]
            context['board'] = dict(zip(columns, board_data))
            
            # Handle form submissions
            if request.method == 'POST':
                if 'name' in request.POST:  # Board update
                    new_name = request.POST.get('name').strip()
                    new_perms = request.POST.get('comment_perms')
                    
                    cursor.execute("""
                        UPDATE board 
                        SET name = %s, comment_perms = %s 
                        WHERE bid = %s
                    """, [new_name, new_perms, bid])
                    messages.success(request, "Board updated successfully")
                    return redirect('edit_board', bid=bid)
                
                # Image handling
                tags = request.POST.get('tags', '')
                if 'image' in request.FILES:  # Image upload
                    image_file = request.FILES['image']
                    src_url = request.POST.get('source_url')
                    
                    # Convert image to bytes
                    img_bytes = b''
                    for chunk in image_file.chunks():
                        img_bytes += chunk
                    
                    with transaction.atomic():
                        # Create pin
                        cursor.execute("""
                            INSERT INTO Pin (uname, bid)
                            VALUES (%s, %s)
                            RETURNING pinid
                        """, [username, bid])
                        pin_id = cursor.fetchone()[0]
                        
                        # Create picture
                        cursor.execute("""
                            INSERT INTO Picture (org_pinid, img_data, src_url)
                            VALUES (%s, %s, %s)
                            RETURNING picid
                        """, [pin_id, img_bytes, src_url])
                        pic_id = cursor.fetchone()[0]
                        
                        # Update pin with picid
                        cursor.execute("""
                            UPDATE Pin SET picid = %s 
                            WHERE pinid = %s
                        """, [pic_id, pin_id])

                        # Process tags
                        if tags:
                            process_tags(tags, pic_id)
                        
                    messages.success(request, "Image uploaded successfully")
                    return redirect('edit_board', bid=bid)
            
            # Get existing pins with tags
            cursor.execute("""
                SELECT p.pinid, pic.picid, pic.img_data, pic.src_url,
                       COALESCE(array_agg(t.tname), '{}'::varchar[]) as tags
                FROM Pin p
                JOIN Picture pic ON p.picid = pic.picid
                LEFT JOIN PictureTag pt ON pic.picid = pt.picid
                LEFT JOIN Tag t ON pt.tname = t.tname
                WHERE p.bid = %s
                GROUP BY p.pinid, pic.picid
                ORDER BY p.created_at DESC
            """, [bid])
            
            pins = []
            for row in cursor.fetchall():
                pins.append({
                    'pinid': row[0],
                    'picid': row[1],
                    'img_data': base64.b64encode(row[2]).decode('utf-8'),
                    'src_url': row[3],
                    'tags': row[4]
                })
            context['pins'] = pins
            
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
    
    return render(request, 'edit_board.html', context)

def delete_board_view(request, bid):
    if 'username' not in request.session:
        return redirect('login')
    
    try:
        with connection.cursor() as cursor:
            # Verify ownership before deletion
            cursor.execute("""
                DELETE FROM board 
                WHERE bid = %s AND uname = %s
            """, [bid, request.session['username']])
            
            if cursor.rowcount == 0:
                messages.error(request, "Board not found or access denied")
            else:
                messages.success(request, "Board deleted successfully")
                
    except Exception as e:
        messages.error(request, f"Deletion error: {str(e)}")
    
    return redirect('dashboard')

def delete_pin_view(request, pinid):
    if 'username' not in request.session:
        return redirect('login')
    
    try:
        with connection.cursor() as cursor:
            # Verify ownership before deletion
            cursor.execute("""
                DELETE FROM Pin 
                WHERE pinid = %s AND uname = %s
            """, [pinid, request.session['username']])
            
            if cursor.rowcount == 0:
                messages.error(request, "Pin not found or access denied")
            else:
                messages.success(request, "Pin deleted successfully")
                
    except Exception as e:
        messages.error(request, f"Deletion error: {str(e)}")
    
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

# TODO edit profile
# TODO view pinboards
# TODO follow streams
# TODO friend requests
# TODO search for other users
# TODO search for other pinboards
# TODO board comments & likes