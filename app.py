from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string

app = Flask(__name__)  # <-- correct: __name__ (with double underscores)

app.secret_key = 'your_secret_key'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'sai1639'
app.config['MYSQL_DB'] = 'Railway_Management_System'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

def generate_pnr():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

@app.route('/')
def home():
    if session.get('admin_loggedin'):
        return redirect(url_for('admin_dashboard'))
    elif session.get('user_loggedin'):
        return redirect(url_for('user_portal'))
    else:
        return redirect(url_for('user_login'))

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == "admin" and password == "admin1234":
            session['admin_loggedin'] = True
            session['adminname'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            msg = 'Incorrect username or password!'
    return render_template('admin_login.html', msg=msg)

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_loggedin'):
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html', adminname=session['adminname'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/user_register', methods=['GET', 'POST'])
def user_register():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        mobile = request.form['mobile']
        email = request.form['email']
        password = request.form['password']
        dob = request.form['dob']
        gender = request.form['gender']
        hashed_password = generate_password_hash(password)
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM User WHERE UserEmail = %s', (email,))
        existing_user = cur.fetchone()
        if existing_user:
            msg = 'User with this email already exists!'
        else:
            cur.execute(
                'INSERT INTO User (UserName, UserMobile, UserEmail, Password, DateOfBirth, Gender) VALUES (%s, %s, %s, %s, %s, %s)',
                (username, mobile, email, hashed_password, dob, gender)
            )
            mysql.connection.commit()
            msg = 'Registration successful! You can now login.'
        cur.close()
    return render_template('user_register.html', msg=msg)

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute('SELECT * FROM User WHERE UserEmail = %s', (email,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user['Password'], password):
            session['user_loggedin'] = True
            session['userid'] = user['UserID']
            session['username'] = user['UserName']
            session['user_email'] = user['UserEmail']
            session['full_name'] = user['UserName']
            session['age'] = user.get('Age', '') if 'Age' in user else ''
            session['gender'] = user.get('Gender', '') if 'Gender' in user else ''
            return redirect(url_for('user_portal'))
        else:
            msg = 'Incorrect email or password!'
    return render_template('user_login.html', msg=msg)

@app.route('/user_portal')
def user_portal():
    if not session.get('user_loggedin'):
        return redirect(url_for('user_login'))
    email = session.get('user_email', '')
    return render_template('user_portal.html', username=session['username'], email=email)

@app.route('/logout_user')
def logout_user():
    session.clear()
    return redirect(url_for('user_login'))

@app.route('/train_info', methods=['GET', 'POST'])
def train_info():
    if not session.get('admin_loggedin'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST' and 'add_train' in request.form:
        train_no = request.form['train_no']
        train_name = request.form['train_name']
        train_type = request.form['train_type']
        total_seats = request.form['total_seats']
        ac_seats = request.form['ac_seats']
        sleeper_seats = request.form['sleeper_seats']
        general_seats = request.form['general_seats']
        cur = mysql.connection.cursor()
        cur.execute('INSERT INTO Train (TrainNumber, TrainName, TrainType, TotalSeats, AC_Seats, Sleeper_Seats, General_Seats) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (train_no, train_name, train_type, total_seats, ac_seats, sleeper_seats, general_seats))
        mysql.connection.commit()
        flash('Train added successfully!', 'success')
        cur.close()
        return redirect(url_for('train_info'))
    if request.method == 'POST' and 'delete_train' in request.form:
        train_id = request.form['train_id']
        cur = mysql.connection.cursor()
        cur.execute('DELETE FROM Train WHERE TrainID = %s', (train_id,))
        mysql.connection.commit()
        flash('Train removed successfully!', 'success')
        cur.close()
        return redirect(url_for('train_info'))
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM Train')
    train_list = cur.fetchall()
    cur.close()
    return render_template('train_info.html', trains=train_list)

@app.route('/routes')
def routes():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT r.RouteID, r.RouteName, t.TrainNumber, t.TrainName, t.TrainType
        FROM Route r
        JOIN Train t ON r.TrainID = t.TrainID
    """)
    route_rows = cur.fetchall()
    routes = []
    for route in route_rows:
        cur.execute("""
            SELECT rs.SequenceNumber, s.StationName, rs.ArrivalTime, rs.DepartureTime, rs.HaltDuration, rs.DistanceFromOrigin
            FROM RouteStation rs
            JOIN Station s ON rs.StationID = s.StationID
            WHERE rs.RouteID = %s
            ORDER BY rs.SequenceNumber
        """, (route['RouteID'],))
        station_schedule = cur.fetchall()
        route['stations'] = station_schedule
        routes.append(route)
    cur.close()
    return render_template('routes.html', routes=routes)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if not session.get('user_loggedin'):
        return redirect(url_for('user_login'))

    train_results = []
    from_station = ''
    to_station = ''
    journey_date = ''

    cur = mysql.connection.cursor()
    cur.execute('SELECT StationName FROM Station ORDER BY StationName')
    station_list = cur.fetchall()

    if request.method == 'POST':
        if 'confirm_booking' not in request.form:
            from_station = request.form['from_station']
            to_station = request.form['to_station']
            journey_date = request.form['journey_date']

            query = '''
                SELECT t.TrainID, t.TrainNumber, t.TrainName, t.TrainType,
                       t.TotalSeats, t.AC_Seats, t.Sleeper_Seats, t.General_Seats
                FROM Train t
                JOIN Route r ON r.TrainID = t.TrainID
                JOIN RouteStation rs_from ON rs_from.RouteID = r.RouteID
                JOIN RouteStation rs_to ON rs_to.RouteID = r.RouteID
                WHERE rs_from.StationID = (SELECT StationID FROM Station WHERE StationName = %s)
                  AND rs_to.StationID = (SELECT StationID FROM Station WHERE StationName = %s)
                  AND rs_from.SequenceNumber < rs_to.SequenceNumber
            '''
            cur.execute(query, (from_station, to_station))
            train_results = cur.fetchall()

        elif 'confirm_booking' in request.form:
            train_id = request.form['train_id']
            from_station = request.form['from_station']
            to_station = request.form['to_station']
            journey_date = request.form['journey_date']
            ticket_class = request.form['ticket_class']
            user_id = session['userid']

            cur.execute('''
                SELECT r.RouteID
                FROM Route r
                JOIN RouteStation rs_from ON rs_from.RouteID = r.RouteID
                JOIN RouteStation rs_to ON rs_to.RouteID = r.RouteID
                WHERE r.TrainID = %s
                  AND rs_from.StationID = (SELECT StationID FROM Station WHERE StationName = %s)
                  AND rs_to.StationID = (SELECT StationID FROM Station WHERE StationName = %s)
                  AND rs_from.SequenceNumber < rs_to.SequenceNumber
                LIMIT 1
            ''', (train_id, from_station, to_station))
            route_row = cur.fetchone()
            if not route_row:
                flash("Booking route not found!", "danger")
                cur.close()
                return redirect(url_for('booking'))
            route_id = route_row['RouteID']

            if ticket_class == 'AC':
                total_fare = 2000
            elif ticket_class == 'Sleeper':
                total_fare = 1200
            else:
                total_fare = 800

            session['pending_booking'] = {
                'train_id': train_id,
                'from_station': from_station,
                'to_station': to_station,
                'journey_date': journey_date,
                'ticket_class': ticket_class,
                'total_fare': total_fare,
                'route_id': route_id
            }
            cur.close()
            return redirect(url_for('payment'))

    cur.close()
    return render_template('booking.html',
                           station_list=station_list,
                           train_results=train_results,
                           from_station=from_station,
                           to_station=to_station,
                           journey_date=journey_date)

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if not session.get('user_loggedin'):
        return redirect(url_for('user_login'))
    booking = session.get('pending_booking')
    if not booking:
        flash("No pending booking found. Start again.", "danger")
        return redirect(url_for('booking'))

    if request.method == 'POST' and 'pay_now' in request.form:
        train_id = booking['train_id']
        from_station = booking['from_station']
        to_station = booking['to_station']
        journey_date = booking['journey_date']
        ticket_class = booking['ticket_class']
        total_fare = booking['total_fare']
        route_id = booking['route_id']
        user_id = session['userid']
        pnr = generate_pnr()

        if ticket_class == 'AC':
            seat_col = 'AC_Seats'
        elif ticket_class == 'Sleeper':
            seat_col = 'Sleeper_Seats'
        else:
            seat_col = 'General_Seats'

        cur = mysql.connection.cursor()
        cur.execute(f"SELECT {seat_col} FROM Train WHERE TrainID = %s", (train_id,))
        result = cur.fetchone()
        if result[seat_col] <= 0:
            flash(f"No {ticket_class} seats available on payment attempt!", "danger")
            cur.close()
            session.pop('pending_booking', None)
            return redirect(url_for('booking'))
        cur.execute(f"UPDATE Train SET {seat_col} = {seat_col} - 1 WHERE TrainID = %s", (train_id,))
        cur.execute('''
            INSERT INTO Booking (PNR_Number, JourneyDate, TotalFare, BookingStatus, PaymentStatus, UserID, TrainID, RouteID, TicketClass)
            VALUES (%s, %s, %s, 'Confirmed', 'Completed', %s, %s, %s, %s)
        ''', (pnr, journey_date, total_fare, user_id, train_id, route_id, ticket_class))
        mysql.connection.commit()
        cur.close()
        session.pop('pending_booking', None)
        flash(f'Payment successful! PNR: {pnr} | Class: {ticket_class} | Fare: {total_fare}', 'success')
        return redirect(url_for('previous_bookings'))

    return render_template('payment.html', booking=booking)

@app.route('/profile')
def profile():
    if not session.get('user_loggedin'):
        return redirect(url_for('user_login'))
    user_id = session['userid']
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT UserName, UserEmail, UserMobile, DateOfBirth, Gender
        FROM User
        WHERE UserID = %s
    """, (user_id,))
    user = cur.fetchone()
    cur.close()
    return render_template('profile.html', user=user)

@app.route('/previous_bookings')
def previous_bookings():
    if not session.get('user_loggedin'):
        return redirect(url_for('user_login'))
    user_id = session['userid']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.PNR_Number, b.JourneyDate, t.TrainName, t.TrainNumber, b.BookingStatus, b.TotalFare, b.TicketClass
        FROM Booking b
        JOIN Train t ON b.TrainID = t.TrainID
        WHERE b.UserID = %s
        ORDER BY b.BookingDate DESC
    """, (user_id,))
    bookings = cur.fetchall()
    cur.close()
    return render_template('previous_bookings.html', bookings=bookings)

@app.route('/cancel_ticket', methods=['GET', 'POST'])
def cancel_ticket():
    msg = ''
    if request.method == 'POST':
        pnr_number = request.form['pnr_number']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Booking WHERE PNR_Number = %s AND BookingStatus != 'Cancelled'", (pnr_number,))
        booking = cur.fetchone()
        if not booking:
            msg = "Invalid or already cancelled PNR. Please check the number."
        else:
            seat_col = ''
            if booking['TicketClass'] == 'AC':
                seat_col = 'AC_Seats'
            elif booking['TicketClass'] == 'Sleeper':
                seat_col = 'Sleeper_Seats'
            else:
                seat_col = 'General_Seats'
            cur.execute(f"UPDATE Train SET {seat_col} = {seat_col} + 1 WHERE TrainID = %s", (booking['TrainID'],))
            cur.execute("UPDATE Booking SET BookingStatus = 'Cancelled' WHERE PNR_Number = %s", (pnr_number,))
            mysql.connection.commit()
            msg = "Ticket cancelled successfully."
        cur.close()
    return render_template('cancel_ticket.html', msg=msg)

@app.route('/pnr_status', methods=['GET', 'POST'])
def pnr_status():
    booking = None
    msg = ''
    if request.method == 'POST':
        pnr_number = request.form['pnr_number']
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""
            SELECT b.*, t.TrainName, t.TrainNumber,
              (SELECT s1.StationName FROM RouteStation rs1 JOIN Station s1 ON s1.StationID=rs1.StationID WHERE rs1.RouteID = b.RouteID ORDER BY rs1.SequenceNumber ASC LIMIT 1) AS FromStation,
              (SELECT s2.StationName FROM RouteStation rs2 JOIN Station s2 ON s2.StationID=rs2.StationID WHERE rs2.RouteID = b.RouteID ORDER BY rs2.SequenceNumber DESC LIMIT 1) AS ToStation
            FROM Booking b
            JOIN Train t ON b.TrainID = t.TrainID
            WHERE b.PNR_Number = %s
        """, (pnr_number,))
        booking = cur.fetchone()
        cur.close()
        if not booking:
            msg = "No booking found for this PNR."
    return render_template('pnr_status.html', booking=booking, msg=msg)

@app.route('/feedback_user', methods=['GET', 'POST'])
def feedback_user():
    msg = ''
    if not session.get('user_loggedin'):
        return redirect(url_for('user_login'))
    if request.method == 'POST':
        subject = request.form['subject']
        message = request.form['message']
        user_id = session['userid']
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO Feedback (UserID, Subject, Message)
            VALUES (%s, %s, %s)
        """, (user_id, subject, message))
        mysql.connection.commit()
        cur.close()
        msg = 'Thank you for your feedback!'
    return render_template('feedback_user.html', msg=msg)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if not session.get('admin_loggedin'):
        return redirect(url_for('admin_login'))
    msg = ''
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        feedback_id = request.form['feedback_id']
        new_status = request.form['status']
        cur.execute("UPDATE Feedback SET Status = %s WHERE FeedbackID = %s", (new_status, feedback_id))
        mysql.connection.commit()
        msg = 'Status updated.'
    cur.execute("""
        SELECT f.FeedbackID, f.Subject, f.Message, f.SubmissionDate, f.Status, u.UserName
        FROM Feedback f
        LEFT JOIN User u ON f.UserID = u.UserID
        ORDER BY f.SubmissionDate DESC
    """)
    feedbacks = cur.fetchall()
    cur.close()
    return render_template('feedback.html', feedbacks=feedbacks, msg=msg)

@app.route('/food_order', methods=['GET', 'POST'])
def food_order():
    if not session.get('user_loggedin'):
        return redirect(url_for('user_login'))
    msg = ''
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM Menu")
    menu_items = cur.fetchall()
    if request.method == 'POST':
        food_item = request.form['food_item']
        quantity = int(request.form['quantity'])
        cur.execute("SELECT Price FROM Menu WHERE FoodItem = %s", (food_item,))
        price_row = cur.fetchone()
        if price_row:
            total_amount = price_row['Price'] * quantity
            # Insert as Pending
            cur.execute("""
                INSERT INTO FoodOrder (UserID, FoodItem, Quantity, TotalAmount, Status)
                VALUES (%s, %s, %s, %s, 'Pending')
            """, (session['userid'], food_item, quantity, total_amount))
            order_id = cur.lastrowid
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('pay_food_order', order_id=order_id))
        else:
            msg = "Item not found!"
    cur.close()
    return render_template('food_order.html', menu_items=menu_items, msg=msg)
@app.route('/pay_food_order/<int:order_id>', methods=['GET', 'POST'])
def pay_food_order(order_id):
    if not session.get('user_loggedin'):
        return redirect(url_for('user_login'))
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM FoodOrder WHERE OrderID=%s AND UserID=%s", (order_id, session['userid']))
    order = cur.fetchone()
    if not order or order['Status'] == 'Completed':
        cur.close()
        return redirect(url_for('food_order'))
    if request.method == 'POST':
        payment_method = request.form['payment_method']
        cur.execute("UPDATE FoodOrder SET Status='Completed' WHERE OrderID=%s", (order_id,))
        mysql.connection.commit()
        cur.close()
        return render_template('pay_food_order_success.html', order=order)
    cur.close()
    return render_template('pay_food_order.html', order=order)


@app.route('/help_user')
def help_user():
    return render_template('help_user.html')

@app.route('/payment_history')
def payment_history():
    if not session.get('user_loggedin'):
        return redirect(url_for('user_login'))
    user_id = session['userid']
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT PNR_Number, BookingDate, JourneyDate, TotalFare, PaymentStatus, BookingStatus
        FROM Booking
        WHERE UserID = %s AND PaymentStatus = 'Completed'
        ORDER BY BookingDate DESC
    """, (user_id,))
    payments = cur.fetchall()
    cur.close()
    return render_template('payment_history.html', payments=payments)


@app.route('/passenger_info')
def passenger_info():
    if not session.get('admin_loggedin'):
        return redirect(url_for('admin_login'))
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT 
            u.UserID, u.UserName, u.UserEmail, u.UserMobile, u.DateOfBirth, u.Gender,
            COUNT(DISTINCT b.TrainID) AS NumTrainsBooked,
            COUNT(b.BookingID) AS TotalBookings
        FROM User u
        LEFT JOIN Booking b ON b.UserID = u.UserID
        GROUP BY u.UserID
    """)
    passengers = cur.fetchall()
    cur.close()
    return render_template('passenger_info.html', passengers=passengers)

@app.route('/delete_passenger/<int:userid>', methods=['POST'])
def delete_passenger(userid):
    if not session.get('admin_loggedin'):
        return redirect(url_for('admin_login'))
    cur = mysql.connection.cursor()
    # Consider deleting from Booking, FoodOrder, etc. if needed for referential integrity
    cur.execute("DELETE FROM User WHERE UserID = %s", (userid,))
    mysql.connection.commit()
    cur.close()
    flash('Passenger deleted successfully.', 'success')
    return redirect(url_for('passenger_info'))


@app.route('/crew_management', methods=['GET', 'POST'])
def crew_management():
    if not session.get('admin_loggedin'):
        return redirect(url_for('admin_login'))
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    msg = ''
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        phone = request.form['phone']
        gender = request.form['gender']
        cur.execute(
            "INSERT INTO Crew(Name, Role, Gender, Phone) VALUES (%s, %s, %s, %s)",
            (name, role, gender, phone)
        )
        mysql.connection.commit()
        msg = 'Crew member added.'
    cur.execute("SELECT * FROM Crew")
    crew_list = cur.fetchall()
    cur.close()
    return render_template('crew_management.html', crew=crew_list, msg=msg)

@app.route('/delete_crew/<int:crewid>', methods=['POST'])
def delete_crew(crewid):
    if not session.get('admin_loggedin'):
        return redirect(url_for('admin_login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM Crew WHERE CrewID=%s", (crewid,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('crew_management'))

@app.route('/call_center')
def call_center():
    return render_template('call_center.html')

@app.route('/station_master')
def station_master():
    # For a real system, you would restrict this route to logged-in station master accounts!
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Example: show all trains arriving today at this station, say with StationID = 1
    cur.execute("""
        SELECT t.TrainNumber, t.TrainName, rs.ArrivalTime, rs.DepartureTime, rs.Platform, r.RouteName
        FROM RouteStation rs
        JOIN Route r ON r.RouteID = rs.RouteID
        JOIN Train t ON t.TrainID = r.TrainID
        WHERE rs.StationID = %s
        ORDER BY rs.ArrivalTime
    """, (1,))  # Replace '1' with dynamic station id per user/session
    schedule = cur.fetchall()
    cur.close()
    return render_template('station_master.html', schedule=schedule)
@app.route('/ticket_inspector', methods=['GET', 'POST'])
def ticket_inspector():
    ticket_info = None
    msg = ''
    action_msg = ''
    if request.method == 'POST':
        # Inspector action: verify, check, or fine
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # Handle mark checked
        if 'mark_checked' in request.form:
            booking_id = int(request.form['booking_id'])
            inspector_id = 1  # <-- Replace this with logged-in crew id in real app
            issue_flagged = request.form.get('issue_flagged', '')
            cur.execute("""
                INSERT INTO InspectionLog (BookingID, InspectorID, IssueFlagged)
                VALUES (%s, %s, %s)
            """, (booking_id, inspector_id, issue_flagged))
            mysql.connection.commit()
            action_msg = f'Ticket marked as checked. Issue: {issue_flagged if issue_flagged else "None"}'
        # Handle issue fine
        elif 'issue_fine' in request.form:
            booking_id = int(request.form['booking_id'])
            inspector_id = 1  # <-- Replace with logged-in inspector ID
            fine_amount = float(request.form['fine_amount'])
            fine_reason = request.form['fine_reason']
            cur.execute("""
                INSERT INTO FineCollection (CollectedBy, Amount, Reason, RelatedBookingID)
                VALUES (%s, %s, %s, %s)
            """, (inspector_id, fine_amount, fine_reason, booking_id))
            mysql.connection.commit()
            action_msg = f'Fine of ₹{fine_amount:.2f} issued: {fine_reason}'
        # Ticket search
        else:
            pnr = request.form.get('pnr')
            if pnr:
                cur.execute("""
                    SELECT b.BookingID, b.PNR_Number, b.JourneyDate, b.TicketClass, b.BookingStatus, b.PaymentStatus,
                           u.UserName, t.TrainNumber, t.TrainName
                    FROM Booking b
                    JOIN User u ON b.UserID = u.UserID
                    JOIN Train t ON t.TrainID = b.TrainID
                    WHERE b.PNR_Number = %s
                """, (pnr,))
                ticket_info = cur.fetchone()
                if not ticket_info:
                    msg = "No record for this PNR."
            else:
                msg = 'Please provide a PNR.'
        cur.close()
    return render_template(
        'ticket_inspector.html', 
        ticket_info=ticket_info, 
        msg=msg,
        action_msg=action_msg
    )


@app.route('/catering')
def catering():
    if not session.get('admin_loggedin'):
        return redirect(url_for('admin_login'))
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT fo.OrderID, u.UserName, fo.FoodItem, fo.Quantity, fo.TotalAmount, fo.OrderDate, fo.Status
        FROM FoodOrder fo
        JOIN User u ON fo.UserID = u.UserID
        ORDER BY fo.OrderDate DESC
    """)
    orders = cur.fetchall()
    cur.close()
    return render_template('catering.html', orders=orders)

@app.route('/revenue_management')
def revenue_management():
    if not session.get('admin_loggedin'):
        return redirect(url_for('admin_login'))
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Total booking revenue
    cur.execute("SELECT SUM(TotalFare) AS BookingRevenue FROM Booking WHERE PaymentStatus='Completed'")
    booking_revenue = cur.fetchone()["BookingRevenue"] or 0
    # Total food order revenue
    cur.execute("SELECT SUM(TotalAmount) AS FoodRevenue FROM FoodOrder WHERE Status='Completed'")
    food_revenue = cur.fetchone()["FoodRevenue"] or 0
    # Total paid fines revenue
    cur.execute("SELECT SUM(Amount) AS FineRevenue FROM FineCollection WHERE PaymentStatus = 'Paid'")
    fine_revenue = cur.fetchone()["FineRevenue"] or 0
    cur.close()
    total_revenue = booking_revenue + food_revenue + fine_revenue
    return render_template(
        'revenue_management.html',
        booking_revenue=booking_revenue,
        food_revenue=food_revenue,
        fine_revenue=fine_revenue,
        total_revenue=total_revenue
    )

@app.route('/my_fines', methods=['GET', 'POST'])
def my_fines():
    if not session.get('user_loggedin'):
        return redirect(url_for('user_login'))
    user_id = session['userid']
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST' and 'pay_fine_id' in request.form:
        fine_id = int(request.form['pay_fine_id'])
        payment_method = request.form['payment_method']
        cur.execute("""
            UPDATE FineCollection
            SET PaymentStatus='Paid', PaymentMethod=%s
            WHERE FineID=%s
        """, (payment_method, fine_id))
        mysql.connection.commit()
    cur.execute("""
        SELECT f.FineID, f.DateCollected, f.Amount, f.Reason, f.PaymentStatus, f.PaymentMethod, b.PNR_Number
        FROM FineCollection f
        JOIN Booking b ON f.RelatedBookingID = b.BookingID
        WHERE b.UserID = %s
        ORDER BY f.DateCollected DESC
    """, (user_id,))
    fines = cur.fetchall()
    cur.close()
    return render_template('my_fines.html', fines=fines)

if __name__ == '__main__':
    app.run(debug=True)
