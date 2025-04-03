from flask import Flask, render_template_string, request
import re
import smtplib
import dns.resolver
import csv
import io
import threading
import webbrowser

app = Flask(__name__)

def is_valid_format(email):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email)

def get_mx_record(domain):
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        mx_records = sorted([(r.preference, str(r.exchange)) for r in answers], key=lambda x: x[0])
        return mx_records[0][1] if mx_records else None
    except:
        return None

def smtp_check(email, from_email='verify@example.com'):
    if not is_valid_format(email):
        return 'Invalid Format'
    domain = email.split('@')[1]
    mx_server = get_mx_record(domain)
    if not mx_server:
        return 'No MX Record'
    try:
        server = smtplib.SMTP(timeout=10)
        server.connect(mx_server)
        server.helo('example.com')
        server.mail(from_email)
        code, _ = server.rcpt(email)
        server.quit()
        if code == 250:
            return 'Valid'
        else:
            return f'Invalid ({code})'
    except:
        return 'SMTP Error'

HTML_TEMPLATE = """
<!doctype html>
<html lang=\"zh\">
  <head>
    <meta charset=\"utf-8\">
    <title>Email 驗證工具</title>
  </head>
  <body>
    <h2>單一 Email 驗證</h2>
    <form method=\"POST\" action=\"/single\">
      <input type=\"email\" name=\"email\" placeholder=\"輸入 email\" required>
      <button type=\"submit\">驗證</button>
    </form>
    {% if single_result %}<p>結果：{{ single_result }}</p>{% endif %}

    <h2>批次 CSV 驗證 (最大 100MB)</h2>
    <form method=\"POST\" action=\"/batch\" enctype=\"multipart/form-data\">
      <input type=\"file\" name=\"csvfile\" accept=\".csv\" required>
      <button type=\"submit\">上傳並驗證</button>
    </form>
    {% if batch_results %}
      <h3>結果：</h3>
      <ul>
        {% for email, result in batch_results %}
          <li>{{ email }}: {{ result }}</li>
        {% endfor %}
      </ul>
    {% endif %}
  </body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/single', methods=['POST'])
def single():
    email = request.form['email']
    result = smtp_check(email)
    return render_template_string(HTML_TEMPLATE, single_result=f"{email}: {result}")

@app.route('/batch', methods=['POST'])
def batch():
    file = request.files['csvfile']
    if file and file.filename.endswith('.csv'):
        if file.content_length and file.content_length > 100 * 1024 * 1024:
            return "檔案過大，請限制在 100MB 以下。"
        stream = io.StringIO(file.stream.read().decode("utf-8"))
        reader = csv.reader(stream)
        results = []
        for row in reader:
            if row:
                email = row[0]
                result = smtp_check(email)
                results.append((email, result))
        return render_template_string(HTML_TEMPLATE, batch_results=results)
    return "請上傳正確的 CSV 檔案。"

def open_browser():
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    threading.Timer(1.0, open_browser).start()
    app.run()
