from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
from .utils import detect_anomalies, process_csv
from app.models import EnergyRecord

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import make_response
from flask import request
from collections import defaultdict

from flask import Response
import csv
from io import StringIO

from flask import make_response, render_template_string
from datetime import datetime

main = Blueprint('main', __name__)

UPLOAD_FOLDER = 'data/'
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
from datetime import datetime

@main.route('/')
def index():
    selected_meter = request.args.get('meter')
    start_date = request.args.get('start')
    end_date = request.args.get('end')

    # Get all records ordered by date
    all_records = EnergyRecord.query.order_by(EnergyRecord.date).all()

    # Get distinct meter numbers
    meter_numbers = sorted(set(r.meter_no for r in all_records))

    # Filter by selected meter
    if selected_meter:
        filtered_records = [r for r in all_records if r.meter_no == selected_meter]
    else:
        filtered_records = all_records

    # Filter by date range (convert r.date to datetime safely)
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            filtered_records = [
                r for r in filtered_records
                if start <= datetime.strptime(str(r.date), "%Y-%m-%d") <= end
            ]
        except ValueError:
            flash("Invalid date format.", "danger")

    records = filtered_records

    # Prepare graph data
    dates = [r.date for r in records]
    units = [r.units_received for r in records]
    tokens = [r.token_amount for r in records]

    # Totals
    total_units = sum(units)
    total_tokens = sum(tokens)
    avg_efficiency = total_units / total_tokens if total_tokens else 0

    # Meter breakdown
    from collections import defaultdict
    meter_breakdown = defaultdict(lambda: {"tokens": 0, "units": 0, "count": 0})
    for r in all_records:
        m = meter_breakdown[r.meter_no]
        m["tokens"] += r.token_amount
        m["units"] += r.units_received
        m["count"] += 1

    # Anomalies
    anomalies = detect_anomalies(records)

    return render_template(
        "index.html",
        records=records,
        anomalies=anomalies,
        dates=dates,
        units=units,
        tokens=tokens,
        total_units=total_units,
        total_tokens=total_tokens,
        avg_efficiency=avg_efficiency,
        meter_numbers=meter_numbers,
        selected_meter=selected_meter,
        start_date=start_date,
        end_date=end_date,
        meter_breakdown=meter_breakdown
    )

@main.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'warning')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            success = process_csv(filepath)
            if success:
                flash('File uploaded and processed successfully!', 'success')
            else:
                flash('File uploaded but processing failed.', 'danger')
            return redirect(url_for('main.upload'))
        else:
            flash('Invalid file format. Please upload a CSV.', 'danger')
            return redirect(request.url)
    return render_template('upload.html')

@main.route('/export')
def export_csv():
    import io
    import csv
    from flask import make_response

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Date', 'Token (ZMW)', 'Units Received (kWh)', 'Meter No.'])
    records = EnergyRecord.query.order_by(EnergyRecord.date).all()

    for record in records:
        writer.writerow([record.date, record.token_amount, record.units_received, record.meter_no])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=zesco_report.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@main.route('/export_pdf')
def export_pdf():
    records = EnergyRecord.query.order_by(EnergyRecord.date).all()

    # Create a file-like buffer to receive PDF data
    from io import BytesIO
    buffer = BytesIO()

    # Create the PDF object, using the buffer as its "file."
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, height - 50, "ZESCO Energy Usage Report")

    # Table header
    p.setFont("Helvetica-Bold", 12)
    y = height - 80
    p.drawString(40, y, "Date")
    p.drawString(120, y, "Token (ZMW)")
    p.drawString(240, y, "Units (kWh)")
    p.drawString(360, y, "Meter No.")
    y -= 20

    # Table rows
    p.setFont("Helvetica", 10)
    for record in records:
        p.drawString(40, y, record.date)
        p.drawString(120, y, f"{record.token_amount:.2f}")
        p.drawString(240, y, f"{record.units_received:.2f}")
        p.drawString(360, y, record.meter_no)
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50

    p.save()

    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Disposition'] = 'attachment; filename=zesco_report.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response


from flask import request, Response
from io import StringIO
import csv
from datetime import datetime
from app.models import EnergyRecord
from app.utils import detect_anomalies  # or your actual path

@main.route('/export_anomalies_csv')
def export_anomalies_csv():
    selected_meter = request.args.get('meter')
    start_date = request.args.get('start')
    end_date = request.args.get('end')

    # --- Step 1: Query + filter data ---
    records = EnergyRecord.query.order_by(EnergyRecord.date).all()

    if selected_meter:
        records = [r for r in records if r.meter_no == selected_meter]

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            records = [r for r in records if start <= datetime.strptime(str(r.date), "%Y-%m-%d") <= end]
        except ValueError:
            pass  # ignore invalid date format

    # --- Step 2: Detect anomalies ---
    anomalies = detect_anomalies(records)

    # --- Step 3: Create CSV ---
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date', 'Meter No.', 'Token (ZMW)', 'Units Received', 'Reason'])

    for a in anomalies:
        cw.writerow([
            a['date'],
            a['meter_no'],
            a['token_amount'],
            a['units_received'],
            a['reason']
        ])

    output = si.getvalue()

    today = datetime.now().strftime("%Y-%m-%d")
    return Response(
        output,
        mimetype='text/csv',
        headers={
            "Content-Disposition": f"attachment; filename=anomaly_report_{today}.csv"
        }
    )


from flask import request, send_file
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO
import matplotlib.pyplot as plt
from collections import Counter
from datetime import datetime
import os
from app.models import EnergyRecord  # Make sure this is your model

@main.route('/export_anomalies_pdf')
def export_anomalies_pdf():
    selected_meter = request.args.get('meter')
    start_date = request.args.get('start')
    end_date = request.args.get('end')

    # --- Step 1: Query + filter data ---
    records = EnergyRecord.query.order_by(EnergyRecord.date).all()

    if selected_meter:
        records = [r for r in records if r.meter_no == selected_meter]

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            records = [r for r in records if start <= datetime.strptime(str(r.date), "%Y-%m-%d") <= end]
        except ValueError:
            pass  # ignore invalid date format

    # --- Step 2: Detect anomalies ---
    anomalies = detect_anomalies(records)
    today = datetime.now().strftime("%Y-%m-%d")

    # --- Step 3: Prepare PDF ---
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Logo (if available)
    logo_path = os.path.join("app", "static", "zesco_logo.png")
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=120, height=40))
        elements.append(Spacer(1, 12))

    # Header
    elements.append(Paragraph("⚠️ ZESCO Anomaly Report", styles['Title']))
    elements.append(Paragraph(f"Generated on: {today}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Pie chart of anomaly types
    if anomalies:
        reason_counts = Counter(a["reason"] for a in anomalies)
        labels = list(reason_counts.keys())
        sizes = list(reason_counts.values())

        plt.figure(figsize=(4, 4))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.axis("equal")
        pie_chart_path = os.path.join("app", "static", "anomaly_pie.png")
        plt.savefig(pie_chart_path, bbox_inches='tight')
        plt.close()
        elements.append(Image(pie_chart_path, width=200, height=200))
        elements.append(Spacer(1, 12))

    # Anomalies Table
    if anomalies:
        table_data = [["Date", "Meter No.", "Token (ZMW)", "Units", "Reason"]]
        for a in anomalies:
            table_data.append([
                a["date"], a["meter_no"], a["token_amount"],
                a["units_received"], a["reason"]
            ])
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("✅ No anomalies detected for the selected filters.", styles['Normal']))

    doc.build(elements)

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'anomaly_report_{today}.pdf',
        mimetype='application/pdf'
    )
