from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.messages import get_messages
from django.db import connection
from django.db import transaction
from django.http import Http404
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
                        # TODO use proper password hashing comparison in production
                        if current_password != stored_password:
                            errors.append("Current password is incorrect")
                        elif new_password != confirm_password:
                            errors.append("New passwords do not match")
                        else:
                            # TODO use proper password hashing comparison in production
                            updates.append("passwd = %s")
                            params.append(new_password)
                
                if errors:
                    return render(request, 'edit_profile.html', {'error': ' '.join(errors), 'user': {'personal_name': personal_name}})
                
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
                    return redirect('user_profile', username=request.session.username)
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
    """Update tags for a specific picture"""
    tags = [tag.strip().lower() for tag in tags_str.split(',') if tag.strip()]
    
    with connection.cursor() as cursor:
        try:
            # Remove existing tags
            cursor.execute("DELETE FROM picturetag WHERE picid = %s", [picid])
            
            # Insert new tags
            for tag in tags:
                # Insert tag if new
                cursor.execute("""
                    INSERT INTO Tag (tname)
                    VALUES (%s)
                    ON CONFLICT (tname) DO NOTHING
                """, [tag])
                
                # Link tag to picture
                cursor.execute("""
                    INSERT INTO picturetag (picid, tname)
                    VALUES (%s, %s)
                    ON CONFLICT (picid, tname) DO NOTHING
                """, [picid, tag])
        
        except Exception as e:
            print(f"Tag processing error: {str(e)}")

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
                # Board metadata update
                if 'name' in request.POST:
                    new_name = request.POST.get('name', '').strip()
                    new_perms = request.POST.get('comment_perms', 'public')
                    
                    if not new_name:
                        messages.error(request, "Board name cannot be empty")
                        return redirect('edit_board', bid=bid)
                    
                    cursor.execute("""
                        UPDATE board 
                        SET name = %s, comment_perms = %s 
                        WHERE bid = %s
                    """, [new_name, new_perms, bid])
                    messages.success(request, "Board updated successfully")
                    return redirect('edit_board', bid=bid)
                
                # Tag update handling
                if 'picid' in request.POST and 'tags' in request.POST:
                    picid = request.POST['picid']
                    new_tags = request.POST['tags']
                    
                    try:
                        # Verify picture ownership
                        cursor.execute("""
                            SELECT 1 FROM Picture p
                            JOIN Pin pi ON p.org_pinid = pi.pinid
                            JOIN Board b ON pi.bid = b.bid
                            WHERE p.picid = %s AND b.uname = %s
                        """, [picid, username])
                        
                        if not cursor.fetchone():
                            messages.error(request, "Permission denied")
                            return redirect('edit_board', bid=bid)
                        
                        # Process tag update
                        process_tags(new_tags, picid)
                        messages.success(request, "Tags updated successfully")
                        return redirect('edit_board', bid=bid)
                    
                    except Exception as e:
                        messages.error(request, f"Error updating tags: {str(e)}")
                        return redirect('edit_board', bid=bid)
                
                # Image upload handling
                if 'image' in request.FILES:
                    image_file = request.FILES['image']
                    src_url = request.POST.get('source_url', '')
                    tags = request.POST.get('tags', '')
                    
                    if not src_url:
                        messages.error(request, "Source URL is required")
                        return redirect('edit_board', bid=bid)
                    
                    try:
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
                                
                        messages.success(request, "Image uploaded successfully with tags")
                        return redirect('edit_board', bid=bid)
                    
                    except Exception as e:
                        messages.error(request, f"Error uploading image: {str(e)}")
                        return redirect('edit_board', bid=bid)
            
            # Get existing pins with tags
            cursor.execute("""
                SELECT p.pinid, pic.picid, pic.img_data, pic.src_url,
                       COALESCE(array_agg(t.tname), '{}'::varchar[]) as tags
                FROM Pin p
                JOIN Picture pic ON p.picid = pic.picid
                LEFT JOIN picturetag pt ON pic.picid = pt.picid
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
        messages.error(request, "Error processing request")
    
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

def board_view(request, bid):
    try:
        with connection.cursor() as cursor:
            # Get board metadata
            cursor.execute("""
                SELECT b.name, u.personal_name, b.created_at, u.uname, u.personal_name 
                FROM board b
                JOIN "User" u ON b.uname = u.uname
                WHERE b.bid = %s
            """, [bid])
            
            board_data = cursor.fetchone()
            if not board_data:
                return redirect('home')
            
            # Get all pins with basic info
            cursor.execute("""
                SELECT p.pinid, pic.img_data, pic.src_url,
                       array_agg(t.tname) AS tags
                FROM pin p
                JOIN picture pic ON p.picid = pic.picid
                LEFT JOIN picturetag pt ON pic.picid = pt.picid
                LEFT JOIN tag t ON pt.tname = t.tname
                WHERE p.bid = %s
                GROUP BY p.pinid, pic.picid
                ORDER BY p.created_at DESC
            """, [bid])
            
            pins = []
            for row in cursor.fetchall():
                pins.append({
                    'pinid': row[0],
                    'img_data': base64.b64encode(row[1]).decode('utf-8'),
                    'src_url': row[2],
                    'tags': row[3] if row[3] else []
                })
            
            context = {
                'board': {
                    'name': board_data[0],
                    'owner': board_data[1],
                    'created_at': board_data[2],
                    'bid': bid,
                    'uname': board_data[3],
                    'owner': board_data[4]
                },
                'pins': pins
            }
            
            return render(request, 'view_board.html', context)
            
    except Exception as e:
        print(f"View Board error: {str(e)}")
        return redirect('dashboard')

def pin_view(request, pinid):
    try:
        with connection.cursor() as cursor:
            current_user = request.session.get('username', '')
            
            # Get pin details
            cursor.execute("""
                SELECT p.pinid, pic.img_data, pic.src_url, p.created_at,
                       b.bid, b.name AS board_name, u.uname, u.personal_name,
                       COUNT(l.org_pinid) AS like_count,
                       array_agg(t.tname) AS tags,
                       EXISTS(SELECT 1 FROM "Like" 
                              WHERE org_pinid = p.pinid 
                              AND uname = %s) AS liked
                FROM pin p
                JOIN picture pic ON p.picid = pic.picid
                JOIN board b ON p.bid = b.bid
                JOIN "User" u ON p.uname = u.uname
                LEFT JOIN "Like" l ON p.pinid = l.org_pinid
                LEFT JOIN picturetag pt ON pic.picid = pt.picid
                LEFT JOIN tag t ON pt.tname = t.tname
                WHERE p.pinid = %s
                GROUP BY p.pinid, pic.picid, b.bid, u.uname
            """, [current_user, pinid])
            
            pin_data = cursor.fetchone()
            if not pin_data:
                return redirect('dashboard')

            # Get comments with ownership info
            cursor.execute("""
                SELECT c.cid, c.content, c.created_at, 
                       u.personal_name, c.uname, b.uname as board_owner
                FROM "Comment" c
                JOIN "User" u ON c.uname = u.uname
                JOIN pin p ON c.pinid = p.pinid
                JOIN board b ON p.bid = b.bid
                WHERE c.pinid = %s
                ORDER BY c.created_at DESC
            """, [pinid])
            
            columns = [col[0] for col in cursor.description]
            comments = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            context = {
                'pin': {
                    'id': pin_data[0],
                    'img_data': base64.b64encode(pin_data[1]).decode('utf-8'),
                    'src_url': pin_data[2],
                    'created_at': pin_data[3],
                    'board': {
                        'id': pin_data[4],
                        'name': pin_data[5]
                    },
                    'author': {
                        'username': pin_data[6],
                        'name': pin_data[7]
                    },
                    'like_count': pin_data[8],
                    'tags': pin_data[9] if pin_data[9] else [],
                    'liked': pin_data[10]
                },
                'comments': comments,
                'current_user': current_user
            }
            
            return render(request, 'view_pin.html', context)
            
    except Exception as e:
        messages.error(request, f"Error loading pin: {str(e)}")
        return redirect('dashboard')

def like_pin(request, pinid):
    if 'username' not in request.session:
        return redirect('login')
    
    try:
        with connection.cursor() as cursor:
            username = request.session['username']
            cursor.execute("""
                INSERT INTO "Like" (uname, org_pinid)
                VALUES (%s, %s)
                ON CONFLICT (uname, org_pinid) DO NOTHING
            """, [username, pinid])
            
            if cursor.rowcount == 0:
                cursor.execute("""
                    DELETE FROM "Like" 
                    WHERE uname = %s AND org_pinid = %s
                """, [username, pinid])
            
            return redirect('view_pin', pinid=pinid)
            
    except Exception as e:
        return redirect('view_pin', pinid=pinid)

def comment_pin(request, pinid):
    if 'username' not in request.session:
        return redirect('login')
    
    if request.method == 'POST':
        username = request.session['username']
        content = request.POST.get('content', '').strip()
        
        if not content:
            messages.error(request, "Comment cannot be empty")
            return redirect('view_pin', pinid=pinid)
        
        try:
            with connection.cursor() as cursor:
                # Check comment permissions: owner can always comment
                cursor.execute("""
                    SELECT 1 FROM pin p
                    JOIN board b ON p.bid = b.bid
                    WHERE p.pinid = %s
                    AND (
                        p.uname = %s  -- Pin owner can always comment
                        OR b.comment_perms = 'public'
                        OR (
                            b.comment_perms = 'friends'
                            AND EXISTS(
                                SELECT 1 FROM friend
                                WHERE (uname1 = b.uname AND uname2 = %s)
                                   OR (uname2 = b.uname AND uname1 = %s)
                            )
                        )
                    )
                """, [pinid, username, username, username])
                
                if not cursor.fetchone():
                    messages.error(request, "You don't have permission to comment here")
                    return redirect('view_pin', pinid=pinid)
                
                # Insert comment
                cursor.execute("""
                    INSERT INTO "Comment" (uname, pinid, content)
                    VALUES (%s, %s, %s)
                """, [username, pinid, content])
                
                messages.success(request, "Comment added successfully")
                return redirect('view_pin', pinid=pinid)
                
        except Exception as e:
            messages.error(request, f"Error posting comment: {str(e)}")
            return redirect('view_pin', pinid=pinid)
    
    return redirect('view_pin', pinid=pinid)

def delete_comment(request, cid):
    if 'username' not in request.session:
        return redirect('login')
    
    try:
        with connection.cursor() as cursor:
            #username = request.session['username']
            
            # Get comment ownership info
            cursor.execute("""
                SELECT c.uname, b.uname, c.pinid
                FROM "Comment" c
                JOIN pin p ON c.pinid = p.pinid
                JOIN board b ON p.bid = b.bid
                WHERE c.cid = %s
            """, [cid])
            
            result = cursor.fetchone()
            if not result:
                messages.error(request, "Comment not found")
            
            comment_author, board_owner, pinid = result
            current_user = request.session['username']
            
            # Check permissions
            if current_user not in [comment_author, board_owner]:
                messages.error(request, "Permission denied")
            
            # Delete comment
            cursor.execute("""
                DELETE FROM "Comment" 
                WHERE cid = %s
            """, [cid])
            
            messages.success(request, "Comment deleted successfully")
            
    except Exception as e:
        messages.error(request, f"Error deleting comment: {str(e)}")
    
    return redirect('view_pin', pinid=pinid)

def search_view(request):
    if 'username' not in request.session:
        return redirect('login')
    
    query = request.GET.get('q', '').strip()
    context = {'query': query}
    
    if query:
        try:
            # Search Users
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT uname, personal_name, created_at 
                    FROM "User"
                    WHERE uname ILIKE %s OR personal_name ILIKE %s
                    LIMIT 10
                """, [f'%{query}%', f'%{query}%'])
                context['users'] = [
                    dict(zip([col[0] for col in cursor.description], row))
                    for row in cursor.fetchall()
                ]

            # Search Boards
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT bid, name, created_at, uname 
                    FROM board 
                    WHERE name ILIKE %s
                    ORDER BY created_at DESC
                    LIMIT 12
                """, [f'%{query}%'])
                context['boards'] = [
                    dict(zip([col[0] for col in cursor.description], row))
                    for row in cursor.fetchall()
                ]

        except Exception as e:
            messages.error(request, f"Search error: {str(e)}")
    
    return render(request, 'search_results.html', context)

def user_profile_view(request, username):
    if 'username' not in request.session:
        return redirect('login')
    
    context = {}
    viewer = request.session['username']
    try:
        # Get profile user details
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT uname, personal_name, email, created_at 
                FROM "User" 
                WHERE uname = %s
            """, [username])
            profile_user = cursor.fetchone()
            
        if not profile_user:
            raise Http404("User not found")

        context['profile_user'] = {
            'uname': profile_user[0],
            'personal_name': profile_user[1],
            'email': profile_user[2],
            'join_date': profile_user[3]
        }

        # Get user's boards
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT bid, name, comment_perms, created_at 
                FROM board 
                WHERE uname = %s 
                ORDER BY created_at DESC
            """, [username])
            columns = [col[0] for col in cursor.description]
            context['boards'] = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Get friends list if viewing own profile
        if viewer == username:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT CASE
                        WHEN f.uname1 = %s THEN f.uname2
                        ELSE f.uname1
                        END AS friend_uname,
                        u.personal_name
                    FROM Friend f
                    JOIN "User" u ON 
                        (f.uname1 = u.uname OR f.uname2 = u.uname)
                        AND u.uname != %s
                    WHERE %s IN (f.uname1, f.uname2)
                    ORDER BY u.personal_name
                """, [username, username, username])
                columns = [col[0] for col in cursor.description]
                context['friends'] = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Check friend status if not viewing own profile
        if viewer != username:
            with connection.cursor() as cursor:
                # Check friendship
                uname1, uname2 = sorted([viewer, username])
                cursor.execute("""
                    SELECT 1 FROM Friend
                    WHERE uname1 = %s AND uname2 = %s
                """, [uname1, uname2])
                is_friend = cursor.fetchone() is not None

                if is_friend:
                    context['friend_status'] = 'accepted'
                else:
                    # Check pending requests
                    cursor.execute("""
                        SELECT status FROM friendrequest 
                        WHERE (sender_uname = %s AND receiver_uname = %s)
                           OR (sender_uname = %s AND receiver_uname = %s)
                        ORDER BY sent_at DESC 
                        LIMIT 1
                    """, [viewer, username, username, viewer])
                    friend_request = cursor.fetchone()
                    context['friend_status'] = friend_request[0] if friend_request else None

        else:
            # Get incoming friend requests for own profile
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT sender_uname, sent_at 
                    FROM FriendRequest 
                    WHERE receiver_uname = %s AND status = 'pending'
                """, [username])
                columns = [col[0] for col in cursor.description]
                context['incoming_requests'] = [dict(zip(columns, row)) for row in cursor.fetchall()]

    except Exception as e:
        messages.error(request, f"Error loading profile: {str(e)}")
        print(f"Error loading profile: {str(e)}")
        return redirect('dashboard')

    return render(request, 'user_profile.html', context)

def send_friend_request(request, username):
    if 'username' not in request.session:
        return redirect('login')
    
    sender = request.session['username']
    receiver = username

    if sender == receiver:
        messages.error(request, "You cannot send a friend request to yourself.")
        return redirect('user_profile', username=username)

    try:
        with connection.cursor() as cursor:
            # Check if request already exists
            cursor.execute("""
                SELECT status FROM friendrequest 
                WHERE (sender_uname = %s AND receiver_uname = %s)
                   OR (sender_uname = %s AND receiver_uname = %s)
            """, [sender, receiver, receiver, sender])
            
            existing = cursor.fetchone()
            if existing:
                if existing[0] == 'pending':
                    messages.info(request, "Friend request already pending.")
                elif existing[0] == 'accepted':
                    messages.info(request, "You are already friends.")
                return redirect('user_profile', username=username)

            # Create new request
            cursor.execute("""
                INSERT INTO friendrequest (sender_uname, receiver_uname, status, sent_at)
                VALUES (%s, %s, 'pending', NOW())
            """, [sender, receiver])
            
            messages.success(request, "Friend request sent successfully!")

    except Exception as e:
        print(f"Error sending friend request: {str(e)}")
        messages.error(request, f"Error sending friend request: {str(e)}")

    return redirect('user_profile', username=username)

def handle_friend_request(request, username, action):
    if 'username' not in request.session:
        return redirect('login')
    
    receiver = request.session['username']
    sender = username

    if action not in ['accept', 'reject']:
        messages.error(request, "Invalid action")
        return redirect('user_profile', username=receiver)

    try:
        with connection.cursor() as cursor:
            # Update friend request status
            cursor.execute("""
                UPDATE friendrequest
                SET status = %s
                WHERE sender_uname = %s AND receiver_uname = %s
                AND status = 'pending'
            """, ['accepted' if action == 'accept' else 'rejected', sender, receiver])

            if action == 'accept':
                # Determine alphabetical order for friend pair
                uname1, uname2 = sorted([sender, receiver])
                # Add friendship relation
                cursor.execute("""
                    INSERT INTO Friend (uname1, uname2)
                    VALUES (%s, %s)
                    ON CONFLICT (uname1, uname2) DO NOTHING
                """, [uname1, uname2])

            messages.success(request, f"Friend request {action}ed successfully!")

    except Exception as e:
        messages.error(request, f"Error processing request: {str(e)}")

    return redirect('user_profile', username=receiver)

# TODO Fix duplicate likes issue (also duplicates tags)

# TODO browse liked pins
# TODO follow streams
# TODO friend requests
# TODO see friends list
# TODO implement repinning

# TODO integrate models into the django admin panel