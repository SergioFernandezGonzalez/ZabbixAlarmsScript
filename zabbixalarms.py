from dotenv import load_dotenv
from jira import JIRA
import os
from flask import Flask, request

# Load environment variables
load_dotenv()

# Get JIRA credentials from environment variables
USERNAME_TID = os.getenv("USERNAME_TID")
PASSWORD_TID = os.getenv("PASSWORD_TID")
SERVER_TID = os.getenv("SERVER_TID")

# JIRA options
options = {'server': SERVER_TID}



# Initialize JIRA client
jira = JIRA(basic_auth=(USERNAME_TID, PASSWORD_TID), options=options)

app = Flask(__name__)

# Function to generate options for the component select
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

# Function to search for issues based on selected component
def search_issues_by_component(component, fix_version):
    return jira.search_issues(f'component = "{component}" AND issuetype in ("User Story", Bug, "sub-bug", Task, Requirement, Vulnerability) AND project in (GVPPLATF, OPSSUP) AND resolution in (Fixed, Done, EMPTY) AND fixVersion in ("{fix_version}")')


# Function to retrieve issue details related to Zabbix Alarms (SCOMs) comments
def get_issue_details(issues):
    issue_details = []
    for issue in issues:
        # Check if the issue has comments
        if hasattr(issue.fields, 'comment') and issue.fields.comment.comments:
            # Iterate through the comments of the issue
            for comment in issue.fields.comment.comments:
                # Check if the comment contains "Zabbix Alarms (SCOMs)"
                if "Zabbix Alarms (SCOMs)" in comment.body:
                    # Check if the comment contains phrases indicating no added alarms
                    no_added_present = any(phrase in comment.body for phrase in ["No added", "No Zabbix", "_no alarms", "Non added", "Not needed", "No SCOMs", "no alarms", "No alarms", "- _List of new/updated alarms_","- _List of new/updated alarms_", "- No new/updated alarm", "- _Non Added_" ])
                    # If no phrases indicating no added alarms are found, add the details to the list
                    if not no_added_present:
                        # Find the start index of the content after "*Zabbix Alarms (SCOMs):*"
                        start_index = comment.body.find("*Zabbix Alarms (SCOMs):*") + len("*Zabbix Alarms (SCOMs):*")
                        # Extract the content
                        zabbix_alarms_content = comment.body[start_index:].strip()
                        # Split the content by "[SCOM]"
                        scom_list = zabbix_alarms_content.split("[SCOM]")
                        # Remove empty elements from the list
                        scom_list = [item.strip() for item in scom_list if item.strip()]
                        issue_details.append((issue.key, issue.fields.summary, scom_list, issue.permalink()))
                        break  # Break the loop after finding the comment to move to the next issue
    return issue_details

@app.route('/search', methods=['GET'])
def search():
    # Get selected component from the form
    selected_component = request.args.get('component')
    selected_fix_version = request.args.get('fix_version')
    # Search for issues based on the selected component
    issues = search_issues_by_component(selected_component, selected_fix_version)

    
    # Get issue details related to Zabbix Alarms (SCOMs) comments
    issue_details = get_issue_details(issues)
    
    # Generate HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Zabbix Alarms Issues</title>
        <style>
            body {{
                margin-top: 50px; 
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            tr:hover {{
                background-color: #ddd;
            }}
            a {{
                text-decoration: none;
                color: #0052cc;
                font-weight: bold;
            }}
            .zabbix-title {{
                color: #8a2be2; /* Dark purple */
            }}
            .zabbix-content {{
                color: #ff0000; /* Red */
                font-size: 16px;
            }}
            .scom-list {{
                color: #000000; /* Black */
                font-size: 14px;
            }}
            .back-to-home {{
                position: absolute;
                top: 10px;
                left: 10px;
                margin: 20px;
            }}
        </style>
    </head>
    <body>
        <a href="/" class="back-to-home">&larr; Atrás</a>  <!-- Botón para volver a la página principal con una flecha hacia la izquierda -->
        <h2>Zabbix Alarms Issues for Component: {selected_component}</h2>
        <table>
            <tr>
                <th>JIRA Key</th>
                <th>Ticket Name</th>
                <th>Comments</th>
            </tr>
    """

    for jira_key, ticket_name, scom_list, issue_link in issue_details:
        html_content += f"""
            <tr>
                <td><a href='{issue_link}'>{jira_key}</a></td>
                <td>{ticket_name}</td>
                <td>
                    <h2 class="zabbix-title">Zabbix Alarms (SCOMs)</h2>
    """

        for scom_item in scom_list:
            html_content += f"""
                    <ul class="scom-list">
                        <li>{scom_item}</li>
                    </ul>
    """
        html_content += """
                </td>
            </tr>
    """

    html_content += """
        </table>
    </body>
    </html>
    """
   

    return html_content

@app.route('/')
def index():
    # Generate options for the component select
    component_options = generate_component_options()
    
    # Generate HTML content for the component selection form
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Zabbix Alarms Issues</title>
    </head>
    <body>
        <h1>Zabbix Alarms (SCOMs) by Component and FV</h1>
        <form action="/search" method="get">
            <label for="component">Select a component:</label>
            <select id="component" name="component">
                {component_options}  <!-- Include component options here -->
            </select>
            <label for="fix_version">Select a fix version:</label>
            <select id="fix_version" name="fix_version">
                <option value="GVPCore_24.7">GVPCore_24.7</option>
                <option value="GVPCore_24.5">GVPCore_24.5</option>
                <!-- Add more options as needed -->
            </select>
            <button type="submit">Search</button>
        </form>
    </body>
    </html>
    """
    
    
    return html_content

if __name__ == '__main__':
    app.run(debug=True)
