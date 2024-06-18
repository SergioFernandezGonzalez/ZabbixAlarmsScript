from flask import Flask, render_template_string, request, redirect, url_for, session
from jira import JIRA, JIRAError

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'  # Cambiar a una clave segura y única
JIRA_SERVER = 'https://jira.tid.es'

# Función para buscar problemas según el componente y la versión de corrección seleccionados
def search_issues_by_component(component, fix_version, username, password):
    try:
        # Configura el cliente JIRA con las credenciales proporcionadas por el usuario
        jira = JIRA(server=JIRA_SERVER, basic_auth=(username, password))

        # Realiza la búsqueda de problemas en JIRA
        jql_query = f'component = "{component}" AND fixVersion = "{fix_version}"'
        issues = jira.search_issues(jql_query)

        return issues

    except JIRAError as e:
        app.logger.error(f"Error en JIRA: {e.status_code} - {e.text}")
        raise

# Función para obtener detalles de problemas relacionados con comentarios de Zabbix Alarms (SCOMs)
def get_issue_details(issues):
    issue_details = []
    for issue in issues:
        if hasattr(issue.fields, 'comment') and issue.fields.comment.comments:
            for comment in issue.fields.comment.comments:
                if "Zabbix Alarms (SCOMs)" in comment.body:
                    # Lista de frases específicas a evitar
                    unwanted_phrases = [
                        "No added", "- _No alarm added_", "- _No new alarm added_", "- _No new/updated alarm_", 
                        "None", "_No new/updated alarms_", "No Zabbix", "_no alarms", "Non added", "Not needed", 
                        "No SCOMs", "no alarms", "No alarms", "- _List of new/updated alarms_", 
                        "- _List of new/updated alarms_", "- No new/updated alarm", "- _Non Added_", "-","- No new alarms"
                    ]

                    # Filtrar las líneas no deseadas
                    def is_unwanted(line):
                        # Verificar si la línea es solo un guion o contiene una frase no deseada
                        if line.strip() == "-":
                            return True
                        for phrase in unwanted_phrases:
                            if line.startswith(phrase):
                                return True
                        return False

                    # Comprobar si alguna de las frases no deseadas está presente en el comentario
                    if not any(is_unwanted(line) for line in comment.body.splitlines()):
                        start_index = comment.body.find("*Zabbix Alarms (SCOMs):*") + len("*Zabbix Alarms (SCOMs):*")
                        zabbix_alarms_content = comment.body[start_index:].strip()
                        scom_list = zabbix_alarms_content.split("[SCOM]")
                        scom_list = [item.strip() for item in scom_list if item.strip()]
                        issue_details.append(
                            (issue.key, issue.fields.summary, scom_list, issue.permalink())
                        )
                        break
    return issue_details

# Función para generar opciones para el select de componentes
def generate_component_options():
    components = [
        "gvp.api",
        "gvp.authenticationservice",
        "gvp.backend.api",
        "gvp.blender.api",
        "gvp.bss.scheduler",
        "gvp.catalogexporter.agent",
        "gvp.catalogexporter.contentwise.agent",
        "gvp.catalogexporter",
        "gvp.catalogmanagement.agent",
        "gvp.catalogmanagement.api",
        "gvp.catalogmanagement.api.v2",
        "gvp.catalogmanagement.queue.guard.agent",
        "gvp.catchup.agent",
        "gvp.commands.agent",
        "gvp.commands.consolidator",
        "gvp.commands.scheduler",
        "gvp.contentimporter",
        "gvp.contentmonitor",
        "gvp.dmm",
        "gvp.dmmws",
        "gvp.drm.api",
        "gvp.drm.proxy.api",
        "gvp.email.agent",
        "gvp.epg.async",
        "gvp.epg.programreader",
        "gvp.epg.programwatcher",
        "gvp.externaldistributor.api",
        "gvp.externallogs",
        "gvp.fairplay.issuer",
        "gvp.filewatcher",
        "gvp.gal",
        "gvp.itaas.postman",
        "gvp.itaas.postman.db",
        "gvp.itaas.prestige",
        "gvp.itaas.prometheus",
        "gvp.itaas.prometheus.db",
        "gvp.jobs.api",
        "gvp.metadataenrichment.agent",
        "gvp.metadataenrichment.api",
        "gvp.mib5",
        "gvp.mib.drm.api",
        "gvp.mib.redirector",
        "gvp.mibauth",
        "gvp.moviemetadatavalidation.agent",
        "gvp.netflix.agents.read",
        "gvp.netflix.agents.readchangeplan",
        "gvp.netflix.agents.send",
        "gvp.netflix.api",
        "gvp.nginx.content.api",
        "gvp.nginx.cotafiles",
        "gvp.nginx.drm.issuers",
        "gvp.nginx.medias",
        "gvp.notifications.apn",
        "gvp.notifications.consolidator",
        "gvp.notifications.errormanager",
        "gvp.notifications.fcm",
        "gvp.notifications.mediaroom",
        "gvp.notifications.openplatform",
        "gvp.notifications.scheduler",
        "gvp.opch.ott.global",
        "gvp.parameters.api",
        "gvp.playbackconcurrency.api",
        "gvp.playready.issuer",
        "gvp.premiumtvposters",
        "gvp.provision.agent",
        "gvp.provision.api",
        "gvp.purchase.event.hub",
        "gvp.purchase.event.manager",
        "gvp.purchases.api",
        "gvp.sports.api",
        "gvp.sports.epg.matching.consumer",
        "gvp.sports.external.consumer",
        "gvp.sports.scheduler",
        "gvp.sso",
        "gvp.tags.agent",
        "gvp.tags.api",
        "gvp.user.bi.agent",
        "gvp.vrm.proxy",
        "gvp.vrm.pvr.agent",
        "gvp.widevine"
    ]

    options_html = ""
    for component in components:
        options_html += f"<option value='{component}'>{component}</option>"

    return options_html

@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    component_options = generate_component_options()

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - Zabbix Alarms Issues</title>

        <style>
            body {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            form {
                width: 80%;
                max-width: 600px;
                padding: 20px;
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
            select, button {
                width: calc(100% - 22px);
                padding: 10px;
                margin: 8px 0;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            button[type=submit] {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            button[type=submit]:hover {
                background-color: #45a049;
            }
        </style>
    </head>
    <body>
        <div>
            <h1 style="text-align: center;">Zabbix Alarms (SCOMs) by Component and Fix Version</h1>
            <form action="/search" method="get">
                <label for="component">Select a component:</label>
                <select id="component" name="component">
                    {{ component_options | safe }}
                </select>
                <label for="fix_version">Select a fix version:</label>
                <select id="fix_version" name="fix_version">
                    <option value="GVPCore_24.10">GVPCore_24.10</option>
                    <option value="GVPCore_24.7">GVPCore_24.7</option>
                    <option value="GVPCore_24.5">GVPCore_24.5</option>
                </select>
                <button type="submit">Search</button>
            </form>
        </div>
    </body>
    </html>
    """, component_options=component_options)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            # Intenta autenticar con JIRA usando las credenciales ingresadas por el usuario
            jira = JIRA(server=JIRA_SERVER, basic_auth=(username, password))
            
            # Si la autenticación es exitosa, establece la sesión como autenticada
            session['logged_in'] = True
            session['username'] = username
            session['password'] = password

            return redirect(url_for('index'))

        except JIRAError as e:
            app.logger.error(f"Error de autenticación en JIRA: {e.status_code} - {e.text}")
            error = "Error de autenticación. Por favor, verifica tu nombre de usuario y contraseña."

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Login Jira Tid - Zabbix Alarms Issues</title>
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        form {
            width: 80%;
            max-width: 400px;
            padding: 20px;
            border: 1px solid #ccc;
            border-radius: 5px;
            background-color: #f9f9f9;
        }
        input[type=text], input[type=password] {
            width: calc(100% - 22px);
            padding: 10px;
            margin: 8px 0;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        button[type=submit] {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            width: 100%;
            padding: 10px;
            margin-top: 10px;
        }
        button[type=submit]:hover {
            background-color: #45a049;
        }
        .error {
            color: red;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div>
        <h2 style="text-align: center;">Login - Zabbix Alarms Issues</h2>
        <form action="/login" method="post">
            {% if error %}
            <p class="error">{{ error }}</p>
            {% endif %}
            <label for="username">Username:</label>
            <input type="text" id="username" name="username" required>
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>

    """, error=error)

@app.route('/search')
def search():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    component = request.args.get('component')
    fix_version = request.args.get('fix_version')

    username = session['username']
    password = session['password']

    try:
        issues = search_issues_by_component(component, fix_version, username, password)
        issue_details = get_issue_details(issues)

        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Zabbix Alarms Issues</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                }
                table {
                    width: 80%;
                    border-collapse: collapse;
                    margin: 20px auto;
                }
                th, td {
                    padding: 8px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }
                th {
                    background-color: #f2f2f2;
                }
                tr:hover {
                    background-color: #f5f5f5;
                }
                h1 {
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <h1>Zabbix Alarms (SCOMs) for Component: {{ component }} and Fix Version: {{ fix_version }}</h1>
            <table>
                <tr>
                    <th>Issue Key</th>
                    <th>Summary</th>
                    <th>Zabbix Alarms (SCOMs)</th>
                    <th>Link</th>
                </tr>
                {% for key, summary, scom_list, link in issue_details %}
                <tr>
                    <td>{{ key }}</td>
                    <td>{{ summary }}</td>
                    <td>
                        <ul>
                        {% for scom in scom_list %}
                            <li>{{ scom }}</li>
                        {% endfor %}
                        </ul>
                    </td>
                    <td><a href="{{ link }}" target="_blank">View Issue</a></td>
                </tr>
                {% endfor %}
            </table>
        </body>
        </html>
        """, component=component, fix_version=fix_version, issue_details=issue_details)

    except JIRAError as e:
        error = f"Error en JIRA: {e.status_code} - {e.text}"
        app.logger.error(error)
        return render_template_string(f"<h2>{error}</h2>")

if __name__ == '__main__':
    app.run(debug=True, port=3113)

